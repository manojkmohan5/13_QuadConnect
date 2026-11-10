"""
Tests for P1-A9:

* Part 3: the check of the model's filters against the request's own words
  (connect.ai_search.check_against_request), run on every model answer before
  the database query.
* Part 1: P1-A8's embedding model placing an interest the model wrote in its own
  words on the list (match_by_meaning), and the time limit on the model
  (ModelTimeout).

    python manage.py test connect.tests_a9

No model is loaded: where understand() runs, the model's reply comes from
patching connect.ai_search.generate_reply, as in tests_a6.py, and the
embedding model's similarities from patching embed_similarities. The T-numbers
are the evaluation requests in README_AI.md (Part 3).
"""

import sys
import time
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

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


# --- Part 1: interests placed by meaning (P1-A8's embedding model) ----------------------------

ROOT = Path(__file__).resolve().parent.parent
NAMES = [*INTERESTS, "Art", "Photography", "Outdoors", "Travel"]
SCORES = {  # stand-in similarities: BGE-small's own top two for each word (docs/a9_part1/calibration.csv)
    "Painting": {"Art": 0.822, "Photography": 0.707},
    "Tech": {"Technology": 0.904, "Gaming": 0.643},
    "weather": {"Outdoors": 0.766, "Travel": 0.674},  # close, but not close enough
    "Engineering": {"Engineers Without Borders": 0.747, "Technology": 0.732},  # near two names
    "<b>x</b>": {"Art": 0.99},
}


def similarities(words, names):
    return [[SCORES.get(word, {}).get(name, 0.5) for name in names] for word in words]


def embedder(side_effect=similarities):
    """A patch for embed_similarities: the scores above, or an error."""
    return patch("connect.ai_search.embed_similarities", side_effect=side_effect)


@override_settings(AI_EMBED_ENABLED=True)  # CI sets AI_EMBED_ENABLED=0; embed_similarities is replaced anyway
class MatchByMeaningTests(SimpleTestCase):

    def test_a_word_close_to_one_name_is_placed_on_it(self):
        with embedder():
            self.assertEqual(ai_search.match_by_meaning(["Painting", "Tech"], NAMES),
                             {"Painting": "Art", "Tech": "Technology"})

    def test_a_word_near_no_name_or_near_two_is_left_out(self):
        with embedder():
            self.assertEqual(ai_search.match_by_meaning(["weather", "Engineering", "student_data"], NAMES), {})

    def test_both_limits_must_be_met(self):
        low, lead = ai_search.MEANING_MIN, ai_search.MEANING_LEAD
        cases = [((low + 0.001, low + 0.001 - lead - 0.001), {"Hiking": "Outdoors"}),
                 ((low - 0.001, low - 0.001 - lead - 0.001), {}),  # not similar enough
                 ((low + 0.05, low + 0.05 - lead + 0.001), {})]  # not far enough ahead of Travel
        for (outdoors, travel), expected in cases:
            scores = {"Outdoors": outdoors, "Travel": travel}
            with self.subTest(outdoors=outdoors, travel=travel), \
                    embedder(lambda words, names, s=scores: [[s.get(name, 0.0) for name in names] for _ in words]):
                self.assertEqual(ai_search.match_by_meaning(["Hiking"], NAMES), expected)

    def test_only_a_few_distinct_words_are_compared(self):
        with embedder() as model:
            ai_search.match_by_meaning(["Tech", "Tech", "", *[f"word {n}" for n in range(20)]], NAMES)
        words = model.call_args.args[0]
        self.assertEqual(len(words), 2 * ai_search.MAX_INTERESTS)
        self.assertEqual(words[:2], ["Tech", "word 0"])

    def test_nothing_to_place_never_calls_the_model(self):
        with embedder() as model:
            self.assertEqual(ai_search.match_by_meaning([], NAMES), {})
            self.assertEqual(ai_search.match_by_meaning(["Tech"], []), {})
        model.assert_not_called()

    @override_settings(AI_EMBED_ENABLED=False)
    def test_switched_off_it_is_never_called(self):
        with embedder() as model:
            self.assertEqual(ai_search.match_by_meaning(["Painting"], NAMES), {})
        model.assert_not_called()

    def test_a_missing_busy_or_crashing_model_places_nothing(self):
        for error in (ai_search.ModelUnavailable("no sentence-transformers"), ai_search.ModelBusy("busy"),
                      RuntimeError("out of memory")):
            with self.subTest(error=error), embedder(error):
                self.assertEqual(ai_search.match_by_meaning(["Painting"], NAMES), {})

    def test_an_answer_of_the_wrong_shape_places_nothing(self):
        for rows in ([], [[0.99]], [[0.99] * len(NAMES)] * 3):
            with self.subTest(rows=len(rows)), embedder(lambda words, names, r=rows: r):
                self.assertEqual(ai_search.match_by_meaning(["Painting", "Tech"], NAMES), {})


class EmbedderTests(SimpleTestCase):

    def test_a_missing_sentence_transformers_is_reported_and_not_retried_at_once(self):
        model = ai_search.Embedder("nobody/no-such-model")
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with self.assertRaisesMessage(ai_search.ModelUnavailable, "not installed"):
                model.similarities(["Tech"], NAMES)
            with self.assertRaisesMessage(ai_search.ModelUnavailable, "not retrying yet"):
                model.similarities(["Tech"], NAMES)

    def test_a_busy_embedder_lets_the_search_go_on_at_once(self):
        model = ai_search.Embedder("nobody/no-such-model")
        model.lock.acquire()
        try:
            with patch("connect.ai_search.LOCK_WAIT_SECONDS", 0.01), self.assertRaises(ai_search.ModelBusy):
                model.similarities(["Tech"], NAMES)
        finally:
            model.lock.release()

    def test_the_names_are_encoded_once_until_the_list_changes(self):
        model = ai_search.Embedder("nobody/no-such-model")
        model.model = MagicMock()
        model.model.encode.side_effect = lambda texts, normalize_embeddings: np.ones((len(texts), 4)) / 2
        self.assertEqual(model.similarities(["Tech", "Painting"], NAMES).shape, (2, len(NAMES)))
        model.similarities(["Tech"], NAMES)
        self.assertEqual(model.model.encode.call_count, 3)  # the names, then the words twice
        model.similarities(["Tech"], NAMES[:3])
        self.assertEqual(model.model.encode.call_count, 5)  # a new list is encoded again


@override_settings(AI_LOCAL_ENABLED=True, AI_EMBED_ENABLED=True)
class UnderstandPlacesByMeaningTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def understand(self, reply, request):
        with patch("connect.ai_search.vocabulary", return_value=(NAMES, COLLEGES)), \
                patch("connect.ai_search.generate_reply", return_value=reply):
            return ai_search.understand(request)

    def test_t08_painting_becomes_art(self):
        with embedder() as model:
            answer = self.understand('{"interests": ["Photography", "Painting"]}', "anyone who paints or takes photos")
        self.assertEqual(answer["filters"], {"interests": ["Photography", "Art"]})
        self.assertEqual(answer["by_meaning"], {"Painting": "Art"})
        self.assertEqual(model.call_args.args[0], ["Painting"])  # a name already on the list is not compared

    def test_t10_tech_becomes_technology_and_the_check_still_runs(self):
        with embedder():
            answer = self.understand('{"interests": ["Robotics", "Tech"], "connection": "FRIEND"}',
                                     "robotics club folks or people into tech")
        self.assertEqual(answer["filters"], {"interests": ["Illini Robotics", "Technology"]})

    def test_a_word_near_nothing_is_still_dropped(self):
        with embedder():
            answer = self.understand('{"interests": ["weather"]}', "what's the weather like in Champaign today?")
        self.assertEqual((answer["filters"], answer["by_meaning"]), ({}, {}))

    def test_without_the_embedding_model_the_search_is_as_before(self):
        with embedder(ai_search.ModelUnavailable("not installed")):
            answer = self.understand('{"interests": ["Photography", "Painting"]}', "anyone who paints or takes photos")
        self.assertEqual((answer["source"], answer["filters"]), ("model", {"interests": ["Photography"]}))

    def test_a_placed_name_past_the_limit_is_not_reported(self):
        reply = '{"interests": ["Gaming", "Movies", "Reading", "Basketball", "Painting"]}'
        with embedder():
            answer = self.understand(reply, "gamers, movie fans, readers, ballers and painters")
        self.assertEqual(len(answer["filters"]["interests"]), ai_search.MAX_INTERESTS)
        self.assertEqual(answer["by_meaning"], {})

    def test_answers_with_and_without_it_are_cached_apart(self):
        with embedder(), patch("connect.ai_search.vocabulary", return_value=(NAMES, COLLEGES)), \
                patch("connect.ai_search.generate_reply", return_value='{"interests": ["Painting"]}') as model:
            self.assertEqual(ai_search.understand("painters")["filters"], {"interests": ["Art"]})
            with override_settings(AI_EMBED_ENABLED=False):
                self.assertEqual(ai_search.understand("painters")["filters"], {})
        self.assertEqual(model.call_count, 2)


# --- Part 1: the time limit on the model ---------------------------------------------------------

class Batch(dict):
    """A tokenizer's output, as LocalModel.generate() uses it."""

    def to(self, device):
        return self


class TimeLimitTests(SimpleTestCase):

    def model(self, seconds, reply='{"day": "SUNDAY"}'):
        """A LocalModel whose generation takes `seconds`; nothing is loaded."""
        model = ai_search.LocalModel("nobody/no-such-model")
        model.tokenizer, model.model = MagicMock(pad_token_id=0), MagicMock()
        model.tokenizer.apply_chat_template.return_value = Batch(input_ids=MagicMock(shape=(1, 3)))
        model.tokenizer.decode.return_value = reply
        model.model.generate.side_effect = lambda **kwargs: time.sleep(seconds) or [[1, 2, 3, 4]]
        return model

    @override_settings(AI_LOCAL_MAX_SECONDS=0.05)
    def test_a_generation_stopped_by_the_limit_is_a_timeout(self):
        model = self.model(0.06)
        with patch.object(model, "_shared_start", return_value=None), self.assertRaises(ai_search.ModelTimeout):
            model.generate([])

    @override_settings(AI_LOCAL_MAX_SECONDS=5)
    def test_a_generation_within_the_limit_is_returned(self):
        model = self.model(0)
        with patch.object(model, "_shared_start", return_value=None):
            self.assertEqual(model.generate([]), '{"day": "SUNDAY"}')
        self.assertEqual(model.model.generate.call_args.kwargs["max_time"], 5)

    @override_settings(AI_LOCAL_ENABLED=True)
    def test_a_timeout_is_not_retried_and_the_keyword_parser_answers(self):
        cache.clear()
        with patch("connect.ai_search.vocabulary", return_value=(NAMES, COLLEGES)), \
                patch("connect.ai_search.generate_reply", side_effect=ai_search.ModelTimeout("60 s")) as model:
            answer = ai_search.understand("gamers free saturday afternoon")
        self.assertEqual(model.call_count, 1)
        self.assertEqual(answer["source"], "keywords")
        self.assertEqual(answer["filters"], {"interests": ["Gaming"], "day": "SATURDAY", "time": "14-16"})
        self.assertEqual(answer["note"], "The language model took too long to answer.")


# --- Part 1: the page, the download command and the setup -----------------------------------

@override_settings(AI_LOCAL_ENABLED=True, AI_EMBED_ENABLED=True)
class AskPageTests(TestCase):

    url = reverse("connect:student-ask")

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data", stdout=StringIO())
        cls.member = User.objects.create_user("member")

    def setUp(self):
        cache.clear()
        self.client.force_login(self.member)

    def ask(self, reply, request):
        with embedder(), patch("connect.ai_search.generate_reply", return_value=reply):
            return self.client.get(self.url, {"q": request})

    def test_the_page_says_which_words_were_placed_by_meaning(self):
        response = self.ask('{"interests": ["Photography", "Painting"]}', "anyone who paints or takes photos")
        self.assertContains(response, "Interest: Art")
        self.assertContains(response, "Matched by meaning with <code>BAAI/bge-small-en-v1.5</code>")
        self.assertContains(response, '"Painting" &rarr; Art')

    def test_no_note_when_every_name_was_on_the_list(self):
        response = self.ask('{"interests": ["Gaming"]}', "gamers")
        self.assertNotContains(response, "Matched by meaning")

    def test_the_models_own_words_are_escaped(self):
        response = self.ask('{"interests": ["<b>x</b>"]}', "bold people")
        self.assertContains(response, "&lt;b&gt;x&lt;/b&gt;")
        self.assertNotContains(response, "<b>x</b>")

    def test_an_empty_request_explains_itself_and_never_runs_the_model(self):
        for request in ("", "   "):
            with self.subTest(request=request), patch("connect.ai_search.generate_reply") as model:
                response = self.client.get(self.url, {"q": request})
                self.assertContains(response, "Describe the students you are looking for, in a few words.")
                model.assert_not_called()

    def test_an_over_long_request_explains_itself_and_never_runs_the_model(self):
        with embedder() as meaning, patch("connect.ai_search.generate_reply") as model:
            response = self.client.get(self.url, {"q": "gamers " * 40})
        self.assertContains(response, "Keep it to 200 characters or fewer.")
        model.assert_not_called()
        meaning.assert_not_called()

    def test_no_match_says_how_to_widen_the_search(self):
        response = self.ask('{"interests": ["Reading"], "college": "Grainger College of Engineering", '
                            '"energy": "QUIET"}', "quiet engineering students who love reading")  # T03
        self.assertContains(response, "0 students found")
        self.assertContains(response, "No student matches all of these filters")
        self.assertContains(response, "Try asking for less")

    def test_the_download_command_fetches_both_models(self):
        out = StringIO()
        with embedder(), patch("connect.ai_search.generate_reply",
                               return_value='{"connection": "FRIEND", "day": "SUNDAY", "time": "12-14"}'):
            call_command("download_ai_model", stdout=out)
        self.assertIn("The local model is ready.", out.getvalue())
        self.assertIn("{'Painting': 'Art', 'Tech': 'Technology'}", out.getvalue())
        self.assertIn("The embedding model is ready.", out.getvalue())


class SetupTests(SimpleTestCase):

    def test_requirements_pin_sentence_transformers(self):
        self.assertIn("sentence-transformers==", (ROOT / "requirements.txt").read_text().lower())

    def test_the_env_example_names_the_embedding_settings(self):
        text = (ROOT / ".env.example").read_text()
        for line in ("AI_EMBED_ENABLED=1", "AI_EMBED_MODEL=BAAI/bge-small-en-v1.5"):
            self.assertIn(line, text.splitlines())
