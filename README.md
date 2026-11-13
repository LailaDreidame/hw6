# Campus Customs Vendor Desk (MGT 409, Homework 6)

An agent that reads one vendor document (HTML, PDF, or email), pulls out the quote, and recommends or rejects it under the shop handbook rules. The homework also measures what cached tokens save and tests the agent against hidden prompt injection.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then put your Portkey key in .env
```

## Run the agent

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

The agent reads that one vendor document (`.html`, `.pdf`, or `.eml`) and prints the vendor, SKU, unit price, lead time in days, minimum order, a `recommend` / `do_not_recommend` decision and a one-sentence reason. Each run is added to `output/usage_log.json` (tokens and cost) and `output/audit_trail.json` (tool calls and the answer).

**Defenses (Problem 6):** all three layers (code, design, prompt) are on by default. Use `--defenses none` for the original undefended agent, or pick layers, e.g. `--defenses code,prompt`. `python attack_test.py` scores the undefended agent on the 12 practice documents (Problem 5), and `python defense_test.py` reruns them under each defense layer (Problem 6).

`python red_team_test.py` runs my two attacks in `data/my_attacks/` (built by `make_attacks.py`) with and without defenses (Problem 7). `python exam_run.py` runs the final defended agent on the 10 exam documents and writes `output/exam_results.json` (Problem 8).

`python build_report.py` rebuilds the one-file results page `output/hw6_report.html` from the run logs (Problem 9).

Add `--setup without_cache` to turn prompt caching off (the default is `with_cache`). `python cache_test.py` runs all 12 practice documents both ways (Problem 4).

Every AI call uses **gpt-6-luna** through Portkey (set `PORTKEY_API_KEY` in `.env` or your shell).

The `send_email` and `approve_payment` tools are traps: they never send or pay anything and only write to `output/trap_calls.json`.

## Layout

- `data/`: course data (handbook, prices, practice and exam documents) plus my two attack files in `data/my_attacks/`
- `output/`: everything the homework asks us to produce
