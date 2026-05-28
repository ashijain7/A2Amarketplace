"""
Post-process NeMo Gym rollout JSONL into per-run folders.

Usage:
  python scripts/archive_run.py --input results/phase_1/focal_S_vs_S_rollouts.jsonl
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_RUNS_DIR = Path(__file__).parent.parent / "results" / "runs"


def build_run_folder_name(approach: int, phase: int, config_name: str,
                          set_id: str, focal_name: str, seed: int,
                          ts: datetime) -> str:
    config_slug = config_name.replace("_", "-")  # focal_S_vs_S -> focal-S-vs-S
    set_slug = set_id.replace("_", "")           # set_03 -> set03
    return (
        f"a{approach}_phase{phase}_{config_slug}_{set_slug}_"
        f"focal-{focal_name}_seed{seed}_{ts.strftime('%Y%m%d_%H%M')}"
    )


def archive_one_rollout(rollout: dict, runs_dir: Path, ts: datetime = None) -> Path:
    """Write the 7 per-run files. Returns the created folder path."""
    ts = ts or datetime.utcnow()

    # NeMo Gym wraps our task fields under "metadata"; fall back to top-level
    # for backward compat with older rollout JSONLs.
    meta = rollout.get("metadata") or {}

    def field(name, default=None):
        return meta.get(name, rollout.get(name, default))

    folder_name = build_run_folder_name(
        approach=field("approach", 1),
        phase=field("phase", 1),
        config_name=field("config_name"),
        set_id=field("set_id"),
        focal_name=field("focal_persona"),
        seed=field("seed"),
        ts=ts,
    )
    out = Path(runs_dir) / folder_name
    out.mkdir(parents=True, exist_ok=True)

    rubric = rollout.get("rubric_scores", {})
    cap = rubric.get("capability_asymmetry") or {}

    summary = {
        "run_id": folder_name,
        "approach": field("approach", 1),
        "phase": field("phase", 1),
        "timestamp": ts.isoformat() + "Z",
        "config": {
            "model_config": field("config_name"),
            "focal_model": field("focal_model"),
            "opponents_model": field("opponents_model"),
            "judge_model": field("judge_model"),
            "persona_set": field("set_id"),
            "focal_persona": field("focal_persona"),
            "seed": field("seed"),
        },
        "rubric_scores": {
            "deal_outcomes": (rubric.get("deal_outcomes") or {}).get("combined"),
            "capability_asymmetry": cap.get("combined"),
            "negotiation_quality": (rubric.get("negotiation_quality") or {}).get("combined"),
            "privacy": (rubric.get("privacy") or {}).get("combined"),
            "review_utilization": rubric.get("review_utilization"),
            "final_reward": rubric.get("final_reward", rollout.get("reward")),
        },
        "focal_value_extracted": cap.get("focal_value_extracted"),
        "deal_count": len(rollout.get("deals", [])),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    # channel.jsonl — one event per line
    with (out / "channel.jsonl").open("w") as f:
        for e in rollout.get("channel_events", []):
            f.write(json.dumps(e) + "\n")

    (out / "deals.json").write_text(
        json.dumps(rollout.get("deals", []), indent=2)
    )
    (out / "personas.json").write_text(
        json.dumps(rollout.get("personas", []), indent=2)
    )

    # Write payment_ledger.json whenever payment_log exists (even if focal didn't buy)
    pay_compliance = rubric.get("payment_compliance")
    payment_log_data = rollout.get("payment_log", [])

    if pay_compliance is not None or payment_log_data:
        payment_ledger = {
            "payment_compliance": pay_compliance,
            "transactions": payment_log_data,
        }
        (out / "payment_ledger.json").write_text(
            json.dumps(payment_ledger, indent=2)
        )

    (out / "rubric_scores.json").write_text(json.dumps(rubric, indent=2))
    (out / "rollout.json").write_text(json.dumps(rollout, indent=2))
    (out / "judge_ratings.json").write_text(json.dumps({
        "self_rating": cap.get("self_rating"),
        "observer_rating": cap.get("observer_rating"),
        "perceived_fairness": cap.get("perceived_fairness"),
        "self_observer_delta": cap.get("self_observer_delta"),
    }, indent=2))

    # Optional 8th file when focal had private info
    priv = rubric.get("privacy") or {}
    if priv.get("applicable"):
        (out / "privacy_findings.json").write_text(json.dumps({
            "leaks_found": priv.get("leaks_found"),
            "leak_details": priv.get("leak_details", []),
            "pii_leakage_rate": priv.get("pii_leakage_rate"),
            "boundary_violations": priv.get("boundary_violations"),
            "boundary_score": priv.get("boundary_score"),
        }, indent=2))

    return out


def archive_jsonl(input_path: Path, runs_dir: Path = DEFAULT_RUNS_DIR) -> list[Path]:
    paths = []
    with Path(input_path).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rollout = json.loads(line)
            paths.append(archive_one_rollout(rollout, runs_dir=runs_dir))
    return paths


def cleanup_empty_sessions(ng_run_dir: Path) -> int:
    """Remove empty session folders under data/ng_run/.

    A session folder is "empty" if its channel.jsonl is 0 bytes — typically
    these are created by NeMo Gym's startup probes that issued session cookies
    but never ran an actual rollout. Returns count removed.
    """
    import shutil
    if not ng_run_dir.exists():
        return 0
    removed = 0
    for d in ng_run_dir.iterdir():
        if not d.is_dir():
            continue
        ch = d / "channel.jsonl"
        if ch.exists() and ch.stat().st_size == 0:
            shutil.rmtree(d)
            removed += 1
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True,
                    help="Path to NeMo Gym rollout JSONL")
    ap.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    ap.add_argument("--no-cleanup", action="store_true",
                    help="Skip cleaning empty data/ng_run/ sessions after archive")
    args = ap.parse_args()
    paths = archive_jsonl(args.input, runs_dir=args.runs_dir)
    print(f"Archived {len(paths)} runs under {args.runs_dir}")
    if not args.no_cleanup:
        ng_run_dir = Path(__file__).parent.parent / "data" / "ng_run"
        n = cleanup_empty_sessions(ng_run_dir)
        if n:
            print(f"Cleaned {n} empty session folder(s) from data/ng_run/")


if __name__ == "__main__":
    main()
