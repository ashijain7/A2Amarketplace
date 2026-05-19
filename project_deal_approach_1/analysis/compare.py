"""
Aggregate per-run summary.json files into a phase-level comparison.

Outputs results/aggregates/phase_1_summary.json with:
- mean rewards per config
- per-set breakdown
- asymmetry_test (focal_H_vs_S vs focal_S_vs_H mean value extracted)
"""

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_RUNS_DIR = Path(__file__).parent.parent / "results" / "runs"
DEFAULT_OUT_DIR = Path(__file__).parent.parent / "results" / "aggregates"


def _load_summaries(runs_dir: Path, phase: int) -> list[dict]:
    summaries = []
    for folder in sorted(Path(runs_dir).iterdir()):
        if not folder.is_dir():
            continue
        f = folder / "summary.json"
        if not f.exists():
            continue
        data = json.loads(f.read_text())
        if data.get("phase") == phase:
            summaries.append(data)
    return summaries


def _mean_or_none(values: list) -> float | None:
    nums = [v for v in values if isinstance(v, (int, float))]
    return statistics.mean(nums) if nums else None


def aggregate_runs(runs_dir: Path, phase: int) -> dict:
    summaries = _load_summaries(runs_dir, phase=phase)

    configs: dict[str, dict] = {}
    for s in summaries:
        cfg = s["config"]["model_config"]
        bucket = configs.setdefault(cfg, {
            "rollout_count": 0,
            "rewards": [],
            "deal_outcomes": [],
            "capability_asymmetry": [],
            "negotiation_quality": [],
            "privacy": [],
            "value_extracted": [],
            "per_set": {},
        })
        bucket["rollout_count"] += 1
        rs = s["rubric_scores"]
        bucket["rewards"].append(rs.get("final_reward"))
        bucket["deal_outcomes"].append(rs.get("deal_outcomes"))
        bucket["capability_asymmetry"].append(rs.get("capability_asymmetry"))
        bucket["negotiation_quality"].append(rs.get("negotiation_quality"))
        bucket["privacy"].append(rs.get("privacy"))
        bucket["value_extracted"].append(s.get("focal_value_extracted"))
        set_id = s["config"]["persona_set"]
        set_bucket = bucket["per_set"].setdefault(set_id, {"rollout_count": 0, "rewards": []})
        set_bucket["rollout_count"] += 1
        set_bucket["rewards"].append(rs.get("final_reward"))

    out_configs = {}
    for cfg, b in configs.items():
        out_configs[cfg] = {
            "rollout_count": b["rollout_count"],
            "mean_reward": _mean_or_none(b["rewards"]),
            "mean_deal_outcomes": _mean_or_none(b["deal_outcomes"]),
            "mean_capability_asymmetry": _mean_or_none(b["capability_asymmetry"]),
            "mean_neg_quality": _mean_or_none(b["negotiation_quality"]),
            "mean_privacy": _mean_or_none(b["privacy"]),
            "mean_value_extracted": _mean_or_none(b["value_extracted"]),
            "per_set_breakdown": {
                sid: {"rollout_count": sb["rollout_count"],
                      "mean_reward": _mean_or_none(sb["rewards"])}
                for sid, sb in b["per_set"].items()
            },
        }

    h_in_s = out_configs.get("focal_H_vs_S", {}).get("mean_value_extracted")
    s_in_h = out_configs.get("focal_S_vs_H", {}).get("mean_value_extracted")
    if h_in_s is not None and s_in_h is not None:
        delta = s_in_h - h_in_s
        if h_in_s > 0:
            ratio = s_in_h / h_in_s
            interp = (f"Sonnet extracts {ratio:.1f}x more from a Haiku field "
                      f"than Haiku does from a Sonnet field")
        else:
            interp = "Insufficient data for ratio interpretation"
        asym = {
            "focal_H_vs_S_mean_value_extracted": h_in_s,
            "focal_S_vs_H_mean_value_extracted": s_in_h,
            "delta": delta,
            "interpretation": interp,
        }
    else:
        asym = None

    return {
        "phase": phase,
        "approach": 1,
        "total_rollouts": len(summaries),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "configs": out_configs,
        "asymmetry_test": asym,
    }


def write_phase_summary(runs_dir: Path, out_path: Path, phase: int):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = aggregate_runs(runs_dir=runs_dir, phase=phase)
    out_path.write_text(json.dumps(data, indent=2))
    print(f"Wrote aggregate for {data['total_rollouts']} runs -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, default=1)
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    ap.add_argument("--out", type=Path, default=None,
                    help="Output JSON path. Defaults to "
                         "results/aggregates/phase_{N}_summary.json.")
    args = ap.parse_args()
    if args.out is None:
        args.out = DEFAULT_OUT_DIR / f"phase_{args.phase}_summary.json"
    write_phase_summary(runs_dir=args.runs_dir, out_path=args.out, phase=args.phase)


if __name__ == "__main__":
    main()
