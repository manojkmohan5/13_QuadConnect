"""
Login required on every page, unless its view is marked public (P1-A5).

Django's LoginRequiredMiddleware sends a visitor who is not signed in to the
login page, then back to where they were going. The views decorated with
@login_not_required stay open: the home page, the privacy page, the public
API (/api/summary/), and allauth's own sign-in pages.

A program calling the JSON API cannot fill in a login form, so API paths
get a 401 JSON answer instead of the redirect. The API documentation page
(/api/ itself) is a page, and redirects like the others.

Anything served to a logged-in user is marked never-cache, so Back after
logging out cannot show a private page from the browser's cache.
"""

from django.contrib.auth.middleware import (
    LoginRequiredMiddleware as DjangoLoginRequired,
)
from django.http import JsonResponse
from django.urls import reverse
from django.utils.cache import add_never_cache_headers


def login_required_response(request):
    """The 401 a private API endpoint sends to a visitor who is not logged in
    (the API documentation page shows this exact body)."""
    return JsonResponse({
        "error": "Log in to use this endpoint. Only /api/summary/ is public.",
        "login": request.build_absolute_uri(reverse("account_login")),
    }, status=401, json_dumps_params={"indent": 2})


class LoginRequiredMiddleware(DjangoLoginRequired):

    def handle_no_permission(self, request, view_func):
        if request.path.startswith("/api/") and request.path != reverse("connect:api-docs"):
            return login_required_response(request)
        return super().handle_no_permission(request, view_func)

    def process_response(self, request, response):
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            add_never_cache_headers(response)
        return response
