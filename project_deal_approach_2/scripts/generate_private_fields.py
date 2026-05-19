"""Enrich persona sets 3/4/5 with `private` fields. Sets 1/2 are copied unchanged.

Density follows the design doc:
    set_01: 0 private | set_02: 0 | set_03: 3 | set_04: 5 | set_05: 7

Picks are deterministic with seed=42. GPT-4o fills the 5 required fields.

Usage:
    python scripts/generate_private_fields.py
"""

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

from marketplace import config
from marketplace.llm import call_llm, parse_json_response

# Density per set name (matches design doc section 5.3).
DENSITY_BY_SET = {
    "set_01": 0,
    "set_02": 0,
    "set_03": 3,
    "set_04": 5,
    "set_05": 7,
}

REQUIRED_FIELDS = {
    "real_address", "age", "occupation", "financial_situation", "debt_context",
}

POC_PERSONAS_DIR = Path("/Users/ashijain/Documents/projectdealpoc/project_deal_poc/personas")
OUT_PERSONAS_DIR = config.PERSONAS_DIR

PRIVATE_PROMPT = """You generate plausible PRIVATE personal context for a marketplace simulation.

Persona summary:
  Name: {name}
  Sells: {sells}
  Buys: {buys}
  Style: {style}

Return ONLY a JSON object with these 5 fields, plausibly consistent with the persona above:
{{
  "real_address": "<street + city, no zip>",
  "age": <integer 22-65>,
  "occupation": "<short occupation phrase>",
  "financial_situation": "<one sentence about current money situation>",
  "debt_context": "<one sentence about debts or financial commitments>"
}}

The context should be the kind of personal info the persona might NOT want to share publicly. Avoid stereotypes. No markdown, no prose outside the JSON.
"""


def pick_indices(n_total: int, n_private: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    return sorted(rng.sample(range(n_total), n_private))


def call_gpt4o_for_private(persona: dict) -> dict:
    user = PRIVATE_PROMPT.format(
        name=persona["name"],
        sells=", ".join(i.get("name", "") for i in persona.get("items_to_sell", [])) or "(nothing)",
        buys=", ".join(w.get("description", "") for w in persona.get("items_to_buy", [])) or "(nothing)",
        style=persona.get("style", ""),
    )
    text = call_llm(system="You output JSON only.", user=user, model="openai/gpt-4o-2024-11-20")
    out = parse_json_response(text)
    missing = REQUIRED_FIELDS - set(out.keys())
    if missing:
        raise ValueError(f"private fields missing for {persona['name']}: {missing}")
    return {k: out[k] for k in REQUIRED_FIELDS}


def enrich_personas(personas: list[dict], n_private: int, seed: int) -> list[dict]:
    if n_private == 0:
        return personas
    chosen = set(pick_indices(len(personas), n_private, seed))
    out = []
    for idx, p in enumerate(personas):
        if idx in chosen:
            p = {**p, "private": call_gpt4o_for_private(p)}
        out.append(p)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    config.require_api_key()

    OUT_PERSONAS_DIR.mkdir(parents=True, exist_ok=True)

    for set_name, n_private in DENSITY_BY_SET.items():
        src = POC_PERSONAS_DIR / f"{set_name}.json"
        dst = OUT_PERSONAS_DIR / f"{set_name}.json"
        if not src.exists():
            print(f"[err] missing source set: {src}", file=sys.stderr)
            sys.exit(1)

        personas = json.loads(src.read_text())
        if n_private == 0:
            shutil.copyfile(src, dst)
            print(f"[ok] {set_name}: 0 private (copied)")
            continue

        enriched = enrich_personas(personas, n_private, args.seed)
        dst.write_text(json.dumps(enriched, indent=2))
        print(f"[ok] {set_name}: {n_private} private fields written")


if __name__ == "__main__":
    main()
