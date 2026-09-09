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
git clone https://github.com/<owner>/13_QuadConnect.git
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

Open <http://127.0.0.1:8000/>.

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

## Running in development vs production

Settings are split into a package. Pick an environment with
`DJANGO_SETTINGS_MODULE`.

| | Module | `DEBUG` | `ALLOWED_HOSTS` |
|---|---|---|---|
| Development | `quadconnect.settings.development` | `True` | localhost, 127.0.0.1 |
| Production | `quadconnect.settings.production` | `False` | **required** from `.env` |

`manage.py` defaults to development; `wsgi.py` and `asgi.py` default to
production, so a real deployment cannot accidentally boot with `DEBUG=True`.

```bash
# development (default)
python manage.py runserver

# production settings locally
DJANGO_SETTINGS_MODULE=quadconnect.settings.production python manage.py runserver

# production deployment checklist
DJANGO_SETTINGS_MODULE=quadconnect.settings.production \
  python manage.py check --deploy
```

Production **fails fast**: if `DJANGO_ALLOWED_HOSTS` is unset it raises at
startup rather than silently serving any `Host` header. Set
`DJANGO_SECURE_SSL=1` behind real TLS to switch on HSTS, the SSL redirect and
secure cookies — with that flag, `check --deploy` reports zero issues.

All CSS is inline in `base.html`, so production mode renders correctly without
`collectstatic`. When real static assets arrive, add WhiteNoise at the same
time.

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

| Path | Name | View kind | Owner |
|---|---|---|---|
| `/` | `connect:home` | dashboard | shared |
| `/students/` | `connect:student-list` | Generic CBV (`ListView`) | Kritika |
| `/students/<pk>/` | `connect:student-detail` | Generic CBV (`DetailView`) | Kritika |
| `/matches/` | `connect:match-list` | FBV using `render()` | Manojkumar |
| `/locations/` | `connect:location-list` | Base CBV (`View`) | Prathamesh |
| `/feedback/summary/` | `connect:feedback-summary` | FBV using `HttpResponse` | Dhruv |
| `/admin/` | — | Django Admin | — |

Every route is named and namespaced under `connect`, so templates reverse them
with `{% url 'connect:match-list' %}` rather than hard-coding paths.

---

## Project layout

```
13_QuadConnect/
├── manage.py                     defaults to development settings
├── requirements.txt
├── .env.example                  committed; copy to .env
├── docs/
│   ├── wireframes/v1/            9 screens + flow, exported as PNG
│   ├── branching_strategy/       diagram.png + branching.md
│   ├── notes/notes.txt           weekly log, view register, reflection
│   ├── build_tasks/              per-developer build instructions
│   ├── screenshots/              browser evidence
│   ├── er_diagram.pdf
│   └── data_model_notes.md       why each model and on_delete exists
├── quadconnect/
│   ├── settings/
│   │   ├── base.py               shared; reads .env
│   │   ├── development.py        DEBUG=True
│   │   └── production.py         DEBUG=False + security headers
│   ├── urls.py  wsgi.py  asgi.py
└── connect/                      the one domain app
    ├── models.py                 8 models
    ├── views.py                  divided into one section per owner
    ├── urls.py                   all routes named
    ├── admin.py                  all 8 models registered, with inlines
    ├── templates/connect/
    │   ├── base.html             {% block title %} / {% block content %}
    │   └── entity_list.html      shared list template, model-agnostic
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
first. In short: branch from `main`, stay inside your own section of
`views.py`, never edit `base.html`, and merge one branch at a time.

```bash
git switch main && git pull
git switch -c feature/<area>-views
# … work, commit in small meaningful steps …
git push -u origin feature/<area>-views
```

Per-developer build instructions live in
[`docs/build_tasks/`](docs/build_tasks/).

---

## Tech

Django 5.2.17 · Python 3.11 · SQLite · `python-dotenv`.
No JavaScript framework, no CSS framework, no build step — templates are
server-rendered Django templates with inline CSS.
