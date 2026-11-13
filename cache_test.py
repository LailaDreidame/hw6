"""Problem 4: run all 12 practice documents with and without the prompt cache.

Run from hw6/:  python cache_test.py
Saves every model call to output/cache_test.json and prints a summary.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from agent import CACHE_SETUPS, NO_DEFENSES, run
from tools import DATA_DIR, OUTPUT_DIR, TRAP_LOG

DOCS = sorted((DATA_DIR / "practice_docs").iterdir())
OUT = OUTPUT_DIR / "cache_test.json"
SETUPS = ["without_cache", "with_cache"]


def main() -> None:
    if not TRAP_LOG.exists():
        TRAP_LOG.write_text("[]\n", encoding="utf-8")
    key = {k["file"]: k for k in json.loads((DATA_DIR / "practice_key.json").read_text())}
    calls = []
    for setup in SETUPS:
        assert setup in CACHE_SETUPS
        for doc in DOCS:
            out = run(str(doc.relative_to(DATA_DIR.parent)), setup, NO_DEFENSES)
            correct = out["answer"]["decision"] == key[doc.name]["decision"]
            for c in out["calls"]:
                calls.append({"setup": setup, "document": doc.name, **c})
            u = out["usage"]
            print(f"{setup:14} {doc.name:28} in={u['input_tokens']:6} cached={u['cached_tokens']:6} "
                  f"write={u['cache_write_tokens']:6} out={u['output_tokens']:4} ${u['cost_usd']:.6f} "
                  f"decision_ok={correct}")
    OUT.write_text(json.dumps(calls, indent=2) + "\n", encoding="utf-8")

    totals = defaultdict(lambda: defaultdict(float))
    for c in calls:
        t = totals[c["setup"]]
        for f in ("input_tokens", "cached_tokens", "cache_write_tokens", "output_tokens", "cost_usd"):
            t[f] += c[f]
        t["calls"] += 1
    print(json.dumps({s: dict(t) for s, t in totals.items()}, indent=2))


if __name__ == "__main__":
    main()
