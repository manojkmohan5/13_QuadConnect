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

from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.utils.timezone import localtime
from django.views import View
from django.views.generic import DetailView, ListView

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


def _feedback_summary_data():
    """Build aggregate data for the private feedback summary."""

    summary = ExperienceFeedback.objects.aggregate(
        total=Count("id"),
        average_rating=Avg("rating"),
        wants_connection=Count(
            "id",
            filter=Q(wants_to_stay_connected=True),
        ),
        conversation=Count(
            "id",
            filter=Q(enjoyed_conversation=True),
        ),
        shared_interests=Count(
            "id",
            filter=Q(enjoyed_shared_interests=True),
        ),
        activity=Count(
            "id",
            filter=Q(enjoyed_activity=True),
        ),
        comfortable=Count(
            "id",
            filter=Q(felt_comfortable=True),
        ),
    )

    total = summary["total"]

    if total:
        counts_by_rating = dict(
            ExperienceFeedback.objects
            .values("rating")
            .annotate(count=Count("id"))
            .values_list("rating", "count")
        )

        distribution = [
            (
                stars,
                counts_by_rating.get(stars, 0),
                round(counts_by_rating.get(stars, 0) * 100 / total, 1),
            )
            for stars in range(1, 6)
        ]
    else:
        distribution = []

    enjoyment = [
        ("Enjoyed conversation", summary["conversation"]),
        ("Enjoyed shared interests", summary["shared_interests"]),
        ("Enjoyed the activity", summary["activity"]),
        ("Felt comfortable", summary["comfortable"]),
    ]

    return {
        "total": total,
        "average_rating": summary["average_rating"],
        "distribution": distribution,
        "enjoyment": enjoyment,
        "wants_connection": summary["wants_connection"],
    }


def feedback_summary(request):
    """Show an aggregate-only summary of private experience feedback."""

    context = _feedback_summary_data()

    template = loader.get_template("connect/feedback_summary.html")

    return HttpResponse(
        template.render(context, request),
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
        raw_seats = (request.GET.get("seats") or "").strip()

        # "Which venues can seat a squad of N?" is a real product question:
        # Squad Connect groups are 4-8 students, so a venue that seats 6
        # cannot host all of them. A hand-typed value must not 500.
        min_seats, bad_seats = None, False
        if raw_seats:
            try:
                min_seats = int(raw_seats)
            except ValueError:
                bad_seats = True

        # Only approved venues are ever schedulable. Unapproved rows exist so
        # a venue can be retired without losing the history of matches held
        # there - see docs/project_reference.md section 6.
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

        if min_seats is not None:
            queryset = queryset.filter(capacity__gte=min_seats)
        elif bad_seats:
            queryset = queryset.none()

        items = self._build_items(queryset)

        # Empty states differ by cause, so the reader learns what to change.
        if bad_seats:
            empty_title = "Could not read that group size"
            empty_message = (
                f'"{raw_seats}" is not a number. Enter a whole number of '
                f"students, for example 8."
            )
        elif min_seats is not None:
            empty_title = f"No approved venue seats {min_seats} students"
            empty_message = (
                "The largest approved venue is smaller than that group. "
                "Try a smaller group size, or clear the filter."
            )
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
                "Matches cannot be scheduled until a venue is approved. "
                "Run python manage.py seed_demo_data to load sample venues."
            )

        context = {
            "page_title": "Campus locations - QuadConnect",
            "heading": "Approved campus locations",
            "subtitle": (
                "Only approved public venues are listed. Every QuadConnect "
                "match is scheduled at one of these."
            ),
            "items": items,
            "empty_title": empty_title,
            "empty_message": empty_message,
            # For the filter controls in location_list.html.
            "selected_setting": setting,
            "selected_seats": raw_seats,
        }

        return render(request, "connect/location_list.html", context)


# ===========================================================================
# Section B2 - Generic Class-Based View (ListView / DetailView)
# OWNER: Kritika Agrawal (kritika7)   URL names: connect:student-list,
#                                                connect:student-detail
# See docs/build_tasks/kritika_profile_views.md
# ===========================================================================


class StudentProfileListView(ListView):
    """Browse the verified student roster, filterable by college.

    The graded generic view. Setting `model` is enough for ListView to build
    the queryset, name the context, paginate, and find
    connect/studentprofile_list.html by its own naming convention - so no
    `template_name` is set here on purpose. Compare with
    `CampusLocationListView` above, which does all four by hand.
    """

    model = StudentProfile
    context_object_name = "students"
    paginate_by = 10

    def get_queryset(self):
        """Apply the optional ?college= filter on top of the default order.

        The interest count is annotated rather than counted per row, so the
        list costs the same number of queries whatever its length.
        """
        # annotate() adds a GROUP BY, and Django drops Meta.ordering from a
        # grouped query - which makes pagination non-deterministic (a student
        # can appear on two pages, or none). Re-apply the ordering explicitly.
        queryset = StudentProfile.objects.annotate(
            interest_count=Count("interest_links")
        ).order_by("full_name", "net_id")
        college = (self.request.GET.get("college") or "").strip()
        if college:
            queryset = queryset.filter(college__icontains=college)
        return queryset

    def get_context_data(self, **kwargs):
        """Add what the filter box and the empty state need to explain
        themselves: the current filter, the colleges that actually exist,
        and the unfiltered total."""
        context = super().get_context_data(**kwargs)
        context["selected_college"] = (
            self.request.GET.get("college") or ""
        ).strip()
        context["colleges"] = (
            StudentProfile.objects.order_by("college")
            .values_list("college", flat=True)
            .distinct()
        )
        context["total_count"] = StudentProfile.objects.count()
        return context


class StudentProfileDetailView(DetailView):
    """One student's profile: preferences, interests, availability, history.

    DetailView handles the primary-key lookup and the 404 for a missing
    student, which is the other half of what the generic views buy you.
    """

    model = StudentProfile
    context_object_name = "student"

    def get_context_data(self, **kwargs):
        """Prefetch the related rows the template walks, so the page costs a
        fixed number of queries rather than one per interest."""
        context = super().get_context_data(**kwargs)
        student = self.object
        context["interest_links"] = (
            student.interest_links.select_related("interest")
            .order_by("-is_primary", "interest__name")
        )
        context["slots"] = student.availability_slots.all()
        context["participations"] = (
            student.match_participations
            .select_related("match", "match__location")
            .order_by("-match__scheduled_for")
        )
        return context
