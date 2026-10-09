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

All three read the same production URL and need no account.

### Use 1: a command-line report for club organizers

- **Code:** [`public_api_uses/1_interest_report.py`](public_api_uses/1_interest_report.py)
- **Screenshot:** [`02_use1_python_report.png`](../screenshots/p1-a5/02_use1_python_report.png)
- **Run:** `python docs/a5/public_api_uses/1_interest_report.py`. It needs only
  `requests`, which is already in `requirements.txt`.

A club organizer or the student-life office runs this script to see what
QuadConnect students care about, without access to any private page. It
fetches `/api/summary/` with `requests` and prints three things:

- the share of picks that go to hobbies versus student organizations: 29 of 41,
  or 71%, are hobbies;
- the five most picked interests: Food and Movies, then Fitness, Gaming and
  Music;
- the 11 interests that only one student picked, which are candidates to
  promote or merge.

It finishes by checking the API's contract (three fields per row, no repeated
interest) and stops with an error if that ever changes.

### Use 2: statistics in a Jupyter notebook

- **Notebook:**
  [`public_api_uses/2_public_api_notebook.ipynb`](public_api_uses/2_public_api_notebook.ipynb),
  saved with its outputs
- **Screenshot:** [`03_use2_notebook.png`](../screenshots/p1-a5/03_use2_notebook.png)
- **Run:** on top of the site's requirements, `pip install pandas matplotlib
  notebook`. These are kept out of `requirements.txt` so production stays
  small.

A data-minded student or the course staff loads the API into a pandas
DataFrame with one `requests.get`, then studies it like any dataset. The
notebook finds:

- an interest is picked by 1.86 students on average, with a median of 1.5;
- hobbies average 2.42 picks each, against 1.20 for student organizations;
- the five most picked interests hold 41% of all picks;
- 11 of the 22 interests are picked more often than average.

A Matplotlib chart shows that most interests are picked by one or two
students.

### Use 3: a refreshable Excel workbook

- **Query:** [`public_api_uses/3_excel_power_query.pq`](public_api_uses/3_excel_power_query.pq)
- **Workbook:** [`public_api_uses/3_excel_power_query.xlsx`](public_api_uses/3_excel_power_query.xlsx)
- **Screenshot:** [`04_use3_excel.png`](../screenshots/p1-a5/04_use3_excel.png)

Staff who live in spreadsheets can use the API with no code to run. In Excel,
a Power Query reads `/api/summary/` straight into a table
(`Json.Document(Web.Contents(url))`, then `Table.FromRecords`). **Data >
Refresh All** reloads it, so nothing is copied by hand.

Ordinary formulas over that table give:

- picks by type: `COUNTIFS`, `SUMIFS` and `AVERAGEIFS`;
- the most picked interest: `INDEX`/`MATCH`, which finds Food;
- how many interests only one student picked: 11.

A bar chart shows picks by type.

To rebuild it, use **Data > Get Data > From Other Sources > Blank Query >
Advanced Editor**, then paste the `.pq` file. Or open the workbook, choose
**Enable Content**, and refresh.
