"""Generate tasks/marketdeal_tasks.jsonl: 5 sets × 3 configs × 3 seeds = 45 tasks."""

import argparse
import json
from pathlib import Path

from marketplace import config

SET_NAMES = ["set_01", "set_02", "set_03", "set_04", "set_05"]
CONFIGS = ["all_sonnet", "mixed", "all_haiku"]
SEEDS = [42, 43, 44]


RUN_MARKETPLACE_TOOL = {
    "type": "function",
    "function": {
        "name": "run_marketplace",
        "description": "Run a full multi-agent marketplace simulation and return the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "persona_set":  {"type": "string"},
                "model_config": {"type": "string", "enum": CONFIGS},
                "seed":         {"type": "integer"},
            },
            "required": ["persona_set", "model_config", "seed"],
        },
    },
}


def _count_possible_deals(personas: list[dict]) -> int:
    possible = 0
    for s in personas:
        for item in s.get("items_to_sell", []):
            found = False
            for b in personas:
                if b["name"] == s["name"]:
                    continue
                for w in b.get("items_to_buy", []):
                    if w["ceiling_price"] >= item["floor_price"]:
                        possible += 1
                        found = True
                        break
                if found:
                    break
    return possible


def compute_possible_deals_by_set() -> dict[str, int]:
    out = {}
    for name in SET_NAMES:
        path = Path(config.PERSONAS_DIR) / f"{name}.json"
        personas = json.loads(path.read_text())
        out[name] = _count_possible_deals(personas)
    return out


def build_phase_1_tasks(possible_deals_by_set: dict[str, int]) -> list[dict]:
    tasks: list[dict] = []
    for persona_set in SET_NAMES:
        for mc in CONFIGS:
            for seed in SEEDS:
                tasks.append({
                    "responses_create_params": {
                        "input": [{
                            "role": "user",
                            "content": (
                                f"Run marketplace scenario: persona_set={persona_set}, "
                                f"model_config={mc}, seed={seed}. "
                                f"Call the run_marketplace tool with these parameters."
                            ),
                        }],
                        "tools": [RUN_MARKETPLACE_TOOL],
                    },
                    "metadata": {
                        "persona_set": persona_set,
                        "model_config": mc,
                        "seed": seed,
                        "expected_possible_deals": possible_deals_by_set[persona_set],
                    },
                })
    return tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, default=1)
    parser.add_argument("--out", type=str,
                        default="/Users/ashijain/Documents/projectdealpoc/project_deal_approach_2/tasks/marketdeal_tasks.jsonl")
    args = parser.parse_args()
    assert args.phase == 1, "only Phase 1 supported in this script"

    poss = compute_possible_deals_by_set()
    print(f"Possible deals by set: {poss}")
    tasks = build_phase_1_tasks(poss)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")
    print(f"Wrote {len(tasks)} tasks to {out}")


if __name__ == "__main__":
    main()
