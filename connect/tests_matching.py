"""
Tests for weekend matching (connect/matching.py) and its pages
(connect/meetups.py): sign up, get matched, answer, check in, feedback.

    python manage.py test connect.tests_matching

"Now" is fixed: Thursday 12 November 2026, 10 AM in Champaign, so the
weekend being matched is Saturday 14 and Sunday 15 November.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import matching
from .models import (
    AvailabilitySlot,
    CampusLocation,
    ConnectionType,
    ExperienceFeedback,
    Interest,
    InterestCategory,
    Match,
    MatchRequest,
    MatchStatus,
    ParticipantResponse,
    ProfileInterest,
    StudentProfile,
    TimeBlock,
    Weekday,
)

CHAMPAIGN = ZoneInfo("America/Chicago")
NOW = datetime(2026, 11, 12, 10, 0, tzinfo=CHAMPAIGN)  # a Thursday
WEEK = date(2026, 11, 9)
SAT_2PM = datetime(2026, 11, 14, 14, 0, tzinfo=CHAMPAIGN)
SAT, SUN = Weekday.SATURDAY, Weekday.SUNDAY
FRIEND, SQUAD = ConnectionType.FRIEND, ConnectionType.SQUAD


class MatchingTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.gaming = Interest.objects.create(name="Gaming", category=InterestCategory.HOBBY)
        cls.gym = Interest.objects.create(name="Gym", category=InterestCategory.HOBBY)
        cls.music = Interest.objects.create(name="Music", category=InterestCategory.HOBBY)
        cls.board_games = Interest.objects.create(name="Board games", category=InterestCategory.ACTIVITY)
        cls.cafe = CampusLocation.objects.create(name="Espresso Royale", street_address="1117 W Oregon St",
                                                 capacity=6)
        cls.union = CampusLocation.objects.create(name="Illini Union", street_address="1401 W Green St",
                                                  capacity=12)
        CampusLocation.objects.create(name="Closed Cafe", street_address="1 Main St", is_approved=False)

    def student(self, net_id, interests, free=((SAT, TimeBlock.AFTERNOON),), starred=()):
        profile = StudentProfile.objects.create(
            user=User.objects.create_user(net_id), net_id=net_id, illinois_email=f"{net_id}@illinois.edu",
            full_name=net_id.title(), college="Grainger College of Engineering")
        for interest in interests:
            ProfileInterest.objects.create(profile=profile, interest=interest, is_primary=interest in starred)
        for day, block in free:
            AvailabilitySlot.objects.create(profile=profile, weekday=day, time_block=block)
        return profile

    def match_of(self, profile):
        mine = matching.current_match(profile, WEEK)
        return mine.match if mine else None

    def members(self, match):
        return {p.profile for p in match.participants.all()}


class WeekendTests(MatchingTestCase):

    def test_the_coming_weekend_and_its_blocks(self):
        self.assertEqual(matching.coming_week(NOW), WEEK)
        slots = matching.weekend_slots(WEEK, NOW)
        self.assertEqual(len(slots), 8)
        self.assertEqual(slots[0].start, datetime(2026, 11, 14, 10, 0, tzinfo=CHAMPAIGN))
        # Sunday 1 PM: the 4 PM block is still far enough ahead. 3 PM: not, so next weekend.
        self.assertEqual(matching.coming_week(datetime(2026, 11, 15, 13, 0, tzinfo=CHAMPAIGN)), WEEK)
        self.assertEqual(matching.coming_week(datetime(2026, 11, 15, 15, 0, tzinfo=CHAMPAIGN)),
                         WEEK + timedelta(days=7))


class PairingTests(MatchingTestCase):

    def test_two_students_who_share_an_interest_and_a_time_are_paired(self):
        ana = self.student("ana1", [self.gaming, self.gym],
                           [(SAT, TimeBlock.AFTERNOON), (SUN, TimeBlock.MIDDAY)])
        ben = self.student("ben2", [self.gaming], [(SUN, TimeBlock.MIDDAY), (SAT, TimeBlock.AFTERNOON)])
        self.assertEqual(matching.sign_up(ana, FRIEND, WEEK, NOW), [])  # nobody else yet
        [match] = matching.sign_up(ben, FRIEND, WEEK, NOW)
        self.assertEqual(self.members(match), {ana, ben})
        self.assertEqual((match.connection_type, match.status), (FRIEND, MatchStatus.PROPOSED))
        self.assertEqual(match.scheduled_for, SAT_2PM)  # the soonest block both are free
        self.assertEqual(match.week_start, WEEK)
        self.assertEqual(match.location, self.cafe)  # approved, and the smallest that seats them
        self.assertRegex(match.check_in_code, r"^QC-\d{4}$")
        self.assertEqual(match.suggested_activity, self.board_games)  # they share Gaming
        for p in match.participants.all():
            self.assertEqual((p.response, p.match_reason), (ParticipantResponse.PENDING, "Gaming"))

    def test_no_pair_without_a_shared_interest_or_a_shared_time(self):
        ana = self.student("ana1", [self.gaming])
        matching.sign_up(ana, FRIEND, WEEK, NOW)
        matching.sign_up(self.student("cy3", [self.music]), FRIEND, WEEK, NOW)
        matching.sign_up(self.student("dee4", [self.gaming], [(SUN, TimeBlock.MORNING)]), FRIEND, WEEK, NOW)
        matching.sign_up(self.student("eve5", [self.gaming]), SQUAD, WEEK, NOW)  # a group, not a 1-on-1
        self.assertFalse(Match.objects.exists())

    def test_the_best_matched_pair_goes_first(self):
        ana = self.student("ana1", [self.gaming, self.gym, self.music])
        ben = self.student("ben2", [self.gaming])
        cy = self.student("cy3", [self.gym, self.music], starred=[self.music])
        for profile in (ana, ben, cy):  # all in the pool before matching runs
            MatchRequest.objects.create(profile=profile, week_start=WEEK, connection_type=FRIEND)
        [match] = matching.match_week(WEEK, NOW)
        self.assertEqual(self.members(match), {ana, cy})
        self.assertIsNone(self.match_of(ben))

    def test_a_past_or_too_close_block_is_never_used(self):
        saturday_noon = datetime(2026, 11, 14, 12, 30, tzinfo=CHAMPAIGN)
        ana = self.student("ana1", [self.gaming])  # free Saturday 2 PM: under 2 hours away
        matching.sign_up(ana, FRIEND, WEEK, saturday_noon)
        matching.sign_up(self.student("ben2", [self.gaming]), FRIEND, WEEK, saturday_noon)
        self.assertFalse(Match.objects.exists())


class SquadTests(MatchingTestCase):

    def test_a_squad_needs_four_who_share_an_interest_and_a_time(self):
        squad = [self.student(f"s{n}", [self.gaming]) for n in range(4)]
        for profile in squad[:3]:
            self.assertEqual(matching.sign_up(profile, SQUAD, WEEK, NOW), [])
        [match] = matching.sign_up(squad[3], SQUAD, WEEK, NOW)
        self.assertEqual(self.members(match), set(squad))
        self.assertEqual((match.connection_type, match.scheduled_for), (SQUAD, SAT_2PM))

    def test_a_squad_takes_eight_at_most_and_a_venue_that_seats_them(self):
        pool = [self.student(f"s{n}", [self.gaming]) for n in range(9)]
        for profile in pool:
            MatchRequest.objects.create(profile=profile, week_start=WEEK, connection_type=SQUAD)
        [match] = matching.match_week(WEEK, NOW)
        self.assertEqual(self.members(match), set(pool[:8]))  # first to sign up, first in
        self.assertEqual(match.location, self.union)  # the cafe seats 6
        self.assertIsNone(self.match_of(pool[8]))

    def test_a_squad_goes_ahead_without_one_but_not_without_two(self):
        squad = [self.student(f"s{n}", [self.gaming]) for n in range(4)]
        for profile in squad:
            matching.sign_up(profile, SQUAD, WEEK, NOW)
        match = self.match_of(squad[0])
        places = {p.profile: p for p in match.participants.all()}
        matching.respond(places[squad[0]], accept=False, now=NOW)
        match.refresh_from_db()
        self.assertEqual(match.status, MatchStatus.PROPOSED)
        matching.respond(places[squad[1]], accept=False, now=NOW)
        match.refresh_from_db()
        self.assertEqual(match.status, MatchStatus.CANCELLED)


class AnswerTests(MatchingTestCase):

    def setUp(self):
        self.ana = self.student("ana1", [self.gaming])
        self.ben = self.student("ben2", [self.gaming])
        matching.sign_up(self.ana, FRIEND, WEEK, NOW)
        matching.sign_up(self.ben, FRIEND, WEEK, NOW)
        self.match = self.match_of(self.ana)
        self.places = {p.profile: p for p in self.match.participants.select_related("match")}

    def test_both_accept_and_it_is_confirmed(self):
        matching.respond(self.places[self.ana], accept=True, now=NOW)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, MatchStatus.PROPOSED)
        matching.respond(self.places[self.ben], accept=True, now=NOW)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, MatchStatus.CONFIRMED)

    def test_a_decline_matches_the_other_with_someone_else_never_the_decliner(self):
        cy = self.student("cy3", [self.gaming])
        matching.sign_up(cy, FRIEND, WEEK, NOW)  # waiting: the others are taken
        self.assertIsNone(self.match_of(cy))
        matching.respond(self.places[self.ben], accept=False, now=NOW)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, MatchStatus.CANCELLED)
        self.assertEqual(self.members(self.match_of(self.ana)), {self.ana, cy})
        self.assertIsNone(self.match_of(self.ben))  # the only one left is the one he declined

    def test_leaving_the_weekend(self):
        matching.leave(self.ben, WEEK, NOW)
        self.assertFalse(MatchRequest.objects.filter(profile=self.ben).exists())
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, MatchStatus.CANCELLED)
        self.assertIsNone(self.match_of(self.ana))
        self.assertTrue(MatchRequest.objects.filter(profile=self.ana).exists())  # still waiting

    def test_check_in_opens_half_an_hour_before_and_two_complete_it(self):
        ana, ben = self.places[self.ana], self.places[self.ben]
        matching.respond(ana, accept=True, now=NOW)
        matching.respond(ben, accept=True, now=NOW)
        ana.match.refresh_from_db()
        self.assertFalse(matching.can_check_in(ana, SAT_2PM - timedelta(minutes=31)))
        self.assertTrue(matching.can_check_in(ana, SAT_2PM - timedelta(minutes=30)))
        self.assertFalse(matching.can_check_in(ana, SAT_2PM + timedelta(hours=2, minutes=1)))
        self.assertFalse(matching.can_answer(ana, SAT_2PM))  # too late to decline
        matching.check_in(ana, SAT_2PM)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, MatchStatus.CONFIRMED)
        matching.check_in(ben, SAT_2PM + timedelta(minutes=5))
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, MatchStatus.COMPLETED)

    def test_staying_connected_takes_both(self):
        ana, ben = self.places[self.ana], self.places[self.ben]
        for place in (ana, ben):
            place.response, place.checked_in_at = ParticipantResponse.ACCEPTED, SAT_2PM
            place.save()
        self.assertTrue(matching.can_give_feedback(ana))
        ExperienceFeedback.objects.create(participant=ana, rating=5, wants_to_stay_connected=True)
        self.assertFalse(matching.can_give_feedback(ana))
        self.assertEqual(matching.stay_connected(ana), [])  # Ben has not said
        ExperienceFeedback.objects.create(participant=ben, rating=4, wants_to_stay_connected=True)
        self.assertEqual(matching.stay_connected(ana), [self.ben])
        self.assertEqual(matching.stay_connected(ben), [self.ana])


@patch("django.utils.timezone.now", return_value=NOW)
class MeetPageTests(MatchingTestCase):

    def setUp(self):
        self.ana = self.student("ana1", [self.gaming])
        self.ben = self.student("ben2", [self.gaming])

    def sign_up_as(self, profile, kind=FRIEND):
        self.client.force_login(profile.user)
        return self.client.post(reverse("connect:meet"), {"connection_type": kind}, follow=True)

    def test_without_a_profile_the_page_asks_for_one(self, _now):
        self.client.force_login(User.objects.create_user("new"))
        response = self.client.get(reverse("connect:meet"))
        self.assertContains(response, "First, your profile")
        self.assertContains(response, f'href="{reverse("connect:profile")}"')

    def test_sign_up_wait_then_matched_when_someone_fits(self, _now):
        self.assertContains(self.sign_up_as(self.ana), "You&#x27;re signed up")
        self.assertContains(self.client.get(reverse("connect:home")), "You&#x27;re signed up for this weekend")
        response = self.sign_up_as(self.ben)
        self.assertContains(response, "You have a match!")
        self.assertContains(response, "Your Friend Connect (1-on-1)")
        self.assertContains(response, self.ana.get_absolute_url())
        self.client.force_login(self.ana.user)
        self.assertContains(self.client.get(reverse("connect:home")), "You have a match: Saturday 2:00 PM")

    def test_accept_from_the_page_then_check_in_when_it_opens(self, now):
        self.sign_up_as(self.ana)
        self.sign_up_as(self.ben)
        match = Match.objects.get()
        answer = reverse("connect:match-answer", args=[match.pk])
        self.client.post(answer, {"action": "accept"})
        self.client.force_login(self.ana.user)
        response = self.client.post(answer, {"action": "accept", "next": reverse("connect:meet")}, follow=True)
        self.assertRedirects(response, reverse("connect:meet"))
        self.assertContains(response, "Everyone&#x27;s in")
        self.assertContains(response, "Check-in opens 30 minutes before the start")
        response = self.client.post(answer, {"action": "check_in"}, follow=True)
        self.assertContains(response, "That can&#x27;t be done any more")  # Thursday: too early
        now.return_value = SAT_2PM
        response = self.client.post(answer, {"action": "check_in"}, follow=True)
        self.assertContains(response, "You&#x27;re checked in")
        self.assertContains(response, reverse("connect:match-feedback", args=[match.pk]))

    def test_feedback_once_after_checking_in(self, now):
        self.sign_up_as(self.ana)
        self.sign_up_as(self.ben)
        match = Match.objects.get()
        url = reverse("connect:match-feedback", args=[match.pk])
        self.assertRedirects(self.client.get(url), match.get_absolute_url())  # not checked in
        match.participants.update(response=ParticipantResponse.ACCEPTED, checked_in_at=SAT_2PM)
        now.return_value = SAT_2PM + timedelta(hours=2)
        self.assertContains(self.client.get(url), "How was it?")
        response = self.client.post(url, {"rating": "5", "wants_to_stay_connected": "on"}, follow=True)
        self.assertContains(response, "Your feedback is private")
        self.assertTrue(ExperienceFeedback.objects.filter(participant__profile=self.ben,
                                                          wants_to_stay_connected=True).exists())
        self.assertRedirects(self.client.get(url), match.get_absolute_url())  # once

    def test_a_match_is_seen_only_by_its_students_and_staff(self, _now):
        self.sign_up_as(self.ana)
        self.sign_up_as(self.ben)
        match = Match.objects.get()
        self.assertContains(self.client.get(match.get_absolute_url()), "Your part")
        outsider = self.student("cy3", [self.music])
        self.client.force_login(outsider.user)
        for url in (match.get_absolute_url(), reverse("connect:match-icebreakers", args=[match.pk]),
                    reverse("connect:match-feedback", args=[match.pk])):
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.client.post(reverse("connect:match-answer", args=[match.pk]),
                                          {"action": "decline"}).status_code, 404)
        self.assertNotContains(self.client.get(reverse("connect:match-list")), match.get_absolute_url())
        self.client.force_login(User.objects.create_user("staffer", is_staff=True))
        self.assertEqual(self.client.get(match.get_absolute_url()).status_code, 200)
        self.assertContains(self.client.get(reverse("connect:match-list")), match.get_absolute_url())

    def test_leave_from_the_page(self, _now):
        self.sign_up_as(self.ana)
        response = self.client.post(reverse("connect:meet"), {"leave": "1"}, follow=True)
        self.assertContains(response, "You&#x27;ve left this weekend")
        self.assertContains(response, "Sign me up")
        self.assertFalse(MatchRequest.objects.exists())
