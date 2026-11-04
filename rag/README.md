# P1-A8: Semantic Relationships and Retrieval

**QuadConnect · The Connectors · Team 13 · INFO 490, Fall 2026**

A retrieval-augmented generation (RAG) system that answers students' questions about QuadConnect from its student
handbook: handbook → chunks → embeddings → vector store → top-k chunks → prompt → language model → answer. This
folder is independent of the Django app.

| Part | Status |
|---|---|
| 1. Build the RAG pipeline | Done |
| 2. System experiments | Done |
| 3. Failure analysis and improvement | Done |
| 4. System design reflection | Done |

## Files

| File | What it is |
|---|---|
| `rag_system.ipynb` | The full implementation and the experiments, with every output saved |
| `rag_analysis.md` | The analysis: the pipeline, the evaluation tables and comparisons, the failures and the fix, and the system design |
| `requirements.txt` | Every package the notebook needs, with pinned versions |
| `data/handbook.md` | The knowledge base: QuadConnect's student handbook (13 sections, 44 paragraphs, 4,875 words) |
| `data/staff_guide.md` | QuadConnect's staff and developer guide (11 sections, 44 paragraphs, 4,555 words): the extra documents of the larger dataset in Step 2.5 |
| `results/` | Everything the notebook saves, listed below |

**In `results/`:**

| File | Saved by | What it holds |
|---|---|---|
| `chunks.csv` | Step 1.2 | Every chunk of the three strategies |
| `embedding_stats.csv` | Step 1.3 | Each model and strategy: size, indexing time, storage |
| `retrieval_demo.csv`, `generation_demo.csv` | Steps 1.4, 1.5 | The demonstration tables |
| `generations.jsonl` | Steps 1.5 to 4.2 | Every answer from the language model, saved under a hash of its prompt |
| `test_queries.csv` | Step 2.1 | The eight test questions with their key facts and evidence |
| `evaluation.csv` | Step 2.2 | The 72 runs: retrieved chunks (full text), scores, answers, timings |
| `configurations.csv` | Step 2.2 | The nine configurations, summarised |
| `by_model.csv`, `embedding_models.png` | Step 2.3 | The embedding models compared |
| `by_strategy.csv`, `chunking_strategies.png` | Step 2.4 | The chunking strategies compared |
| `scaling.csv`, `scaling_summary.csv`, `dataset_size.png` | Step 2.5 | The data scaling experiment |
| `fact_outcomes.csv` | Step 3.1 | Every key fact of every Part 2 run: in the context or not, in the answer or not |
| `root_causes.csv` | Step 3.2 | The tests of each failure's causes: where the evidence ranks when one thing changes |
| `fix_options.csv` | Step 3.3 | The retrieval fixes considered |
| `fixes.csv`, `fixes_summary.csv` | Step 3.3 | The system before and after the two fixes |
| `costs.csv`, `cost_factors.png` | Step 4.1 | What each factor costs a day at 10,000 users |
| `alternatives.csv`, `approaches.csv` | Step 4.2 | RAG against pure prompting and the whole handbook in the prompt |
| `design_numbers.csv`, `system_design.png` | Step 4.3 | The load, capacity and daily cost, and the system's diagram |

## Setup

1. Use Python 3.11 (the version we ran it with).
2. From this folder, install the packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Optional: put `GROQ_API_KEY=...` in `../.env` (the repository's `.env`, never committed). The notebook needs it
   only to answer a question whose answer is not already saved in `results/generations.jsonl`. Every answer the
   notebook shows is saved, so a re-run works without it. `HF_TOKEN` there is optional too; it only speeds up model
   downloads.

## Run

Open `rag_system.ipynb` in Jupyter and choose *Run All*, or run it from this folder:

```bash
jupyter nbconvert --to notebook --execute --inplace rag_system.ipynb
```

* Run it from this folder: every path in the notebook is relative to it (`data/`, `results/`, `../.env`).
* The first run downloads the three embedding models from Hugging Face, about 1.9 GB, into the usual Hugging Face
  cache. After that, a full run takes three to four minutes on a laptop CPU; no GPU is needed.
* The answers come from the saved file, so they are the same on every run, and so are the retrieval results and
  every score. The timings (indexing, embedding a question, searching) are measured on each run, so they vary a little
  from one run to the next.
