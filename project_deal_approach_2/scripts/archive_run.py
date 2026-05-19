"""Post-process NeMo Gym rollout JSONL into per-run archive folders.

Folder naming: a2_phase1_{config}_{set}_seed{S}_{YYYYMMDD}_{HHMM}
Files written per run:
  summary.json, channel.jsonl, deals.json, personas.json,
  rubric_scores.json, rollout.json, judge_ratings.json
For mixed runs: also model_advantage.json
For runs with private agents: also privacy_findings.json
"""

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from resources_server.model_config import MODEL_SONNET, MODEL_HAIKU
from resources_server.persona_loader import load_persona_set


def build_run_id(phase: int, model_config: str, persona_set: str, seed: int, when: str) -> str:
    set_short = persona_set.replace("_", "")  # set_03 -> set03
    return f"a2_phase{phase}_{model_config}_{set_short}_seed{seed}_{when}"


def archive_rollout(rollout: dict, personas: list[dict], out_root: Path, when: str) -> Path:
    meta = rollout["metadata"]
    persona_set = meta["persona_set"]
    model_config_name = meta["model_config"]
    seed = meta["seed"]

    run_id = build_run_id(1, model_config_name, persona_set, seed, when)
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    run_result = rollout["run_result"]
    rubric_scores = rollout["rubric_scores"]
    final_reward = rollout.get("reward", rubric_scores.get("final_reward"))

    # personas snapshot + model assignments
    personas_snapshot = {
        "personas": personas,
        "model_assignments": run_result.get("model_assignments", {}),
    }
    (run_dir / "personas.json").write_text(json.dumps(personas_snapshot, indent=2))

    # channel as JSONL
    with (run_dir / "channel.jsonl").open("w") as f:
        for ev in run_result.get("channel_log", []):
            f.write(json.dumps(ev) + "\n")

    # deals
    (run_dir / "deals.json").write_text(json.dumps(run_result.get("deals", []), indent=2))

    # raw rollout
    (run_dir / "rollout.json").write_text(json.dumps(rollout, indent=2, default=str))

    # rubric scores
    (run_dir / "rubric_scores.json").write_text(json.dumps(rubric_scores, indent=2, default=str))

    # judge ratings (subset of capability_asymmetry)
    ca = rubric_scores.get("capability_asymmetry", {})
    judge_ratings = {
        "per_agent_self_rating": ca.get("per_agent_self_rating", {}),
        "per_agent_observer_rating": ca.get("per_agent_observer_rating", {}),
    }
    (run_dir / "judge_ratings.json").write_text(json.dumps(judge_ratings, indent=2))

    # action counts
    action_counts: dict[str, int] = {}
    for ev in run_result.get("channel_log", []):
        action_counts[ev["action"]] = action_counts.get(ev["action"], 0) + 1

    deals = run_result.get("deals", [])
    total_value = sum(d["price"] for d in deals)
    avg_price = total_value / len(deals) if deals else 0.0
    avg_seller_margin = (
        sum(d["price"] - d["seller_floor"] for d in deals) / len(deals)
    ) if deals else 0.0
    avg_buyer_savings = (
        sum((d["buyer_ceiling"] or 0) - d["price"] for d in deals) / len(deals)
    ) if deals else 0.0

    private_bearing = [p["name"] for p in personas if p.get("private")]
    per_agent_gains = run_result.get("per_agent_gains", {})

    summary = {
        "run_id": run_id,
        "approach": 2,
        "phase": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "model_config": model_config_name,
            "model_assignments": run_result.get("model_assignments", {}),
            "judge_model": "openai/gpt-4o-2024-11-20",
            "persona_set": persona_set,
            "seed": seed,
        },
        "agents": [p["name"] for p in personas],
        "private_bearing_agents": private_bearing,
        "run": {
            "total_events": sum(action_counts.values()),
            "stop_reason": run_result.get("stop_reason"),
            "deals_closed": len(deals),
            "total_value_traded": round(total_value, 2),
            "turns_used": run_result.get("turns_used"),
        },
        "channel_stats": {
            k: action_counts.get(k, 0)
            for k in ("listing","offer","counter","accept","decline","reject","pass")
        },
        "rubric_scores": {
            "deal_outcomes": rubric_scores.get("deal_outcomes", {}).get("combined"),
            "capability_asymmetry": rubric_scores.get("capability_asymmetry", {}).get("combined"),
            "advantage_ratio": rubric_scores.get("advantage_ratio"),
            "negotiation_quality": rubric_scores.get("negotiation_quality", {}).get("combined"),
            "privacy": rubric_scores.get("privacy", {}).get("combined"),
            "review_utilization": rubric_scores.get("review_utilization"),
            "final_reward": final_reward,
        },
        "per_agent_gains": {
            agent: {
                "model": "sonnet" if run_result["model_assignments"].get(agent) == MODEL_SONNET else "haiku",
                "gain": gain,
            }
            for agent, gain in per_agent_gains.items()
        },
        "deal_metrics": {
            "count": len(deals),
            "total_value": round(total_value, 2),
            "avg_price": round(avg_price, 2),
            "avg_seller_margin": round(avg_seller_margin, 2),
            "avg_buyer_savings": round(avg_buyer_savings, 2),
        },
        "deals": deals,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    # model_advantage.json — mixed only
    if model_config_name == "mixed":
        sonnet_gains = [
            g for a, g in per_agent_gains.items()
            if run_result["model_assignments"].get(a) == MODEL_SONNET
        ]
        haiku_gains = [
            g for a, g in per_agent_gains.items()
            if run_result["model_assignments"].get(a) == MODEL_HAIKU
        ]
        adv = {
            "advantage_ratio": rubric_scores.get("advantage_ratio"),
            "sonnet_mean_gain": round(statistics.mean(sonnet_gains), 2) if sonnet_gains else 0.0,
            "haiku_mean_gain": round(statistics.mean(haiku_gains), 2) if haiku_gains else 0.0,
            "sonnet_gains": sonnet_gains,
            "haiku_gains": haiku_gains,
            "sonnet_perceived_fairness": ca.get("sonnet_perceived_fairness"),
            "haiku_perceived_fairness": ca.get("haiku_perceived_fairness"),
        }
        (run_dir / "model_advantage.json").write_text(json.dumps(adv, indent=2))

    # privacy_findings.json — only when private bearers exist
    if private_bearing:
        priv = rubric_scores.get("privacy", {})
        (run_dir / "privacy_findings.json").write_text(json.dumps(priv, indent=2))

    return run_dir


def archive_jsonl(rollouts_path: Path, out_root: Path) -> list[Path]:
    when = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    folders: list[Path] = []
    with rollouts_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rollout = json.loads(line)
            persona_set = rollout["metadata"]["persona_set"]
            personas = load_persona_set(persona_set)
            folders.append(archive_rollout(rollout, personas, out_root, when))
    return folders


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollouts", required=True,
                        help="path to NeMo Gym rollout JSONL")
    parser.add_argument("--out-root",
                        default="/Users/ashijain/Documents/projectdealpoc/project_deal_approach_2/results/runs")
    args = parser.parse_args()
    folders = archive_jsonl(Path(args.rollouts), Path(args.out_root))
    print(f"Archived {len(folders)} runs to {args.out_root}")


if __name__ == "__main__":
    main()
