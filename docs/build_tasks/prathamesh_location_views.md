# Build Task — Prathamesh Mulay

| | |
|---|---|
| **Branch** | `feature/location-views` |
| **Graded view kind** | **B1 — Base Class-Based View (inherits `django.views.View`)** |
| **Feature area** | Availability, scheduling, check-in (wireframe Screens 5, 8) |
| **Model** | `CampusLocation` |
| **Route** | `/locations/` → `connect:location-list` |
| **Template** | `connect/entity_list.html` — **SHARED, already exists, do not edit** |

Read [`README.md`](README.md) in this folder first. Yours is the view the
grader checks for **Base CBV (2 pts)** — and, together with Manojkumar, for
**template reuse (2 pts)**.

## Start here

```bash
git clone https://github.com/manojkmohan5/13_QuadConnect.git
cd 13_QuadConnect
git switch feature/location-views          # your branch, already on the remote

python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# .venv\Scripts\activate           # PowerShell
# source .venv/bin/activate        # macOS / Linux

pip install -r requirements.txt
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
# paste that value into DJANGO_SECRET_KEY in .env

python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver          # http://127.0.0.1:8000/locations/ shows a stub
```

You should see a placeholder page at `/locations/` saying "Not implemented yet".
Replacing it is your whole task. Work through the steps below in order, then
tick every box in the Done checklist at the bottom.

---

## What you are building

A list of approved public meeting places — the venues QuadConnect is allowed
to schedule a match at — showing capacity, indoor/outdoor, and how many
matches each has hosted.

The point of this task is contrast. Kritika's `ListView` does the querying,
context naming and template lookup for her. You do all three **by hand** in
`get()`. Write it so a reader can see exactly what a generic view would have
done for you — that is what earns the reflection bonus later.

You render the **same** `entity_list.html` as Manojkumar, from a completely
different view style. That is the template-reuse deliverable.

**Do not edit `entity_list.html`.** If the contract genuinely cannot express
what you need, agree a change with Manojkumar first — it breaks his page too.

### The template's context contract

Documented at the top of `entity_list.html`:

| Key | Type | Meaning |
|---|---|---|
| `page_title` | str | `<title>` text |
| `heading` | str | page heading |
| `subtitle` | str | optional line under the heading |
| `items` | list[dict] | the rows |
| `empty_title` | str | headline when `items` is empty |
| `empty_message` | str | explanatory line when empty |

Each item dict: `title` (required), `subtitle`, `meta` (list of short strings),
`badge` (pill on the right), `url` (makes the title a link).

---

## Step 1 — replace the stub in `views.py`

In `connect/views.py`, find:

```
# Section B1 - Base Class-Based View (inherits django.views.View)
# OWNER: Prathamesh Mulay (pmulay2)
```

Delete `campus_location_list_stub` and write `CampusLocationListView` there.
Add `from django.views import View` at the top of the file.

Requirements the rubric checks:

- inherits **`django.views.View`** — *not* `ListView`, *not* `TemplateView`
- implements **`get(self, request)`**
- queries the model **manually** (`CampusLocation.objects.…`)
- returns a rendered template with context

Behaviour:

- Query `CampusLocation.objects.annotate(match_count=Count("matches"))`.
  The `matches` reverse accessor is defined by `Match.location`'s
  `related_name`. Without the annotate you would query inside the loop.
- Support a `?setting=` filter with three values:
  - `indoor` → `is_indoor=True`
  - `outdoor` → `is_indoor=False`
  - anything else or absent → no filter
  This is how you reach the empty state without deleting data — pick whichever
  value returns nothing in the seeded set, or add a `?setting=` value that
  matches no rows.
- Also expose only approved venues by default (`is_approved=True`), and say so
  in the subtitle. Unapproved venues exist so they can be retired without
  losing history — see `docs/project_reference.md` §5.
- Shape each row into the item contract:
  - `title` → the venue name
  - `subtitle` → the street address
  - `meta` → indoor/outdoor, `Seats up to N`, `Hosted N matches`, and the
    arrival note if present
  - `badge` → `Indoor` or `Outdoor`
- Return `render(request, "connect/entity_list.html", context)`.

`render()` is fine here — the graded distinction for your view is
**base `View` vs generic `ListView`**, not how the response is produced.
Manojkumar owns the `render()` demonstration; Dhruv owns the manual
`HttpResponse` one.

Keep the row-shaping in a small helper method on the class (e.g.
`_build_items(self, queryset)`) so `get()` stays short. A point is awarded for
code clarity.

---

## Step 2 — update `urls.py`

Swap your one line. **Path and `name=` must not change.**

```python
path("locations/", views.CampusLocationListView.as_view(), name="location-list"),
```

`.as_view()` is required — a class cannot be a URL target directly. Forgetting
it is the single most common mistake with CBVs, and the error message
(`__init__() takes 1 positional argument but 2 were given`) does not obviously
point at it.

---

## Step 3 — the filter UI (optional but encouraged)

`entity_list.html` exposes `{% block filters %}`. To add a filter form without
touching the shared template, create `connect/location_list.html`:

```
{% extends "connect/entity_list.html" %}
{% block filters %}
  … your indoor/outdoor filter form …
{% endblock %}
```

…and render that instead. You still reuse the shared list body and empty state
through inheritance. If you skip this, reach the empty state by typing the
query parameter in the address bar.

---

## The empty state

The shared template renders `empty_title` and `empty_message`. Make them
useful, and make them differ by cause:

| Situation | `empty_title` | `empty_message` |
|---|---|---|
| Filter matched nothing | `No indoor venues approved` | Name the filter and how to clear it |
| No venues at all | `No approved campus locations` | Say that matches cannot be scheduled until a venue is approved, and to run `seed_demo_data` |

That second message is worth writing properly — an empty venue list is a real
product state, not just a rendering edge case. No venues means no meetings can
be scheduled at all.

---

## Step 4 — verify

```bash
python manage.py check
python manage.py runserver
```

| URL | Expect |
|---|---|
| `/locations/` | 200, 4 venues, nav and footer visible |
| `/locations/?setting=outdoor` | 200, only The Main Quad |
| `/locations/?setting=indoor` | 200, the three indoor venues |
| a filter matching nothing | 200, **empty state** |

Confirm the class really is a base `View` and that the shared template was used:

```bash
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','quadconnect.settings.development')
django.setup()
from django.views import View
from django.views.generic import ListView
from connect.views import CampusLocationListView as V
print('inherits View     :', issubclass(V, View))
print('inherits ListView :', issubclass(V, ListView), '(must be False)')
from django.test import Client
r = Client().get('/locations/')
print('status', r.status_code)
print('templates', [t.name for t in r.templates if t.name])
"
```

`entity_list.html` must appear, and `inherits ListView` must print `False`.

---

## Step 5 — screenshot

Save into `docs/screenshots/`:

| File | Shows |
|---|---|
| `03_cbv_base.png` | `/locations/` populated — **your graded evidence** |

Full browser window, address bar visible.

---

## Step 6 — notes

In `docs/notes/notes.txt`:

1. **VIEW REGISTER → KIND B1** — `Status: TODO` → `Status: DONE`; correct
   anything that drifted from what you built.
2. **REFLECTION → Base CBV vs Generic CBV** — replace the `[Prathamesh] TODO`
   line. Be concrete: list what you had to write by hand in `get()` that
   Kritika's `ListView` did for her — the queryset, `context_object_name`, the
   template name, pagination. Then say when writing it yourself is *worth* it.
3. **WEEKLY LOG** — add a line for what you finished.

---

## Step 7 — update `docs/project_reference.md` (REQUIRED, do this last)

`docs/project_reference.md` is the team's shared memory. It is how the next
person knows what already exists. It is **not**
part of the Canvas submission; we keep it purely for our own knowledge.

Two edits, both in your own row/block only:

**1. Status board (§0)** — change your row from `NOT STARTED` to done:

```
| Prathamesh Mulay | `feature/location-views` | Base CBV | <route> | DONE - <one line on what shipped> |
```

**2. Work log (§9)** — replace your placeholder block using this exact shape,
so every entry reads the same way:

```markdown
### DONE `feature/location-views` - Prathamesh Mulay - YYYY-MM-DD
**Shipped:** one sentence on what the view does.
**Files added:** paths.
**Files changed:** paths, and what changed in each.
**Decisions that differ from the build task:** anything you did differently,
and why. Write "none" if there were none.
**Gotchas for the next person:** anything that surprised you, cost you time,
or that someone extending this view must know. Write "none" if there were none.
**Verified:** manage.py check clean / route returns 200 / empty state renders /
screenshot saved.
```

If you hit a trap worth warning others about, also add it to **§11 Traps**.

**Only touch your own row and your own block.** Four people edit this file; git
merges different lines cleanly but conflicts on the same line.

---

## Commit sequence

```
Add CampusLocationListView base CBV with manual queryset
Wire location-list route to the class-based view
Add indoor/outdoor filter extending shared entity_list
Record base CBV in notes and add screenshot
```

---

## Done checklist

- [ ] `python manage.py check` → 0 issues
- [ ] `/locations/` returns 200 and extends `base.html`
- [ ] Class inherits `django.views.View`, **not** a generic view
- [ ] `get()` implemented with a hand-written queryset
- [ ] `.as_view()` used in `urls.py`
- [ ] Renders the **shared** `entity_list.html` (directly or by extending it)
- [ ] `entity_list.html` itself is **unmodified**
- [ ] `{% for %}` + `{% empty %}` both render
- [ ] A filter value reaches the empty state without deleting data
- [ ] Query count does not grow with the number of venues
- [ ] `03_cbv_base.png` saved
- [ ] `notes.txt` VIEW REGISTER marked DONE + reflection written
- [ ] `base.html` untouched · other owners' sections untouched
- [ ] `docs/project_reference.md` status board row + work log block updated
- [ ] Branch pushed, PR opened against `main`
