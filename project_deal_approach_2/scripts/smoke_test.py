"""End-to-end smoke test using REAL OpenRouter calls.

Runs ONE task (set_01 / all_haiku / seed=42), prints the result, and
exits non-zero on failure. Use this to verify the full pipeline before
kicking off the 45-task experiment.

Usage:
    python scripts/smoke_test.py
"""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from marketplace import config
from resources_server.app import build_app, MarketplaceServer
from resources_server.persona_loader import load_persona_set
from resources_server.verifiers import compute_rubric_scores


def main():
    config.require_api_key()

    print("[smoke] running /run_marketplace with set_01 / all_haiku / seed=42 ...")
    client = TestClient(build_app())
    r = client.post(
        "/run_marketplace",
        json={"persona_set": "set_01", "model_config": "all_haiku", "seed": 42},
    )
    if r.status_code != 200:
        print(f"[smoke] FAIL: status {r.status_code}\n{r.text}", file=sys.stderr)
        sys.exit(1)

    body = r.json()
    print(f"[smoke] turns_used={body['turns_used']} deals={len(body['deals'])} stop_reason={body['stop_reason']}")
    print(f"[smoke] per_agent_gains={body['per_agent_gains']}")
    assert "model_assignments" in body
    assert isinstance(body["deals"], list)

    print("[smoke] computing rubric scores ...")
    personas = load_persona_set("set_01")
    scores = compute_rubric_scores(
        run_result=body,
        personas=personas,
        model_config_name="all_haiku",
        expected_possible_deals=8,
        judge_model="openai/gpt-4o-2024-11-20",
    )
    print(f"[smoke] final_reward = {scores['final_reward']}")
    print(f"[smoke] deal_outcomes.combined = {scores['deal_outcomes']['combined']}")
    print(f"[smoke] capability_asymmetry.combined = {scores['capability_asymmetry']['combined']}")
    print(f"[smoke] negotiation_quality.combined = {scores['negotiation_quality']['combined']}")
    print(f"[smoke] privacy.combined = {scores['privacy']['combined']}")
    print("[smoke] OK")


if __name__ == "__main__":
    main()
