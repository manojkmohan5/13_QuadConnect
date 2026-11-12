"""
Tests for joining QuadConnect (connect/onboarding.py): a double click on
"Create account", and setting up a profile after the first login.

    python manage.py test connect.tests_onboarding
"""

from unittest.mock import patch

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from .models import Interest, InterestCategory, StudentProfile, TimeBlock, Weekday

PASSWORD = "quad-Connect-2026!"  # noqa: S105 - a test password
NUDGE = "Your profile is not set up yet."


class OnboardingTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.gaming = Interest.objects.create(name="Gaming", category=InterestCategory.HOBBY)
        cls.gym = Interest.objects.create(name="Gym", category=InterestCategory.HOBBY)
        cls.esports = Interest.objects.create(name="UIUC Esports", category=InterestCategory.RSO)
        Interest.objects.create(name="Coffee", category=InterestCategory.ACTIVITY)
        StudentProfile.objects.create(
            user=User.objects.create_user("jordan4"), net_id="jordan4",
            illinois_email="jordan4@illinois.edu", full_name="Jordan Alvarez",
            college="Grainger College of Engineering")
        cls.maddy = User.objects.create_user("maddy", "maddy1234@gmail.com", PASSWORD)

    def answers(self, **changes):
        """The profile form, filled in as a student would send it."""
        data = {
            "full_name": "Maddy Brooks", "net_id": "mbrooks2",
            "college": "School of Information Sciences", "department": "Information Sciences",
            "preferred_connection": "SQUAD", "group_preference": "SMALL",
            "social_energy": "4", "conversation_style": "DEEP",
            "hobbies": [self.gaming.pk, self.gym.pk], "clubs": [self.esports.pk],
            "saturday": [TimeBlock.AFTERNOON], "sunday": [TimeBlock.MORNING, TimeBlock.EVENING],
        }
        data.update(changes)
        return data


class SignUpTests(OnboardingTestCase):

    def test_a_second_copy_of_the_form_gets_the_form_back_not_a_500(self):
        # A double click: both copies pass the "username taken" check before
        # either is saved. With the check skipped, this copy is the second.
        with patch.object(DefaultAccountAdapter, "clean_username",
                          lambda self, username, shallow=False: username):
            response = self.client.post(reverse("account_signup"), {
                "username": "maddy", "email": "maddy.again@gmail.com",
                "password1": PASSWORD, "password2": PASSWORD})
        self.assertContains(response, "The account was not created.")
        self.assertContains(response, escape('The username "maddy" was taken a moment ago'))
        self.assertEqual(User.objects.filter(username="maddy").count(), 1)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_new_account_goes_on_to_set_up_its_profile(self):
        response = self.client.post(reverse("account_signup"), {
            "username": "mbrooks", "email": "MBrooks2@illinois.edu",
            "password1": PASSWORD, "password2": PASSWORD}, follow=True)
        self.assertRedirects(response, reverse("connect:profile"))
        self.assertContains(response, "<h1 class=\"page\">Set up your profile</h1>", html=True)
        # The NetID is read from an illinois.edu address.
        self.assertEqual(response.context["form"]["net_id"].value(), "mbrooks2")
        self.assertNotContains(response, NUDGE)  # not on the form itself
        # Only hobbies and clubs are offered: meeting activities are for matches.
        self.assertContains(response, "UIUC Esports")
        self.assertNotContains(response, "Coffee")


class LoginTests(OnboardingTestCase):

    def test_a_student_with_no_profile_sets_it_up_first(self):
        response = self.client.post(reverse("account_login") + "?next=/reports/",
                                    {"login": "maddy", "password": PASSWORD})
        self.assertRedirects(response, reverse("connect:profile"), fetch_redirect_response=False)

    def test_staff_go_where_they_were_going(self):
        User.objects.create_user("staffer", password=PASSWORD, is_staff=True)
        response = self.client.post(reverse("account_login") + "?next=/reports/",
                                    {"login": "staffer", "password": PASSWORD})
        self.assertRedirects(response, "/reports/", fetch_redirect_response=False)


class ProfileTests(OnboardingTestCase):

    def setUp(self):
        self.client.force_login(self.maddy)

    def test_until_it_is_set_up_every_page_links_to_the_form(self):
        response = self.client.get(reverse("connect:student-list"))
        self.assertContains(response, NUDGE)
        self.assertContains(response, f'class="me" href="{reverse("connect:profile")}"')
        self.client.force_login(User.objects.create_user("staffer", is_staff=True))
        self.assertNotContains(self.client.get(reverse("connect:student-list")), NUDGE)

    def test_saving_makes_the_profile_and_shows_it(self):
        response = self.client.post(reverse("connect:profile"), self.answers(), follow=True)
        profile = StudentProfile.objects.get(user=self.maddy)
        self.assertRedirects(response, profile.get_absolute_url())
        self.assertContains(response, "Your profile is set up.")
        self.assertContains(response, "Edit your profile")
        self.assertEqual(profile.illinois_email, "mbrooks2@illinois.edu")
        self.assertIsNotNone(profile.onboarding_completed_at)
        self.assertFalse(profile.is_sso_verified)  # a NetID typed into a form proves nothing
        self.assertEqual(set(profile.interests.all()), {self.gaming, self.gym, self.esports})
        self.assertEqual(set(profile.availability_slots.values_list("weekday", "time_block")), {
            (Weekday.SATURDAY, TimeBlock.AFTERNOON),
            (Weekday.SUNDAY, TimeBlock.MORNING), (Weekday.SUNDAY, TimeBlock.EVENING)})
        # The student is on the roster now, and the menu links to the profile.
        roster = self.client.get(reverse("connect:student-list"))
        self.assertContains(roster, "Maddy Brooks")
        self.assertContains(roster, f'class="me" href="{profile.get_absolute_url()}"')
        self.assertNotContains(roster, NUDGE)

    def test_a_google_sign_in_with_the_netid_address_is_verified(self):
        EmailAddress.objects.create(user=self.maddy, email="mbrooks2@illinois.edu",
                                    verified=True, primary=True)
        self.client.post(reverse("connect:profile"), self.answers())
        self.assertTrue(StudentProfile.objects.get(user=self.maddy).is_sso_verified)

    def test_each_problem_is_named_and_nothing_is_saved(self):
        problems = {
            "net_id": ("Jordan4 ", 'Another account already has a profile with the NetID "jordan4".'),
            "college": ("", "Choose your college from the list."),
            "hobbies": ([], "Pick at least one interest or club"),
            "saturday": ([], "Pick at least one time on Saturday or Sunday."),
        }
        for field, (value, message) in problems.items():
            with self.subTest(field=field):
                answers = self.answers(**{field: value})
                if field == "hobbies":
                    answers["clubs"] = []
                if field == "saturday":
                    answers["sunday"] = []
                response = self.client.post(reverse("connect:profile"), answers)
                self.assertContains(response, "Your profile was not saved.")
                self.assertContains(response, escape(message))
                self.assertFalse(StudentProfile.objects.filter(user=self.maddy).exists())
        response = self.client.post(reverse("connect:profile"), self.answers(net_id="m.brooks"))
        self.assertContains(response, "A NetID is letters followed by optional digits")

    def test_editing_shows_the_answers_and_replaces_them(self):
        self.client.post(reverse("connect:profile"), self.answers())
        profile = StudentProfile.objects.get(user=self.maddy)
        set_up_at = profile.onboarding_completed_at
        profile.interest_links.filter(interest=self.gym).update(is_primary=True)  # starred in Admin

        form = self.client.get(reverse("connect:profile")).context["form"]
        self.assertEqual(form["net_id"].value(), "mbrooks2")
        self.assertEqual(set(form["hobbies"].value()), {self.gaming.pk, self.gym.pk, self.esports.pk})
        self.assertEqual(form["sunday"].value(), [TimeBlock.MORNING, TimeBlock.EVENING])

        response = self.client.post(reverse("connect:profile"), self.answers(
            hobbies=[self.gym.pk], clubs=[], saturday=[], sunday=[TimeBlock.EVENING]), follow=True)
        self.assertContains(response, "Your profile is saved.")
        profile.refresh_from_db()
        self.assertEqual(list(profile.interests.all()), [self.gym])
        self.assertTrue(profile.interest_links.get().is_primary)  # a kept interest keeps its star
        self.assertEqual(list(profile.availability_slots.values_list("weekday", "time_block")),
                         [(Weekday.SUNDAY, TimeBlock.EVENING)])
        self.assertEqual(profile.onboarding_completed_at, set_up_at)
        self.assertEqual(StudentProfile.objects.filter(user=self.maddy).count(), 1)
