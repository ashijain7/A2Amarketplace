"""
Generate fictional personas via Claude.

This is our "10-minute interview" step. Instead of interviewing real
humans like Project Deal did, we ask Claude to invent a coherent set
of fictional people with overlapping wants and sells.

Usage:
    python -m project_deal_poc.interview --n 6
"""

import argparse
import json
from pathlib import Path

from . import config
from .llm import call_llm, parse_json_array_response


def generate_personas(n: int = 6) -> list[dict]:
    """Call Claude to generate n personas. Returns a list of dicts."""
    system_prompt = config.INTERVIEWER_PROMPT_PATH.read_text().format(n=n)
    user_msg = f"Generate exactly {n} personas now. Return only the JSON array."

    print(f"[interview] Asking {config.INTERVIEWER_MODEL} to generate {n} personas...")
    raw = call_llm(
        system=system_prompt,
        user=user_msg,
        model=config.INTERVIEWER_MODEL,
        temperature=0.9,        # higher temp for more variety
        max_tokens=3000,        # need room for full array
    )

    personas = parse_json_array_response(raw)

    if not isinstance(personas, list):
        raise ValueError(f"Expected a JSON array, got {type(personas).__name__}")
    if len(personas) != n:
        print(f"[interview] Warning: asked for {n} personas, got {len(personas)}")

    return personas


def validate_personas(personas: list[dict]) -> list[str]:
    """Light schema check. Returns a list of warnings (empty if all good)."""
    warnings = []
    seen_ids = set()
    seen_names = set()

    for i, p in enumerate(personas):
        if "name" not in p:
            warnings.append(f"Persona {i}: missing 'name'")
            continue
        if p["name"] in seen_names:
            warnings.append(f"Persona {i} ({p['name']}): duplicate name")
        seen_names.add(p["name"])

        for item in p.get("items_to_sell", []):
            iid = item.get("item_id")
            if not iid:
                warnings.append(f"{p['name']}: a sell item has no item_id")
            elif iid in seen_ids:
                warnings.append(f"{p['name']}: duplicate item_id '{iid}'")
            else:
                seen_ids.add(iid)
            if "floor_price" not in item:
                warnings.append(f"{p['name']}: sell item '{iid}' has no floor_price")

        for want in p.get("items_to_buy", []):
            wid = want.get("want_id")
            if not wid:
                warnings.append(f"{p['name']}: a buy item has no want_id")
            elif wid in seen_ids:
                warnings.append(f"{p['name']}: duplicate want_id '{wid}'")
            else:
                seen_ids.add(wid)
            if "ceiling_price" not in want:
                warnings.append(f"{p['name']}: buy item '{wid}' has no ceiling_price")

    return warnings


def main():
    parser = argparse.ArgumentParser(description="Generate marketplace personas.")
    parser.add_argument("--n", type=int, default=config.DEFAULT_NUM_PERSONAS)
    parser.add_argument("--out", type=Path, default=config.PERSONAS_PATH)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    personas = generate_personas(n=args.n)
    warnings = validate_personas(personas)

    args.out.write_text(json.dumps(personas, indent=2))
    print(f"[interview] Wrote {len(personas)} personas to {args.out}")

    if warnings:
        print("[interview] Schema warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("[interview] All personas passed schema check.")

    # Quick human-readable summary
    print("\n[interview] Summary:")
    for p in personas:
        sells = ", ".join(i["name"][:30] for i in p.get("items_to_sell", []))
        buys = ", ".join(w["description"][:30] for w in p.get("items_to_buy", []))
        print(f"  {p['name']:12} sells: {sells}")
        print(f"  {'':12} buys:  {buys}")


if __name__ == "__main__":
    main()
