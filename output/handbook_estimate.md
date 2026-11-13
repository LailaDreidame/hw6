# Handbook estimate (Problem 2)

How much `data/shop_handbook.md` costs, since the agent sends the whole handbook to gpt-6-luna on every call.

## Token count: about 10,062 tokens

| Method | Tokens |
|---|---|
| Offline: tiktoken `o200k_base` tokenizer | 10,058 |
| API: gpt-6-luna input tokens with the handbook minus without it | **10,062** |

**How I got it** (script: `count_handbook_tokens.py`):

1. **Offline count.** I counted the handbook's tokens with the `o200k_base` tokenizer in OpenAI's `tiktoken` library and got 10,058. The handbook is 28,903 characters and 6,127 words, so that's about 2.9 characters per token. Tables, dashes and SKU codes break into many small tokens.
2. **API check.** I made two tiny calls to gpt-6-luna through Portkey with the same question ("Reply with the single word OK."):
   - without the handbook, the API reported **13** input tokens;
   - with the handbook as the system message, it reported **10,075** input tokens.
   - 10,075 − 13 = **10,062 tokens** for the handbook. That's 4 more than the offline count because of the system-message wrapper.

The cost math below uses the API number, **10,062 tokens**, because that's what the API bills. Neither call had any cached tokens. (Portkey reports the model as `gpt-6-luna-global`, the name of gpt-6-luna's global deployment.)

## Prices (from `data/prices.json`, gpt-6-luna, per 1M tokens)

| Token type | $ per 1M tokens | $ per token |
|---|---|---|
| Input (not cached) | $0.10 | $0.0000001 |
| Cached input (cache hit) | $0.01 | $0.00000001 |
| Cache write (first time a prefix is stored) | $0.125 | $0.000000125 |
| Output | $0.50 | (not part of the handbook) |

## Cost of the handbook alone

These figures cover only the handbook's input tokens. The vendor document, the question and the model's answer cost extra and are measured in Problem 4.

### One call

| Setup | Math | Cost |
|---|---|---|
| Without cache | 10,062 × $0.10 / 1,000,000 | **$0.0010062** (~0.10¢) |
| With cache, first call (cache write) | 10,062 × $0.125 / 1,000,000 | **$0.00125775** (~0.13¢) |
| With cache, later call (cache hit) | 10,062 × $0.01 / 1,000,000 | **$0.00010062** (~0.01¢) |

### 1,000 calls

| Setup | Math | Cost |
|---|---|---|
| Without cache | 1,000 × $0.0010062 | **$1.0062** |
| With cache (1 write + 999 hits) | $0.00125775 + 999 × $0.00010062 = $0.00125775 + $0.10051938 | **$0.1018** |

**Caching saves $0.9044 per 1,000 calls**, or about **89.9%** ($0.1018 vs. $1.0062). A cache hit costs one tenth of the normal input price. The first write costs 25% more than a normal call, but only once.

## Assumptions to check in Problem 4

- **The handbook comes first in every call, unchanged.** Caching only matches an identical prefix, so the handbook has to go before the vendor document.
- **The cache stays warm.** If calls are far enough apart for the cache to expire, the handbook gets written again at $0.125/1M. Each extra write adds about $0.0011 compared with a cache hit.
- **The whole handbook is cached.** OpenAI caches in 128-token steps, so a few tokens at the end of the cached part may still be billed at the full input price.
