# P1-A8: Semantic Relationships and Retrieval

**QuadConnect · The Connectors · Team 13 · INFO 490, Fall 2026**

A retrieval-augmented generation (RAG) system that answers students' questions about QuadConnect from its student
handbook: handbook → chunks → embeddings → vector store → top-k chunks → prompt → language model → answer. This
folder is independent of the Django app.

| Part | Status |
|---|---|
| 1. Build the RAG pipeline | Done |
| 2. System experiments | Next |
| 3. Failure analysis and improvement | Next |
| 4. System design reflection | Next |

## Files

| File | What it is |
|---|---|
| `rag_system.ipynb` | The full implementation and the experiments, with every output saved |
| `rag_analysis.md` | The analysis: the pipeline, and the evaluation, comparisons, failures and design as the parts are added |
| `requirements.txt` | Every package the notebook needs, with pinned versions |
| `data/handbook.md` | The knowledge base: QuadConnect's student handbook (13 sections, 44 paragraphs, 4,875 words) |
| `results/` | What the notebook saves: the chunks, the embedding statistics, the demo tables and every generated answer |

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
  cache. After that, a full run takes about two minutes on a laptop CPU; no GPU is needed.
* The answers come from the saved file, so they are the same on every run. The timings (indexing, embedding a
  question, searching) are measured on each run, so they vary a little from one run to the next.
