# P1-A10: AI analytics dashboard

`/analytics/` (staff only; log in as `mohitg2` / `uiuc12345`) monitors **Ask in plain English**
(`/search/ask/`) in three sections: system performance, user behavior and cost. Each card is titled with
the question it answers. The submission write-up is [`P1-A10_report.pdf`](P1-A10_report.pdf) (source:
[`report.html`](report.html)); screenshots are in [`screenshots/`](screenshots/).

| Piece | Where |
|---|---|
| Log model, one row per search | `AIRequestLog` in [`connect/models.py`](../../connect/models.py), migration `0003_ai_request_log` |
| Logging (latency, tokens, source, filters, results) | `log_request()` and the `usage` counter in [`connect/ai_search.py`](../../connect/ai_search.py) |
| Statistics and the 8 Vega-Lite specs | [`connect/analytics.py`](../../connect/analytics.py) |
| Page | [`connect/templates/connect/analytics.html`](../../connect/templates/connect/analytics.html), drawn by `static/js/charts.js` |
| Simulated logs (6 weeks, 563 searches) | [`seed_ai_logs`](../../connect/management/commands/seed_ai_logs.py), run by `seed_demo_data` |
| Tests | [`connect/tests_a10.py`](../../connect/tests_a10.py) |

**Data.** The live site cannot run the model (512 MB host), so its real logs are keyword-fallback searches
with no tokens. The dashboard therefore ships simulated logs built from P1-A9's real measurements (the 20
evaluation requests' latencies, results, and token counts from Qwen2.5-1.5B's tokenizer). Real searches are
logged alongside them from the moment the migration runs. `seed_ai_logs` does nothing if any log exists.

**Cost.** Tokens times the price of a hosted model of the same size (`PRICE_PER_M_*` in `analytics.py`).
Cost is not stored, so changing the price re-prices every row.

## Deploy (PythonAnywhere)

```bash
cd ~/13_QuadConnect && git pull
python manage.py migrate
python manage.py seed_ai_logs
python manage.py collectstatic --noinput
```

Then **Reload** the web app on the Web tab and open `/analytics/` as `mohitg2`.
