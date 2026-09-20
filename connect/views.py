"""
Views for the connect app.

P1-A2 requires four kinds of view over the same domain. Each is owned by one
team member and lives in its own clearly-marked section below:

    Section A1  HttpResponse FBV   feedback_summary          Dhruv Thaker
    Section A2  render() FBV       match_list                Manojkumar
    Section B1  Base CBV (View)    CampusLocationListView    Prathamesh Mulay
    Section B2  Generic CBV        StudentProfileListView    Kritika Agrawal

The four stubs below are placeholders committed on `main` so that
`base.html` can reverse every nav link from day one and the site is never
broken mid-integration. Each owner replaces their own stub on their own
feature branch; nobody needs to touch base.html or another owner's section.
"""

from datetime import date

from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.timezone import localtime
from django.views import View

from .models import (
    CampusLocation,
    ExperienceFeedback,
    Interest,
    Match,
    MatchParticipant,
    StudentProfile,
)


# ===========================================================================
# Home - shared dashboard (owned by main, do not claim as a graded view)
# ===========================================================================


def home(request):
    """Landing page: a count of every seeded entity plus recent matches."""
    context = {
        "counts": [
            ("Student profiles", StudentProfile.objects.count()),
            ("Interests in catalogue", Interest.objects.count()),
            ("Approved campus locations",
             CampusLocation.objects.filter(is_approved=True).count()),
            ("Matches", Match.objects.count()),
            ("Match participants", MatchParticipant.objects.count()),
            ("Feedback submissions", ExperienceFeedback.objects.count()),
        ],
        "recent_matches": (
            Match.objects.select_related("location", "suggested_activity")
            .annotate(headcount=Count("participants"))[:5]
        ),
        "average_rating": ExperienceFeedback.objects.aggregate(
            avg=Avg("rating")
        )["avg"],
    }
    return render(request, "connect/home.html", context)


# ===========================================================================
# Section A1 - Function-Based View returning HttpResponse manually
# OWNER: Dhruv Thaker (dthaker3)   URL name: connect:feedback-summary
# See docs/build_tasks/dhruv_feedback_views.md
# ===========================================================================


def feedback_summary(request):
    """STUB - replace on branch feature/feedback-views."""
    return HttpResponse(
        "<h1>Feedback summary</h1>"
        "<p>Not implemented yet. Owner: Dhruv Thaker.</p>",
        content_type="text/html",
    )


# ===========================================================================
# Section A2 - Function-Based View using the render() shortcut
# OWNER: Manojkumar Mohankumar (mm240)   URL name: connect:match-list
# See docs/build_tasks/manojkumar_match_views.md
# ===========================================================================


def _match_rows(matches):
    """Shape a Match queryset into rows for the shared list template.

    `entity_list.html` knows nothing about any model - it renders plain
    dicts. Turning a Match into one of those dicts is the view's job, which
    is what lets the same template serve this page and the campus-location
    page from two different view styles.

    Expects the queryset to be annotated with `headcount`.
    """
    rows = []
    for match in matches:
        activity = (match.suggested_activity.name
                    if match.suggested_activity else "No activity suggested")
        # localtime() converts the stored UTC value to America/Chicago.
        # %-I is glibc-only, so strip the leading zero by hand for Windows.
        when = localtime(match.scheduled_for)
        when_str = (when.strftime("%a %d %b, ")
                    + when.strftime("%I:%M %p").lstrip("0"))
        rows.append({
            "title": match.get_connection_type_display(),
            "subtitle": f"{match.location.name} - "
                        f"{match.location.street_address}",
            "meta": [
                when_str,
                f"{match.headcount} student"
                f"{'' if match.headcount == 1 else 's'}",
                activity,
                f"Code {match.check_in_code}",
            ],
            "badge": match.get_status_display(),
        })
    return rows


def match_list(request):
    """List every weekly scheduled experience, optionally filtered by week.

    The graded `render()` view: it queries the model, builds a context
    dictionary, and hands both to the render() shortcut. Compare with
    `feedback_summary` above, which does the same job the long way.
    """
    raw_week = (request.GET.get("week") or "").strip()
    selected_week, bad_date = None, False

    if raw_week:
        try:
            selected_week = date.fromisoformat(raw_week)
        except ValueError:
            # A hand-typed query string should not produce a 500.
            bad_date = True

    matches = (
        Match.objects
        .select_related("location", "suggested_activity")
        .annotate(headcount=Count("participants"))
    )
    if selected_week:
        matches = matches.filter(week_start=selected_week)
    elif bad_date:
        matches = matches.none()

    # Empty states differ by cause: an unreadable date, a week with nothing
    # scheduled, and a database with no matches at all are three different
    # problems and deserve three different messages.
    if bad_date:
        empty_title = "Could not read that date"
        empty_message = (f'"{raw_week}" is not a date. Use the format '
                         f'YYYY-MM-DD, for example 2026-09-07.')
    elif selected_week:
        empty_title = f"No matches for the week of {selected_week:%d %b %Y}"
        empty_message = ("No experience was scheduled that week. Clear the "
                         "filter to see every match.")
    else:
        empty_title = "No matches scheduled yet"
        empty_message = ("Matches appear here once a weekly matching cycle "
                         "runs. Run python manage.py seed_demo_data to load "
                         "sample data.")

    context = {
        "page_title": "Matches - QuadConnect",
        "heading": "Weekly matches",
        "subtitle": "Every scheduled experience, newest cycle first. "
                    "Each match is one real meeting at an approved campus "
                    "location.",
        "items": _match_rows(matches),
        "empty_title": empty_title,
        "empty_message": empty_message,
        # For the filter form in match_list.html.
        "selected_week": raw_week,
        "available_weeks": (
            Match.objects.order_by("-week_start")
            .values_list("week_start", flat=True).distinct()
        ),
    }
    return render(request, "connect/match_list.html", context)


# ===========================================================================
# Section B1 - Base Class-Based View (inherits django.views.View)
# OWNER: Prathamesh Mulay (pmulay2)   URL name: connect:location-list
# See docs/build_tasks/prathamesh_location_views.md
# ===========================================================================


class CampusLocationListView(View):
    """List approved QuadConnect campus meeting locations."""

    def _build_items(self, queryset):
        items = []

        for location in queryset:
            setting = "Indoor" if location.is_indoor else "Outdoor"

            meta = [
                setting,
                f"Seats up to {location.capacity}",
                f"Hosted {location.match_count} matches",
            ]

            if location.arrival_note:
                meta.append(location.arrival_note)

            items.append(
                {
                    "title": location.name,
                    "subtitle": location.street_address,
                    "meta": meta,
                    "badge": setting,
                    "url": None,
                }
            )

        return items

    def get(self, request):
        setting = request.GET.get("setting", "").strip().lower()

        queryset = (
            CampusLocation.objects.annotate(
                match_count=Count("matches")
            )
            .filter(is_approved=True)
            .order_by("name")
        )

        if setting == "indoor":
            queryset = queryset.filter(is_indoor=True)
        elif setting == "outdoor":
            queryset = queryset.filter(is_indoor=False)

        items = self._build_items(queryset)

        if items:
            empty_title = ""
            empty_message = ""
        elif setting == "indoor":
            empty_title = "No indoor venues approved"
            empty_message = (
                "Try clearing the indoor filter to see other approved venues."
            )
        elif setting == "outdoor":
            empty_title = "No outdoor venues approved"
            empty_message = (
                "Try clearing the outdoor filter to see other approved venues."
            )
        else:
            empty_title = "No approved campus locations"
            empty_message = (
                "Matches cannot be scheduled until a venue is approved."
            )

        context = {
            "page_title": "Campus Locations",
            "entity_name": "Campus Locations",
            "items": items,
            "empty_title": empty_title,
            "empty_message": empty_message,
        }

        return render(request, "connect/location_list.html", context)


# ===========================================================================
# Section B2 - Generic Class-Based View (ListView / DetailView)
# OWNER: Kritika Agrawal (kritika7)   URL names: connect:student-list,
#                                                connect:student-detail
# See docs/build_tasks/kritika_profile_views.md
# ===========================================================================


def student_profile_list_stub(request):
    """STUB - replace with StudentProfileListView on
    branch feature/profile-views."""
    return HttpResponse(
        "<h1>Students</h1><p>Not implemented yet. Owner: Kritika Agrawal.</p>",
        content_type="text/html",
    )


def student_profile_detail_stub(request, pk):
    """STUB - replace with StudentProfileDetailView on
    branch feature/profile-views."""
    return HttpResponse(
        f"<h1>Student {pk}</h1><p>Not implemented yet. "
        f"Owner: Kritika Agrawal.</p>",
        content_type="text/html",
    )
