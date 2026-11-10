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
| **Assignment in flight** | **P1-A9** — Integrated AI Application Deployment (300 pts; GitHub and an in-person demo): Parts 2 and 3 done on `feature/p1-a9-part2-3` — `README_AI.md` (the AI system design and the evaluation of the integrated feature), the request check in `connect/ai_search.py`, `connect/tests_a9.py` and the raw results in `docs/a9_evaluation/`; Part 1 on `feature/p1-a9-part1`, cut from it — A8's embedding model in the search, the time limit, `README_AI.md` Part 1 and `docs/a9_part1/`. Audited on 2026-11-09 and opened as PR #16 into `main`, not merged yet (§9). |
| **Last completed** | P1-A8 — Semantic Relationships and Retrieval — merged into `main` (PR #15, 2026-11-08) |
| **`main` status** | Has P1-A2 to P1-A8 (P1-A8 in PR #15). |
| **What remains** | P1-A9: merging PR #16 into `main`, the Canvas file (the repository link, a summary of the AI feature and the demo time) and the in-person demo on Thursday 2026-11-12, 11:30 AM, EDUC 339 (§9). |

`main` ships P1-A2 (split settings, `.env` handling, `base.html`, the shared
list template, a home dashboard and the four graded views), P1-A3 (detail
pages, search, static files with cache busting, Matplotlib charts, a POST form
on a CBV, a JSON API) and P1-A4 (chart-ready API endpoints, two Vega-Lite
charts, Open Trivia DB icebreakers, CSV/JSON exports with a reports page, the
committed seed database) and P1-A5 (accounts with django-allauth, every page
private by default, Google sign-in, one public API). `feature/p1-a6` adds
everything in §9's P1-A6 entry: the model lab in `llm-test/`, "Ask in plain
English" (a local Hugging Face model) and the automatic check of venue
suggestions (an external API). CI: every push to `feature/p1-a6` runs one
check, **Deploy / test (push)** (`.github/workflows/deploy.yml`), with every
CI step inside that one job. It runs on no other branch: code reaches `main`
only through a PR whose head has passed it.

### Status board — UPDATE YOUR ROW WHEN YOU FINISH

| Owner | Branch | View kind | Route | Status |
|---|---|---|---|---|
| Kritika Agrawal | `feature/profile-views` | Generic CBV | `/students/` | ✅ DONE — `StudentProfileListView` + `DetailView`, `?college=` filter, default template naming |
| Manojkumar Mohankumar | `feature/match-views` | FBV `render()` | `/matches/` | ✅ DONE — `match_list` with `?week=` filter, renders the shared list template |
| Prathamesh Mulay | `feature/location-views` | Base CBV | `/locations/` | ✅ DONE — `CampusLocationListView` base CBV with setting + seats filters, reuses the shared list template |
| Dhruv Thaker | `feature/feedback-views` | FBV `HttpResponse` | `/feedback/summary/` | ✅ DONE — aggregate feedback summary with rating distribution, enjoyment metrics, and connection preferences |
| Manojkumar Mohankumar (P1-A3, solo) | `feature/p1-a3` | all six A3 sections | `/search/`, `/matches/<pk>/`, `/locations/<pk>/`, `/insights/`, `/api/` | ✅ DONE — merged to `main` in PR #6 (2026-09-28); see §9 |
| Manojkumar Mohankumar (P1-A4) | `feature/p1-a4` | all four A4 parts | `/api/summary/`, `/vega-lite/...`, `/api/icebreakers/`, `/reports/`, `/export/...` | ✅ DONE — merged to `main` in PR #9 (2026-10-05); live at <https://manojkmohan43.pythonanywhere.com/>; see §9 |
| Manojkumar Mohankumar (P1-A5) | `feature/p1-a5` | Parts 1–4 | `/accounts/...`, every route behind a login, `/api/summary/` public | ✅ DONE — merged to `main` in PR #10 (2026-10-12); deployed 2026-10-09; see §9 |
| Manojkumar Mohankumar (P1-A6) | `feature/p1-a6` | Parts 1–3 | `/search/ask/`, the venue check on `/locations/`, `llm-test/` | ✅ DONE — merged to `main` in PR #11 (2026-10-19); see §9 |
| Manojkumar Mohankumar (P1-A7) | `feature/p1-a7-part-1`, `-part-2`, `-part-3` | Parts 1–3 | `multi-model/` (not Django) | ✅ DONE — merged to `main` in PR #12 (2026-10-26), PR #13 and PR #14 (2026-11-03); see §9 |
| Manojkumar Mohankumar (P1-A8) | `feature/p1-a8` | Parts 1–4 | `rag/` (not Django) | ✅ DONE — merged to `main` in PR #15 (2026-11-08); see §9 |
| Prathamesh Mulay, Manojkumar Mohankumar (P1-A9) | `feature/p1-a9-part2-3` | Parts 2–3 | `README_AI.md`, the request check in `connect/ai_search.py`, `docs/a9_evaluation/` | DONE — Parts 2 and 3 done 2026-11-08; in PR #16 through `feature/p1-a9-part1`, which contains them; see §9 |
| Kritika Agrawal (P1-A9) | `feature/p1-a9-part1` | Part 1 | `README_AI.md` Part 1, `match_by_meaning()` and `ModelTimeout` in `connect/ai_search.py`, `docs/a9_part1/` | BUILDING — Part 1 done and audited 2026-11-09; PR #16 into `main` open, not merged; see §9 |

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
| **Stack** | Django 5.2.17 · Python 3.11 · SQLite · `python-dotenv` · WhiteNoise · Matplotlib (A3) · django-allauth (A5) · `transformers` + `torch` (A6) |
| **Platform** | Windows 11, PowerShell + Git Bash |

No JavaScript framework, no CSS framework, no build step. Server-rendered
Django templates and one stylesheet in `static/css/` (inline CSS until A3).

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
- **No machine learning in matching.** Matching is a deterministic weighted
  score over hard constraints plus soft signals. Never describe the matching
  as ML — the paper, the data model and the TCC must stay consistent. P1-A6
  added language models that read text, and nothing else: "Ask in plain
  English" turns a sentence into allow-listed search filters, and the venue
  check gives staff advice. Neither decides a match, and neither approves
  anything.

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
├── requirements.txt               pip freeze, 61 pins (A6): Django, django-allauth, whitenoise, matplotlib, requests, vl-convert-python, torch, transformers, ...
├── README_AI.md                   (A9) Parts 2-3: AI workflow, architecture, model choice, evaluation
├── llm-test/                      (A6) ai_prototype.ipynb (the model lab), requirements.txt (its extras), results/runs.jsonl
├── manage.py                      -> quadconnect.settings.development
├── db.sqlite3                     COMMITTED since A4 — seed data only
├── static/                        (A3) css/quadconnect.css, img/logo.svg, fonts/; (A4) js/charts.js, vendor/vega/
├── templates/                     (A5) account/ (login, sign-up, logout pages), allauth/ (layout)
├── staticfiles/                   IGNORED — collectstatic output (production)
├── docs/
│   ├── wireframes/
│   │   ├── v1/                    10 PNGs: 9 screens + flow
│   │   ├── QuadConnect_Wireframes.pdf
│   │   └── QuadConnect_Project_Idea_Description.pdf
│   ├── branching_strategy/        diagram.png + branching.md
│   ├── notes/notes.txt            weekly log, VIEW REGISTER, REFLECTION
│   ├── build_tasks/               one spec per developer + shared rules
│   ├── screenshots/               README.md manifest, A2 captures, p1-a3/ (19), p1-a4/ (19), p1-a5/
│   ├── a5/                        (A5) the public API's Vega-Lite spec, its three uses, README
│   ├── a9_part1/                  (A9) Part 1's measurements of the embedding step, and measure.py
│   ├── a9_evaluation/             (A9) the raw before and after results of the Part 3 runs
│   ├── README_AI_P1-A6.md         (A6) the AI write-up, README_AI.md until A9
│   ├── er_diagram.pdf
│   └── data_model_notes.md        why each model and on_delete exists
├── quadconnect/
│   ├── settings/
│   │   ├── base.py                shared; reads .env; BASE_DIR 3 levels up
│   │   ├── development.py         DEBUG=True
│   │   └── production.py          DEBUG=False + security headers + hashed static
│   ├── urls.py                    /admin/, /accounts/ (allauth) and '' -> connect.urls
│   ├── wsgi.py  asgi.py           -> quadconnect.settings.production
└── connect/
    ├── models.py                  8 models; A3 added get_absolute_url() to 3 (no migration)
    ├── views.py                   one section per owner, plus A3 sections
    ├── forms.py                   (A3) search, NetID lookup, venue suggestion; (A5) login form
    ├── middleware.py              (A5) login required by default; 401 JSON for /api/
    ├── charts.py                  (A3) Matplotlib charts + Insights page
    ├── api.py                     (A3) JSON API + docs page; (A4) /api/summary/...
    ├── vega_charts.py             (A4) Vega-Lite spec + PNG/JPG endpoints
    ├── specs/                     (A4) chart1_bar.vl.json, chart2_line.vl.json
    ├── icebreakers.py             (A4) Open Trivia DB questions for a match
    ├── reports.py                 (A4) /reports/ and the CSV/JSON exports
    ├── ai_search.py               (A6) "Ask in plain English": the local model, its prompt and guardrails, the view;
    │                              (A9) check_against_request(); Part 1: match_by_meaning() and Embedder, ModelTimeout
    ├── ai_venues.py               (A6) the external API that checks venue suggestions
    ├── tests.py                   (A3) 45 tests, one class per A3 section
    ├── tests_a4.py                (A4) 42 tests, one class per A4 part
    ├── tests_a5.py                (A5) 25 tests: access, navigation, accounts, Google
    ├── tests_a6.py                (A6) 61 tests: no model is loaded and no API called
    ├── tests_a9.py                (A9) 37 tests: Part 1's embedding step, time limit and page, the request check; no model is loaded
    ├── urls.py                    every route named, namespace "connect"
    ├── admin.py                   all 8 registered, with inlines
    ├── migrations/                0001_initial.py; 0002 (A6) adds CampusLocation's ai_* fields
    ├── templates/connect/
    │   ├── base.html              site shell; A3 moved its CSS to static/
    │   ├── entity_list.html       SHARED — model-agnostic list
    │   └── home.html, *_detail.html, student_search.html, insights.html, api_docs.html, icebreakers.html, reports.html, ...
    └── management/commands/
        ├── seed_demo_data.py      idempotent
        ├── verify_constraints.py  11 checks, all rolled back
        └── download_ai_model.py   (A6) fetches the local model before the first search; (A9) the embedding model too
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

**Static files (A3).** `STATICFILES_DIRS = [BASE_DIR / "static"]`. WhiteNoise
serves them in both environments (`WhiteNoiseMiddleware` straight after
`SecurityMiddleware`, and `whitenoise.runserver_nostatic` so dev behaves like
prod). Production uses `CompressedManifestStaticFilesStorage`: content-hashed
names, `immutable` caching, gzip. **Production needs
`collectstatic --noinput` before it starts**; development does not.

### `.env` keys

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Signing key. Required. Rotated when it left source. |
| `DJANGO_SETTINGS_MODULE` | Which settings module to load. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated. Required in production. |
| `DJANGO_SECURE_SSL` | `1` behind real TLS. |
| `MAPS_API_KEY` | Placeholder for the Screen 8 map. Dummy value. |
| `GOOGLE_CLIENT_ID` | Google OAuth client (A5). Required in production; in development, empty hides the Google button. |
| `GOOGLE_CLIENT_SECRET` | That client's secret. Required when the ID is set. Never in the database. |
| `DJANGO_DB_PATH` | Optional SQLite path. The live site's database lives outside the repository. |
| `AI_LOCAL_ENABLED`, `AI_LOCAL_MODEL`, `AI_LOCAL_MAX_SECONDS` | (A6) The local model for "Ask in plain English": on/off, its Hugging Face id, its time limit. |
| `AI_EMBED_ENABLED`, `AI_EMBED_MODEL` | (A9) The embedding model that places an interest the model wrote in its own words on the list: on/off, its Hugging Face id. |
| `AI_API_PROVIDER`, `AI_API_MODEL` | (A6) The venue check's API (`groq`, `openrouter`, `gemini`, `huggingface`) and an optional model. |
| `GROQ_API_KEY` (or `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `AI_API_KEY`) | (A6) That provider's key. Without one, suggestions are saved "not checked" and nothing is sent. |
| `HF_TOKEN` | (A6) Optional Hugging Face token: faster downloads, and the key for `AI_API_PROVIDER=huggingface`. |

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
ai_decision VenueCheck blank  ai_flags  ai_reason  ai_checked_by  ai_checked_at
            (A6: the automatic check of a suggestion; advice for staff only,
             set by connect/ai_venues.py, read-only in Admin)
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
| `/privacy/` | `connect:privacy` | FBV `render()`, public | A5 | `privacy.html` |
| `/students/` | `connect:student-list` | Generic CBV | Kritika | `studentprofile_list.html` (default naming) |
| `/students/<pk>/` | `connect:student-detail` | Generic CBV | Kritika | `studentprofile_detail.html` |
| `/matches/` | `connect:match-list` | FBV `render()` | Manojkumar | `entity_list.html` (shared) |
| `/locations/` | `connect:location-list` | Base CBV | Prathamesh | `entity_list.html` (shared) |
| `/feedback/summary/` | `connect:feedback-summary` | FBV `HttpResponse` | Dhruv | `feedback_summary.html` |
| `/search/` | `connect:student-search` | Base CBV, GET+POST | A3 | `student_search.html` |
| `/search/ask/` | `connect:student-ask` | FBV `render()`, GET; a local language model reads the request | A6 | `student_ask.html` |
| `/matches/<pk>/` | `connect:match-detail` | Generic CBV | A3 | `match_detail.html` (default naming) |
| `/locations/<pk>/` | `connect:location-detail` | Generic CBV | A3 | `campuslocation_detail.html` (default naming) |
| `/insights/` + two `.png` | `connect:insights`, `connect:chart-*` | FBV, `image/png` | A3 | `insights.html` |
| `/api/`, `/api/locations/`, `/api/matches/`, `/api/locations.txt` | `connect:api-*` | CBV + FBV, `JsonResponse` / `HttpResponse` | A3 | `api_docs.html` for `/api/` |
| `/api/summary/`, `/api/summary/matches-per-week/` | `connect:api-summary*` | FBV, `JsonResponse`; `/api/summary/` public with CORS `*` (A5) | A4 | — |
| `/vega-lite/<chart>.vl.json`, `.png`, `.jpg` | `connect:vega-spec`, `connect:vega-image` | FBV, JSON / image | A4 | — |
| `/api/icebreakers/?match=<id>`, `/matches/<pk>/icebreakers/` | `connect:api-icebreakers`, `connect:match-icebreakers` | FBV, calls Open Trivia DB | A4 | `icebreakers.html` |
| `/reports/`, `/export/students.csv`, `/export/students.json` | `connect:reports`, `connect:export-students-*` | FBV, `render()` / attachments | A4 | `reports.html` |

`/locations/` also gained `post()` in A3 (venue suggestions), and in A6 that
`post()` runs the automatic check before it saves. Everything is
namespaced: `{% url 'connect:match-list' %}`. Links to a single record always
go through `get_absolute_url()` (`StudentProfile`, `Match`, `CampusLocation`).

**Access (A5).** `connect.middleware.LoginRequiredMiddleware` makes every
view private. A view opens to everyone only with `@login_not_required`: today
`home`, `privacy` and `summary_api`, plus allauth's own sign-in views. A signed-out page
request redirects to `/accounts/login/?next=...`, and an `/api/` request gets
`401` JSON. A new view is private unless you mark it, so decide on purpose,
and add a public one to `PUBLIC_ROUTES` in `tests_a5.py`. The account pages
live under `/accounts/` (allauth's URLs), with the site's templates in the
project-level `templates/account/`.

### Template architecture

- **`base.html`** — owned by `main`. Document shell, nav, palette, footer.
  Provides `{% block title %}`, `{% block heading %}`, `{% block subtitle %}`,
  `{% block content %}`, `{% block extra_css %}`.
  **Never edited from a feature branch** — that is the one guaranteed four-way
  conflict, designed out by pre-naming every route. (In practice A3, A4, A5
  and A6 each changed `base.html` on their own feature branch and merged it
  through a pull request; see their entries in §9. Keep such changes small
  and list them in the entry.)
- **`entity_list.html`** — shared, model-agnostic. Renders a list of plain
  dicts (`title`, `subtitle`, `meta`, `badge`, `url`) so the template does not
  know what a Match or a CampusLocation is. Two owners render it from
  different view styles; that is the "template reuse" deliverable.
  A3 added `{% block after_list %}` below the list (the venue form uses it).
- ~~CSS is inline in `base.html`~~ (A2). Since A3 the design lives in
  `static/css/quadconnect.css`, loaded with `{% static %}`, and WhiteNoise
  keeps `DEBUG=False` rendering. No `style=""` attributes in templates except
  the data-driven width of the rating bars. `base.html` also gained
  `{% block page_header %}` (home replaces it with the hero) and a flash
  message region. A4 added `{% block scripts %}` at the end of `<body>`
  (Insights loads the Vega scripts there) and a ninth nav link, Reports.

---

## 8. Commands

```bash
python manage.py runserver           # dev, / and /admin/
python manage.py migrate
python manage.py seed_demo_data      # idempotent
python manage.py verify_constraints  # 11/11 pass
python manage.py check
python manage.py test connect        # 210 tests (45 A3, 42 A4, 25 A5, 61 A6, 37 A9)
python manage.py download_ai_model   # A6, A9: fetch both local models before the first search
ruff check .                         # rules in ruff.toml; CI runs the same

DJANGO_SETTINGS_MODULE=quadconnect.settings.production \
  python manage.py check --deploy    # 0 issues with DJANGO_SECURE_SSL=1
DJANGO_SETTINGS_MODULE=quadconnect.settings.production \
  python manage.py collectstatic --noinput   # before running production (A3)
```

### Superusers — both, password `uiuc12345`

`mohitg2` (named in P1-A1 section 4) and `tester` (named in its checklist).
The assignment contradicted itself; both exist.

### Seeded data

8 profiles across 6 colleges · 28 interests (12 hobby, 10 RSO, 6 activity) ·
41 interest selections · 16 availability slots · 4 campus locations (Illini
Union, Grainger Library, Main Quad, Espresso Royale) · 19 matches over nine
weeks (2026-07-13 to 2026-09-07): the original three keep ids 1–3
(`QC-4827` Friend/PROPOSED, `QC-5193` Squad/CONFIRMED with check-ins,
`QC-3312` Friend/COMPLETED), and A4 added 16 past ones (`QC-1301`–`QC-1316`,
one cancelled) for the matches-per-week chart · 55 participants · 33 feedback
rows · staff `tester` and `mohitg2`. Sign-up dates are fixed, so reseeding
changes nothing.

### `verify_constraints` — 11 checks

5 uniqueness violations → `IntegrityError`; 3 PROTECT blocks →
`ProtectedError`; 2 CASCADE removals; 1 SET_NULL survival. **Every check runs
inside a rolled-back transaction**, so the database is never mutated. Preserve
that property when adding checks.

---

## 9. Work log

The running history of what has actually been built. Newest at the top.

### BUILDING `feature/p1-a9-part1` - Kritika Agrawal - 2026-11-09
**Shipped so far:** P1-A9 Part 1, on a branch cut from `feature/p1-a9-part2-3` at `461e03e`.
- `README_AI.md`: a new Part 1 section, with one subsection per rubric step: the feature, the reuse of A6, A7
  and A8, where the models run, the flow in the app (with a diagram), and the guardrails (18, each with its test).
- `connect/ai_search.py`:
  - `match_by_meaning()`, `Embedder` and `embed_similarities()`. P1-A8's `BAAI/bge-small-en-v1.5` (via
    `sentence-transformers`) places an interest the model wrote in its own words, if `match_name()` could not
    place it by spelling. A word is placed only at a cosine similarity of at least 0.78 and a lead of at least
    0.08 over the next interest. On Part 3's 20 requests, exactly right went from 15 to 17 (T08 and T10), with
    no unasked filter and the same median time.
  - `ModelTimeout`: a generation stopped at `AI_LOCAL_MAX_SECONDS` is not retried. The keyword parser answers,
    and the page says the model took too long.
- `student_ask.html`: a *Matched by meaning* note lists each placement.
- `download_ai_model`: fetches and tests the embedding model too.
- `connect/tests_a9.py`: 29 new tests (210 in all). Both models are stand-ins.
- `docs/a9_part1/`: `measure.py`, and its results with the real models: the calibration words, and the
  20 requests with the step off and on.

**Files changed:** `requirements.txt` (`sentence-transformers` and its 6 dependencies), `.env.example` and
`settings/base.py` (`AI_EMBED_ENABLED`, `AI_EMBED_MODEL`), `connect/tests_a6.py` (its seeded tests run with the
embedding step off, so they test A6's spelling-only allow-list), the CI workflow (runs on
`feature/p1-a9-part1`, with `AI_EMBED_ENABLED=0`), `README.md`, this file, notes.txt.

**Gotchas:**
- `README_AI.md` Parts 2 and 3 were written before Part 1 changed the pipeline. The audit below brought Part 2
  up to date (2.1, the 2.2 diagram and 2.3). Part 3 keeps its measured tables, and 3.4 adds Part 1's re-run as a
  second improvement.
- `MEANING_MIN` and `MEANING_LEAD` fit `bge-small-en-v1.5`. Another `AI_EMBED_MODEL` needs its own limits:
  re-run `docs/a9_part1/measure.py`.
- In the held-out words, *lunch* was placed on Food. A wrong placement always shows on the page.
- Measured on an Apple M5 (24 GB, CPU): a median of 2.35 s per search, and 9.5 s for the first search after a
  start, while both models load from the cache.

**Audit (Manojkumar Mohankumar, 2026-11-09):** every rubric step and deliverable checked on the branch.
- The evidence was re-run on a second machine (Windows, CPU): all 115 embedding similarities in
  `calibration.csv` agree within 0.0005, with the same placements, and all 40 rows of `requests.json` recompute
  from their recorded model replies (filters, chips, students found, verdicts). 210 tests pass, and the 197
  relative links in the Markdown files resolve.
- Fixed: `README_AI.md` 2.1, the 2.2 diagram and 2.3 now describe the embedding step and the time limit;
  Part 3's summary, failure 3 and 3.4 record the embedding step as a second improvement; the README's CI
  section named `feature/p1-a6`; `.gitignore` now also ignores a model cache folder inside the repository.
- PR #16 into `main` opened; it stays unmerged until the team decides.

### BUILDING `feature/p1-a9-part2-3` - Prathamesh Mulay, Manojkumar Mohankumar - 2026-11-08
**Shipped so far:** P1-A9 Parts 2 and 3, on a branch cut from `main` at
`5c24c9b`, after P1-A8 merged.
- `README_AI.md`: the P1-A9 write-up. Part 2: the AI workflow, two
  architecture diagrams, and the model choice tied to A6, A7 and A8. Part 3:
  20 requests (A6's 15 and 5 new ones) through the live `/search/ask/` page,
  before and after the improvement, with the failure analysis.
- `connect/ai_search.py`: `check_against_request()`, run on every model answer
  after `clean_filters()`. A day, time or connection type the request does not
  name is removed, and a college it names wins. Exactly right went from 11 to
  15 of 20, and unasked filters from 6 requests to none.
- `connect/tests_a9.py`: 8 tests, no model loaded (181 tests in all).
- `docs/a9_evaluation/`: the raw results of both runs, as collected.
- `docs/README_AI_P1-A6.md`: the P1-A6 write-up, moved from `README_AI.md`.

**Files changed:** `README.md` (P1-A9 section, layout, test count),
`.gitattributes` (the evaluation evidence kept as collected), the CI workflow
(now runs on `feature/p1-a9-part2-3`), this file, notes.txt.

**Gotchas:**
- The evaluation ran on Prathamesh's MacBook Air (Apple M4, 16 GB), on the
  CPU: a median of 3.6 s per search, against 10 s on our A6 laptop.
- The first search after a restart, or after `runserver` reloads a changed
  file, loads the model again (about 20 s there).

### DONE `feature/p1-a8` - Manojkumar Mohankumar - 2026-11-03
**Shipped:** P1-A8 Parts 1 to 4 (the RAG pipeline, the
experiments, failure analysis and improvement, and the system design), on a branch cut from `main` at `e36b97e`,
merged into `main` in PR #15. The assignment is
independent of the Django app, so everything is in `rag/`.
- `data/handbook.md`: the knowledge base, QuadConnect's student handbook
  (13 sections, 44 paragraphs, 4,875 words), written from the app's code,
  data and pages; matching, check-in and feedback are described as the data
  model defines them, since the prototype has no engine or forms for them.
- `rag_system.ipynb`, Steps 1.1–1.5:
  - the handbook read and checked against the brief's size rules;
  - three chunking strategies, with every chunk checked for split sentences
    and mixed sections;
  - three BGE embedding models (384 / 768 / 1,024 dimensions) in nine
    vector stores;
  - top-3 cosine retrieval;
  - generation with gpt-oss-20b, its replies saved in
    `results/generations.jsonl`.
- `rag_system.ipynb`, Steps 2.1–2.5:
  - 8 test questions with 18 key facts and their evidence sentences;
  - 72 runs (9 configurations x 8 questions) with retrieved chunks,
    context quality, a 1-10 answer score, latency and notes;
  - embedding models and chunking strategies compared, with charts;
  - a data scaling experiment on three nested datasets.
- `data/staff_guide.md`: a staff and developer guide (44 paragraphs,
  4,555 words) written from the app's code, the larger dataset's extra
  documents.
- `rag_system.ipynb`, Steps 3.1–3.3:
  - every key fact of the 72 runs traced to retrieval or generation;
  - four failures in detail, each cause tested one at a time;
  - two fixes measured before and after on 24 runs: top-k 3 -> 5 (kept)
    and a new prompt in two versions (not kept: it invented a step).
- `rag_system.ipynb`, Steps 4.1–4.3:
  - cost per factor at 10,000 users a day, priced with A7's prices;
  - RAG against pure prompting and the whole handbook in the prompt,
    and when to use fine-tuning (RAG chosen);
  - the design for 10,000 users a day, with its diagram.
- `rag_analysis.md` (all four parts), `README.md`, `requirements.txt`.

**Files changed:** `README.md` (P1-A8 section, layout), `ruff.toml` (E402
for the notebook), `.gitattributes` (LF for `rag/data` and `rag/results`; binary for
`rag/results/*.png`),
the CI workflow (now runs on `feature/p1-a8`), this file, notes.txt.

**Gotchas:**
- The first run downloads about 1.9 GB of embedding models.
- Timings differ from run to run; the answers, retrieval results and
  scores do not, because the answers are saved and retrieval is exact.
- Part 2 makes about 80 calls to Groq on a fresh cache, all saved; with
  the saved file, a full run takes three to four minutes.

### DONE `feature/p1-a7-part-3` - Manojkumar Mohankumar - 2026-11-03
**Shipped:** P1-A7 Part 3 (multi-model routing strategy), on a branch cut
from `main` at `38e5248`, merged into `main` in PR #14.
- `multi_model_system.ipynb`, Part 3:
  - The router's menu: our Qwen2.5-3B, and gpt-oss-20b, gpt-oss-120b and
    Qwen3.8-27B on Hugging Face. It shows their Part 1 scores per job and
    every provider's measured speed.
  - Step 3.1: five scenarios (normal operation, peak usage hours,
    high-complexity queries, cost optimization, overload or outage).
  - Step 3.2: a routing strategy for each, in the brief's table, and the
    router's six rules in order.
  - Step 3.3: every strategy run against the same situation without it,
    for latency, cost and quality, with a chart across the six traffic
    levels.
- `system_design.md`: section 3, the routing design, with the same tables.

**Files changed:**
- The notebook: Part 3 added. Part 2's `capacity()` gained an optional cap
  on requests in flight, which leaves its results byte-identical.
- `system_design.md`, `README.md`, the CI workflow (now on
  `feature/p1-a7-part-3`), this file and notes.txt.

**Gotchas:**
- Part 3 runs after Part 2's cells and needs no models.
- Its provider speeds are Hugging Face's measurements of 3 November 2026.
- On an L4, our Qwen2.5-3B cannot write icebreakers within 1 second, so
  that target is 2 seconds (the words stream).

### DONE `feature/p1-a7-part-2` - Manojkumar Mohankumar - 2026-11-03
**Shipped:** P1-A7 Part 2 (cost comparison and infrastructure planning), on
a branch cut from `main` at `17cfa98`, merged into `main` in PR #13
(2026-11-03, merge commit `38e5248`).
- `multi_model_system.ipynb`, Part 2:
  - Tokens per request and per user, from Part 1's 375 replies: 392 per
    request, 697 per user a day.
  - The token load at the six traffic levels.
  - A roofline estimate of what one AWS `g6.4xlarge` (one NVIDIA L4) serves
    for each model.
  - The machines and their cost for every model at every level (90 rows).
  - The comparable Hugging Face model and its cheapest provider, the API bill
    and its servers (90 rows).
  - The comparison, a chart, and the break-even points under four what-ifs.
- `system_design.md`: section 2, the cost analysis, with both 90-row tables.
- `results/`: `local_hosting_costs.csv`, `api_costs.csv`.

**Files changed:**
- The notebook: Part 2 added. Part 1 is unchanged and its table is
  byte-identical.
- `system_design.md` and `README.md` (the P1-A7 section).
- The CI workflow: it now runs on `feature/p1-a7-part-2`.
- This file and notes.txt.

**Gotchas:**
- Part 2 needs no models and runs on its own after a restart.
- Its prices are a snapshot from 3 November 2026, each kept in one cell.
  Check them again before quoting the results later.
- There was no L4 to measure on, so every hosted cost rests on the roofline's
  efficiency assumptions (60% of the bandwidth, 40% of the arithmetic). The
  notebook's what-ifs show what a 2× error does.

### DONE `feature/p1-a7-part-1` - Manojkumar Mohankumar - 2026-10-26
**Shipped:** P1-A7 Part 1 (model size selection and benchmarking), on a
branch cut from `main` at `fd89f6b`, merged into `main` in PR #12
(2026-10-26, merge commit `17cfa98`). The assignment is independent of the
Django app, so everything is in `multi-model/`.
- `multi_model_system.ipynb`: the same 15 models as A6 in A6's five size
  categories, 5 prompt types QuadConnect needs (structured extraction,
  classification, prediction, summarization, text generation) × 5 prompts,
  375 replies with latency, tokens/sec and time to first token, each scored
  1–10 by a rubric in code (accuracy gates the score), a hand spot check of 20
  replies, a timing check, and the Step 1.6 analysis.
- `system_design.md`: Part 1's architectural conclusions (three model tiers).
- `results/`: `runs.jsonl` (every reply, resumable), `benchmark_table.csv`,
  `manual_check.json`.

**Files changed:** `README.md` (P1-A7 section, layout), `ruff.toml` (E402 for
the new notebook), the CI workflow (now runs on `feature/p1-a7-part-1`), this file,
notes.txt.

**Gotchas:** a laptop that sleeps mid-run stalls a reply (one took 43 minutes);
the notebook's timing check finds such replies, and deleting them from
`runs.jsonl` and re-running regenerates only them.

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

### DONE `feature/p1-a6` - Manojkumar Mohankumar - 2026-10-19
**Shipped:** all three P1-A6 parts on one branch cut from `main` at
`df81e3b`. Route A (prompt engineering), chosen because the instructor's
machine must download a pre-trained model by itself.
- Part 1: `llm-test/ai_prototype.ipynb`. Its first code cell downloads the
  weights. It picks 15 models from the Open LLM Leaderboard's own dataset (3
  per size category: Qwen2.5 at every size, plus the two best non-gated models
  of other families by IFEval), tests them on 15 fixed search requests with
  hand-written answers, compares zero-, one-, few- and many-shot prompts, and
  scores adherence, correctness, injection safety, speed and memory. The XL
  category (over 15B) runs on Groq's free API: the leaderboard's XL models
  need paid hosting (Hugging Face Inference Providers had no free credit), so
  it uses the three open-weight XL models Groq serves (gpt-oss-20b,
  Qwen3.8-27B, gpt-oss-120b), which came out after the leaderboard closed.
- Part 2: "Ask in plain English" (`/search/ask/`, a local model in a Django
  view) and the automatic check of venue suggestions (an external API, Groq by
  default), written up in `README_AI.md` (now `docs/README_AI_P1-A6.md`). The model is Qwen2.5-1.5B-Instruct
  with the many-shot prompt (notebook Step 7): the smallest model that clears
  0.85 after the allow-list (0.92).
- Part 3: the production reflection, section 3 of `docs/notes/notes.txt`.

**Files added:** `README_AI.md` (moved to `docs/README_AI_P1-A6.md` in A9), `llm-test/` (notebook, requirements,
results), `connect/ai_search.py`, `connect/ai_venues.py`,
`connect/tests_a6.py`, `connect/templates/connect/student_ask.html`,
`connect/management/commands/download_ai_model.py`,
`connect/migrations/0002_campuslocation_ai_check.py`.

**Files changed:** `requirements.txt` (torch, transformers and their
dependencies, 61 pins); `settings/base.py` (the AI block); `models.py`
(`VenueCheck`, five `ai_*` fields on `CampusLocation`); `views.py` (the venue
form runs the check); `urls.py`; `admin.py`; `base.html` (Search stays
marked on the ask page); `student_search.html`, `location_list.html`;
`.gitignore` (weights); `.env.example` (AI keys); `privacy.html` (what the
venue check sends to Groq); `tests.py` (the venue form tests run without an
API key); the CI workflow (this branch, CPU torch, the
size check counts the web app only, `AI_LOCAL_ENABLED=0`); `db.sqlite3`
(rebuilt with migration 0002); README, notes.txt, this file.

**Decisions:** a teammate's P1-A6 branch (`p1-a6-text-intelligence`) was
reviewed first and not used: its own test failed (two links it documents were
never committed), 3 of its 15 models were never run, and its API was never
called live. This branch was built separately. float32 on CPUs, 4-bit for 2B
to 15B models (§11 trap 29).

**Verified:** 173 tests (61 in `tests_a6.py`), ruff clean, CI green. The
notebook runs end to end from its reply cache with no errors. Live on the
laptop: the search with the real model inside Django (49 s for the first
search, which loads the model, then about 10 s a search, 6.4 GB of memory)
and the venue check against Groq (5 of 5 test suggestions judged as
expected, all saved unapproved).

**Gotchas for the next person:** §11 traps 29–35.

### `main` — P1-A5 merged · 2026-10-12 · PR #10
**Merged:** `feature/p1-a5` into `main` through PR #10. Merge commit
`df81e3b`. The PR's head had passed the Deploy / test check, and nothing
surfaced at integration. The workflow then moved to `feature/p1-a6`.

### DONE `feature/p1-a5` - Manojkumar Mohankumar - 2026-10-08
**Shipped so far:** Parts 1–3 of P1-A5 on one branch cut from `main` at
`70d0ad4`.
- Part 1: django-allauth accounts with the site's own login, sign-up and
  logout pages. Every view is private unless marked `@login_not_required`.
  API paths answer `401` JSON instead of redirecting. The nav shows only
  Home, Log in and Sign up until you log in.
- Part 2: "Continue with Google" on the login and sign-up pages, with the
  client keys read from `.env`.
- Part 3: `/api/summary/` is the one public API. A Vega-Lite spec reads it
  from production, and three other uses read it too: a command-line
  report, a notebook and an Excel workbook (`docs/a5/`).

**Files added:** `connect/middleware.py`, `connect/tests_a5.py`,
`templates/account/` (`login.html`, `signup.html`, `logout.html`,
`snippets/google_button.html`), `templates/allauth/` (layout and `h1`
element), `docs/a5/` (the spec, three uses, README),
`docs/screenshots/p1-a5/` (4).

**Files changed:**
- `requirements.txt` (django-allauth and its dependencies, 29 pins);
- `settings/base.py` (apps, middleware, the accounts block) and
  `settings/production.py` (a dummy email backend);
- `quadconnect/urls.py` (`accounts/`);
- `views.py` (the home page is public, and shows its dashboard only after
  login);
- `api.py` (only `summary_api` is public and allows any origin; the docs
  page shows the real 401);
- `forms.py` (the login form subclass);
- `base.html` (nav by login state, account links, the logout button);
- `home.html` (a signed-out landing page);
- `api_docs.html`;
- the CSS (account links, the Google button);
- the A3 and A4 tests (they log in first);
- the CI workflow (signed-out and signed-in smoke test, no stored OAuth
  client);
- `db.sqlite3` (rebuilt with the account tables);
- README, notes.txt, this file.

**Decisions that differ from the plan:**
- Private by default through the middleware, not a decorator on each view.
- The Google client lives in `.env`, not in a `SocialApp` row, because the
  database is public.
- The Google Cloud project belongs to adqatar22@gmail.com: Google Cloud is
  switched off for illinois.edu accounts.
- No mail server, so there is no email verification and no password reset
  link.

**Gotchas for the next person:** §11 traps 24–28.

**Verified:** 112 tests and ruff clean. Signed out, every route but the
public two redirects or answers `401`, and signed in, every route opens (a
test walks the whole URLconf). The Vega-Lite spec draws in the editor with no
warnings, from a browser that never logged in.

**Deployed:** 2026-10-09, checked on the live site signed out, signed in,
through sign-up, and through Continue with Google with a real Google account.
**To do:** the team video.

### `main` — P1-A4 merged · 2026-10-05 · PR #9
**Merged:** `feature/p1-a4` into `main` through PR #9. Merge commit
`70d0ad4`. The PR's head had passed the Deploy / test check. Nothing
surfaced at integration. The workflow then moved to `feature/p1-a5`, so
`main` still runs no CI of its own, and there is no automatic deploy.

### BUILT `feature/p1-a4` - Manojkumar Mohankumar - 2026-10-02
**Shipped:** all four P1-A4 parts on one branch cut from `main` at `6ccd9d1`.
Part 1: `/api/summary/` and `/api/summary/matches-per-week/`, and two
Vega-Lite specs that load them through `data.url`, drawn on `/insights/` and
rendered at `/vega-lite/chart1.png` and `/vega-lite/chart2.jpg`. Part 2:
Open Trivia DB icebreakers for each match (`/api/icebreakers/?match=<id>` and
a page). Part 3: student CSV/JSON exports and `/reports/`. Part 4: frozen
requirements, the committed seed database, the install-size check.
Deployed on 2026-10-04 to PythonAnywhere's free plan (user `manojkmohan43`,
teacher `mohitg27`): <https://manojkmohan43.pythonanywhere.com/>.

**Files added:** `connect/vega_charts.py`, `connect/specs/` (2 specs),
`connect/icebreakers.py`, `connect/reports.py`, `connect/tests_a4.py`,
templates `icebreakers.html` and `reports.html`, `static/js/charts.js`,
`static/vendor/vega/` (Vega 6.4.0, Vega-Lite 6.4.3, vega-embed 7.3.0 + BSD
licences), `db.sqlite3`, `docs/screenshots/p1-a4/` (17).

**Files changed:** `requirements.txt` (pip freeze, 23 pins); `.gitignore`
(`db.sqlite3` no longer ignored); `seed_demo_data.py` (16 past matches,
fixed dates, staff accounts); `api.py` (summary endpoints, CORS, docs
examples); `charts.py` and `insights.html` (Figures 3–4); `match_detail.html`
(icebreakers button); `base.html` (Reports link, `scripts` block);
`studentprofile_list.html` (download links); `api_docs.html`; `urls.py`
(9 routes); the CSS; the CI workflow (DB check, size check, A4 smoke test);
README, notes.txt, this file.

**Decisions that differ from the plan:** the chart images are drawn with
the API's rows handed to vl-convert, not by letting it fetch `data.url`,
since a single-worker host would deadlock on a request to itself. A trivia
topic needs at least two members behind it; otherwise it is General
Knowledge. The exports leave out the email.

**Gotchas for the next person:** §11 traps 20–22, and trap 7 again: the
match list and the home page annotated a `Count` with no `order_by()`. It
went unseen while ids matched date order; the seeded history broke that.

**Audit:** three independent reviews (Django, security, WCAG 2.1 AA) before
the push. Fixed: the match order above; vega-embed's menu and hover tooltips
switched off (mouse-only downloads, tooltips that cannot be dismissed);
scrolling tables made focusable regions; card grids fit 320 px;
`/api/summary/` counts verified students and splits same-named interests;
chart images cached a minute, trivia reused 5 s; a BOM on the CSV; CI
rejects extra password hashes in the committed database.

**Verified:** 87 tests; ruff clean; `check --deploy` 0 issues; the whole CI
job on a clean checkout, including a production smoke test of 32 URLs; both
specs run in the Vega-Lite editor against the local API; the Insights page
logs nothing to the console; every page fits 320 px without sideways
scrolling.

### `main` — P1-A3 merged · 2026-09-28 · PR #6
**Merged:** `feature/p1-a3` into `main` through PR #6, merged by Kritika
Agrawal (`agrawal-kritika`). Merge commit `0c69793`.

**What surfaced at integration:** nothing. The PR's head `cb85d4c` had passed
the Deploy / test check, `main` had not moved since `df2c1d1`, and the merged
tree is byte-identical to `cb85d4c` (same tree hash).

**Verified on `main`:** the full CI job, run locally on a clean checkout of
`origin/main` (no `.env`, fresh database): ruff, `check`, no missing
migrations, seed, `verify_constraints` 11/11, 45 tests, `check --deploy`,
`collectstatic`, and the production smoke test all passed. `main` is the
default branch and the repository is public.

**Note:** the workflow runs only on pushes to `feature/p1-a3`, so `main`'s
merge commit shows no check of its own. Add `main` to its branch list to
change that.

### DONE `feature/p1-a3` - Manojkumar Mohankumar - 2026-09-24
**Shipped:** all six P1-A3 sections, solo, on one branch cut from `main` at
`df2c1d1`: detail pages linked through `get_absolute_url()`, a GET + POST
search with aggregates, the site CSS moved to `static/` with production cache
busting, two Matplotlib charts served as PNG endpoints, a POST "suggest a
venue" form on the locations CBV, and a read-only JSON API. Merged into
`main` on 2026-09-28 through PR #6 (see the merge entry above).

**Files added:** `static/css/quadconnect.css`, `static/img/logo.svg`,
`static/fonts/` (Inter + OFL), `connect/forms.py`, `connect/charts.py`,
`connect/api.py`, `connect/tests.py` (was a stub), templates
`match_detail.html`, `campuslocation_detail.html`, `student_search.html`,
`insights.html`, `api_docs.html`, `docs/screenshots/p1-a3/` (19).

**Files changed:** `requirements.txt` (whitenoise, matplotlib);
`settings/base.py` (`STATICFILES_DIRS`, WhiteNoise middleware,
`runserver_nostatic`); `settings/production.py` (manifest storage);
`models.py` (`get_absolute_url()` ×3, no migration); `views.py` (detail views,
search, `CampusLocationListView.post()`, row URLs, plural fix); `urls.py`
(10 new routes); `admin.py` (`is_approved` list-editable); `base.html`
(static assets, 8-link nav with `aria-current`, messages, `page_header`
block); every template (inline styles → classes, lists → `<ul>`);
README, notes.txt, this file.

**Decisions that differ from the plan:** match and venue detail pages shipped
in one commit because each links to the other. The NetID lookup renders from
the POST instead of redirecting, since a redirect would put the NetID in a
URL. Unapproved venues are 404 for non-staff rather than shown with a
banner, so unreviewed suggestions are never published.

**Gotchas for the next person:** see §11 traps 13–19. The expensive ones:
filtering through a relation and then annotating a `Count` over the same
relation counts only the filtered rows; model validators never reach form
widgets; a form action's `#fragment` survives the redirect after it.

**Verified:** 45 tests pass; `check` clean; `check --deploy` 0 issues with
SSL on; `makemigrations --check` no changes; `verify_constraints` 11/11; prod
with `DEBUG=False` serves `quadconnect.<hash>.css` as `immutable` + gzip; every
page fits 375 px; new colour pairs ≥ WCAG AA; keyboard reaches the skip link
first; mutation checks confirm the key tests fail when the code they guard is
removed.

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

### ✅ `feature/profile-views` — Kritika Agrawal — 2026-09-20
**Shipped:** `/students/` lists the verified roster with college, connection
preference, social energy and interest count, filterable by `?college=` and
paginated at 10. `/students/<pk>/` shows one student's preferences,
interests, availability and match history.

**Files added:** `connect/templates/connect/studentprofile_list.html`,
`connect/templates/connect/studentprofile_detail.html`,
`docs/screenshots/04_cbv_generic.png`, `05_list_normal.png`,
`06_list_empty.png`.

**Files changed:** `connect/views.py` — Section B2 only: both stubs replaced
with `StudentProfileListView` and `StudentProfileDetailView`.
`connect/urls.py` — both routes to `.as_view()`. `docs/notes/notes.txt`.

**Decisions that differ from the build task:** none. `template_name` is
deliberately **not** set — the templates are found by Django's naming
convention (`<app>/<model>_list.html`), which is what makes this view the
counterpoint to Prathamesh's hand-written base CBV. Matches and locations set
their template explicitly, so the project shows both conventions.

**Gotchas for the next person:**
- **`annotate()` silently breaks pagination.** Adding `Count(...)` puts a
  `GROUP BY` on the query, and Django then drops `Meta.ordering` from a
  grouped query. Pagination becomes non-deterministic — a row can appear on
  two pages or none. Django only raises `UnorderedObjectListWarning`, not an
  error, so it passes `manage.py check`. Always `.order_by()` explicitly
  after an `annotate()` on a paginated list.
- A generic CBV stops saving you much once the template needs context the
  model does not carry: the filter goes in `get_queryset()`, the filter's own
  UI state goes in `get_context_data()`, and both must call `super()`.

**Verified:** `manage.py check` 0 issues **and no warnings** · `/students/`
200 with 8 · `?college=Grainger` 3 · `?college=Nonexistent` 200 with the
empty state · `/students/1/` 200 · `/students/9999/` **404** · templates
resolved by convention · reflected `?college=` value HTML-escaped ·
`queryset.ordered` is `True`.

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

### ✅ `feature/location-views` — Prathamesh Mulay — 2026-09-20
**Shipped:** `/locations/` lists approved public venues with capacity,
indoor/outdoor and matches hosted, filterable by `?setting=` and `?seats=`.

**Files added:** `connect/templates/connect/location_list.html`;
`docs/screenshots/03_cbv_base.png`; `docs/screenshots/07_cbv_base_empty.png`.

**Files changed:** `connect/views.py` — Section B1 only: `CampusLocationListView`
with `_build_items()` helper. `connect/urls.py` — stub swapped for
`.as_view()`. `docs/notes/notes.txt`, `docs/screenshots/README.md`.

**Decisions that differ from the build task:** added a `?seats=N` minimum-capacity
filter that the task did not ask for. It was necessary: with the seeded data
3 approved venues are indoor and 1 is outdoor, so **no `?setting=` value could
ever empty the list**, and `{% empty %}` was impossible to demonstrate. `?seats=`
is a genuine product query — Squad Connect groups are 4–8 students, so venue
capacity decides where a squad can meet — and `?seats=25` returns nothing.

**Gotchas for the next person:**
- `base.html` defines `.filter` (singular). Using `class="filters"` silently
  renders unstyled controls — no error, it just looks broken.
- When you add a filter, check that at least one value returns **zero rows**.
  A filter that can never empty the list cannot demonstrate `{% empty %}`.
- Parse query params defensively: `?seats=banana` must show the empty state,
  not a 500.
- Docs were originally committed straight to `main` rather than to the branch,
  which left `notes.txt` un-updated and a screenshot named
  `Screenshot _03_cbv_base.png`. Put doc updates on your branch with the code.

**Verified:** `manage.py check` 0 issues · `/locations/` 200 with 4 venues ·
`?setting=indoor` 3, `?setting=outdoor` 1 · `?seats=8` 3, `?seats=13` 1 ·
`?seats=25` and `?seats=banana` both 200 with the empty state, neither a 500 ·
template chain `location_list.html → entity_list.html → base.html` ·
1 SQL query · reflected `?seats=` value HTML-escaped · `entity_list.html` and
`base.html` unmodified by this branch.

### ✅ `feature/feedback-views` - Dhruv Thaker - 2026-09-20

**Shipped:** Implemented the aggregate feedback summary at `/feedback/summary/`, including total submissions, average rating, rating distribution, enjoyment metrics, and stay-connected preferences.

**Files added:** `connect/templates/connect/feedback_summary.html`.

**Files changed:** `connect/views.py` — replaced the feedback stub with an `HttpResponse` FBV using `loader.get_template()` and added aggregate feedback calculations.

**Decisions that differ from the build task:** None.

**Gotchas for the next person:**
- The feedback summary must remain aggregate-only; individual ratings and
  `private_note` values must never be displayed.
- **`loader.get_template()` names the template in a string, so a typo in the
  filename is not caught by `manage.py check`, by any import, or by any
  linter — only by requesting the page.** Load the page in a browser before
  calling a view done. `check` passing means nothing here.

**Found in review — the page returned a 500.** The template was committed as
`feedback_summary.html;` — a **trailing semicolon in the filename** — while the
view loaded `connect/feedback_summary.html`. `/feedback/summary/` raised
`TemplateDoesNotExist`. This had already been merged, so `main` was broken
until the file was renamed. Also completed in review: `notes.txt` (kind A1 was
still `TODO`, reflection blank) and the missing screenshot.

**Verified after the fix:** `manage.py check` 0 issues · `/feedback/summary/`
**200** (was 500) · every other route 200/302 · uses `loader.get_template` +
`HttpResponse`, `render()` not called · `request` passed to `.render()` ·
privacy holds — 2 stored `private_note` values, neither rendered, no
per-student attribution, privacy statement on the page · 2 SQL queries ·
empty state renders (forced in a rolled-back transaction).

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
3. **`DEBUG=False` stops `runserver` serving `/static/`.** A2 kept its CSS
   inline for that reason. A3 moved it to `static/` and added WhiteNoise in the
   same change. Production now needs `collectstatic --noinput` first, or every
   `{% static %}` raises (the manifest does not exist yet).
4. **`db.sqlite3` is committed (since A4), and must hold only seed data.**
   Logging in to the admin locally writes a session row; committing that
   would publish a working session key. Rebuild it instead: delete the
   file, `migrate`, `seed_demo_data`. CI fails if it holds sessions.
5. **`UniqueConstraint` cannot span relations** (see §6).
6. **`private_note` is private.** Never render it, and never show per-student
   ratings. Aggregate only.
7. **`annotate()` drops `Meta.ordering` and breaks pagination.** A `Count`
   annotation adds a `GROUP BY`, and Django ignores default ordering on a
   grouped query. Paginated rows then repeat or vanish. It surfaces only as
   `UnorderedObjectListWarning`. Always `.order_by()` after `annotate()`.
8. **`manage.py check` does not open your page.** A template referenced by
   string — `loader.get_template("...")`, `render(request, "...")`,
   `template_name` — is only resolved at request time. A filename typo passes
   every static check and 500s in the browser. One shipped to `main` as
   `feedback_summary.html;`. **Always load the page.**
9. **Check colour contrast before committing a new colour.** Five pairs in
   the original palette sat between 4.33:1 and 4.47:1 — under the 4.5:1 AA
   minimum, and invisible to the eye. Compute the ratio; do not judge it.
10. **PyMuPDF `insert_textbox` renders nothing** when the rect is too short —
   silently, no exception. Relevant if anyone regenerates the wireframe PNGs.
11. **IEEEtran `\maketitle` cannot run mid-document** — the P1-A1 paper was two
   documents merged with `pypdf`. Its LaTeX sources were deleted; changing
   those PDFs means rebuilding from scratch.
12. **8 models vs P1-A1's "recommended 3–5."** The binding rule was a minimum of
   2 per feature. Do not "fix" this by collapsing models — it would force
   nullable columns meaningless for half the rows.
13. **Filter through a relation, then `Count` it, and you count only the rows
   that matched.** `filter(interest_links__interest__name__icontains="gam")
   .annotate(n=Count("interest_links"))` gives each student the number of
   *matching* interests, not all of them, because Django reuses the join.
   Re-select first: `StudentProfile.objects.filter(pk__in=matches.values("pk"))`.
14. **Spanning a to-many relation in `filter()` duplicates rows.** A student
   with two matching interests comes back twice. Add `.distinct()` (the
   search does, and a test proves it).
15. **Model validators never reach the form widget.** `CampusLocation.capacity`
   validates 2–50, but its `ModelForm` input rendered `min="0"` (from
   `PositiveSmallIntegerField`) and no `max`. Set widget attrs in the form.
16. **A form action's `#fragment` survives the redirect after the POST.** The
   venue form posts to `#suggest`, so after Post/Redirect/Get the browser
   reopened at the form, below the success message. Give the redirect its
   own fragment (`#main`).
17. **CSS specificity: `.form [aria-invalid="true"]` loses to
   `.form input[type="text"]`.** The error border never showed. Qualify it
   with the element (`.form input[aria-invalid="true"]`).
18. **Never `pyplot` in a view.** It keeps every figure in a global registry
   until `plt.close()` (a leak per request), and its default backend here is
   TkAgg, a GUI. Build `matplotlib.figure.Figure` directly and save into
   `BytesIO`. First Matplotlib import builds a font cache (~45 s, once).
19. **Windows tooling:** text-mode `subprocess` stdin turns LF line endings
   into CRLF, so a patch piped to `git apply` stops matching; pass bytes.
   Bash heredocs can eat backslashes in inline Python (this entry lost its
   own escape examples that way); write the script to a file instead.
20. **Vega-Lite warns "Dropping fit-y because spec has discrete height"** for
   `"width": "container"` with a step height (`{"step": 20}`), even though
   nothing is dropped. The bar chart uses a fixed height to keep the
   console and the editor's log clean.
21. **Open Trivia DB answers a second request within 5 seconds with HTTP 429**
   (`response_code` 5), per IP address. `raise_for_status()` turns it into
   an `HTTPError`; the code maps it to 503 with `Retry-After`. Tests mock
   `requests.get`; a manual check needs a 5-second gap between calls.
22. **vl-convert starts its renderer on the first image** a process draws:
   a few seconds, rarely much longer on a busy Windows machine. The
   `--noreload` dev server also caches templates, so restart it after
   editing one.
23. **PythonAnywhere from Windows:** a console created through the API only
   starts once it is opened in a browser. Git Bash rewrites `/home/...`
   arguments into Windows paths (set `MSYS_NO_PATHCONV=1`). And the live
   `db.sqlite3` on the server lived in the repository (`--skip-worktree`)
   until A5. Since A5 it is `~/quadconnect-data/db.sqlite3` (`DJANGO_DB_PATH`),
   so `git pull` never touches live accounts.
24. **With `LoginRequiredMiddleware`, every test client must log in.** A
   test that gets a page now gets a redirect to the login page instead.
   Log in once in a base class's `setUp()`, and every subclass that
   defines its own `setUp()` must call `super().setUp()`: 20 tests failed
   until two classes did.
25. **Creating users with a password makes tests slow.** Each hash costs
   real time. Create test users with `create_user("name")` (no password)
   and `force_login()`: the suite went from 126 s to about 63 s.
26. **allauth's login form links to password reset** in the password
   field's help text, and that needs a mail server we do not have. It is
   removed in `connect.forms.LoginForm`, wired in with `ACCOUNT_FORMS`.
27. **Google Cloud is switched off for illinois.edu accounts**, and
   Google refuses to sign in to Gmail in a browser driven by automation
   ("This browser or app may not be secure"). Set up OAuth clients in a
   normal browser with a personal Google account.
28. **`ruff check .` lints notebooks too.** A committed `.ipynb` under
   `docs/` is checked like any `.py` file, so CI fails on a notebook's
   lint error.
29. **bfloat16 is slow on a CPU without native support.** On our Ryzen 7
   6800HS, Qwen2.5-1.5B took 49.8 s to read a 503-token prompt in bfloat16
   and 6.9 s in float32; 4-bit NF4 computing in float32 took 14.7 s. Use
   float32 on CPUs and bfloat16 on GPUs (both the notebook and
   `ai_search.py` do).
30. **The Hugging Face cache on Windows** copies files instead of linking
   them unless Developer Mode is on (a warning, not an error), and
   downloads without `HF_TOKEN` are rate-limited (about 12 MB/s here).
31. **ruff's import sorter wraps imports longer than 88 characters**, even
   though line length (E501) is not checked: write long imports in the
   wrapped form, or `ruff check --fix` does it.
32. **`python -I` ignores `PYTHONIOENCODING`.** Print non-ASCII text from an
   isolated script with `sys.stdout.reconfigure(encoding="utf-8")`.
33. **"afternoon" contains "noon".** Keyword patterns need word boundaries
   (`\bnoon`); a test caught the keyword parser reading "Saturday
   afternoon" as midday.
34. **Never let a test reach a real model or API.** The venue form tests
   (P1-A3) post suggestions, so they run with `AI_API_KEY=""`; the A6 tests
   patch `generate_reply` and `requests.post`; CI sets
   `AI_LOCAL_ENABLED=0`, or a stray call would download gigabytes.
35. **`torch` from PyPI on Linux is the CUDA build** (several GB). CI and
   any CPU-only Linux host should add
   `--extra-index-url https://download.pytorch.org/whl/cpu`; the free
   PythonAnywhere plan cannot hold torch at all, and does not need it (the
   search falls back to keywords).

---

## 12. Assignment history

### P1-A1 — Product + Data Models + UI/UX (35 pts) — submitted
Four uploads: the TCC workbook, the Idea Description PDF (rebuilt in genuine
IEEE two-column after the original was single-column), the Wireframes PDF
(rebuilt low-fidelity after the original was high-fidelity Figma screenshots,
with those kept as an iteration-v2 appendix), and the Django project ZIP.
Deliverables live outside this repo in the workspace `SUBMIT/` folder.

### P1-A2 — Fullstack Development + GitHub Secrets (30 pts) — submitted
Section 1 structure/security/GitHub done on `main`; the four feature
branches merged one at a time (see §9). Submission was one item: the public
GitHub repository URL.

### P1-A3 — URLs, ORM, static files, charts, forms, API (60 pts) — merged, to submit
Built by Manojkumar alone on `feature/p1-a3`; all six sections done and
verified (§9). Merged into `main` on 2026-09-28 through PR #6. Submission is
one item, the public repository URL, due Mon 2026-09-28 at 23:59. The
notes.txt answers the assignment asks for are in its section 2; screenshots
in `docs/screenshots/p1-a3/`.

### P1-A4 — APIs, Vega-Lite charts, exports, static files, deployment (40 pts) — merged, submitted
Built by Manojkumar on `feature/p1-a4` (§9). Due Mon 2026-10-05 at 23:59.
Submission: the Vega-Lite specs (`connect/specs/`) and screenshots of the
working charts (`docs/screenshots/p1-a4/`), in the repository. Deployed to
PythonAnywhere on 2026-10-04: <https://manojkmohan43.pythonanywhere.com/>, user `manojkmohan43`, teacher
`mohitg27`. Merged into `main` through PR #9 on 2026-10-05.

### P1-A5.1 — Authentication, Google OAuth, public API, project video (50 pts) — merged, submitted
Built on `feature/p1-a5` (§9). Due Mon 2026-10-12. No new repository; the
live site must run the logged-in version. Submission:
- the public API's production URL,
  <https://manojkmohan43.pythonanywhere.com/api/summary/>;
- the GitHub URL;
- `docs/a5/group-13-vega-lite-API-demo.txt` and its editor screenshot
  (`docs/screenshots/p1-a5/01_vega_editor_public_api.png`);
- the team video as a downloadable file, 300 seconds at most. It opens with
  a slide (members and emails, product name and title, course) and the
  required spoken introduction, then demonstrates the live site.

Merged into `main` through PR #10 on 2026-10-12; the video is in the
workspace `SUBMIT/` folder.

### P1-A5.2 — Individual deployment and external feedback (20 pts, individual)
Each member deploys the site on their own PythonAnywhere account and collects
written feedback from five people outside the class. Dhruv's deployment
(`dthaker6.pythonanywhere.com`) uses the team's Google client; its callback
was added on 2026-10-13.

### P1-A6 — Text Intelligence (100 pts) — building
Built on `feature/p1-a6` (§9). Due Mon 2026-10-19. Submission: the GitHub URL
with the Django code and `llm-test/ai_prototype.ipynb` (Route A, so no
fine-tuning notebook). Part 2 is `README_AI.md` (now `docs/README_AI_P1-A6.md`); Part 3 is section 3 of
`docs/notes/notes.txt`.

### Next
The matching algorithm remains the biggest open design question:
`compatibility_score` and `match_reason` are fields that nothing computes
outside seed data. Weighting, normalisation to 0–100, squad formation for
4–8 people, tie-breaking, starvation avoidance, and generating `match_reason`
from the same computation so the explanation cannot drift from the score.
