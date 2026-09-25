"""
Read-only JSON API (P1-A3 Section 6).

    GET /api/                 FBV   api_docs            HTML documentation
    GET /api/locations/       CBV   LocationListAPI     JsonResponse
    GET /api/matches/         FBV   match_list_api      JsonResponse
    GET /api/locations.txt    FBV   location_list_text  HttpResponse, text/plain

JsonResponse vs HttpResponse: JsonResponse serialises a dict with
DjangoJSONEncoder (dates, datetimes and decimals included) and sets
Content-Type: application/json, so clients parse it as data.
HttpResponse sends whatever string it is given, labelled text/html unless
told otherwise; /api/locations.txt returns the same venues as text/plain,
for people rather than programs.

What leaves through the API is public by design: approved venues and the
match schedule. No student names, NetIDs, emails, check-in codes or
feedback. Query parameters are validated with forms, and a bad value gets
a 400 JSON error naming the parameter and how to fix it.
"""

from django import forms
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import localtime
from django.views import View
from django.views.decorators.http import require_GET

from .models import CampusLocation, ConnectionType, Match, MatchStatus

JSON_PARAMS = {"indent": 2}  # readable in a browser; a few bytes per line


# --- Query parameter validation ---------------------------------------------


class LocationFilters(forms.Form):
    setting = forms.ChoiceField(
        required=False,
        choices=[("indoor", "indoor"), ("outdoor", "outdoor")],
        error_messages={"invalid_choice":
                        'Use setting=indoor or setting=outdoor, not "%(value)s".'},
    )
    min_seats = forms.IntegerField(
        required=False,
        min_value=1,
        error_messages={"invalid": "Use a whole number, e.g. min_seats=8.",
                        "min_value": "Use a number of seats of 1 or more."},
    )


class MatchFilters(forms.Form):
    week = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        error_messages={"invalid": "Use the Monday the week starts on, as "
                                   "YYYY-MM-DD, e.g. week=2026-09-07."},
    )
    type = forms.ChoiceField(
        required=False,
        choices=ConnectionType.choices,
        error_messages={"invalid_choice": 'Use type=FRIEND or type=SQUAD, '
                                          'not "%(value)s".'},
    )
    status = forms.ChoiceField(
        required=False,
        choices=MatchStatus.choices,
        error_messages={"invalid_choice":
                        "Use status=" + ", ".join(MatchStatus.values)
                        + ', not "%(value)s".'},
    )


def _bad_params(filters):
    """400 listing every invalid parameter with how to fix it."""
    return JsonResponse({
        "error": "Invalid query parameter.",
        "fields": {name: [e["message"] for e in errors]
                   for name, errors in filters.errors.get_json_data().items()},
    }, status=400, json_dumps_params=JSON_PARAMS)


def _used(cleaned):
    """The filters actually applied, echoed back so a client can confirm."""
    return {k: v for k, v in cleaned.items() if v not in (None, "")}


# --- Locations --------------------------------------------------------------


def _locations(cleaned):
    venues = (CampusLocation.objects.filter(is_approved=True)
              .annotate(matches_hosted=Count("matches"))
              .order_by("name"))
    if cleaned.get("setting"):
        venues = venues.filter(is_indoor=cleaned["setting"] == "indoor")
    if cleaned.get("min_seats") is not None:
        venues = venues.filter(capacity__gte=cleaned["min_seats"])
    return venues


def _location_json(request, venue):
    return {
        "id": venue.pk,
        "name": venue.name,
        "street_address": venue.street_address,
        "arrival_note": venue.arrival_note,
        "setting": "indoor" if venue.is_indoor else "outdoor",
        "capacity": venue.capacity,
        "matches_hosted": venue.matches_hosted,
        "url": request.build_absolute_uri(venue.get_absolute_url()),
    }


class LocationListAPI(View):
    """GET /api/locations/ - approved venues as JSON (class-based).

    ?setting=indoor|outdoor   ?min_seats=<whole number>
    Only get() is defined, so View answers any other method with 405.
    """

    def get(self, request):
        filters = LocationFilters(request.GET)
        if not filters.is_valid():
            return _bad_params(filters)
        venues = [_location_json(request, v) for v in _locations(filters.cleaned_data)]
        return JsonResponse({
            "count": len(venues),
            "filters": _used(filters.cleaned_data),
            "results": venues,
        }, json_dumps_params=JSON_PARAMS)


@require_GET
def location_list_text(request):
    """GET /api/locations.txt - the same venues through plain HttpResponse.

    HttpResponse does no serialisation: it sends the string it is given,
    and says text/plain only because content_type says so.
    """
    filters = LocationFilters(request.GET)
    if not filters.is_valid():
        return _bad_params(filters)
    lines = [f"{v.name} | {v.street_address} | "
             f"{'indoor' if v.is_indoor else 'outdoor'} | seats {v.capacity}"
             for v in _locations(filters.cleaned_data)]
    body = "\n".join(lines) or "No approved venues match."
    return HttpResponse(body + "\n", content_type="text/plain; charset=utf-8")


# --- Matches ----------------------------------------------------------------


def _match_json(request, match):
    return {
        "id": match.pk,
        "connection_type": match.connection_type,
        "connection_type_label": match.get_connection_type_display(),
        "status": match.status,
        "week_start": match.week_start,
        # Local time with its UTC offset, e.g. 2026-09-12T14:00:00-05:00.
        "scheduled_for": localtime(match.scheduled_for),
        "location": {
            "id": match.location.pk,
            "name": match.location.name,
        },
        "suggested_activity": (match.suggested_activity.name
                               if match.suggested_activity else None),
        "participant_count": match.participant_count,
        "url": request.build_absolute_uri(match.get_absolute_url()),
    }


@require_GET
def match_list_api(request):
    """GET /api/matches/ - the match schedule as JSON (function-based).

    ?week=YYYY-MM-DD   ?type=FRIEND|SQUAD   ?status=PROPOSED|CONFIRMED|...
    Participants appear only as a count; the check-in code is left out.
    """
    filters = MatchFilters(request.GET)
    if not filters.is_valid():
        return _bad_params(filters)
    data = filters.cleaned_data
    matches = (Match.objects.select_related("location", "suggested_activity")
               .annotate(participant_count=Count("participants"))
               .order_by("-week_start", "-scheduled_for"))
    if data.get("week"):
        matches = matches.filter(week_start=data["week"])
    if data.get("type"):
        matches = matches.filter(connection_type__exact=data["type"])
    if data.get("status"):
        matches = matches.filter(status__exact=data["status"])
    results = [_match_json(request, m) for m in matches]
    return JsonResponse({
        "count": len(results),
        "filters": _used(data),
        "results": results,
    }, json_dumps_params=JSON_PARAMS)


# --- Documentation ----------------------------------------------------------


@require_GET
def api_docs(request):
    """GET /api/ - how to call each endpoint, with live examples.

    The Content-Type values and the sample body come from calling the real
    views, so this page cannot drift from what the API actually returns.
    """
    json_response = LocationListAPI.as_view()(request)
    text_response = location_list_text(request)
    locations = reverse("connect:api-locations")
    matches = reverse("connect:api-matches")
    text = reverse("connect:api-locations-text")
    return render(request, "connect/api_docs.html", {
        "sample": json_response.content.decode(),
        "json_type": json_response["Content-Type"],
        "text_type": text_response["Content-Type"],
        "html_type": HttpResponse()["Content-Type"],
        "examples": {
            "locations": [locations, f"{locations}?setting=indoor",
                          f"{locations}?min_seats=10",
                          f"{locations}?min_seats=many"],
            "matches": [matches, f"{matches}?type=SQUAD",
                        f"{matches}?week=2026-09-07",
                        f"{matches}?status=COMPLETED",
                        f"{matches}?week=next-week"],
            "text": [text, f"{text}?setting=outdoor"],
        },
    })
