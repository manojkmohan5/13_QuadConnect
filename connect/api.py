"""
Read-only JSON API (P1-A3 Section 6, extended in P1-A4 and P1-A5).

    GET /api/                           FBV  api_docs            HTML documentation
    GET /api/locations/                 CBV  LocationListAPI     JsonResponse
    GET /api/matches/                   FBV  match_list_api      JsonResponse
    GET /api/locations.txt              FBV  location_list_text  HttpResponse, text/plain
    GET /api/summary/                   FBV  summary_api         chart-ready list (A4)
    GET /api/summary/matches-per-week/  FBV  matches_per_week_api  chart-ready records (A4)
    GET /api/icebreakers/?match=<id>    FBV  (icebreakers.py)    Open Trivia DB (A4)

The two /api/summary/ endpoints feed the Vega-Lite charts: flat rows, no
wrapping metadata, so a spec can point data.url straight at them.

Public and protected (P1-A5): /api/summary/ is the one public endpoint. It
needs no login and allows any origin (CORS), so the Vega-Lite editor or
anyone's script can read it; it holds counts only, no names. Every other
endpoint needs a login, and answers 401 without one (connect/middleware.py).

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

from collections import Counter
from datetime import timedelta
from functools import wraps

from django import forms
from django.contrib.auth.decorators import login_not_required
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import localtime
from django.views import View
from django.views.decorators.http import require_GET

from .models import CampusLocation, ConnectionType, Interest, Match, MatchStatus

JSON_PARAMS = {"indent": 2}  # readable in a browser; a few bytes per line


def allow_any_origin(view):
    """Let a page on any other site read this response (CORS).

    Only for the public API: it is what lets the Vega-Lite editor, or a
    classmate's chart, load /api/summary/ from their own page.
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        return response
    return wrapped


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
               .order_by("-week_start", "-scheduled_for", "-pk"))
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


# --- Chart data (P1-A4) -----------------------------------------------------
#
# Plain functions first, views second: the Vega-Lite image endpoints call the
# functions directly, so a server rendering a chart never has to make an
# HTTP request back to itself.


def interest_popularity():
    """Verified students per interest, most picked first. Interests nobody
    picked are left out. Two interests may share a name across categories
    (Food is a hobby and a meeting activity); such a name gets its type
    added, so each one keeps its own bar.

    [{"category": "Food", "count": 4, "type": "Hobby / Interest"}, ...]
    """
    verified = Q(profile_links__profile__is_sso_verified=True)
    interests = (Interest.objects.annotate(students=Count("profile_links", filter=verified))
                 .filter(students__gt=0)
                 .order_by("-students", "name"))
    rows = [{"category": i.name, "count": i.students,
             "type": i.get_category_display()} for i in interests]
    names = Counter(r["category"] for r in rows)
    for r in rows:
        if names[r["category"]] > 1:
            r["category"] = f"{r['category']} ({r['type']})"
    return rows


def matches_per_week():
    """Matches scheduled per matching week, oldest first, as records.

    Weeks with no matches between the first and the last are included with
    a count of 0, so a line chart shows the gap instead of hiding it.

    [{"date": "2026-07-13", "count": 1, "participants": 2}, ...]
    """
    rows = {r["week_start"]: r for r in
            Match.objects.values("week_start")
            .annotate(count=Count("id", distinct=True),
                      participants=Count("participants"))}
    if not rows:
        return []
    first, last = min(rows), max(rows)
    grid = {first + timedelta(weeks=n) for n in range((last - first).days // 7 + 1)}
    return [{"date": week.isoformat(),
             "count": rows[week]["count"] if week in rows else 0,
             "participants": rows[week]["participants"] if week in rows else 0}
            for week in sorted(grid | set(rows))]


@login_not_required  # the one public endpoint (P1-A5)
@allow_any_origin
@require_GET
def summary_api(request):
    """GET /api/summary/ - students per interest, for the bar chart.

    A bare list of {"category", "count"} rows, the shape the assignment
    shows, plus each interest's type for colour.
    """
    return JsonResponse(interest_popularity(), safe=False,
                        json_dumps_params=JSON_PARAMS)


@require_GET
def matches_per_week_api(request):
    """GET /api/summary/matches-per-week/ - matches per week, for the line
    chart, as {"records": [{"date", "count", "participants"}, ...]}."""
    return JsonResponse({"records": matches_per_week()},
                        json_dumps_params=JSON_PARAMS)


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
    icebreakers = reverse("connect:api-icebreakers")
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
            "summary": [reverse("connect:api-summary"),
                        reverse("connect:api-summary-matches-per-week")],
            "icebreakers": [f"{icebreakers}?match=2", f"{icebreakers}?match=two"],
        },
    })
