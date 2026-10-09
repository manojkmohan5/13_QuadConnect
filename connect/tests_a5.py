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
from allauth.account.adapter import get_adapter
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import get_resolver, reverse
from django.utils.html import escape

PUBLIC_ROUTES = {"home", "privacy", "api-summary"}
# A value for each URL parameter, so every route can be requested.
SAMPLE_KWARGS = {"pk": 1, "chart": "chart1", "fmt": "png"}

GOOGLE = {"google": {"SCOPE": ["profile", "email"], "OAUTH_PKCE_ENABLED": True,
                     "AUTH_PARAMS": {"access_type": "online", "prompt": "select_account"},
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


# --- Part 1.4: everything private except the landing page, privacy and the public API


class AccessTests(AuthTestCase):

    def test_only_the_public_routes_open_without_a_login(self):
        login = reverse("account_login")
        for name, path in connect_routes():
            with self.subTest(path=path):
                response = self.client.get(path)
                if name in PUBLIC_ROUTES:
                    self.assertEqual(response.status_code, 200)
                elif path.startswith("/api/") and name != "api-docs":
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
        self.assertContains(response, f'href="{reverse("account_signup")}">Sign up</a>')
        self.assertNotContains(response, "Recent matches")
        self.assertNotContains(response, "QC-")  # no check-in codes
        self.assertContains(response, f'href="{reverse("connect:privacy")}"')  # footer

    def test_admin_signs_in_through_the_rate_limited_login_page(self):
        response = self.client.get(reverse("admin:login") + "?next=/admin/")
        self.assertRedirects(response, reverse("account_login") + "?next=/admin/",
                             fetch_redirect_response=False)
        self.client.force_login(User.objects.get(username="tester"))
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_pages_seen_logged_in_are_never_cached(self):
        self.assertNotIn("no-store", self.client.get(reverse("connect:home")).get("Cache-Control", ""))
        self.client.force_login(self.member)
        self.assertIn("no-store", self.client.get(reverse("connect:student-list"))["Cache-Control"])

    def test_log_out_with_an_expired_session_goes_home(self):
        response = self.client.post(reverse("account_logout"))
        self.assertRedirects(response, reverse("connect:home"), fetch_redirect_response=False)

    def test_rate_limits_use_the_visitor_ip_behind_the_proxy(self):
        request = RequestFactory().get("/", HTTP_X_REAL_IP="203.0.113.7", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(get_adapter(request).get_client_ip(request), "203.0.113.7")
        request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(get_adapter(request).get_client_ip(request), "10.0.0.1")


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

    def test_the_admin_link_is_for_staff_only(self):
        admin = f'href="{reverse("admin:index")}"'
        self.assertNotContains(self.client.get(reverse("connect:home")), admin)
        self.client.force_login(self.member)
        self.assertNotContains(self.client.get(reverse("connect:home")), admin)
        self.client.force_login(User.objects.get(username="tester"))
        self.assertContains(self.client.get(reverse("connect:home")), admin)


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

    def test_next_rides_in_the_login_form(self):
        User.objects.create_user("ada", "ada@illinois.edu", self.PASSWORD)
        self.assertContains(self.client.get(reverse("account_login") + "?next=/reports/"),
                            'name="next" value="/reports/"')
        response = self.client.post(reverse("account_login"),  # next only in the form
                                    {"login": "ada", "password": self.PASSWORD, "next": "/reports/"})
        self.assertRedirects(response, "/reports/", fetch_redirect_response=False)

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
        response = self.client.get(reverse("account_reset_password"))
        self.assertContains(response, "can't send email yet")
        self.assertNotContains(response, "<form")


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

    @override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE,
                       SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_behind_the_https_proxy_google_calls_back_over_https(self):
        # As PythonAnywhere's proxy sends it: the browser's Host, and the scheme it used.
        response = self.client.post(reverse("google_login"), HTTP_HOST="testserver",
                                    HTTP_X_FORWARDED_PROTO="https")
        query = parse_qs(urlsplit(response["Location"]).query)
        self.assertEqual(query["redirect_uri"], ["https://testserver/accounts/google/login/callback/"])

    def google_callback(self, profile):
        """Go through the Google flow with Google itself mocked: the button,
        then Google's redirect back with a code, which the site exchanges
        for the user's profile."""
        location = self.client.post(reverse("google_login"))["Location"]
        state = parse_qs(urlsplit(location).query)["state"][0]
        token = {"access_token": "test-token", "token_type": "Bearer", "expires_in": 3600}
        with (patch("allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
                    return_value=token),
              patch("allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter._fetch_user_info",
                    return_value=profile)):
            return self.client.get(reverse("google_callback"), {"code": "test-code", "state": state})

    @override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE)
    def test_google_sign_in_creates_the_account_and_logs_in(self):
        response = self.google_callback({"sub": "1234567890", "email": "ada@example.com",
                                         "email_verified": True, "name": "Ada Lovelace",
                                         "given_name": "Ada", "family_name": "Lovelace"})
        self.assertRedirects(response, reverse("connect:home"), fetch_redirect_response=False)
        user = User.objects.get(pk=self.client.session["_auth_user_id"])
        self.assertEqual((user.email, user.first_name), ("ada@example.com", "Ada"))
        self.assertTrue(user.socialaccount_set.filter(provider="google", uid="1234567890").exists())

    @override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE)
    def test_google_sign_in_never_takes_over_an_account_by_email(self):
        # jordan4 is a seeded student; a Google account with the same
        # address must not be logged in as them.
        response = self.google_callback({"sub": "999", "email": "jordan4@illinois.edu",
                                         "email_verified": True, "name": "Someone Else"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(response, reverse("socialaccount_signup"), fetch_redirect_response=False)

    @override_settings(SOCIALACCOUNT_PROVIDERS=GOOGLE)
    def test_the_button_sends_the_browser_to_google(self):
        response = self.client.post(reverse("google_login"))
        url = urlsplit(response["Location"])
        query = parse_qs(url.query)
        self.assertEqual(url.netloc, "accounts.google.com")
        self.assertEqual(query["client_id"], ["test-client.apps.googleusercontent.com"])
        self.assertEqual(query["redirect_uri"], ["http://testserver/accounts/google/login/callback/"])
        self.assertIn("code_challenge", query)  # PKCE
        self.assertEqual(query["prompt"], ["select_account"])
