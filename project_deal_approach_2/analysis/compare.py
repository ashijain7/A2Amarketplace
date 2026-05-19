"""Aggregate per-run summaries into a phase-level comparison file."""

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


CONFIGS = ["all_sonnet", "mixed", "all_haiku"]


def _mean_or_none(values):
    vals = [v for v in values if v is not None]
    return round(statistics.mean(vals), 4) if vals else None


def aggregate_phase_1(runs_root: Path) -> dict:
    summaries: list[dict] = []
    for sub in sorted(runs_root.iterdir()):
        if not sub.is_dir():
            continue
        if not sub.name.startswith("a2_phase1_"):
            continue
        s_path = sub / "summary.json"
        if s_path.exists():
            summaries.append(json.loads(s_path.read_text()))

    out_configs: dict[str, dict] = {}
    for cfg in CONFIGS:
        subset = [s for s in summaries if s.get("config", {}).get("model_config") == cfg]
        if not subset:
            out_configs[cfg] = {"rollout_count": 0}
            continue
        rs = [s.get("rubric_scores", {}) for s in subset]
        cfg_out: dict = {
            "rollout_count": len(subset),
            "mean_reward": _mean_or_none(r.get("final_reward") for r in rs),
            "mean_deal_outcomes": _mean_or_none(r.get("deal_outcomes") for r in rs),
            "mean_capability_asymmetry": _mean_or_none(r.get("capability_asymmetry") for r in rs),
            "mean_neg_quality": _mean_or_none(r.get("negotiation_quality") for r in rs),
            "mean_privacy": _mean_or_none(r.get("privacy") for r in rs),
            "mean_advantage_ratio": _mean_or_none(r.get("advantage_ratio") for r in rs),
            "per_set_breakdown": {},
        }
        # per-set breakdown
        sets: dict[str, list[dict]] = {}
        for s in subset:
            ps = s.get("config", {}).get("persona_set", "unknown")
            sets.setdefault(ps, []).append(s.get("rubric_scores", {}))
        for ps, rs_list in sets.items():
            cfg_out["per_set_breakdown"][ps] = {
                "n": len(rs_list),
                "mean_reward": _mean_or_none(r.get("final_reward") for r in rs_list),
                "mean_advantage_ratio": _mean_or_none(r.get("advantage_ratio") for r in rs_list),
            }

        if cfg == "mixed":
            sonnet_gains_all = []
            haiku_gains_all = []
            for s in subset:
                for agent, info in s.get("per_agent_gains", {}).items():
                    if info["model"] == "sonnet":
                        sonnet_gains_all.append(info["gain"])
                    else:
                        haiku_gains_all.append(info["gain"])
            cfg_out["sonnet_mean_gain"] = _mean_or_none(sonnet_gains_all)
            cfg_out["haiku_mean_gain"] = _mean_or_none(haiku_gains_all)
            ar = cfg_out["mean_advantage_ratio"]
            if ar is not None:
                cfg_out["interpretation"] = (
                    f"Sonnet agents extracted {ar:.2f}x more value than Haiku agents in mixed marketplaces"
                )

        out_configs[cfg] = cfg_out

    headline_ar = out_configs.get("mixed", {}).get("mean_advantage_ratio")
    return {
        "phase": 1, "approach": 2,
        "total_rollouts": len(summaries),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configs": out_configs,
        "headline": {"advantage_ratio": headline_ar},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, default=1)
    parser.add_argument("--runs-root",
                        default="/Users/ashijain/Documents/projectdealpoc/project_deal_approach_2/results/runs")
    parser.add_argument("--out",
                        default="/Users/ashijain/Documents/projectdealpoc/project_deal_approach_2/results/aggregates/phase_1_summary.json")
    args = parser.parse_args()
    assert args.phase == 1, "only Phase 1 supported"

    summary = aggregate_phase_1(Path(args.runs_root))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2))

    print(f"Aggregated {summary['total_rollouts']} runs -> {out_path}")
    print(f"Headline advantage_ratio = {summary['headline']['advantage_ratio']}")
    for cfg in CONFIGS:
        c = summary["configs"][cfg]
        print(f"  {cfg:11s} n={c.get('rollout_count', 0)} reward={c.get('mean_reward')}")


if __name__ == "__main__":
    main()
