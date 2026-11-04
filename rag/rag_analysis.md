# QuadConnect RAG system: analysis (P1-A8)

**The Connectors · Team 13 · INFO 490, Fall 2026**

This document explains the retrieval-augmented generation (RAG) system we built for QuadConnect, and what our
experiments show about it. The implementation and every number below are in
[`rag_system.ipynb`](rag_system.ipynb); the saved results are in [`results/`](results/).

| Part | Section | Status |
|---|---|---|
| 1. Build the RAG pipeline | [1. The pipeline](#1-the-pipeline) | Done |
| 2. System experiments | [2. Experiments](#2-experiments) | Done |
| 3. Failure analysis and improvement | [3. Failures and a fix](#3-failures-and-a-fix) | Done |
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
| Small | Fixed | 50 | 156 tokens | 1.75 s | 35 ms | 75 KB | 50/50 |
| Small | Overlapping | 31 | 346 tokens | 2.42 s | 78 ms | 46 KB | 31/31 |
| Small | Hybrid | 48 | 162 tokens | 1.82 s | 38 ms | 72 KB | 48/48 |
| Medium | Fixed | 50 | 156 tokens | 5.28 s | 106 ms | 150 KB | 50/50 |
| Medium | Overlapping | 31 | 346 tokens | 7.48 s | 241 ms | 93 KB | 31/31 |
| Medium | Hybrid | 48 | 162 tokens | 5.22 s | 109 ms | 144 KB | 48/48 |
| Large | Fixed | 50 | 156 tokens | 17.59 s | 352 ms | 200 KB | 50/50 |
| Large | Overlapping | 31 | 346 tokens | 93.95 s | 3031 ms | 124 KB | 31/31 |
| Large | Hybrid | 48 | 162 tokens | 18.59 s | 387 ms | 192 KB | 48/48 |

No chunk reaches the 512-token limit, so nothing is cut off, and every chunk, searched with its own vector, finds
itself first. Indexing time grows with the model: about 50 ms
a chunk for the small model and 1257 ms for the large one, on
our laptop's CPU.

### 1.4 Retrieval

The question is embedded with the store's own model, every chunk is scored by cosine similarity, and the top 3 come
back with their rank, score, section and source paragraphs. One question on all nine stores, "How do I check in when
I get to the meetup?" (the check-in paragraph is S06-P3):

| Embedding | Chunking | Top chunk | Score | Its paragraphs | Paragraphs in the top 3 | Embed question | Search |
|---|---|---|---|---|---|---|---|
| Small | Fixed | fix-24 | 0.7584 | S06-P2, S06-P3 | S06-P2, S06-P3, S10-P1, S10-P2, S07-P1 | 38 ms | 2.9 ms |
| Small | Overlapping | ove-15 | 0.7582 | S06-P3, S06-P4 | S06-P3, S06-P4, S06-P2, S10-P1, S10-P2 | 27 ms | 3.0 ms |
| Small | Hybrid | hyb-23 | 0.7729 | S06-P3 | S06-P3, S10-P2, S06-P2 | 29 ms | 2.8 ms |
| Medium | Fixed | fix-24 | 0.6903 | S06-P2, S06-P3 | S06-P2, S06-P3, S10-P1, S10-P2, S06-P4 | 62 ms | 2.6 ms |
| Medium | Overlapping | ove-15 | 0.7229 | S06-P3, S06-P4 | S06-P3, S06-P4, S06-P2, S10-P1, S10-P2 | 60 ms | 2.8 ms |
| Medium | Hybrid | hyb-23 | 0.7274 | S06-P3 | S06-P3, S06-P2, S10-P2 | 134 ms | 2.4 ms |
| Large | Fixed | fix-24 | 0.7305 | S06-P2, S06-P3 | S06-P2, S06-P3, S07-P2, S07-P3, S10-P1, S10-P2 | 219 ms | 2.6 ms |
| Large | Overlapping | ove-15 | 0.7381 | S06-P3, S06-P4 | S06-P3, S06-P4, S06-P2, S10-P1, S10-P2 | 221 ms | 2.0 ms |
| Large | Hybrid | hyb-23 | 0.7561 | S06-P3 | S06-P3, S10-P2, S10-P1 | 224 ms | 2.5 ms |

Every configuration ranks a chunk containing S06-P3 first. Embedding the question takes about
31 ms with the small model, 85 ms with the medium one and
222 ms with the large one; the search itself takes a few milliseconds.

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
| Which venues can seat a full squad of eight? | hyb-19, hyb-22, hyb-20 | A full squad of eight can fit at the Illini Union (12 seats), the Grainger Engineering Library (8 seats), and the Main Quad (20 seats). Espresso Royale only seats six, so it does not accommodate a full squad of eight. [2] | 56 ms | 2.4 ms | 3.15 s | 561 |
| What does Google send to QuadConnect when I sign in? | hyb-05, hyb-06, hyb-04 | When you sign in with Google, Google sends QuadConnect four pieces of information: your name, your email address, a link to your profile picture, and your Google account number. This is all that QuadConnect receives from Google. [1] | 65 ms | 2.6 ms | 1.16 s | 604 |
| Can I use QuadConnect as an app on my phone? | hyb-01, hyb-03, hyb-05 | The handbook does not cover whether QuadConnect is available as a phone app. | 62 ms | 2.6 ms | 0.80 s | 596 |

The first two answers are correct and cite the excerpt they used, and the third correctly says the handbook does not
cover it. Generating takes about a second or more, far longer than retrieval, so the language model dominates the
time a student waits.

---

## 2. Experiments

Part 2 measures how the embedding model's size and the chunking strategy change what the system retrieves and how
well it answers. Every test question runs through all nine configurations (3 embedding models × 3 chunking
strategies). Everything else stays fixed: k = 3 chunks, the same prompt, and the same language model with the same
settings. So any difference between two configurations comes from the embedding model or the chunking.

### 2.1 Test queries

Eight questions a student could ask, worded the way a student would ask them rather than the way the handbook says it.
They test different kinds of difficulty:

| Question | What makes it hard |
|---|---|
| Q1 | One fact, but the answer means comparing numbers (seats against a squad of eight) |
| Q2 | The answer is something the app *cannot* do, which a model might paper over |
| Q3, Q4 | Worded differently from the handbook: it never says "why didn't I get a match", "shy" or "nervous" |
| Q5, Q6 | The answer is stated in two sections, so it can be found in more than one place |
| Q7 | Several facts in one answer |
| Q8 | Not in the handbook at all: the right answer is to say so, not to guess |

**For each answerable question, we wrote down the key facts a complete answer must state before running any
experiment.** For each fact we also recorded the evidence: the handbook sentences that state it. Step 2.2 scores
against these:

* a retrieved chunk is **relevant** if it contains an evidence sentence for any of the question's facts;
* a fact is **in the context** if at least one of its evidence sentences is in the three retrieved chunks;
* a fact is **in the answer** if the answer states it. A pattern checks this; for example, Q4's first fact needs the
  words "Friend Connect".

For Q8, any price, or a claim that QuadConnect is free, would be invented: the handbook says nothing about payment.

| Q | Question | Kind | Key facts a complete answer states | Evidence in |
|---|---|---|---|---|
| Q1 | Our squad has eight people. Which venues have enough seats for all of us? | One fact, with numbers to compare | The Illini Union fits the squad: it seats 12 / The Grainger Engineering Library fits the squad: it seats 8 / The Main Quad fits the squad: it seats 20 / Espresso Royale is too small: it seats 6 | S06-P2 |
| Q2 | I forgot my password. How do I get back into my account? | One paragraph; the answer is something the app cannot do | QuadConnect cannot send a password reset link, because it cannot send email yet / If you signed up with Google, use Continue with Google / Otherwise, email the address on the Privacy page; the team sets a new password | S02-P3 |
| Q3 | Why didn't I get a match this week? | A why-question in other words than the handbook's | A match needs at least one free weekend slot in common with other students / Marking more weekend windows, or both days, makes a match more likely | S04-P2, S13-P2 |
| Q4 | I'm shy and big groups make me nervous. Can I meet just one person? | In other words than the handbook's: it never says shy or nervous | Yes: choose Friend Connect, a one-on-one meetup with a single other student / Set the group size preference to One person | S03-P4, S03-P5, S05-P4 |
| Q5 | Will the others in my match see the rating and note I leave after the meetup? | Stated in two sections, in three paragraphs | No: the rating and the note are never shown to the other students in the match / Only totals and averages across all students are shown, on the Feedback summary page | S09-P1, S09-P3, S13-P5 |
| Q6 | Can the AI that checks venue suggestions approve my venue on its own? | A safety rule, stated in two sections | No: the automatic check only advises, and never approves a venue / Staff review the suggestion and make the decision | S07-P1, S07-P3, S07-P4, S13-P3, S13-P4 |
| Q7 | Does QuadConnect sell my data or share it with other companies? | Several facts in one answer | Nothing about you is sold or shared / The only public data is how many students picked each interest: no names, NetIDs or email addresses / Outside services get only what they need: PythonAnywhere hosts the site, Google handles sign-in, and Groq checks venue suggestions with contact details removed | S07-P4, S11-P2, S12-P2 |
| Q8 | Do I have to pay to use QuadConnect? | Not in the handbook: the right answer says so | None: the handbook does not cover it, and the answer should say so | - |

### 2.2 Evaluation table

Each of the 8 questions runs through each of the 9 configurations: **72 runs**, each with its retrieved chunks, its
answer and its timings. The columns are the brief's:

* **Retrieved chunks:** the three chunks in rank order, each with its id, the paragraphs it comes from, its cosine
  similarity to the question, whether it is relevant (holds evidence) or noise, and its first words. The full text of
  every retrieved chunk, and every full answer, is in `results/evaluation.csv`.
* **Retrieved Context Quality:** how many of the question's key facts the three chunks contain, and how many of the
  three chunks are relevant. *Good* means the context holds every key fact, *Partial* some, *Poor* none. Q8 has
  nothing to find.
* **Answer Quality,** from 1 to 10: 1 + 9 × the share of the key facts the answer states, minus 3 for a claim the
  handbook contradicts. For Q8 it is 10 if the answer says the handbook does not cover the question and invents
  nothing, and 1 otherwise.
* **Latency:** embedding the question and searching (measured on this run), and the language model's reply (measured
  when the reply was first generated, then saved with it).
* **Notes:** what went wrong and where: a fact missing from the context (with the rank its best chunk reached in the
  full ranking), a fact the answer left out although the context had it, a refusal, noise.

Every answer score comes from code, so it is the same on every run. The scores were then checked against the text
of all 72 answers. That check found two patterns that misread an answer, and both were corrected in Step 2.1: Q7's
"not sold" pattern had counted the refusal "the excerpts do not mention QuadConnect selling" as the fact, and Q3's
"mark more windows" pattern had matched words that describe the problem ("only marked one slot") rather than the fix.

**Each configuration over the eight questions.** The context and answer columns cover the seven answerable questions
and their 18 key facts; Q8 has its own column.

| Embedding model | Chunking | Good | Partial | Poor | Facts in context | Relevant chunks (of 3) | Facts stated | Answer score | Q8 declined | Embed (ms, median) | Generate (s, median) | Prompt tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Small | Fixed | 5 | 2 | 0 | 15/18 | 1.71 | 14/18 | 7.86 | yes | 25 | 0.91 | 547 |
| Small | Overlapping | 7 | 0 | 0 | 18/18 | 1.71 | 16/18 | 8.93 | yes | 24 | 0.89 | 992 |
| Small | Hybrid | 6 | 0 | 1 | 16/18 | 1.43 | 13/18 | 7.21 | yes | 25 | 0.74 | 549 |
| Medium | Fixed | 5 | 2 | 0 | 14/18 | 1.57 | 11/18 | 7.10 | yes | 59 | 0.95 | 542 |
| Medium | Overlapping | 6 | 1 | 0 | 17/18 | 1.71 | 14/18 | 7.86 | yes | 59 | 0.81 | 989 |
| Medium | Hybrid | 6 | 0 | 1 | 16/18 | 1.43 | 13/18 | 7.21 | yes | 58 | 0.72 | 555 |
| Large | Fixed | 6 | 0 | 1 | 15/18 | 1.71 | 14/18 | 8.07 | yes | 211 | 1.27 | 556 |
| Large | Overlapping | 7 | 0 | 0 | 18/18 | 1.86 | 15/18 | 8.50 | yes | 213 | 0.87 | 994 |
| Large | Hybrid | 5 | 1 | 1 | 15/18 | 1.29 | 13/18 | 7.21 | yes | 213 | 0.73 | 557 |

**The full table: 72 runs**, one table per question, each with its nine configurations. "Retrieved chunks" lists the
three chunks in rank order, with the paragraphs each one comes from, its similarity score and the first words of its
text. The answers are under each table.

#### Q1: Our squad has eight people. Which venues have enough seats for all of us?

*One fact, with numbers to compare. Evidence in: S06-P2.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q1 | [1] noise · fix-20 (S05-P3, S05-P4) · 0.712 · "This matters most in a squad, where several people ..."<br>[2] relevant · fix-24 (S06-P2, S06-P3) · 0.673 · "A full squad of eight therefore fits every venue ..."<br>[3] relevant · fix-23 (S06-P2) · 0.632 · "Each venue page tells you how to find your ..." | Good: 4/4 facts; 2/3 chunks relevant | 10/10: 4/4 facts stated | 1.67 s: embed 25 ms + search 2.8 ms + generate 1.64 s | Context had every fact. 1 of 3 chunks is noise. |
| Small (bge-small-en-v1.5) | Overlapping | Q1 | [1] relevant · ove-14 (S06-P2, S06-P3) · 0.669 · "Each venue page tells you how to find your ..."<br>[2] noise · ove-16 (S07-P1, S07-P2) · 0.624 · "If you know a public place that would suit ..."<br>[3] noise · ove-12 (S05-P3, S05-P4) · 0.622 · "A match moves through four stages. It starts as ..." | Good: 4/4 facts; 1/3 chunks relevant | 10/10: 4/4 facts stated | 0.80 s: embed 24 ms + search 2.0 ms + generate 0.77 s | Context had every fact. 2 of 3 chunks are noise. |
| Small (bge-small-en-v1.5) | Hybrid | Q1 | [1] noise · hyb-19 (S05-P4) · 0.677 · "Squad matches bring four to eight students together, so ..."<br>[2] relevant · hyb-22 (S06-P2) · 0.661 · "At Espresso Royale on Goodwin you meet in the ..."<br>[3] noise · hyb-38 (S10-P2) · 0.622 · "A good meetup depends on everyone showing up. Accept ..." | Good: 4/4 facts; 1/3 chunks relevant | 10/10: 4/4 facts stated | 0.72 s: embed 26 ms + search 2.4 ms + generate 0.70 s | Context had every fact. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Fixed | Q1 | [1] noise · fix-20 (S05-P3, S05-P4) · 0.667 · "This matters most in a squad, where several people ..."<br>[2] relevant · fix-24 (S06-P2, S06-P3) · 0.593 · "A full squad of eight therefore fits every venue ..."<br>[3] noise · fix-21 (S05-P4) · 0.530 · "Your group size preference matters here as well. A ..." | Partial: 1/4 facts; 1/3 chunks relevant | 3.2/10: 1/4 facts stated | 2.00 s: embed 60 ms + search 2.3 ms + generate 1.94 s | Context missed 'Illini Union' (its best chunk ranked 4), 'Grainger' (its best chunk ranked 4), 'Main Quad' (its best chunk ranked 4). 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Overlapping | Q1 | [1] relevant · ove-14 (S06-P2, S06-P3) · 0.525 · "Each venue page tells you how to find your ..."<br>[2] noise · ove-12 (S05-P3, S05-P4) · 0.522 · "A match moves through four stages. It starts as ..."<br>[3] noise · ove-16 (S07-P1, S07-P2) · 0.505 · "If you know a public place that would suit ..." | Good: 4/4 facts; 1/3 chunks relevant | 10/10: 4/4 facts stated | 0.95 s: embed 59 ms + search 2.4 ms + generate 0.89 s | Context had every fact. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Hybrid | Q1 | [1] noise · hyb-19 (S05-P4) · 0.658 · "Squad matches bring four to eight students together, so ..."<br>[2] relevant · hyb-22 (S06-P2) · 0.577 · "At Espresso Royale on Goodwin you meet in the ..."<br>[3] noise · hyb-25 (S07-P1) · 0.537 · "If you know a public place that would suit ..." | Good: 4/4 facts; 1/3 chunks relevant | 10/10: 4/4 facts stated | 0.97 s: embed 60 ms + search 2.3 ms + generate 0.91 s | Context had every fact. 2 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Fixed | Q1 | [1] noise · fix-20 (S05-P3, S05-P4) · 0.667 · "This matters most in a squad, where several people ..."<br>[2] relevant · fix-23 (S06-P2) · 0.625 · "Each venue page tells you how to find your ..."<br>[3] relevant · fix-24 (S06-P2, S06-P3) · 0.623 · "A full squad of eight therefore fits every venue ..." | Good: 4/4 facts; 2/3 chunks relevant | 10/10: 4/4 facts stated | 0.89 s: embed 213 ms + search 1.9 ms + generate 0.67 s | Context had every fact. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Overlapping | Q1 | [1] relevant · ove-14 (S06-P2, S06-P3) · 0.637 · "Each venue page tells you how to find your ..."<br>[2] relevant · ove-13 (S06-P1, S06-P2) · 0.615 · "Every QuadConnect meetup takes place at an approved campus ..."<br>[3] noise · ove-16 (S07-P1, S07-P2) · 0.592 · "If you know a public place that would suit ..." | Good: 4/4 facts; 2/3 chunks relevant | 10/10: 4/4 facts stated | 1.02 s: embed 219 ms + search 2.4 ms + generate 0.80 s | Context had every fact. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Hybrid | Q1 | [1] relevant · hyb-22 (S06-P2) · 0.661 · "At Espresso Royale on Goodwin you meet in the ..."<br>[2] noise · hyb-19 (S05-P4) · 0.642 · "Squad matches bring four to eight students together, so ..."<br>[3] noise · hyb-26 (S07-P2) · 0.594 · "The form checks your suggestion before it is saved. ..." | Good: 4/4 facts; 1/3 chunks relevant | 10/10: 4/4 facts stated | 0.95 s: embed 213 ms + search 2.4 ms + generate 0.73 s | Context had every fact. 2 of 3 chunks are noise. |

<details>
<summary>The nine answers to Q1</summary>

* **Small, Fixed** (10/10: 4/4 facts stated): Your squad of eight can fit in any venue that seats at least eight people. According to the handbook, the Illini Union seats 12, the Grainger Engineering Library seats 8, and the Main Quad seats 20, so all three of those venues can accommodate your group. Espresso Royale only seats six, so it would be too small for eight people. [1] [3]

* **Small, Overlapping** (10/10: 4/4 facts stated): Your squad of eight can fit at any venue that lists at least eight seats. According to the venue details, the Illini Union seats twelve, the Grainger Engineering Library seats eight, and the Main Quad seats twenty, so all three of those venues can accommodate your group. Espresso Royale only seats six, so it would not fit an eight‑person squad. [1]

* **Small, Hybrid** (10/10: 4/4 facts stated): Your squad of eight can fit in any venue that seats at least eight people. According to the venue list, the Illini Union (12 seats), Grainger Engineering Library (8 seats), and Main Quad (20 seats) all have enough space for your group. Espresso Royale only seats six, so it would be too small for a full squad. [2]

* **Medium, Fixed** (3.2/10: 1/4 facts stated): All venues can accommodate a full squad of eight people except Espresso Royale, which is only suitable for Friend Connect meetups and smaller squads. [2]

* **Medium, Overlapping** (10/10: 4/4 facts stated): Your squad of eight can fit at any venue that seats at least eight people. According to the venue information, the Illini Union seats twelve, the Grainger Engineering Library seats eight, and the Main Quad seats twenty, so all three of those venues can accommodate your group. Espresso Royale only seats six, so it would be too small for eight people. [1]

* **Medium, Hybrid** (10/10: 4/4 facts stated): Your squad of eight can fit in any venue that seats at least eight people. According to the venue list, the Illini Union (12 seats), Grainger Engineering Library (8 seats), and Main Quad (20 seats) all accommodate your group. Espresso Royale only seats six, so it would be too small for an eight‑person squad.

* **Large, Fixed** (10/10: 4/4 facts stated): Your squad of eight can fit in any venue that seats at least eight people. According to the venue details, the Illini Union (12 seats), Grainger Engineering Library (8 seats), and Main Quad (20 seats) all accommodate your group. Espresso Royale only seats six, so it would be too small for an eight‑person squad. [2] [3]

* **Large, Overlapping** (10/10: 4/4 facts stated): Your squad of eight can fit at any venue that seats at least eight people. According to the venue list, the Illini Union seats twelve, the Grainger Engineering Library seats eight, and the Main Quad seats twenty, so all three of those locations can accommodate your full squad. Espresso Royale only seats six, so it would not fit all eight people. [1]

* **Large, Hybrid** (10/10: 4/4 facts stated): Your squad of eight can fit in any venue that seats at least eight people. According to the handbook, the Illini Union seats twelve, the Grainger Engineering Library seats eight, and the Main Quad seats twenty, so all three of those venues can accommodate your group. Espresso Royale only seats six, so it would be too small for an eight‑person squad. [1]

</details>

#### Q2: I forgot my password. How do I get back into my account?

*One paragraph; the answer is something the app cannot do. Evidence in: S02-P3.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q2 | [1] relevant · fix-07 (S02-P2, S02-P3) · 0.695 · "Your QuadConnect profile is kept separate from the way ..."<br>[2] noise · fix-05 (S02-P1) · 0.635 · "You can create a QuadConnect account in two ways. ..."<br>[3] noise · fix-08 (S02-P3) · 0.606 · "There are no tracking cookies, no analytics cookies and ..." | Good: 3/3 facts; 1/3 chunks relevant | 10/10: 3/3 facts stated | 0.93 s: embed 24 ms + search 2.6 ms + generate 0.90 s | Context had every fact. 2 of 3 chunks are noise. |
| Small (bge-small-en-v1.5) | Overlapping | Q2 | [1] noise · ove-03 (S02-P1, S02-P2) · 0.644 · "You can create a QuadConnect account in two ways. ..."<br>[2] relevant · ove-04 (S02-P2, S02-P3) · 0.637 · "When you continue with Google, Google sends QuadConnect four ..."<br>[3] noise · ove-25 (S11-P1, S11-P2) · 0.571 · "QuadConnect keeps only what it needs. For your account ..." | Good: 3/3 facts; 1/3 chunks relevant | 10/10: 3/3 facts stated | 1.28 s: embed 24 ms + search 2.5 ms + generate 1.26 s | Context had every fact. 2 of 3 chunks are noise. |
| Small (bge-small-en-v1.5) | Hybrid | Q2 | [1] relevant · hyb-06 (S02-P3) · 0.672 · "QuadConnect cannot send email yet, so it cannot send ..."<br>[2] noise · hyb-04 (S02-P1) · 0.636 · "You can create a QuadConnect account in two ways. ..."<br>[3] noise · hyb-05 (S02-P2) · 0.616 · "When you continue with Google, Google sends QuadConnect four ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 0.75 s: embed 24 ms + search 2.4 ms + generate 0.72 s | Context had every fact. Answer left out 'no reset email' although the context had it. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Fixed | Q2 | [1] relevant · fix-07 (S02-P2, S02-P3) · 0.622 · "Your QuadConnect profile is kept separate from the way ..."<br>[2] noise · fix-05 (S02-P1) · 0.581 · "You can create a QuadConnect account in two ways. ..."<br>[3] noise · fix-06 (S02-P1, S02-P2) · 0.482 · "The only pages open to everyone are the landing ..." | Good: 3/3 facts; 1/3 chunks relevant | 10/10: 3/3 facts stated | 0.91 s: embed 66 ms + search 2.3 ms + generate 0.84 s | Context had every fact. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Overlapping | Q2 | [1] noise · ove-03 (S02-P1, S02-P2) · 0.541 · "You can create a QuadConnect account in two ways. ..."<br>[2] relevant · ove-04 (S02-P2, S02-P3) · 0.522 · "When you continue with Google, Google sends QuadConnect four ..."<br>[3] noise · ove-21 (S08-P3, S08-P4) · 0.447 · "If you would rather describe the students you want ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 1.15 s: embed 57 ms + search 2.3 ms + generate 1.09 s | Context had every fact. Answer left out 'no reset email' although the context had it. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Hybrid | Q2 | [1] relevant · hyb-06 (S02-P3) · 0.595 · "QuadConnect cannot send email yet, so it cannot send ..."<br>[2] noise · hyb-04 (S02-P1) · 0.567 · "You can create a QuadConnect account in two ways. ..."<br>[3] noise · hyb-05 (S02-P2) · 0.533 · "When you continue with Google, Google sends QuadConnect four ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 0.78 s: embed 58 ms + search 2.3 ms + generate 0.72 s | Context had every fact. Answer left out 'no reset email' although the context had it. 2 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Fixed | Q2 | [1] relevant · fix-07 (S02-P2, S02-P3) · 0.584 · "Your QuadConnect profile is kept separate from the way ..."<br>[2] noise · fix-05 (S02-P1) · 0.571 · "You can create a QuadConnect account in two ways. ..."<br>[3] noise · fix-06 (S02-P1, S02-P2) · 0.515 · "The only pages open to everyone are the landing ..." | Good: 3/3 facts; 1/3 chunks relevant | 10/10: 3/3 facts stated | 1.05 s: embed 207 ms + search 1.9 ms + generate 0.84 s | Context had every fact. 2 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Overlapping | Q2 | [1] noise · ove-03 (S02-P1, S02-P2) · 0.568 · "You can create a QuadConnect account in two ways. ..."<br>[2] relevant · ove-04 (S02-P2, S02-P3) · 0.547 · "When you continue with Google, Google sends QuadConnect four ..."<br>[3] noise · ove-15 (S06-P3, S06-P4) · 0.502 · "When you arrive, you check in with your match's ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 2.35 s: embed 237 ms + search 1.9 ms + generate 2.11 s | Context had every fact. Answer left out 'no reset email' although the context had it. 2 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Hybrid | Q2 | [1] relevant · hyb-06 (S02-P3) · 0.584 · "QuadConnect cannot send email yet, so it cannot send ..."<br>[2] noise · hyb-04 (S02-P1) · 0.558 · "You can create a QuadConnect account in two ways. ..."<br>[3] noise · hyb-05 (S02-P2) · 0.541 · "When you continue with Google, Google sends QuadConnect four ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 0.96 s: embed 237 ms + search 2.3 ms + generate 0.72 s | Context had every fact. Answer left out 'no reset email' although the context had it. 2 of 3 chunks are noise. |

<details>
<summary>The nine answers to Q2</summary>

* **Small, Fixed** (10/10: 3/3 facts stated): If you signed up with Google, simply click **Continue with Google** on the login page. If you created a password, email the address listed on the Privacy page and the team will set a new password for you. (QuadConnect cannot send a password‑reset link itself.)【1】

* **Small, Overlapping** (10/10: 3/3 facts stated): If you signed up with a password, you can’t reset it yourself because QuadConnect can’t send email. Instead, email the address listed on the Privacy page and the team will set a new password for you. If you signed up with Google, simply use “Continue with Google” on the login page to sign back in.

* **Small, Hybrid** (7/10: 2/3 facts stated): If you forgot your password and you signed up with a username and password, email the address listed on the Privacy page and the team will set a new password for you. If you signed up with Google, simply use “Continue with Google” on the login page to sign back in.

* **Medium, Fixed** (10/10: 3/3 facts stated): If you signed up with Google, simply use “Continue with Google” on the login page. If you created a password‑based account, email the address listed on the Privacy page and the team will set a new password for you. (QuadConnect cannot send a password reset link itself.)

* **Medium, Overlapping** (7/10: 2/3 facts stated): If you signed up with a password, email the address listed on the Privacy page and the team will set a new password for you. If you signed up with Google, simply use “Continue with Google” on the login page to sign back in.

* **Medium, Hybrid** (7/10: 2/3 facts stated): If you forgot your password and you signed up with a username and password, email the address listed on the Privacy page and the team will set a new password for you. If you signed up with Google, simply use “Continue with Google” on the login page to sign back in.

* **Large, Fixed** (10/10: 3/3 facts stated): If you signed up with Google, simply use “Continue with Google” on the login page. If you created a password‑based account, email the address listed on the Privacy page and the team will set a new password for you. (QuadConnect cannot send a password reset link itself.)

* **Large, Overlapping** (7/10: 2/3 facts stated): If you signed up with a password, email the address listed on the Privacy page and the team will set a new password for you. If you signed up with Google, simply use “Continue with Google” on the login page to sign back in.

* **Large, Hybrid** (7/10: 2/3 facts stated): If you forgot your password and you signed up with a username and password, email the address listed on the Privacy page and the team will set a new password for you. If you signed up with Google, simply use “Continue with Google” on the login page to sign back in.

</details>

#### Q3: Why didn't I get a match this week?

*A why-question in other words than the handbook's. Evidence in: S04-P2, S13-P2.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q3 | [1] relevant · fix-47 (S13-P2, S13-P3) · 0.689 · "Then QuadConnect cannot match you that week, because a ..."<br>[2] noise · fix-17 (S05-P1) · 0.683 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[3] relevant · fix-16 (S04-P2) · 0.645 · "Two students can be matched only if they share ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.95 s: embed 24 ms + search 2.3 ms + generate 0.92 s | Context had every fact. 1 of 3 chunks is noise. |
| Small (bge-small-en-v1.5) | Overlapping | Q3 | [1] noise · ove-10 (S05-P1, S05-P2) · 0.679 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[2] noise · ove-11 (S05-P2, S05-P3) · 0.664 · "For every student in a match, QuadConnect records a ..."<br>[3] relevant · ove-29 (S13-P2, S13-P3) · 0.657 · "What happens if my free times do not overlap ..." | Good: 2/2 facts; 1/3 chunks relevant | 10/10: 2/2 facts stated | 1.09 s: embed 24 ms + search 1.9 ms + generate 1.06 s | Context had every fact. 2 of 3 chunks are noise. |
| Small (bge-small-en-v1.5) | Hybrid | Q3 | [1] noise · hyb-17 (S05-P3) · 0.705 · "A match moves through four stages. It starts as ..."<br>[2] noise · hyb-15 (S05-P1) · 0.696 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[3] noise · hyb-18 (S05-P3) · 0.670 · "Declining is how you are withdrawn from a meetup ..." | Poor: 0/2 facts; 0/3 chunks relevant | 1/10: 0/2 facts stated | 0.78 s: embed 25 ms + search 2.4 ms + generate 0.76 s | Context missed 'shared slot needed' (its best chunk ranked 5), 'mark more windows' (its best chunk ranked 5). Answer said the handbook does not cover it. 3 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Fixed | Q3 | [1] noise · fix-17 (S05-P1) · 0.650 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[2] relevant · fix-16 (S04-P2) · 0.608 · "Two students can be matched only if they share ..."<br>[3] relevant · fix-47 (S13-P2, S13-P3) · 0.605 · "Then QuadConnect cannot match you that week, because a ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.99 s: embed 59 ms + search 2.2 ms + generate 0.93 s | Context had every fact. 1 of 3 chunks is noise. |
| Medium (bge-base-en-v1.5) | Overlapping | Q3 | [1] noise · ove-10 (S05-P1, S05-P2) · 0.612 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[2] relevant · ove-28 (S13-P1, S13-P2) · 0.603 · "Can I choose who I meet? Not directly. QuadConnect ..."<br>[3] relevant · ove-29 (S13-P2, S13-P3) · 0.589 · "What happens if my free times do not overlap ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.92 s: embed 58 ms + search 2.3 ms + generate 0.86 s | Context had every fact. 1 of 3 chunks is noise. |
| Medium (bge-base-en-v1.5) | Hybrid | Q3 | [1] noise · hyb-15 (S05-P1) · 0.669 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[2] noise · hyb-17 (S05-P3) · 0.666 · "A match moves through four stages. It starts as ..."<br>[3] noise · hyb-18 (S05-P3) · 0.636 · "Declining is how you are withdrawn from a meetup ..." | Poor: 0/2 facts; 0/3 chunks relevant | 1/10: 0/2 facts stated | 0.72 s: embed 54 ms + search 2.3 ms + generate 0.67 s | Context missed 'shared slot needed' (its best chunk ranked 5), 'mark more windows' (its best chunk ranked 5). Answer said the handbook does not cover it. 3 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Fixed | Q3 | [1] noise · fix-17 (S05-P1) · 0.666 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[2] relevant · fix-47 (S13-P2, S13-P3) · 0.663 · "Then QuadConnect cannot match you that week, because a ..."<br>[3] relevant · fix-16 (S04-P2) · 0.626 · "Two students can be matched only if they share ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.98 s: embed 204 ms + search 2.1 ms + generate 0.77 s | Context had every fact. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Overlapping | Q3 | [1] noise · ove-10 (S05-P1, S05-P2) · 0.671 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[2] relevant · ove-28 (S13-P1, S13-P2) · 0.639 · "Can I choose who I meet? Not directly. QuadConnect ..."<br>[3] noise · ove-11 (S05-P2, S05-P3) · 0.638 · "For every student in a match, QuadConnect records a ..." | Good: 2/2 facts; 1/3 chunks relevant | 10/10: 2/2 facts stated | 1.27 s: embed 204 ms + search 2.4 ms + generate 1.06 s | Context had every fact. 2 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Hybrid | Q3 | [1] noise · hyb-17 (S05-P3) · 0.686 · "A match moves through four stages. It starts as ..."<br>[2] noise · hyb-15 (S05-P1) · 0.675 · "QuadConnect works in weekly cycles. A matching week starts ..."<br>[3] noise · hyb-16 (S05-P2) · 0.652 · "For every student in a match, QuadConnect records a ..." | Poor: 0/2 facts; 0/3 chunks relevant | 1/10: 0/2 facts stated | 0.92 s: embed 213 ms + search 2.5 ms + generate 0.71 s | Context missed 'shared slot needed' (its best chunk ranked 5), 'mark more windows' (its best chunk ranked 5). Answer said the handbook does not cover it. 3 of 3 chunks are noise. |

<details>
<summary>The nine answers to Q3</summary>

* **Small, Fixed** (10/10: 2/2 facts stated): The handbook says that a match can only happen if you and another student share at least one free slot. If you only marked a single slot or didn’t mark any weekend windows, the matching algorithm has no common time to pair you with anyone, so no match will be produced that week. Make sure you keep your availability up‑to‑date and mark multiple windows or both weekend days to increase the chances of a match. [1] [3]

* **Small, Overlapping** (10/10: 2/2 facts stated): The handbook says that a match can only be made if you have at least one free‑time window that overlaps with someone else’s. If you didn’t get a match this week, it’s most likely because your free‑time slots didn’t line up with anyone else’s that week. The only way to fix this is to mark more of the eight weekend windows (10 AM‑6 PM on Saturday and Sunday) so the system has more overlap to work with. [3]

* **Small, Hybrid** (1/10: 0/2 facts stated): The handbook excerpts don’t explain why you might not receive a match in a given week.

* **Medium, Fixed** (10/10: 2/2 facts stated): The handbook says that a match can only happen if you and another student share at least one free time slot. If you didn’t have any overlapping availability with anyone else that week, QuadConnect simply couldn’t create a match for you. The solution is to add more free windows—especially on both weekend days—to give the algorithm more options for a match.

* **Medium, Overlapping** (10/10: 2/2 facts stated): You didn’t get a match because the system couldn’t find a shared free slot that week. QuadConnect requires at least one overlapping weekend window (10 AM‑6 PM on Saturday or Sunday) to create a match; if none of your marked windows overlap with anyone else’s, no match is produced. Make sure you’ve marked more of the eight weekend windows so the algorithm has room to find a compatible group.

* **Medium, Hybrid** (1/10: 0/2 facts stated): The handbook excerpts you provided don’t explain why you might not receive a match in a given week.

* **Large, Fixed** (10/10: 2/2 facts stated): You didn’t get a match because the app couldn’t find a shared free slot between you and any other student. Matching requires at least one common time window, and if you only marked one slot or none of the weekend windows, the algorithm has no overlap to work with. Make sure your availability is up‑to‑date and includes multiple windows, especially both Saturday and Sunday, to give the matching engine more options for a weekly match.

* **Large, Overlapping** (10/10: 2/2 facts stated): You didn’t get a match because QuadConnect could not find a shared free‑time slot with anyone else. A shared weekend window is the only hard rule for matching; if none of your marked windows overlap with another student’s, no match will be created that week. Make sure you mark more of the eight weekend windows (10 AM‑6 PM on Saturday and Sunday) so the algorithm has room to find a compatible group.

* **Large, Hybrid** (1/10: 0/2 facts stated): The handbook excerpts don’t explain why a student might not receive a match in a given week.

</details>

#### Q4: I'm shy and big groups make me nervous. Can I meet just one person?

*In other words than the handbook's: it never says shy or nervous. Evidence in: S03-P4, S03-P5, S05-P4.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q4 | [1] relevant · fix-21 (S05-P4) · 0.619 · "Your group size preference matters here as well. A ..."<br>[2] noise · fix-20 (S05-P3, S05-P4) · 0.606 · "This matters most in a squad, where several people ..."<br>[3] relevant · fix-12 (S03-P4) · 0.606 · "Then you choose how you want to meet. Friend ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 0.94 s: embed 26 ms + search 2.5 ms + generate 0.92 s | Context had every fact. Answer left out 'group size' although the context had it. 1 of 3 chunks is noise. |
| Small (bge-small-en-v1.5) | Overlapping | Q4 | [1] relevant · ove-08 (S03-P4, S03-P5) · 0.609 · "Then you choose how you want to meet. Friend ..."<br>[2] noise · ove-28 (S13-P1, S13-P2) · 0.586 · "Can I choose who I meet? Not directly. QuadConnect ..."<br>[3] relevant · ove-12 (S05-P3, S05-P4) · 0.579 · "A match moves through four stages. It starts as ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 0.94 s: embed 26 ms + search 2.5 ms + generate 0.91 s | Context had every fact. Answer left out 'group size' although the context had it. 1 of 3 chunks is noise. |
| Small (bge-small-en-v1.5) | Hybrid | Q4 | [1] noise · hyb-38 (S10-P2) · 0.602 · "A good meetup depends on everyone showing up. Accept ..."<br>[2] relevant · hyb-19 (S05-P4) · 0.596 · "Squad matches bring four to eight students together, so ..."<br>[3] relevant · hyb-10 (S03-P4) · 0.595 · "Then you choose how you want to meet. Friend ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 0.72 s: embed 24 ms + search 2.4 ms + generate 0.69 s | Context had every fact. Answer left out 'group size' although the context had it. 1 of 3 chunks is noise. |
| Medium (bge-base-en-v1.5) | Fixed | Q4 | [1] relevant · fix-21 (S05-P4) · 0.547 · "Your group size preference matters here as well. A ..."<br>[2] noise · fix-37 (S09-P2, S09-P3) · 0.529 · "In your feedback you can say that you want ..."<br>[3] noise · fix-20 (S05-P3, S05-P4) · 0.528 · "This matters most in a squad, where several people ..." | Good: 2/2 facts; 1/3 chunks relevant | 10/10: 2/2 facts stated | 0.87 s: embed 59 ms + search 1.9 ms + generate 0.81 s | Context had every fact. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Overlapping | Q4 | [1] relevant · ove-08 (S03-P4, S03-P5) · 0.535 · "Then you choose how you want to meet. Friend ..."<br>[2] relevant · ove-12 (S05-P3, S05-P4) · 0.524 · "A match moves through four stages. It starts as ..."<br>[3] noise · ove-28 (S13-P1, S13-P2) · 0.512 · "Can I choose who I meet? Not directly. QuadConnect ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 0.82 s: embed 61 ms + search 2.3 ms + generate 0.76 s | Context had every fact. Answer left out 'group size' although the context had it. 1 of 3 chunks is noise. |
| Medium (bge-base-en-v1.5) | Hybrid | Q4 | [1] noise · hyb-35 (S09-P2) · 0.536 · "Feedback is also how a one-off meetup can turn ..."<br>[2] relevant · hyb-19 (S05-P4) · 0.524 · "Squad matches bring four to eight students together, so ..."<br>[3] relevant · hyb-10 (S03-P4) · 0.522 · "Then you choose how you want to meet. Friend ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 0.78 s: embed 61 ms + search 2.9 ms + generate 0.72 s | Context had every fact. Answer left out 'group size' although the context had it. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Fixed | Q4 | [1] relevant · fix-21 (S05-P4) · 0.624 · "Your group size preference matters here as well. A ..."<br>[2] relevant · fix-12 (S03-P4) · 0.591 · "Then you choose how you want to meet. Friend ..."<br>[3] noise · fix-37 (S09-P2, S09-P3) · 0.587 · "In your feedback you can say that you want ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 2.92 s: embed 221 ms + search 2.3 ms + generate 2.69 s | Context had every fact. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Overlapping | Q4 | [1] relevant · ove-08 (S03-P4, S03-P5) · 0.596 · "Then you choose how you want to meet. Friend ..."<br>[2] relevant · ove-12 (S05-P3, S05-P4) · 0.575 · "A match moves through four stages. It starts as ..."<br>[3] noise · ove-22 (S09-P1, S09-P2) · 0.566 · "After a meetup you can leave private feedback about ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 1.06 s: embed 215 ms + search 2.4 ms + generate 0.84 s | Context had every fact. Answer left out 'group size' although the context had it. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Hybrid | Q4 | [1] noise · hyb-35 (S09-P2) · 0.609 · "Feedback is also how a one-off meetup can turn ..."<br>[2] relevant · hyb-10 (S03-P4) · 0.569 · "Then you choose how you want to meet. Friend ..."<br>[3] noise · hyb-38 (S10-P2) · 0.568 · "A good meetup depends on everyone showing up. Accept ..." | Partial: 1/2 facts; 1/3 chunks relevant | 5.5/10: 1/2 facts stated | 1.05 s: embed 225 ms + search 2.4 ms + generate 0.82 s | Context missed 'group size' (its best chunk ranked 4). 2 of 3 chunks are noise. |

<details>
<summary>The nine answers to Q4</summary>

* **Small, Fixed** (5.5/10: 1/2 facts stated): Yes—if you prefer a quieter, one‑on‑one meetup, you can choose Friend Connect. In your profile you can select “Friend Connect” to get matched with a single other student each week, which is designed for people who like a quieter, more personal conversation. This setting is the default if you don’t make a choice, and it will keep you from being placed in a larger squad. [3]

* **Small, Overlapping** (5.5/10: 1/2 facts stated): Yes—QuadConnect offers a one‑on‑one option called **Friend Connect** for students who prefer a quieter, more personal conversation. If you choose that setting, your matches will always be one‑on‑one rather than a larger squad. You can set this preference in your profile and it will be used for future matches. [1]

* **Small, Hybrid** (5.5/10: 1/2 facts stated): Yes, you can choose to meet just one person. In your profile you can select “Friend Connect,” which is a one‑on‑one meetup with a single other student. This option is designed for people who prefer a quieter, more personal conversation and is the default if you don’t choose otherwise. [3]

* **Medium, Fixed** (10/10: 2/2 facts stated): Yes, you can meet just one person. In the weekly matching, students who choose “One person” as their group size are matched for a one‑on‑one meetup, which is what Friend Connect is designed for. This option is specifically for those who prefer smaller, more intimate gatherings.

* **Medium, Overlapping** (5.5/10: 1/2 facts stated): Yes—QuadConnect offers a one‑on‑one option called **Friend Connect** for students who prefer a quieter, more personal conversation. If you choose that setting, your profile will be matched with a single other student each week. You can select Friend Connect in your profile settings, and the match you receive will carry that connection type.

* **Medium, Hybrid** (5.5/10: 1/2 facts stated): Yes, you can choose a one‑on‑one meetup. In your profile you can select “Friend Connect,” which is a one‑on‑one coffee with a single other student, so you’ll only be matched with one person each week. This option is designed for people who prefer a quieter, more personal conversation and avoids the pressure of larger groups.

* **Large, Fixed** (10/10: 2/2 facts stated): Yes. If you prefer a one‑on‑one meetup, choose the “One person” group size in your profile. That will place you on Friend Connect, which is a one‑on‑one coffee‑style meeting with a single other student. This option is designed for quieter, more personal conversations and is the default if you don’t make a choice. [1] [2]

* **Large, Overlapping** (5.5/10: 1/2 facts stated): Yes—QuadConnect lets you choose a one‑on‑one meetup. If you select “Friend Connect” (the default), you’ll be matched with a single other student for a quieter, more personal conversation. This option is designed for people who prefer a smaller setting and less group pressure.

* **Large, Hybrid** (5.5/10: 1/2 facts stated): Yes, you can choose a one‑on‑one meetup. In your profile you can select **Friend Connect**, which pairs you with a single other student for a quieter, more personal conversation. If you don’t choose, your profile defaults to Friend Connect, so you’ll automatically get one‑on‑one matches. This option is designed for people who prefer a quieter setting over larger groups. [2]

</details>

#### Q5: Will the others in my match see the rating and note I leave after the meetup?

*Stated in two sections, in three paragraphs. Evidence in: S09-P1, S09-P3, S13-P5.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q5 | [1] relevant · fix-36 (S09-P1, S09-P2) · 0.789 · "After a meetup you can leave private feedback about ..."<br>[2] noise · fix-19 (S05-P3) · 0.697 · "A match moves through four stages. It starts as ..."<br>[3] noise · fix-24 (S06-P2, S06-P3) · 0.695 · "A full squad of eight therefore fits every venue ..." | Partial: 1/2 facts; 1/3 chunks relevant | 5.5/10: 1/2 facts stated | 0.79 s: embed 26 ms + search 2.8 ms + generate 0.76 s | Context missed 'only totals' (its best chunk ranked 4). 2 of 3 chunks are noise. |
| Small (bge-small-en-v1.5) | Overlapping | Q5 | [1] relevant · ove-22 (S09-P1, S09-P2) · 0.779 · "After a meetup you can leave private feedback about ..."<br>[2] noise · ove-11 (S05-P2, S05-P3) · 0.723 · "For every student in a match, QuadConnect records a ..."<br>[3] relevant · ove-23 (S09-P2, S09-P3) · 0.720 · "Feedback is also how a one-off meetup can turn ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.89 s: embed 25 ms + search 2.3 ms + generate 0.86 s | Context had every fact. 1 of 3 chunks is noise. |
| Small (bge-small-en-v1.5) | Hybrid | Q5 | [1] relevant · hyb-34 (S09-P1) · 0.800 · "After a meetup you can leave private feedback about ..."<br>[2] relevant · hyb-48 (S13-P5) · 0.745 · "Who can see my feedback and my notes? Nobody ..."<br>[3] noise · hyb-35 (S09-P2) · 0.745 · "Feedback is also how a one-off meetup can turn ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.68 s: embed 25 ms + search 2.0 ms + generate 0.65 s | Context had every fact. 1 of 3 chunks is noise. |
| Medium (bge-base-en-v1.5) | Fixed | Q5 | [1] relevant · fix-36 (S09-P1, S09-P2) · 0.713 · "After a meetup you can leave private feedback about ..."<br>[2] relevant · fix-38 (S09-P3) · 0.678 · "It reports the number of feedback submissions, the average ..."<br>[3] noise · fix-24 (S06-P2, S06-P3) · 0.654 · "A full squad of eight therefore fits every venue ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 1.20 s: embed 54 ms + search 1.9 ms + generate 1.14 s | Context had every fact. Answer left out 'only totals' although the context had it. 1 of 3 chunks is noise. |
| Medium (bge-base-en-v1.5) | Overlapping | Q5 | [1] relevant · ove-22 (S09-P1, S09-P2) · 0.696 · "After a meetup you can leave private feedback about ..."<br>[2] noise · ove-11 (S05-P2, S05-P3) · 0.662 · "For every student in a match, QuadConnect records a ..."<br>[3] noise · ove-15 (S06-P3, S06-P4) · 0.656 · "When you arrive, you check in with your match's ..." | Partial: 1/2 facts; 1/3 chunks relevant | 5.5/10: 1/2 facts stated | 0.69 s: embed 59 ms + search 2.3 ms + generate 0.62 s | Context missed 'only totals' (its best chunk ranked 4). 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Hybrid | Q5 | [1] relevant · hyb-34 (S09-P1) · 0.733 · "After a meetup you can leave private feedback about ..."<br>[2] relevant · hyb-48 (S13-P5) · 0.679 · "Who can see my feedback and my notes? Nobody ..."<br>[3] noise · hyb-23 (S06-P3) · 0.656 · "When you arrive, you check in with your match's ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.67 s: embed 63 ms + search 2.3 ms + generate 0.61 s | Context had every fact. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Fixed | Q5 | [1] relevant · fix-36 (S09-P1, S09-P2) · 0.790 · "After a meetup you can leave private feedback about ..."<br>[2] relevant · fix-38 (S09-P3) · 0.719 · "It reports the number of feedback submissions, the average ..."<br>[3] noise · fix-24 (S06-P2, S06-P3) · 0.699 · "A full squad of eight therefore fits every venue ..." | Good: 2/2 facts; 2/3 chunks relevant | 5.5/10: 1/2 facts stated | 1.36 s: embed 212 ms + search 2.3 ms + generate 1.14 s | Context had every fact. Answer left out 'only totals' although the context had it. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Overlapping | Q5 | [1] relevant · ove-22 (S09-P1, S09-P2) · 0.789 · "After a meetup you can leave private feedback about ..."<br>[2] relevant · ove-23 (S09-P2, S09-P3) · 0.735 · "Feedback is also how a one-off meetup can turn ..."<br>[3] noise · ove-11 (S05-P2, S05-P3) · 0.719 · "For every student in a match, QuadConnect records a ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 1.11 s: embed 207 ms + search 2.3 ms + generate 0.90 s | Context had every fact. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Hybrid | Q5 | [1] relevant · hyb-34 (S09-P1) · 0.798 · "After a meetup you can leave private feedback about ..."<br>[2] relevant · hyb-48 (S13-P5) · 0.731 · "Who can see my feedback and my notes? Nobody ..."<br>[3] noise · hyb-35 (S09-P2) · 0.724 · "Feedback is also how a one-off meetup can turn ..." | Good: 2/2 facts; 2/3 chunks relevant | 10/10: 2/2 facts stated | 0.87 s: embed 214 ms + search 2.3 ms + generate 0.65 s | Context had every fact. 1 of 3 chunks is noise. |

<details>
<summary>The nine answers to Q5</summary>

* **Small, Fixed** (5.5/10: 1/2 facts stated): No. The rating and private note you leave after a meetup are not shown to the other students in your match. They remain confidential to you and are only used by QuadConnect to improve future matches. This is described in the handbook’s feedback section. [1]

* **Small, Overlapping** (10/10: 2/2 facts stated): No. Your rating and private note are kept confidential and are never shown to the other students in your match. Only the overall feedback summary is visible to everyone, but individual ratings and notes remain private. [1] [3]

* **Small, Hybrid** (10/10: 2/2 facts stated): No. Your rating, ticks, and private note are kept private and are not shown to anyone else in your match. Only aggregate totals and averages are visible on the Feedback summary page, and individual feedback is never displayed in the app. [2]

* **Medium, Fixed** (5.5/10: 1/2 facts stated): No. Your rating and private note are only visible to you and are never shown to the other students in your match. The handbook states that “individual ratings and private notes are never displayed” and that the note is “never shown to the other students in your match”【1】【2】.

* **Medium, Overlapping** (5.5/10: 1/2 facts stated): No. Your rating and private note are kept confidential; they are never shown to the other students in your match. The handbook states that the note and rating are private and not displayed to anyone else.

* **Medium, Hybrid** (10/10: 2/2 facts stated): No. Your rating, ticks, and private note are kept private and are not shown to anyone else in your match. Only aggregate totals and averages appear on the Feedback summary page, not individual details. [2]

* **Large, Fixed** (5.5/10: 1/2 facts stated): No. Your rating and private note are only visible to you and are never shown to the other students in your match. The handbook states that “individual ratings and private notes are never displayed” and that the note is “never shown to the other students in your match”【1】【2】.

* **Large, Overlapping** (10/10: 2/2 facts stated): No. Your rating and private note are kept confidential and are never shown to the other students in your match. Only aggregate statistics appear on the Feedback summary page, not individual responses. [1]

* **Large, Hybrid** (10/10: 2/2 facts stated): No. Your rating, ticks, and private note are kept private and are not shown to anyone else in your match. Only aggregate totals and averages are visible on the Feedback summary page, and individual feedback is never displayed in the app. [2]

</details>

#### Q6: Can the AI that checks venue suggestions approve my venue on its own?

*A safety rule, stated in two sections. Evidence in: S07-P1, S07-P3, S07-P4, S13-P3, S13-P4.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q6 | [1] relevant · fix-49 (S13-P4, S13-P5) · 0.799 · "Ask in plain English uses a language model on ..."<br>[2] relevant · fix-29 (S07-P3, S07-P4) · 0.776 · "The venue's name, address and meeting note go to ..."<br>[3] relevant · fix-48 (S13-P3, S13-P4) · 0.760 · "Every QuadConnect meetup is scheduled at an approved campus ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 1.00 s: embed 24 ms + search 2.4 ms + generate 0.98 s | Context had every fact. |
| Small (bge-small-en-v1.5) | Overlapping | Q6 | [1] relevant · ove-31 (S13-P4, S13-P5) · 0.795 · "Does an AI decide anything about me? QuadConnect uses ..."<br>[2] relevant · ove-17 (S07-P2, S07-P3) · 0.784 · "The form checks your suggestion before it is saved. ..."<br>[3] relevant · ove-18 (S07-P3, S07-P4) · 0.780 · "When you send a suggestion, QuadConnect also runs an ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 1.35 s: embed 23 ms + search 2.4 ms + generate 1.32 s | Context had every fact. |
| Small (bge-small-en-v1.5) | Hybrid | Q6 | [1] relevant · hyb-47 (S13-P4) · 0.804 · "Does an AI decide anything about me? QuadConnect uses ..."<br>[2] relevant · hyb-29 (S07-P4) · 0.792 · "A suggestion that tries to give the AI instructions ..."<br>[3] relevant · hyb-27 (S07-P3) · 0.786 · "When you send a suggestion, QuadConnect also runs an ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 0.90 s: embed 25 ms + search 2.4 ms + generate 0.88 s | Context had every fact. |
| Medium (bge-base-en-v1.5) | Fixed | Q6 | [1] relevant · fix-49 (S13-P4, S13-P5) · 0.739 · "Ask in plain English uses a language model on ..."<br>[2] relevant · fix-29 (S07-P3, S07-P4) · 0.702 · "The venue's name, address and meeting note go to ..."<br>[3] relevant · fix-48 (S13-P3, S13-P4) · 0.699 · "Every QuadConnect meetup is scheduled at an approved campus ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 1.04 s: embed 59 ms + search 2.4 ms + generate 0.98 s | Context had every fact. |
| Medium (bge-base-en-v1.5) | Overlapping | Q6 | [1] relevant · ove-31 (S13-P4, S13-P5) · 0.725 · "Does an AI decide anything about me? QuadConnect uses ..."<br>[2] relevant · ove-18 (S07-P3, S07-P4) · 0.699 · "When you send a suggestion, QuadConnect also runs an ..."<br>[3] relevant · ove-30 (S13-P3, S13-P4) · 0.688 · "Can we meet at a place that is not ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 0.72 s: embed 59 ms + search 2.3 ms + generate 0.66 s | Context had every fact. |
| Medium (bge-base-en-v1.5) | Hybrid | Q6 | [1] relevant · hyb-47 (S13-P4) · 0.736 · "Does an AI decide anything about me? QuadConnect uses ..."<br>[2] relevant · hyb-29 (S07-P4) · 0.724 · "A suggestion that tries to give the AI instructions ..."<br>[3] relevant · hyb-27 (S07-P3) · 0.696 · "When you send a suggestion, QuadConnect also runs an ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 0.94 s: embed 59 ms + search 2.4 ms + generate 0.88 s | Context had every fact. |
| Large (bge-large-en-v1.5) | Fixed | Q6 | [1] relevant · fix-29 (S07-P3, S07-P4) · 0.755 · "The venue's name, address and meeting note go to ..."<br>[2] relevant · fix-49 (S13-P4, S13-P5) · 0.724 · "Ask in plain English uses a language model on ..."<br>[3] relevant · fix-48 (S13-P3, S13-P4) · 0.703 · "Every QuadConnect meetup is scheduled at an approved campus ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 1.61 s: embed 211 ms + search 2.4 ms + generate 1.40 s | Context had every fact. |
| Large (bge-large-en-v1.5) | Overlapping | Q6 | [1] relevant · ove-18 (S07-P3, S07-P4) · 0.745 · "When you send a suggestion, QuadConnect also runs an ..."<br>[2] relevant · ove-31 (S13-P4, S13-P5) · 0.735 · "Does an AI decide anything about me? QuadConnect uses ..."<br>[3] relevant · ove-30 (S13-P3, S13-P4) · 0.734 · "Can we meet at a place that is not ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 2.41 s: embed 210 ms + search 2.4 ms + generate 2.20 s | Context had every fact. |
| Large (bge-large-en-v1.5) | Hybrid | Q6 | [1] relevant · hyb-29 (S07-P4) · 0.758 · "A suggestion that tries to give the AI instructions ..."<br>[2] relevant · hyb-47 (S13-P4) · 0.746 · "Does an AI decide anything about me? QuadConnect uses ..."<br>[3] relevant · hyb-27 (S07-P3) · 0.745 · "When you send a suggestion, QuadConnect also runs an ..." | Good: 2/2 facts; 3/3 chunks relevant | 10/10: 2/2 facts stated | 0.94 s: embed 226 ms + search 2.3 ms + generate 0.71 s | Context had every fact. |

<details>
<summary>The nine answers to Q6</summary>

* **Small, Fixed** (10/10: 2/2 facts stated): No. The AI only gives advice; it never approves a venue on its own. The check can flag problems and suggest whether a place looks suitable, but staff must approve it before it can be used for a meetup【2】【3】.

* **Small, Overlapping** (10/10: 2/2 facts stated): No. The AI that checks venue suggestions only gives advice and flags; it never approves a venue on its own. The staff member reviews the AI’s advice and makes the final decision【2】【3】.

* **Small, Hybrid** (10/10: 2/2 facts stated): No. The AI that checks venue suggestions only gives advice and flags; it never approves a venue on its own. The staff member reviews the AI’s recommendation and makes the final decision【1】【3】.

* **Medium, Fixed** (10/10: 2/2 facts stated): No. The AI only gives advice; it never approves a venue on its own. The check can flag problems and suggest whether a place looks suitable, but staff must approve it before it can be used for a meetup【2】【3】.

* **Medium, Overlapping** (10/10: 2/2 facts stated): No. The AI only gives advice and flags; it never approves a venue by itself. The final decision is made by a staff member who reviews the AI’s recommendation and any flags before approving the suggestion. [2] [3]

* **Medium, Hybrid** (10/10: 2/2 facts stated): No. The AI that checks venue suggestions only gives advice and flags; it never approves a venue on its own. The staff member reviews the AI’s recommendation and makes the final decision【1】【3】.

* **Large, Fixed** (10/10: 2/2 facts stated): No. The AI that checks venue suggestions only gives advice to staff; it never approves a venue on its own. The staff make the final decision after reviewing the AI’s recommendation. This is stated in the handbook excerpts [1] and [2].

* **Large, Overlapping** (10/10: 2/2 facts stated): No. The AI only gives advice and flags; it never approves a venue by itself. The final decision is made by a staff member who reviews the AI’s recommendation and any flags before approving the location. [1] [2]

* **Large, Hybrid** (10/10: 2/2 facts stated): No. The AI that checks venue suggestions only gives advice and flags; it never approves a venue by itself. The staff member reviews the AI’s recommendation before deciding on the venue【3】【2】.

</details>

#### Q7: Does QuadConnect sell my data or share it with other companies?

*Several facts in one answer. Evidence in: S07-P4, S11-P2, S12-P2.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q7 | [1] noise · fix-43 (S11-P3) · 0.705 · "To stop QuadConnect from using your Google account, remove ..."<br>[2] noise · fix-06 (S02-P1, S02-P2) · 0.701 · "The only pages open to everyone are the landing ..."<br>[3] relevant · fix-41 (S11-P1, S11-P2) · 0.692 · "QuadConnect keeps only what it needs. For your account ..." | Partial: 1/3 facts; 1/3 chunks relevant | 4/10: 1/3 facts stated | 0.87 s: embed 26 ms + search 2.5 ms + generate 0.85 s | Context missed 'only counts public' (its best chunk ranked 8), 'outside services' (its best chunk ranked 8). 2 of 3 chunks are noise. |
| Small (bge-small-en-v1.5) | Overlapping | Q7 | [1] relevant · ove-26 (S11-P2, S11-P3) · 0.712 · "Nothing about you is sold or shared. QuadConnect's one ..."<br>[2] relevant · ove-25 (S11-P1, S11-P2) · 0.693 · "QuadConnect keeps only what it needs. For your account ..."<br>[3] noise · ove-04 (S02-P2, S02-P3) · 0.669 · "When you continue with Google, Google sends QuadConnect four ..." | Good: 3/3 facts; 2/3 chunks relevant | 7/10: 2/3 facts stated | 0.87 s: embed 25 ms + search 2.2 ms + generate 0.84 s | Context had every fact. Answer left out 'outside services' although the context had it. 1 of 3 chunks is noise. |
| Small (bge-small-en-v1.5) | Hybrid | Q7 | [1] noise · hyb-39 (S11-P1) · 0.704 · "QuadConnect keeps only what it needs. For your account ..."<br>[2] noise · hyb-41 (S11-P3) · 0.699 · "You stay in control of your data. To delete ..."<br>[3] relevant · hyb-40 (S11-P2) · 0.682 · "Nothing about you is sold or shared. QuadConnect's one ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 1.59 s: embed 26 ms + search 2.4 ms + generate 1.56 s | Context had every fact. Answer left out 'outside services' although the context had it. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Fixed | Q7 | [1] noise · fix-06 (S02-P1, S02-P2) · 0.689 · "The only pages open to everyone are the landing ..."<br>[2] noise · fix-43 (S11-P3) · 0.655 · "To stop QuadConnect from using your Google account, remove ..."<br>[3] relevant · fix-42 (S11-P2, S11-P3) · 0.655 · "QuadConnect's one public API, the interest summary at /api/summary/, ..." | Partial: 2/3 facts; 1/3 chunks relevant | 1/10: 0/3 facts stated | 1.67 s: embed 60 ms + search 2.4 ms + generate 1.61 s | Context missed 'not sold' (its best chunk ranked 5). Answer left out 'only counts public', 'outside services' although the context had them. Answer said the handbook does not cover it. 2 of 3 chunks are noise. |
| Medium (bge-base-en-v1.5) | Overlapping | Q7 | [1] relevant · ove-26 (S11-P2, S11-P3) · 0.716 · "Nothing about you is sold or shared. QuadConnect's one ..."<br>[2] noise · ove-04 (S02-P2, S02-P3) · 0.678 · "When you continue with Google, Google sends QuadConnect four ..."<br>[3] relevant · ove-25 (S11-P1, S11-P2) · 0.665 · "QuadConnect keeps only what it needs. For your account ..." | Good: 3/3 facts; 2/3 chunks relevant | 7/10: 2/3 facts stated | 0.78 s: embed 59 ms + search 2.3 ms + generate 0.72 s | Context had every fact. Answer left out 'outside services' although the context had it. 1 of 3 chunks is noise. |
| Medium (bge-base-en-v1.5) | Hybrid | Q7 | [1] relevant · hyb-40 (S11-P2) · 0.711 · "Nothing about you is sold or shared. QuadConnect's one ..."<br>[2] noise · hyb-41 (S11-P3) · 0.675 · "You stay in control of your data. To delete ..."<br>[3] noise · hyb-39 (S11-P1) · 0.668 · "QuadConnect keeps only what it needs. For your account ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 0.64 s: embed 56 ms + search 2.4 ms + generate 0.58 s | Context had every fact. Answer left out 'outside services' although the context had it. 2 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Fixed | Q7 | [1] noise · fix-06 (S02-P1, S02-P2) · 0.738 · "The only pages open to everyone are the landing ..."<br>[2] noise · fix-43 (S11-P3) · 0.715 · "To stop QuadConnect from using your Google account, remove ..."<br>[3] noise · fix-05 (S02-P1) · 0.706 · "You can create a QuadConnect account in two ways. ..." | Poor: 0/3 facts; 0/3 chunks relevant | 1/10: 0/3 facts stated | 2.81 s: embed 213 ms + search 2.8 ms + generate 2.60 s | Context missed 'not sold' (its best chunk ranked 9), 'only counts public' (its best chunk ranked 6), 'outside services' (its best chunk ranked 6). Answer said the handbook does not cover it. 3 of 3 chunks are noise. |
| Large (bge-large-en-v1.5) | Overlapping | Q7 | [1] relevant · ove-26 (S11-P2, S11-P3) · 0.775 · "Nothing about you is sold or shared. QuadConnect's one ..."<br>[2] noise · ove-04 (S02-P2, S02-P3) · 0.717 · "When you continue with Google, Google sends QuadConnect four ..."<br>[3] relevant · ove-27 (S12-P1, S12-P2) · 0.705 · "QuadConnect has a few pages that describe the community ..." | Good: 3/3 facts; 2/3 chunks relevant | 7/10: 2/3 facts stated | 0.98 s: embed 219 ms + search 2.3 ms + generate 0.76 s | Context had every fact. Answer left out 'outside services' although the context had it. 1 of 3 chunks is noise. |
| Large (bge-large-en-v1.5) | Hybrid | Q7 | [1] noise · hyb-41 (S11-P3) · 0.746 · "You stay in control of your data. To delete ..."<br>[2] relevant · hyb-40 (S11-P2) · 0.726 · "Nothing about you is sold or shared. QuadConnect's one ..."<br>[3] noise · hyb-05 (S02-P2) · 0.708 · "When you continue with Google, Google sends QuadConnect four ..." | Good: 3/3 facts; 1/3 chunks relevant | 7/10: 2/3 facts stated | 1.29 s: embed 213 ms + search 2.5 ms + generate 1.08 s | Context had every fact. Answer left out 'outside services' although the context had it. 2 of 3 chunks are noise. |

<details>
<summary>The nine answers to Q7</summary>

* **Small, Fixed** (4/10: 1/3 facts stated): The handbook states that QuadConnect does not sell or share your data with other companies. It keeps only the information it needs for your account and matching, and nothing about you is sold or shared. [3]

* **Small, Overlapping** (7/10: 2/3 facts stated): QuadConnect does not sell or share your personal data. The handbook states that “Nothing about you is sold or shared” and that the public API only publishes aggregated interest counts without names, NetIDs or email addresses [1][2].

* **Small, Hybrid** (7/10: 2/3 facts stated): QuadConnect does not sell or share your personal data. The handbook states that “Nothing about you is sold or shared” and that the public API only publishes aggregated interest counts without names, NetIDs, or email addresses.

* **Medium, Fixed** (1/10: 0/3 facts stated): The handbook excerpts do not mention QuadConnect selling or sharing your data with other companies.

* **Medium, Overlapping** (7/10: 2/3 facts stated): QuadConnect does not sell or share your personal data. The handbook states that “Nothing about you is sold or shared” and that the public API only publishes aggregated interest counts without names, NetIDs or email addresses. All other data is kept only as needed for your account and profile, and no third‑party sharing is described.

* **Medium, Hybrid** (7/10: 2/3 facts stated): QuadConnect does not sell or share your personal data. The handbook states that nothing about you is sold or shared, and the public API only publishes aggregated interest counts without names, NetIDs, or email addresses [1].

* **Large, Fixed** (1/10: 0/3 facts stated): The handbook excerpts you provided do not contain any information about QuadConnect selling or sharing your data with other companies.

* **Large, Overlapping** (7/10: 2/3 facts stated): QuadConnect does not sell or share your personal data. The handbook states that nothing about you is sold or shared, and all public data is aggregated counts without names, NetIDs or email addresses [1].

* **Large, Hybrid** (7/10: 2/3 facts stated): QuadConnect does not sell or share your personal data with other companies. The handbook states that “Nothing about you is sold or shared” and that the public API only publishes aggregated interest counts without names, NetIDs, or email addresses. No other sharing of personal data is described in the handbook.

</details>

#### Q8: Do I have to pay to use QuadConnect?

*Not in the handbook: the right answer says so. Evidence in: -.*

| Embedding Model | Chunking Strategy | Query | Retrieved chunks | Retrieved Context Quality | Answer Quality | Latency | Notes |
|---|---|---|---|---|---|---|---|
| Small (bge-small-en-v1.5) | Fixed | Q8 | [1] noise · fix-05 (S02-P1) · 0.738 · "You can create a QuadConnect account in two ways. ..."<br>[2] noise · fix-01 (S01-P1) · 0.730 · "QuadConnect is a social app for students at the ..."<br>[3] noise · fix-34 (S08-P3, S08-P4) · 0.726 · "You type a request such as students who like ..." | n/a: nothing to find (top score 0.738) | 10/10: declined correctly | 0.92 s: embed 25 ms + search 2.4 ms + generate 0.89 s | Declined correctly: the handbook does not say. |
| Small (bge-small-en-v1.5) | Overlapping | Q8 | [1] noise · ove-01 (S01-P1, S01-P2) · 0.722 · "QuadConnect is a social app for students at the ..."<br>[2] noise · ove-29 (S13-P2, S13-P3) · 0.722 · "What happens if my free times do not overlap ..."<br>[3] noise · ove-02 (S01-P2, S01-P3) · 0.720 · "QuadConnect is a closed community for verified Illinois students. ..." | n/a: nothing to find (top score 0.722) | 10/10: declined correctly | 0.66 s: embed 24 ms + search 2.4 ms + generate 0.63 s | Declined correctly: the handbook does not say. |
| Small (bge-small-en-v1.5) | Hybrid | Q8 | [1] noise · hyb-02 (S01-P2) · 0.734 · "QuadConnect is a closed community for verified Illinois students. ..."<br>[2] noise · hyb-01 (S01-P1) · 0.731 · "QuadConnect is a social app for students at the ..."<br>[3] noise · hyb-40 (S11-P2) · 0.720 · "Nothing about you is sold or shared. QuadConnect's one ..." | n/a: nothing to find (top score 0.734) | 10/10: declined correctly | 0.88 s: embed 24 ms + search 2.3 ms + generate 0.86 s | Declined correctly: the handbook does not say. |
| Medium (bge-base-en-v1.5) | Fixed | Q8 | [1] noise · fix-05 (S02-P1) · 0.721 · "You can create a QuadConnect account in two ways. ..."<br>[2] noise · fix-01 (S01-P1) · 0.689 · "QuadConnect is a social app for students at the ..."<br>[3] noise · fix-06 (S02-P1, S02-P2) · 0.686 · "The only pages open to everyone are the landing ..." | n/a: nothing to find (top score 0.721) | 10/10: declined correctly | 0.67 s: embed 56 ms + search 2.3 ms + generate 0.62 s | Declined correctly: the handbook does not say. |
| Medium (bge-base-en-v1.5) | Overlapping | Q8 | [1] noise · ove-03 (S02-P1, S02-P2) · 0.712 · "You can create a QuadConnect account in two ways. ..."<br>[2] noise · ove-04 (S02-P2, S02-P3) · 0.692 · "When you continue with Google, Google sends QuadConnect four ..."<br>[3] noise · ove-01 (S01-P1, S01-P2) · 0.674 · "QuadConnect is a social app for students at the ..." | n/a: nothing to find (top score 0.712) | 10/10: declined correctly | 1.06 s: embed 55 ms + search 3.3 ms + generate 1.00 s | Declined correctly: the handbook does not say. |
| Medium (bge-base-en-v1.5) | Hybrid | Q8 | [1] noise · hyb-04 (S02-P1) · 0.711 · "You can create a QuadConnect account in two ways. ..."<br>[2] noise · hyb-01 (S01-P1) · 0.693 · "QuadConnect is a social app for students at the ..."<br>[3] noise · hyb-05 (S02-P2) · 0.692 · "When you continue with Google, Google sends QuadConnect four ..." | n/a: nothing to find (top score 0.711) | 10/10: declined correctly | 1.33 s: embed 57 ms + search 2.1 ms + generate 1.27 s | Declined correctly: the handbook does not say. |
| Large (bge-large-en-v1.5) | Fixed | Q8 | [1] noise · fix-05 (S02-P1) · 0.777 · "You can create a QuadConnect account in two ways. ..."<br>[2] noise · fix-06 (S02-P1, S02-P2) · 0.733 · "The only pages open to everyone are the landing ..."<br>[3] noise · fix-03 (S01-P2, S01-P3) · 0.726 · "The current prototype signs you in with a username ..." | n/a: nothing to find (top score 0.777) | 10/10: declined correctly | 2.42 s: embed 208 ms + search 2.4 ms + generate 2.21 s | Declined correctly: the handbook does not say. |
| Large (bge-large-en-v1.5) | Overlapping | Q8 | [1] noise · ove-03 (S02-P1, S02-P2) · 0.758 · "You can create a QuadConnect account in two ways. ..."<br>[2] noise · ove-04 (S02-P2, S02-P3) · 0.742 · "When you continue with Google, Google sends QuadConnect four ..."<br>[3] noise · ove-26 (S11-P2, S11-P3) · 0.734 · "Nothing about you is sold or shared. QuadConnect's one ..." | n/a: nothing to find (top score 0.758) | 10/10: declined correctly | 1.04 s: embed 205 ms + search 2.3 ms + generate 0.83 s | Declined correctly: the handbook does not say. |
| Large (bge-large-en-v1.5) | Hybrid | Q8 | [1] noise · hyb-04 (S02-P1) · 0.771 · "You can create a QuadConnect account in two ways. ..."<br>[2] noise · hyb-06 (S02-P3) · 0.738 · "QuadConnect cannot send email yet, so it cannot send ..."<br>[3] noise · hyb-05 (S02-P2) · 0.737 · "When you continue with Google, Google sends QuadConnect four ..." | n/a: nothing to find (top score 0.771) | 10/10: declined correctly | 2.50 s: embed 211 ms + search 2.3 ms + generate 2.29 s | Declined correctly: the handbook does not say. |

<details>
<summary>The nine answers to Q8</summary>

* **Small, Fixed** (10/10: declined correctly): The handbook excerpts you provided do not mention any payment or subscription requirements for using QuadConnect.

* **Small, Overlapping** (10/10: declined correctly): The handbook does not mention any payment or subscription requirements for using QuadConnect.

* **Small, Hybrid** (10/10: declined correctly): The handbook excerpts do not mention any payment or subscription requirements for using QuadConnect.

* **Medium, Fixed** (10/10: declined correctly): The handbook excerpts do not mention any fees or payment requirements for using QuadConnect.

* **Medium, Overlapping** (10/10: declined correctly): The handbook excerpts do not mention any fees or payment requirements for using QuadConnect.

* **Medium, Hybrid** (10/10: declined correctly): The handbook excerpts do not mention any payment or subscription requirements for using QuadConnect.

* **Large, Fixed** (10/10: declined correctly): The handbook does not mention any payment or subscription requirements for using QuadConnect.

* **Large, Overlapping** (10/10: declined correctly): The handbook excerpts do not mention any pricing or payment requirements for using QuadConnect.

* **Large, Hybrid** (10/10: declined correctly): The handbook excerpts you provided do not mention any payment or subscription requirements for using QuadConnect.

</details>

### 2.3 Embedding models compared

The 63 runs of the seven answerable questions, grouped by embedding model. Each model's numbers pool its three
chunking strategies: 7 questions × 3 strategies = 21 runs and 54 key facts. The cost columns come from Step 1.3 (the
model's size, the time to embed a chunk, the storage for the vectors) and from the runs (the time to embed a
question). Timings are from this machine's CPU and change a little from run to run.

**Cost:**

| Model | Parameters | Dimensions | Embed a chunk | Embed a question | Vectors for 129 chunks |
|---|---|---|---|---|---|
| Small | 33 million | 384 | 50 ms | 25 ms | 194 KB |
| Medium | 109 million | 768 | 152 ms | 59 ms | 387 KB |
| Large | 335 million | 1024 | 1257 ms | 213 ms | 516 KB |

Large against small, on the run saved in the notebook: 10 times the parameters, 2.7 times the dimensions and storage, 25.0 times the time to embed a chunk and 8.7 times the time to embed a question.

**Quality** (seven answerable questions × three strategies = 21 runs and 54 key facts per model):

| Model | Facts in context | Good contexts | Relevant chunks (of 3) | Mean reciprocal rank | Facts stated | Stated, of those in context | Answer score | Q8 declined |
|---|---|---|---|---|---|---|---|---|
| Small | 49/54 (91%) | 18/21 | 1.62 | 0.77 | 80% | 88% | 8.00 | 3/3 |
| Medium | 47/54 (87%) | 17/21 | 1.57 | 0.79 | 70% | 81% | 7.39 | 3/3 |
| Large | 48/54 (89%) | 18/21 | 1.62 | 0.78 | 78% | 88% | 7.93 | 3/3 |

![Three bar charts. Left: the share of key facts in the retrieved context for the small, medium and large models
under each chunking strategy. Middle: the mean answer score for the same nine configurations. Right: the time each
model takes to embed a question.](results/embedding_models.png)

**Did the larger model always do better?** Every strategy and question, model by model:

| Strategy | Q | Facts in context (S/M/L) | First relevant rank (S/M/L) | Answer score (S/M/L) | Where the large model did worse |
|---|---|---|---|---|---|
| Fixed | Q1 | 4/1/4 | 2/2/2 | 10/3.2/10 | - |
| Fixed | Q2 | 3/3/3 | 1/1/1 | 10/10/10 | - |
| Fixed | Q3 | 2/2/2 | 1/2/2 | 10/10/10 | lower rank |
| Fixed | Q4 | 2/2/2 | 1/1/1 | 5.5/10/10 | - |
| Fixed | Q5 | 1/2/2 | 1/1/1 | 5.5/5.5/5.5 | - |
| Fixed | Q6 | 2/2/2 | 1/1/1 | 10/10/10 | - |
| Fixed | Q7 | 1/2/0 | 3/3/6 | 4/1/1 | fewer facts, lower rank, worse answer |
| Overlapping | Q1 | 4/4/4 | 1/1/1 | 10/10/10 | - |
| Overlapping | Q2 | 3/3/3 | 2/2/2 | 10/7/7 | worse answer |
| Overlapping | Q3 | 2/2/2 | 3/2/2 | 10/10/10 | - |
| Overlapping | Q4 | 2/2/2 | 1/1/1 | 5.5/5.5/5.5 | - |
| Overlapping | Q5 | 2/1/2 | 1/1/1 | 10/5.5/10 | - |
| Overlapping | Q6 | 2/2/2 | 1/1/1 | 10/10/10 | - |
| Overlapping | Q7 | 3/3/3 | 1/1/1 | 7/7/7 | - |
| Hybrid | Q1 | 4/4/4 | 2/2/1 | 10/10/10 | - |
| Hybrid | Q2 | 3/3/3 | 1/1/1 | 7/7/7 | - |
| Hybrid | Q3 | 0/0/0 | 5/5/5 | 1/1/1 | - |
| Hybrid | Q4 | 2/2/1 | 2/2/2 | 5.5/5.5/5.5 | fewer facts |
| Hybrid | Q5 | 2/2/2 | 1/1/1 | 10/10/10 | - |
| Hybrid | Q6 | 2/2/2 | 1/1/1 | 10/10/10 | - |
| Hybrid | Q7 | 3/3/3 | 3/1/2 | 7/7/7 | lower rank |

In 21 strategy-question pairs, the large model found fewer facts than a smaller model in 2, ranked the evidence lower in 3 and answered worse in 2. It beat both smaller models on facts found in 0, on rank in 1 and on the answer in 0.

**How does embedding size affect retrieval quality?** On this handbook, hardly at all, and not in the order of
size. Pooled over the three strategies, the small model put 49 of the 54 key facts into the context (91%), the large
model 48 (89%) and the medium model 47 (87%), and the first relevant chunk ranked about as high for all three (mean
reciprocal rank 0.77 to 0.79). Each gap comes from one or two questions where a needed chunk ranked just below the
top 3:

* the medium model missed Q1's seat counts with fixed chunks (the chunk holding them ranked 4th) and Q5's "only
  totals" with overlapping chunks (4th);
* the large model missed all three facts of Q7 with fixed chunks (its best evidence chunk ranked 6th) and Q4's group
  size with hybrid chunks (4th);
* the small model missed Q5's "only totals" with fixed chunks (4th).

The differences are this small because the task is easy for all three. The handbook is short (31 to 50 chunks per
strategy) and written in plain words, and each question is about a subject the handbook names. The three models
also come from one family and were trained the same way, so they mostly agree on which chunks are closest.

**How does embedding size affect answer quality?** Answers follow the context, so they barely depend on the model
either: 8.0 out of 10 for the small model, 7.9 for the large and 7.4 for the medium. Against the small model, the
medium model lost points in four runs and gained in one. Two were lost in retrieval (Q1 and Q5 above) and two by the
generator: it left out a fact that was in the context (Q2 with overlapping chunks), and for Q7 with fixed chunks it
answered that the excerpts do not cover the question, although they held two of its three facts. The gain was Q4
with fixed chunks, where the medium model's answer also named the group size. Most lost points are the generator's, not the retriever's: of the facts
that reached the context, the answers stated 88% with the small and the large model and 81% with the medium. The
generator tends to give the main point and drop a second fact, such as Q2's "QuadConnect cannot send a reset link"
or Q7's outside services. The noise around the evidence matters too. For Q2 with overlapping chunks, all three
models retrieved the same two chunks first and a different third chunk, and only the small model's answer stated all
three facts.

**Did larger embeddings always perform better?** No. In the 21 strategy-question pairs above, the large model found
fewer facts than a smaller model in 2, ranked the evidence lower in 3 and answered worse in 2. It beat both smaller
models only once, with a better rank for Q1 on hybrid chunks, and never on facts found or on the answer. It cost far
more: 10 times the small model's parameters, 2.7 times the storage per vector, about 10 times the time to embed a
chunk and several times the time to embed a question (the ratios are above; timings vary from run to run). **For a knowledge base of this size, the small model is the better choice:** it did at least as well, for a
fraction of the cost. A larger model is worth testing again when the
collection grows or the questions get harder to match, which is what Step 2.5 starts to do.

### 2.4 Chunking strategies compared

The same 63 runs, grouped by chunking strategy: each strategy pools its three models (21 runs, 54 key facts). The
cost side is how much the generator reads: words per chunk, words in the context, and prompt tokens.

**What the generator reads:**

| Strategy | Words per chunk | Context words | Noise words | Prompt tokens | Generate (median) |
|---|---|---|---|---|---|
| Fixed | 98 | 299 | 128 | 548 | 0.92 s |
| Overlapping | 222 | 679 | 286 | 992 | 0.86 s |
| Hybrid | 102 | 311 | 170 | 554 | 0.72 s |

**Quality** (seven answerable questions × three models = 21 runs and 54 key facts per strategy):

| Strategy | Facts in context | Good contexts | Relevant chunks (of 3) | Mean reciprocal rank | Facts stated | Stated, of those in context | Answer score | Q8 declined |
|---|---|---|---|---|---|---|---|---|
| Fixed | 44/54 (81%) | 16/21 | 1.67 | 0.78 | 72% | 89% | 7.68 | 3/3 |
| Overlapping | 53/54 (98%) | 20/21 | 1.76 | 0.85 | 83% | 85% | 8.43 | 3/3 |
| Hybrid | 47/54 (87%) | 17/21 | 1.38 | 0.71 | 72% | 83% | 7.21 | 3/3 |

![Three bar charts. Left: the share of key facts in the retrieved context for the fixed, overlapping and hybrid
strategies with each embedding model. Middle: the mean answer score for the same nine configurations. Right: the mean
prompt tokens per question for each strategy.](results/chunking_strategies.png)

**Per question** (facts summed over the three models, answer scores averaged):

| Q | Facts × 3 models | Facts in context: Fixed | Facts in context: Overlapping | Facts in context: Hybrid | Answer score: Fixed | Answer score: Overlapping | Answer score: Hybrid |
|---|---|---|---|---|---|---|---|
| Q1 | 12 | 9 | 12 | 12 | 7.73 | 10.00 | 10.00 |
| Q2 | 9 | 9 | 9 | 9 | 10.00 | 8.00 | 7.00 |
| Q3 | 6 | 6 | 6 | 0 | 10.00 | 10.00 | 1.00 |
| Q4 | 6 | 6 | 6 | 5 | 8.50 | 5.50 | 5.50 |
| Q5 | 6 | 5 | 5 | 6 | 5.50 | 8.50 | 10.00 |
| Q6 | 6 | 6 | 6 | 6 | 10.00 | 10.00 | 10.00 |
| Q7 | 9 | 3 | 9 | 9 | 2.00 | 7.00 | 7.00 |

Mean answer score without Q3: Fixed 7.29, Overlapping 8.17, Hybrid 8.25.

**What the generator saw for Q1** ("Our squad has eight people. Which venues have enough seats for all of us?") with the medium model; the full chunk texts are in
the notebook and in `results/evaluation.csv`:

| Strategy | Retrieved | Context | Answer | Answer quality |
|---|---|---|---|---|
| Fixed | [1] fix-20: noise<br>[2] fix-24: relevant<br>[3] fix-21: noise | Partial: 1/4 facts; 1/3 chunks relevant | All venues can accommodate a full squad of eight people except Espresso Royale, which is only suitable for Friend Connect meetups and smaller squads. [2] | 3.2/10: 1/4 facts stated |
| Overlapping | [1] ove-14: relevant<br>[2] ove-12: noise<br>[3] ove-16: noise | Good: 4/4 facts; 1/3 chunks relevant | Your squad of eight can fit at any venue that seats at least eight people. According to the venue information, the Illini Union seats twelve, the Grainger Engineering Library seats eight, and the Main Quad seats twenty, so all three of those venues can accommodate your group. Espresso Royale only seats six, so it would be too small for eight people. [1] | 10/10: 4/4 facts stated |
| Hybrid | [1] hyb-19: noise<br>[2] hyb-22: relevant<br>[3] hyb-25: noise | Good: 4/4 facts; 1/3 chunks relevant | Your squad of eight can fit in any venue that seats at least eight people. According to the venue list, the Illini Union (12 seats), Grainger Engineering Library (8 seats), and Main Quad (20 seats) all accommodate your group. Espresso Royale only seats six, so it would be too small for an eight‑person squad. | 10/10: 4/4 facts stated |

**Which chunking strategy worked better?** Overlapping paragraphs, on every measure of quality. They put 53 of the
54 key facts into the context (98%), gave 20 Good contexts out of 21, ranked the first relevant chunk highest (mean
reciprocal rank 0.85), and led to the best answers (8.4 out of 10). Hybrid chunks retrieved 47 facts (87%) and
scored 7.2; fixed-length chunks retrieved the fewest, 44 (81%), and scored 7.7.

**Why:**

* **Overlapping gives every paragraph two chances, and keeps it whole.** Apart from the first and last paragraph of
  a section, each paragraph sits in two chunks, so if one pairing ranks low, the other can still reach the top 3.
  And no paragraph is ever cut: Q1's seat counts and its conclusion, "a full squad of eight therefore fits every
  venue except Espresso Royale", always arrive together.
* **Fixed length cuts where the word count says, not where the meaning does.** The 120-word limit put those two
  sentences of Q1 into different chunks: `fix-23` holds the seat counts and `fix-24` the conclusion (table above). The medium model retrieved only the second, so its answer could say
  "all venues except Espresso Royale" but could not name a single venue, and it scored 3.2.
* **Hybrid chunks are precise, but each paragraph has only one chance, and every chunk starts with its section's
  title.** Q3, "Why didn't I get a match this week?", failed on hybrid chunks with all three models: the top 3 were
  all chunks of Section 5, *How weekly matching works*, which share the question's words (match, week), while the
  evidence ranked 5th. With fixed and overlapping chunks, Section 5 still took one or two of the top places, but
  at least one chunk holding the evidence reached the top 3 for every model. Part 3 tests whether the titles cause
  this.

**How did chunking affect retrieval relevance?** It decided whether the evidence was found at all (Q1 with fixed
chunks, Q3 with hybrid chunks), and how much noise came with it. The count of relevant chunks favours overlapping
(1.76 of 3, against 1.67 for fixed and 1.38 for hybrid), but partly by construction: a paragraph is in two
overlapping chunks and only one hybrid chunk, so when the answer is in one paragraph, as for Q1 and Q2, two of
hybrid's three chunks are noise however well it ranks. Measured in words, the trade runs the other way: an
overlapping context averages about 680 words, of which about 290 are noise, against about 310 words with 170 of noise
for hybrid and 300 with 130 for fixed length.

**How did chunking affect the final answers?** Answers followed the context. Overlapping, with the most complete
context, gave the best answers, and it was the only strategy with no Poor context. Hybrid's lower mean comes almost
entirely from Q3: without Q3, hybrid's answers average 8.25 and overlapping's 8.17, so on the other six questions
hybrid matched overlapping with prompts about 45% smaller (550 tokens against 990). Bigger chunks cost more input
tokens, but on Groq they barely changed how long an answer took (median 0.7 to 0.9 seconds for every strategy).

**In short:** overlapping chunks are the most reliable here, at almost twice the prompt size; hybrid chunks are as
good on most questions at half the size, but one wording made them miss; fixed-length chunks are the weakest,
because they ignore the handbook's structure.

### 2.5 Data scaling experiment

The same eight questions run on three datasets, each one containing the one before it:

| Dataset | What it holds | Paragraphs | Words | Overlapping chunks |
|---|---|---|---|---|
| Small | Sections 1 to 7 of the handbook: the account, the profile, availability, matching, meeting up and venues | 25 | 2,958 | 18 |
| Full | The whole handbook, as in Steps 2.1 to 2.4 | 44 | 4,875 | 31 |
| Large | The handbook plus QuadConnect's staff and developer guide, `data/staff_guide.md` | 88 | 9,430 | 64 |

**The small dataset** is the handbook as if only its first seven sections had been written. It still holds 14 of the
18 key facts. Q5's evidence and two of Q7's three facts are in the later sections, so these two questions show what a
smaller dataset does to a question it no longer covers.

**The large dataset** adds a second document of 44 paragraphs (4,555 words), written for this experiment from
QuadConnect's code in the same way as the handbook. It is about running the app rather than using it: the settings,
the admin site, how the venue check works inside, the data model, the tests and the deployment. It uses the
handbook's vocabulary (venues, matches, feedback, Google, Groq) but is not written for students, which makes it
realistic noise: text that looks related to a student's question but rarely answers it. Where a guide sentence does
state a key fact, as "Staff make the final decision" does for Q6, it counts as evidence, so a guide chunk is noise
only when it holds none of the question's facts. Those sentences were listed before the experiment ran
(`GUIDE_EVIDENCE` in the notebook).

**The setup:** overlapping chunks, the strategy that retrieved best in Step 2.4, with all three embedding models, k = 3
and the same generator. The datasets differ by whole sections, so every chunk of a smaller dataset is also a chunk of
the larger ones, with the same text. Any change in the top 3 therefore comes from chunks that were added or removed.

**Measures:** facts in the dataset and in the context, and the answer score, as in Step 2.2; noise, the number of the
three retrieved chunks that hold no evidence; and the margin, how much higher the best relevant chunk scores than the
best noise chunk. A shrinking margin means noise is closing in on the evidence, even before it pushes the evidence
out; a negative margin means a noise chunk already ranks above all of the evidence (which may still be in the top 3).
The noise measures use the five questions whose evidence is in all three datasets, Q1, Q2, Q3, Q4 and Q6, so
that lost coverage and added noise are not mixed up.

**Results by dataset and model.** "Shared" columns cover the five questions whose evidence is in all three datasets
(Q1, Q2, Q3, Q4 and Q6, 13 key facts); the margin is the best relevant chunk's score minus the best noise chunk's.

| Dataset | Model | Facts in the dataset | Facts in context | Answer score | Facts in context, shared | Noise chunks, shared | Guide chunks, shared | Margin, shared | Q8 declined | Q8 top score |
|---|---|---|---|---|---|---|---|---|---|---|
| Small | Small | 14/18 | 13/18 | 6.36 | 13/13 | 1.4 | 0.0 | 0.049 | yes | 0.722 |
| Small | Medium | 14/18 | 13/18 | 6.36 | 13/13 | 1.4 | 0.0 | 0.038 | yes | 0.713 |
| Small | Large | 14/18 | 13/18 | 6.36 | 13/13 | 1.2 | 0.0 | 0.039 | yes | 0.758 |
| Full | Small | 18/18 | 18/18 | 8.93 | 13/13 | 1.4 | 0.0 | 0.035 | yes | 0.722 |
| Full | Medium | 18/18 | 17/18 | 7.86 | 13/13 | 1.2 | 0.0 | 0.031 | yes | 0.713 |
| Full | Large | 18/18 | 18/18 | 8.50 | 13/13 | 1.2 | 0.0 | 0.037 | yes | 0.758 |
| Large | Small | 18/18 | 18/18 | 8.50 | 13/13 | 1.2 | 0.2 | 0.017 | yes | 0.722 |
| Large | Medium | 18/18 | 17/18 | 8.29 | 13/13 | 1.0 | 0.2 | 0.012 | yes | 0.713 |
| Large | Large | 18/18 | 18/18 | 8.50 | 13/13 | 1.0 | 0.4 | 0.011 | yes | 0.758 |

![Three line charts over the small, full and large datasets, one line per embedding model. Left: the share of key
facts in the context. Middle: the margin of the evidence over the nearest noise chunk, which falls as the dataset
grows. Right: the mean answer score.](results/dataset_size.png)

**Per question** (S/M/L = small, medium and large embedding model):

| Q | Dataset | Facts in the dataset | Facts in context (S/M/L) | Noise chunks (S/M/L) | Guide chunks (S/M/L) | Margin (S/M/L) | Answer score (S/M/L) |
|---|---|---|---|---|---|---|---|
| Q1 | Small | 4/4 | 4/4/4 | 2/2/1 | 0/0/0 | 0.045/0.003/0.045 | 10/10/10 |
| Q1 | Full | 4/4 | 4/4/4 | 2/2/1 | 0/0/0 | 0.045/0.003/0.045 | 10/10/10 |
| Q1 | Large | 4/4 | 4/4/4 | 2/2/1 | 0/0/0 | 0.045/0.003/0.045 | 10/10/10 |
| Q2 | Small | 3/3 | 3/3/3 | 2/2/2 | 0/0/0 | -0.007/-0.018/-0.022 | 7/7/7 |
| Q2 | Full | 3/3 | 3/3/3 | 2/2/2 | 0/0/0 | -0.007/-0.018/-0.022 | 10/7/7 |
| Q2 | Large | 3/3 | 3/3/3 | 1/1/1 | 1/1/1 | -0.007/-0.008/-0.022 | 7/10/7 |
| Q3 | Small | 2/2 | 2/2/2 | 2/2/2 | 0/0/0 | -0.028/-0.026/-0.058 | 10/5.5/10 |
| Q3 | Full | 2/2 | 2/2/2 | 2/1/2 | 0/0/0 | -0.022/-0.008/-0.032 | 10/10/10 |
| Q3 | Large | 2/2 | 2/2/2 | 2/1/2 | 0/0/0 | -0.022/-0.008/-0.032 | 10/10/10 |
| Q4 | Small | 2/2 | 2/2/2 | 1/1/1 | 0/0/0 | 0.062/0.053/0.067 | 5.5/10/5.5 |
| Q4 | Full | 2/2 | 2/2/2 | 1/1/1 | 0/0/0 | 0.023/0.023/0.030 | 5.5/5.5/5.5 |
| Q4 | Large | 2/2 | 2/2/2 | 1/1/1 | 0/0/0 | 0.023/0.023/0.030 | 5.5/5.5/5.5 |
| Q5 | Small | 0/2 | 0/0/0 | 3/3/3 | 0/0/0 | -/-/- | 1/1/1 |
| Q5 | Full | 2/2 | 2/1/2 | 1/2/1 | 0/0/0 | 0.056/0.034/0.070 | 10/5.5/10 |
| Q5 | Large | 2/2 | 2/1/2 | 1/2/0 | 0/0/1 | 0.056/0.034/0.070 | 10/5.5/10 |
| Q6 | Small | 2/2 | 2/2/2 | 0/0/0 | 0/0/0 | 0.173/0.181/0.164 | 10/10/10 |
| Q6 | Full | 2/2 | 2/2/2 | 0/0/0 | 0/0/0 | 0.136/0.158/0.164 | 10/10/10 |
| Q6 | Large | 2/2 | 2/2/2 | 0/0/0 | 0/0/1 | 0.047/0.051/0.035 | 10/10/10 |
| Q7 | Small | 1/3 | 0/0/0 | 3/3/3 | 0/0/0 | -0.102/-0.122/-0.153 | 1/1/1 |
| Q7 | Full | 3/3 | 3/3/3 | 1/1/1 | 0/0/0 | 0.043/0.038/0.057 | 7/7/7 |
| Q7 | Large | 3/3 | 3/3/3 | 1/1/1 | 0/0/0 | 0.043/0.038/0.057 | 7/7/7 |
| Q8 | Small | - | - | 3/3/3 | 0/0/0 | -/-/- | 10/10/10 |
| Q8 | Full | - | - | 3/3/3 | 0/0/0 | -/-/- | 10/10/10 |
| Q8 | Large | - | - | 3/3/3 | 0/0/0 | -/-/- | 10/10/10 |

**How does dataset size affect retrieval quality?**

* **A smaller dataset loses coverage, not precision.** The small dataset holds only 14 of the 18 key facts, so every
  model's context held 13, against 17 or 18 on the full handbook, and the answer score fell from 7.9–8.9 to 6.4. All
  of that loss is coverage. On the five questions whose evidence it still holds, every model retrieved all 13 of
  their facts, exactly as on the full handbook. For Q5 and Q7, which lost all or most of their evidence, all six runs
  answered that the handbook does not cover the question rather than guessing: the system lost answers but stayed
  honest.
* **A larger dataset kept the same facts in the context.** On the large dataset the facts in the context did not
  change (18, 17 and 18 of 18, as on the full handbook), and the answer scores stayed within half a point (8.3 to
  8.5), moved only by different wording in Q2's answers. Five guide chunks reached a top 3 (Q2 with all three
  models, and Q5 and Q6 with the large model), and every one of them held a key fact: the guide restates a few of
  the handbook's facts for staff, so more data also brought more evidence. On the five shared questions, noise in the
  top 3 even fell slightly, from 1.2–1.4 chunks to 1.0–1.2, because those guide chunks replaced handbook noise.

**How does dataset size affect noise?**

* **Noise moves closer as the dataset grows.** On the five shared questions, the margin of the evidence over the
  nearest noise chunk averaged 0.038 to 0.049 on the small dataset, 0.031 to 0.037 on the full handbook and 0.011 to
  0.017 on the large one: doubling the data cut it to between a third and a half. Most of the drop is Q6. On the full
  handbook its evidence led every noise chunk by 0.14 to 0.16. On the large dataset the nearest noise was the guide's
  two paragraphs on how the venue check works (ove-47, G06-P1 and G06-P2), which describe the same AI check but not
  who approves a venue, and they came within 0.035 to 0.05.
* **At k = 3 the noise did not yet push evidence out,** but a margin of about 0.01 leaves little room: a slightly
  different wording, or a still larger collection, would let near-misses through. As a knowledge base grows,
  retrieval has to separate the right chunk from more and more similar text.
* **A smaller dataset has wider margins on what it covers, and nothing but noise on what it does not.** For Q5 and
  Q7 on the small dataset, all three retrieved chunks were noise, so the generator's refusal was the only safeguard.
* **A question that nothing answers is unaffected.** Q8 drew the same top score on all three datasets (0.71 to
  0.76): the guide added nothing closer to "Do I have to pay?" than the handbook had, and every run declined.

**In short:** a smaller dataset fails by missing information, and a larger one by crowding the right chunk with
near-misses. The second effect grows with scale, which is why Part 4 returns to it.

### Part 2 at a glance

| Step | What was done | Main result |
|---|---|---|
| 2.1 Test queries | 8 questions in a student's words; 18 key facts with the sentences that state them; one question the handbook does not answer | The evidence spans 17 paragraphs in 10 sections |
| 2.2 Evaluation table | 72 runs (9 configurations × 8 questions), each with its retrieved chunks, context quality, answer score, latency and notes | Best: the small model with overlapping chunks (18 of 18 facts retrieved, answers 8.9 of 10); every configuration declined Q8 |
| 2.3 Embedding models | Model size against retrieval, answers and cost | The small model did as well as the large one at a fraction of the cost: larger was not always better |
| 2.4 Chunking strategies | Fixed length, overlapping and hybrid compared | Overlapping retrieved 98% of the facts and gave the best answers; leaving out Q3, which hybrid missed, hybrid's answers averaged as high at about half the prompt size |
| 2.5 Dataset size | Small (25 paragraphs), full (44) and large (88) datasets | A smaller dataset loses coverage; a larger one kept the facts, but the evidence's lead over the nearest noise shrank to a third or a half |

---

## 3. Failures and a fix

Every failure below happened in Part 2's 72 runs; none was staged for this part. Step 3.1 counts where the key facts
were lost and shows four failures in detail. Step 3.2 tests each failure's possible causes one at a time. Step 3.3
fixes the two main causes and measures the system before and after.

### 3.1 Failure cases

A key fact can be lost in two places: in **retrieval**, when it never reaches the context, or in **generation**, when
it is in the context but the answer leaves it out. Counting every key fact of every run (18 facts × 9 configurations
= 162) shows where the system loses information.

| Strategy | Key facts | Stated | Lost in retrieval | Lost by the generator | Stated without its evidence |
|---|---|---|---|---|---|
| Fixed | 54 | 39 | 10 | 5 | 0 |
| Overlapping | 54 | 45 | 1 | 8 | 0 |
| Hybrid | 54 | 39 | 7 | 8 | 0 |
| All nine configurations | 162 | 123 | 18 | 21 | 0 |

**The facts that were lost, and where** (each fact is counted once per configuration, 9 runs):

| Q | Fact | Stated | Lost in retrieval | Lost by the generator |
|---|---|---|---|---|
| Q1 | Illini Union | 8 | 1 | 0 |
| Q1 | Grainger | 8 | 1 | 0 |
| Q1 | Main Quad | 8 | 1 | 0 |
| Q2 | no reset email | 4 | 0 | 5 |
| Q3 | shared slot needed | 6 | 3 | 0 |
| Q3 | mark more windows | 6 | 3 | 0 |
| Q4 | group size | 2 | 1 | 6 |
| Q5 | only totals | 5 | 2 | 2 |
| Q7 | not sold | 7 | 2 | 0 |
| Q7 | only counts public | 6 | 2 | 1 |
| Q7 | outside services | 0 | 2 | 7 |

**Both halves of the system lose facts.** Retrieval lost 18 of the 162 key facts, and the generator lost 21 more that
were in the context. No answer stated a key fact without its evidence, so no fact was guessed.

**Four failures, one of each kind the brief names and one more:**

| | Failure | Kind | Where it happened |
|---|---|---|---|
| F1 | Q3's evidence never reached the context, so the answer said the handbook does not explain it | Wrong chunks retrieved | Hybrid chunks, all three models |
| F2 | Q1's seat counts were missing, so the answer could not name a single venue | Incomplete context | Medium model, fixed chunks |
| F3 | Q7's answer said the handbook does not mention selling or sharing data, although the context held two of the question's three facts | Incorrect answer | Medium model, fixed chunks |
| F4 | Every answer to Q7 says that QuadConnect does not share data with other companies, and none says that Groq, Google and PythonAnywhere do receive some | Incomplete, misleading answer | All nine configurations |

#### F1: wrong chunks retrieved

*Q3, medium model, hybrid chunks:* "Why didn't I get a match this week?" Poor: 0/2 facts; 0/3 chunks relevant. Where each fact's evidence ranked: shared slot needed 5, mark more windows 5.

| Chunk | Relevance | Score | Its text begins |
|---|---|---|---|
| [1] hyb-15 | noise | 0.669 | How weekly matching works: QuadConnect works in weekly cycles. A matching week starts on a Monday, and each cycle produces a small number of scheduled meetings rather than a feed ... |
| [2] hyb-17 | noise | 0.666 | How weekly matching works: A match moves through four stages. It starts as Proposed, when it has been offered to the students in it. Each student then answers. Your answer ... |
| [3] hyb-18 | noise | 0.636 | How weekly matching works: Declining is how you are withdrawn from a meetup that other students are still planning to attend, and a student cannot be dropped from a match ... |

Answer (1/10: 0/2 facts stated): "The handbook excerpts you provided don’t explain why you might not receive a match in a given week."

The same failure with every model:

| Model | Chunk 1 | Chunk 2 | Chunk 3 | Best rank per fact | Answer quality |
|---|---|---|---|---|---|
| Small | hyb-17 | hyb-15 | hyb-18 | 5 5 | 1/10: 0/2 facts stated |
| Medium | hyb-15 | hyb-17 | hyb-18 | 5 5 | 1/10: 0/2 facts stated |
| Large | hyb-17 | hyb-15 | hyb-16 | 5 5 | 1/10: 0/2 facts stated |

#### F2: incomplete context

*Q1, medium model, fixed chunks:* "Our squad has eight people. Which venues have enough seats for all of us?" Partial: 1/4 facts; 1/3 chunks relevant. Where each fact's evidence ranked: Illini Union 4, Grainger 4, Main Quad 4, not Espresso Royale 2.

| Chunk | Relevance | Score | Its text begins |
|---|---|---|---|
| [1] fix-20 | noise | 0.667 | This matters most in a squad, where several people plan their weekend around the group. A clear decline lets the others know who is coming, while a silent no-show leaves ... |
| [2] fix-24 | relevant | 0.593 | A full squad of eight therefore fits every venue except Espresso Royale, which suits Friend Connect meetups and smaller squads. If you are not sure where to go, open the ... |
| [3] fix-21 | noise | 0.530 | Your group size preference matters here as well. A student who chose One person as their group size suits Friend Connect, while a student who chose Small group suits a ... |

Answer (3.2/10: 1/4 facts stated): "All venues can accommodate a full squad of eight people except Espresso Royale, which is only suitable for Friend Connect meetups and smaller squads. [2]"

#### F3: incorrect answer

*Q7, medium model, fixed chunks:* "Does QuadConnect sell my data or share it with other companies?" Partial: 2/3 facts; 1/3 chunks relevant. Where each fact's evidence ranked: not sold 5, only counts public 3, outside services 3.

| Chunk | Relevance | Score | Its text begins |
|---|---|---|---|
| [1] fix-06 | noise | 0.689 | The only pages open to everyone are the landing page, the privacy notice, the login and sign-up pages, and one public summary of interests. When you continue with Google, Google ... |
| [2] fix-43 | noise | 0.655 | To stop QuadConnect from using your Google account, remove it from the third-party connections in your Google account settings. The student lists that staff can download for reports leave out ... |
| [3] fix-42 | relevant | 0.655 | QuadConnect's one public API, the interest summary at /api/summary/, publishes only how many students picked each interest, never names, NetIDs or email addresses. The site is hosted on PythonAnywhere, and ... |

Answer (1/10: 0/3 facts stated): "The handbook excerpts do not mention QuadConnect selling or sharing your data with other companies."

#### F4: incomplete, misleading answer

| Model | Chunks | Outside services in context | In the answer | Answer quality | The answer begins |
|---|---|---|---|---|---|
| Small | Fixed | no | no | 4/10: 1/3 facts stated | The handbook states that QuadConnect does not sell or share your data with other companies. It ... |
| Small | Overlapping | yes | no | 7/10: 2/3 facts stated | QuadConnect does not sell or share your personal data. The handbook states that “Nothing about you ... |
| Small | Hybrid | yes | no | 7/10: 2/3 facts stated | QuadConnect does not sell or share your personal data. The handbook states that “Nothing about you ... |
| Medium | Fixed | yes | no | 1/10: 0/3 facts stated | The handbook excerpts do not mention QuadConnect selling or sharing your data with other companies. ... |
| Medium | Overlapping | yes | no | 7/10: 2/3 facts stated | QuadConnect does not sell or share your personal data. The handbook states that “Nothing about you ... |
| Medium | Hybrid | yes | no | 7/10: 2/3 facts stated | QuadConnect does not sell or share your personal data. The handbook states that nothing about you ... |
| Large | Fixed | no | no | 1/10: 0/3 facts stated | The handbook excerpts you provided do not contain any information about QuadConnect selling or sharing your ... |
| Large | Overlapping | yes | no | 7/10: 2/3 facts stated | QuadConnect does not sell or share your personal data. The handbook states that nothing about you ... |
| Large | Hybrid | yes | no | 7/10: 2/3 facts stated | QuadConnect does not sell or share your personal data with other companies. The handbook states that ... |

### 3.2 Root cause analysis

The brief asks whether each failure came from the chunking, the embedding model or the way the question was asked.
Each of these can be tested on its own: change it, keep everything else the same, and see whether the evidence comes
back. These tests change only retrieval, so they need no new answers; they measure where the evidence ranks.

* **Chunking:** the same handbook text, cut or labelled differently.
* **Embedding model:** the same chunks and question, with the other two models.
* **Query formulation:** the same chunks and model, with the question reworded but meaning the same thing.
* **Generation:** when the fact was already in the context, none of the three can be the cause; the generator is.

**F1, Q3 on hybrid chunks:** the rank (and score) of the first chunk that holds Q3's evidence; ranks 1 to 3 are
retrieved.

| Test | Small | Medium | Large |
|---|---|---|---|
| As in Part 2: titled chunks, the student's question | 5 (0.655) | 5 (0.606) | 5 (0.621) |
| Chunking: the same chunks without their section titles | 3 (0.655) | 2 (0.612) | 2 (0.629) |
| Query: 'I got no match this week. What could be the reason?' | 5 (0.669) | 5 (0.608) | 5 (0.615) |
| Query: 'Why didn't QuadConnect match me with anyone this week?' | 2 (0.774) | 3 (0.684) | 2 (0.743) |
| Query: 'Why didn't I get a match this week? Does my availability matter?' | 1 (0.756) | 1 (0.71) | 1 (0.707) |

**F2, Q1 on fixed chunks:** where the chunk with the seat counts ranks.

| Test | Small | Medium | Large |
|---|---|---|---|
| As in Part 2: the student's question | 3 (0.632) | 4 (0.526) | 2 (0.625) |
| Query: 'Which venues have at least eight seats?' | 1 (0.614) | 1 (0.521) | 1 (0.601) |
| Query: 'How many people does each venue seat?' | 2 (0.643) | 2 (0.581) | 1 (0.632) |

**F3, Q7 on fixed chunks:** where the sentence "Nothing about you is sold or shared." ranks.

| Test | Small | Medium | Large |
|---|---|---|---|
| As in Part 2: the student's question | 3 (0.692) | 5 (0.649) | 9 (0.674) |
| Query: 'Does QuadConnect sell or share my personal data?' | 3 (0.749) | 3 (0.692) | 4 (0.73) |
| The same question, overlapping chunks | 1 (0.712) | 1 (0.716) | 1 (0.775) |
| The same question, hybrid chunks | 3 (0.682) | 1 (0.711) | 2 (0.726) |

**F4, and the other facts the generator dropped:**

| Q | Fact | Runs with the fact in the context | Answers that left it out |
|---|---|---|---|
| Q2 | no reset email | 9 | 5 |
| Q4 | group size | 8 | 6 |
| Q5 | only totals | 7 | 2 |
| Q7 | only counts public | 7 | 1 |
| Q7 | outside services | 7 | 7 |

**The causes, failure by failure:**

| | Chunking | Embedding model | Query formulation | Generation |
|---|---|---|---|---|
| **F1** Q3, wrong chunks | **Yes.** Without their section titles, the same chunks put the evidence 2nd or 3rd instead of 5th. The title "How weekly matching works" in front of four Section 5 chunks made them look like the answer. | **No.** All three models ranked the evidence 5th, behind the same Section 5 chunks. | **Yes.** The question names the symptom (no match this week), and those words are Section 5's subject: a plain paraphrase, "I got no match this week. What could be the reason?", still ranks the evidence 5th. Adding the cause's word ("Does my availability matter?") puts it 1st with every model. | – |
| **F2** Q1, incomplete context | **Yes.** The 120-word window cut paragraph S06-P2 in two. The seat counts became the last sentence of `fix-23`, whose other sentences say where to wait at each venue, and the conclusion about a squad of eight opened `fix-24`. | **Partly.** Only the medium model missed it, by 0.004 (0.526 against 0.530 for the 3rd chunk); the small and large models ranked it 3rd and 2nd. | **Yes.** "Which venues have at least eight seats?" puts the seat counts 1st with every model; the student's "squad of eight people" matches chunks about squads instead. | – |
| **F3** Q7, incorrect answer | **Yes.** The window cut paragraph S11-P2 after its first sentence: "Nothing about you is sold or shared." became the last line of `fix-41`, a chunk about what QuadConnect keeps, and the rest of the paragraph opened `fix-42`. | **Yes.** That sentence ranked 3rd with the small model, 5th with the medium and 9th with the large. | **Yes.** "Other companies" matches the chunks about Google, a company that does receive data. Without it ("Does QuadConnect sell or share my personal data?"), the sentence ranks 3rd or 4th. | **Yes.** The context still held two of the three facts, but the prompt's rule "if the excerpts do not contain the answer, say that the handbook does not cover it" led the generator to refuse instead of answering the part it could. |
| **F4** Q7, incomplete answer | No | No | No | **Yes, alone.** The fact was in the context in 7 of the 9 runs, and no answer gave it. The prompt asks for at most four sentences and does not ask for exceptions, so the generator answers "no" and stops. |

**In short:** each retrieval failure had more than one cause. The chunking decided what text sat together in a
chunk, and the question's wording decided which chunks looked closest; the embedding model only tipped near-ties
(F2, F3). The generator's failures had one cause: the prompt. It lost 21 facts that were in the context, more than
retrieval lost, and the same habit shows in Q2 (the missing reset link) and Q4 (the group size). Step 3.3 fixes one
cause on each side.

### 3.3 System improvement

Two fixes, one for each half of the system:

1. **Fix 1, retrieval: change top-k from 3 to 5.** Every key fact that hybrid chunks missed in Part 2 ranked 4th or
   5th (Q3's evidence 5th with every model, Q4's group size 4th with the large model), so two more chunks should
   bring them in. The table below compares the retrieval options first, without generating answers. Removing the
   section titles (a chunking change) also brings Q3's evidence in, with no extra text, but still misses Q4's group
   size; k = 5 is the only option that puts all 54 key facts into the context, and five hybrid chunks are still less
   text than three overlapping ones. Rewording the question works too (Step 3.2), but students cannot be asked to
   word questions like the handbook: the system would have to rewrite every question, at the cost of another model
   call each.
2. **Fix 2, generation: improve the prompt.** The first try keeps every rule of the original instruction and adds
   two: give every fact from the excerpts that answers the question, including any exception, limit or setting the
   student can change; and when the excerpts answer only part of the question, answer that part and say which part
   is not covered. It also allows five sentences instead of four. Reading its answers showed a side effect (below),
   so a final version changes two phrases: only settings that "the excerpts mention", and "add nothing that they do
   not say".

**The test:** hybrid chunks with all three models and all eight questions (24 runs), in four stages: A, Part 2 as it
was; B, with fix 1; C, with fix 1 and fix 2's first try; D, with fix 1 and the final fix 2. The failing runs on fixed
chunks (F2, F3, and Q7 with the large model) go through the same four stages. Q8 stays in the test, to check that no
change makes the system guess. Every new answer was read against its score. That found one more pattern miss: Q3's
"shared slot" pattern did not accept "shares". It is corrected in Step 2.1, and it changes no Part 2 score.

**Retrieval fixes considered** (retrieval only, all three models, the seven answerable questions):

| Option | Key facts in the context (of 54) | Words in the context (mean) |
|---|---|---|
| Part 2: hybrid chunks, k = 3 | 47 | 304 |
| Chunking: hybrid chunks without their titles, k = 3 | 53 | 310 |
| Top-k: hybrid chunks, k = 4 | 48 | 405 |
| Top-k: hybrid chunks, k = 5 | 54 | 512 |
| For comparison, Part 2's best: overlapping chunks, k = 3 | 53 | 679 |

**Fix 2's system instruction, first try** (stage C):

> You are QuadConnect's help assistant. Answer the student's question using only the handbook excerpts below. Give every fact from the excerpts that answers the question, including any exception, limit or setting the student can change. If the excerpts answer only part of the question, answer that part and say which part the handbook does not cover. If they do not answer it at all, say that the handbook does not cover it, and do not guess. Keep the answer to at most five sentences, and cite the excerpts you used by their numbers, such as [1] or [2].

**Fix 2's system instruction, final** (stage D):

> You are QuadConnect's help assistant. Answer the student's question using only the handbook excerpts below. Give every fact from the excerpts that answers the question, including any exception, limit or setting the excerpts mention, and add nothing that they do not say. If the excerpts answer only part of the question, answer that part and say which part they do not cover. If they do not answer it at all, say that the handbook does not cover it, and do not guess. Keep the answer to at most five sentences, and cite the excerpts you used by their numbers, such as [1] or [2].

**Before and after**, on hybrid chunks with all three models and all eight questions (21 answerable runs, 54 key
facts, and Q8 three times per stage):

| Stage | Facts in context | Facts stated | Answer score | Q8 declined | Answers with the invented 'account settings' | Noise chunks | Prompt tokens | Generate (median) |
|---|---|---|---|---|---|---|---|---|
| A. Before (Part 2): k = 3, original prompt | 47/54 | 39/54 | 7.21 | 3/3 | 0 | 1.62 | 554 | 0.72 s |
| B. Fix 1: k = 5, original prompt | 54/54 | 44/54 | 8.29 | 3/3 | 0 | 3.24 | 820 | 1.11 s |
| C. Fix 2, first try: k = 5, new prompt (first try) | 54/54 | 47/54 | 8.79 | 3/3 | 3 | 3.24 | 866 | 0.80 s |
| D. Fix 2, final: k = 5, new prompt (final) | 54/54 | 44/54 | 8.21 | 3/3 | 2 | 3.24 | 873 | 1.00 s |

**Answer score per question**, stage by stage (A = before, B = fix 1, C = fix 2's first try, D = both fixes):

| Q | Small model: A → B → C → D | Medium model: A → B → C → D | Large model: A → B → C → D |
|---|---|---|---|
| Q1 | 10 → 10 → 10 → 10 | 10 → 10 → 10 → 10 | 10 → 10 → 10 → 10 |
| Q2 | 7 → 7 → 10 → 10 | 7 → 7 → 7 → 7 | 7 → 7 → 7 → 7 |
| Q3 | 1 → 10 → 10 → 5.5 | 1 → 5.5 → 10 → 5.5 | 1 → 10 → 5.5 → 10 |
| Q4 | 5.5 → 5.5 → 10 → 5.5 | 5.5 → 5.5 → 10 → 10 | 5.5 → 5.5 → 5.5 → 5.5 |
| Q5 | 10 → 10 → 10 → 10 | 10 → 10 → 10 → 10 | 10 → 10 → 5.5 → 5.5 |
| Q6 | 10 → 10 → 10 → 10 | 10 → 10 → 10 → 10 | 10 → 10 → 10 → 10 |
| Q7 | 7 → 7 → 7 → 7 | 7 → 7 → 10 → 7 | 7 → 7 → 7 → 7 |
| Q8 | 10 → 10 → 10 → 10 | 10 → 10 → 10 → 10 | 10 → 10 → 10 → 10 |

**The first try's side effect:** answers that tell the student to change a password in "account settings", which
the handbook never mentions:

* C, Q2, small model, hybrid chunks: "Once logged in, you can change your password in your account settings if you wish. [1] [2]"
* C, Q2, medium model, hybrid chunks: "Once you regain access, you can change your password in your account settings."
* C, Q2, large model, hybrid chunks: "Once you’re back in, you can change your password in your account settings if you wish."
* D, Q2, medium model, hybrid chunks: "Once you regain access, you can change your password in your account settings. [1] [2]"
* D, Q2, large model, hybrid chunks: "Once you’re logged in, you can change your password in your account settings. [1] [2]"

**The failures from 3.1, stage by stage:**

| Q | Model | Chunks | Facts in context, A → B | Answer score, A → B → C → D |
|---|---|---|---|---|
| Q3 | Small | Hybrid | 0 → 2 of 2 | 1 → 10 → 10 → 5.5 |
| Q3 | Medium | Hybrid | 0 → 2 of 2 | 1 → 5.5 → 10 → 5.5 |
| Q3 | Large | Hybrid | 0 → 2 of 2 | 1 → 10 → 5.5 → 10 |
| Q1 | Medium | Fixed | 1 → 4 of 4 | 3.2 → 10 → 10 → 10 |
| Q7 | Medium | Fixed | 2 → 3 of 3 | 1 → 1 → 7 → 7 |
| Q7 | Large | Fixed | 0 → 0 of 3 | 1 → 1 → 1 → 1 |
| Q7 | Small | Hybrid | 3 → 3 of 3 | 7 → 7 → 7 → 7 |
| Q7 | Medium | Hybrid | 3 → 3 of 3 | 7 → 7 → 10 → 7 |
| Q7 | Large | Hybrid | 3 → 3 of 3 | 7 → 7 → 7 → 7 |

**The four failures after the fixes:**

* **F1 at stage B** (Q3, medium model, hybrid chunks; 2 of 2 facts in context, 1 stated, score 5.5): "The handbook says that a match can only happen if you share at least one free time slot with other students. If you haven’t kept your availability up‑to‑date or you only marked a very narrow window, the system may not find anyone who can meet at that time, so no match is produced that week. In short, a lack of shared free slots is the most common reason for not getting a match. [5]"
* **F2 at stage B** (Q1, medium model, fixed chunks; 4 of 4 facts in context, 4 stated, score 10): "Your squad of eight can fit at any venue that seats at least eight people. According to the handbook, the Illini Union seats 12, the Grainger Engineering Library seats 8, and the Main Quad seats 20, so all three can accommodate your group. Espresso Royale only seats six, so it would not be large enough for eight people. [1] [4]"
* **F3 at stage B** (Q7, medium model, fixed chunks; 3 of 3 facts in context, 0 stated, score 1): "The handbook does not state that QuadConnect sells or shares your data with other companies."
* **F3 at stage D** (Q7, medium model, fixed chunks; 3 of 3 facts in context, 2 stated, score 7): "QuadConnect does not sell or share your data with other companies. The handbook states that “nothing about you is sold or shared” [5]. It also notes that data sent to external AI services is stripped of personal identifiers before use, and no other sharing is described [3]."
* **F4 at stage D** (Q7, medium model, hybrid chunks; 3 of 3 facts in context, 2 stated, score 7): "QuadConnect does not sell or share your personal data. The handbook states that “Nothing about you is sold or shared” and that the public API only publishes aggregated interest counts without names, NetIDs or email addresses [1]. No other excerpt indicates any sale or sharing of your data."

**What the fixes did.**

* **Fix 1 worked, with no side effects.** With five chunks, all 54 key facts reached the context with every model
  (47 before), and the answer score rose from 7.21 to 8.29. Three runs got better (Q3 with every model) and none got
  worse. F1 is fixed: the small and large models now answer Q3 in full (10), and the medium model gives the rule but
  not the advice to mark more windows (5.5). F2 is fixed too: on fixed chunks, the medium model now gets the seat
  counts and names every venue (3.2 → 10). The price is size: about 820 prompt tokens instead of 550, which is still
  17% less than overlapping chunks (990), with every key fact in the context against overlapping's 53.
* **Fix 2 fixed the false refusal, but it did not make answers reliably more complete.** With the original prompt,
  the medium model still refused Q7 on fixed chunks even when its five chunks held all three facts (stage B). Both
  new prompts made it answer (1 → 7), so F3's last cause was the prompt, as Step 3.2 found. The first try also stated
  three more facts (47 against 44) and raised the score to 8.79, but all three of its answers to Q2 added a step the
  handbook never mentions: "you can change your password in your account settings". The final version, which tells
  the model to add nothing the excerpts do not say, still added it in two of three runs, and it stated no more facts
  than the original prompt (44; score 8.21). Both versions also lost a fact the original prompt had kept: the large
  model's answer to Q5 dropped the totals on the Feedback summary page (10 → 5.5).
* **F4 is not fixed.** Most answers to Q7 still leave out the outside services: asking for "every exception" did not
  make the generator treat Groq, Google and PythonAnywhere as part of the answer, and some answers still say the
  handbook mentions no other sharing.
* **Q7 with the large model on fixed chunks still fails.** Its evidence ranks 6th to 9th, so five chunks are not
  enough. Step 3.2 shows the fix it would need: without the words "other companies", the evidence ranks 4th.

**What we keep: fix 1.** Hybrid chunks with k = 5 and the original prompt put every key fact into the context,
raise the answer score from 7.2 to 8.3 and add no invented claims, at about 820 prompt tokens. We would not ship
either new prompt: with this generator, wording that asks for more facts also invites facts of its own, and the
stricter wording took the gain away without removing the invention. The answers' remaining omissions need a
different kind of fix, such as a second step that checks each answer against the excerpts, which Part 4 discusses.

These results come from the same eight questions that revealed the failures. They show that the fixes work on these
failures; a real system would confirm them on new questions before relying on them.

### Part 3 at a glance

| Step | What was done | Main result |
|---|---|---|
| 3.1 Failure cases | Every key fact of the 72 runs traced; four failures shown with their chunks and answers | Retrieval lost 18 of 162 facts and the generator 21 more; the failures cover wrong chunks, incomplete context, an incorrect answer and a misleading one |
| 3.2 Root causes | Each possible cause tested alone: the chunking, the model and the question's wording, changed one at a time | Retrieval failures came from chunking and wording, with the model only tipping near-ties; the generator's failures came from the prompt |
| 3.3 Improvement | Fix 1: top-k from 3 to 5. Fix 2: the prompt, in two versions. Before and after on 24 runs and the failing ones | Fix 1 put all 54 facts in the context and raised answers from 7.2 to 8.3 with no regressions. Fix 2 cured the false refusal but invented a password step, so we keep fix 1 only |
