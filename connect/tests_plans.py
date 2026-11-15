"""
Tests for plans (connect/plans.py): posting a plan and RSVPing to it.

    python manage.py test connect.tests_plans
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import plans
from .models import CampusLocation, Plan, PlanRSVP, StudentProfile


class PlanTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data", stdout=StringIO())
        cls.host, cls.alice, cls.bob = StudentProfile.objects.order_by("pk")[:3]
        cls.place = CampusLocation.objects.filter(is_approved=True).order_by("-capacity").first()

    def make(self, **kwargs):
        defaults = {"host": self.host, "title": "Board games", "location": self.place, "capacity": 3,
                    "starts_at": timezone.now() + timedelta(days=2)}
        return Plan.objects.create(**{**defaults, **kwargs})

    def as_(self, profile):
        self.client.force_login(profile.user)

    def rsvp(self, plan, action):
        return self.client.post(reverse("connect:plan-rsvp", args=[plan.pk]), {"action": action}, follow=True)


class PostingTests(PlanTestCase):

    def form(self, **overrides):
        when = timezone.localtime(timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
        return {"title": "  Coffee   and  chess ", "starts_at": when, "location": self.place.pk,
                "capacity": 4, "details": "", **overrides}

    def test_a_student_posts_a_plan_and_is_its_host(self):
        self.as_(self.host)
        response = self.client.post(reverse("connect:plan-create"), self.form(), follow=True)
        plan = Plan.objects.get()
        self.assertEqual((plan.host, plan.title), (self.host, "Coffee and chess"))
        self.assertContains(response, "You're hosting")  # template text, not escaped
        self.assertContains(response, "1 of 4 going")

    def test_bad_answers_are_refused_with_a_reason(self):
        self.as_(self.host)
        soon = timezone.localtime(timezone.now() + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M")
        late = timezone.localtime(timezone.now() + timedelta(days=40)).strftime("%Y-%m-%dT%H:%M")
        hidden = CampusLocation.objects.create(name="Someone's flat", street_address="1 Elm St", is_approved=False)
        cases = [
            ({"starts_at": soon}, "at least an hour from now"),
            ({"starts_at": late}, "in the next 30 days"),
            ({"location": hidden.pk}, "Choose one of the approved places."),
            ({"capacity": 1}, "room for at least 2 people"),
            ({"capacity": self.place.capacity + 1}, f"seats up to {self.place.capacity}"),
            ({"title": "   "}, "Say what you&#x27;re doing"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                response = self.client.post(reverse("connect:plan-create"), self.form(**overrides))
                self.assertContains(response, message)
        self.assertFalse(Plan.objects.exists())

    def test_without_a_profile_you_are_asked_to_set_one_up(self):
        self.client.force_login(User.objects.create_user("newcomer"))
        response = self.client.post(reverse("connect:plan-create"), self.form())
        self.assertContains(response, "First, your profile")
        self.assertFalse(Plan.objects.exists())

    def test_the_list_shows_upcoming_plans_but_not_past_or_called_off_ones(self):
        self.make(title="Upcoming hike")
        self.make(title="Old hike", starts_at=timezone.now() - timedelta(hours=3))
        self.make(title="Cancelled hike", cancelled_at=timezone.now())
        self.as_(self.alice)
        response = self.client.get(reverse("connect:plan-list"))
        upcoming = [plan.title for plan in response.context["upcoming"]]
        self.assertEqual(upcoming, ["Upcoming hike"])


class RSVPTests(PlanTestCase):

    def test_join_then_leave(self):
        plan = self.make()
        self.as_(self.alice)
        self.assertContains(self.rsvp(plan, "join"), "You&#x27;re going. See you there!")
        self.assertTrue(plan.rsvps.filter(profile=self.alice).exists())
        self.assertContains(self.rsvp(plan, "leave"), "You&#x27;re no longer going")
        self.assertFalse(plan.rsvps.exists())

    def test_a_full_plan_takes_no_one_else(self):
        plan = self.make(capacity=2)  # the host and one more
        PlanRSVP.objects.create(plan=plan, profile=self.alice)
        self.as_(self.bob)
        self.assertContains(self.rsvp(plan, "join"), "That can&#x27;t be done any more")
        self.assertEqual(plan.rsvps.count(), 1)

    def test_the_last_place_goes_to_one_student_only(self):
        plan = self.make(capacity=2)
        plans.join(plan, self.alice)
        with self.assertRaises(plans.Full):
            plans.join(plan, self.bob)  # passed the page's check before alice took the place
        self.assertEqual(list(plan.rsvps.values_list("profile", flat=True)), [self.alice.pk])

    def test_one_place_per_student(self):
        plan = self.make()
        plans.join(plan, self.alice)
        with self.assertRaises(IntegrityError):
            PlanRSVP.objects.create(plan=plan, profile=self.alice)

    def test_the_host_cannot_rsvp_to_their_own_plan(self):
        plan = self.make()
        self.as_(self.host)
        self.rsvp(plan, "join")
        self.assertFalse(plan.rsvps.exists())

    def test_no_rsvps_once_started_or_called_off(self):
        for plan in (self.make(starts_at=timezone.now() - timedelta(minutes=5)),
                     self.make(cancelled_at=timezone.now())):
            with self.subTest(plan=plan.title):
                self.as_(self.alice)
                self.rsvp(plan, "join")
                self.assertFalse(plan.rsvps.exists())

    def test_rsvp_is_post_only(self):
        self.as_(self.alice)
        response = self.client.get(reverse("connect:plan-rsvp", args=[self.make().pk]))
        self.assertEqual(response.status_code, 405)


class CancelTests(PlanTestCase):

    def test_only_the_host_can_call_it_off(self):
        plan = self.make()
        self.as_(self.alice)
        self.client.post(reverse("connect:plan-cancel", args=[plan.pk]))
        plan.refresh_from_db()
        self.assertIsNone(plan.cancelled_at)

        self.as_(self.host)
        response = self.client.post(reverse("connect:plan-cancel", args=[plan.pk]), follow=True)
        plan.refresh_from_db()
        self.assertIsNotNone(plan.cancelled_at)
        self.assertContains(response, "called this plan off")

    def test_your_plans_lists_hosted_and_joined_with_true_counts(self):
        self.make(title="Mine")
        joined = self.make(host=self.bob, title="Bob's")
        PlanRSVP.objects.create(plan=joined, profile=self.alice)
        PlanRSVP.objects.create(plan=joined, profile=self.host)
        self.as_(self.host)
        mine = {plan.title: plan.going for plan in self.client.get(reverse("connect:plan-list")).context["mine"]}
        self.assertEqual(mine, {"Mine": 1, "Bob's": 3})
