# Build Tasks — P1-A2

One file per developer. Read **only your own** file, plus the ground rules
below. Each task is self-contained and can be completed without waiting for
anyone else.

| Owner | Task file | Branch | View kind |
|---|---|---|---|
| Kritika Agrawal | [kritika_profile_views.md](kritika_profile_views.md) | `feature/profile-views` | Generic CBV |
| Manojkumar Mohankumar | [manojkumar_match_views.md](manojkumar_match_views.md) | `feature/match-views` | FBV — `render()` |
| Prathamesh Mulay | [prathamesh_location_views.md](prathamesh_location_views.md) | `feature/location-views` | Base CBV |
| Dhruv Thaker | [dhruv_feedback_views.md](dhruv_feedback_views.md) | `feature/feedback-views` | FBV — `HttpResponse` |

---

## Ground rules — all four of you

**Everything already runs.** `main` has the settings split, `.env` handling,
`base.html`, a shared list template, and **all four routes already named and
wired to stub views**. Your job is to replace one stub with a real
implementation. Nothing you do should break another person's page.

### Files you may touch

- Your own **section** of `connect/views.py` (the file is divided by commented
  section headers — yours has your name on it)
- Your own **line(s)** in `connect/urls.py` — swap the stub for your real view.
  **Do not change the path or the `name=`.** `base.html` reverses both.
- Your own **templates** under `connect/templates/connect/`
- Your entry in `docs/notes/notes.txt`
- Your screenshot in `docs/screenshots/`

### Files you must NOT touch

| File | Why |
|---|---|
| `connect/templates/connect/base.html` | Owned by `main`. Every route is already reversed there. Editing it from four branches is the one guaranteed merge conflict. |
| Another owner's section of `views.py` | Even to fix something. Raise it in the group chat. |
| `connect/models.py` and `migrations/` | The data model is frozen for P1-A2. |
| `quadconnect/settings/*` | Ask first. |
| `connect/templates/connect/entity_list.html` | **Shared** by Manojkumar and Prathamesh. Its context contract is documented at the top of the file. If you genuinely need to change it, agree with the other owner first. |

### First-time setup

```bash
git clone <repo-url>
cd 13_QuadConnect

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
python manage.py runserver
```

`db.sqlite3` is gitignored on purpose. Never `git add -f` it.

### Definition of done — every task

1. `python manage.py check` reports 0 issues.
2. Your URL returns **HTTP 200** in a browser.
3. Your page **extends `base.html`** — the nav bar and footer are visible.
4. Your list renders a `{% for %}` loop **and** a `{% empty %}` branch with a
   genuinely helpful empty-state message.
5. You can trigger the empty state without deleting data (each task explains
   how).
6. `docs/notes/notes.txt` — your entry in the **VIEW REGISTER** has
   `Status: DONE`, and you have filled in your line in **REFLECTION**.
7. Your screenshot is saved in `docs/screenshots/` with the exact filename
   your task specifies.
8. Commits are small and imperative: `Add StudentProfileListView generic CBV`,
   not `update stuff`.

### Git workflow

```bash
git switch main
git pull
git switch feature/<your-branch>     # your branch already exists
git merge main                       # resolve here, never on main

# … work, committing in small steps …

git push -u origin feature/<your-branch>
```

Then open a pull request against `main`. Manojkumar merges them one at a time.

### Reference

`CLAUDE.md` at the repo root is the full project reference: product decisions,
every model field, every `on_delete` and why. Read section 5 before querying
anything.
