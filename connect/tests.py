"""
Tests for the P1-A3 features, one class per assignment section.

    python manage.py test connect

Every class shares one small dataset (QuadConnectData) so each assertion can
name exact rows. EmptyDatabaseTests checks the empty states separately.
"""

import importlib
import json
import os
from datetime import date, datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import Client, TestCase
from django.urls import reverse

from .charts import selections_by_category_data, students_by_college_data
from .models import (
    CampusLocation,
    ConnectionType,
    Interest,
    InterestCategory,
    Match,
    MatchParticipant,
    MatchStatus,
    ProfileInterest,
    StudentProfile,
)
from .views import _search_students

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CHICAGO = ZoneInfo("America/Chicago")  # settings.TIME_ZONE


class QuadConnectData(TestCase):
    """Three students, three approved-or-not venues, two matches."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user("staff", password="pw", is_staff=True)

        gaming = Interest.objects.create(name="Gaming", category=InterestCategory.HOBBY)
        # "Board games" also contains "gam", so a search for "gam" reaches Ada
        # through two interest rows: the case .distinct() exists for.
        board = Interest.objects.create(name="Board games", category=InterestCategory.ACTIVITY)
        esports = Interest.objects.create(name="UIUC Esports", category=InterestCategory.RSO)
        reading = Interest.objects.create(name="Reading", category=InterestCategory.HOBBY)

        def student(net_id, name, college, connection, interests):
            profile = StudentProfile.objects.create(
                user=User.objects.create_user(net_id), net_id=net_id,
                illinois_email=f"{net_id}@illinois.edu", full_name=name,
                college=college, preferred_connection=connection)
            for interest in interests:
                ProfileInterest.objects.create(profile=profile, interest=interest)
            return profile

        cls.ada = student("ada1", "Ada Lovelace", "Grainger College of Engineering",
                          ConnectionType.FRIEND, [gaming, board])
        cls.ben = student("ben2", "Ben Okafor", "Grainger College of Engineering",
                          ConnectionType.SQUAD, [esports])
        cls.cy = student("cy3", "Cy Chen", "College of Media",
                         ConnectionType.SQUAD, [reading])

        cls.union = CampusLocation.objects.create(
            name="Illini Union", street_address="1401 W Green St, Urbana",
            is_indoor=True, capacity=12)
        cls.quad = CampusLocation.objects.create(
            name="Main Quad", street_address="601 S Wright St, Champaign",
            is_indoor=False, capacity=20)
        cls.pending = CampusLocation.objects.create(
            name="Secret Spot", street_address="1 Hidden Rd", is_approved=False)

        cls.squad = Match.objects.create(
            connection_type=ConnectionType.SQUAD, week_start=date(2026, 9, 7),
            scheduled_for=datetime(2026, 9, 12, 14, 0, tzinfo=CHICAGO),
            location=cls.union, suggested_activity=board,
            status=MatchStatus.CONFIRMED, check_in_code="QC-1111")
        MatchParticipant.objects.create(match=cls.squad, profile=cls.ben, compatibility_score=80)
        MatchParticipant.objects.create(match=cls.squad, profile=cls.cy, compatibility_score=70)
        cls.friend = Match.objects.create(
            connection_type=ConnectionType.FRIEND, week_start=date(2026, 9, 14),
            scheduled_for=datetime(2026, 9, 19, 10, 0, tzinfo=CHICAGO),
            location=cls.quad, status=MatchStatus.PROPOSED, check_in_code="QC-2222")
        MatchParticipant.objects.create(match=cls.friend, profile=cls.ada)

    def assertSays(self, response, text):
        """assertContains, but blind to the line breaks templates add."""
        self.assertIn(text, " ".join(response.content.decode().split()))


# --- Section 1: URL linking and navigation ------------------------------------


class UrlLinkingTests(QuadConnectData):

    def test_home_renders_and_nav_reverses_every_section(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for name in ["home", "student-list", "student-search", "match-list",
                     "location-list", "feedback-summary", "insights", "api-docs"]:
            self.assertContains(response, f'href="{reverse("connect:" + name)}"')

    def test_get_absolute_url_builds_pk_paths(self):
        self.assertEqual(self.ada.get_absolute_url(), f"/students/{self.ada.pk}/")
        self.assertEqual(self.squad.get_absolute_url(), f"/matches/{self.squad.pk}/")
        self.assertEqual(self.union.get_absolute_url(), f"/locations/{self.union.pk}/")

    def test_every_list_row_links_to_its_detail_page(self):
        pages = {
            "/students/": [self.ada, self.ben, self.cy],
            "/matches/": [self.squad, self.friend],
            "/locations/": [self.union, self.quad],
            "/": [self.squad, self.friend],
        }
        for url, objects in pages.items():
            response = self.client.get(url)
            for obj in objects:
                self.assertContains(response, f'href="{obj.get_absolute_url()}"')
        # An unapproved venue is never linked from the public list.
        self.assertNotContains(self.client.get("/locations/"), self.pending.get_absolute_url())

    def test_detail_pages_link_onward(self):
        response = self.client.get(self.squad.get_absolute_url())
        self.assertContains(response, f'href="{self.ben.get_absolute_url()}"')
        self.assertContains(response, f'href="{self.union.get_absolute_url()}"')
        response = self.client.get(self.union.get_absolute_url())
        self.assertContains(response, f'href="{self.squad.get_absolute_url()}"')
        response = self.client.get(self.ben.get_absolute_url())
        self.assertContains(response, f'href="{self.squad.get_absolute_url()}"')

    def test_unknown_pk_is_404(self):
        for url in ["/students/999999/", "/matches/999999/", "/locations/999999/"]:
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_unapproved_venue_is_404_except_for_staff(self):
        url = self.pending.get_absolute_url()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.staff)
        self.assertSays(self.client.get(url), "Only staff can see this page")

    def test_nav_marks_list_page_and_detail_page_differently(self):
        list_page = self.client.get("/matches/").content.decode()
        detail_page = self.client.get(self.squad.get_absolute_url()).content.decode()
        self.assertRegex(list_page, r'href="/matches/"\s+class="active" aria-current="page"')
        self.assertRegex(detail_page, r'href="/matches/"\s+class="active" aria-current="true"')


# --- Section 2: ORM queries, GET and POST search ------------------------------


class SearchTests(QuadConnectData):
    url = reverse("connect:student-search")

    def names(self, response):
        return [s.full_name for s in response.context["students"]]

    def test_no_filters_lists_everyone(self):
        response = self.client.get(self.url)
        self.assertEqual(self.names(response), ["Ada Lovelace", "Ben Okafor", "Cy Chen"])
        self.assertContains(response, "All 3 students")

    def test_name_icontains(self):
        self.assertEqual(self.names(self.client.get(self.url, {"q": "LOVEL"})), ["Ada Lovelace"])

    def test_interest_span_is_distinct(self):
        # Ada matches "gam" through Gaming and Board games; she appears once,
        # both from the search function itself and on the page.
        self.assertEqual(list(_search_students({"q": "gam"})), [self.ada])
        response = self.client.get(self.url, {"q": "gam"})
        self.assertEqual(self.names(response), ["Ada Lovelace"])
        self.assertEqual(response.context["summary"]["total"], 1)

    def test_exact_filters_combine(self):
        response = self.client.get(self.url, {
            "college": "Grainger College of Engineering",
            "connection": ConnectionType.SQUAD})
        self.assertEqual(self.names(response), ["Ben Okafor"])

    def test_venue_filter_spans_three_relations(self):
        response = self.client.get(self.url, {"venue": "Illini Union"})
        self.assertEqual(self.names(response), ["Ben Okafor", "Cy Chen"])

    def test_invalid_choice_is_reported_on_the_field(self):
        response = self.client.get(self.url, {"college": "Nope"})
        self.assertEqual(self.names(response), [])
        self.assertContains(response, "Pick a college from the list.")
        self.assertContains(response, 'aria-invalid="true"')

    def test_no_match_shows_empty_state(self):
        response = self.client.get(self.url, {"q": "zzz"})
        self.assertContains(response, "No students match these filters")
        self.assertContains(response, "No students to group.")

    def test_total_and_grouped_aggregates(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["summary"]["total"], 3)
        self.assertEqual(
            [(r["college"], r["students"]) for r in response.context["by_college"]],
            [("Grainger College of Engineering", 2), ("College of Media", 1)])
        top = {i.name: i.students for i in response.context["top_interests"]}
        self.assertEqual(top, {"Board games": 1, "Gaming": 1, "Reading": 1, "UIUC Esports": 1})

    def test_aggregates_follow_the_filters(self):
        response = self.client.get(self.url, {"venue": "Illini Union"})
        self.assertEqual(
            [(r["college"], r["students"]) for r in response.context["by_college"]],
            [("College of Media", 1), ("Grainger College of Engineering", 1)])

    def test_post_lookup_is_case_insensitive_and_keeps_netid_out_of_url(self):
        response = self.client.post(self.url, {"net_id": "  ADA1 "})
        self.assertEqual(response.context["found"], self.ada)
        self.assertEqual(response.request["QUERY_STRING"], "")
        self.assertContains(response, f'href="{self.ada.get_absolute_url()}"')

    def test_post_lookup_miss_is_a_field_error(self):
        response = self.client.post(self.url, {"net_id": "nobody9"})
        self.assertIsNone(response.context["found"])
        self.assertContains(response, 'No verified student has the NetID')
        self.assertContains(response, 'aria-invalid="true"')

    def test_post_lookup_rejects_malformed_netid(self):
        response = self.client.post(self.url, {"net_id": "ada1@illinois.edu"})
        self.assertContains(response, "A NetID is letters followed by optional digits")

    def test_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url, {"net_id": "ada1"}).status_code, 403)
        page = client.get(self.url).content.decode()
        token = page.split('name="csrfmiddlewaretoken" value="')[1].split('"')[0]
        response = client.post(self.url, {"net_id": "ada1", "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 200)


# --- Section 3: static files -------------------------------------------------


class StaticFilesTests(QuadConnectData):

    def test_base_template_links_static_assets(self):
        response = self.client.get("/")
        self.assertContains(response, '<link rel="stylesheet" href="/static/css/quadconnect.css">')
        self.assertContains(response, 'src="/static/img/logo.svg"')

    def test_static_files_are_found(self):
        for path in ["css/quadconnect.css", "img/logo.svg",
                     "fonts/inter-latin-wght-normal.woff2"]:
            self.assertIsNotNone(finders.find(path), path)

    def test_production_hashes_static_filenames(self):
        with mock.patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": "example.com"}):
            prod = importlib.reload(importlib.import_module("quadconnect.settings.production"))
        self.assertEqual(prod.STORAGES["staticfiles"]["BACKEND"],
                         "whitenoise.storage.CompressedManifestStaticFilesStorage")
        middleware = prod.MIDDLEWARE
        self.assertEqual(middleware.index("whitenoise.middleware.WhiteNoiseMiddleware"),
                         middleware.index("django.middleware.security.SecurityMiddleware") + 1)


# --- Section 4: charts ---------------------------------------------------------


class ChartTests(QuadConnectData):

    def test_chart_data_comes_from_orm_aggregates(self):
        self.assertEqual(students_by_college_data(), [
            ("Grainger College of Engineering", 1, 1), ("College of Media", 0, 1)])
        self.assertEqual([(key, n) for key, _, n in selections_by_category_data()], [
            (InterestCategory.HOBBY, 2), (InterestCategory.ACTIVITY, 1), (InterestCategory.RSO, 1)])

    def test_chart_endpoints_return_png(self):
        for name in ["chart-students-by-college", "chart-interest-categories"]:
            response = self.client.get(reverse("connect:" + name))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertTrue(response.content.startswith(PNG_MAGIC))

    def test_insights_page_embeds_charts_with_alt_text_and_captions(self):
        response = self.client.get(reverse("connect:insights"))
        self.assertContains(response, f'src="{reverse("connect:chart-students-by-college")}"')
        self.assertContains(response, 'alt="Stacked bar chart of 3 verified students across 2 colleges')
        self.assertContains(response, 'alt="Pie chart of 4 interest selections by category.')
        self.assertContains(response, "<figcaption>", count=2)


# --- Section 5: forms on a class-based view -------------------------------------


class LocationFormTests(QuadConnectData):
    url = reverse("connect:location-list")

    def valid(self, **overrides):
        data = {"name": "Siebel Center for Design", "street_address": "1208 S Fourth St",
                "is_indoor": "on", "capacity": "10"}
        return {**data, **overrides}

    def titles(self, response):
        return [item["title"] for item in response.context["items"]]

    def test_get_filters_use_query_parameters(self):
        self.assertEqual(self.titles(self.client.get(self.url, {"seats": "15"})), ["Main Quad"])
        self.assertEqual(self.titles(self.client.get(self.url, {"setting": "indoor"})), ["Illini Union"])

    def test_valid_post_saves_unapproved_venue_and_redirects(self):
        # follow=True: the flash message is shown once, on the page the
        # redirect lands on.
        response = self.client.post(self.url, self.valid(is_approved="on"), follow=True)
        self.assertEqual(response.redirect_chain, [(self.url + "#main", 302)])
        venue = CampusLocation.objects.get(name="Siebel Center for Design")
        self.assertFalse(venue.is_approved)  # the smuggled is_approved=on is ignored
        self.assertContains(response, "was sent for review")
        self.assertNotIn("Siebel Center for Design", [i["title"] for i in response.context["items"]])

    def test_invalid_post_rerenders_with_field_errors(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].errors), {"name", "street_address", "capacity"})
        self.assertSays(response, "Fix the 3 fields marked below")
        self.assertContains(response, 'aria-invalid="true"', count=3)
        self.assertEqual(CampusLocation.objects.count(), 3)

    def test_duplicate_name_is_rejected_ignoring_case_and_spaces(self):
        response = self.client.post(self.url, self.valid(name="  illini   UNION "))
        self.assertContains(response, "already listed or waiting for review")

    def test_capacity_outside_model_range_is_rejected(self):
        response = self.client.post(self.url, self.valid(capacity="1"))
        self.assertContains(response, "A meetup needs at least 2 seats")
        # The input advertises the same range the model enforces.
        self.assertRegex(response.content.decode(), r'name="capacity"[^>]* min="2" max="50"')

    def test_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url, self.valid()).status_code, 403)
        self.assertFalse(CampusLocation.objects.filter(name="Siebel Center for Design").exists())

    def test_pending_names_are_shown_to_staff_only(self):
        public = self.client.get(self.url)
        self.assertContains(public, "1 suggestion")
        self.assertNotContains(public, "Secret Spot")
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(self.url), "Secret Spot")


# --- Section 6: JSON API ---------------------------------------------------------


class ApiTests(QuadConnectData):

    def get_json(self, name, **params):
        response = self.client.get(reverse("connect:" + name), params)
        self.assertEqual(response["Content-Type"], "application/json")
        return response.status_code, json.loads(response.content)

    def test_locations_api_lists_approved_venues(self):
        status, data = self.get_json("api-locations")
        self.assertEqual(status, 200)
        self.assertEqual(data["count"], 2)
        self.assertEqual([v["name"] for v in data["results"]], ["Illini Union", "Main Quad"])
        self.assertEqual(data["results"][0]["url"],
                         "http://testserver" + self.union.get_absolute_url())

    def test_locations_api_filters(self):
        _, data = self.get_json("api-locations", setting="outdoor")
        self.assertEqual([v["name"] for v in data["results"]], ["Main Quad"])
        _, data = self.get_json("api-locations", min_seats="15")
        self.assertEqual([v["name"] for v in data["results"]], ["Main Quad"])
        self.assertEqual(data["filters"], {"min_seats": 15})

    def test_bad_parameter_is_a_400_naming_the_field(self):
        status, data = self.get_json("api-locations", min_seats="many")
        self.assertEqual(status, 400)
        self.assertEqual(list(data["fields"]), ["min_seats"])
        status, data = self.get_json("api-locations", min_seats="-3")
        self.assertEqual((status, data["fields"]["min_seats"]),
                         (400, ["Use a number of seats of 1 or more."]))
        status, data = self.get_json("api-matches", week="next-week", type="duo")
        self.assertEqual(status, 400)
        self.assertEqual(set(data["fields"]), {"week", "type"})

    def test_matches_api_filters(self):
        _, data = self.get_json("api-matches", type="SQUAD")
        self.assertEqual([m["id"] for m in data["results"]], [self.squad.pk])
        _, data = self.get_json("api-matches", week="2026-09-14")
        self.assertEqual([m["id"] for m in data["results"]], [self.friend.pk])
        _, data = self.get_json("api-matches", status="CONFIRMED")
        self.assertEqual(data["results"][0]["participant_count"], 2)
        self.assertEqual(data["results"][0]["scheduled_for"], "2026-09-12T14:00:00-05:00")

    def test_api_never_exposes_private_fields(self):
        body = (self.client.get(reverse("connect:api-matches")).content
                + self.client.get(reverse("connect:api-locations")).content).decode()
        for secret in ["QC-1111", "ben2", "Ben Okafor", "illinois.edu", "Secret Spot"]:
            self.assertNotIn(secret, body)

    def test_text_endpoint_is_plain_httpresponse(self):
        response = self.client.get(reverse("connect:api-locations-text"))
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("Illini Union | 1401 W Green St, Urbana | indoor | seats 12",
                      response.content.decode())

    def test_api_is_read_only(self):
        for name in ["api-locations", "api-matches", "api-locations-text"]:
            self.assertEqual(self.client.post(reverse("connect:" + name)).status_code, 405)

    def test_docs_page_shows_live_content_types(self):
        response = self.client.get(reverse("connect:api-docs"))
        self.assertContains(response, "<code>application/json</code>")
        self.assertContains(response, "<code>text/plain; charset=utf-8</code>")


# --- Empty database ------------------------------------------------------------


class EmptyDatabaseTests(TestCase):

    def test_pages_show_empty_states(self):
        self.assertContains(self.client.get("/search/"), "No students match these filters")
        self.assertContains(self.client.get("/insights/"), "No students yet")
        self.assertContains(self.client.get("/locations/"), "No approved campus locations")
        self.assertEqual(self.client.get("/api/locations/").json()["count"], 0)

    def test_chart_endpoints_still_return_png(self):
        for name in ["chart-students-by-college", "chart-interest-categories"]:
            response = self.client.get(reverse("connect:" + name))
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertTrue(response.content.startswith(PNG_MAGIC))
