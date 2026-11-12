"""
Tests for joining QuadConnect (connect/onboarding.py): a double click on
"Create account".

    python manage.py test connect.tests_onboarding
"""

from unittest.mock import patch

from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

PASSWORD = "quad-Connect-2026!"  # noqa: S105 - a test password


class SignUpTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user("maddy", "maddy1234@gmail.com", PASSWORD)

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
