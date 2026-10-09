"""
django-allauth adapter (P1-A5): the visitor's IP address on PythonAnywhere.

allauth rate-limits failed logins and sign-ups per IP address. Behind a load
balancer such as PythonAnywhere's, REMOTE_ADDR can be the balancer itself,
shared by every visitor, so one person's failed logins would lock everyone
out. The balancer passes the visitor's address in X-Real-IP; use it when it
is there, and allauth's own answer (REMOTE_ADDR) when it is not, as locally.

A visitor can send their own X-Real-IP, which only dodges the per-IP limit:
the per-account limit (5 failed logins in 5 minutes) still applies.
"""

from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):

    def get_client_ip(self, request):
        return request.headers.get("X-Real-IP") or super().get_client_ip(request)
