# Build Task — Kritika Agrawal

| | |
|---|---|
| **Branch** | `feature/profile-views` |
| **Graded view kind** | **B2 — Generic Class-Based View** |
| **Feature area** | Onboarding & student profiles (wireframe Screens 1–2) |
| **Model** | `StudentProfile` |
| **Routes** | `/students/` → `connect:student-list`<br>`/students/<pk>/` → `connect:student-detail` |
| **Templates** | `connect/studentprofile_list.html`, `connect/studentprofile_detail.html` |

Read [`README.md`](README.md) in this folder first — it has the ground rules
and setup. Yours is the view the grader will check for **Generic CBV (2 pts)**.

## Start here

```bash
git clone https://github.com/manojkmohan5/13_QuadConnect.git
cd 13_QuadConnect
git switch feature/profile-views          # your branch, already on the remote

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
python manage.py runserver          # http://127.0.0.1:8000/students/ shows a stub
```

You should see a placeholder page at `/students/` saying "Not implemented yet".
Replacing it is your whole task. Work through the steps below in order, then
tick every box in the Done checklist at the bottom.

---

## What you are building

A browsable roster of verified students, using Django's generic `ListView` so
that pagination, `context_object_name` and template naming come for free —
plus a `DetailView` for one student.

Deliberately use **Django's default template naming convention**
(`<app>/<model>_list.html`, lowercased, no underscore between model words) so
the deck demonstrates both conventions: yours by convention, the other two by
explicit `template_name`. Do not set `template_name` — let Django find it.

### The `?college=` filter matters

It is not decoration. It is how the team produces the **empty-state
screenshot** required by Section 3 without deleting data. Visiting
`/students/?college=Nonexistent` must render your `{% empty %}` branch.

---

## Step 1 — replace the stub in `views.py`

In `connect/views.py`, find:

```
# Section B2 - Generic Class-Based View (ListView / DetailView)
# OWNER: Kritika Agrawal (kritika7)
```

Delete `student_profile_list_stub` and `student_profile_detail_stub` and write
your views in that section. Add the generic-view import at the top of the file
(`from django.views.generic import DetailView, ListView`).

### `StudentProfileListView`

Requirements the rubric checks:

- inherits `ListView`
- sets `model = StudentProfile`
- sets `context_object_name` (use `students`)
- relies on Django's default template name

Behaviour:

- `paginate_by = 10`
- `get_queryset()` — start from `StudentProfile.objects.all()`; if a non-empty
  `college` query parameter is present, filter with
  `college__icontains=<value>`. Keep the model's default ordering.
- `get_context_data()` — also pass:
  - `selected_college` — the raw query parameter, so the filter box can
    re-display what was typed
  - `colleges` — the distinct list of colleges actually present, for a
    datalist. `StudentProfile.objects.values_list("college", flat=True).distinct()`
  - `total_count` — the unfiltered count, so the page can say
    "3 of 8 students"

Avoid the N+1: the list shows each student's interest count, so use
`.annotate(interest_count=Count("interest_links"))`.

### `StudentProfileDetailView`

- inherits `DetailView`, `model = StudentProfile`, `context_object_name = "student"`
- in `get_context_data()`, add the student's interests and availability. Use
  `select_related`/`prefetch_related` so the page is a small, fixed number of
  queries:
  - `interest_links` → `select_related("interest")`, primary ones first
  - `availability_slots`
  - `match_participations` → `select_related("match", "match__location")`

---

## Step 2 — update `urls.py`

Swap your two lines only. **Path and `name=` must not change.**

```python
path("students/", views.StudentProfileListView.as_view(), name="student-list"),
path("students/<int:pk>/", views.StudentProfileDetailView.as_view(),
     name="student-detail"),
```

---

## Step 3 — templates

Create both under `connect/templates/connect/`.

### `studentprofile_list.html`

```
{% extends "connect/base.html" %}
```

Must contain:

- `{% block title %}` and `{% block heading %}`
- a `<form method="get">` filter with an `<input name="college">` pre-filled
  from `selected_college`, a submit button, and a "Clear" link back to
  `{% url 'connect:student-list' %}` shown only when a filter is active
- a `{% for student in students %}` loop. For each: full name (linked to
  `{% url 'connect:student-detail' student.pk %}`), NetID, college,
  department, `get_preferred_connection_display`,
  `get_social_energy_display`, interest count
- a `{% empty %}` branch — see the wording rule below
- pagination controls when `is_paginated`

Reuse the CSS classes already in `base.html`: `card`, `row`, `title`,
`subtitle`, `meta`, `badge`, `empty`, `filter`. Do not write a new stylesheet.

### `studentprofile_detail.html`

Extends the same base. Show the student's identity, their preference fields,
their starred and regular interests, their weekend availability, and their
match history. Link back to the list.

---

## The empty state

A blank page is not an empty state. It must say **what is empty and what to do
next**, and it must change depending on *why* it is empty:

- filter active, no matches → name the filter value and offer the Clear link
- no students at all → tell the reader to run `seed_demo_data`

```
{% empty %}
  <div class="empty">
    {% if selected_college %}
      <div class="big">No students in "{{ selected_college }}"</div>
      <p>No verified student has a college matching that text.
         <a href="{% url 'connect:student-list' %}">Clear the filter</a>
         to see all {{ total_count }} students.</p>
    {% else %}
      <div class="big">No students yet</div>
      <p>Run <code>python manage.py seed_demo_data</code> to load the sample
         roster.</p>
    {% endif %}
  </div>
{% endfor %}
```

---

## Step 4 — verify

```bash
python manage.py check
python manage.py runserver
```

| URL | Expect |
|---|---|
| `/students/` | 200, 8 students, nav and footer visible |
| `/students/?college=Grainger` | 200, filtered subset, Clear link shown |
| `/students/?college=Nonexistent` | 200, **empty state**, not a blank page |
| `/students/1/` | 200, one student's detail |
| `/students/9999/` | 404 (DetailView handles this for free) |

Check the template Django actually used — it proves you followed the default
naming convention rather than getting lucky:

```bash
python -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','quadconnect.settings.development')
django.setup()
from django.test import Client
r = Client().get('/students/')
print('status', r.status_code)
print('templates', [t.name for t in r.templates if t.name])
print('context key students ->', len(r.context['students']))
"
```

---

## Step 5 — screenshots

Save into `docs/screenshots/`:

| File | Shows |
|---|---|
| `04_cbv_generic.png` | `/students/` populated — **your graded evidence** |
| `05_list_normal.png` | `/students/` populated (Section 3 normal state) |
| `06_list_empty.png` | `/students/?college=Nonexistent` — the empty state |

Full browser window, address bar visible.

---

## Step 6 — notes

In `docs/notes/notes.txt`:

1. **VIEW REGISTER → KIND B2** — change `Status: TODO` to `Status: DONE`, and
   correct anything that drifted from what you actually built.
2. **REFLECTION → Base CBV vs Generic CBV** — replace the `[Kritika] TODO`
   line. Answer honestly and concretely: what did `ListView` hand you for
   free, and where did it get in the way when you added `?college=`? Naming
   the friction is what earns the bonus, not praising the framework.
3. **WEEKLY LOG** — add a line under Week 3 for what you finished.

---

## Step 7 — update `CLAUDE.md` (REQUIRED, do this last)

`CLAUDE.md` at the repo root is the team's shared memory. It is how the next
person — and the next AI assistant — knows what already exists. It is **not**
part of the Canvas submission; we keep it purely for our own knowledge.

Two edits, both in your own row/block only:

**1. Status board (§0)** — change your row from `NOT STARTED` to done:

```
| Kritika Agrawal | `feature/profile-views` | Generic CBV | <route> | DONE - <one line on what shipped> |
```

**2. Work log (§9)** — replace your placeholder block using this exact shape,
so every entry reads the same way:

```markdown
### DONE `feature/profile-views` - Kritika Agrawal - YYYY-MM-DD
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

Roughly one commit per step; small and imperative.

```
Add StudentProfileListView generic CBV with college filter
Add student list template with filter and empty state
Add StudentProfileDetailView with interests and availability
Add student detail template
Record generic CBV in notes and add screenshots
```

---

## Done checklist

- [ ] `python manage.py check` → 0 issues
- [ ] `/students/` returns 200 and extends `base.html`
- [ ] `context_object_name = "students"` and `model = StudentProfile` set
- [ ] Default template naming used — no `template_name` attribute
- [ ] `{% for %}` + `{% empty %}` both render
- [ ] `?college=Nonexistent` shows the empty state, not a blank page
- [ ] `/students/1/` detail page works, `/students/9999/` 404s
- [ ] 3 screenshots saved with the exact filenames above
- [ ] `notes.txt` VIEW REGISTER marked DONE + reflection written
- [ ] `base.html` untouched · other owners' sections untouched
- [ ] `CLAUDE.md` status board row + work log block updated
- [ ] Branch pushed, PR opened against `main`
