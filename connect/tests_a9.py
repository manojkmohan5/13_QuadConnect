"""
Tests for P1-A9: the check of the model's filters against the request's own
words (connect.ai_search.check_against_request), run on every model answer
before the database query.

    python manage.py test connect.tests_a9

No model is loaded: where understand() runs, the model's reply comes from
patching connect.ai_search.generate_reply, as in tests_a6.py. The T-numbers
are the evaluation requests in README_AI.md (Part 3).
"""

from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from connect import ai_search

INTERESTS = ["Basketball", "Gaming", "Movies", "Reading", "Illini Robotics", "Technology",
             "Engineers Without Borders"]
COLLEGES = ["College of Media", "Gies College of Business", "Grainger College of Engineering"]


def check(filters, request):
    return ai_search.check_against_request(filters, request, INTERESTS, COLLEGES)


class CheckAgainstRequestTests(SimpleTestCase):

    def test_t03_corrects_college_to_grainger(self):
        checked = check({"interests": ["Reading"], "college": "Gies College of Business", "energy": "QUIET"},
                        "quiet engineering students who love reading")
        self.assertEqual(checked, {"interests": ["Reading"], "college": "Grainger College of Engineering",
                                   "energy": "QUIET"})

    def test_t13_removes_unrequested_day_and_time(self):
        checked = check({"interests": ["Movies"], "college": "College of Media", "connection": "FRIEND",
                         "day": "SUNDAY", "time": "10-12"},
                        "journalism majors into movies, for a one-on-one")
        self.assertEqual(checked, {"interests": ["Movies"], "college": "College of Media", "connection": "FRIEND"})

    def test_t02_keeps_requested_saturday_afternoon(self):
        request = "find gamers who are free saturday afternoon"
        asked = {"interests": ["Gaming"], "day": "SATURDAY", "time": "14-16"}
        self.assertEqual(check(asked, request), asked)
        # A different day and time from the model give way to the ones the request names.
        self.assertEqual(check({"interests": ["Gaming"], "day": "SUNDAY", "time": "10-12"}, request), asked)

    def test_t10_removes_an_unrequested_one_on_one(self):
        checked = check({"interests": ["Illini Robotics"], "connection": "FRIEND"},
                        "robotics club folks or people into tech")
        self.assertEqual(checked, {"interests": ["Illini Robotics"]})

    def test_it_never_adds_a_filter(self):
        self.assertEqual(check({}, "gamers from grainger, one-on-one, free saturday afternoon"), {})
        self.assertEqual(check({"interests": ["Gaming"]}, "gamers free saturday afternoon"), {"interests": ["Gaming"]})

    def test_engineers_without_borders_is_a_club_not_the_college(self):
        words = ai_search.keyword_filters("members of engineers without borders", INTERESTS, COLLEGES)
        self.assertEqual(words, {"interests": ["Engineers Without Borders"]})
        words = ai_search.keyword_filters("engineering students", INTERESTS, COLLEGES)
        self.assertEqual(words, {"college": "Grainger College of Engineering"})


@override_settings(AI_LOCAL_ENABLED=True)  # CI sets AI_LOCAL_ENABLED=0; generate_reply is replaced anyway
class UnderstandAppliesTheCheckTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def understand(self, reply, request):
        with patch("connect.ai_search.vocabulary", return_value=(INTERESTS, COLLEGES)), \
                patch("connect.ai_search.generate_reply", return_value=reply):
            return ai_search.understand(request)

    def test_the_model_answer_is_checked_before_the_query(self):
        answer = self.understand('{"interests": ["Movies"], "college": "College of Media", "connection": "FRIEND",'
                                 ' "day": "SUNDAY", "time": "10-12"}',
                                 "journalism majors into movies, for a one-on-one")
        self.assertEqual(answer["source"], "model")
        self.assertEqual(answer["filters"],
                         {"interests": ["Movies"], "college": "College of Media", "connection": "FRIEND"})

    def test_a_correct_answer_passes_unchanged(self):
        answer = self.understand('{"interests": ["Gaming"], "day": "SATURDAY", "time": "14-16"}',
                                 "find gamers who are free saturday afternoon")
        self.assertEqual(answer["filters"], {"interests": ["Gaming"], "day": "SATURDAY", "time": "14-16"})
