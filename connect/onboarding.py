"""
Joining QuadConnect: the account.

    SignupView   /accounts/signup/   allauth's sign-up, safe against a double click
"""

from allauth.account.views import SignupView as AllauthSignupView
from django.db import IntegrityError, transaction


class SignupView(AllauthSignupView):
    """allauth's sign-up page. A double click on "Create account" sends the
    form twice: both copies pass allauth's "username taken" check before
    either is saved, and the second save breaks the database's unique rule.
    That was a 500 page. Now it is the form again, saying what happened.

    Public like allauth's own view: it inherits the login_not_required
    dispatch."""

    def form_valid(self, form):
        try:
            with transaction.atomic():  # the whole sign-up, or none of it
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("username", (
                f'The username "{form.cleaned_data["username"]}" was taken a moment ago, '
                "perhaps by a second click on Create account. If that account is "
                "yours, log in. If not, choose another username."))
            return self.form_invalid(form)
