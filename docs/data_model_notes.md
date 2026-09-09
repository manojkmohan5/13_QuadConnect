# QuadConnect — Part 4 Design Notes

**Team:** The Connectors · **Team Number:** 13
**Members:** Kritika Agrawal, Manojkumar Mohankumar, Prathamesh Mulay, Dhruv Mayur Thaker
**Django:** 5.2.17 · **Python:** 3.11 · **Database:** SQLite (`db.sqlite3`, project root)

---

## 1. Why these project and app names

| Name | Value | Reasoning |
|---|---|---|
| `<startproject_folder_name>` | `quadconnect` | The deployable product as a whole. It carries settings, the root URLconf, and WSGI/ASGI entry points — anything true of the whole site rather than of one feature. |
| `<app_name>` | `connect` | The one core domain of the product: the lifecycle that turns two verified students into a completed in-person experience. Every model here answers "who is being connected, on what basis, where, and what came of it." |

`connect` was chosen over broader candidates such as `core` or `main`, which
say nothing about the domain, and over narrower ones such as `matching`,
which would have described only the middle of the lifecycle and left
onboarding and feedback without a home.

Later assignments add sibling apps as the product grows past this one domain
(for example `events` for campus events, `assistant` for the AI campus
assistant). Each team member owns one feature area inside `connect` for now —
see the Team Contribution Contract.

---

## 2. Model overview

Eight models, each mapping to a screen in the wireframe deck.

| Model | Real-world entity | Screen |
|---|---|---|
| `StudentProfile` | An SSO-verified UIUC student and their matching signals | 1–4 |
| `Interest` | One selectable interest, RSO, or meeting activity | 2, 5 |
| `ProfileInterest` | One student's selection of one interest (M2M through) | 2 |
| `AvailabilitySlot` | One weekend window a student marked free | 5 |
| `CampusLocation` | An approved public meeting place on campus | 8 |
| `Match` | One scheduled weekly experience | 6, 7 |
| `MatchParticipant` | One student's place in one match | 6, 7, 8 |
| `ExperienceFeedback` | One student's private post-meeting feedback | 9 |

This exceeds the recommended 3–5 because the binding requirement is a
*minimum* of two models per feature, and the product has four distinct
feature areas (onboarding, matching, scheduling/check-in, feedback). Every
model earns its place by holding state no other model can: collapsing any two
of them would force nullable columns that are meaningless for half the rows.

### Relationships

```
auth.User 1───1 StudentProfile 1───N AvailabilitySlot
                     │ 1                         
                     │                            
                     N ProfileInterest N───1 Interest
                     │                          │
                     │ (PROTECT)                │ (SET_NULL, activities only)
                     N                          │
              MatchParticipant N───1 Match ─────┘
                     │ 1               │ N
                     │                 │
                     1                 1
          ExperienceFeedback     CampusLocation
```

`StudentProfile ↔ Interest` is many-to-many, realised explicitly through
`ProfileInterest` so a selection can carry its own data (`is_primary`,
`selected_at`) rather than being a bare link.

---

## 3. `on_delete` choices and why

| Relation | Behaviour | Justification |
|---|---|---|
| `StudentProfile.user` | `CASCADE` | A profile describes exactly one account. Orphaning it would strand personal data that can no longer be reached or deleted through the account it belongs to. |
| `AvailabilitySlot.profile` | `CASCADE` | Availability is worthless without the student it describes. |
| `ProfileInterest.profile` | `CASCADE` | A selection has no meaning without the student who made it. |
| `ProfileInterest.interest` | **`PROTECT`** | Deleting a catalogue entry students already picked would silently rewrite their profiles and invalidate past match explanations. Retire it with `is_active=False` instead. |
| `Match.location` | **`PROTECT`** | A past meeting must always be able to say where it happened. Venues are retired with `is_approved=False`. |
| `Match.suggested_activity` | **`SET_NULL`** | The suggestion is a prompt, not part of the meeting's identity. Losing it leaves a still-valid meeting. |
| `MatchParticipant.match` | `CASCADE` | A participant row describes a place inside one meeting; without the meeting it describes nothing. |
| `MatchParticipant.profile` | **`PROTECT`** | Deleting a student mid-cycle would silently shrink a squad other students still plan to attend. Withdrawal must be explicit (`response=DECLINED`). |
| `ExperienceFeedback.participant` | `CASCADE` | Feedback is about one specific attendance and cannot be attributed without it. |

The mix is deliberate: `CASCADE` where the child is a detail of its parent,
`PROTECT` where deletion would destroy history or affect a third party, and
`SET_NULL` where the link is genuinely optional.

---

## 4. Uniqueness constraints

Five multi-field `UniqueConstraint`s, all verified against the live database:

| Constraint | Fields | Prevents |
|---|---|---|
| `uniq_profile_netid_email` | `net_id`, `illinois_email` | A NetID paired with someone else's mailbox during a bad SSO import |
| `uniq_interest_name_per_category` | `name`, `category` | Duplicate catalogue entries (while still allowing "Sports" as both a hobby and an activity) |
| `uniq_interest_per_profile` | `profile`, `interest` | The same interest selected twice, which would double-count overlap |
| `uniq_slot_per_profile_day_block` | `profile`, `weekday`, `time_block` | The same weekend window selected twice |
| `uniq_participant_per_match` | `match`, `profile` | The same student appearing twice in one match |

---

## 5. Default ordering

Every model sets `Meta.ordering` so lists are stable without callers asking:

| Model | Ordering | Why |
|---|---|---|
| `StudentProfile` | `full_name`, `net_id` | Admin browsing is by person |
| `Interest` | `category`, `name` | Chip pickers group by category |
| `ProfileInterest` | `profile`, `-is_primary`, `interest` | Starred picks first |
| `AvailabilitySlot` | `profile`, `weekday`, `time_block` | Chronological within a student |
| `CampusLocation` | `name` | Alphabetical venue list |
| `Match` | `-week_start`, `-scheduled_for` | Newest cycle first — the common case |
| `MatchParticipant` | `match`, `-compatibility_score`, `profile` | Best fit first within a match |
| `ExperienceFeedback` | `-submitted_at` | Most recent feedback first |

---

## 6. Reproducing this database

```bash
python manage.py migrate
python manage.py seed_demo_data       # 8 students, 3 matches, 2 feedback rows
python manage.py verify_constraints   # proves constraints + on_delete (11/11)
python manage.py runserver
```

Superusers (both created because the assignment text specifies `mohitg2` in
section 4 and `tester` in the checklist):

| Username | Password |
|---|---|
| `mohitg2` | `uiuc12345` |
| `tester` | `uiuc12345` |

`db.sqlite3` is committed at the project root already seeded, so no commands
are required to review the data — log in at `/admin/` directly.

---

## 7. Test data

Seeded by `connect/management/commands/seed_demo_data.py` (idempotent):

- **8 student profiles** across five colleges, varied social preferences
- **28 interests** (12 hobbies, 10 RSOs, 6 activities)
- **41 interest selections** exercising the M2M through-model
- **16 availability slots**
- **4 approved campus locations** (Illini Union, Grainger Library, Main Quad, Espresso Royale)
- **3 matches** — one Friend Connect awaiting response, one confirmed Squad Connect with check-ins, one completed experience
- **9 match participants**, **2 feedback submissions**

## 8. Constraint and `on_delete` verification

`python manage.py verify_constraints` runs 11 checks, each inside a
transaction that is rolled back, so the submitted database is never mutated.
All 11 pass:

```
=== UniqueConstraint enforcement ===
  PASS  uniq_interest_per_profile - apatel22 picks 'Food' twice
  PASS  uniq_slot_per_profile_day_block - apatel22 re-adds Saturday 2 - 4 PM
  PASS  uniq_participant_per_match - jordan4 added to match QC-4827 twice
  PASS  uniq_interest_name_per_category - second 'Art' hobby entry
  PASS  uniq_profile_netid_email - reuse of apatel22/apatel22@illinois.edu

=== on_delete behaviour ===
  PASS  PROTECT - delete Interest 'Art' selected by 2 student(s)
  PASS  PROTECT - delete CampusLocation 'Espresso Royale on Goodwin' hosting 1 match(es)
  PASS  PROTECT - delete StudentProfile 'apatel22' in 1 match(es)
  PASS  CASCADE - delete Match removes participants and feedback
  PASS  CASCADE - delete User removes its StudentProfile
  PASS  SET_NULL - delete suggested activity, Match survives

11/11 checks passed, 0 failed.
```

---

## 9. Scope of this milestone

P1-A1 is a data-modelling milestone, so `connect/views.py` holds a single
read-only dashboard at `/` that proves the models are queryable outside
Django Admin. The nine-screen flow from the wireframes is implemented in a
later assignment, one feature per team member.

## 10. References

- Django 5.2 model field reference — <https://docs.djangoproject.com/en/5.2/ref/models/fields/>
- Django 5.2 constraints reference — <https://docs.djangoproject.com/en/5.2/ref/models/constraints/>
- QuadConnect interactive prototype — <https://trek-galaxy-20520998.figma.site/>
