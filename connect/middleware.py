"""
Login required on every page, unless its view is marked public (P1-A5).

Django's LoginRequiredMiddleware sends a visitor who is not signed in to the
login page, then back to where they were going. The views decorated with
@login_not_required stay open: the home page, the public API
(/api/summary/), and allauth's own sign-in pages.

A program calling the JSON API cannot fill in a login form, so API paths
get a 401 JSON answer instead of the redirect. The API documentation page
(/api/ itself) is a page, and redirects like the others.
"""

from django.contrib.auth.middleware import (
    LoginRequiredMiddleware as DjangoLoginRequired,
)
from django.http import JsonResponse
from django.urls import reverse


class LoginRequiredMiddleware(DjangoLoginRequired):

    def handle_no_permission(self, request, view_func):
        if request.path.startswith("/api/") and request.path != reverse("connect:api-docs"):
            return JsonResponse({
                "error": "Log in to use this endpoint. Only /api/summary/ is public.",
                "login": request.build_absolute_uri(reverse("account_login")),
            }, status=401, json_dumps_params={"indent": 2})
        return super().handle_no_permission(request, view_func)
