"""
URL routing for the connect app.

Every route is named, so templates and tests reverse them by name rather than
by hard-coded path. Namespaced as `connect`, e.g. {% url 'connect:match-list' %}.

The four graded P1-A2 views:

    /students/            connect:student-list       Generic CBV   Kritika
    /matches/             connect:match-list         render() FBV  Manojkumar
    /locations/           connect:location-list      Base CBV      Prathamesh
    /feedback/summary/    connect:feedback-summary   HttpResponse  Dhruv

P1-A3 added detail pages (/matches/<pk>/, /locations/<pk>/), search
(/search/), charts (/insights/...) and the JSON API (/api/...). P1-A4 added
chart data (/api/summary/...), Vega-Lite specs and images (/vega-lite/...),
icebreakers (/api/icebreakers/, /matches/<pk>/icebreakers/), and reports
with exports (/reports/, /export/...). Each group sits under a comment
naming its assignment section; every /api/ route is in one block. Paths and
names must not change without updating base.html and the models'
get_absolute_url(), which reverse them.
"""

from django.urls import path

from . import api, charts, icebreakers, reports, vega_charts, views

app_name = "connect"

urlpatterns = [
    path("", views.home, name="home"),
    # P1-A5: public, linked from Google's sign-in screen and the footer.
    path("privacy/", views.privacy, name="privacy"),

    # --- Kritika Agrawal - Generic CBV -----------------------------------
    path("students/", views.StudentProfileListView.as_view(),
         name="student-list"),
    path("students/<int:pk>/", views.StudentProfileDetailView.as_view(),
         name="student-detail"),

    # --- P1-A3 Section 2 - ORM search (GET and POST forms) ------------------
    path("search/", views.StudentSearchView.as_view(), name="student-search"),

    # --- Manojkumar Mohankumar - render() FBV ----------------------------
    path("matches/", views.match_list, name="match-list"),
    path("matches/<int:pk>/", views.MatchDetailView.as_view(),
         name="match-detail"),
    # P1-A4 Part 2 - the same result as /api/icebreakers/, as a page.
    path("matches/<int:pk>/icebreakers/", icebreakers.icebreakers_page,
         name="match-icebreakers"),

    # --- Prathamesh Mulay - Base CBV (POST added in P1-A3 Section 5) --------
    path(
        "locations/",
        views.CampusLocationListView.as_view(),
        name="location-list",
    ),
    path("locations/<int:pk>/", views.CampusLocationDetailView.as_view(),
         name="location-detail"),

    # --- Dhruv Thaker - HttpResponse FBV ---------------------------------
    path("feedback/summary/", views.feedback_summary, name="feedback-summary"),

    # --- P1-A3 Section 4 - Matplotlib charts ------------------------------
    # The page, and one image/png endpoint per chart.
    path("insights/", charts.insights, name="insights"),
    path("insights/students-by-college.png", charts.students_by_college_png,
         name="chart-students-by-college"),
    path("insights/interest-categories.png", charts.interest_categories_png,
         name="chart-interest-categories"),

    # --- Read-only JSON API (P1-A3 Section 6, extended in P1-A4) -----------
    path("api/", api.api_docs, name="api-docs"),
    path("api/locations/", api.LocationListAPI.as_view(), name="api-locations"),
    path("api/matches/", api.match_list_api, name="api-matches"),
    path("api/locations.txt", api.location_list_text, name="api-locations-text"),
    # Chart-ready data for the Vega-Lite charts (P1-A4 Part 1).
    path("api/summary/", api.summary_api, name="api-summary"),
    path("api/summary/matches-per-week/", api.matches_per_week_api,
         name="api-summary-matches-per-week"),
    # Open Trivia DB questions for a match, from its members' interests (Part 2).
    path("api/icebreakers/", icebreakers.icebreakers_api, name="api-icebreakers"),

    # --- P1-A4 Part 1.2 - Vega-Lite charts ---------------------------------
    # The spec (data.url points at /api/summary/...) and server-rendered images.
    path("vega-lite/<slug:chart>.vl.json", vega_charts.vega_spec, name="vega-spec"),
    path("vega-lite/<slug:chart>.<slug:fmt>", vega_charts.vega_image, name="vega-image"),

    # --- P1-A4 Part 3 - reports and the student exports ---------------------
    path("reports/", reports.reports, name="reports"),
    path("export/students.csv", reports.students_csv, name="export-students-csv"),
    path("export/students.json", reports.students_json, name="export-students-json"),
]
