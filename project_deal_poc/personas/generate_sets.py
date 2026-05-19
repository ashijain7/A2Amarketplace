"""
Generate frozen persona sets for reproducible experiments.

Run once to create sets 01-05. All experiments should use these fixed sets.

Usage:
    python -m project_deal_poc.personas.generate_sets

Generates 5 independent sets of 10 personas each. Each set uses a different
random seed so the LLM produces a meaningfully different cast of characters.
The actual seller/buyer mix in each set is determined by the LLM — review
each set after generation and regenerate any that look too easy (every buyer
perfectly matched to a seller) or too sparse.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from project_deal_poc import config
from project_deal_poc.interview import generate_personas, validate_personas

SETS = [
    {"set_id": "01"},
    {"set_id": "02"},
    {"set_id": "03"},
    {"set_id": "04"},
    {"set_id": "05"},
]

SETS_DIR = config.PERSONAS_DIR
N_PERSONAS = 10


def generate_set(set_def: dict) -> list[dict]:
    """Generate one persona set of N_PERSONAS agents. Returns validated personas."""
    print(f"\n[generate_sets] Generating set_{set_def['set_id']} ({N_PERSONAS} agents)...")

    personas = generate_personas(n=N_PERSONAS)
    warnings = validate_personas(personas)
    if warnings:
        print(f"[generate_sets] Warnings for set_{set_def['set_id']}:")
        for w in warnings:
            print(f"  - {w}")
    return personas


def main():
    config.require_api_key()
    SETS_DIR.mkdir(parents=True, exist_ok=True)

    for set_def in SETS:
        out_path = SETS_DIR / f"set_{set_def['set_id']}.json"
        if out_path.exists():
            print(f"[generate_sets] {out_path.name} already exists — skipping. Delete to regenerate.")
            continue
        personas = generate_set(set_def)
        out_path.write_text(json.dumps(personas, indent=2))
        print(f"[generate_sets] Wrote {len(personas)} personas to {out_path}")

    print("\n[generate_sets] All sets generated.")
    print(f"Use: uv run deal --persona-set 1  (through 5)")


if __name__ == "__main__":
    main()
