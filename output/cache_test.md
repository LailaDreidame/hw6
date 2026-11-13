# With and without cached tokens (Problem 4)

I ran the agent on all 12 practice documents two ways, back to back on 2026-11-13, using gpt-6-luna through Portkey. Every model call is saved in `output/cache_test.json`: 48 calls, 24 per setup, because each document takes 2 calls. Script: `cache_test.py`. Run one document in either setup with `python agent.py --doc ... --setup with_cache|without_cache`.

## The two setups and the proof they worked

| Setup | How it is set up (`agent.py` → `CACHE_SETUPS`) | What the API reported |
|---|---|---|
| **With cache** | The prompt and handbook come first and are identical every time. They're marked as a cache breakpoint, and every call shares one `prompt_cache_key` so OpenAI sends them to the same cache. | **23 of 24 calls read from the cache.** 247,240 of 261,839 input tokens (94%) were cached. The one call with no cache read was the very first call, which stored the handbook. |
| **Without cache** | OpenAI's "explicit" cache mode with no breakpoints, so it neither stores nor reuses anything. | **All 24 calls: 0 cached tokens and 0 cache-write tokens.** Every input token was billed at the full price. |

Both setups sent exactly the same input (261,839 tokens in total), so the only difference is how those tokens were billed.

## 1. Total cost, cost per document, and % saved

Cost = full-price input × $0.10/1M + cached input × $0.01/1M + cache writes × $0.125/1M + output × $0.50/1M (from `data/prices.json`).

| Document | Without cache | With cache | Saved |
|---|---|---|---|
| p01_bluehen_quote.html | $0.002258 | $0.001572 | 30.4% |
| p02_elmcity_quote.html | $0.002294 | $0.000394 | 82.8% |
| p03_ivyprint_catalog.html | $0.002247 | $0.000324 | 85.6% |
| p04_harborstitch_quote.html | $0.002290 | $0.000363 | 84.1% |
| p05_maplemills_quote.pdf | $0.002215 | $0.000284 | 87.2% |
| p06_qtextile_quote.pdf | $0.002220 | $0.000290 | 86.9% |
| p07_longwharf_quote.pdf | $0.002226 | $0.000321 | 85.6% |
| p08_chapelst_email.eml | $0.002234 | $0.000310 | 86.1% |
| p09_westville_email.eml | $0.002237 | $0.000331 | 85.2% |
| p10_eastrock_email.eml | $0.002233 | $0.000320 | 85.7% |
| p11_yorkst_quote.html | $0.002247 | $0.000327 | 85.4% |
| p12_bluehen_quote.pdf | $0.002254 | $0.000315 | 86.0% |
| **Total (12 documents)** | **$0.026953** | **$0.005152** | **80.9%** |
| **Average per document** | **$0.002246** | **$0.000429** | |
| Average per document once the cache is warm (p02–p12) | $0.002245 | $0.000325 | 85.5% |

**Caching saved 80.9% across all 12 documents, and 85.5% per document once the handbook was in the cache.**

Caching changed the cost, not the answers. Each document got the same decision in both setups.

## 2. Real numbers vs. my Problem 2 estimate

| | Problem 2 estimate (handbook only) | Real (whole call) |
|---|---|---|
| Input tokens per call | 10,062 | about 10,760 on call 1 and 11,210 on call 2 |
| Calls per document | assumed 1 | **2** |
| Cost per call, without cache | $0.0010062 | $0.0011231 (+12%) |
| Cost per call, with cache (warm) | $0.0001006 | $0.0001627 |
| Saved | 89.9% | 80.9% overall, 85.5% once warm |

- **The handbook estimate was right.** About 10,760 tokens get cached on every call, and the handbook is 10,062 of them. The other ~700 are the agent's instructions (`prompts/prompt.md`), the tool descriptions and the answer format, which are also the same every time.
- **Each document takes 2 calls, not 1.** So the handbook is sent twice per document. Per document, the real cost is about double the Problem 2 per-call figure: $0.00225 vs. $0.0010 without cache.
- **The real saving is a bit lower than predicted (81–86% vs. 90%)** because each call also carries things the cache can't cover: the vendor document, the agent's answer and a small cache-write charge. Problem 2 only counted the handbook.

## 3. Projection: 1,000 documents a day for 30 days (30,000 documents)

| Setup | Cost per document | 30-day cost |
|---|---|---|
| Without cache | $0.002246 | **$67.38** |
| With cache (warm, measured p02–p12) | $0.000325 | **$9.76** |
| With cache, plus storing the handbook again each morning | | **~$9.80** |
| **Monthly saving with cache** | | **~$57.60 (about 85%)** |

At 1,000 documents a day (about one every 1.5 minutes during the day), the 30-minute cache stays warm, so the handbook would usually only need storing again once a day, after the overnight gap. Each time costs about $0.00125 extra, or about $0.04 a month. Even a worst case, where the cache expired after every 12 documents like in this test, would only be $12.88 a month.

## 4. What surprised me, and why it happens

1. **Each document costs two handbook sends, not one.** The agent talks to the model twice. On the first call the model only decides to open the document. On the second call it reads the document and gives the answer. The full handbook goes out both times, because the model has no memory between calls. Without caching, that doubles the bill. This is also why the very first document still saved 30%: its second call reused the handbook stored by its first call a few seconds earlier.

2. **The cache charges a fee to store things, even on "cached" calls.** Storing text in the cache costs 25% more than normal input ($0.125 vs. $0.10 per million). The first document paid that extra on the whole handbook, so it was the most expensive one with caching. After that, every call still stored the small new part, the vendor document, at that higher price. Those cache writes added up to 14,527 tokens. So caching isn't free: it pays off only because each stored handbook gets reused many times at a tenth of the price.

3. **"Without cache" can cost more than the plain price if you set it up the lazy way.** Before the real runs, I tested the default setting with two identical calls in a row. Both stored the whole handbook (10,326 tokens of cache writes each), and the second one did not reuse the first one's copy. The default setting tries to cache on its own, so a call that doesn't reuse the cache still pays the 25% storage fee for nothing. That's why I used "explicit" mode for the no-cache runs. It stores nothing, so those runs show zero cache tokens and cost exactly the plain input price, which makes the comparison fair.

4. **Almost all of the bill is input, not the answer.** Across all 24 calls per setup, the answers (output tokens) cost under $0.001. The handbook being sent over and over is what costs money, which is exactly what caching targets.

5. **Three documents got the wrong decision in both setups** (p02, p07, p12). Caching didn't cause it, since the answers were the same either way. I'll look at why in Problem 5.
