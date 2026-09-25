"""
URL routing for the connect app.

Every route is named, so templates and tests reverse them by name rather than
by hard-coded path. Namespaced as `connect`, e.g. {% url 'connect:match-list' %}.

The four graded P1-A2 views:

    /students/            connect:student-list       Generic CBV   Kritika
    /matches/             connect:match-list         render() FBV  Manojkumar
    /locations/           connect:location-list      Base CBV      Prathamesh
    /feedback/summary/    connect:feedback-summary   HttpResponse  Dhruv

Each owner swaps their own line from the stub to the real view on their own
branch. The path and the name must not change - base.html reverses all of them.
"""

from django.urls import path

from . import views

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

    # --- Prathamesh Mulay - Base CBV -------------------------------------
    # Replace with CampusLocationListView.as_view()
    path(
        "locations/",
        views.CampusLocationListView.as_view(),
        name="location-list",
    ),
    path("locations/<int:pk>/", views.CampusLocationDetailView.as_view(),
         name="location-detail"),
    # --- Dhruv Thaker - HttpResponse FBV ---------------------------------
    path("feedback/summary/", views.feedback_summary, name="feedback-summary"),
]
