# QuadConnect: multi-model system design (P1-A7)

**The Connectors · Team 13 · INFO 490, Fall 2026**

This document holds the architectural reasoning behind QuadConnect's AI features. The experiments behind every
number are in [`multi_model_system.ipynb`](multi_model_system.ipynb), and every model reply is in
[`results/`](results/).

| Part | Section | Status |
|---|---|---|
| 1. Model size selection and benchmarking | [1. Which models, for which jobs](#1-which-models-for-which-jobs) | Done |
| 2. Cost comparison and infrastructure | [2. Cost at six traffic levels](#2-cost-at-six-traffic-levels) | Done |
| 3. Multi-model routing | [3. Routing strategies](#3-routing-strategies) | Done |

---

## 1. Which models, for which jobs

### What we measured

The 15 models from P1-A6, three in each size category, each answered the same **25 prompts**: five prompt types
QuadConnect needs, five realistic inputs each.

| Prompt type | QuadConnect's job |
|---|---|
| Structured extraction | Turn a search request into filters from QuadConnect's own lists |
| Classification | Approve, review or reject a suggested meeting place |
| Prediction | Read a post-meetup note: the star rating, and whether the student wants to stay connected |
| Summarization | One sentence for staff from three feedback notes, with no names |
| Text generation | Three icebreaker questions about a new match's shared interests |

Every reply was scored by the same rules in code, from 1 to 10, on accuracy against a reference answer, instruction
adherence, structure and clarity. Accuracy gates the score: a wrong answer scores 1 however neat it looks. In a hand
check of 20 random replies, the code differed from our own scores by 0.94 points on average.

Twelve models ran on our laptop's CPU (an AMD Ryzen 7 6800HS: float32 under 2B, 4-bit NF4 from 2B up), and the
three over 15B ran on Groq's API.

### Results

| Model | Category | Mean score (1–10) | Median latency | Tokens/sec |
|---|---|---|---|---|
| SmolLM2-135M | Ultra-Light | 4.51 | 2.3 s | 17.7 |
| SmolLM2-360M | Ultra-Light | 6.81 | 3.9 s | 9.1 |
| Qwen2.5-0.5B | Ultra-Light | 6.66 | 4.4 s | 8.1 |
| Qwen2.5-1.5B | Small | 7.77 | 11.6 s | 3.4 |
| Falcon3-1B | Small | 7.25 | 9.4 s | 4.2 |
| granite-3.1-2b | Small | 9.11 | 39.8 s | 0.9 |
| **Qwen2.5-3B** | Medium | **9.32** | 34.9 s | 0.8 |
| Falcon3-3B | Medium | 8.34 | 32.2 s | 0.9 |
| Phi-4-mini | Medium | 9.19 | 46.1 s | 0.6 |
| Qwen2.5-7B | Large | 9.27 | 85.9 s | 0.3 |
| Llama-3.1-Tulu-3-8B | Large | 9.19 | 89.7 s | 0.3 |
| Falcon3-10B | Large | 9.57 | 138.0 s | 0.2 |
| gpt-oss-20b | Very Large (Groq) | 9.85 | 0.50 s | 921 |
| **Qwen3.8-27B** | Very Large (Groq) | **9.96** | 0.46 s | 490 |
| gpt-oss-120b | Very Large (Groq) | 9.96 | 0.55 s | 476 |

Local latency is our CPU; hosted latency is Groq's hardware plus the network, so the two are not comparable.

**By category and prompt type (mean score):**

| Category | Extraction | Classification | Prediction | Summarization | Text generation | All |
|---|---|---|---|---|---|---|
| Ultra-Light (< 1B) | 3.75 | 3.96 | 6.04 | 7.30 | 8.91 | 5.99 |
| Small (1B–3B) | 5.33 | 7.60 | 8.32 | 8.97 | 10.00 | 8.04 |
| Medium (3B–7B) | 7.19 | 8.80 | 9.46 | 9.32 | 9.97 | 8.95 |
| Large (7B–15B) | 8.64 | 9.40 | 9.64 | 9.04 | 10.00 | 9.34 |
| Very Large (> 15B) | 9.80 | 10.00 | 9.82 | 10.00 | 10.00 | 9.92 |

### What this means for the architecture

1. **The jobs are not equally hard, so one model is the wrong unit.**
   - Icebreakers are solved from 1.5B up: 11 of the 15 models score a perfect 10.
   - Extraction needs exact values from long lists. That is where small models fail (26 of the 75 extraction
     replies used a value not on the list), and only the Very Large category clears 9.5 on it.
   - So the system should send each job to the smallest model that does it well, not every job to one model.
2. **Bigger is better on average, but not model by model.** Size and score have a rank correlation of 0.94, yet
   Qwen2.5-3B (9.32) beat three larger local models, and granite-3.1-2b beat Falcon3-3B. The choice of model inside a
   tier should come from measurement, not from parameter count.
3. **Three candidate tiers come out of Part 1.** These are the building blocks for the cost model (Part 2) and the
   routing (Part 3):

   | Tier | Model | Why |
   |---|---|---|
   | Fast local | Qwen2.5-1.5B | Answers in about 12 s on a laptop CPU; on a GPU, A6 estimated 0.4 s (an NVIDIA L4). Perfect on icebreakers, 9.2 on summaries. It is the model QuadConnect's search already runs (A6). |
   | Quality local | Qwen2.5-3B | The best local balance: 9.32, within 0.25 of the best local model at a quarter of its latency. It needs a GPU to be interactive. |
   | API | Qwen3.8-27B on Groq (gpt-oss-20b as a second provider) | 9.96 in under half a second. It costs per token, which Part 2 prices. |

   Parts 2 and 3 revise this. On an L4 the fast local tier is no faster than the quality one, so Part 3 keeps only
   Qwen2.5-3B locally. Its API tier is gpt-oss-20b (and gpt-oss-120b for feedback ratings): Qwen3.8-27B's scores at
   about a sixth of the price (section 3).

4. **Checks stay outside the models.** Larger models still broke rules:
   - 10 of the 12 local models, up to 10B, put a participant's name in a staff summary.
   - Falcon3-10B leaked a chat-template token into a reply.
   - Two Large models missed a request for staff to follow up.

   Whatever the routing, output checks stay in front of the user: the allow-list and strict schema QuadConnect's
   search already applies, and a no-names check for any summary.
5. **On our own hardware, the CPU is the bottleneck.** The 4-bit models generate under 1 token per second on this
   CPU (0.2 to 0.9), against 3 to 18 for the small full-precision models. Local hosting at scale means GPUs; Part 2
   compares that with paying per token.

---

## 2. Cost at six traffic levels

Part 2 prices QuadConnect's AI at six traffic levels, from 1,000 to 100 million daily active users, in two ways: renting
GPU machines and hosting each model ourselves, or paying per token for a comparable model on Hugging Face's Inference
Providers. The notebook's Part 2 computes every number below from Part 1's saved token counts and from prices checked
on 3 November 2026, and saves the two 90-row tables to [`results/local_hosting_costs.csv`](results/local_hosting_costs.csv)
and [`results/api_costs.csv`](results/api_costs.csv). All costs are US dollars.

### What one user costs in tokens (Steps 2.1 and 2.2)

Part 1 measured the prompt and reply tokens of all 375 requests; the table uses the mean over the 15 models. How often
a user reaches each job is our estimate, because QuadConnect has only seed data and no usage log yet.

| Job (prompt type) | Where it runs | Requests per user per day | Prompt tokens per request | Generated tokens per request | Tokens per user per day |
|---|---|---|---|---|---|
| Structured extraction | Search in plain words (`search/ask/`) | 1.000 | 478.8 | 36.6 | 515.4 |
| Text generation | Icebreakers for a match (`matches/<id>/icebreakers/`) | 0.500 | 193.8 | 51.4 | 122.6 |
| Prediction | Rating a feedback note after a meetup | 0.200 | 183.7 | 16.0 | 39.9 |
| Summarization | Staff summary of feedback (`feedback/summary/`) | 0.067 | 203.7 | 28.9 | 15.5 |
| Classification | Checking a newly suggested venue | 0.010 | 341.9 | 28.3 | 3.7 |
| **All five** |  | **1.777** |  |  | **697** (629 prompt + 68 generated) |

**Average tokens per request = 392** (354 prompt +
38 generated). A daily active user makes 1.78 requests, so
**697 tokens a day**. 90% of them are prompt tokens. The brief asks for generated tokens, and we count prompt tokens as well, because
providers bill them and a GPU has to process them.

**Total Daily Token Load = Daily Active Users × Avg Tokens per Request × Requests per User per Day = Daily Active
Users × 697:**

| Daily Traffic Category | Daily Active Users | Requests per day | Total Daily Token Load | Peak requests per second |
|---|---|---|---|---|
| Prototype | 1,000 | 1,777 | 697,000 | 0.04 |
| Early Startup | 10,000 | 17,767 | 6,970,000 | 0.41 |
| Growing Product | 100,000 | 177,667 | 69,700,000 | 4.11 |
| Large Platform | 1,000,000 | 1,776,667 | 697,000,000 | 41.13 |
| Mass Consumer App | 10,000,000 | 17,766,667 | 6,970,000,000 | 411.27 |
| Global Platform | 100,000,000 | 177,666,667 | 69,700,000,000 | 4,112.65 |

The peak is a busiest hour with twice the average hour's traffic. Every machine count is sized for it.

### Two ways to pay (Steps 2.3 and 2.4)

**Hosting it ourselves.** AWS's `g6.4xlarge` is the brief's machine: 16 vCPUs, 64 GiB of RAM and one NVIDIA L4 GPU
(24 GB), for $1.3232 an hour ($31.76 a day). Qwen3.8-27B and gpt-oss-120b do not fit on one L4, so they get the
`g6.12xlarge`: four L4s for $4.6016 an hour ($110.44 a day). Each model is served with vLLM, never at a lower precision
than Part 1 measured: 16-bit under 2B; FP8 from 2B to 15B, which Part 1 measured at 4-bit; and each Very Large model
in its released format. We had no L4 to measure on, so a machine's capacity is a roofline estimate. A server step
lasts as long as the slower of reading the weights and caches at 300 GB/s and doing 2 operations per parameter per
token at 121 trillion a second (242 trillion in FP8). Each model's cache size comes from its `config.json`. We assume a
server reaches 60% of the bandwidth and 40% of the arithmetic. **Machines Needed** = peak tokens per second ÷ one
machine's tokens per second, rounded up, and at least 1.

**Paying per token.** For each model we take the same model if a provider sells it, and otherwise the sold model
closest in size. No model under 3B is on sale, so the six smallest map to granite-4.2-3b. The price is that of the
provider cheapest for our mix of tokens, blended over prompt and reply tokens. QuadConnect still needs servers that
build each prompt, call the API and run Part 1's output checks: one AWS `m7i.large` ($2.42 a day) per 25 calls a
second at peak. **Total Cost** = the API bill + those servers.

| Model | Category | Part 1 score | Served as, on | Tokens/s per machine | Hosted: $ per 1M tokens (busy machine) | Comparable paid model (cheapest provider for our mix) | API: $ per 1M tokens (our mix) | Hosted ÷ API |
|---|---|---|---|---|---|---|---|---|
| SmolLM2-135M | Ultra-Light | 4.51 | BF16, `g6.4xlarge` | 148,770 | $0.0049 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 0.13 |
| SmolLM2-360M | Ultra-Light | 6.81 | BF16, `g6.4xlarge` | 62,104 | $0.0118 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 0.31 |
| Qwen2.5-0.5B | Ultra-Light | 6.66 | BF16, `g6.4xlarge` | 46,390 | $0.0158 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 0.41 |
| Qwen2.5-1.5B | Small | 7.77 | BF16, `g6.4xlarge` | 15,398 | $0.0477 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 1.23 |
| Falcon3-1B | Small | 7.25 | BF16, `g6.4xlarge` | 14,263 | $0.0515 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 1.33 |
| granite-3.1-2b | Small | 9.11 | FP8, `g6.4xlarge` | 18,692 | $0.0393 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 1.01 |
| Qwen2.5-3B | Medium | 9.32 | FP8, `g6.4xlarge` | 15,407 | $0.0477 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 1.23 |
| Falcon3-3B | Medium | 8.34 | FP8, `g6.4xlarge` | 14,741 | $0.0499 | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | 1.29 |
| Phi-4-mini | Medium | 9.19 | FP8, `g6.4xlarge` | 12,438 | $0.0591 | google/gemma-3-4b-it (deepinfra) | $0.0549 | 1.08 |
| Qwen2.5-7B | Large | 9.27 | FP8, `g6.4xlarge` | 6,309 | $0.1165 | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | 5.08 |
| Llama-3.1-Tulu-3-8B | Large | 9.19 | FP8, `g6.4xlarge` | 5,978 | $0.1230 | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | 5.36 |
| Falcon3-10B | Large | 9.57 | FP8, `g6.4xlarge` | 4,650 | $0.1581 | Qwen/Qwen3.5-9B (deepinfra) | $0.1049 | 1.51 |
| gpt-oss-20b | Very Large | 9.85 | MXFP4, `g6.4xlarge` | 6,653 | $0.1105 | openai/gpt-oss-20b (deepinfra) | $0.0407 | 2.71 |
| Qwen3.8-27B | Very Large | 9.96 | FP8, `g6.12xlarge` | 5,536 | $0.4618 | Qwen/Qwen3.8-27B (deepinfra) | $0.4244 | 1.09 |
| gpt-oss-120b | Very Large | 9.96 | MXFP4, `g6.12xlarge` | 14,839 | $0.1723 | openai/gpt-oss-120b (deepinfra) | $0.0500 | 3.45 |

The last column decides the long run. Below 1, a busy machine makes a token for less than the API sells one.

### Results

**The cheaper option at each traffic level, and how many times cheaper it is** ("1.0×" is a tie in practice: within
5%):

| Model | Prototype | Early Startup | Growing Product | Large Platform | Mass Consumer App | Global Platform |
|---|---|---|---|---|---|---|
| SmolLM2-135M | API 13.0× | API 11.8× | API 6.2× | local 1.0× | local 4.9× | local 8.9× |
| SmolLM2-360M | API 13.0× | API 11.8× | API 6.2× | local 1.0× | local 3.3× | local 3.8× |
| Qwen2.5-0.5B | API 13.0× | API 11.8× | API 6.2× | local 1.0× | local 2.5× | local 2.8× |
| Qwen2.5-1.5B | API 13.0× | API 11.8× | API 6.2× | API 2.0× | API 1.1× | API 1.1× |
| Falcon3-1B | API 13.0× | API 11.8× | API 6.2× | API 2.0× | API 1.2× | API 1.2× |
| granite-3.1-2b | API 13.0× | API 11.8× | API 6.2× | local 1.0× | local 1.1× | local 1.1× |
| Qwen2.5-3B | API 13.0× | API 11.8× | API 6.2× | API 2.0× | API 1.1× | API 1.1× |
| Falcon3-3B | API 13.0× | API 11.8× | API 6.2× | API 2.0× | API 1.1× | API 1.1× |
| Phi-4-mini | API 12.9× | API 11.3× | API 5.1× | API 1.5× | local 1.0× | local 1.0× |
| Qwen2.5-7B | API 13.0× | API 12.3× | API 7.9× | API 4.6× | API 4.1× | API 4.1× |
| Llama-3.1-Tulu-3-8B | API 13.0× | API 12.3× | API 7.9× | API 4.6× | API 4.3× | API 4.3× |
| Falcon3-10B | API 12.8× | API 10.1× | API 3.3× | API 1.6× | API 1.4× | API 1.4× |
| gpt-oss-20b | API 13.0× | API 11.8× | API 6.0× | API 2.9× | API 2.4× | API 2.4× |
| Qwen3.8-27B | API 40.6× | API 20.5× | API 3.5× | API 1.1× | API 1.1× | API 1.1× |
| gpt-oss-120b | API 45.1× | API 39.9× | API 18.7× | API 5.6× | API 3.1× | API 3.1× |

Hosting is cheaper in 14 of the 90 cases.

**Monthly cost (30 days) of Part 1's three tiers:**

| Model (Part 1 tier) | Option | Prototype | Early Startup | Growing Product | Large Platform | Mass Consumer App | Global Platform |
|---|---|---|---|---|---|---|---|
| Qwen2.5-1.5B (fast local) | hosted | $953 | $953 | $953 | $1,906 | $10,481 | $100,044 |
|  | API (granite-4.2-3b) | $74 | $81 | $154 | $956 | $9,343 | $93,069 |
| Qwen2.5-3B (quality local) | hosted | $953 | $953 | $953 | $1,906 | $10,481 | $100,044 |
|  | API (granite-4.2-3b) | $74 | $81 | $154 | $956 | $9,343 | $93,069 |
| Qwen3.8-27B (API tier) | hosted | $3,313 | $3,313 | $3,313 | $9,940 | $99,396 | $967,454 |
|  | API (Qwen3.8-27B) | $82 | $161 | $960 | $9,019 | $89,974 | $899,379 |

**From how many daily users hosting stays cheaper** (searched from 1,000 to 100 million users in steps of 5%, so the
figures are rounded; "never" means it is still dearer at 100 million):

| Model | As estimated | Machines serve 2× more | Machines serve 2× less | Each model's own tokens |
|---|---|---|---|---|
| SmolLM2-135M | 1.0 million | 1.0 million | 1.0 million | 1.0 million |
| SmolLM2-360M | 1.0 million | 1.0 million | 1.0 million | 1.0 million |
| Qwen2.5-0.5B | 1.0 million | 1.0 million | 3.2 million | 1.1 million |
| Qwen2.5-1.5B | never | 1.0 million | never | never |
| Falcon3-1B | never | 2.0 million | never | never |
| granite-3.1-2b | 6.3 million | 1.0 million | never | 8.3 million |
| Qwen2.5-3B | never | 1.0 million | never | never |
| Falcon3-3B | never | 2.0 million | never | never |
| Phi-4-mini | 25.1 million | 720,000 | never | 15.1 million |
| Qwen2.5-7B | never | never | never | never |
| Llama-3.1-Tulu-3-8B | never | never | never | never |
| Falcon3-10B | never | 1.3 million | never | never |
| gpt-oss-20b | never | never | never | never |
| Qwen3.8-27B | never | 760,000 | never | never |
| gpt-oss-120b | never | never | never | never |

### The answers (Step 2.5)

**1. At what scale is local hosting cheaper?**

Only from about **1 million daily users**, and only for the smallest models. As estimated, hosting is cheaper in
14 of the 90 cases. Five models end up cheaper to host: the three Ultra-Light models from about 1 million daily users,
granite-3.1-2b from about 6.3 million, and Phi-4-mini from about 25 million. For the other ten it is still dearer at
100 million. Machines come in whole units, so near a break-even the cheaper option can switch back and forth:
granite-3.1-2b ties with the API at 1 million users, then the API is cheaper again until about 6.3 million.

The reason is the cost per token on a busy machine, in the tables above. Hosting wins only where our machine makes a
token for less than the API sells one. That happens for the Ultra-Light models, which are far smaller than the
smallest model on sale (granite-4.2-3b, $0.0388 per million tokens for our mix): their busy-machine cost is $0.0049 to
$0.0158. It almost happens for the models that match what is on sale: granite-3.1-2b is 1.01× the API's price per
token, Phi-4-mini 1.08×, Qwen3.8-27B 1.09×. It never happens for the 7B, 8B and gpt-oss models. Providers sell those
tokens 2.7 to 5.4 times cheaper than an L4 makes them: Llama-3.1-8B at $0.0229 per million, against $0.1230 for
Llama-3.1-Tulu-3-8B on our machine. Providers run on bigger GPUs that stay busy all day.

The cheap local cases come with a catch. The models that win most clearly are the Ultra-Light ones, which scored
4.51 to 6.81 in Part 1: too weak for most of QuadConnect's jobs, while the API's granite-4.2-3b is a much better model.
Among the models good enough to use (8 or more in Part 1), where hosting wins the API never costs more than 1.12
times as much.

**2. At what scale is API usage cheaper?**

**Everywhere up to 100,000 daily users, for all 15 models**, by 3.3 to 45 times. A GPU machine costs $31.76 a day
(the 4-GPU machine $110.44) even when it is nearly idle. Through the API, 1,000 users' tokens for a small model cost
$0.03 a day, plus $2.42 for the server that calls the API; 100,000 users' tokens cost $2.70. Below about 380,000
daily users the API is cheaper for every model in every what-if we ran.

Past 1 million users the API is still cheaper for **10 of the 15 models at every level**: Qwen2.5-1.5B,
Falcon3-1B, Qwen2.5-3B, Falcon3-3B, Qwen2.5-7B, Llama-3.1-Tulu-3-8B, Falcon3-10B and all three Very Large models.
At 100 million users its lead is 1.1 to 4.3 times, $93,069 a month against $100,044 for Qwen2.5-3B, for example.

**How sure can we be?** The prices are real. The GPU capacity is our estimate, so we tested it:

* If our machines serve **2× more** than estimated, hosting wins for 11 of the 15 models, from 0.7 to 2 million
  users. A real benchmark could show this, and so could machines that are busy around the clock instead of sized for the
  peak.
* If they serve **2× less**, only the three Ultra-Light models win.
* With **each model's own token counts** instead of the average, the same five models win.
* Never, in any what-if, does hosting win for Qwen2.5-7B, Llama-3.1-Tulu-3-8B, gpt-oss-20b or gpt-oss-120b.

So the conclusion that does not move is this: below a few hundred thousand daily users, rent tokens, not machines.

**3. When would you switch your architecture?**

Part 1 gave us three tiers: a fast local model (Qwen2.5-1.5B), a quality local model (Qwen2.5-3B) and an API model
(Qwen3.8-27B). Part 2 says when each should really run on our own machines:

1. **Start on the API, for every job.** Use Hugging Face's router with the cheapest provider for our mix. Up to
   100,000 daily users the bill is $74 to $154 a month for the small models, against $953 for one GPU machine. There is
   also nothing to operate.
2. **Reconsider at about 1 million daily users.** That is where one machine's daily cost meets the API bill for the
   small models ($31.76 against $31.87). The decision then rests on a number we could not measure. So the trigger is to
   **benchmark one `g6.4xlarge`** with vLLM on our real prompts. A machine must serve at least 1.23× our estimate
   for Qwen2.5-3B (about 19,000 tokens a second) to beat the API per token.
3. **Move only the high-volume, small-model jobs.** Search alone is 74% of our tokens, and icebreakers are 18%.
   Those can run on Qwen2.5-3B or granite-3.1-2b machines once the benchmark clears the bar. Everything else stays on the API.
4. **Keep the large models on the API at every scale.** Providers sell gpt-oss tokens 2.7 to 3.4 times cheaper than
   our L4 machines can make them. Hosting those would need bigger GPUs, which is a different machine and a different
   calculation.

Some reasons can bring the switch earlier or push it later, and they are not on the bill:

* **Earlier:** feedback notes are students' own words, and on our machines they never leave our account. Only one
  provider sells granite-4.2-3b, so an outage stops the feature. Provider rate limits can cap a busy day.
* **Later:** GPU machines need monitoring, updates and someone on call. A real deployment also needs a second machine
  for failover, which doubles the smallest local bill. Where hosting does win among the good models, it saves little:
  granite-3.1-2b saves $768 a month at 10 million users, less than the engineering time it takes.

Part 3 turns this into routing rules: which request goes to which model, in which situation.

### What this means for the architecture

1. **The API is the default, not the fallback.** At QuadConnect's real scale, from a prototype up to 100,000 daily
   users, the API costs 3.3 to 45 times less than one idle GPU machine, and there is nothing to operate.
2. **One measurement decides the switch.** Every hosted cost above rests on our roofline estimate, and a 2× error
   moves the break-even by millions of users. Before buying machines, benchmark one `g6.4xlarge` with our real
   prompts.
3. **At scale, split the jobs.** Do not migrate everything. Search and icebreakers carry 92% of the tokens and run well on
   small models, so they are the jobs worth hosting. The large models stay on the API, where their tokens are cheaper.
   Part 3's routing makes this split, request by request (section 3).
4. **Prices move.** API prices and cloud prices both change, so the notebook keeps every price in one cell with its
   date, and the whole comparison re-runs in seconds.

### The full tables

All costs are per day. The same rows are in [`results/local_hosting_costs.csv`](results/local_hosting_costs.csv) and
[`results/api_costs.csv`](results/api_costs.csv).

<details>
<summary><b>Step 2.3: local hosting, all 90 rows</b> (15 models × 6 traffic levels)</summary>

| Model Name | Daily Traffic Category | Avg Tokens per User | Total Daily Token Load | Per Machine Cost (Cloud) | Machines Needed | Total Machine Cost |
|---|---|---|---|---|---|---|
| SmolLM2-135M-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| SmolLM2-135M-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| SmolLM2-135M-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| SmolLM2-135M-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 1 | $31.76 |
| SmolLM2-135M-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 2 | $63.52 |
| SmolLM2-135M-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 11 | $349.36 |
| SmolLM2-360M-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| SmolLM2-360M-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| SmolLM2-360M-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| SmolLM2-360M-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 1 | $31.76 |
| SmolLM2-360M-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 3 | $95.28 |
| SmolLM2-360M-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 26 | $825.76 |
| Qwen2.5-0.5B-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-0.5B-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-0.5B-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-0.5B-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-0.5B-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 4 | $127.04 |
| Qwen2.5-0.5B-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 35 | $1,111.60 |
| Qwen2.5-1.5B-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-1.5B-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-1.5B-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-1.5B-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 2 | $63.52 |
| Qwen2.5-1.5B-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 11 | $349.36 |
| Qwen2.5-1.5B-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 105 | $3,334.80 |
| Falcon3-1B-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Falcon3-1B-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Falcon3-1B-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Falcon3-1B-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 2 | $63.52 |
| Falcon3-1B-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 12 | $381.12 |
| Falcon3-1B-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 114 | $3,620.64 |
| granite-3.1-2b-instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| granite-3.1-2b-instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| granite-3.1-2b-instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| granite-3.1-2b-instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 1 | $31.76 |
| granite-3.1-2b-instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 9 | $285.84 |
| granite-3.1-2b-instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 87 | $2,763.12 |
| Qwen2.5-3B-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-3B-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-3B-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-3B-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 2 | $63.52 |
| Qwen2.5-3B-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 11 | $349.36 |
| Qwen2.5-3B-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 105 | $3,334.80 |
| Falcon3-3B-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Falcon3-3B-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Falcon3-3B-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Falcon3-3B-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 2 | $63.52 |
| Falcon3-3B-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 11 | $349.36 |
| Falcon3-3B-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 110 | $3,493.60 |
| Phi-4-mini-instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Phi-4-mini-instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Phi-4-mini-instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Phi-4-mini-instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 2 | $63.52 |
| Phi-4-mini-instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 13 | $412.88 |
| Phi-4-mini-instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 130 | $4,128.80 |
| Qwen2.5-7B-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-7B-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-7B-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Qwen2.5-7B-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 3 | $95.28 |
| Qwen2.5-7B-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 26 | $825.76 |
| Qwen2.5-7B-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 256 | $8,130.56 |
| Llama-3.1-Tulu-3-8B (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Llama-3.1-Tulu-3-8B (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Llama-3.1-Tulu-3-8B (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Llama-3.1-Tulu-3-8B (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 3 | $95.28 |
| Llama-3.1-Tulu-3-8B (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 27 | $857.52 |
| Llama-3.1-Tulu-3-8B (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 270 | $8,575.20 |
| Falcon3-10B-Instruct (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| Falcon3-10B-Instruct (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| Falcon3-10B-Instruct (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| Falcon3-10B-Instruct (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 4 | $127.04 |
| Falcon3-10B-Instruct (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 35 | $1,111.60 |
| Falcon3-10B-Instruct (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 347 | $11,020.72 |
| gpt-oss-20b (`g6.4xlarge`) | Prototype | 697 | 697,000 | $31.76 | 1 | $31.76 |
| gpt-oss-20b (`g6.4xlarge`) | Early Startup | 697 | 6,970,000 | $31.76 | 1 | $31.76 |
| gpt-oss-20b (`g6.4xlarge`) | Growing Product | 697 | 69,700,000 | $31.76 | 1 | $31.76 |
| gpt-oss-20b (`g6.4xlarge`) | Large Platform | 697 | 697,000,000 | $31.76 | 3 | $95.28 |
| gpt-oss-20b (`g6.4xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $31.76 | 25 | $794.00 |
| gpt-oss-20b (`g6.4xlarge`) | Global Platform | 697 | 69,700,000,000 | $31.76 | 243 | $7,717.68 |
| Qwen3.8-27B (`g6.12xlarge`) | Prototype | 697 | 697,000 | $110.44 | 1 | $110.44 |
| Qwen3.8-27B (`g6.12xlarge`) | Early Startup | 697 | 6,970,000 | $110.44 | 1 | $110.44 |
| Qwen3.8-27B (`g6.12xlarge`) | Growing Product | 697 | 69,700,000 | $110.44 | 1 | $110.44 |
| Qwen3.8-27B (`g6.12xlarge`) | Large Platform | 697 | 697,000,000 | $110.44 | 3 | $331.32 |
| Qwen3.8-27B (`g6.12xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $110.44 | 30 | $3,313.20 |
| Qwen3.8-27B (`g6.12xlarge`) | Global Platform | 697 | 69,700,000,000 | $110.44 | 292 | $32,248.48 |
| gpt-oss-120b (`g6.12xlarge`) | Prototype | 697 | 697,000 | $110.44 | 1 | $110.44 |
| gpt-oss-120b (`g6.12xlarge`) | Early Startup | 697 | 6,970,000 | $110.44 | 1 | $110.44 |
| gpt-oss-120b (`g6.12xlarge`) | Growing Product | 697 | 69,700,000 | $110.44 | 1 | $110.44 |
| gpt-oss-120b (`g6.12xlarge`) | Large Platform | 697 | 697,000,000 | $110.44 | 2 | $220.88 |
| gpt-oss-120b (`g6.12xlarge`) | Mass Consumer App | 697 | 6,970,000,000 | $110.44 | 11 | $1,214.84 |
| gpt-oss-120b (`g6.12xlarge`) | Global Platform | 697 | 69,700,000,000 | $110.44 | 109 | $12,037.96 |

</details>

<details>
<summary><b>Step 2.4: Hugging Face Inference API, all 90 rows</b> (15 models × 6 traffic levels)</summary>

| Local LLM Model Size | Comparable Paid Model Hosted on Hugging Face | Cost of Paid API per Token ($ per 1M tokens) | Daily Traffic Category | Total Token Load | Estimated API Cost | Machines Required (API infrastructure) | Total Cost |
|---|---|---|---|---|---|---|---|
| SmolLM2-135M-Instruct (0.135B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| SmolLM2-135M-Instruct (0.135B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| SmolLM2-135M-Instruct (0.135B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| SmolLM2-135M-Instruct (0.135B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| SmolLM2-135M-Instruct (0.135B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| SmolLM2-135M-Instruct (0.135B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| SmolLM2-360M-Instruct (0.362B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| SmolLM2-360M-Instruct (0.362B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| SmolLM2-360M-Instruct (0.362B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| SmolLM2-360M-Instruct (0.362B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| SmolLM2-360M-Instruct (0.362B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| SmolLM2-360M-Instruct (0.362B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| Qwen2.5-0.5B-Instruct (0.494B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| Qwen2.5-0.5B-Instruct (0.494B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| Qwen2.5-0.5B-Instruct (0.494B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| Qwen2.5-0.5B-Instruct (0.494B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| Qwen2.5-0.5B-Instruct (0.494B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| Qwen2.5-0.5B-Instruct (0.494B, Ultra-Light) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| Qwen2.5-1.5B-Instruct (1.544B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| Qwen2.5-1.5B-Instruct (1.544B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| Qwen2.5-1.5B-Instruct (1.544B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| Qwen2.5-1.5B-Instruct (1.544B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| Qwen2.5-1.5B-Instruct (1.544B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| Qwen2.5-1.5B-Instruct (1.544B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| Falcon3-1B-Instruct (1.669B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| Falcon3-1B-Instruct (1.669B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| Falcon3-1B-Instruct (1.669B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| Falcon3-1B-Instruct (1.669B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| Falcon3-1B-Instruct (1.669B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| Falcon3-1B-Instruct (1.669B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| granite-3.1-2b-instruct (2.534B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| granite-3.1-2b-instruct (2.534B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| granite-3.1-2b-instruct (2.534B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| granite-3.1-2b-instruct (2.534B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| granite-3.1-2b-instruct (2.534B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| granite-3.1-2b-instruct (2.534B, Small) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| Qwen2.5-3B-Instruct (3.086B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| Qwen2.5-3B-Instruct (3.086B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| Qwen2.5-3B-Instruct (3.086B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| Qwen2.5-3B-Instruct (3.086B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| Qwen2.5-3B-Instruct (3.086B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| Qwen2.5-3B-Instruct (3.086B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| Falcon3-3B-Instruct (3.228B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| Falcon3-3B-Instruct (3.228B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Early Startup | 6,970,000 | $0.27 | 1 | $2.69 |
| Falcon3-3B-Instruct (3.228B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Growing Product | 69,700,000 | $2.70 | 1 | $5.12 |
| Falcon3-3B-Instruct (3.228B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Large Platform | 697,000,000 | $27.03 | 2 | $31.87 |
| Falcon3-3B-Instruct (3.228B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Mass Consumer App | 6,970,000,000 | $270.30 | 17 | $311.44 |
| Falcon3-3B-Instruct (3.228B, Medium) | ibm-granite/granite-4.2-3b (deepinfra) | $0.0388 | Global Platform | 69,700,000,000 | $2,703.00 | 165 | $3,102.30 |
| Phi-4-mini-instruct (3.836B, Medium) | google/gemma-3-4b-it (deepinfra) | $0.0549 | Prototype | 697,000 | $0.04 | 1 | $2.46 |
| Phi-4-mini-instruct (3.836B, Medium) | google/gemma-3-4b-it (deepinfra) | $0.0549 | Early Startup | 6,970,000 | $0.38 | 1 | $2.80 |
| Phi-4-mini-instruct (3.836B, Medium) | google/gemma-3-4b-it (deepinfra) | $0.0549 | Growing Product | 69,700,000 | $3.83 | 1 | $6.25 |
| Phi-4-mini-instruct (3.836B, Medium) | google/gemma-3-4b-it (deepinfra) | $0.0549 | Large Platform | 697,000,000 | $38.25 | 2 | $43.09 |
| Phi-4-mini-instruct (3.836B, Medium) | google/gemma-3-4b-it (deepinfra) | $0.0549 | Mass Consumer App | 6,970,000,000 | $382.50 | 17 | $423.64 |
| Phi-4-mini-instruct (3.836B, Medium) | google/gemma-3-4b-it (deepinfra) | $0.0549 | Global Platform | 69,700,000,000 | $3,825.00 | 165 | $4,224.30 |
| Qwen2.5-7B-Instruct (7.616B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Prototype | 697,000 | $0.02 | 1 | $2.44 |
| Qwen2.5-7B-Instruct (7.616B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Early Startup | 6,970,000 | $0.16 | 1 | $2.58 |
| Qwen2.5-7B-Instruct (7.616B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Growing Product | 69,700,000 | $1.60 | 1 | $4.02 |
| Qwen2.5-7B-Instruct (7.616B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Large Platform | 697,000,000 | $15.98 | 2 | $20.82 |
| Qwen2.5-7B-Instruct (7.616B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Mass Consumer App | 6,970,000,000 | $159.80 | 17 | $200.94 |
| Qwen2.5-7B-Instruct (7.616B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Global Platform | 69,700,000,000 | $1,598.00 | 165 | $1,997.30 |
| Llama-3.1-Tulu-3-8B (8.03B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Prototype | 697,000 | $0.02 | 1 | $2.44 |
| Llama-3.1-Tulu-3-8B (8.03B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Early Startup | 6,970,000 | $0.16 | 1 | $2.58 |
| Llama-3.1-Tulu-3-8B (8.03B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Growing Product | 69,700,000 | $1.60 | 1 | $4.02 |
| Llama-3.1-Tulu-3-8B (8.03B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Large Platform | 697,000,000 | $15.98 | 2 | $20.82 |
| Llama-3.1-Tulu-3-8B (8.03B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Mass Consumer App | 6,970,000,000 | $159.80 | 17 | $200.94 |
| Llama-3.1-Tulu-3-8B (8.03B, Large) | meta-llama/Llama-3.1-8B-Instruct (deepinfra) | $0.0229 | Global Platform | 69,700,000,000 | $1,598.00 | 165 | $1,997.30 |
| Falcon3-10B-Instruct (10.306B, Large) | Qwen/Qwen3.5-9B (deepinfra) | $0.1049 | Prototype | 697,000 | $0.07 | 1 | $2.49 |
| Falcon3-10B-Instruct (10.306B, Large) | Qwen/Qwen3.5-9B (deepinfra) | $0.1049 | Early Startup | 6,970,000 | $0.73 | 1 | $3.15 |
| Falcon3-10B-Instruct (10.306B, Large) | Qwen/Qwen3.5-9B (deepinfra) | $0.1049 | Growing Product | 69,700,000 | $7.31 | 1 | $9.73 |
| Falcon3-10B-Instruct (10.306B, Large) | Qwen/Qwen3.5-9B (deepinfra) | $0.1049 | Large Platform | 697,000,000 | $73.10 | 2 | $77.94 |
| Falcon3-10B-Instruct (10.306B, Large) | Qwen/Qwen3.5-9B (deepinfra) | $0.1049 | Mass Consumer App | 6,970,000,000 | $731.00 | 17 | $772.14 |
| Falcon3-10B-Instruct (10.306B, Large) | Qwen/Qwen3.5-9B (deepinfra) | $0.1049 | Global Platform | 69,700,000,000 | $7,310.00 | 165 | $7,709.30 |
| gpt-oss-20b (20.9B, Very Large) | openai/gpt-oss-20b (deepinfra) | $0.0407 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| gpt-oss-20b (20.9B, Very Large) | openai/gpt-oss-20b (deepinfra) | $0.0407 | Early Startup | 6,970,000 | $0.28 | 1 | $2.70 |
| gpt-oss-20b (20.9B, Very Large) | openai/gpt-oss-20b (deepinfra) | $0.0407 | Growing Product | 69,700,000 | $2.84 | 1 | $5.26 |
| gpt-oss-20b (20.9B, Very Large) | openai/gpt-oss-20b (deepinfra) | $0.0407 | Large Platform | 697,000,000 | $28.39 | 2 | $33.23 |
| gpt-oss-20b (20.9B, Very Large) | openai/gpt-oss-20b (deepinfra) | $0.0407 | Mass Consumer App | 6,970,000,000 | $283.90 | 17 | $325.04 |
| gpt-oss-20b (20.9B, Very Large) | openai/gpt-oss-20b (deepinfra) | $0.0407 | Global Platform | 69,700,000,000 | $2,839.00 | 165 | $3,238.30 |
| Qwen3.8-27B (27.8B, Very Large) | Qwen/Qwen3.8-27B (deepinfra) | $0.4244 | Prototype | 697,000 | $0.30 | 1 | $2.72 |
| Qwen3.8-27B (27.8B, Very Large) | Qwen/Qwen3.8-27B (deepinfra) | $0.4244 | Early Startup | 6,970,000 | $2.96 | 1 | $5.38 |
| Qwen3.8-27B (27.8B, Very Large) | Qwen/Qwen3.8-27B (deepinfra) | $0.4244 | Growing Product | 69,700,000 | $29.58 | 1 | $32.00 |
| Qwen3.8-27B (27.8B, Very Large) | Qwen/Qwen3.8-27B (deepinfra) | $0.4244 | Large Platform | 697,000,000 | $295.80 | 2 | $300.64 |
| Qwen3.8-27B (27.8B, Very Large) | Qwen/Qwen3.8-27B (deepinfra) | $0.4244 | Mass Consumer App | 6,970,000,000 | $2,958.00 | 17 | $2,999.14 |
| Qwen3.8-27B (27.8B, Very Large) | Qwen/Qwen3.8-27B (deepinfra) | $0.4244 | Global Platform | 69,700,000,000 | $29,580.00 | 165 | $29,979.30 |
| gpt-oss-120b (116.8B, Very Large) | openai/gpt-oss-120b (deepinfra) | $0.0500 | Prototype | 697,000 | $0.03 | 1 | $2.45 |
| gpt-oss-120b (116.8B, Very Large) | openai/gpt-oss-120b (deepinfra) | $0.0500 | Early Startup | 6,970,000 | $0.35 | 1 | $2.77 |
| gpt-oss-120b (116.8B, Very Large) | openai/gpt-oss-120b (deepinfra) | $0.0500 | Growing Product | 69,700,000 | $3.48 | 1 | $5.90 |
| gpt-oss-120b (116.8B, Very Large) | openai/gpt-oss-120b (deepinfra) | $0.0500 | Large Platform | 697,000,000 | $34.83 | 2 | $39.67 |
| gpt-oss-120b (116.8B, Very Large) | openai/gpt-oss-120b (deepinfra) | $0.0500 | Mass Consumer App | 6,970,000,000 | $348.33 | 17 | $389.47 |
| gpt-oss-120b (116.8B, Very Large) | openai/gpt-oss-120b (deepinfra) | $0.0500 | Global Platform | 69,700,000,000 | $3,483.30 | 165 | $3,882.60 |

</details>

---

## 3. Routing strategies

Part 3 decides which model answers each request, and how that changes with the situation. The notebook's Part 3 runs
every strategy on QuadConnect's own numbers (Part 1's scores and token counts, Part 2's machines and prices, and the
providers' measured speeds), so every figure below comes from it.

**The router's menu** holds only models whose quality Part 1 measured on QuadConnect's own jobs:

| Where | Model | What Parts 1 and 2 found |
|---|---|---|
| Our machines | Qwen2.5-3B (FP8 on a `g6.4xlarge`, as in Part 2) | 10 on icebreakers, feedback ratings and venue checks, 9.9 on staff summaries, but 6.7 on search |
| Hugging Face API | gpt-oss-20b (3 providers) | 9.8 on search, 10 on three of the other jobs, 9.46 on feedback ratings |
| Hugging Face API | gpt-oss-120b (6 providers) | 9.8 on search and 10 on the other four |
| Hugging Face API | Qwen3.8-27B (5 providers) | Part 1's API tier: the same scores as gpt-oss-120b, at several times the price (table below) |

**Speed targets.** Two jobs keep a student waiting. A search needs the whole reply before it can run, so it has 1
second. Icebreakers appear word by word, so the full reply has 2 seconds. Nobody waits for a feedback rating, a staff
summary or a venue check: they run in the background.

**How a request's latency is estimated.** Through the API: the provider's time to first token, plus the reply's
length at the provider's speed. Hugging Face's router measures both for every provider; these are its figures of
3 November 2026. On our machines: one token per server step, from Part 2's roofline, with the requests in flight
capped so that the slowest waiting job meets its target (the cap costs some of Part 2's throughput).

**Quality** is Part 1's score (1–10) for that model on that job, weighted by how often each job runs (Step 2.1).
**Cost** is Part 2's: our machines by the day, API tokens at each provider's price, and the `m7i.large` servers that
call the API.

**Design level: the Mass Consumer App, 10 million daily users.** Below about 2.3 million users the router keeps every
job on the API (Scenario 4), so the rules that involve our machines would never fire. At 10 million every rule below is
in use, so that is where the strategies are evaluated; Scenario 4 covers all six traffic levels.

**What a request costs on each**, as the mean over the job mix (at the cheapest provider for an API model; for ours,
a busy machine as in Part 2), next to Part 1's scores:

| Model | Where | search | icebreakers | feedback rating | staff summary | venue check | USD per 1,000 requests |
|---|---|---|---|---|---|---|---|
| Qwen2.5-3B | our machines | 6.70 | 10.00 | 10.00 | 9.90 | 10.00 | $0.0177 |
| gpt-oss-20b | Hugging Face, 3 providers | 9.80 | 10.00 | 9.46 | 10.00 | 10.00 | $0.0208 |
| gpt-oss-120b | Hugging Face, 6 providers | 9.80 | 10.00 | 10.00 | 10.00 | 10.00 | $0.0246 |
| Qwen3.8-27B | Hugging Face, 5 providers | 9.80 | 10.00 | 10.00 | 10.00 | 10.00 | $0.1405 |

### Step 3.1: Define five system scenarios

| # | Scenario | What happens at QuadConnect | Routing condition | How the router knows |
|---|---|---|---|---|
| 1 | Normal operation | An ordinary hour: steady traffic, every machine and provider working. | Query complexity (which job it is) and the speed target | The page that sends the request names the job |
| 2 | Peak usage hours | From 5 to 11 pm students make plans for the evening, and traffic runs at twice the average (Part 2's peak). | System load | Requests in flight on our machines |
| 3 | High-complexity queries | Searches typed in students' own words, which have to be mapped onto QuadConnect's lists: "Grainger students in the robotics club", "someone shy to talk about books and movies with, one on one". | Query complexity and confidence score | The job, and Part 1's output checks on every reply |
| 4 | Cost optimization | Traffic grows, or a month's budget is tight, and the AI bill has to come down. | Daily request volume | Each job's request count over the past day |
| 5 | System overload or outage | An API provider fails, one of our machines fails, or no API can be reached at all. | System load and provider health | Failed or timed-out calls, and our machines' health checks |

**A condition we tested and did not use: prompt length.** Our model's five search prompts are all about the same
length (456 to 461 tokens), and it failed on the ones with implicit wording: a campus building, a personality, a campus
event. Length does not tell a hard request from an easy one, so the router uses the job and the output checks.

### Step 3.2: Design routing strategies

| Scenario | Routing strategy | Local models used | Hugging Face model used | Expected benefit |
|---|---|---|---|---|
| 1. Normal operation | Each job goes to the cheapest place that is good enough for it (within 0.1 of the best score any model got on it in Part 1) and fast enough for its target. Search goes to the API. The other four jobs go to our machines once their volume pays for the machines. | Qwen2.5-3B: icebreakers, feedback ratings, staff summaries and venue checks | gpt-oss-20b via deepinfra: every search | The best API model's quality at about half its cost |
| 2. Peak usage hours | Our machines are sized for the average hour, not the busiest. When they are full, a new request for one of their jobs goes to that job's API option instead of waiting. | Qwen2.5-3B, on 2 machines instead of 3 | gpt-oss-20b via deepinfra (gpt-oss-120b for feedback ratings): the overflow | One machine less and no queue, at the same quality |
| 3. High-complexity queries | Searches skip our machines and go straight to the API. On the other jobs, a reply that breaks one of Part 1's rules is re-asked of the API. | Qwen2.5-3B, never for search | gpt-oss-20b via deepinfra: searches and re-asked replies | Searches at 9.8 instead of 6.7, and no student's name in a staff summary |
| 4. Cost optimization | The daily volume decides. Below about 2.3 million users every job stays on the API, each on its cheapest good-enough model and provider; above that, the easy jobs move to our machines. On a tight budget, the jobs nobody waits for move out of the busiest hours. | Qwen2.5-3B, from about 2.3 million users | gpt-oss-20b and gpt-oss-120b, at their cheapest providers | The lowest bill at every traffic level |
| 5. System overload or outage | A provider whose calls fail or time out is skipped, and the next cheapest option that meets the target takes over. A failed machine's share goes to the API. With no API at all, our machines keep their jobs and search uses QuadConnect's keyword search. | Qwen2.5-3B | gpt-oss-120b via novita and gpt-oss-20b via ovhcloud: the fallbacks | Every request answered while a provider or a machine is down |

**The router's rules, in the order it applies them:**

1. **Health:** a provider whose calls fail or time out is skipped (Scenario 5).
2. **Job:** a search goes to the API (Scenario 3). The other jobs go to our machines when the volume rule has put them
   there (Scenario 4), and to the API otherwise.
3. **Load:** when our machines are full, the request goes to its job's API option instead of waiting (Scenarios 2
   and 5).
4. **Model and provider:** on the API, the cheapest option that is good enough for the job and fast enough for its
   target (Scenario 1).
5. **Confidence:** every reply is checked. One that breaks a rule is re-asked of the job's API option, or held back
   when no API answers (Scenarios 3 and 5).
6. **Budget:** when money is tight, the background jobs wait for the quiet hours (Scenario 4).

### Step 3.3: Evaluate the strategies

Each strategy runs against the same situation without it, at 10 million daily users unless a table says otherwise.
**Waiting time** is the mean latency of the two jobs a student waits for, search and icebreakers, weighted by how often
each runs. **Score** is Part 1's score (1–10) of the model that answers, weighted by the job mix.

#### Scenario 1: normal operation

The cheapest API option for each job, if it runs on the API:

| Job | Cheapest good-enough API option | Latency | Target | USD per 1,000 requests | Score |
|---|---|---|---|---|---|
| search | gpt-oss-20b via deepinfra | 0.94 s | 1 s | $0.0242 | 9.80 |
| icebreakers | gpt-oss-20b via deepinfra | 1.03 s | 2 s | $0.0181 | 10.00 |
| feedback rating | gpt-oss-120b via deepinfra | 0.93 s | none (background) | $0.0141 | 10.00 |
| staff summary | gpt-oss-20b via deepinfra | 0.80 s | none (background) | $0.0144 | 10.00 |
| venue check | gpt-oss-20b via deepinfra | 0.83 s | none (background) | $0.0187 | 10.00 |

The router's plan. Our 3 machines run at most 99 requests at a time, so icebreakers
finish within their 2 seconds:

| Job | Runs on | Requests per day | Latency | Score | API USD/day |
|---|---|---|---|---|---|
| search | gpt-oss-20b via deepinfra | 10,000,000 | 0.94 s | 9.80 | $242.16 |
| icebreakers | Qwen2.5-3B-Instruct (ours) | 5,000,000 | 1.99 s | 10.00 | $0.00 |
| feedback rating | Qwen2.5-3B-Instruct (ours) | 2,000,000 | 0.55 s | 10.00 | $0.00 |
| staff summary | Qwen2.5-3B-Instruct (ours), 20% re-asked of gpt-oss-20b via deepinfra | 666,667 | 0.94 s | 10.00 | $1.92 |
| venue check | Qwen2.5-3B-Instruct (ours) | 100,000 | 1.06 s | 10.00 | $0.00 |

Against the same day with no routing:

| System | Our machines | API servers | USD per day | Waiting time | Score (1–10) | Replies breaking a rule |
|---|---|---|---|---|---|---|
| No routing: Part 1's API tier (Qwen3.8-27B) for every job | 0 | 17 | $2,537.66 | 0.69 s | 9.89 | 0.0% |
| No routing: the best single API model (gpt-oss-120b) for every job | 0 | 17 | $654.22 | 0.79 s | 9.89 | 0.0% |
| No routing: our Qwen2.5-3B machines for every job | 11 | 0 | $349.36 | 1.11 s | 8.14 | 23.3% |
| Routing (Scenario 1) | 3 | 10 | $363.56 | 1.29 s | 9.89 | 0.0% |

#### Scenario 2: peak usage hours

In the busiest hours our machines would need 38,673 tokens a second. The rule sizes them for the
average hour (2 machines) and sends the excess, 25% of their requests in those
hours, to the API. Without the rule those 2 machines would leave 956,738 requests
waiting after the six busiest hours.

| Our machines are | Our machines | API servers | USD per day | Waiting time | Score (1–10) | Replies breaking a rule |
|---|---|---|---|---|---|---|
| Machines sized for the busiest hour (Scenario 1's plan) | 3 | 10 | $363.56 | 1.29 s | 9.89 | 0.0% |
| Machines sized for the average, the busiest hours' excess to the API | 2 | 12 | $352.43 | 1.25 s | 9.89 | 0.0% |

#### Scenario 3: high-complexity queries

Three ways to answer the 10,000,000 searches a day:

| Searches | Runs on | Our machines | USD per day | Latency | Score | Replies breaking a rule |
|---|---|---|---|---|---|---|
| Our Qwen2.5-3B only | Qwen2.5-3B-Instruct (ours) | 9 | $285.84 | 0.97 s | 6.70 | 40% |
| Our Qwen2.5-3B, rule-breaking replies re-asked of the API | Qwen2.5-3B-Instruct (ours), 40% re-asked of gpt-oss-20b via deepinfra | 9 | $382.70 | 1.35 s | 8.80 | 0% |
| Straight to the API (the routing rule) | gpt-oss-20b via deepinfra | 0 | $242.16 | 0.94 s | 9.80 | 0% |

The same confidence rule on the jobs our machines keep. Here it is staff summaries, where 20% of our model's
replies in Part 1 named a student:

| Staff summaries | Runs on | Latency | Score | Replies breaking a rule | API USD/day |
|---|---|---|---|---|---|
| Staff summaries, no checks | Qwen2.5-3B-Instruct (ours) | 0.78 s | 9.90 | 20% | $0.00 |
| Staff summaries, re-asked on a broken rule | Qwen2.5-3B-Instruct (ours), 20% re-asked of gpt-oss-20b via deepinfra | 0.94 s | 10.00 | 0% | $1.92 |

#### Scenario 4: cost optimization

The router at all six traffic levels, in US dollars a day, against the three systems without routing. It first moves
jobs to our machines at about 2,290,868 daily users.

| Traffic level | Jobs on our machines | Our machines | Routing | Best single API model | Part 1's API tier | All on our machines | Routing score | Saving against the best single API model |
|---|---|---|---|---|---|---|---|---|
| Prototype | none | 0 | $2.46 | $2.48 | $2.67 | $31.76 | 9.89 | 1% |
| Early Startup | none | 0 | $2.79 | $3.03 | $4.92 | $31.76 | 9.89 | 8% |
| Growing Product | none | 0 | $6.14 | $8.55 | $27.39 | $31.76 | 9.89 | 28% |
| Large Platform | none | 0 | $42.07 | $66.15 | $254.49 | $63.52 | 9.89 | 36% |
| Mass Consumer App | icebreakers, feedback rating, staff summary, venue check | 3 | $363.56 | $654.22 | $2,537.66 | $349.36 | 9.89 | 44% |
| Global Platform | icebreakers, feedback rating, staff summary | 26 | $3,515.21 | $6,530.07 | $25,364.49 | $3,461.84 | 9.89 | 46% |

With a tight budget, the background jobs move out of the busiest hours. The busiest hours then need only
26,296 tokens a second and the quiet hours 17,017, so our machines go from
3 to 2:

| Plan | Our machines | API servers | USD per day | Waiting time | Score (1–10) | Replies breaking a rule |
|---|---|---|---|---|---|---|
| Scenario 1's plan | 3 | 10 | $363.56 | 1.29 s | 9.89 | 0.0% |
| Background jobs moved out of the busiest hours | 2 | 10 | $331.80 | 1.29 s | 9.89 | 0.0% |

#### Scenario 5: system overload or outage

Each failure lasts the busiest hour of the day. Waiting time and score count the replies a model gives; in the last
row, searches get keyword results.

| Event (one busiest hour) | Without routing rules | With the routing rules | Answered by a model | USD in that hour | Waiting time | Score |
|---|---|---|---|---|---|---|
| normal | all answered | all answered | 100% | $25.32 | 1.29 s | 9.89 |
| the main provider (deepinfra) is down | 56% of requests fail: every search | all answered: search to gpt-oss-120b via novita; re-asked summaries to gpt-oss-20b via ovhcloud | 100% | $38.01 | 1.17 s | 9.89 |
| one of our machines fails | a queue builds: the other 2 serve 75% of the load | all answered: 25% of our machines' requests go to the API | 100% | $26.83 | 1.21 s | 9.89 |
| every API provider is down | 56% of requests fail: every search | our machines keep their jobs (0.8% of replies, those breaking a rule, held back); every search uses QuadConnect's keyword search | 43% | $4.98 | 1.99 s | 10.00 |

#### The five scenarios side by side

| Scenario | Without the strategy | With it | Cost without | Cost with | Waiting without | Waiting with | Score without | Score with |
|---|---|---|---|---|---|---|---|---|
| 1. Normal operation | gpt-oss-120b for every job | each job to its cheapest good-enough place | $654.22 a day | $363.56 a day | 0.79 s | 1.29 s | 9.89 | 9.89 |
| 2. Peak usage hours | machines sized for the busiest hour | sized for the average, overflow to the API | $363.56 a day | $352.43 a day | 1.29 s | 1.25 s | 9.89 | 9.89 |
| 3. High-complexity queries (searches) | our model first, re-asked on a broken rule | every search straight to the API | $382.70 a day | $242.16 a day | 1.35 s | 0.94 s | 8.80 | 9.80 |
| 4. Cost optimization (tight budget) | Scenario 1's plan | background jobs out of the busiest hours | $363.56 a day | $331.80 a day | 1.29 s | 1.29 s | 9.89 | 9.89 |
| 5. Outage: the main provider is down | 56% of requests fail | the next provider takes over | $25.32 in that hour | $38.01 in that hour | fails | 1.17 s | fails | 9.89 |

#### What the evaluation shows

**How the strategies improve latency**

* **Searches always meet their 1-second target.** gpt-oss-20b at deepinfra answers a search in 0.94 seconds. Trying
  our model first, and re-asking the API when the reply breaks a rule, would average 1.35 seconds, because 40% of
  searches would wait for two models (Scenario 3).
* **Peak hours never build a queue.** Two machines sized for the average hour, with no overflow rule, would leave
  956,738 requests waiting after the six busiest hours. With the rule, the excess goes to the API, and the waiting time
  even drops slightly, from 1.29 to 1.25 seconds (Scenario 2).
* **Failures do not stop the app.** When deepinfra is down, searches move to gpt-oss-120b at novita and take 0.75
  seconds. When one of our machines fails, a quarter of its jobs' requests go to the API and nothing waits
  (Scenario 5).
* **Icebreakers pay for the routing.** On our machines they take 1.99 seconds instead of 1.03 through the API. That
  is inside their 2-second target, and they appear word by word. It is also why the best single API model is faster on
  average: 0.79 seconds against the router's 1.29.

**How they reduce cost**

* **Each job pays only for the model it needs.** At 10 million daily users, Part 1's API tier (Qwen3.8-27B for every
  job) costs $2,537.66 a day and the best single API model (gpt-oss-120b) $654.22. The router costs $363.56: 86% and
  44% less (Scenario 1). Qwen3.8-27B is 5.7 times the price of gpt-oss-120b per request for the same scores, so leaving
  it off the menu is the biggest single saving.
* **The saving grows with traffic.** Against the best single API model it is 1% at 1,000 users, 28% at 100,000 and 46%
  at 100 million (Scenario 4). Below about 2.3 million users it comes only from choosing the model and provider for
  each job; above that, the easy jobs also move to our machines.
* **No machine is bought for the peak alone.** Our machines sized for the average hour, with the overflow rule, are 2
  instead of 3: $352.43 a day instead of $363.56 (Scenario 2). Moving the background jobs out of the busiest hours also
  needs 2 instead of 3: $331.80 a day (Scenario 4).
* **The hard job is not tried twice.** Sending searches straight to the API costs $242.16 a day, against $382.70 for
  our model plus re-asks (Scenario 3).
* **The router turns down a cheaper option that is worse.** Running every job on our machines is 4% cheaper than the
  router at 10 million users ($349.36 a day) and 2% cheaper at 100 million. But its score falls to 8.14, and 23% of
  its replies break a rule.

**How they maintain output quality**

* **Every job is answered by a model good enough for it:** one that scored within 0.1 of the best any model got on that
  job in Part 1. The router's score, 9.89, is the same as the best single API model's at every traffic level
  (Scenario 4).
* **The output checks catch what a cheaper model gets wrong in form.** Without them, 20% of our model's staff
  summaries name a student; with them none do, for $1.92 a day (Scenario 3).
* **The checks cannot catch a wrong answer that breaks no rule.** That is why searches never run on our machines: our
  model scored 6.7 on them, and re-asking only lifts that to 8.8 (Scenario 3).
* **The fallbacks give a smaller, honest answer instead of a bad one.** With no API at all, 43% of requests are still
  answered by a model at full quality (10.0). Searches get QuadConnect's keyword results. The 0.8% of replies that
  break a rule are held back for staff instead of being shown (Scenario 5).

**What could change these results.** The prices and speeds are a snapshot from 3 November 2026, and our machines'
capacity is Part 2's estimate. The router re-plans whenever its inputs change. If a benchmark shows our machines
serving twice as much, the easy jobs move to them sooner; if a provider slows down past a target, the router stops
using it.

### What this means for the architecture

1. **The API tier changes.** Part 1 named Qwen3.8-27B the API tier. Part 3 replaces it with gpt-oss-20b, and
   gpt-oss-120b for feedback ratings: the same scores at a sixth of the price.
2. **Our machines arrive with volume.** Below about 2.3 million daily users every job stays on
   the API. Above that, a pool of Qwen2.5-3B machines takes icebreakers, feedback ratings, staff summaries and venue
   checks. Searches never move there.
3. **Every reply is checked, by code, before anyone sees it.** The checks decide when to re-ask the API, and they keep
   a student's name out of staff summaries whichever model wrote them.
4. **Every path has a fallback.** There is a second provider for each API job, the API for our machines' overflow,
   and keyword search when no model can answer.
