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
(/search/), charts (/insights/...) and the JSON API (/api/...), each under a
comment naming its assignment section. Paths and names must not change
without updating base.html and the models' get_absolute_url(), which
reverse them.
"""

from django.urls import path

from . import api, charts, views

app_name = "connect"

urlpatterns = [
    path("", views.home, name="home"),

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

    # --- P1-A3 Section 6 - read-only JSON API -----------------------------
    path("api/", api.api_docs, name="api-docs"),
    path("api/locations/", api.LocationListAPI.as_view(), name="api-locations"),
    path("api/matches/", api.match_list_api, name="api-matches"),
    path("api/locations.txt", api.location_list_text, name="api-locations-text"),
]
