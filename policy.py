"""Defense layer 2 (design): the purchasing decision is made by code, not by the model.

The model only reports the facts it read. This module reads the approved / removed vendor lists
and the catalogue max unit costs straight from data/shop_handbook.md and applies the four
purchasing checks (handbook section 4). A document can change what the model reads, but it
cannot talk its way past these rules, and the reason sentence is written here, so no link or
other text from the document can ride along in it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

HANDBOOK = Path(__file__).resolve().parent / "data" / "shop_handbook.md"
MAX_LEAD_DAYS = 21
MAX_MIN_ORDER = 600


def _norm(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _section(text: str, number: int) -> str:
    m = re.search(rf"^## {number}\..*?(?=^## \d+\.|\Z)", text, re.S | re.M)
    return m.group(0) if m else ""


def _rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows[1:]  # drop the header row


@lru_cache(maxsize=1)
def handbook_rules() -> dict:
    text = HANDBOOK.read_text(encoding="utf-8")
    approved = {_norm(r[1]): r[1] for r in _rows(_section(text, 5))}
    removed = {_norm(r[0]): (r[0], r[1]) for r in _rows(_section(text, 6))}
    catalogue = {}
    for r in _rows(_section(text, 9)):
        m = re.search(r"\$([\d,]+\.\d+)", r[4])
        if m:
            catalogue[r[0].upper()] = {"item": r[1], "max_unit_cost": float(m.group(1).replace(",", ""))}
    return {"approved": approved, "removed": removed, "catalogue": catalogue}


# Labeled lines in a quote, e.g. "Lead time: 26 business days" or "Unit price</th><td>$21.80".
_GAP = r"(?:[^\w$<]|<[^>]{0,30}>){0,40}?"   # punctuation, spaces, or HTML tags between label and value
_PATTERNS = {
    "sku": re.compile(r"\b(CC-[A-Z]{2}-\d{3})\b"),
    "unit_price": re.compile(r"unit\s+price" + _GAP + r"\$\s*([\d,]+(?:\.\d+)?)", re.I),
    "lead_time_days": re.compile(r"lead\s+time" + _GAP + r"(\d+)\s*(?:business\s+|calendar\s+)?days?", re.I),
    "min_order": re.compile(r"minimum\s+order" + _GAP + r"([\d,]+)\s*units?", re.I),
}


def fill_missing(answer: dict, doc_text: str) -> dict:
    """Backstop for a model that leaves a field blank: take the FIRST labeled value in the text the
    model was given. Only fills fields that are None; never changes a value the model reported."""
    filled = {}
    for field, pattern in _PATTERNS.items():
        if answer.get(field) is None and doc_text:
            m = pattern.search(doc_text)
            if m:
                raw = m.group(1).replace(",", "")
                filled[field] = raw if field == "sku" else float(raw) if field == "unit_price" else int(raw)
    return filled


def decide(vendor: str | None, sku: str | None, unit_price: float | None,
           lead_time_days: int | None, min_order: int | None) -> tuple[str, str, dict]:
    """Apply the four purchasing checks. Returns (decision, one-sentence reason, check details)."""
    rules = handbook_rules()
    v = _norm(vendor)
    fails: list[str] = []
    checks: dict[str, str] = {}

    # 1. approved vendor
    if v in rules["removed"]:
        name, status = rules["removed"][v]
        checks["approved_vendor"] = "fail"
        fails.append(f"{name} is on the removed/pending vendor list")
    elif v in rules["approved"]:
        checks["approved_vendor"] = "pass"
    else:
        checks["approved_vendor"] = "fail"
        fails.append(f"{vendor or 'the vendor'} is not on the approved vendor list")

    # 2. price at or below the catalogue max unit cost
    item = rules["catalogue"].get((sku or "").upper())
    if unit_price is None:
        checks["price"] = "fail"
        fails.append("the unit price is unknown")
    elif item is None:
        checks["price"] = "fail"
        fails.append(f"SKU {sku or '(none)'} is not in the catalogue, so the price cannot be checked")
    elif unit_price <= item["max_unit_cost"]:
        checks["price"] = "pass"
    else:
        checks["price"] = "fail"
        fails.append(f"the ${unit_price:.2f} unit price is above the ${item['max_unit_cost']:.2f} max unit cost for {sku}")

    # 3. lead time
    if lead_time_days is None:
        checks["lead_time"] = "fail"
        fails.append("the lead time is unknown")
    elif lead_time_days <= MAX_LEAD_DAYS:
        checks["lead_time"] = "pass"
    else:
        checks["lead_time"] = "fail"
        fails.append(f"the {lead_time_days}-day lead time is over the {MAX_LEAD_DAYS}-day limit")

    # 4. minimum order
    if min_order is None:
        checks["min_order"] = "fail"
        fails.append("the minimum order is unknown")
    elif min_order <= MAX_MIN_ORDER:
        checks["min_order"] = "pass"
    else:
        checks["min_order"] = "fail"
        fails.append(f"the {min_order}-unit minimum order is over the {MAX_MIN_ORDER}-unit limit")

    if not fails:
        reason = (f"All four checks pass: {rules['approved'][v]} is approved, ${unit_price:.2f} is within the "
                  f"${item['max_unit_cost']:.2f} max for {sku}, {lead_time_days} days is within {MAX_LEAD_DAYS}, "
                  f"and {min_order} units is within {MAX_MIN_ORDER}.")
        return "recommend", reason, checks
    joined = fails[0] if len(fails) == 1 else ", ".join(fails[:-1]) + " and " + fails[-1]
    return "do_not_recommend", f"Do not recommend because {joined}.", checks
