"""Problem 6: rerun all 12 practice documents with the defenses on, and measure each layer.

Run from hw6/:  python defense_test.py
  - output/defense_results.json : all three layers on (same shape as Problem 5, plus tokens and dollars)
  - output/defense_layers.json  : every document under each config (none, code, design, prompt, all),
                                  used to see what each layer catches and what it costs
"""

from __future__ import annotations

import json

from agent import ALL_DEFENSES, NO_DEFENSES
from attack_test import run_all
from tools import OUTPUT_DIR

CONFIGS = {
    "none": NO_DEFENSES,
    "code": frozenset({"code"}),
    "design": frozenset({"design"}),
    "prompt": frozenset({"prompt"}),
    "all": ALL_DEFENSES,
}


def main() -> None:
    tmp = OUTPUT_DIR / "_layer_run.json"
    layers = {}
    for name, defenses in CONFIGS.items():
        out_path = OUTPUT_DIR / "defense_results.json" if name == "all" else tmp
        layers[name] = run_all(out_path, name, {"defenses": defenses})
    tmp.unlink(missing_ok=True)
    (OUTPUT_DIR / "defense_layers.json").write_text(json.dumps(layers, indent=2, ensure_ascii=False) + "\n",
                                                    encoding="utf-8")
    print("\nconfig    fooled  avg_in   avg_out  avg_$")
    for name, rows in layers.items():
        n = len(rows)
        print(f"{name:8} {sum(r['fooled'] for r in rows):3}/{n}  {sum(r['input_tokens'] for r in rows)/n:8.0f} "
              f"{sum(r['output_tokens'] for r in rows)/n:7.1f}  {sum(r['cost_usd'] for r in rows)/n:.6f}")


if __name__ == "__main__":
    main()
