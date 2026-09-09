# Build Task — Dhruv Thaker

| | |
|---|---|
| **Branch** | `feature/feedback-views` |
| **Graded view kind** | **A1 — Function-Based View returning `HttpResponse` manually** |
| **Feature area** | Social preferences & feedback (wireframe Screens 4, 9) |
| **Model** | `ExperienceFeedback` |
| **Route** | `/feedback/summary/` → `connect:feedback-summary` |
| **Template** | `connect/feedback_summary.html` — **yours, create it** |

Read [`README.md`](README.md) in this folder first. Yours is the view the
grader checks for **`HttpResponse` FBV (2 pts)**.

---

## What you are building

A read-only summary of private post-experience feedback: average rating, how
many students opted in to stay connected, and which enjoyment factors came up
most often.

Your view is the one that does **not** use the `render()` shortcut. You load
the template yourself and wrap the result in an `HttpResponse`. That is the
whole point — it shows the request/response cycle that `render()` hides.

```python
from django.http import HttpResponse
from django.template import loader

template = loader.get_template("connect/feedback_summary.html")
return HttpResponse(template.render(context, request))
```

Pass `request` as the second argument to `.render()`. Without it the template
has no `RequestContext`, so context processors do not run — and `{% url %}` in
`base.html` would still work, but anything depending on `request` would not.
Passing it is what makes the manual path equivalent to `render()`.

---

## Privacy rule — read this before you write the query

`ExperienceFeedback.private_note` is **private**. `CLAUDE.md` §2 states it is
never shown to other participants, and the wireframe on Screen 9 promises the
student exactly that.

Your page is **aggregate only**. Do not render `private_note`. Do not render
which individual student left which rating. Counts, averages and distributions
only. If a number would identify one person's opinion, do not show it.

This is a product rule, not a style preference. Breaking it contradicts the
paper and the wireframes.

---

## Step 1 — replace the stub in `views.py`

In `connect/views.py`, find:

```
# Section A1 - Function-Based View returning HttpResponse manually
# OWNER: Dhruv Thaker (dthaker3)
```

Replace `feedback_summary` in that section.

Requirements the rubric checks:

- a **function**, not a class
- uses `loader.get_template(...)` and wraps the result in `HttpResponse`
- **does not** call `render()`

Behaviour — build a context containing:

- `total` — number of feedback submissions
- `average_rating` — `ExperienceFeedback.objects.aggregate(Avg("rating"))`
- `distribution` — a list of `(stars, count, percent)` for 1–5, so the
  template can draw a simple bar. Include stars with zero responses; a rating
  nobody gave is information too.
- `enjoyment` — a list of `(label, count)` for the four boolean fields
  `enjoyed_conversation`, `enjoyed_shared_interests`, `enjoyed_activity`,
  `felt_comfortable`. Use one `aggregate()` with `Count(..., filter=Q(...))`
  rather than four separate queries.
- `wants_connection` — how many said `wants_to_stay_connected=True`
- `mutual_pairs` — **only if you have time**: for Friend Connect matches where
  *both* participants opted in. This is the mutual-connection rule from
  `CLAUDE.md` §2. If it turns out fiddly, skip it and note it in `notes.txt`
  as an open item — a correct simple page beats a half-working clever one.

Keep the aggregation in a module-level helper so the view body stays short.
A point is awarded for code clarity.

---

## Step 2 — `urls.py`

Your line already points at `views.feedback_summary`. If your function keeps
that name, **no change is needed**. Do not alter the path or the `name=`.

---

## Step 3 — the template

Create `connect/templates/connect/feedback_summary.html`.

It still extends the shared base — loading a template manually has nothing to
do with skipping inheritance:

```
{% extends "connect/base.html" %}
```

Must contain:

- `{% block title %}` and `{% block heading %}`
- headline stats using the `card` / `stat` / `grid` classes already in
  `base.html`
- a `{% for %}` loop over `distribution` **with an `{% empty %}` branch**
- a `{% for %}` loop over `enjoyment`
- a short line stating that feedback is private and aggregated

Do not write a new stylesheet. Reuse `card`, `grid`, `stat`, `row`, `meta`,
`badge`, `empty`.

---

## The empty state

Your page has a genuine empty state: a matching cycle that has run but where
nobody has submitted feedback yet.

```
{% empty %}
  <div class="empty">
    <div class="big">No feedback submitted yet</div>
    <p>Feedback appears here once students complete a match and submit the
       Screen 9 form. Run <code>python manage.py seed_demo_data</code> to load
       sample responses.</p>
  </div>
{% endfor %}
```

To see it without deleting data, run the dev server against a scratch database
so your real one is untouched:

```bash
DJANGO_SETTINGS_MODULE=quadconnect.settings.development \
python -c "
import os,django
os.environ['DJANGO_SETTINGS_MODULE']='quadconnect.settings.development'
django.setup()
from django.test import Client
from connect.models import ExperienceFeedback
from django.db import transaction
try:
    with transaction.atomic():
        ExperienceFeedback.objects.all().delete()
        html = Client().get('/feedback/summary/').content.decode()
        print('empty state present:', 'No feedback submitted yet' in html)
        raise RuntimeError('rollback')
except RuntimeError:
    print('rolled back - database untouched')
print('rows still here:', ExperienceFeedback.objects.count())
"
```

That is the same rollback trick `verify_constraints` uses. For the screenshot
itself, either take it against a scratch copy of `db.sqlite3` or temporarily
delete the two seeded rows and re-run `seed_demo_data` afterwards.

---

## Step 4 — verify

```bash
python manage.py check
python manage.py runserver
```

| URL | Expect |
|---|---|
| `/feedback/summary/` | 200, average rating and distribution, nav and footer visible |

Confirm you used the manual path and not `render()`:

```bash
python -c "
import os,django,inspect
os.environ.setdefault('DJANGO_SETTINGS_MODULE','quadconnect.settings.development')
django.setup()
from connect import views
src = inspect.getsource(views.feedback_summary)
print('uses loader.get_template :', 'get_template' in src)
print('uses HttpResponse        :', 'HttpResponse' in src)
print('uses render(             :', 'render(request' in src, '(must be False)')
from django.test import Client
r = Client().get('/feedback/summary/')
print('status', r.status_code)
print('private_note leaked      :', b'private_note' in r.content, '(must be False)')
"
```

All three of the first checks must read as expected, and **`private_note
leaked` must be `False`**.

---

## Step 5 — screenshot

Save into `docs/screenshots/`:

| File | Shows |
|---|---|
| `01_fbv_httpresponse.png` | `/feedback/summary/` populated — **your graded evidence** |

Full browser window, address bar visible.

---

## Step 6 — notes

In `docs/notes/notes.txt`:

1. **VIEW REGISTER → KIND A1** — `Status: TODO` → `Status: DONE`; correct
   anything that drifted from what you built. If you skipped `mutual_pairs`,
   record it under **CHALLENGES & OPEN QUESTIONS**.
2. **REFLECTION → HttpResponse vs render()** — replace the `[Dhruv] TODO`
   line. Be concrete: what did you have to do by hand that `render()` does for
   you, and when would the manual path actually be the right choice? (Hint:
   when the response is not HTML, when you need to set headers or a status
   code, when you are streaming.)
3. **WEEKLY LOG** — add a line for what you finished.

---

## Commit sequence

```
Add feedback_summary FBV using loader.get_template and HttpResponse
Add feedback summary template with rating distribution
Add empty state for no submitted feedback
Record HttpResponse FBV in notes and add screenshot
```

---

## Done checklist

- [ ] `python manage.py check` → 0 issues
- [ ] `/feedback/summary/` returns 200 and extends `base.html`
- [ ] View is a **function**, uses `loader.get_template` + `HttpResponse`
- [ ] **Does not** call `render()`
- [ ] `request` passed as the second argument to `template.render()`
- [ ] `{% for %}` + `{% empty %}` both render
- [ ] **No `private_note` and no per-student ratings on the page**
- [ ] Aggregation uses a single query, not one per boolean field
- [ ] `01_fbv_httpresponse.png` saved
- [ ] `notes.txt` VIEW REGISTER marked DONE + reflection written
- [ ] `base.html` untouched · other owners' sections untouched
- [ ] Branch pushed, PR opened against `main`
