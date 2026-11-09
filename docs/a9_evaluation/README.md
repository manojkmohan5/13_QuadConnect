# P1-A9 evaluation evidence

The raw results behind Part 3 of [`README_AI.md`](../../README_AI.md). The same 20 requests (T01–T15 and
N1–N5) were submitted through the live `/search/ask/` page, before and after the check described in 3.4.
Prathamesh Mulay collected them, with a browser runner, on the machine described in 3.2.

| File | What it holds |
|---|---|
| `before_results.json`, `before_results.csv` | One row per request before the change: the request, its expected filters, the chips the page showed, who read the request, the students found, the time the page reported, the browser wall time and the HTTP status. The 21st row, `T01_REPEAT`, is the cached repeat of T01. |
| `after_results.json`, `after_results.csv` | The same, after the change. |
| `before_summary.json`, `after_summary.json` | The counts and the app-reported times of each run, and the cached repeat. |
| `RESTART_AND_CACHE_MEASUREMENTS.md` | The first request after a restart, and the cached repeat. These are kept apart from the 20-request statistics. |

Each JSON file and the CSV file beside it hold the same rows.
