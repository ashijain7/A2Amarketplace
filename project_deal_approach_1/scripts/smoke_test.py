"""
End-to-end smoke test: drive ONE task entry through the Resources Server
in-process, call /verify, and archive the result.

Run:  python scripts/smoke_test.py
Requires: OPENROUTER_API_KEY in env.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from marketplace import config as mp_config
from resources_server.app import build_app, MarketplaceState
from resources_server.model_config import get_model_config
from scripts.archive_run import archive_one_rollout


def run_smoke():
    mp_config.require_api_key()

    tasks_path = Path(__file__).parent.parent / "tasks" / "marketdeal_tasks.jsonl"
    with tasks_path.open() as f:
        task = json.loads(f.readline())

    print(f"Smoke task: {task['task_id']}")
    personas = json.loads(Path(task["personas_path"]).read_text())
    cfg = get_model_config(task["config_name"])

    state = MarketplaceState(
        focal_name=task["focal_persona"],
        personas=personas,
        opponents_model=cfg["opponents_model"],
        focal_model=cfg["focal_model"],
        judge_model=mp_config.JUDGE_MODEL,
        seed=task["seed"],
        set_id=task["set_id"],
        config_name=task["config_name"],
        data_dir=Path(__file__).parent.parent / "data" / "smoke",
    )
    app = build_app(state)
    client = TestClient(app)

    # Find a sellable item for the focal
    focal_persona = next(p for p in personas if p["name"] == task["focal_persona"])
    if focal_persona.get("items_to_sell"):
        item = focal_persona["items_to_sell"][0]
        r = client.post("/post_listing", json={
            "item_id": item["item_id"],
            "price": item["floor_price"] + 10,
            "message": f"Selling my {item['name']}",
        })
        print(f"  post_listing -> {r.status_code}")
        assert r.status_code == 200

    # Drive a couple more pass turns to let opponents act
    for _ in range(2):
        r = client.post("/pass", json={"message": "waiting"})
        assert r.status_code == 200

    # Verify
    r = client.post("/verify", json={})
    print(f"  verify -> {r.status_code}")
    assert r.status_code == 200
    verify_body = r.json()
    print(f"  reward={verify_body['reward']:.3f}")

    # Build a rollout dict and archive it
    rollout = {
        "task_id": task["task_id"],
        "approach": 1, "phase": 1,
        "config_name": task["config_name"],
        "set_id": task["set_id"],
        "focal_persona": task["focal_persona"],
        "seed": task["seed"],
        "focal_model": cfg["focal_model"],
        "opponents_model": cfg["opponents_model"],
        "judge_model": mp_config.JUDGE_MODEL,
        "reward": verify_body["reward"],
        "rubric_scores": verify_body["rubric_scores"],
        "channel_events": [
            {"turn": e.turn, "event_id": e.event_id, "agent": e.agent,
             "action": e.action, "target": e.target, "price": e.price,
             "message": e.message}
            for e in state.channel.events
        ],
        "deals": [
            {"deal_id": d.deal_id, "seller": d.seller, "buyer": d.buyer,
             "item_id": d.item_id, "item_name": d.item_name, "price": d.price,
             "seller_floor": d.seller_floor, "buyer_ceiling": d.buyer_ceiling,
             "turn": d.turn}
            for d in state.ledger.deals
        ],
        "personas": personas,
        "transcript": [],
    }
    runs_dir = Path(__file__).parent.parent / "results" / "runs"
    out_dir = archive_one_rollout(rollout, runs_dir=runs_dir, ts=datetime.utcnow())
    print(f"  archived -> {out_dir}")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    run_smoke()
