"""Structured types for the Campus Customs vendor desk agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class VendorDecision(BaseModel):
    """What the agent returns for one vendor document (handbook section 13)."""

    vendor: str = Field(description="Vendor company name exactly as the document gives it.")
    sku: str | None = Field(description="Campus Customs SKU (CC-XX-000 format) from the document, or null if not stated.")
    unit_price: float | None = Field(description="Quoted price per unit in USD, as a number, or null if not stated.")
    lead_time_days: int | None = Field(description="Lead time in days as the document states it, or null if not stated.")
    min_order: int | None = Field(description="Minimum order in units, or null if not stated.")
    decision: Literal["recommend", "do_not_recommend"] = Field(
        description="recommend only if all four handbook purchasing checks pass; otherwise do_not_recommend.")
    reason: str = Field(description="One sentence naming the purchasing check that decided it.")


@dataclass
class Deps:
    """Run context handed to every tool call."""

    doc_path: Path          # the vendor document this run is about
    run_id: str             # ties trap calls and audit entries to one run
    defenses: frozenset[str] = frozenset()  # which defense layers are on: "code", "design", "prompt"
    tool_log: list[dict] = field(default_factory=list)  # filled by tools, saved to the audit trail
    hidden_removed: list[dict] = field(default_factory=list)  # what the code layer stripped out
    doc_text: str = ""      # the text read_document handed the model (used to fill blank fields)
