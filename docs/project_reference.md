# QuadConnect — Project Reference

> Single source of truth. Read this before touching anything.
> Plain markdown - readable by the whole team and by any tooling.

### Why this file exists

It is the team's **accumulated memory**. Every assignment, every branch, every
decision that cost someone an hour ends up here, so that six weeks from now
nobody has to reverse-engineer why `MatchParticipant.profile` is `PROTECT` or
why there is no `settings.py`.

It grows as we work: each developer records their branch before merging, and
the person doing the merge folds those entries into a single history. The rule
is simple — **if you learned it the hard way, write it down here.**

This file is kept for our own reference and is **not part of any Canvas
submission**. That is deliberate: it can be blunt about what went wrong,
what we chose not to build, and where the shortcuts are.

---

## 0. CURRENT STATE — read this first

| | |
|---|---|
| **Repo** | `13_QuadConnect` |
| **Assignment in flight** | **P1-A2** — Fullstack Development + GitHub Secrets (30 pts) |
| **Last completed** | P1-A1 — Product + Data Models + UI/UX (35 pts) |
| **`main` status** | Scaffold complete and verified. Dev **and** prod both boot clean. |
| **What remains** | Four feature branches, one per developer. Then merge, screenshot, submit. |

`main` currently ships: split settings, `.env` handling, `base.html`, a shared
list template, a home dashboard, and **all four graded routes already named
and wired to owner-marked stub views**. The site is never broken: every nav
link resolves today, and each developer replaces exactly one stub.

### Status board — UPDATE YOUR ROW WHEN YOU FINISH

| Owner | Branch | View kind | Route | Status |
|---|---|---|---|---|
| Kritika Agrawal | `feature/profile-views` | Generic CBV | `/students/` | ⬜ NOT STARTED |
| Manojkumar Mohankumar | `feature/match-views` | FBV `render()` | `/matches/` | ✅ DONE — `match_list` with `?week=` filter, renders the shared list template |
| Prathamesh Mulay | `feature/location-views` | Base CBV | `/locations/` | ⬜ DONE - Locations |
| Dhruv Thaker | `feature/feedback-views` | FBV `HttpResponse` | `/feedback/summary/` | ⬜ NOT STARTED |

**Whoever completes a branch:** updating this file is
**Step 7 of that developer's build task** and a box on their Done
checklist. It is not optional and it is not housekeeping — it is how the team
keeps a memory. Before the final commit on their branch:

1. Change their row above to `DONE — <one-line summary of what shipped>`.
2. Replace their block in **§9 Work log** using the template documented there:
   what shipped, files added/changed, decisions that differ from the build
   task, gotchas for the next person, and what was verified.
3. Add any new gotcha to **§11 Traps**.

Keep edits confined to your own row and your own block — four people edit this
file. Git merges different lines cleanly but conflicts on the same line.

### Merge protocol — repo owner

Branches merge into `main` **one at a time**, never in parallel. After each
merge:

1. Keep the incoming work-log block as written by its author.
2. Flip that row on the status board if the author did not.
3. Append a short merge entry to §9 noting anything that only surfaced during
   integration — a conflict, a behaviour that broke when two branches met, a
   decision reversed.

When all four are merged, §9 is the complete story of P1-A2 and this file is
handed forward to the next assignment as-is.

---

## 1. Identity

| | |
|---|---|
| **Product** | QuadConnect: A Verified Campus Social Discovery Platform |
| **Course** | INFO 490 (`info_490_120268_265091`), Fall 2026, UIUC |
| **Team** | The Connectors · **Team 13** |
| **Prototype** | <https://trek-galaxy-20520998.figma.site/> |
| **Stack** | Django 5.2.17 · Python 3.11 · SQLite · `python-dotenv` |
| **Platform** | Windows 11, PowerShell + Git Bash |

No JavaScript framework, no CSS framework, no build step. Server-rendered
Django templates with inline CSS.

### Members and feature ownership

| Member | NetID | Email | Owns |
|---|---|---|---|
| Kritika Agrawal | kritika7 | kritika7@illinois.edu | Onboarding & profile (Screens 1–2) |
| Manojkumar Mohankumar | mm240 | mm240@illinois.edu | Matching engine (Screens 3, 6–7) |
| Prathamesh Mulay | pmulay2 | pmulay2@illinois.edu | Availability, scheduling, check-in (Screens 5, 8) |
| Dhruv Thaker | dthaker3 | dthaker3@illinois.edu | Social preferences & feedback (Screens 4, 9) |

**Name spelling is settled: "Agrawal", not "Agarwal."** Confirmed by the team.
Do not reintroduce it.

Papers list authors **alphabetically by surname**: Agrawal, Mohankumar, Mulay,
Thaker.

### Team norms

- Meetings: Tuesdays 10–11pm, Saturdays 11am–1pm
- Response time: within 24 hours
- Missed meeting: notify 2–3 hours ahead; read notes and post written status
  within 24 hours; two consecutive unexplained absences escalate to the TA

---

## 2. What the product is

A verified, student-only platform that helps UIUC students form real
friendships through **structured, in-person experiences**.

Core thesis: *the problem is not a lack of people to meet — it is finding
compatible people and a comfortable context in which to meet them.*

### What it deliberately is NOT

Every one of these is a decision, not an omission:

- **No endless messaging.** Matching exists to produce one scheduled meeting.
- **No swiping, no feed, no browsing.** Exactly one match per week.
- **No open sign-up.** UIUC SSO only; a closed community is the safety model.
- **No public profiles.** Identity is withheld until both sides accept.
- **No unilateral connections.** A lasting connection requires mutual opt-in.
- **No machine learning.** Matching is a deterministic weighted score over hard
  constraints plus soft signals. Never describe this project as using ML — the
  paper, the data model and the TCC must stay consistent.

### Five design principles

1. **Verified community** — institutional authentication gates participation.
2. **Intentional matching** — interests, preferences, availability, campus
   involvement; never random pairing.
3. **Offline-first** — technology exists to produce a real-world meeting.
4. **User control and safety** — approved public locations, check-in,
   reporting, private feedback.
5. **Feedback loop** — post-experience feedback improves future matching.

### Two connection types

- **Friend Connect** — one-to-one, weekly, in person.
- **Squad Connect** — small group of 4–8 students, weekly, in person.

---

## 3. The nine screens

| # | Screen | Purpose | Backed by |
|---|---|---|---|
| 1 | UIUC SSO Login | Verified student-only entry | `StudentProfile` |
| 2 | Interests & Hobbies | Hobbies, RSOs, college/dept, optional job | `Interest`, `ProfileInterest` |
| 3 | Choose Connection Type | Friend vs Squad | `StudentProfile.preferred_connection` |
| 4 | Social Preferences | Energy, style, environment, group, age, degree, RSO | `StudentProfile` |
| 5 | Availability | Weekend slots, activities, indoor/outdoor | `AvailabilitySlot` |
| 6 | Weekly Friend Match | The match + *why you matched* + suggested experience | `Match`, `MatchParticipant` |
| 7 | Squad Connect Match | Group of 4–8, shared interests, experience | `Match`, `MatchParticipant` |
| 8 | Meeting & Check-in | Location, arrival steps, QR + short code | `CampusLocation`, `MatchParticipant.checked_in_at` |
| 9 | Post-Experience Feedback | Rating, enjoyment, per-person stay-connected | `ExperienceFeedback` |

**Flow:** 1 → 2 → 3 → 4 → 5 → weekly matching cycle → (6 **or** 7) → 8 → 9 →
mutual connection. Screens 2–5 are a four-step wizard. Branching happens once,
at the match; both branches reconverge at check-in.

None of these screens are implemented yet. P1-A2 builds four *list* views over
the same models as a foundation.

### Interaction rules from the wireframes

- Chips are multi-select toggles with a live count.
- Primary buttons stay **disabled with an explanatory line** — never silently.
- Radios for single-choice, checkboxes for multi-choice, so control shape
  signals how many answers are allowed.
- On Screen 3 the entire card is the hit target.
- Screen 8 offers **two** check-in methods (QR + short code) so a dead battery
  cannot block attendance.
- Screen 9 requires only the star rating.
- The Screen 8 safety banner is persistent and not dismissible.

---

## 4. Repository layout

```
13_QuadConnect/                    <- repo root IS the Django project root
├── README.md                      setup, dev/prod, env vars, URL map
├── docs/project_reference.md                      this file
├── .gitignore                     .env on line 1
├── .env                           IGNORED — never committed
├── .env.example                   committed, placeholders only
├── requirements.txt               Django 5.2.17, python-dotenv
├── manage.py                      -> quadconnect.settings.development
├── db.sqlite3                     IGNORED — rebuild with seed_demo_data
├── docs/
│   ├── wireframes/
│   │   ├── v1/                    10 PNGs: 9 screens + flow
│   │   ├── QuadConnect_Wireframes.pdf
│   │   └── QuadConnect_Project_Idea_Description.pdf
│   ├── branching_strategy/        diagram.png + branching.md
│   ├── notes/notes.txt            weekly log, VIEW REGISTER, REFLECTION
│   ├── build_tasks/               one spec per developer + shared rules
│   ├── screenshots/               README.md manifest + 6 captures
│   ├── er_diagram.pdf
│   └── data_model_notes.md        why each model and on_delete exists
├── quadconnect/
│   ├── settings/
│   │   ├── base.py                shared; reads .env; BASE_DIR 3 levels up
│   │   ├── development.py         DEBUG=True
│   │   └── production.py          DEBUG=False + security headers
│   ├── urls.py                    /admin/ and '' -> connect.urls
│   ├── wsgi.py  asgi.py           -> quadconnect.settings.production
└── connect/
    ├── models.py                  8 models — FROZEN for P1-A2
    ├── views.py                   divided into one section per owner
    ├── urls.py                    every route named, namespace "connect"
    ├── admin.py                   all 8 registered, with inlines
    ├── migrations/0001_initial.py
    ├── templates/connect/
    │   ├── base.html              OWNED BY main — do not edit on a branch
    │   ├── entity_list.html       SHARED — model-agnostic list
    │   └── home.html
    └── management/commands/
        ├── seed_demo_data.py      idempotent
        └── verify_constraints.py  11 checks, all rolled back
```

### Naming rationale

- **`quadconnect`** (project) — the deployable product as a whole.
- **`connect`** (app) — the one core domain: the lifecycle that turns two
  verified students into a completed in-person experience. Chosen over `core`
  or `main` (say nothing) and over `matching` (describes only the middle,
  orphaning onboarding and feedback).

Future sibling apps as scope grows: `events`, `assistant`.

---

## 5. Settings and environment

Settings are a **package**, not a module. Pick one with
`DJANGO_SETTINGS_MODULE`.

| | Module | `DEBUG` | `ALLOWED_HOSTS` |
|---|---|---|---|
| Development | `quadconnect.settings.development` | `True` | localhost, 127.0.0.1 |
| Production | `quadconnect.settings.production` | `False` | **required** from env |

`manage.py` defaults to development; `wsgi.py`/`asgi.py` default to production,
so a real deployment cannot boot with `DEBUG=True`.

Production **fails fast**: unset `DJANGO_ALLOWED_HOSTS` raises `RuntimeError`
at startup rather than silently serving any `Host` header. With
`DJANGO_SECURE_SSL=1`, `check --deploy` reports **zero issues** (HSTS, SSL
redirect, secure cookies all switch on).

### `.env` keys

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Signing key. Required. Rotated when it left source. |
| `DJANGO_SETTINGS_MODULE` | Which settings module to load. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated. Required in production. |
| `DJANGO_SECURE_SSL` | `1` behind real TLS. |
| `MAPS_API_KEY` | Placeholder for the Screen 8 map. Dummy value. |

---

## 6. Data model — 8 models

All in `connect/models.py`. **Frozen for P1-A2** — do not add fields or
migrations. Every model has a class docstring, `Meta.ordering`, and `__str__`.

### Choice vocabularies

```python
ConnectionType      FRIEND | SQUAD
SocialEnergy        1 QUIET · 2 RESERVED · 3 BALANCED · 4 OUTGOING · 5 VERY_SOCIAL
ConversationStyle   CASUAL | DEEP | ACTIVITY
GroupPreference     ONE | SMALL | EITHER
Weekday             6 SATURDAY | 7 SUNDAY          (ISO numbering, Mon=1)
TimeBlock           10-12 | 12-14 | 14-16 | 16-18  (four 2-hour windows)
InterestCategory    HOBBY | RSO | ACTIVITY
MatchStatus         PROPOSED | CONFIRMED | COMPLETED | CANCELLED
ParticipantResponse PENDING | ACCEPTED | DECLINED
```

Always choices, never free text, so comparison needs no string normalisation.

### `StudentProfile`
SSO-verified student + every matching signal. Separate from `auth.User` so
authentication can be swapped for real Shibboleth SSO without touching
product data.

```
user  OneToOne -> auth.User  CASCADE UNIQUE   net_id CharField UNIQUE
illinois_email EmailField UNIQUE              full_name, college, department,
preferred_connection  ConnectionType          part_time_job  CharField
social_energy SocialEnergy                    conversation_style ConversationStyle
group_preference GroupPreference              prefers_same_age Boolean
prefers_shared_rso Boolean                    open_to_other_departments Boolean
interests M2M -> Interest through ProfileInterest
is_sso_verified Boolean  (False = out of the matching pool)
onboarding_completed_at DateTime null         created_at DateTime auto_now_add
Meta.ordering ["full_name","net_id"]   UC (net_id, illinois_email)
```

### `Interest`
Shared vocabulary behind the chip pickers, so "Gaming" means the same thing
for everyone and overlap is countable.

```
name CharField   category InterestCategory   is_active Boolean
Meta.ordering ["category","name"]   UC (name, category)
```
Per-category uniqueness so "Sports" can be both a HOBBY and an ACTIVITY.

### `ProfileInterest` — M2M through-model
Explicit so a selection can carry weight (`is_primary` = starred).

```
profile FK -> StudentProfile CASCADE    interest FK -> Interest PROTECT
is_primary Boolean    selected_at DateTime auto_now_add
Meta.ordering ["profile","-is_primary","interest"]   UC (profile, interest)
```

### `AvailabilitySlot`
Rows not a blob, because availability is a **hard constraint** — the
intersection must be a DB query.

```
profile FK -> StudentProfile CASCADE   weekday Weekday   time_block TimeBlock
Meta.ordering ["profile","weekday","time_block"]
UC (profile, weekday, time_block)
```

### `CampusLocation`
Approved public meeting places. In the DB rather than free text, which is what
makes "approved locations only" enforceable.

```
name CharField UNIQUE   street_address   arrival_note   is_indoor Boolean
capacity PositiveSmallInt 2..50          is_approved Boolean
Meta.ordering ["name"]
```

### `Match`
One weekly scheduled experience — the central object.

```
connection_type ConnectionType   week_start DateField (Monday)
scheduled_for DateTimeField      location FK -> CampusLocation PROTECT
suggested_activity FK -> Interest SET_NULL null
                   limit_choices_to={"category": ACTIVITY}
status MatchStatus               check_in_code CharField UNIQUE  "QC-4827"
Meta.ordering ["-week_start","-scheduled_for"]
```

### `MatchParticipant`
One student's place in one match. Its own model because membership carries
state belonging to the pairing, not to either side.

```
match FK -> Match CASCADE        profile FK -> StudentProfile PROTECT
response ParticipantResponse     compatibility_score Decimal(5,2) 0..100
match_reason CharField  (renders "Why you matched" on Screen 6)
checked_in_at DateTime null
Meta.ordering ["match","-compatibility_score","profile"]
UC (match, profile)
```

### `ExperienceFeedback`
Private post-meeting feedback. One-to-one with a *participant row*, not a
student, because one review exists per experience.

```
participant OneToOne -> MatchParticipant CASCADE UNIQUE
rating PositiveSmallInt 1..5
enjoyed_conversation / enjoyed_shared_interests /
enjoyed_activity / felt_comfortable   Boolean
wants_to_stay_connected Boolean   (mutual opt-in gate)
private_note TextField            NEVER shown to other participants
submitted_at DateTime auto_now_add
Meta.ordering ["-submitted_at"]
```

### Relationship map

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

### `on_delete` — the reasoning must survive

| Relation | Rule | Why |
|---|---|---|
| `StudentProfile.user` | CASCADE | Orphaning strands personal data unreachable through the account. |
| `AvailabilitySlot.profile` | CASCADE | Worthless without the student. |
| `ProfileInterest.profile` | CASCADE | No meaning without who made it. |
| `ProfileInterest.interest` | **PROTECT** | Deleting a picked catalogue entry silently rewrites profiles and invalidates past match explanations. Retire with `is_active=False`. |
| `Match.location` | **PROTECT** | A past meeting must always say where it happened. Retire with `is_approved=False`. |
| `Match.suggested_activity` | **SET_NULL** | A prompt, not part of the meeting's identity. |
| `MatchParticipant.match` | CASCADE | Describes a place inside one meeting. |
| `MatchParticipant.profile` | **PROTECT** | Deleting a student mid-cycle silently shrinks a squad others plan to attend. Withdrawal must be explicit. |
| `ExperienceFeedback.participant` | CASCADE | Unattributable without the attendance. |

Pattern: **CASCADE** when the child is a detail of its parent · **PROTECT**
when deletion destroys history or affects a third party · **SET_NULL** when
the link is genuinely optional.

### The five `UniqueConstraint`s

`uniq_profile_netid_email` · `uniq_interest_name_per_category` ·
`uniq_interest_per_profile` · `uniq_slot_per_profile_day_block` ·
`uniq_participant_per_match`

> **Django limitation:** `UniqueConstraint` cannot span relations. "One match
> per student per week" (`profile`, `match__week_start`) is **not expressible**
> and was removed. Enforce it in the matching service layer.

---

## 7. Views and routes

`connect/views.py` is divided into commented sections, one per owner. Stay in
yours.

| Path | Name | Kind | Owner | Template |
|---|---|---|---|---|
| `/` | `connect:home` | dashboard | shared/`main` | `home.html` |
| `/students/` | `connect:student-list` | Generic CBV | Kritika | `studentprofile_list.html` (default naming) |
| `/students/<pk>/` | `connect:student-detail` | Generic CBV | Kritika | `studentprofile_detail.html` |
| `/matches/` | `connect:match-list` | FBV `render()` | Manojkumar | `entity_list.html` (shared) |
| `/locations/` | `connect:location-list` | Base CBV | Prathamesh | `entity_list.html` (shared) |
| `/feedback/summary/` | `connect:feedback-summary` | FBV `HttpResponse` | Dhruv | `feedback_summary.html` |

Everything is namespaced: `{% url 'connect:match-list' %}`.

### Template architecture

- **`base.html`** — owned by `main`. Document shell, nav, palette, footer.
  Provides `{% block title %}`, `{% block heading %}`, `{% block subtitle %}`,
  `{% block content %}`, `{% block extra_css %}`.
  **Never edited from a feature branch** — that is the one guaranteed four-way
  conflict, designed out by pre-naming every route.
- **`entity_list.html`** — shared, model-agnostic. Renders a list of plain
  dicts (`title`, `subtitle`, `meta`, `badge`, `url`) so the template does not
  know what a Match or a CampusLocation is. Two owners render it from
  different view styles; that is the "template reuse" deliverable.
- CSS is **inline in `base.html`** on purpose: with `DEBUG=False`, `runserver`
  will not serve `/static/`, so this keeps production mode rendering without
  `collectstatic`. Add WhiteNoise only when real static assets arrive.

---

## 8. Commands

```bash
python manage.py runserver           # dev, / and /admin/
python manage.py migrate
python manage.py seed_demo_data      # idempotent
python manage.py verify_constraints  # 11/11 pass
python manage.py check

DJANGO_SETTINGS_MODULE=quadconnect.settings.production \
  python manage.py check --deploy    # 0 issues with DJANGO_SECURE_SSL=1
```

### Superusers — both, password `uiuc12345`

`mohitg2` (named in P1-A1 section 4) and `tester` (named in its checklist).
The assignment contradicted itself; both exist.

### Seeded data

8 profiles across 5 colleges · 28 interests (12 hobby, 10 RSO, 6 activity) ·
41 interest selections · 16 availability slots · 4 campus locations (Illini
Union, Grainger Library, Main Quad, Espresso Royale) · 3 matches
(`QC-4827` Friend/PROPOSED, `QC-5193` Squad/CONFIRMED with check-ins,
`QC-3312` Friend/COMPLETED) · 9 participants · 2 feedback rows.

### `verify_constraints` — 11 checks

5 uniqueness violations → `IntegrityError`; 3 PROTECT blocks →
`ProtectedError`; 2 CASCADE removals; 1 SET_NULL survival. **Every check runs
inside a rolled-back transaction**, so the database is never mutated. Preserve
that property when adding checks.

---

## 9. Work log

The running history of what has actually been built. Newest at the top.

**Each developer replaces their own placeholder block before merging**, using
this exact shape so every entry reads the same way and the merged file stays
scannable:

```markdown
### DONE `feature/<branch>` - <Name> - YYYY-MM-DD
**Shipped:** one sentence on what it does.
**Files added:** paths.
**Files changed:** paths, and what changed in each.
**Decisions that differ from the build task:** what and why, or "none".
**Gotchas for the next person:** what surprised you or cost you time, or "none".
**Verified:** check clean / route 200 / empty state renders / screenshot saved.
```

**At merge time** the repo owner reviews each incoming block, keeps it, and
adds a short merge entry of their own recording anything that only became
visible when the branches came together — conflicts hit, behaviour that broke
on integration, decisions reversed. That merge entry is the part that is
easiest to skip and most valuable later.

### `main` — accessibility fix · 2026-09-09 · Manojkumar
**Shipped:** shared palette now meets WCAG 2.1 AA, plus explicit focus rings.

**Files changed:** `connect/templates/connect/base.html` only.

**Why:** an audit of the rendered colour combinations found five text pairs
under the 4.5:1 minimum for normal text — `--muted` on the page background
(4.47:1, used by subtitles, section headers and the footer), `--accent` on the
page background (4.46:1, links), and `--accent` on `--accent-soft` (4.33:1,
the status badges). All were marginal, none was visible by eye, all were
failures. Darkened `--muted` `#6b7280`→`#666e7b` and `--accent`
`#c8461e`→`#c0421c`; everything now measures 4.67:1 or better.

Also added `:focus-visible` outlines — the browser default ring is easy to
lose against the card background and 2.4.7 requires focus to be visible at
all times.

**Gotchas for the next person:** this lands in `base.html`, which feature
branches must not edit. Merge `main` into your branch to pick it up. If you
introduce a new colour, check it before you commit — the pairs that failed
were all "looks fine" greys and oranges.

**Verified:** all seven rendered pairs ≥4.67:1 · `manage.py check` 0 issues.

### `main` — P1-A2 scaffold · 2026-09-09 · Manojkumar
Repo initialised as `13_QuadConnect`, 15 commits. Flattened so the repo root
is the Django project root. Split settings into a package and fixed `BASE_DIR`
to three levels. Moved `SECRET_KEY` into `.env` **and rotated it**, because the
previous `django-insecure-…` value had already been written to a file.
Added `.gitignore`, `.env.example`, `requirements.txt`, `base.html`,
`entity_list.html`, the home dashboard, all four named routes with
owner-marked stubs, `docs/` (wireframe PNGs, branching diagram + strategy,
notes with the VIEW REGISTER, per-developer build tasks, screenshot manifest),
and the README. Verified from a clean clone: migrate, seed, dev check, prod
`check --deploy` all pass; all six routes return 200.

### ⬜ `feature/profile-views` — Kritika
*Not started. Replace this block when done: what shipped, files touched,
decisions that differ from the build task, anything the next person needs.*

### ✅ `feature/match-views` — Manojkumar Mohankumar — 2026-09-09
**Shipped:** `/matches/` lists every scheduled experience with location,
activity, headcount and status, filterable by `?week=YYYY-MM-DD`.

**Files added:** `connect/templates/connect/match_list.html` (25 lines —
extends `entity_list.html`, overrides only `{% block filters %}`);
`docs/screenshots/02_fbv_render.png`.

**Files changed:** `connect/views.py` — Section A2 only: added `_match_rows()`
helper and the real `match_list` view, plus `date` and `localtime` imports.
`connect/urls.py` untouched (the stub already pointed at `views.match_list`).
`docs/notes/notes.txt` — view register, reflection, weekly log.

**Decisions that differ from the build task:** none in substance. Took
Option A for the filter (child template extending the shared one) as the task
recommended. Used `<input type="date">` rather than a `<select>` of known
weeks, because the native picker is free and a hand-typed query string still
has to be handled either way.

**Gotchas for the next person:**
- `strftime("%-I")` to strip a leading zero from the hour is **glibc-only and
  crashes on Windows**. Use `.strftime("%I:%M %p").lstrip("0")` instead. This
  bit during development.
- `entity_list.html` exposes `{% block filters %}`, so a view can add filter
  UI by extending it rather than editing it. Prathamesh should do the same
  for `?setting=` — neither of us needs to modify the shared template.
- Times are stored UTC and localised to America/Chicago by `localtime()`. A
  raw shell dump shows 19:00 where the page correctly shows 2:00 PM. Not a
  bug.

**Verified:** `manage.py check` 0 issues · `/matches/` 200 with 3 rows ·
`?week=2026-09-07` 2 rows · `?week=2026-08-31` 1 row · `?week=1999-01-01` and
`?week=banana` both 200 with *different* empty-state messages, neither a 500 ·
template chain `match_list.html → entity_list.html → base.html` ·
2 SQL queries for 3 matches, flat as rows grow · reflected `?week=` value is
HTML-escaped, no XSS · no 5xx on empty, whitespace, impossible-date,
duplicated or path-traversal query values.

**Found during the post-build audit:** the shared palette failed WCAG 2.1 AA
contrast in five places. Fixed on `main` (see the entry below) and merged in,
which is why this branch contains a merge commit.

### ⬜ `feature/location-views` — Prathamesh
- Implemented CampusLocationListView using Django's base View class.
- Added manual CampusLocation queryset with approved-location filtering
  and match-count annotation.
- Added indoor/outdoor filtering through location_list.html extending
  the shared entity_list.html template.
- Wired the /locations/ route using CampusLocationListView.as_view().
- Added required Base CBV screenshot and reflection notes.

### ⬜ `feature/feedback-views` — Dhruv
*Not started.*

---

## 10. Conventions

- Docstring in **every** model class: what entity, and why it exists.
- Inline comment on **every** `on_delete` explaining the choice.
- `Meta.ordering` on every model.
- Choices as `TextChoices`/`IntegerChoices`, never bare strings.
- `help_text` on any field whose meaning is not obvious.
- Admin: `list_display`, `list_filter`, `search_fields`,
  `autocomplete_fields`, inlines, fieldsets grouped **by wireframe screen**.
- Management commands idempotent (`update_or_create` / `get_or_create`).
- Views: keep row-shaping in a helper so the view body stays readable.
- Use `select_related` / `prefetch_related` / `annotate` — no query inside a
  template loop.
- 79-column source, PEP 8.
- Commit messages imperative and specific: `Add CampusLocationListView base
  CBV`, never `update stuff`.

---

## 11. Traps

1. **`BASE_DIR` is three levels up**, not two — the settings package added a
   directory. Get it wrong and Django creates an empty `db.sqlite3` one level
   too deep, silently.
2. **`.as_view()` is required** for CBVs in `urls.py`. Forgetting it gives
   `__init__() takes 1 positional argument but 2 were given`, which does not
   point at the cause.
3. **`DEBUG=False` stops `runserver` serving `/static/`.** Our CSS is inline,
   so prod renders fine today. Adding static assets means adding WhiteNoise at
   the same time.
4. **`db.sqlite3` is gitignored.** Never `git add -f` it — a tracked binary
   conflicts on every branch. Re-run `seed_demo_data` instead.
5. **`UniqueConstraint` cannot span relations** (see §6).
6. **`private_note` is private.** Never render it, and never show per-student
   ratings. Aggregate only.
7. **Check colour contrast before committing a new colour.** Five pairs in
   the original palette sat between 4.33:1 and 4.47:1 — under the 4.5:1 AA
   minimum, and invisible to the eye. Compute the ratio; do not judge it.
8. **PyMuPDF `insert_textbox` renders nothing** when the rect is too short —
   silently, no exception. Relevant if anyone regenerates the wireframe PNGs.
9. **IEEEtran `\maketitle` cannot run mid-document** — the P1-A1 paper was two
   documents merged with `pypdf`. Its LaTeX sources were deleted; changing
   those PDFs means rebuilding from scratch.
10. **8 models vs P1-A1's "recommended 3–5."** The binding rule was a minimum of
   2 per feature. Do not "fix" this by collapsing models — it would force
   nullable columns meaningless for half the rows.

---

## 12. Assignment history

### P1-A1 — Product + Data Models + UI/UX (35 pts) — submitted
Four uploads: the TCC workbook, the Idea Description PDF (rebuilt in genuine
IEEE two-column after the original was single-column), the Wireframes PDF
(rebuilt low-fidelity after the original was high-fidelity Figma screenshots,
with those kept as an iteration-v2 appendix), and the Django project ZIP.
Deliverables live outside this repo in the workspace `SUBMIT/` folder.

### P1-A2 — Fullstack Development + GitHub Secrets (30 pts) — in flight
Section 1 structure/security/GitHub: **done on `main`**.
Sections 2 and 3 views/templates: **four feature branches pending**.
Submission is one item: the public GitHub repository URL.
Instructor `27guptamohit` is added as a collaborator **last**, after all four
branches merge.

### Next
The matching algorithm remains the biggest open design question:
`compatibility_score` and `match_reason` are fields that nothing computes
outside seed data. Weighting, normalisation to 0–100, squad formation for
4–8 people, tie-breaking, starvation avoidance, and generating `match_reason`
from the same computation so the explanation cannot drift from the score.
