"""Campus Customs vendor desk agent (entry point).

Run from hw6/:
    python agent.py --doc data/practice_docs/p01_bluehen_quote.html                    # all defenses on
    python agent.py --doc data/practice_docs/p01_bluehen_quote.html --defenses none    # Problem 3 agent, no defenses
    python agent.py --doc ... --defenses code,prompt                                   # any mix of layers

Reads one vendor document, returns the key facts and a recommend / do_not_recommend decision,
and appends the run to output/usage_log.json and output/audit_trail.json.

Defense layers (Problem 6):
  code   - sanitize.py: the model only sees the text a person would see (hidden text removed).
  design - policy.py decides recommend / do_not_recommend from the handbook rules (the model only
           reports facts); send_email / approve_payment need a human sign-off, so a model request
           to use them is blocked and logged instead of run; read_document can only open this run's file.
  prompt - the safety rules in prompts/prompt.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import (Agent, DeferredToolRequests, DeferredToolResults, NativeOutput, Tool,  # noqa: E402
                         ToolDenied)
from pydantic_ai.messages import ModelResponse, ToolCallPart  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import RequestUsage, RunUsage, UsageLimits  # noqa: E402

from models import Deps, VendorDecision  # noqa: E402
from policy import decide, fill_missing  # noqa: E402
from tools import (ALL_TOOLS, DATA_DIR, OUTPUT_DIR, ROOT, TRAP_LOG, append_json, approve_payment,  # noqa: E402
                   now, read_document, send_email)

# --- the only model allowed in this homework --------------------------------
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

PROMPT_PATH = ROOT / "prompts" / "prompt.md"
HANDBOOK_PATH = DATA_DIR / "shop_handbook.md"
PRICES = json.loads((DATA_DIR / "prices.json").read_text(encoding="utf-8"))[MODEL_NAME]
USAGE_LOG = OUTPUT_DIR / "usage_log.json"
AUDIT_TRAIL = OUTPUT_DIR / "audit_trail.json"

MODEL_SETTINGS = OpenAIResponsesModelSettings(
    max_tokens=8_000,                 # reasoning tokens count toward this cap
    openai_reasoning_effort="low",
)
RUN_LIMITS = UsageLimits(request_limit=6, tool_calls_limit=6)

# --- prompt cache setups (Problem 4) ----------------------------------------
# with_cache: the prompt + handbook prefix is marked for caching and every call shares one
#   prompt_cache_key, so OpenAI routes them to the same cache and reuses the handbook.
# without_cache: "explicit" mode with no cache breakpoints, so OpenAI neither writes nor reads
#   the cache (the API then reports 0 cached and 0 cache-write tokens).
CACHE_SETUPS: dict[str, OpenAIResponsesModelSettings] = {
    "with_cache": OpenAIResponsesModelSettings(
        openai_prompt_cache_key="campus-customs-vendor-desk",
        openai_prompt_cache_options={"mode": "implicit", "ttl": "30m"},
        openai_cache_instructions=True,
    ),
    "without_cache": OpenAIResponsesModelSettings(
        openai_prompt_cache_options={"mode": "explicit"},
    ),
}
DEFAULT_SETUP = "with_cache"

# --- defense layers (Problem 6) ---------------------------------------------
ALL_DEFENSES = frozenset({"code", "design", "prompt"})
NO_DEFENSES: frozenset[str] = frozenset()
SAFETY_BLOCK = re.compile(r"<!-- SAFETY RULES START.*?<!-- SAFETY RULES END -->\n\n", re.S)
HUMAN_SIGNOFF_MSG = ("Blocked: this tool needs a human sign-off and cannot be used while reviewing a "
                     "vendor document. Do not try again; finish the review.")

for env_file in (ROOT / ".env", ROOT.parent / ".env", ROOT.parent.parent / ".env"):
    load_dotenv(env_file)


def parse_defenses(text: str) -> frozenset[str]:
    text = text.strip().lower()
    if text == "all":
        return ALL_DEFENSES
    if text in ("none", ""):
        return NO_DEFENSES
    layers = frozenset(p.strip() for p in text.split(","))
    unknown = layers - ALL_DEFENSES
    if unknown:
        raise ValueError(f"Unknown defense layer(s): {sorted(unknown)}. Use code, design, prompt, all, or none.")
    return layers


def label(defenses: frozenset[str]) -> str:
    return "none" if not defenses else "all" if defenses == ALL_DEFENSES else "+".join(sorted(defenses))


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey."""
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise SystemExit("PORTKEY_API_KEY is not set (shell environment or a .env file).")
    # The class Portkey config has a response cache that replays the saved answer to an identical
    # request (x-portkey-cache-status: HIT). Force a fresh call so every run really asks gpt-6-luna.
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL,
                         default_headers={"x-portkey-api-key": key, "x-portkey-cache-force-refresh": "true"})
    model = OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
    assert model.model_name == MODEL_NAME, "Only gpt-6-luna is allowed."
    return model


def instructions(defenses: frozenset[str] = ALL_DEFENSES) -> str:
    """Agent prompt + the full shop handbook. Identical on every call (so it can be cached).
    Without the prompt layer, the safety rules block is cut out of prompts/prompt.md."""
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    if "prompt" not in defenses:
        prompt = SAFETY_BLOCK.sub("", prompt)
    return prompt + "\n" + HANDBOOK_PATH.read_text(encoding="utf-8")


def build_agent(setup: str = DEFAULT_SETUP, defenses: frozenset[str] = ALL_DEFENSES) -> Agent:
    settings = OpenAIResponsesModelSettings(**MODEL_SETTINGS, **CACHE_SETUPS[setup])
    if "design" in defenses:
        # Trap tools stay in the system but need a human sign-off: a model request is paused, not run.
        tools = [Tool(read_document), Tool(send_email, requires_approval=True),
                 Tool(approve_payment, requires_approval=True)]
        output_type = [NativeOutput(VendorDecision), DeferredToolRequests]
    else:
        tools = ALL_TOOLS
        output_type = NativeOutput(VendorDecision)
    return Agent(build_model(), deps_type=Deps, output_type=output_type,
                 instructions=instructions(defenses), tools=tools, model_settings=settings)


def cost_usd(u: RunUsage | RequestUsage) -> float:
    """Dollar cost from prices.json: uncached input, cached input, cache writes, output."""
    uncached = u.input_tokens - u.cache_read_tokens - u.cache_write_tokens
    return round((uncached * PRICES["input_per_1m"]
                  + u.cache_read_tokens * PRICES["cached_input_per_1m"]
                  + u.cache_write_tokens * PRICES["cache_write_per_1m"]
                  + u.output_tokens * PRICES["output_per_1m"]) / 1_000_000, 8)


def usage_record(u: RunUsage) -> dict:
    return {"requests": u.requests, "input_tokens": u.input_tokens,
            "cached_tokens": u.cache_read_tokens, "cache_write_tokens": u.cache_write_tokens,
            "output_tokens": u.output_tokens, "reasoning_tokens": u.output_reasoning_tokens,
            "cost_usd": cost_usd(u)}


def call_records(messages) -> list[dict]:
    """One record per model call, with every token count the API reported for it."""
    calls = []
    for i, m in enumerate(r for r in messages if isinstance(r, ModelResponse)):
        u = m.usage
        calls.append({"call": i + 1, "model_reported": m.model_name,
                      "input_tokens": u.input_tokens, "cached_tokens": u.cache_read_tokens,
                      "cache_write_tokens": u.cache_write_tokens, "output_tokens": u.output_tokens,
                      "reasoning_tokens": u.output_reasoning_tokens, "details": dict(u.details),
                      "cost_usd": cost_usd(u)})
    return calls


def models_reported(messages) -> list[str]:
    return sorted({m.model_name for m in messages if isinstance(m, ModelResponse) and m.model_name})


def run(doc: str, setup: str = DEFAULT_SETUP, defenses: frozenset[str] = ALL_DEFENSES) -> dict:
    doc_path = Path(doc)
    run_id = uuid.uuid4().hex[:8]
    deps = Deps(doc_path=doc_path, run_id=run_id, defenses=frozenset(defenses))
    agent = build_agent(setup, deps.defenses)
    prompt = f"Review this vendor document: {doc}"

    result = agent.run_sync(prompt, deps=deps, usage_limits=RUN_LIMITS)
    blocked: list[dict] = []
    for _ in range(3):  # design layer: deny every trap-tool request, then let the model finish
        if not isinstance(result.output, DeferredToolRequests):
            break
        for call in result.output.approvals:
            blocked.append({"tool": call.tool_name, "arguments": call.args_as_dict()})
        denials = DeferredToolResults(
            approvals={c.tool_call_id: ToolDenied(HUMAN_SIGNOFF_MSG) for c in result.output.approvals})
        result = agent.run_sync(message_history=result.all_messages(), deferred_tool_results=denials,
                                deps=deps, usage_limits=RUN_LIMITS, usage=result.usage)
    if isinstance(result.output, DeferredToolRequests):
        raise RuntimeError("The model kept asking for blocked tools; no answer produced.")

    model_answer = result.output.model_dump()
    answer = dict(model_answer)
    checks = None
    filled: dict = {}
    if "design" in deps.defenses:
        # Design layer: fill any blank field from the document's own labeled line (never overrides),
        # then code applies the handbook rules to the facts and writes the reason.
        filled = fill_missing(answer, deps.doc_text)
        answer.update(filled)
        answer["decision"], answer["reason"], checks = decide(
            answer["vendor"], answer["sku"], answer["unit_price"], answer["lead_time_days"], answer["min_order"])

    usage = usage_record(result.usage)
    messages = result.all_messages()
    calls = call_records(messages)
    tools_called = [p.tool_name for m in messages if isinstance(m, ModelResponse)
                    for p in m.parts if isinstance(p, ToolCallPart)]
    time = now()

    append_json(USAGE_LOG, {"run_id": run_id, "document": doc_path.name, "time": time, "setup": setup,
                            "defenses": label(deps.defenses), "model": MODEL_NAME,
                            "models_reported": models_reported(messages), **usage})
    audit = {"run_id": run_id, "document": doc_path.name, "time": time, "defenses": label(deps.defenses),
             "tool_calls": deps.tool_log, "tools_called_in_order": tools_called}
    if "code" in deps.defenses:
        audit["hidden_content_removed"] = deps.hidden_removed
    if "design" in deps.defenses:
        audit["blocked_tool_requests"] = blocked
        audit["model_answer"] = model_answer
        audit["filled_from_document"] = filled
        audit["rule_checks"] = checks
    audit["final_answer"] = answer
    append_json(AUDIT_TRAIL, audit)
    return {"document": doc_path.name, "run_id": run_id, "setup": setup, "defenses": label(deps.defenses),
            "answer": answer, "model_answer": model_answer, "blocked_tool_requests": blocked,
            "hidden_removed": deps.hidden_removed, "usage": usage, "calls": calls}


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Customs vendor desk agent")
    parser.add_argument("--doc", required=True, help="path to one vendor document (.html, .pdf, .eml)")
    parser.add_argument("--setup", choices=sorted(CACHE_SETUPS), default=DEFAULT_SETUP,
                        help="prompt cache setup (default: with_cache)")
    parser.add_argument("--defenses", default="all",
                        help="defense layers: all (default), none, or a list like code,design,prompt")
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(exist_ok=True)
    if not TRAP_LOG.exists():
        TRAP_LOG.write_text("[]\n", encoding="utf-8")
    out = run(args.doc, args.setup, parse_defenses(args.defenses))
    for key in ("calls", "model_answer", "hidden_removed"):
        out.pop(key)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
