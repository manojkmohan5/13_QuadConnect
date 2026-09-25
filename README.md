# QuadConnect

**A verified campus social discovery platform for UIUC students.**

QuadConnect helps students form real friendships through structured,
in-person experiences. Students authenticate with university SSO, describe
their interests and social preferences, and receive **one** match per week —
either a one-to-one *Friend Connect* or a small-group *Squad Connect* — with a
scheduled time, an approved campus location, and a suggested activity.

It is deliberately not a feed, not a swiping app, and not a messaging app.
Matching exists to produce a single real-world meeting.

> **The Connectors · Team 13** · INFO 490, Fall 2026
> University of Illinois Urbana-Champaign

| Member | NetID | Feature area |
|---|---|---|
| Kritika Agrawal | kritika7 | Onboarding & student profiles |
| Manojkumar Mohankumar | mm240 | Matching engine |
| Prathamesh Mulay | pmulay2 | Availability, scheduling, check-in |
| Dhruv Thaker | dthaker3 | Social preferences & feedback |

---

## Quick start

Requires **Python 3.11+**. No other services — the database is SQLite.

```bash
git clone https://github.com/manojkmohan5/13_QuadConnect.git
cd 13_QuadConnect

python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# .venv\Scripts\activate           # Windows PowerShell
# source .venv/bin/activate        # macOS / Linux

pip install -r requirements.txt

cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
# paste the output into DJANGO_SECRET_KEY in .env

python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Run the test suite with
`python manage.py test connect` (45 tests).

The first command after installing pauses for a while (up to a minute on
Windows) while Matplotlib builds its font cache. That happens once.

`db.sqlite3` is intentionally **not** committed — a tracked binary conflicts on
every branch. `seed_demo_data` is idempotent and rebuilds the same dataset, so
run it instead of sharing a database file.

### Admin

```bash
python manage.py createsuperuser
```

The seed data also ships two superusers, both with password `uiuc12345`:
`mohitg2` and `tester`. (P1-A1 named a different one in two places, so both
exist.)

---

## P1-A3 features

Everything below was added in P1-A3. Each section of the assignment maps to
one area of the code, and each has screenshots in
[`docs/screenshots/p1-a3/`](docs/screenshots/p1-a3/) and tests in
[`connect/tests.py`](connect/tests.py).

### 1. URL linking and navigation

Every page shares one navigation bar in `base.html`, built entirely with
`{% url %}`, and the current section is highlighted and marked with
`aria-current`. Students, matches and venues each have a detail page at
`/students/<pk>/`, `/matches/<pk>/` and `/locations/<pk>/`; every list row, the
home page's recent matches and the detail pages themselves link to one another
through each model's `get_absolute_url()`, so every URL pattern is written once,
in `urls.py`. The flow is models (`get_absolute_url()` calls `reverse()`) →
urls (named routes with `<int:pk>`) → views (`DetailView`) → templates
(`{{ match.get_absolute_url }}`).
Screenshots: [01](docs/screenshots/p1-a3/01_home.png), [02](docs/screenshots/p1-a3/02_nav_active_state.png), [03](docs/screenshots/p1-a3/03_detail_via_link.png).

### 2. ORM queries: search with GET and POST

`/search/` (`StudentSearchView`) has two forms. **Search the roster** is a GET
form: name or interest (`full_name__icontains`, and
`interest_links__interest__name__icontains` across two relations), college and
connection type (`__exact`), and "has met at" a venue
(`match_participations__match__location__name__exact`, three relations).
Because it is GET, a search is a URL that can be bookmarked or shared. **Look up
a NetID** is a POST form with `{% csrf_token %}` (`net_id__iexact`), so the
NetID stays out of the URL, browser history, server logs and `Referer`. Below
the results the page shows a total (`aggregate(Count, Avg)`) and grouped
summaries (`values("college").annotate(Count(...))`, interests ranked by
`annotate(Count("profile_links"))`), every loop with an `{% empty %}` branch.
Screenshots: [04](docs/screenshots/p1-a3/04_search_get_results.png), [05](docs/screenshots/p1-a3/05_search_aggregates.png), [06](docs/screenshots/p1-a3/06_search_post_lookup.png).

### 3. Static files and UI

The design lives in [`static/css/quadconnect.css`](static/css/quadconnect.css),
loaded in `base.html` with `{% load static %}` and `{% static %}`, alongside the
logo (`static/img/logo.svg`) and the self-hosted Inter font (`static/fonts/`).
**UI note:** a dark header with the four-quadrant logo, an orange accent used
sparingly for actions and the current nav item, white cards on a warm grey
page, and one type family throughout. Every colour pair meets WCAG 2.1 AA
contrast, focus is always visible, there is a skip link, and every page fits a
375 px phone screen. WhiteNoise serves the files in development and
production; in production they are stored under content-hashed names for
cache busting (see [Running in development vs production](#running-in-development-vs-production)).
Screenshots: [07](docs/screenshots/p1-a3/07_css_applied.png), [08](docs/screenshots/p1-a3/08_cache_busting_page.png), [09](docs/screenshots/p1-a3/09_cache_busting_file.png).

### 4. Charts with Matplotlib

`/insights/` shows two charts drawn from ORM aggregations: a stacked bar chart
of students per college by connection type, and a pie chart of interest
selections by category, each with a title, labels and a legend. Each image is
its own endpoint (`/insights/students-by-college.png`,
`/insights/interest-categories.png`) that draws on a `matplotlib.figure.Figure`,
saves into a `BytesIO` buffer and returns `HttpResponse(content_type="image/png")`.
The page gives each chart a caption, alt text and a data table, all built from
the same rows. Code: [`connect/charts.py`](connect/charts.py).
Screenshots: [10](docs/screenshots/p1-a3/10_insights_page.png), [11](docs/screenshots/p1-a3/11_insights_pie_and_table.png), [12](docs/screenshots/p1-a3/12_chart_png_endpoint.png).

### 5. Forms on a class-based view

`/locations/` (`CampusLocationListView`, a base `View`) now handles both
methods. **GET** reads the `?setting=` and `?seats=` filters. **POST** submits
"Suggest a venue" (`CampusLocationSuggestionForm`, a `ModelForm` with
`{% csrf_token %}`): it saves the venue as unapproved, shows a success message
and redirects (Post/Redirect/Get). An invalid form re-renders with an error
summary and a message next to each field. `is_approved` is not a form field,
so no request can approve its own suggestion; staff approve in Django Admin.
Screenshots: [13](docs/screenshots/p1-a3/13_form_post_errors.png), [14](docs/screenshots/p1-a3/14_form_post_success.png).

### 6. JSON API

A read-only API over public data. Documentation with live examples is at
[`/api/`](http://127.0.0.1:8000/api/); code in [`connect/api.py`](connect/api.py).

| Endpoint | View | Query parameters | Returns |
|---|---|---|---|
| `GET /api/locations/` | `LocationListAPI` (class-based) | `setting=indoor\|outdoor`, `min_seats=<int>` | approved venues, `application/json` |
| `GET /api/matches/` | `match_list_api` (function-based) | `week=YYYY-MM-DD`, `type=FRIEND\|SQUAD`, `status=PROPOSED\|CONFIRMED\|COMPLETED\|CANCELLED` | the match schedule, `application/json` |
| `GET /api/locations.txt` | `location_list_text` (function-based) | same as `/api/locations/` | the same venues, `text/plain; charset=utf-8` |

Every JSON list has the shape `{"count", "filters", "results"}`, and each result
carries a `url` to its page on the site. A bad parameter is never ignored: the
response is `400` with each bad parameter and how to fix it.

```text
GET /api/locations/?setting=indoor&min_seats=10

{
  "count": 1,
  "filters": {"setting": "indoor", "min_seats": 10},
  "results": [
    {"id": 1, "name": "Illini Union", "street_address": "1401 W Green St, Urbana",
     "arrival_note": "Main entrance, ground floor lobby", "setting": "indoor",
     "capacity": 12, "matches_hosted": 1, "url": "http://127.0.0.1:8000/locations/1/"}
  ]
}
```

**HttpResponse vs JsonResponse.** `JsonResponse` serialises a dict (dates and
decimals included) and sends `Content-Type: application/json`, so a client
parses it as data. `HttpResponse` sends whatever string it is given, labelled
`text/html` unless told otherwise; `/api/locations.txt` sends the same venues as
`text/plain`. The API never returns student names, NetIDs, emails, check-in
codes, feedback or unapproved venues.
Screenshots: [15](docs/screenshots/p1-a3/15_api_locations_json.png), [16](docs/screenshots/p1-a3/16_api_matches_json.png), [17](docs/screenshots/p1-a3/17_api_bad_param_400.png), [18](docs/screenshots/p1-a3/18_api_text_plain.png), [19](docs/screenshots/p1-a3/19_api_docs_mime.png).

---

## Running in development vs production

Settings are split into a package. Pick an environment with
`DJANGO_SETTINGS_MODULE`.

| | Module | `DEBUG` | `ALLOWED_HOSTS` | Static files |
|---|---|---|---|---|
| Development | `quadconnect.settings.development` | `True` | localhost, 127.0.0.1 | served from `static/` |
| Production | `quadconnect.settings.production` | `False` | **required** from `.env` | hashed copies in `staticfiles/` |

`manage.py` defaults to development; `wsgi.py` and `asgi.py` default to
production, so a real deployment cannot accidentally boot with `DEBUG=True`.

```bash
# development (default)
python manage.py runserver

# production settings locally: collect the hashed static files first
export DJANGO_SETTINGS_MODULE=quadconnect.settings.production
python manage.py collectstatic --noinput
python manage.py runserver

# production deployment checklist
python manage.py check --deploy
```

**Cache busting.** In production, `collectstatic` writes each static file a
second time under a name that includes a hash of its contents
(`quadconnect.css` → `quadconnect.9d7082daf6a5.css`) and records the mapping in
a manifest; `{% static %}` looks names up there. WhiteNoise serves hashed files
with `Cache-Control: max-age=315360000, public, immutable`, so browsers cache
them for good, and any edit produces a new name, so no browser can keep a stale
stylesheet after a deploy. `staticfiles/` is gitignored.

Production **fails fast**: if `DJANGO_ALLOWED_HOSTS` is unset it raises at
startup rather than silently serving any `Host` header. Set
`DJANGO_SECURE_SSL=1` behind real TLS to switch on HSTS, the SSL redirect and
secure cookies — with that flag, `check --deploy` reports zero issues.

---

## Continuous integration

Every push to `feature/p1-a3` runs one GitHub Actions check, **Deploy / test
(push)**, defined in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).
Its single job runs, in order:

1. `ruff check .` (rules in [`ruff.toml`](ruff.toml))
2. `manage.py check`, and `makemigrations --check` (no model change without a migration)
3. `migrate` and `seed_demo_data` on a fresh database, then `verify_constraints`
4. the test suite (`manage.py test connect`)
5. `check --deploy` and `collectstatic` with production settings
6. a smoke test that boots the production build and checks the status and
   Content-Type of 20 URLs, plus the hashed stylesheet's `immutable` cache header

The workflow generates a throwaway `SECRET_KEY` for each run, so no repository
secret is needed. To run it on `main` after merging, change the branch in its
`on: push: branches:` line.

---

## Environment variables

Copy `.env.example` → `.env`. `.env` is gitignored and must never be committed.

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django signing key. Required. |
| `DJANGO_SETTINGS_MODULE` | Which settings module to load. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated. Required in production. |
| `DJANGO_SECURE_SSL` | `1` behind TLS: HSTS, SSL redirect, secure cookies. |
| `MAPS_API_KEY` | Placeholder for the Screen 8 campus map. Dummy value. |

---

## URL map

| Path | Name | View | Added |
|---|---|---|---|
| `/` | `connect:home` | FBV, `render()` | A2 |
| `/students/` | `connect:student-list` | Generic CBV (`ListView`) | A2 |
| `/students/<pk>/` | `connect:student-detail` | Generic CBV (`DetailView`) | A2 |
| `/search/` | `connect:student-search` | Base CBV (`View`), GET + POST | A3 |
| `/matches/` | `connect:match-list` | FBV, `render()` | A2 |
| `/matches/<pk>/` | `connect:match-detail` | Generic CBV (`DetailView`) | A3 |
| `/locations/` | `connect:location-list` | Base CBV (`View`), GET + POST | A2, POST in A3 |
| `/locations/<pk>/` | `connect:location-detail` | Generic CBV (`DetailView`) | A3 |
| `/feedback/summary/` | `connect:feedback-summary` | FBV, `HttpResponse` | A2 |
| `/insights/` | `connect:insights` | FBV, `render()` | A3 |
| `/insights/students-by-college.png` | `connect:chart-students-by-college` | FBV, `image/png` | A3 |
| `/insights/interest-categories.png` | `connect:chart-interest-categories` | FBV, `image/png` | A3 |
| `/api/` | `connect:api-docs` | FBV, `render()` | A3 |
| `/api/locations/` | `connect:api-locations` | Base CBV, `JsonResponse` | A3 |
| `/api/matches/` | `connect:api-matches` | FBV, `JsonResponse` | A3 |
| `/api/locations.txt` | `connect:api-locations-text` | FBV, `HttpResponse` (text/plain) | A3 |
| `/admin/` | — | Django Admin | A1 |

Every route is named and namespaced under `connect`, so templates reverse them
with `{% url 'connect:match-list' %}` rather than hard-coding paths.

---

## Project layout

```
13_QuadConnect/
├── manage.py                     defaults to development settings
├── requirements.txt              Django, python-dotenv, WhiteNoise, Matplotlib
├── ruff.toml                     lint rules, shared by CI and local runs
├── .github/workflows/deploy.yml  CI: the one "Deploy / test" check
├── .env.example                  committed; copy to .env
├── static/                       site-wide static files ({% static %})
│   ├── css/quadconnect.css       the whole design
│   ├── img/logo.svg              header logo and favicon
│   └── fonts/                    Inter (SIL Open Font License)
├── docs/
│   ├── wireframes/v1/            9 screens + flow, exported as PNG
│   ├── branching_strategy/       diagram.png + branching.md
│   ├── notes/notes.txt           weekly log, view register, P1-A3 answers
│   ├── build_tasks/              per-developer build instructions (A2)
│   ├── screenshots/              A2 evidence; p1-a3/ for this assignment
│   ├── er_diagram.pdf
│   └── data_model_notes.md       why each model and on_delete exists
├── quadconnect/
│   ├── settings/
│   │   ├── base.py               shared; reads .env; static + WhiteNoise
│   │   ├── development.py        DEBUG=True
│   │   └── production.py         DEBUG=False, security headers, hashed static
│   ├── urls.py  wsgi.py  asgi.py
└── connect/                      the one domain app
    ├── models.py                 8 models; get_absolute_url() on 3
    ├── views.py                  pages, detail views, search, venue suggestions
    ├── forms.py                  search, NetID lookup, venue suggestion
    ├── charts.py                 Matplotlib charts and the Insights page
    ├── api.py                    JSON API and its docs page
    ├── tests.py                  45 tests, one class per P1-A3 section
    ├── urls.py                   all routes named
    ├── admin.py                  all 8 models registered, with inlines
    ├── templates/connect/        base.html, shared entity_list.html, pages
    └── management/commands/
        ├── seed_demo_data.py     idempotent sample data
        └── verify_constraints.py proves constraints and on_delete rules
```

---

## Data model

Eight models in `connect/models.py`, each mapping to a screen in the
wireframes. Full rationale — every field, every `on_delete`, every constraint —
is in [`docs/data_model_notes.md`](docs/data_model_notes.md); the diagram is
[`docs/er_diagram.pdf`](docs/er_diagram.pdf).

```
auth.User 1─1 StudentProfile 1─N AvailabilitySlot
                   │ 1
                   N ProfileInterest N─1 Interest
                   │                      │ (SET_NULL, activities only)
                   │ (PROTECT)            │
                   N                      │
            MatchParticipant N─1 Match ───┘
                   │ 1              │ N
                   1                1
        ExperienceFeedback    CampusLocation
```

Verify the constraints and delete rules at any time:

```bash
python manage.py verify_constraints     # 11/11 checks
```

Each check runs inside a transaction that is rolled back, so it never mutates
the database.

---

## Contributing

Read [`docs/branching_strategy/branching.md`](docs/branching_strategy/branching.md)
first. In short: branch from `main`, keep each change in its own section of
`views.py`, commit in small conventional steps (`feat:`, `fix:`, `docs:`), run
`ruff check .` and `python manage.py test connect` before pushing, and merge
one branch at a time.

```bash
git switch main && git pull
git switch -c feature/<area>
# … work, commit in small meaningful steps …
git push -u origin feature/<area>
```

Per-developer build instructions from P1-A2 live in
[`docs/build_tasks/`](docs/build_tasks/).

---

## Tech

Django 5.2.17 · Python 3.11 · SQLite · `python-dotenv` · WhiteNoise 6.12 ·
Matplotlib 3.11. No JavaScript framework, no CSS framework, no build step:
server-rendered Django templates and one stylesheet.
