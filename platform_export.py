"""Convert an adapter result.json into the RLEaaS platform's RolloutRecord shape,
and push a finished run to the platform (best-effort, env-gated).

Dependency-free ON PURPOSE: imported from the engine venv (adapter.py) AND the
sim_ui venv. Stdlib only. Never raises out of push_to_platform."""
import json
import os
import sys
import urllib.request

DEFAULT_ENV_NAME = "project_deal_marketplace"


def result_to_platform_records(result: dict, env_name: str, run_id: str) -> list[dict]:
    """One platform RolloutRecord-shaped dict per set in result['per_set']."""
    recs = []
    for i, ps in enumerate(result.get("per_set", [])):
        reward = ps.get("reward")
        reward = float(reward) if reward is not None else 0.0
        raw_bd = ps.get("rubric_breakdown") or {}
        reward_breakdown = {k: v for k, v in raw_bd.items() if v is not None}
        recs.append({
            "environment_name": env_name,
            "episode_number": i + 1,
            "steps": [{
                "step": 0,
                "action": None,
                "reward": reward,
                "state_summary": None,
                "reward_breakdown": reward_breakdown,
                "timeline_events": None,
            }],
            "total_reward": reward,
            "total_steps": 1,
            "status": "completed",
            "source": "simulation",
            "policy_name": result.get("focal_model"),
            "scenario_name": ps.get("set_id"),
            "final_outcome": {
                "run_id": run_id,
                "phase": result.get("phase"),
                "focal_model": result.get("focal_model"),
                "opponents_model": result.get("opponents_model"),
                "set_id": ps.get("set_id"),
                "focal_persona": ps.get("focal_persona"),
                "num_deals": ps.get("num_deals"),
                "num_channel_events": ps.get("num_channel_events"),
            },
        })
    return recs


def push_to_platform(result: dict, run_id: str) -> int:
    """Best-effort: POST each record to the platform. Returns count POSTed.
    No-op (returns 0) unless BOTH RLEAAS_CALLBACK_URL and RLEAAS_TOKEN are set.
    Never raises — a push failure must not fail the run."""
    url = os.environ.get("RLEAAS_CALLBACK_URL")
    token = os.environ.get("RLEAAS_TOKEN")
    if not url or not token:
        return 0
    sent = 0
    try:
        env_name = os.environ.get("RLEAAS_ENV_NAME", DEFAULT_ENV_NAME)
        recs = result_to_platform_records(result, env_name, run_id)
    except Exception as e:  # noqa: BLE001 — best-effort, never fail the run
        print(f"[platform_export] push conversion failed for run {run_id}: {e}", file=sys.stderr)
        return 0
    for rec in recs:
        try:
            data = json.dumps(rec).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
            sent += 1
        except Exception as e:  # noqa: BLE001 — best-effort, never fail the run
            print(f"[platform_export] push failed for run {run_id}: {e}", file=sys.stderr)
    return sent
