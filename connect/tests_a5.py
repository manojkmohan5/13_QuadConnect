"""
Tests for P1-A5: logins, protected pages and APIs, and the public API.

    python manage.py test connect

Google itself is never called. The Google tests configure a dummy client,
then check that the button appears and that it sends the browser to Google
with that client and our callback address.
"""

from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import get_resolver, reverse
from django.utils.html import escape

PUBLIC_ROUTES = {"home", "api-summary"}
# A value for each URL parameter, so every route can be requested.
SAMPLE_KWARGS = {"pk": 1, "chart": "chart1", "fmt": "png"}

GOOGLE = {"google": {"SCOPE": ["profile", "email"], "OAUTH_PKCE_ENABLED": True,
                     "APPS": [{"client_id": "test-client.apps.googleusercontent.com",
                               "secret": "test-secret", "key": ""}]}}
NO_GOOGLE = {"google": {"SCOPE": ["profile", "email"]}}


def connect_routes():
    """(name, path) for every route of the connect app, from the URLconf
    itself, so a route added later is covered without editing this file."""
    app = next(p for p in get_resolver().url_patterns if getattr(p, "namespace", None) == "connect")
    for route in app.url_patterns:
        kwargs = {name: SAMPLE_KWARGS[name] for name in route.pattern.converters}
        yield route.name, reverse("connect:" + route.name, kwargs=kwargs)


class AuthTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data", stdout=StringIO())
        cls.member = User.objects.create_user("member")


# --- Part 1.4: everything private except the landing page and the public API --


class AccessTests(AuthTestCase):

    def test_every_route_but_two_needs_a_login(self):
        login = reverse("account_login")
        for name, path in connect_routes():
            if name in PUBLIC_ROUTES:
                continue
            with self.subTest(path=path):
                response = self.client.get(path)
                if path.startswith("/api/") and name != "api-docs":
                    self.assertEqual(response.status_code, 401)
                    self.assertIn("error", response.json())
                    self.assertNotIn("Access-Control-Allow-Origin", response)
                else:
                    self.assertRedirects(response, f"{login}?next={path}",
                                         fetch_redirect_response=False)

    def test_a_signed_in_member_can_open_every_route(self):
        self.client.force_login(self.member)
        with patch("connect.icebreakers.requests.get", side_effect=requests.ConnectionError):
            for _name, path in connect_routes():
                with self.subTest(path=path):
                    self.assertNotIn(self.client.get(path).status_code, (302, 401))

    def test_the_public_api_needs_no_login(self):
        response = self.client.get(reverse("connect:api-summary"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(response.json()[0], {"category": "Food", "count": 4, "type": "Hobby / Interest"})

    def test_the_api_docs_label_access_and_show_the_real_401(self):
        body = self.client.get(reverse("connect:api-matches")).content.decode()
        self.client.force_login(self.member)
        response = self.client.get(reverse("connect:api-docs"))
        self.assertContains(response, escape(body))
        self.assertContains(response, '<span class="badge badge-ok">Public</span>', count=1)
        self.assertContains(response, '<span class="badge">Login required</span>', count=5)

    def test_the_landing_page_is_public_and_shows_no_student_data(self):
        response = self.client.get(reverse("connect:home"))
        self.assertContains(response, "Create an account")
        self.assertNotContains(response, "Recent matches")
        self.assertNotContains(response, "QC-")  # no check-in codes

    def test_admin_still_works_for_staff(self):
        self.assertEqual(self.client.get(reverse("admin:login")).status_code, 200)
        self.client.force_login(User.objects.get(username="tester"))
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)


# --- Part 1.5: navigation --------------------------------------------------------


class NavigationTests(AuthTestCase):

    def test_protected_links_are_hidden_before_login(self):
        response = self.client.get(reverse("connect:home"))
        self.assertContains(response, f'href="{reverse("account_login")}"')
        self.assertContains(response, f'href="{reverse("account_signup")}"')
        for name in ["student-list", "match-list", "insights", "reports", "api-docs"]:
            self.assertNotContains(response, f'href="{reverse("connect:" + name)}"')

    def test_protected_links_and_log_out_appear_after_login(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("connect:home"))
        for name in ["student-list", "match-list", "insights", "reports", "api-docs"]:
            self.assertContains(response, f'href="{reverse("connect:" + name)}"')
        self.assertContains(response, "Signed in as <strong>member</strong>")
        self.assertContains(response, f'<form method="post" action="{reverse("account_logout")}">')
        self.assertNotContains(response, f'href="{reverse("account_signup")}"')


# --- Part 1.1-1.2: username/password sign-up, login and logout --------------------


class AccountTests(AuthTestCase):
    PASSWORD = "quad-Connect-2026!"  # noqa: S105 - a test password

    def test_sign_up_creates_the_account_and_logs_in(self):
        response = self.client.post(reverse("account_signup"), {
            "username": "newstudent", "email": "newstudent@illinois.edu",
            "password1": self.PASSWORD, "password2": self.PASSWORD})
        self.assertRedirects(response, reverse("connect:home"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username="newstudent").exists())
        self.assertContains(self.client.get(reverse("connect:home")), "Signed in as <strong>newstudent</strong>")

    def test_sign_up_errors_name_the_field(self):
        response = self.client.post(reverse("account_signup"), {
            "username": "newstudent", "email": "not-an-email",
            "password1": self.PASSWORD, "password2": "something else"})
        self.assertContains(response, "The account was not created.")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertFalse(User.objects.filter(username="newstudent").exists())

    def test_log_in_with_username_or_email_then_return_to_next(self):
        User.objects.create_user("ada", "ada@illinois.edu", self.PASSWORD)
        for login in ["ada", "ada@illinois.edu"]:
            with self.subTest(login=login):
                response = self.client.post(reverse("account_login") + "?next=/reports/",
                                            {"login": login, "password": self.PASSWORD})
                self.assertRedirects(response, "/reports/", fetch_redirect_response=False)
                self.client.post(reverse("account_logout"))

    def test_a_wrong_password_is_reported(self):
        response = self.client.post(reverse("account_login"), {"login": "tester", "password": "wrong"})
        self.assertContains(response, 'role="alert"')
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_log_out_takes_a_post(self):
        self.client.force_login(self.member)
        self.assertContains(self.client.get(reverse("account_logout")), "Do you want to log out")
        self.assertIn("_auth_user_id", self.client.session)  # a GET changes nothing
        response = self.client.post(reverse("account_logout"))
        self.assertRedirects(response, reverse("connect:home"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_page_offers_no_password_reset(self):
        # No mail server: a reset email could never arrive.
        self.assertNotContains(self.client.get(reverse("account_login")), reverse("account_reset_password"))


# --- Part 2: Google ----------------------------------------------------------------


class GoogleTests(AuthTestCase):

    @override_settings(SOCIALACCOUNT_PROVIDERS=NO_GOOGLE)
    def test_no_button_without_a_google_client(self):
        self.assertNotContains(self.client.get(reverse("account_login")), "Continue with Google")

    @override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE)
    def test_login_and_sign_up_pages_offer_google(self):
        for name in ["account_login", "account_signup"]:
            response = self.client.get(reverse(name))
            self.assertContains(response, "Continue with Google")
            self.assertContains(response, '<form method="post" action="/accounts/google/login/')

    @override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE)
    def test_the_button_sends_the_browser_to_google(self):
        response = self.client.post(reverse("google_login"))
        url = urlsplit(response["Location"])
        query = parse_qs(url.query)
        self.assertEqual(url.netloc, "accounts.google.com")
        self.assertEqual(query["client_id"], ["test-client.apps.googleusercontent.com"])
        self.assertEqual(query["redirect_uri"], ["http://testserver/accounts/google/login/callback/"])
        self.assertIn("code_challenge", query)  # PKCE
