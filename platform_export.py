"""Convert an adapter result.json into the RLEaaS platform's RolloutRecord shape,
and push a finished run to the platform (best-effort, env-gated).

Dependency-free ON PURPOSE: imported from the engine venv (adapter.py) AND the
sim_ui venv. Stdlib only. Never raises out of push_to_platform."""
import json
import os
import sys
import urllib.request

DEFAULT_ENV_NAME = "project_deal_marketplace"

# A live row must read like the cached ones, or the Rollouts tab becomes two different
# vocabularies for the same environment. Kept here (not imported from sim_ui) because this
# module is loaded from the engine venv and must stay dependency-free.
_MODE_STAGE = {
    "market_deal": "MarketDeal · Stage I",
    "review": "Review · Stage II",
    "transaction": "Transaction · Stage III",
    "swap_shop": "SwapShop · Stage IV",
}
_MODE_TITLE = {
    "market_deal": "Basic trading",
    "review": "Review-assisted",
    "transaction": "Payment under a scammer",
    "swap_shop": "Item-for-item barter",
}
_MODEL_NAME = {
    "anthropic/claude-sonnet-4-5": "Sonnet 4.5",
    "anthropic/claude-haiku-4-5": "Haiku 4.5",
    "anthropic/claude-opus-4-7": "Opus 4.7",
    "anthropic/claude-opus-4.8": "Opus 4.8",
    "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "google/gemini-3.5-flash": "Gemini 3.5 Flash",
    "openai/gpt-5.5": "GPT-5.5",
}


def model_name(slug):
    """Readable name for a provider/model slug. An unknown model still reads sensibly."""
    if not slug:
        return "?"
    return _MODEL_NAME.get(slug) or str(slug).split("/")[-1]


def result_to_platform_records(result: dict, env_name: str, run_id: str) -> list[dict]:
    """One platform RolloutRecord-shaped dict per set in result['per_set']."""
    recs = []
    phase = result.get("phase") or ""
    stage = _MODE_STAGE.get(phase, phase)
    focal = model_name(result.get("focal_model"))
    opponent = model_name(result.get("opponents_model"))
    duration = result.get("duration_s")
    per_set = result.get("per_set", [])
    # One run can cover several sets; each becomes its own rollout, so the run's duration
    # is shared out rather than reported in full against every one of them.
    per_set_duration = (
        round(float(duration) / len(per_set), 1)
        if duration is not None and per_set
        else None
    )

    for i, ps in enumerate(per_set):
        reward = ps.get("reward")
        reward = float(reward) if reward is not None else 0.0
        raw_bd = ps.get("rubric_breakdown") or {}
        reward_breakdown = {k: v for k, v in raw_bd.items() if v is not None}
        set_id = ps.get("set_id") or "set_00"
        set_label = str(set_id).replace("set_", "Set ")
        deals = ps.get("num_focal_deals") or 0
        steps = ps.get("num_focal_steps") or 0

        rec = {
            # The run names itself, so a retry updates this row instead of creating a
            # second copy of the same episode.
            "id": f"{run_id}__{set_id}",
            "environment_name": env_name,
            "episode_number": i + 1,
            "steps": [{
                "step": 0,
                "action": None,
                "reward": reward,
                "state_summary": None,
                "reward_breakdown": reward_breakdown,
                # [] and not None: the platform counts tool calls by iterating this, and a
                # null key makes it iterate None — which 500s the whole rollout list.
                "timeline_events": [],
            }],
            "total_reward": reward,
            # The evaluated agent's own actions — not the market's traffic around it.
            "total_steps": steps,
            "status": "completed",
            "source": "simulation",
            # The rollout LIST prints only this line, so it must say who was evaluated and
            # who they faced.
            "policy_name": f"{focal} (evaluated) vs {opponent}",
            "checkpoint_label": f"{stage} · {set_label}",
            "scenario_name": f"{stage} — {set_label} ({_MODE_TITLE.get(phase, phase)})",
            # Shown as "Final State". "Resolved" says nothing about a marketplace; whether
            # the agent actually closed anything does.
            "final_environment_state": {
                **reward_breakdown,
                "status": f"{deals} deal{'' if deals == 1 else 's'} closed"
                if deals
                else "no deal closed",
            },
            "verifier_results": [
                {"check": k, "passed": float(v) > 0, "detail": str(v)}
                for k, v in reward_breakdown.items()
            ],
            "final_outcome": {
                "run_id": run_id,
                "phase": phase,
                "focal_model": result.get("focal_model"),
                "opponents_model": result.get("opponents_model"),
                "set_id": set_id,
                "focal_persona": ps.get("focal_persona"),
                "num_focal_deals": deals,
                "num_deals": ps.get("num_deals"),
                "num_channel_events": ps.get("num_channel_events"),
                "max_turns": result.get("max_turns"),
                "resolved": deals > 0,
            },
        }
        # A measured duration, so the Duration column stops guessing (the platform
        # otherwise fills it with total_steps * 0.7). Omitted if we never timed the run.
        if per_set_duration is not None:
            rec["duration_s"] = per_set_duration
        recs.append(rec)
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
