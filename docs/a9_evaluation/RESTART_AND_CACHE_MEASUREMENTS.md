# Separate restart and cache measurements

These measurements are separate from the 20 unique-request latency distributions in `before_results` and `after_results`.

- After-change process restart: Django was stopped with Ctrl+C and restarted. The first request, `Who likes basketball?`, displayed an app-reported time of **22.02 seconds**.
- Cached repeat: browser wall time was **38 ms before** and **37 ms after**. The repeated T01 request is excluded from the 20-request median and p95 calculations.
- The 19.3-second T01 result in the after-run batch was not taken immediately after an explicit process restart. It is likely a cold model reload following Django's development-server autoreloader noticing the saved `ai_search.py` change, but that explanation was not independently instrumented.
