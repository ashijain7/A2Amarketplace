#!/usr/bin/env python3
"""Build a2a_rollouts.json — the cached corpus, in the shape RLEaaS seeds rollouts from.

RLEaaS fills its Rollouts tab by reading a JSON file from its project root at boot
(`seed_hitl_rollout_json_files`, api/main.py) — the same way SRE_24x7 and VRAM do it.
This produces our equivalent from the 140 recorded paper runs, so the corpus shows up
in the platform without a single live run.

A rollout here is the EVALUATED agent's trajectory: `steps` are the focal agent's own
actions. Everything the opponents do is the environment reacting, and belongs to the
episode, not to the agent's step list.

Reads:  results/paper_runs/<config>/phase<N>/rollouts.jsonl   (+ the one salvaged run)
Writes: a2a_rollouts.json

Usage:
    python scripts/build_a2a_rollouts.py --out a2a_rollouts.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim_ui.ui.logic import (  # noqa: E402
    MODE_STAGE,
    MODE_TITLE,
    PAPER_RUNS,
    SALVAGED_RUNS,
    classify_mode,
    models_for,
)

# The rubrics a run may report. `privacy` is the key `compute_final_reward` takes;
# rollouts report it as `persona_privacy`. Normalize to the reported name so the
# platform's KPI averages line up with what the UI shows.
_RUBRICS = (
    "deal_outcomes",
    "capability_asymmetry",
    "negotiation_quality",
    "persona_privacy",
    "review_utilization",
    "swap_quality",
    "transactional_integrity",
)

# A run where the focal never acts is not interesting as a trajectory, but it IS a real
# result — keep it, with an empty step list rather than dropping the episode.
_STAGE_NUM = {"market": "Set", "review": "Set", "transaction": "Set", "swap": "Set"}


def _combined(rubric_scores: dict, key: str):
    """A rubric's headline number; None when the rubric did not apply to this run."""
    val = (rubric_scores or {}).get(key)
    if val is None and key == "persona_privacy":
        val = (rubric_scores or {}).get("privacy")  # older runs use the other key
    if isinstance(val, dict):
        val = val.get("combined")
    return val if isinstance(val, (int, float)) else None


def _focal_steps(rollout: dict, focal: str) -> list[dict]:
    """The evaluated agent's own actions, in order."""
    steps = []
    for ev in rollout.get("channel_events") or []:
        if ev.get("agent") != focal:
            continue
        args = {
            k: ev[k]
            for k in ("target", "price", "swap_item_id")
            if ev.get(k) is not None
        }
        steps.append(
            {
                "step": len(steps) + 1,
                "content": ev.get("message") or "",
                "tool_calls": [{"name": ev.get("action") or "act", "arguments": args}],
                # The engine scores the episode, not the turn — there is no per-step
                # reward to report, and inventing one would be a lie.
                "step_reward": 0.0,
            }
        )
    return steps


def _focal_deals(rollout: dict, focal: str) -> int:
    """How many deals the evaluated agent actually closed (its own, not the market's)."""
    return sum(
        1
        for d in (rollout.get("deals") or [])
        if focal in (d.get("buyer"), d.get("seller"))
    )


def _rollout_record(rollout: dict, index: int) -> dict:
    meta = rollout.get("metadata") or {}
    mode = classify_mode(rollout)
    set_id = meta.get("set_id") or "set_00"
    focal = meta.get("focal_persona") or ""
    # The model pair comes from `config_name` in the run's own metadata. The FOLDER name
    # (C1_sonnet_vs_sonnet) is a different scheme and does not parse as a config slug.
    config = meta.get("config_name") or ""
    focal_model, opponent_model = models_for(config)

    rubrics = {
        k: v
        for k in _RUBRICS
        if (v := _combined(rollout.get("rubric_scores") or {}, k)) is not None
    }
    steps = _focal_steps(rollout, focal)
    set_label = set_id.replace("set_", "Set ")
    deals = _focal_deals(rollout, focal)

    return {
        # Globally unique: one run per (mode, config, set).
        "rollout_id": f"{mode}_{config}_{set_id}",
        # Shown as "Policy" — the only line the rollout LIST prints besides the env name.
        # It has to say WHO was evaluated and WHO they faced, or the row is just a model
        # name with no idea what it was up against.
        "model": f"{focal_model} (evaluated) vs {opponent_model}",
        "task_description": f"{MODE_STAGE[mode]} — {set_label} ({MODE_TITLE[mode]})",
        "label": f"{MODE_STAGE[mode]} · {set_label}",
        # 1-based: this is shown as "Episode #N", and #0 reads like a missing run.
        "train_step": index + 1,
        "total_reward": rollout.get("reward") or 0.0,
        "num_turns": len(steps),
        "terminal_pass": deals > 0,
        # Shown as "Final State". "Resolved" (the platform's generic word) says nothing
        # about a marketplace — what matters is whether the agent actually closed anything.
        "final_state": f"{deals} deal{'' if deals == 1 else 's'} closed"
        if deals
        else "no deal closed",
        # These runs were recorded without timing. The platform otherwise fills the
        # Duration column with total_steps * 0.7 — a number that looks measured and is
        # not. An explicit null makes the UI print "—" instead of inventing one.
        "duration_s": None,
        # Evaluations of a fixed policy, not training rollouts.
        "source": "simulation",
        "episode_rewards": rubrics,
        "turns": steps,
        # Enough context to tell later what a row actually was.
        "a2a_mode": mode,
        "a2a_config": config,
        "a2a_set": set_id,
        "a2a_focal_agent": focal,
        "a2a_evaluated_model": focal_model,
        "a2a_opponent_model": opponent_model,
        "a2a_deals_closed": deals,
        "a2a_channel_events": len(rollout.get("channel_events") or []),
    }


def _load_all() -> list[dict]:
    """Every recorded run in the corpus, including the one salvaged from a killed run."""
    out: list[dict] = []
    for jsonl in sorted(PAPER_RUNS.glob("*/phase*/rollouts.jsonl")):
        for line in jsonl.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    for f in SALVAGED_RUNS:
        if f.is_file():
            out.append(json.loads(f.read_text()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="a2a_rollouts.json")
    args = ap.parse_args()

    raw = _load_all()
    seen: dict[str, dict] = {}
    for i, rollout in enumerate(raw):
        rec = _rollout_record(rollout, i)
        # A duplicate id would mean two runs claim the same (mode, config, set) — the
        # exact collision the mode classifier used to cause. Fail loudly, don't overwrite.
        if rec["rollout_id"] in seen:
            raise SystemExit(f"duplicate rollout_id: {rec['rollout_id']}")
        seen[rec["rollout_id"]] = rec

    doc = {
        # Must equal the registered environment id, or the platform files these under a
        # name nothing else uses.
        "environment": "A2A_Marketplace",
        "model": "7 model pairs (see each rollout)",
        "task_description": "Agent-to-agent marketplace — cached paper corpus",
        "algorithm": "evaluation (no training)",
        "rollouts": list(seen.values()),
    }
    out = Path(args.out)
    out.write_text(json.dumps(doc, indent=1))

    by_mode: dict[str, int] = {}
    for r in doc["rollouts"]:
        by_mode[r["a2a_mode"]] = by_mode.get(r["a2a_mode"], 0) + 1
    print(f"wrote {out} — {len(doc['rollouts'])} rollouts, {out.stat().st_size/1e6:.2f} MB")
    print(f"  by stage: {by_mode}")
    print(f"  steps:    {sum(r['num_turns'] for r in doc['rollouts'])} focal actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
