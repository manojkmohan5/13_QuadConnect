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

from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import render

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


def match_list(request):
    """STUB - replace on branch feature/match-views."""
    return HttpResponse(
        "<h1>Matches</h1><p>Not implemented yet. "
        "Owner: Manojkumar Mohankumar.</p>",
        content_type="text/html",
    )


# ===========================================================================
# Section B1 - Base Class-Based View (inherits django.views.View)
# OWNER: Prathamesh Mulay (pmulay2)   URL name: connect:location-list
# See docs/build_tasks/prathamesh_location_views.md
# ===========================================================================


def campus_location_list_stub(request):
    """STUB - replace with CampusLocationListView on
    branch feature/location-views."""
    return HttpResponse(
        "<h1>Campus locations</h1>"
        "<p>Not implemented yet. Owner: Prathamesh Mulay.</p>",
        content_type="text/html",
    )


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
