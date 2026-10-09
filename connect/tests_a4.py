"""
Tests for the P1-A4 features, one class per assignment part.

    python manage.py test connect

These run on the real seed data (seed_demo_data), because the charts,
reports and exports are about the dataset the deployed site serves.
"""

import csv
import json
import re
from datetime import date, timedelta
from io import StringIO
from itertools import pairwise
from unittest.mock import patch

import requests
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase
from django.urls import reverse
from django.utils.html import strip_tags

from .icebreakers import TRIVIA_URL, common_ground
from .management.commands.seed_demo_data import HISTORY, STAFF_PASSWORD
from .models import (
    CampusLocation,
    ExperienceFeedback,
    Interest,
    InterestCategory,
    Match,
    MatchParticipant,
    MatchStatus,
    ProfileInterest,
    StudentProfile,
)
from .reports import FIELDS
from .vega_charts import load_spec


def seed():
    call_command("seed_demo_data", stdout=StringIO())


class SeededTestCase(TestCase):
    """Every test class below starts from the seeded dataset, signed in as an
    ordinary member: since P1-A5 every page but the landing page needs a
    login (tests_a5.py tests that)."""

    @classmethod
    def setUpTestData(cls):
        seed()
        cls.member = User.objects.create_user("member")  # no password: force_login needs none

    def setUp(self):
        self.client.force_login(self.member)


# --- Part 4: deployment prerequisites (the committed seed data) ---------------


class SeedDataTests(SeededTestCase):

    def test_seed_builds_the_documented_dataset(self):
        self.assertEqual(StudentProfile.objects.count(), 8)
        self.assertEqual(Match.objects.count(), 3 + len(HISTORY))
        self.assertEqual(MatchParticipant.objects.count(), 55)
        self.assertEqual(ExperienceFeedback.objects.count(), 33)
        self.assertEqual(Match.objects.filter(status=MatchStatus.CANCELLED).count(), 1)

    def test_original_three_matches_keep_the_first_ids(self):
        # Docs, screenshots and the CI smoke test link /matches/1/ to /3/.
        codes = list(Match.objects.order_by("pk").values_list("check_in_code", flat=True)[:3])
        self.assertEqual(codes, ["QC-4827", "QC-5193", "QC-3312"])

    def test_no_student_is_in_two_matches_in_one_week(self):
        clashes = (MatchParticipant.objects
                   .values("profile", "match__week_start")
                   .annotate(n=Count("id")).filter(n__gt=1))
        self.assertEqual(list(clashes), [])

    def test_reseeding_changes_nothing(self):
        def snapshot():
            return (
                list(StudentProfile.objects.order_by("net_id")
                     .values_list("net_id", "onboarding_completed_at")),
                list(Match.objects.order_by("check_in_code")
                     .values_list("check_in_code", "scheduled_for", "status")),
                list(MatchParticipant.objects.order_by("match__check_in_code", "profile__net_id")
                     .values_list("compatibility_score", "match_reason", "checked_in_at")),
                ExperienceFeedback.objects.count(),
            )
        before = snapshot()
        seed()
        self.assertEqual(snapshot(), before)

    def test_course_staff_accounts_can_log_in(self):
        for username in ["tester", "mohitg2"]:
            user = User.objects.get(username=username)
            self.assertTrue(user.is_staff and user.is_superuser, username)
            self.assertTrue(user.check_password(STAFF_PASSWORD), username)
        self.assertTrue(self.client.login(username="tester", password=STAFF_PASSWORD))

    def test_students_have_no_password(self):
        # Students sign in through SSO later; nobody can log in as one now.
        student_users = User.objects.filter(student_profile__isnull=False)
        self.assertEqual(student_users.count(), 8)
        self.assertFalse(any(u.has_usable_password() for u in student_users))

    def test_verify_constraints_passes_on_the_seed(self):
        call_command("verify_constraints", stdout=StringIO())  # raises on failure

    def test_match_lists_put_the_newest_cycle_first(self):
        # With the history seeded, id order is no longer date order, and
        # annotate() drops Meta.ordering, so each list must order by date.
        newest = [m.get_absolute_url()
                  for m in Match.objects.order_by("-week_start", "-scheduled_for", "-pk")]
        for name, count in [("match-list", len(newest)), ("home", 5)]:
            page = self.client.get(reverse("connect:" + name)).content.decode()
            links = list(dict.fromkeys(re.findall(r'href="(/matches/\d+/)"', page)))
            self.assertEqual(links, newest[:count], name)


# --- Part 1.1: chart-ready internal API ------------------------------------------


class SummaryApiTests(SeededTestCase):

    def test_summary_is_a_bare_list_of_category_count_rows(self):
        response = self.client.get(reverse("connect:api-summary"))
        self.assertEqual(response["Content-Type"], "application/json")
        rows = response.json()
        self.assertIsInstance(rows, list)
        self.assertEqual(set(rows[0]), {"category", "count", "type"})
        # Most picked first, ties by name; nobody picked an activity.
        self.assertEqual([(r["category"], r["count"]) for r in rows[:3]],
                         [("Food", 4), ("Movies", 4), ("Fitness", 3)])
        self.assertEqual(sum(r["count"] for r in rows), ProfileInterest.objects.count())
        self.assertNotIn("Meeting activity", {r["type"] for r in rows})

    def test_matches_per_week_is_contiguous_weekly_records(self):
        records = self.client.get(reverse("connect:api-summary-matches-per-week")).json()["records"]
        dates = [date.fromisoformat(r["date"]) for r in records]
        self.assertEqual(dates[0], date(2026, 7, 13))
        self.assertEqual(dates[-1], date(2026, 9, 7))
        self.assertTrue(all(b - a == timedelta(weeks=1) for a, b in pairwise(dates)))
        self.assertEqual([r["count"] for r in records], [1, 1, 2, 2, 2, 3, 3, 3, 2])
        self.assertEqual(sum(r["count"] for r in records), Match.objects.count())
        self.assertEqual(sum(r["participants"] for r in records), MatchParticipant.objects.count())

    def test_a_week_without_matches_shows_as_zero(self):
        Match.objects.filter(week_start=date(2026, 8, 10)).delete()
        records = self.client.get(reverse("connect:api-summary-matches-per-week")).json()["records"]
        self.assertIn({"date": "2026-08-10", "count": 0, "participants": 0}, records)

    def test_only_the_public_api_allows_any_origin(self):
        # Since P1-A5 /api/summary/ is the one public endpoint (see tests_a5.py).
        self.assertEqual(self.client.get(reverse("connect:api-summary"))["Access-Control-Allow-Origin"], "*")
        for name in ["api-summary-matches-per-week", "api-locations", "api-matches", "api-locations-text"]:
            self.assertNotIn("Access-Control-Allow-Origin", self.client.get(reverse("connect:" + name)), name)

    def test_summary_endpoints_are_get_only(self):
        for name in ["api-summary", "api-summary-matches-per-week"]:
            self.assertEqual(self.client.post(reverse("connect:" + name)).status_code, 405)

    def summary(self):
        return {r["category"]: r["count"] for r in self.client.get(reverse("connect:api-summary")).json()}

    def test_only_verified_students_count(self):
        StudentProfile.objects.filter(net_id="apatel22").update(is_sso_verified=False)
        self.assertEqual(self.summary()["Food"], 3)  # apatel22 is one of Food's four

    def test_interests_with_the_same_name_keep_their_own_bars(self):
        # Food is both a hobby and a meeting activity.
        ProfileInterest.objects.create(
            profile=StudentProfile.objects.get(net_id="jordan4"),
            interest=Interest.objects.get(name="Food", category=InterestCategory.ACTIVITY))
        rows = self.summary()
        self.assertEqual((rows["Food (Hobby / Interest)"], rows["Food (Meeting activity)"]), (4, 1))
        self.assertNotIn("Food", rows)


# --- Part 1.2: Vega-Lite charts ---------------------------------------------------


class VegaLiteTests(SeededTestCase):

    def setUp(self):
        super().setUp()
        cache.clear()  # the images are cached for a minute

    def test_specs_load_their_data_from_the_summary_api(self):
        # The assignment: data.url pointing at our API, never inline values.
        for name, api in [("chart1", "api-summary"), ("chart2", "api-summary-matches-per-week")]:
            spec = load_spec(name)
            self.assertEqual(spec["$schema"], "https://vega.github.io/schema/vega-lite/v6.json")
            self.assertEqual(spec["data"]["url"], reverse("connect:" + api), name)
            self.assertNotIn("values", spec["data"], name)
        self.assertEqual(load_spec("chart1")["layer"][0]["mark"]["type"], "bar")
        self.assertEqual(load_spec("chart2")["mark"]["type"], "line")

    def test_served_spec_has_an_absolute_data_url(self):
        response = self.client.get(reverse("connect:vega-spec", args=["chart2"]))
        self.assertEqual(response.json()["data"]["url"],
                         "http://testserver" + reverse("connect:api-summary-matches-per-week"))

    def test_image_endpoints_return_png_and_jpeg(self):
        for path, content_type, magic in [("/vega-lite/chart1.png", "image/png", b"\x89PNG"),
                                          ("/vega-lite/chart2.jpg", "image/jpeg", b"\xff\xd8\xff")]:
            response = self.client.get(path)
            self.assertEqual(response["Content-Type"], content_type, path)
            self.assertTrue(response.content.startswith(magic), path)

    def test_images_still_render_with_no_data(self):
        Match.objects.all().delete()
        ProfileInterest.objects.all().delete()
        for path in ["/vega-lite/chart1.png", "/vega-lite/chart2.jpg"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_unknown_chart_or_format_is_404(self):
        for path in ["/vega-lite/chart9.png", "/vega-lite/chart1.gif", "/vega-lite/chart9.vl.json"]:
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_insights_page_embeds_both_charts_with_fallbacks(self):
        response = self.client.get(reverse("connect:insights"))
        for name in ["chart1", "chart2"]:
            self.assertContains(response, f'data-vega-spec="{reverse("connect:vega-spec", args=[name])}"')
        self.assertContains(response, "vendor/vega/vega-embed")
        self.assertContains(response, "<noscript>", count=2)
        self.assertContains(response, 'alt="Bar chart of 22 interests by how many verified students')
        self.assertContains(response, 'alt="Line chart of matches scheduled each week from 2026-07-13 to 2026-09-07')


# --- Part 2: external API (Open Trivia DB icebreakers) --------------------------------


def trivia_reply(status=200, body=None):
    """A requests.Response as Open Trivia DB would send it."""
    response = requests.Response()
    response.status_code = status
    response.url = TRIVIA_URL
    response._content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return response


QUESTION = {"type": "multiple", "difficulty": "easy", "category": "Sports",
            "question": "Which country produced Cafu and Pel&eacute;?",
            "correct_answer": "Brazil", "incorrect_answers": ["Spain", "Argentina", "Portugal"]}


def flat(response):
    """The page's text without tags, whitespace runs collapsed to one space."""
    return " ".join(strip_tags(response.content.decode()).split())


class IcebreakerTests(SeededTestCase):
    """requests.get is replaced in every test: none of them uses the network."""

    def setUp(self):
        super().setUp()
        patcher = patch("connect.icebreakers.requests.get",
                        return_value=trivia_reply(body={"response_code": 0, "results": [QUESTION]}))
        self.get = patcher.start()
        self.addCleanup(patcher.stop)
        cache.clear()  # questions are reused for 5 seconds
        self.squad = Match.objects.get(check_in_code="QC-5193")

    def api(self, **params):
        return self.client.get(reverse("connect:api-icebreakers"), params)

    def test_topic_is_the_category_most_members_share(self):
        found = common_ground(self.squad)
        self.assertEqual(found["members"], 5)
        self.assertEqual(found["topic"], {"category_id": 21, "category": "Sports", "members": 3,
                                          "because": ["Basketball", "Fitness"]})
        self.assertEqual(found["interests"][0],
                         {"interest": "Fitness", "members": 3, "trivia_category": "Sports"})

    def test_members_who_declined_are_left_out(self):
        self.assertEqual(common_ground(Match.objects.get(check_in_code="QC-1306"))["members"], 2)

    def test_tied_topics_are_all_candidates(self):
        # Both members of QC-1303 picked Art, Movies and Reading: three
        # categories tie, and the random pick is made from all three.
        with patch("connect.icebreakers.random.choice", side_effect=lambda tied: tied[-1]) as choice:
            found = common_ground(Match.objects.get(check_in_code="QC-1303"))
        self.assertEqual([name for _, name in choice.call_args.args[0]], ["Books", "Film", "Art"])
        self.assertEqual(found["topic"]["category"], "Art")

    def test_questions_are_reused_for_five_seconds(self):
        # Open Trivia DB turns away a second request within 5 seconds.
        for _ in range(2):
            self.assertEqual(self.api(match=self.squad.pk).status_code, 200)
        self.get.assert_called_once()

    def test_nothing_shared_means_general_knowledge(self):
        topic = common_ground(Match.objects.get(check_in_code="QC-4827"))["topic"]
        self.assertEqual((topic["category_id"], topic["members"], topic["because"]), (9, 0, []))

    def test_api_combines_our_counts_with_the_questions(self):
        response = self.api(match=self.squad.pk)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["topic"]["category"], "Sports")
        self.assertEqual(data["questions"], [{"question": "Which country produced Cafu and Pelé?",
                                              "choices": ["Argentina", "Brazil", "Portugal", "Spain"],
                                              "answer": "Brazil"}])
        self.assertEqual(data["source"]["license"], "CC BY-SA 4.0")
        self.get.assert_called_once_with(TRIVIA_URL, params={
            "amount": 5, "category": 21, "difficulty": "easy", "type": "multiple"}, timeout=5)

    def test_api_names_nobody(self):
        body = self.api(match=self.squad.pk).content.decode()
        for p in self.squad.participants.select_related("profile"):
            self.assertNotIn(p.profile.net_id, body)
            self.assertNotIn(p.profile.full_name, body)
        self.assertNotIn(self.squad.check_in_code, body)

    def test_missing_bad_or_unknown_match(self):
        self.assertIn("match", self.api().json()["fields"])
        self.assertEqual(self.api(match="two").status_code, 400)
        self.assertEqual(self.api(match=999).status_code, 404)
        self.get.assert_not_called()

    def test_upstream_failures_become_gateway_errors(self):
        for outcome, status in [
            (requests.Timeout(), 504),
            (requests.ConnectionError(), 502),
            (trivia_reply(429, {"response_code": 5, "results": []}), 503),
            (trivia_reply(200, {"response_code": 5, "results": []}), 503),
            (trivia_reply(500, b"<h1>Server Error</h1>"), 502),
            (trivia_reply(200, b"<h1>Not JSON</h1>"), 502),
            (trivia_reply(200, {"response_code": 1, "results": []}), 502),
            (trivia_reply(200, {"response_code": 0, "results": [{"question": "?"}]}), 502),
        ]:
            with self.subTest(outcome=outcome):
                self.get.side_effect = outcome if isinstance(outcome, Exception) else None
                self.get.return_value = outcome
                with self.assertLogs("connect.icebreakers", "WARNING"):
                    response = self.api(match=self.squad.pk)
                self.assertEqual(response.status_code, status)
                self.assertTrue(response.json()["error"])
                self.assertEqual(response.get("Retry-After"), "5" if status == 503 else None)

    def test_page_shows_the_questions_and_why(self):
        response = self.client.get(reverse("connect:match-icebreakers", args=[self.squad.pk]))
        text = flat(response)
        self.assertIn("Sports trivia", text)
        self.assertIn("Picked because 3 of the 5 members chose Basketball or Fitness.", text)
        self.assertIn("1. Which country produced Cafu and Pelé?", text)
        self.assertIn("Open Trivia Database", text)

    def test_page_still_shows_the_interests_when_trivia_fails(self):
        self.get.side_effect = requests.Timeout()
        with self.assertLogs("connect.icebreakers", "WARNING"):
            response = self.client.get(reverse("connect:match-icebreakers", args=[self.squad.pk]))
        self.assertContains(response, "did not answer within 5 seconds")
        self.assertContains(response, "<td>Fitness</td>")

    def test_match_page_links_here(self):
        response = self.client.get(self.squad.get_absolute_url())
        self.assertContains(response, reverse("connect:match-icebreakers", args=[self.squad.pk]))
        self.assertEqual(self.client.get(reverse("connect:match-icebreakers", args=[999])).status_code, 404)


# --- Part 3: CSV and JSON exports, and the reports page ----------------------------------


STAMPED = r'^attachment; filename="students_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.{}"$'


def empty_the_database():
    # Matches first: they protect their venues and their participants' profiles.
    Match.objects.all().delete()
    StudentProfile.objects.all().delete()
    CampusLocation.objects.all().delete()


class ExportTests(SeededTestCase):

    def csv_rows(self):
        response = self.client.get(reverse("connect:export-students-csv"))
        return list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

    def test_csv_is_a_dated_attachment_with_a_header_row(self):
        response = self.client.get(reverse("connect:export-students-csv"))
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))  # BOM, for Excel
        self.assertRegex(response["Content-Disposition"], STAMPED.replace("{}", "csv"))
        rows = self.csv_rows()
        self.assertEqual(rows[0], FIELDS)
        names = list(StudentProfile.objects.order_by("full_name", "net_id")
                     .values_list("net_id", flat=True))
        self.assertEqual([row[0] for row in rows[1:]], names)

    def test_csv_row_matches_the_database(self):
        row = dict(zip(FIELDS, next(r for r in self.csv_rows() if r[0] == "apatel22"), strict=True))
        profile = StudentProfile.objects.get(net_id="apatel22")
        self.assertEqual(row["full_name"], profile.full_name)
        self.assertEqual(row["interests"], "; ".join(i.name for i in profile.interests.all()))
        self.assertEqual(row["matches"], str(profile.match_participations.count()))

    def test_json_has_metadata_and_the_same_rows(self):
        response = self.client.get(reverse("connect:export-students-json"))
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertRegex(response["Content-Disposition"], STAMPED.replace("{}", "json"))
        self.assertTrue(response.content.startswith(b'{\n  "generated_at": '))  # indent=2
        data = response.json()
        # One clock for both: the file name is generated_at to the minute.
        stamp = data["generated_at"][:16].replace("T", "_").replace(":", "-")
        self.assertIn(f"students_{stamp}.json", response["Content-Disposition"])
        self.assertEqual(data["record_count"], StudentProfile.objects.count())
        self.assertEqual([s["net_id"] for s in data["students"]],
                         [row[0] for row in self.csv_rows()[1:]])
        self.assertEqual(list(data["students"][0]), FIELDS)

    def test_exports_leave_out_email(self):
        for name in ["export-students-csv", "export-students-json"]:
            body = self.client.get(reverse("connect:" + name)).content.decode()
            for email in StudentProfile.objects.values_list("illinois_email", flat=True):
                self.assertNotIn(email, body, name)

    def test_csv_cells_cannot_run_as_formulas(self):
        StudentProfile.objects.filter(net_id="apatel22").update(department='=HYPERLINK("x")')
        row = next(r for r in self.csv_rows() if r[0] == "apatel22")
        self.assertEqual(row[FIELDS.index("department")], '\'=HYPERLINK("x")')

    def test_empty_database_still_has_the_header_row(self):
        empty_the_database()
        self.assertEqual(self.csv_rows(), [FIELDS])
        data = self.client.get(reverse("connect:export-students-json")).json()
        self.assertEqual((data["record_count"], data["students"]), (0, []))


class ReportsTests(SeededTestCase):

    def test_totals_line_and_grouped_summaries(self):
        response = self.client.get(reverse("connect:reports"))
        self.assertIn("Totals: 8 students, 19 matches (16 completed, 2 upcoming, 1 cancelled) "
                      "and 55 participants across all matches.", flat(response))
        self.assertContains(response, '<th scope="row">All colleges</th>')
        self.assertContains(response, '<th scope="row">All venues</th>')
        venues = response.context["venues"]
        self.assertEqual(sum(v.total for v in venues), Match.objects.count())
        self.assertEqual(sum(v.completed for v in venues),
                         Match.objects.filter(status=MatchStatus.COMPLETED).count())

    def test_download_buttons_and_links(self):
        response = self.client.get(reverse("connect:reports"))
        for name, label in [("export-students-csv", "Download CSV"),
                            ("export-students-json", "Download JSON")]:
            self.assertContains(response, f'href="{reverse("connect:" + name)}" download>{label}</a>')
            self.assertContains(self.client.get(reverse("connect:student-list")),
                                f'href="{reverse("connect:" + name)}" download>')
        self.assertContains(response, 'aria-current="page">Reports</a>')

    def test_empty_tables_say_so(self):
        empty_the_database()
        response = self.client.get(reverse("connect:reports"))
        self.assertContains(response, "No students have joined yet.")
        self.assertContains(response, "No venues have been added yet.")
        self.assertNotContains(response, "<tfoot>")
