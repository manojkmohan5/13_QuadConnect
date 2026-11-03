# QuadConnect RAG system: analysis (P1-A8)

**The Connectors · Team 13 · INFO 490, Fall 2026**

This document explains the retrieval-augmented generation (RAG) system we built for QuadConnect, and what our
experiments show about it. The implementation and every number below are in
[`rag_system.ipynb`](rag_system.ipynb); the saved results are in [`results/`](results/).

| Part | Section | Status |
|---|---|---|
| 1. Build the RAG pipeline | [1. The pipeline](#1-the-pipeline) | Done |
| 2. System experiments | 2. Experiments | Next |
| 3. Failure analysis and improvement | 3. Failures and a fix | Next |
| 4. System design reflection | 4. System design | Next |

---

## 1. The pipeline

The system answers students' questions about QuadConnect from its handbook:

**handbook → chunks → embeddings → vector store → top 3 chunks → prompt → gpt-oss-20b → answer**

### 1.1 The knowledge base

**The dataset is QuadConnect's student handbook** ([`data/handbook.md`](data/handbook.md)), the help guide a student
would read to understand the app. The questions students ask about QuadConnect are about how it works, such as how
matching decides, which times and places are possible, and what happens to their feedback and data, so this is the
knowledge base the system needs.

QuadConnect had no such document: its database holds short fields, and its repository documents are written for
developers. We wrote the handbook for this assignment from the app's own code and pages, so every fact in it is one
the app enforces or shows:

* the formats and preferences come from the data model: Friend Connect (1-on-1) and Squad Connect (4 to 8 students),
  the five-step social energy scale, weekends only in four two-hour windows, the 0–100 fit score and the check-in
  code;
* the venues with their seats and arrival notes, the interests and the colleges come from the seeded database;
* sign-in, cookies and data sharing come from the Privacy page and the settings, the venue check from its module, and
  search from the search pages.

A **paragraph** is a block of text between blank lines under a section heading. Each paragraph covers one idea, and
each section covers one subject.

| Section | Paragraphs | Words |
|---|---|---|
| 1. About QuadConnect | 3 | 353 |
| 2. Creating an account and signing in | 3 | 346 |
| 3. Building your profile | 5 | 594 |
| 4. Setting your availability | 2 | 222 |
| 5. How weekly matching works | 4 | 473 |
| 6. Meeting up: venues, check-in and icebreakers | 4 | 504 |
| 7. Suggesting a new venue | 4 | 466 |
| 8. Finding students | 4 | 419 |
| 9. After the meetup: feedback | 3 | 290 |
| 10. Staying safe and respectful | 2 | 202 |
| 11. Privacy and your data | 3 | 292 |
| 12. Insights, reports and the API | 2 | 205 |
| 13. Frequently asked questions | 5 | 509 |
| **All 13 sections** | **44** | **4,875** |

| Requirement | The brief asks for | The handbook has | Met |
|---|---|---|---|
| Number of paragraphs | at least 20; 30–50 recommended | 44 | yes |
| Paragraph length | about 80–200 words each | 90 to 165 words (mean 111) | yes |
| Total size | 2,000–5,000 words | 4,875 words | yes |

### 1.2 Chunking

Sentences end at `.`, `!` or `?` followed by a capital letter, a digit or a quote. The handbook avoids abbreviations
with full stops, so a sentence never ends early. A section is about one subject, so a section boundary is a topic
boundary. **No strategy splits a sentence, and none puts two sections in one chunk.**

| Strategy | How a chunk is made |
|---|---|
| 1. Fixed length | Whole sentences packed, in order, into chunks of at most 120 words, about one paragraph. Paragraph boundaries are ignored, but each section starts a new chunk; a sentence that would pass the limit starts the next chunk. |
| 2. Overlapping paragraphs | Two adjacent paragraphs of the same section: paragraphs 1 + 2, then 2 + 3, and so on. |
| 3. Hybrid (structure-aware) | One paragraph per chunk, with its section title in front so the chunk names its topic. A paragraph over 150 words is split at the sentence boundary nearest its middle, and both halves keep the title. An FAQ question stays with its answer. |

**How the overlap is implemented:** a window two paragraphs wide slides through each section one paragraph at a time.
Neighbouring chunks share a whole paragraph, half of each chunk, and every paragraph except a section's first and last
is in two chunks. The window restarts at every section, so a pair never mixes two topics.

| Strategy | Chunks | Words per chunk | Mean words | Paragraphs per chunk | Chunks per paragraph |
|---|---|---|---|---|---|
| Fixed | 50 | 21–120 | 98 | 1.46 | 1.66 |
| Overlapping | 31 | 186–285 | 222 | 2.00 | 1.41 |
| Hybrid | 48 | 67–122 | 102 | 1.00 | 1.09 |

The hybrid strategy halved the 4 paragraphs over 150 words (S03-P5, S05-P3, S06-P2, S07-P4). A fixed-length chunk can
be as short as 21 words: the leftover at the end of a section,
which is still whole sentences. The notebook checks on every chunk that it is a run of whole handbook sentences and
comes from one section, and that the chunks of each strategy together contain every sentence. All 129 chunks
are in [`results/chunks.csv`](results/chunks.csv).

### 1.3 Embedding models

Three free `sentence-transformers` models from one family, BAAI's BGE v1.5, sorted by vector size as in the brief.
They are trained the same way, so the main difference between them is size, and that keeps the comparison fair.

| Size | Model | Parameters | Dimensions | Model input limit |
|---|---|---|---|---|
| Small | `BAAI/bge-small-en-v1.5` | 33 million | 384 | 512 tokens |
| Medium | `BAAI/bge-base-en-v1.5` | 109 million | 768 | 512 tokens |
| Large | `BAAI/bge-large-en-v1.5` | 335 million | 1,024 | 512 tokens |

Each chunk's text, title included, becomes one vector of length 1, so the cosine similarity of two vectors is their
dot product. A question gets BGE's retrieval instruction in front ("Represent this sentence for searching relevant
passages: "); chunks do not. Each model and strategy has its own **vector store**: a NumPy matrix, one row per chunk,
next to the chunk table. That makes nine stores.

| Size | Strategy | Chunks | Longest chunk | Indexing time | Per chunk | Vectors | Finds itself first |
|---|---|---|---|---|---|---|---|
| Small | Fixed | 50 | 156 tokens | 1.62 s | 32 ms | 75 KB | 50/50 |
| Small | Overlapping | 31 | 346 tokens | 2.27 s | 73 ms | 46 KB | 31/31 |
| Small | Hybrid | 48 | 162 tokens | 1.70 s | 35 ms | 72 KB | 48/48 |
| Medium | Fixed | 50 | 156 tokens | 4.93 s | 99 ms | 150 KB | 50/50 |
| Medium | Overlapping | 31 | 346 tokens | 7.19 s | 232 ms | 93 KB | 31/31 |
| Medium | Hybrid | 48 | 162 tokens | 6.59 s | 137 ms | 144 KB | 48/48 |
| Large | Fixed | 50 | 156 tokens | 17.10 s | 342 ms | 200 KB | 50/50 |
| Large | Overlapping | 31 | 346 tokens | 23.50 s | 758 ms | 124 KB | 31/31 |
| Large | Hybrid | 48 | 162 tokens | 17.46 s | 364 ms | 192 KB | 48/48 |

No chunk reaches the 512-token limit, so nothing is cut off, and every chunk, searched with its own vector, finds
itself first. Indexing time grows with the model: about 47 ms
a chunk for the small model and 488 ms for the large one, on
our laptop's CPU.

### 1.4 Retrieval

The question is embedded with the store's own model, every chunk is scored by cosine similarity, and the top 3 come
back with their rank, score, section and source paragraphs. One question on all nine stores, "How do I check in when
I get to the meetup?" (the check-in paragraph is S06-P3):

| Embedding | Chunking | Top chunk | Score | Its paragraphs | Paragraphs in the top 3 | Embed question | Search |
|---|---|---|---|---|---|---|---|
| Small | Fixed | fix-24 | 0.7584 | S06-P2, S06-P3 | S06-P2, S06-P3, S10-P1, S10-P2, S07-P1 | 23 ms | 2.1 ms |
| Small | Overlapping | ove-15 | 0.7582 | S06-P3, S06-P4 | S06-P3, S06-P4, S06-P2, S10-P1, S10-P2 | 21 ms | 2.4 ms |
| Small | Hybrid | hyb-23 | 0.7729 | S06-P3 | S06-P3, S10-P2, S06-P2 | 19 ms | 2.5 ms |
| Medium | Fixed | fix-24 | 0.6903 | S06-P2, S06-P3 | S06-P2, S06-P3, S10-P1, S10-P2, S06-P4 | 49 ms | 2.3 ms |
| Medium | Overlapping | ove-15 | 0.7229 | S06-P3, S06-P4 | S06-P3, S06-P4, S06-P2, S10-P1, S10-P2 | 50 ms | 2.7 ms |
| Medium | Hybrid | hyb-23 | 0.7274 | S06-P3 | S06-P3, S06-P2, S10-P2 | 65 ms | 2.5 ms |
| Large | Fixed | fix-24 | 0.7305 | S06-P2, S06-P3 | S06-P2, S06-P3, S07-P2, S07-P3, S10-P1, S10-P2 | 193 ms | 2.7 ms |
| Large | Overlapping | ove-15 | 0.7381 | S06-P3, S06-P4 | S06-P3, S06-P4, S06-P2, S10-P1, S10-P2 | 192 ms | 2.5 ms |
| Large | Hybrid | hyb-23 | 0.7561 | S06-P3 | S06-P3, S10-P2, S10-P1 | 193 ms | 2.6 ms |

Every configuration ranks a chunk containing S06-P3 first. Embedding the question takes about
21 ms with the small model, 55 ms with the medium one and
193 ms with the large one; the search itself takes a few milliseconds.

### 1.5 Generation

**The prompt** has three parts. The system instruction says to answer only from the excerpts, to say when they do not
cover the question instead of guessing, to keep to four sentences and to cite the excerpts. Then come the 3 retrieved
chunks, numbered in rank order and labelled with their section, and finally the question.

**The generation model is gpt-oss-20b**, one of the 15 models our team evaluated in A6 and A7. It scored 9.85 out of 10
across QuadConnect's five jobs in A7. It runs on Groq with A7's exact settings: temperature 0, at most 1,024 new
tokens, and low reasoning effort. The same model and settings are used for every answer in every experiment, so a
difference between configurations comes from retrieval. Each reply is saved in
[`results/generations.jsonl`](results/generations.jsonl) under a hash of the model, its settings and the whole prompt,
so a re-run needs no API key.

The whole pipeline on three questions (the medium model with hybrid chunks); the third is not in the handbook:

| Question | Chunks retrieved | Answer | Embed | Search | Generate | Prompt tokens |
|---|---|---|---|---|---|---|
| Which venues can seat a full squad of eight? | hyb-19, hyb-22, hyb-20 | A full squad of eight can fit at the Illini Union (12 seats), the Grainger Engineering Library (8 seats), and the Main Quad (20 seats). Espresso Royale only seats six, so it does not accommodate a full squad of eight. [2] | 46 ms | 2.2 ms | 3.15 s | 561 |
| What does Google send to QuadConnect when I sign in? | hyb-05, hyb-06, hyb-04 | When you sign in with Google, Google sends QuadConnect four pieces of information: your name, your email address, a link to your profile picture, and your Google account number. This is all that QuadConnect receives from Google. [1] | 50 ms | 2.7 ms | 1.16 s | 604 |
| Can I use QuadConnect as an app on my phone? | hyb-01, hyb-03, hyb-05 | The handbook does not cover whether QuadConnect is available as a phone app. | 49 ms | 1.9 ms | 0.80 s | 596 |

The first two answers are correct and cite the excerpt they used, and the third correctly says the handbook does not
cover it. Generating takes about a second or more, far longer than retrieval, so the language model dominates the
time a student waits.
