"""Problem 8: run the final defended agent on the 10 exam documents.

Run from hw6/:  python exam_run.py
Writes output/exam_results.json straight from the agent's answers (no hand edits).
"""

from __future__ import annotations

import json

from agent import ALL_DEFENSES, run
from tools import DATA_DIR, OUTPUT_DIR, TRAP_LOG

DOCS = sorted((DATA_DIR / "exam_docs").iterdir())


def main() -> None:
    if not TRAP_LOG.exists():
        TRAP_LOG.write_text("[]\n", encoding="utf-8")
    results = []
    for doc in DOCS:
        out = run(str(doc.relative_to(DATA_DIR.parent)), defenses=ALL_DEFENSES)
        a, u = out["answer"], out["usage"]
        trap_called = any(t["run_id"] == out["run_id"] for t in json.loads(TRAP_LOG.read_text()))
        results.append({
            "file": doc.name,
            "vendor": a["vendor"],
            "sku": a["sku"],
            "unit_price": a["unit_price"],
            "lead_time_days": a["lead_time_days"],
            "min_order": a["min_order"],
            "decision": a["decision"],
            "reason": a["reason"],
            "trap_tool_called": trap_called,
            "input_tokens": u["input_tokens"],
            "cached_tokens": u["cached_tokens"],
            "output_tokens": u["output_tokens"],
            "cost_usd": u["cost_usd"],
        })
        blocked = [b["tool"] for b in out["blocked_tool_requests"]]
        print(f"{doc.name:18} {a['vendor']:26} {a['sku']} ${a['unit_price']} {a['lead_time_days']}d "
              f"min {a['min_order']} -> {a['decision']:16} trap={trap_called} blocked={blocked}")
    (OUTPUT_DIR / "exam_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n",
                                                 encoding="utf-8")
    print(f"total ${sum(r['cost_usd'] for r in results):.6f}")


if __name__ == "__main__":
    main()
