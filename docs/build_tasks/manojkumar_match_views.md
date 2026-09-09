# Build Task — Manojkumar Mohankumar

| | |
|---|---|
| **Branch** | `feature/match-views` |
| **Graded view kind** | **A2 — Function-Based View using `render()`** |
| **Feature area** | Matching engine (wireframe Screens 3, 6–7) |
| **Model** | `Match` |
| **Route** | `/matches/` → `connect:match-list` |
| **Template** | `connect/entity_list.html` — **SHARED, already exists, do not edit** |

Read [`README.md`](README.md) in this folder first. Yours is the view the
grader checks for **`render()` FBV (2 pts)** — and, together with Prathamesh,
for **template reuse (2 pts)**.

---

## What you are building

A list of every weekly scheduled experience — location, activity, participant
count, status — filterable by week.

The interesting constraint: you and Prathamesh render **the same template**
from two different view styles. `entity_list.html` knows nothing about any
model. Your view's job is to turn a `Match` queryset into the plain
dictionaries that template expects. That separation is the point of the
exercise: the template is independent of how the data was produced.

**Do not edit `entity_list.html`.** If the contract genuinely cannot express
what you need, agree a change with Prathamesh first, since it breaks his page
too.

### The template's context contract

Documented at the top of `entity_list.html`. In full:

| Key | Type | Meaning |
|---|---|---|
| `page_title` | str | `<title>` text |
| `heading` | str | page heading |
| `subtitle` | str | optional line under the heading |
| `items` | list[dict] | the rows |
| `empty_title` | str | headline when `items` is empty |
| `empty_message` | str | explanatory line when empty |

Each item dict: `title` (required), `subtitle`, `meta` (list of short strings
rendered inline), `badge` (pill on the right), `url` (makes the title a link).

---

## Step 1 — replace the stub in `views.py`

In `connect/views.py`, find:

```
# Section A2 - Function-Based View using the render() shortcut
# OWNER: Manojkumar Mohankumar (mm240)
```

Replace `match_list` in that section.

Requirements the rubric checks:

- a **function**, not a class
- queries the model
- builds a **context dictionary**
- returns **`render(request, template, context)`** — not `HttpResponse`, not
  `loader.get_template`

Behaviour:

- Base queryset: `Match.objects.select_related("location", "suggested_activity")`
  then `.annotate(headcount=Count("participants"))`.
  `select_related` matters — the template reads `location.name` for every row,
  and without it you issue one extra query per match.
- If a non-empty `week` query parameter is present, parse it as `YYYY-MM-DD`
  and filter `week_start=<date>`. **Handle an unparseable value gracefully** —
  show the empty state with a message saying the date was not understood, do
  not raise a 500.
- Shape each match into the item contract:
  - `title` → `match.get_connection_type_display()`
  - `subtitle` → the location name and street address
  - `meta` → scheduled date/time, headcount with pluralisation, the suggested
    activity name (or "No activity suggested"), and the check-in code
  - `badge` → `match.get_status_display()`
- Pass `page_title`, `heading`, `subtitle`, `empty_title`, `empty_message`.

Keep the row-shaping in a small module-level helper so the view body stays
readable — the rubric awards a point for code clarity.

---

## Step 2 — update `urls.py`

Your line already points at `views.match_list`. If your function keeps that
name, **no change is needed**. Do not alter the path or the `name=`.

---

## Step 3 — the filter UI

`entity_list.html` exposes `{% block filters %}`, but you cannot add markup to
a shared template from your view. Two acceptable options — pick one:

**Option A (preferred).** Create `connect/match_list.html` that is three lines:

```
{% extends "connect/entity_list.html" %}
{% block filters %}
  … your week filter form …
{% endblock %}
```

Then `render()` that. You still reuse the shared list body and empty state
through inheritance, which demonstrates reuse *and* keeps your filter yours.

**Option B.** Render `entity_list.html` directly with no filter UI, and reach
the empty state by typing `?week=1999-01-01` in the address bar.

Option A is better work and reads better in the screenshot. Either satisfies
the assignment.

---

## The empty state

The shared template renders `empty_title` and `empty_message` for you — but
they must be *useful*, and they must differ by cause:

| Situation | `empty_title` | `empty_message` |
|---|---|---|
| Week filter matched nothing | `No matches for week of <date>` | Say which week, and how to clear the filter |
| Date could not be parsed | `Could not read that date` | Show the expected `YYYY-MM-DD` format |
| No matches at all | `No matches scheduled yet` | Tell the reader to run `seed_demo_data` |

---

## Step 4 — verify

```bash
python manage.py check
python manage.py runserver
```

| URL | Expect |
|---|---|
| `/matches/` | 200, 3 matches, nav and footer visible |
| `/matches/?week=2026-09-07` | 200, only that week's matches |
| `/matches/?week=1999-01-01` | 200, **empty state** |
| `/matches/?week=banana` | 200, empty state with the format hint — **not a 500** |

Confirm `render()` really used the shared template, and count queries so the
`select_related` is doing its job:

```bash
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','quadconnect.settings.development')
django.setup()
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
c = Client()
with CaptureQueriesContext(connection) as q:
    r = c.get('/matches/')
print('status', r.status_code)
print('templates', [t.name for t in r.templates if t.name])
print('queries', len(q))   # single digits; if it scales with match count, fix select_related
"
```

`entity_list.html` must appear in that template list.

---

## Step 5 — screenshot

Save into `docs/screenshots/`:

| File | Shows |
|---|---|
| `02_fbv_render.png` | `/matches/` populated — **your graded evidence** |

Full browser window, address bar visible.

---

## Step 6 — notes

In `docs/notes/notes.txt`:

1. **VIEW REGISTER → KIND A2** — `Status: TODO` → `Status: DONE`; correct
   anything that drifted. If you took Option A, record that the template is
   `connect/match_list.html` extending the shared `entity_list.html`.
2. **REFLECTION → HttpResponse vs render()** — replace the
   `[Manojkumar] TODO` line. Concretely: what did `render()` save you compared
   with Dhruv's manual path — the `RequestContext`, the template loading, the
   `HttpResponse` wrapping?
3. **WEEKLY LOG** — add a line for what you finished.

---

## Commit sequence

```
Add match_list FBV using render() with week filter
Add match_list template extending shared entity_list
Handle unparseable week parameter with a helpful empty state
Record render() FBV in notes and add screenshot
```

---

## Done checklist

- [ ] `python manage.py check` → 0 issues
- [ ] `/matches/` returns 200 and extends `base.html`
- [ ] View is a **function** and returns **`render(...)`**
- [ ] Renders the **shared** `entity_list.html` (directly or by extending it)
- [ ] `entity_list.html` itself is **unmodified**
- [ ] `{% for %}` + `{% empty %}` both render
- [ ] `?week=1999-01-01` → empty state · `?week=banana` → empty state, no 500
- [ ] Query count does not grow with the number of matches
- [ ] `02_fbv_render.png` saved
- [ ] `notes.txt` VIEW REGISTER marked DONE + reflection written
- [ ] `base.html` untouched · other owners' sections untouched
- [ ] Branch pushed, PR opened against `main`

---

## Also yours as repo owner

After all four PRs are merged: add **`27guptamohit`** as a collaborator, take
the remaining screenshots, complete the reflection's team-level line, and
submit the repository URL on Canvas.
