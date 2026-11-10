# P1-A9 Part 1: measurements of the integrated feature

The evidence behind Part 1 of [`README_AI.md`](../../README_AI.md): how well P1-A8's embedding model
(`BAAI/bge-small-en-v1.5`) places an interest the language model wrote in its own words, and what that changes
for Part 3's 20 evaluation requests. Everything here was produced by [`measure.py`](measure.py), with the real
models, on an Apple M5 (24 GB, CPU inference; no CUDA), Python 3.14.

```bash
python manage.py download_ai_model     # once: both models into the Hugging Face cache
python docs/a9_part1/measure.py        # about 2 minutes once the models are cached
```

The script works on a copy of `db.sqlite3` in a temporary folder, so the committed database gets no login
session. It clears the cache before every request, so every answer comes from the model.

| File | What it holds |
|---|---|
| `calibration.csv` | One row per word: the interest it should be placed on (empty if none), the closest interest and its cosine similarity, the next-closest and its similarity, the lead between them, what `match_by_meaning()` placed, and the outcome. Set `calibration` (34 words that should be placed, 36 that should not) is what `MEANING_MIN = 0.78` and `MEANING_LEAD = 0.08` were fitted to. Set `held-out` (20 and 25 more) played no part in choosing them. |
| `requests.json`, `requests.csv` | Part 3's 20 requests (from [`../a9_evaluation/after_results.json`](../a9_evaluation/after_results.json)), each sent through the `/search/ask/` view twice: with matching by meaning `off` and `on`. Per row: the model's raw replies, the filters, the words placed by meaning, the chips under *Understood as*, who read the request, the students found, the app's time and the wall time, and Part 3's verdict. |
| `summary.json` | The counts and median times of both runs, the calibration counts, the load time and the cost of matching one word. |

## Results

| | Should be placed: placed right | Should not be placed: placed anyway |
|---|---:|---:|
| Calibration set | 21 of 34 | 0 of 36 |
| Held-out set | 11 of 20 | 1 of 25 (*lunch* → Food, 0.821, a lead of 0.113) |

`calibration.csv` measures `match_by_meaning()` alone. In the app it only sees the words that the spelling
match (`match_name()`) has already failed to place. Of these 54 words, only *Movie* is placed by spelling
first (on Movies), so it would never reach the embedding model.

| Part 3's 20 requests | Matching by meaning off | On |
|---|---:|---:|
| Exactly right | 15 | **17** |
| Missing an interest | 5 (T08, T10, T12, N1, N3) | 3 (T12, N1, N3) |
| A filter nobody asked for, or a wrong one | 0 | 0 |
| Read by the model | 20 | 20 |
| Median time on the page | 2.35 s | 2.35 s |

* Placing one word takes a median of 4.1 ms once the model is loaded (50 runs).
* The first request after start-up took 9.5 s, while both models loaded from the cache.
* With matching off, the 20 requests got exactly the verdicts that Part 3's *after* run got on a different
  machine: greedy decoding is repeatable.
* For T12, N1 and N3, the raw replies show the model wrote no interest at all, so there was nothing to place.
