"""
django-allauth adapter: the visitor's IP address on PythonAnywhere (P1-A5),
and the first stop after a login.

allauth rate-limits failed logins and sign-ups per IP address. Behind a load
balancer such as PythonAnywhere's, REMOTE_ADDR can be the balancer itself,
shared by every visitor, so one person's failed logins would lock everyone
out. The balancer passes the visitor's address in X-Real-IP; use it when it
is there, and allauth's own answer (REMOTE_ADDR) when it is not, as locally.

A visitor can send their own X-Real-IP, which only dodges the per-IP limit:
the per-account limit (5 failed logins in 5 minutes) still applies.

After a login or a sign-up, by password or by Google, a student who has no
profile yet goes to set one up first (connect/onboarding.py).
"""

from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import redirect

from .models import StudentProfile


class AccountAdapter(DefaultAccountAdapter):

    def get_client_ip(self, request):
        return request.headers.get("X-Real-IP") or super().get_client_ip(request)

    def post_login(self, request, user, **kwargs):
        """Profile first, wherever the login was headed: until a student has
        one, nobody can find them. Staff are not students, so they go on to
        where they were going."""
        response = super().post_login(request, user, **kwargs)
        if not user.is_staff and not StudentProfile.objects.filter(user=user).exists():
            return redirect("connect:profile")
        return response
