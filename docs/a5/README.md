# P1-A5: the public API, its chart, and three other uses

QuadConnect needs a login for every page and every API endpoint except one:
**`GET /api/summary/`**, on the live site at
<https://manojkmohan43.pythonanywhere.com/api/summary/>.

It returns how many verified students picked each interest, most picked first.
Each row has three fields:

```json
[
  {"category": "Food", "count": 4, "type": "Hobby / Interest"},
  {"category": "Movies", "count": 4, "type": "Hobby / Interest"},
  {"category": "UIUC Esports", "count": 3, "type": "Registered Student Organization"},
  ...
]
```

Why this endpoint is safe to open:

- it holds counts only, with no names, NetIDs, emails or match details;
- only verified students are counted;
- it is built from the database on every request (`connect/api.py`,
  `interest_popularity()`), so it always matches the site.

It needs no login, sends `Access-Control-Allow-Origin: *`, and answers GET
only. Every other `/api/` endpoint answers `401` with a link to the login page.
The API page on the site (`/api/`, after logging in) labels each endpoint
Public or Login required.

Every number below was read from the live API on 2026-10-08: 22 interests and
41 picks.

## Vega-Lite chart from the public API (Part 3.3)

- **Spec:** [`group-13-vega-lite-API-demo.txt`](group-13-vega-lite-API-demo.txt)
- **Screenshot:**
  [`01_vega_editor_public_api.png`](../screenshots/p1-a5/01_vega_editor_public_api.png)

The spec loads its rows with
`"data": {"url": "https://manojkmohan43.pythonanywhere.com/api/summary/"}` and
holds no inline values. It draws two bar panels, hobbies and registered
student organizations, each with its own filter on `type`. Paste the file into
<https://vega.github.io/editor/>, and it draws with no errors or warnings, in
any browser, logged in or not.

## Three other uses of the public API (Part 3.4)

All three read the same production URL and need no account. For each use, the
explanation is 1 to 5 sentences, as the assignment asks, followed by the API it
accesses, the data it uses and its result.

### Use 1: a command-line report for club organizers

A club organizer or the student-life office runs this script to see what
QuadConnect students care about, without access to any private page. It reads
the public API with `requests`, adds up the picks by type, ranks the interests
and lists the ones only one student chose. It ends by checking the API's
contract (three fields per row, no repeated interest) and stops with an error
if that ever changes.

- **API accessed:** `GET https://manojkmohan43.pythonanywhere.com/api/summary/`, with no login.
- **Data used:** all 22 rows, each with `category`, `count` and `type`.
- **Result:**
  - hobbies get 29 of the 41 picks (71%), and student organizations 12 (29%);
  - the five most picked interests are Food and Movies (4 students each), then
    Fitness, Gaming and Music (3 each);
  - 11 interests have only one student, which makes them candidates to promote
    or merge.
- **Code:** [`public_api_uses/1_interest_report.py`](public_api_uses/1_interest_report.py)
- **Screenshot:** [`02_use1_python_report.png`](../screenshots/p1-a5/02_use1_python_report.png)
- **Run:** `python docs/a5/public_api_uses/1_interest_report.py`. It needs only
  `requests`, which is already in `requirements.txt`.

### Use 2: statistics in a Jupyter notebook

A data-minded student or the course staff loads the API into a pandas
DataFrame with one request, then studies it like any dataset. The notebook
describes how many students pick each interest, compares hobbies with student
organizations, and measures how concentrated the picks are. A Matplotlib chart
shows how the picks spread out, by type.

- **API accessed:** `GET https://manojkmohan43.pythonanywhere.com/api/summary/`, with no login.
- **Data used:** the same 22 rows, as a DataFrame.
- **Result:**
  - an interest is picked by 1.86 students on average, with a median of 1.5;
  - hobbies average 2.42 picks each, against 1.20 for student organizations;
  - the five most picked interests hold 41% of all picks;
  - 11 of the 22 interests are picked more often than average;
  - most interests are picked by one or two students.
- **Notebook:**
  [`public_api_uses/2_public_api_notebook.ipynb`](public_api_uses/2_public_api_notebook.ipynb),
  saved with its outputs.
- **Screenshot:** [`03_use2_notebook.png`](../screenshots/p1-a5/03_use2_notebook.png)
- **Run:** on top of the site's requirements, `pip install pandas matplotlib
  notebook`. These are kept out of `requirements.txt` so production stays
  small.

### Use 3: a refreshable Excel workbook

Staff who work in spreadsheets can use the API with no code to run. A Power
Query (`Json.Document(Web.Contents(url))`, then `Table.FromRecords`) loads the
API into an Excel table. **Data > Refresh All** reloads it, so nothing is
copied by hand. Formulas over that table summarise it, and a bar chart shows
picks by type.

- **API accessed:** `GET https://manojkmohan43.pythonanywhere.com/api/summary/`,
  from Excel's Power Query, with no login.
- **Data used:** the same 22 rows, as a refreshable table.
- **Result:**
  - hobbies: 12 interests with 29 picks (71%, 2.42 each);
  - student organizations: 10 interests with 12 picks (29%, 1.20 each);
  - the most picked interest is Food;
  - 11 interests have one student.

  The formulas are `COUNTIFS`, `SUMIFS`, `AVERAGEIFS` and `INDEX`/`MATCH`.
- **Query:** [`public_api_uses/3_excel_power_query.pq`](public_api_uses/3_excel_power_query.pq)
- **Workbook:** [`public_api_uses/3_excel_power_query.xlsx`](public_api_uses/3_excel_power_query.xlsx)
- **Screenshot:** [`04_use3_excel.png`](../screenshots/p1-a5/04_use3_excel.png)
- **Run:** open the workbook, choose **Enable Content**, then **Data > Refresh
  All**. To build it from scratch instead, go to **Data > Get Data > From
  Other Sources > Blank Query > Advanced Editor**, and paste the `.pq` file.
