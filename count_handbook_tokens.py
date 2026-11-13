"""Problem 2: count the handbook's tokens two ways.

1. Offline with tiktoken's o200k_base encoding (the GPT-4o / GPT-5 family tokenizer).
2. Online: send the handbook to gpt-6-luna through Portkey and read the input token count
   the API reports, minus a baseline call with the same tiny question and no handbook.

Run from hw6/:  python count_handbook_tokens.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
HANDBOOK = (ROOT / "data" / "shop_handbook.md").read_text(encoding="utf-8")
MODEL_NAME = "gpt-6-luna"  # the only model allowed in this homework
QUESTION = "Reply with the single word OK."

for env_file in (ROOT / ".env", ROOT.parent / ".env", ROOT.parent.parent / ".env"):
    load_dotenv(env_file)


def offline_count() -> int:
    return len(tiktoken.get_encoding("o200k_base").encode(HANDBOOK))


def api_input_tokens(client: OpenAI, with_handbook: bool) -> dict:
    messages = [{"role": "user", "content": QUESTION}]
    if with_handbook:
        messages.insert(0, {"role": "system", "content": HANDBOOK})
    resp = client.responses.create(model=MODEL_NAME, input=messages,
                                   max_output_tokens=300, reasoning={"effort": "low"})
    u = resp.usage
    return {"model": resp.model, "input_tokens": u.input_tokens,
            "cached_tokens": u.input_tokens_details.cached_tokens,
            "output_tokens": u.output_tokens}


def main() -> None:
    result = {"chars": len(HANDBOOK), "words": len(HANDBOOK.split()),
              "tiktoken_o200k_base": offline_count()}
    key = os.environ["PORTKEY_API_KEY"]
    client = OpenAI(api_key=key, base_url="https://api.portkey.ai/v1",
                    default_headers={"x-portkey-api-key": key})
    result["api_baseline_no_handbook"] = api_input_tokens(client, with_handbook=False)
    result["api_with_handbook"] = api_input_tokens(client, with_handbook=True)
    result["api_handbook_tokens"] = (result["api_with_handbook"]["input_tokens"]
                                     - result["api_baseline_no_handbook"]["input_tokens"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
