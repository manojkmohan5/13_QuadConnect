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

**Live site:** <https://manojkmohan43.pythonanywhere.com/> (PythonAnywhere, user `manojkmohan43`).

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

Open <http://127.0.0.1:8000/>, and log in as `tester` (see [Admin](#admin))
or sign up. Run the test suite with `python manage.py test connect` (104
tests).

The first command after installing pauses for a while (up to a minute on
Windows) while Matplotlib builds its font cache. That happens once.

`db.sqlite3` **is committed**, because P1-A4 deploys it as-is. It holds only the
seed data (`migrate`, then `seed_demo_data`, on an empty file): no login
sessions, no admin history. So after cloning, `migrate` and `seed_demo_data`
change nothing, and the site works straight away. If a local change dirties
it, rebuild it rather than committing the change:

```bash
rm db.sqlite3 && python manage.py migrate && python manage.py seed_demo_data
```

### Admin

```bash
python manage.py createsuperuser
```

The seed data also ships two superusers, both with password `uiuc12345`:
`mohitg2` and `tester`. (P1-A1 named a different one in two places, so both
exist.)

---

## P1-A5 features

Built on `feature/p1-a5`, cut from `main` after P1-A4. Tests are in
[`connect/tests_a5.py`](connect/tests_a5.py). The public API, its Vega-Lite
chart and its three other uses are written up in
[`docs/a5/README.md`](docs/a5/README.md), with screenshots in
[`docs/screenshots/p1-a5/`](docs/screenshots/p1-a5/).

### Part 1: logins and private pages

Accounts use [django-allauth](https://docs.allauth.org/) on top of Django's
own `auth` app.

- **Pages.** `/accounts/login/`, `/accounts/signup/` and `/accounts/logout/`
  use the site's own templates
  ([`templates/account/`](templates/account/)), not allauth's defaults.
  - Log in takes a username or an email address.
  - Sign up asks for a username, an email address and the password twice.
  - Log out is a button in the header that sends a POST, so a link or an
    image on another page cannot sign anyone out.
- **Settings** ([`quadconnect/settings/base.py`](quadconnect/settings/base.py)):
  - `LOGIN_URL = "account_login"`;
  - `LOGIN_REDIRECT_URL = "connect:home"`;
  - `LOGOUT_REDIRECT_URL = "connect:home"`;
  - allauth's `AuthenticationBackend` next to Django's `ModelBackend`.

  There is no mail server, so addresses are not verified by email, and the
  login form has no "Forgot your password?" link. Staff reset passwords in
  Django Admin.
- **Private by default.** Django's `LoginRequiredMiddleware`, extended in
  [`connect/middleware.py`](connect/middleware.py), protects every view that
  is not marked `@login_not_required`. Only the landing page, the privacy
  page, the sign-in pages and `/api/summary/` are marked. A new view is
  private unless someone opens it on purpose.
  - A page sends the visitor to the login page, then back to that page
    (`?next=`).
  - An API endpoint answers `401` with JSON instead, because a program cannot
    fill in a login form.
- **Navigation.** Signed out, the header shows only Home, Log in and Sign up,
  and the home page describes the product instead of showing student data.
  Signed in, it shows every section, "Signed in as *username*", and Log out.

| Signed out, a request for | gets |
|---|---|
| `/`, `/privacy/`, `/accounts/login/`, `/accounts/signup/` | `200` |
| `/api/summary/` | `200`, JSON |
| any other page | `302` to `/accounts/login/?next=<that page>` |
| any other `/api/` endpoint | `401`, JSON with a link to the login page |

### Part 2: Continue with Google

allauth's Google provider puts **Continue with Google** on the login and
sign-up pages.

- The button submits a POST form with a CSRF token, and the sign-in uses
  PKCE.
- A Google account whose email address already belongs to an account signs
  in to that account. Any other Google account gets a new one.
- Settings: `SOCIALACCOUNT_PROVIDERS` and the two `SOCIALACCOUNT_EMAIL_*`
  lines in `base.py`.

The OAuth client's keys come only from the environment: `GOOGLE_CLIENT_ID`
and `GOOGLE_CLIENT_SECRET` in `.env`. They are never stored in the database or
the repository. Without them the button is hidden, and password login works as
before.

QuadConnect's client lives in the Google Cloud project **QuadConnect**. It
was created on 2026-10-09 and is published (**In production**), so any Google
account can sign in. To set up a client from scratch, in the Google Cloud
console:

1. Create a project.
2. On **Google Auth Platform**, set up the consent screen as **External**.
3. Under **Clients**, create a client of type **Web application**. Add these
   **Authorized redirect URIs**:
   - `https://manojkmohan43.pythonanywhere.com/accounts/google/login/callback/`
   - `http://127.0.0.1:8001/accounts/google/login/callback/`
   - `http://localhost:8001/accounts/google/login/callback/`

   For a local run on another port, add the same two local addresses with
   that port.
4. On **Branding**, add the application home page,
   `https://manojkmohan43.pythonanywhere.com/`, and the privacy policy link,
   `https://manojkmohan43.pythonanywhere.com/privacy/`. Google will not
   publish an app without a privacy policy, and its sign-in screen links to
   it.
5. On **Audience**, click **Publish app**. Until it is published, only the
   test users listed there can sign in. With only the name, email and
   picture asked for, Google needs no review.
6. Put the client ID and secret in `.env`, and restart the server.

### Part 3: the public API

`GET /api/summary/` is the one endpoint anyone can use: no login, any origin
(`Access-Control-Allow-Origin: *`), and JSON built from the database on every
request. It returns how many verified students picked each interest, and
nothing about any one student. [`docs/a5/README.md`](docs/a5/README.md)
covers the rest:

- the Vega-Lite chart built on it in the editor
  ([`docs/a5/group-13-vega-lite-API-demo.txt`](docs/a5/group-13-vega-lite-API-demo.txt));
- three other uses: a command-line report, a Jupyter notebook and a
  refreshable Excel workbook, each with its code, a screenshot and what it
  found.

---

## P1-A4 features

Built on `feature/p1-a4`, cut from `main` after P1-A3. Screenshots are in
[`docs/screenshots/p1-a4/`](docs/screenshots/p1-a4/) and tests in
[`connect/tests_a4.py`](connect/tests_a4.py), one class per part. No login
was added: authentication comes in P1-A5.

### Part 1: internal API and Vega-Lite charts

**API.** Two GET endpoints in [`connect/api.py`](connect/api.py) return
chart-ready JSON built from the models:

| Endpoint | Returns |
|---|---|
| `GET /api/summary/` | verified students per interest, most picked first (a name used in two categories, like Food, gets its type added): `[{"category": "Food", "count": 4, "type": "Hobby / Interest"}, ...]` |
| `GET /api/summary/matches-per-week/` | matches in each weekly cycle, oldest first: `{"records": [{"date": "2026-07-13", "count": 1, "participants": 2}, ...]}`; a week with no matches is listed with 0 |

Every JSON endpoint sent `Access-Control-Allow-Origin: *`, so the Vega-Lite
editor, or a classmate's chart on another site, could read it. Since P1-A5
only `/api/summary/` does, and every other endpoint needs a login.

**Charts.** Two Vega-Lite v6 specs live in [`connect/specs/`](connect/specs/):
a bar chart of students per interest
([`chart1_bar.vl.json`](connect/specs/chart1_bar.vl.json)) and a line chart of
matches each week ([`chart2_line.vl.json`](connect/specs/chart2_line.vl.json)).
Both load their rows with `"data": {"url": "/api/summary/..."}` and hold no
inline data. Both run in the Vega-Lite editor against the local server
(screenshots 06 and 07).

- **On the site:** `/insights/` shows them as Figures 3 and 4. vega-embed
  draws them in the browser from self-hosted copies of Vega 6.4, Vega-Lite 6.4
  and vega-embed 7.3 ([`static/vendor/vega/`](static/vendor/vega/)). Each has
  a caption, alt text and a table of the same numbers. Without JavaScript the
  server-drawn image shows instead. vega-embed's `...` menu and hover
  tooltips are switched off: the menu's downloads work only with a mouse,
  and the tooltips cannot be dismissed (WCAG 2.1.1 and 1.4.13). The PNG/JPG
  link and the table under each chart give everyone the same.
- **As images:** `/vega-lite/chart1.png` and `/vega-lite/chart2.jpg` (either
  chart works in either format) draw the same spec on the server with
  vl-convert ([`connect/vega_charts.py`](connect/vega_charts.py)). The view
  hands vl-convert the API's rows instead of letting it fetch `data.url`: a
  server that requests its own URL while answering can stall on a host with
  one worker. A render takes about a second, so each image is cached for a
  minute.
- **The spec:** `/vega-lite/chart1.vl.json` serves the spec with `data.url`
  made absolute for whichever host serves it, so it opens in the editor as it
  is, locally now and from the deployed site later.

To open a chart in the editor, paste the JSON from `/vega-lite/chart1.vl.json`
into <https://vega.github.io/editor/>. Chrome may ask before a public page
reads from `127.0.0.1` ("local network access"); allow it, or use the
deployed site.

The files in `connect/specs/` use a relative `data.url`, so one spec works on
every host. Pasted into the editor as they are, they would look for the data
on vega.github.io. To submit or share a spec, use the copy the deployed site
serves, which carries the deployed API's full address:
<https://manojkmohan43.pythonanywhere.com/vega-lite/chart1.vl.json> and
<https://manojkmohan43.pythonanywhere.com/vega-lite/chart2.vl.json>. Screenshots
[18](docs/screenshots/p1-a4/18_vega_editor_deployed_bar.png) and
[19](docs/screenshots/p1-a4/19_vega_editor_deployed_line.png) show both running in the editor
on the deployed API.

Since P1-A5 the spec URLs need a login, and so does the line chart's data.
The bar chart's data is the public API, so that spec still draws in the
editor. The chart built for the editor is now
[`docs/a5/group-13-vega-lite-API-demo.txt`](docs/a5/group-13-vega-lite-API-demo.txt).

Screenshots: [01](docs/screenshots/p1-a4/01_vega_bar_chart.png) bar chart on the site,
[02](docs/screenshots/p1-a4/02_vega_line_chart.png) line chart,
[03](docs/screenshots/p1-a4/03_chart1_png.png) `chart1.png`, [04](docs/screenshots/p1-a4/04_chart2_jpg.png) `chart2.jpg`,
[05](docs/screenshots/p1-a4/05_chart1_spec.png) the served spec,
[06](docs/screenshots/p1-a4/06_vega_editor_bar.png) and [07](docs/screenshots/p1-a4/07_vega_editor_line.png) both specs
in the Vega-Lite editor, [08](docs/screenshots/p1-a4/08_api_summary.png) and
[09](docs/screenshots/p1-a4/09_api_matches_per_week.png) the two endpoints.

### Part 2: external API (icebreakers from Open Trivia DB)

`GET /api/icebreakers/?match=<id>` returns five trivia questions picked for one
match, and `/matches/<id>/icebreakers/` shows the same result as a page,
linked from every match page. Code:
[`connect/icebreakers.py`](connect/icebreakers.py).
[Open Trivia DB](https://opentdb.com/) is free and needs no key.

1. **Our data:** which interests the match's members picked. Members who
   declined the match are left out.
2. **Analytics:** each interest maps to a trivia category, and each category
   scores the number of members it covers. The topic is the category shared
   by the most members (at least two; ties are broken at random). If nothing
   is shared, the topic is General Knowledge.
3. **External data:** `requests.get("https://opentdb.com/api.php",
   params={"amount": 5, "category": ..., "difficulty": "easy", "type": "multiple"},
   timeout=5)`, then `raise_for_status()`.
4. **Processing:** HTML entities are decoded (`Pel&eacute;` becomes `Pelé`),
   and each question's choices are sorted, so the answer is not always in the
   same place.

The response puts both sides together: the member counts per interest, the
topic they picked and why, and the questions. Nothing from Open Trivia DB is
saved: a topic's questions stay in memory for 5 seconds, Open Trivia DB's own
limit, so a quick reload reuses them instead of being turned away. Members
appear only as counts.

| Situation | Status |
|---|---|
| `match` missing or not a whole number | `400`, with how to fix it |
| no match has that id | `404` |
| Open Trivia DB takes more than 5 seconds | `504` |
| Open Trivia DB is busy: it allows one request per 5 seconds from each address (HTTP 429, or `response_code` 5) | `503` with `Retry-After: 5` |
| any other failure: no connection, an HTTP error, a reply we cannot read, no questions | `502` |

Each error comes back as JSON with an `error` message, and is logged. The
page shows the message and still lists the group's interests. The tests
replace `requests.get`, so they never use the network.
Screenshots: [10](docs/screenshots/p1-a4/10_icebreakers_page.png) the page,
[11](docs/screenshots/p1-a4/11_icebreakers_api_counts.png) and [12](docs/screenshots/p1-a4/12_icebreakers_api_questions.png)
the API (counts, then topic and questions), [13](docs/screenshots/p1-a4/13_icebreakers_api_400.png)
a bad parameter, [14](docs/screenshots/p1-a4/14_icebreakers_busy.png) the busy case on the page.

### Part 3: exports and reports

Code: [`connect/reports.py`](connect/reports.py).

- **`/export/students.csv`:** `text/csv`, saved as
  `students_YYYY-MM-DD_HH-MM.csv` in local time. A header row, then one row
  per student profile ordered by name: NetID, name, college, department,
  matching preferences, interests, number of matches, verified, and sign-up
  date. The email address is left out. The file starts with a UTF-8 byte
  order mark, so Excel shows accented names correctly. A cell that starts like a formula
  (`=`, `+`, `-`, `@`) gets a leading apostrophe, so a spreadsheet shows it as
  text instead of running it.
- **`/export/students.json`:** the same rows as
  `{"generated_at": "<ISO timestamp>", "record_count": 8, "students": [...]}`,
  from `JsonResponse(..., json_dumps_params={"indent": 2})`, saved as
  `students_YYYY-MM-DD_HH-MM.json`.
- **`/reports/`** (`reports.html`, in the nav): students per college split by
  Friend and Squad, and matches per venue split into all, completed and
  upcoming. Each table has headers, a totals row and an `{% empty %}` row.
  Above them are a totals line for the site and the **Download CSV** and
  **Download JSON** buttons. The student list links to both files too.

Screenshots: [15](docs/screenshots/p1-a4/15_reports_page.png) Reports,
[16](docs/screenshots/p1-a4/16_downloaded_files.png) the files saved by clicking the two buttons.

### Part 4: static files and deployment prerequisites

- **Static files:** `STATIC_URL = "/static/"`,
  `STATICFILES_DIRS = [BASE_DIR / "static"]` and
  `STATIC_ROOT = BASE_DIR / "staticfiles"` (gitignored). `base.html` loads the
  stylesheet with `{% load static %}` and `{% static %}`, so every page is
  styled; screenshots 10 and 15 show two. The site was run under both
  settings: development with `runserver`, and production after
  `collectstatic` ([17](docs/screenshots/p1-a4/17_production_insights.png): `DEBUG=False`, hashed
  file names).
- **`requirements.txt`:** `pip freeze` from a clean virtualenv: 23 pinned
  packages and nothing else.
- **`.gitignore`:** `.env`, virtualenvs, `__pycache__/` and `*.pyc`,
  `staticfiles/`, logs, and editor and OS files. `db.sqlite3` is committed,
  with seed data only (see [Quick start](#quick-start)); only its `-journal`
  file is ignored.
- **Size:** the installed packages take 318 MB on Linux (measured in CI;
  vl-convert, Matplotlib and NumPy are most of it), and the repository about
  25 MB with its history. CI fails if the packages ever pass 400 MB, which
  keeps the whole site under a 512 MB quota.
- **Clean-up:** ruff passes (no unused imports), there are no `print()`
  calls, every `/api/` route sits in one block of `urls.py`, every template
  extends `base.html`, and the CI smoke test requests every route.

**Deployed (Parts 4.3 and 4.4):** <https://manojkmohan43.pythonanywhere.com/>, on PythonAnywhere's free
plan, user `manojkmohan43`, with `mohitg27` set as teacher. The steps follow
the course:

- the repository cloned to `/home/manojkmohan43/13_QuadConnect`;
- the virtualenv `/home/manojkmohan43/.virtualenvs/myenv-django` (Python
  3.12), with `requirements.txt` installed;
- `collectstatic` run with production settings;
- on the Web tab: the WSGI file loading `quadconnect.settings.production`, the
  virtualenv above, the static mapping `/static/` to
  `/home/manojkmohan43/13_QuadConnect/staticfiles`, and HTTPS forced.

The committed `db.sqlite3` is used as it is, so the optional steps 6 and 7
(migrate, create the instructor account) were not needed: `tester` /
`uiuc12345` logs in to `/admin/`. Every route answers on the live site, the
icebreakers reach Open Trivia DB, and both specs run in the Vega-Lite editor
from the deployed API ([18](docs/screenshots/p1-a4/18_vega_editor_deployed_bar.png),
[19](docs/screenshots/p1-a4/19_vega_editor_deployed_line.png)).

---

## P1-A3 features

Everything below was added in P1-A3 and merged into `main` on 2026-09-28
(PR #6). Each section of the assignment maps to one area of the code, and each
has screenshots in
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
(`quadconnect.css` → `quadconnect.<hash>.css`, for example
`quadconnect.9d7082daf6a5.css` in screenshots 08 and 09) and records the mapping in
a manifest; `{% static %}` looks names up there. WhiteNoise serves hashed files
with `Cache-Control: max-age=315360000, public, immutable`, so browsers cache
them for good, and any edit produces a new name, so no browser can keep a stale
stylesheet after a deploy. `staticfiles/` is gitignored.

Production **fails fast**: if `DJANGO_ALLOWED_HOSTS` is unset it raises at
startup rather than silently serving any `Host` header. Set
`DJANGO_SECURE_SSL=1` behind real TLS to switch on HSTS, the SSL redirect and
secure cookies — with that flag, `check --deploy` reports zero issues.

---

## Deploying

The site runs on PythonAnywhere (see P1-A4, Part 4). These are the steps it
followed, and what any other host would need:

1. Python 3.11 or newer, and the code:
   `git clone https://github.com/manojkmohan5/13_QuadConnect.git`.
2. A virtualenv with the pinned packages. On a host with a small disk quota,
   skip pip's cache, which would otherwise keep a second copy of every
   package:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install --no-cache-dir -r requirements.txt
   ```

3. Environment variables, in `.env` or the host's settings:
   `DJANGO_SECRET_KEY` (a new one), `DJANGO_SETTINGS_MODULE=quadconnect.settings.production`,
   `DJANGO_ALLOWED_HOSTS=<the site's domain>`, and `DJANGO_SECURE_SSL=1` once
   the site is served over HTTPS. That flag also makes Django trust the host's
   `X-Forwarded-Proto` header. Without it, Django thinks requests arrive over
   `http`, so the chart specs would send an HTTPS page to `http://` data,
   which browsers block, and Google sign-in would send Google an `http://`
   callback address that is not registered. For Google sign-in, also set
   `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (see
   [P1-A5, Part 2](#part-2-continue-with-google)).
4. `python manage.py collectstatic --noinput`, then
   `python manage.py check --deploy`.
5. The WSGI application `quadconnect.wsgi:application`, which defaults to the
   production settings. If the host serves static files itself, map `/static/`
   to `staticfiles/`; if not, WhiteNoise serves them.
6. Nothing for the database: the committed `db.sqlite3` is ready, `migrate`
   finds nothing to do, and the course accounts `tester` and `mohitg2`
   (password `uiuc12345`) are in it.

Two things to check on the host:

- **Outbound HTTPS to `opentdb.com`**, for the icebreakers, and to
  `*.googleapis.com`, where Google sign-in checks the code Google sends back.
  PythonAnywhere's free plan only reaches sites on its allowlist, and both
  are on it. Without opentdb.com, the icebreakers page says the questions
  could not be loaded, and the rest of the site works.
- **Memory:** a worker uses about 90 MB with the site loaded, and about 170 MB
  once it has drawn chart images, because vl-convert's renderer starts with
  the first image (measured on Windows). That first image takes a few
  seconds; later ones take about one.

After deploying, `/vega-lite/chart1.vl.json` points `data.url` at the deployed
API by itself, so the spec can be pasted into the Vega-Lite editor as it is.

**Updating the PythonAnywhere site.** In a Bash console there:

```bash
cd ~/13_QuadConnect && git pull
workon myenv-django
pip install --no-cache-dir -r requirements.txt   # when requirements.txt changed
export DJANGO_SETTINGS_MODULE=quadconnect.settings.production
python manage.py migrate                         # when a migration was added
python manage.py collectstatic --noinput
```

Then press **Reload** on the Web tab. The live `db.sqlite3` changes as people
use the site (admin logins, venue suggestions). Git on the server ignores
those changes (`git update-index --skip-worktree db.sqlite3`), so `git pull`
still works. Never copy the live file back into the repository. A free web
app also has to be extended on the Web tab once a month.

---

## Continuous integration

Every push to `feature/p1-a5`, the branch P1-A5 is built on, runs one GitHub
Actions check, **Deploy / test (push)**, defined in
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml). Its single job
runs, in order:

1. `pip install -r requirements.txt`, then a check that the installed
   packages stay under 400 MB, so the site fits a 512 MB host
2. `ruff check .` (rules in [`ruff.toml`](ruff.toml))
3. `manage.py check`, and `makemigrations --check` (no model change without a migration)
4. checks on the committed `db.sqlite3`: fully migrated, and seed data only
   (no login sessions, no admin history, no unapproved venues, no password
   other than the two course accounts', no stored OAuth client, and the
   `tester` login works)
5. `verify_constraints`, then the test suite (`manage.py test connect`)
6. `check --deploy` and `collectstatic` with production settings
7. a smoke test that boots the production build:
   - signed out, 14 URLs: the public ones open, pages redirect to the login
     page, and APIs answer `401`;
   - it then logs in as `tester` through the login form, as a browser
     would;
   - signed in, it checks the status and Content-Type of 32 URLs, at least
     one for every route;
   - it also checks the hashed stylesheet's `immutable` cache header and the
     four hashed scripts the Insights page loads.

The workflow generates a throwaway `SECRET_KEY` for each run, so no repository
secret is needed.

`main` receives code only by merging the assignment's branch through a pull
request, after the branch head has passed the check. P1-A3 reached `main` this
way in PR #6 (2026-09-28), from `feature/p1-a3`, and P1-A4 in PR #9
(2026-10-05), from `feature/p1-a4`. The
workflow does not run on `main` itself, so `main`'s merge commits show no check
of their own; to run it there too, add `main` to its `on: push: branches:` line.

---

## Environment variables

Copy `.env.example` → `.env`. `.env` is gitignored and must never be committed.

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django signing key. Required. |
| `DJANGO_SETTINGS_MODULE` | Which settings module to load. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated. Required in production. |
| `DJANGO_SECURE_SSL` | `1` behind TLS: HSTS, SSL redirect, secure cookies. |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID. Optional: without it, the "Continue with Google" button is hidden. |
| `GOOGLE_CLIENT_SECRET` | That client's secret. Required when `GOOGLE_CLIENT_ID` is set. |
| `MAPS_API_KEY` | Placeholder for the Screen 8 campus map. Dummy value. |

---

## URL map

| Path | Name | View | Added |
|---|---|---|---|
| `/` | `connect:home` | FBV, `render()` | A2 |
| `/privacy/` | `connect:privacy` | FBV, `render()`; public | A5 |
| `/students/` | `connect:student-list` | Generic CBV (`ListView`) | A2 |
| `/students/<pk>/` | `connect:student-detail` | Generic CBV (`DetailView`) | A2 |
| `/search/` | `connect:student-search` | Base CBV (`View`), GET + POST | A3 |
| `/matches/` | `connect:match-list` | FBV, `render()` | A2 |
| `/matches/<pk>/` | `connect:match-detail` | Generic CBV (`DetailView`) | A3 |
| `/matches/<pk>/icebreakers/` | `connect:match-icebreakers` | FBV, `render()`; calls Open Trivia DB | A4 |
| `/locations/` | `connect:location-list` | Base CBV (`View`), GET + POST | A2, POST in A3 |
| `/locations/<pk>/` | `connect:location-detail` | Generic CBV (`DetailView`) | A3 |
| `/feedback/summary/` | `connect:feedback-summary` | FBV, `HttpResponse` | A2 |
| `/insights/` | `connect:insights` | FBV, `render()` | A3 |
| `/insights/students-by-college.png` | `connect:chart-students-by-college` | FBV, `image/png` | A3 |
| `/insights/interest-categories.png` | `connect:chart-interest-categories` | FBV, `image/png` | A3 |
| `/reports/` | `connect:reports` | FBV, `render()` | A4 |
| `/export/students.csv` | `connect:export-students-csv` | FBV, `HttpResponse` (text/csv, attachment) | A4 |
| `/export/students.json` | `connect:export-students-json` | FBV, `JsonResponse` (attachment) | A4 |
| `/api/` | `connect:api-docs` | FBV, `render()` | A3 |
| `/api/locations/` | `connect:api-locations` | Base CBV, `JsonResponse` | A3 |
| `/api/matches/` | `connect:api-matches` | FBV, `JsonResponse` | A3 |
| `/api/locations.txt` | `connect:api-locations-text` | FBV, `HttpResponse` (text/plain) | A3 |
| `/api/summary/` | `connect:api-summary` | FBV, `JsonResponse` | A4 |
| `/api/summary/matches-per-week/` | `connect:api-summary-matches-per-week` | FBV, `JsonResponse` | A4 |
| `/api/icebreakers/` | `connect:api-icebreakers` | FBV, `JsonResponse`; calls Open Trivia DB | A4 |
| `/vega-lite/<chart>.vl.json` | `connect:vega-spec` | FBV, `JsonResponse` | A4 |
| `/vega-lite/<chart>.png`, `.jpg` | `connect:vega-image` | FBV, `image/png` or `image/jpeg` | A4 |
| `/accounts/login/` | `account_login` | django-allauth, template `account/login.html` | A5 |
| `/accounts/signup/` | `account_signup` | django-allauth, template `account/signup.html` | A5 |
| `/accounts/logout/` | `account_logout` | django-allauth, POST to log out | A5 |
| `/accounts/google/login/` | `google_login` | django-allauth, POST: sends the browser to Google | A5 |
| `/accounts/google/login/callback/` | `google_callback` | django-allauth: Google sends the browser back here | A5 |
| `/admin/` | — | Django Admin | A1 |

Every route of the app is named and namespaced under `connect`, so templates
reverse them with `{% url 'connect:match-list' %}` rather than hard-coding
paths. `/accounts/` holds the rest of allauth's pages too (password change,
connected accounts); the table lists the ones the site links to.

**Access (since P1-A5).** Every route needs a login except `/`, `/privacy/`,
`/api/summary/` and the sign-in pages under `/accounts/`. `/admin/` has its
own login, for staff.

---

## Project layout

```
13_QuadConnect/
├── manage.py                     defaults to development settings
├── requirements.txt              pip freeze: 29 pinned packages
├── db.sqlite3                    committed: seed data only (P1-A4 deploys it)
├── templates/                    site-wide templates
│   ├── account/                  login, sign-up and logout pages (allauth)
│   └── allauth/                  puts allauth's other pages in base.html
├── ruff.toml                     lint rules, shared by CI and local runs
├── .github/workflows/deploy.yml  CI: the one "Deploy / test" check
├── .env.example                  committed; copy to .env
├── static/                       site-wide static files ({% static %})
│   ├── css/quadconnect.css       the whole design
│   ├── img/logo.svg              header logo and favicon
│   ├── fonts/                    Inter (SIL Open Font License)
│   ├── js/charts.js              draws the Vega-Lite charts (vega-embed)
│   └── vendor/vega/              Vega, Vega-Lite, vega-embed (BSD-3-Clause)
├── docs/
│   ├── wireframes/v1/            9 screens + flow, exported as PNG
│   ├── branching_strategy/       diagram.png + branching.md
│   ├── notes/notes.txt           weekly log, view register, P1-A3 answers
│   ├── build_tasks/              per-developer build instructions (A2)
│   ├── screenshots/              A2 evidence; p1-a3/, p1-a4/ and p1-a5/
│   ├── a5/                       the public API's chart and its three other uses
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
    ├── forms.py                  search, NetID lookup, venue suggestion, login
    ├── middleware.py             login required everywhere; 401 for the API
    ├── charts.py                 Matplotlib charts and the Insights page
    ├── api.py                    JSON API, chart data, and the docs page
    ├── vega_charts.py            Vega-Lite specs and their PNG/JPG images
    ├── specs/                    the two Vega-Lite specs (.vl.json)
    ├── icebreakers.py            Open Trivia DB questions for a match
    ├── reports.py                reports page, CSV and JSON exports
    ├── tests.py                  45 tests, one class per P1-A3 section
    ├── tests_a4.py               42 tests, one class per P1-A4 part
    ├── tests_a5.py               17 tests: access, navigation, accounts, Google
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

Django 5.2.17 · Python 3.11 · SQLite · django-allauth 65.19 · `python-dotenv` · WhiteNoise 6.12 ·
Matplotlib 3.11 · Vega-Lite 6.4 (vega-embed in the browser, vl-convert on the
server) · `requests`. No JavaScript framework, no CSS framework, no build step:
server-rendered Django templates, one stylesheet, and one short script that
draws the Vega-Lite charts.
