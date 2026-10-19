# P1-A6 - AI features in QuadConnect

QuadConnect gained two AI features. Both are ordinary Django pages in the existing app (login required, same navigation and styling), not a separate project.

| Feature | Page | Engine | What it does |
|---|---|---|---|
| **Profile assistant** | `/ai/profile-assistant/` (nav link **AI**) | **Local** Hugging Face model through `transformers` | Reads 2-3 free-text sentences and suggests the same preferences onboarding stores: interests from our catalogue, conversation style, group preference, social energy |
| **Match welcome message** | `/matches/<id>/ai-welcome/` (button on every match page) | **Hybrid:** local model + **external API** (Groq, Gemini or OpenRouter) | Writes a short welcome message and three conversation starters for a match |

How it fits the assignment:

| Part | Where |
|---|---|
| Part 1 - model lab (15 models, Route A prompting) | [`llm-test/ai_prototype.ipynb`](llm-test/ai_prototype.ipynb) |
| Part 2 - this file, the Django integration | `connect/ai_local.py`, `connect/ai_api.py`, `connect/ai_views.py`, templates `connect/templates/connect/ai_*.html`, tests `connect/tests_a6.py` |
| Part 3 - production reflection | [`notes.txt`](notes.txt) |

---

## System description

```
student text ──► form validation ──► clean_text ──► LOCAL model (Qwen2.5-1.5B) ──► JSON parse ──► allow-list clean ──► page
 (POST, CSRF,     (10-600 chars)     (strip, fence)   8-example prompt             (1 retry)        (+ keyword fallback)

match page ──► optional note ──► LOCAL model ──► allow-listed prefs ┐
                                                                    ├─► EXTERNAL API ──► schema check ──► page
our DB: format, time, venue, activity, shared interest names ───────┘    (Groq/Gemini/    (template on any
(no names, NetIDs or check-in codes)                                      OpenRouter)      failure)
```

### Data input: how user data is captured

* **Profile assistant:** one `<textarea>` in `ProfileIntroForm` (`connect/forms.py`), submitted with **POST** and a CSRF token. 10-600 characters, with plain-language errors ("Write a little more: at least 10 characters.").
* **Welcome message:** an optional 0-300 character note (`MatchNoteForm`), also POST + CSRF. The meeting facts are **not typed by the user**: they come from the database (`Match`, `CampusLocation`, the suggested activity, and the interests members picked).
* Both pages sit behind the site's login (`LoginRequiredMiddleware`); a GET only shows the form and **never starts a model run or an API call**, so a link, a prefetch or a crawler cannot spend CPU or money.
* **Nothing is stored.** No new tables, no migration; the text and the model's answer exist only for the length of the request, and the committed `db.sqlite3` is untouched.

### Preprocessing: how data is cleaned and formatted before the LLM

`clean_text()` in `connect/ai_local.py`:

1. Unicode NFKC normalisation (folds look-alike characters).
2. Remove control characters and zero-width / bidirectional-override characters.
3. Remove anything that looks like an HTML tag.
4. Replace `"""` and code fences, so the text cannot close the quotation fence the prompt puts around it.
5. Collapse all whitespace to single spaces; cap at 600 characters.

Then the prompt is built (`build_messages`):

* a **system prompt** that states the schema, the allowed values and the default for "not stated", and says the introduction is untrusted data;
* the **interest vocabulary comes from the database** (`Interest` rows, in catalogue order), so adding an interest in the admin changes the prompt without a code change;
* **eight solved examples** (many-shot prompting), the last one showing how to answer an injection attempt. The notebook's Route A comparison chose this: for the 1.5B model zero-shot scored 0.31 (62% JSON, 0% schema-valid) and many-shot 0.84 (100% JSON, 75% schema-valid);
* the student's text, fenced in `"""` as the last user turn. Decoding is greedy (no sampling), at most 90 new tokens, stopping at the first `}`.

For the external API, the payload is **our own facts** plus the *allow-listed* preferences from step 2, as JSON. The raw note is not part of it.

### Safety guardrails: malicious inputs and broken outputs

| Risk | Defence |
|---|---|
| Prompt injection ("ignore all previous instructions...") | Text is fenced and the system prompt calls it untrusted data; an injection pattern list **flags** it (shown to the student, logged); the output is forced through allow-lists, so an obeyed injection still cannot put free text on the page; for the API path the raw note never leaves the server. Notebook result on the injection input: safe for Qwen2.5 (0.5B-14B) and Qwen3-4B, **not** safe for Phi-3.5-mini, Mistral-7B (3-shot), TinyLlama and SmolLM2-135M/360M, which is why we never trust raw model text. |
| Hidden / oversized / markup input | `clean_text()` above plus form `max_length`; output is escaped by Django templates (tested with a `<script>` payload from both the model and the API). |
| Model returns prose, a poem, truncated or fenced JSON | `extract_json()` finds the first complete object in the reply. No object: **one repair retry** ("Reply with ONLY the JSON..."). Still none: **`keyword_fallback()`** (deterministic, model-free). |
| Valid JSON, wrong content (invented interests, `"energy": 9`, wrong types) | `clean_extraction()`: interests must match the catalogue (case-insensitive, de-duplicated, max 5), enums fall back to defaults, energy is clamped to 1-5. |
| Model cannot load (no internet, out of memory, torch missing, `LOCAL_LLM_ENABLED=0`) | `LocalLLMUnavailable` -> keyword matcher, and the page tells the student that simple keyword matching was used. A crash inside generation is also caught: no 500 page. |
| External API fails (no key, timeout 15 s, HTTP 4xx/5xx, 429, non-JSON, wrong shape) | `APIUnavailable` -> deterministic template message built from the same facts, and the page says the AI service was not available. |
| API reply is hostile or huge | Parsed against a schema (`message` string, `starters` list), control characters stripped, message capped at 700 characters, each starter at 160, at most 3 starters; escaped when rendered. |
| Leaking personal data to a third party | Only the interest *names*, format, time, venue and activity are sent. Names, NetIDs, emails and check-in codes are never included (a test asserts this against the seeded match). The API key is read from `.env` only and never logged or rendered. |
| Abuse / cost | Per-user rate limit of 6 calls per minute per feature (HTTP 429 with a message); API timeout and `max_tokens` cap; model generation is serialised with a lock and has `max_time` (default 90 s). |
| CSRF / auth | POST-only generation with CSRF (tested: 403 without a token); login required (a test walks every route logged-out). |

---

## Local LLM integration

* **Library:** `transformers` + `torch` (both pinned in `requirements.txt`).
* **Model:** `Qwen/Qwen2.5-1.5B-Instruct` by default (set `LOCAL_LLM_MODEL` in `.env`). It was chosen from the 15-model notebook test: with the many-shot prompt it scores 0.84 raw / 0.86 after guardrails, is about 3 GB, and answers in ~5-10 s on a plain CPU. The upgrade for a machine with ~12 GB of free RAM or a GPU is `Qwen/Qwen3-4B-Instruct-2507` (0.92, 100% schema-valid); we checked that it loads and answers through the same code path. Reasoning and numbers: notebook step 7 and `notes.txt`.
* **Automatic download:** nothing is committed. The **first request** to `/ai/profile-assistant/` makes `transformers` download the weights into the Hugging Face cache (`~/.cache/huggingface`, outside the repository, ~3 GB) and load them; later requests reuse the loaded model. To do that up front instead:

  ```bash
  python manage.py warm_ai_model
  ```

* **Hardware:** CUDA is used if available; otherwise CPU in bfloat16 (`LOCAL_LLM_DTYPE=float32` is faster on CPUs without bf16 support but doubles the memory).
* **Switch off:** `LOCAL_LLM_ENABLED=0` skips the model and uses only the keyword matcher (useful on a tiny host).
* **Measured here** (4 CPU cores, no GPU, bf16): ~16 s for the first call including load, 6-11 s afterwards for the full page.

## External API integration

* **Providers:** Groq (default, free tier), Google Gemini, OpenRouter. All three speak the OpenAI-compatible `chat/completions` format, so one small `requests` client covers them; `AI_API_PROVIDER` picks one and `AI_API_MODEL` optionally overrides its default model (`llama-3.1-8b-instant`, `gemini-2.0-flash`, `meta-llama/llama-3.1-8b-instruct:free`).
* **Setup:** copy `.env.example` to `.env` and fill in **one** key (`GROQ_API_KEY`, `GEMINI_API_KEY` or `OPENROUTER_API_KEY`, or the generic `AI_API_KEY`). `.env` is git-ignored.
* **Without a key** the page still works: it shows the template message and says so. This is also what the tests exercise; no key or network is needed to run them.
* **Hybrid pipeline** (`connect/ai_api.py`, `connect/ai_views.py::match_welcome`): our data -> local model reads the optional note -> only allow-listed preferences + facts go to the API -> reply validated -> template fallback. The "How this was made" section on the page shows exactly which facts were used and what was sent on.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                         # includes torch + transformers
cp .env.example .env                                    # set DJANGO_SECRET_KEY; add an API key if you have one
python manage.py migrate && python manage.py seed_demo_data
python manage.py runserver
```

Log in as `tester` / `uiuc12345`, then open **AI** in the navigation, or a match and press **AI welcome message**.

```bash
python manage.py test connect            # 161 tests, 49 of them in connect/tests_a6.py (no model, no network)
ruff check .                             # the project's lint rules (also lints the notebook)
```

## Honest limits

* The external API path is tested with mocked HTTP responses (success, JSON-mode rejection, timeout, 429, 5xx, bad JSON). It has **not** been called against a live provider in development because no key was available; the request follows the documented OpenAI-compatible format.
* The 1.5B model misses things a larger one catches (for example it often drops "Technology" and "Illini Robotics" for "quiet engineering junior" text and answers `CASUAL` where `DEEP` is right). That is why the page labels results as suggestions and why the keyword matcher and allow-lists exist.
* The model benchmark used 8 inputs; see the notebook's limitations paragraph before reading small score differences as real.
* `requirements.txt` now contains `torch`, which is far larger than the host limit the P1-A4 CI job enforces (512 MB install size); that job only runs on `feature/p1-a5`, so it does not run for this work, but it would need a bigger limit or a split requirements file before being pointed at this branch.
