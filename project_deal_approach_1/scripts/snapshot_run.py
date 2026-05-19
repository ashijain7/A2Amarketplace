"""
Snapshot a completed NeMo Gym run into a sealed, phase-scoped folder.

Each call creates a fresh directory:

    results/phase{N}/run_{KIND}_{CONFIG_TAG}_{SEED_TAG}_{TIMESTAMP}/
        rollouts.jsonl                   # raw NeMo Gym output (copied)
        aggregate_metrics.json           # aggregate metrics (copied if present)
        materialized_inputs.jsonl        # NeMo Gym sidecar (copied if present)
        metadata.json                    # what this snapshot is + provenance
        runs/                            # per-rollout subfolders from archive_run
            a1_phaseN_*_<set>_focal-*_seed*_<ts>/
                summary.json, channel.jsonl, deals.json,
                personas.json, rubric_scores.json, rollout.json,
                judge_ratings.json [, privacy_findings.json]

Usage:
  python scripts/snapshot_run.py \\
      --phase 1 \\
      --rollouts results/phase_1/phase1_5task_rollouts.jsonl \\
      --kind 5tasks \\
      --config-tag focalSvH \\
      --seed-tag seed42

The snapshot folder is fully self-contained — no references to outside files.
You can delete results/phase_1/*.jsonl and data/ng_run/ after snapshotting and
still have a complete record.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.archive_run import archive_jsonl, cleanup_empty_sessions

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def build_snapshot_name(kind: str, config_tag: str, seed_tag: str,
                        ts: datetime) -> str:
    return f"run_{kind}_{config_tag}_{seed_tag}_{ts.strftime('%Y%m%d_%H%M%S')}"


def snapshot_run(phase: int, rollouts_path: Path, kind: str,
                 config_tag: str, seed_tag: str,
                 aggregate_path: Path | None = None,
                 materialized_path: Path | None = None,
                 ts: datetime | None = None,
                 cleanup_ng_run: bool = True) -> Path:
    rollouts_path = Path(rollouts_path)
    if not rollouts_path.exists():
        raise FileNotFoundError(f"rollouts JSONL not found: {rollouts_path}")
    ts = ts or datetime.utcnow()

    # Default companion files live next to the rollouts JSONL, with NeMo Gym's
    # naming convention <name>_aggregate_metrics.json and <name>_materialized_inputs.jsonl
    stem = rollouts_path.stem  # e.g. "phase1_5task_rollouts"
    parent = rollouts_path.parent
    if aggregate_path is None:
        cand = parent / f"{stem}_aggregate_metrics.json"
        if cand.exists():
            aggregate_path = cand
    if materialized_path is None:
        cand = parent / f"{stem}_materialized_inputs.jsonl"
        if cand.exists():
            materialized_path = cand

    # Build the snapshot dir under results/phaseN/
    phase_dir = RESULTS_DIR / f"phase{phase}"
    snapshot_dir = phase_dir / build_snapshot_name(kind, config_tag, seed_tag, ts)
    snapshot_dir.mkdir(parents=True, exist_ok=False)  # never overwrite

    # 1. Copy raw rollouts
    shutil.copy2(rollouts_path, snapshot_dir / "rollouts.jsonl")

    # 2. Copy aggregate + materialized inputs if present
    if aggregate_path and Path(aggregate_path).exists():
        shutil.copy2(aggregate_path, snapshot_dir / "aggregate_metrics.json")
    if materialized_path and Path(materialized_path).exists():
        shutil.copy2(materialized_path, snapshot_dir / "materialized_inputs.jsonl")

    # 3. Per-rollout archive folders, written under <snapshot>/runs/
    runs_subdir = snapshot_dir / "runs"
    runs_subdir.mkdir(parents=True, exist_ok=True)
    archived = archive_jsonl(rollouts_path, runs_dir=runs_subdir)

    # 4. Snapshot metadata
    n_rollouts = sum(1 for _ in rollouts_path.open() if _.strip())
    metadata = {
        "snapshot_id": snapshot_dir.name,
        "phase": phase,
        "kind": kind,
        "config_tag": config_tag,
        "seed_tag": seed_tag,
        "timestamp_utc": ts.isoformat() + "Z",
        "rollout_count": n_rollouts,
        "archived_run_folders": len(archived),
        "source": {
            "rollouts_jsonl": str(rollouts_path),
            "aggregate_metrics_json": str(aggregate_path) if aggregate_path else None,
            "materialized_inputs_jsonl": str(materialized_path) if materialized_path else None,
        },
    }
    (snapshot_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    # 5. Optional: clean empty session folders from data/ng_run/
    if cleanup_ng_run:
        n = cleanup_empty_sessions(PROJECT_ROOT / "data" / "ng_run")
        if n:
            print(f"Cleaned {n} empty session folder(s) from data/ng_run/")

    return snapshot_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", type=int, required=True,
                    help="Phase number (1, 2, or 3)")
    ap.add_argument("--rollouts", type=Path, required=True,
                    help="Path to NeMo Gym rollouts JSONL")
    ap.add_argument("--kind", type=str, required=True,
                    help="Run kind tag (e.g. '5tasks', '20tasks')")
    ap.add_argument("--config-tag", type=str, required=True,
                    help="Short config tag (e.g. 'focalSvH')")
    ap.add_argument("--seed-tag", type=str, required=True,
                    help="Short seed tag (e.g. 'seed42')")
    ap.add_argument("--aggregate", type=Path, default=None,
                    help="Path to aggregate_metrics.json (auto-detected if omitted)")
    ap.add_argument("--materialized", type=Path, default=None,
                    help="Path to materialized_inputs.jsonl (auto-detected if omitted)")
    ap.add_argument("--no-cleanup", action="store_true",
                    help="Skip cleaning empty data/ng_run/ sessions")
    args = ap.parse_args()

    out = snapshot_run(
        phase=args.phase,
        rollouts_path=args.rollouts,
        kind=args.kind,
        config_tag=args.config_tag,
        seed_tag=args.seed_tag,
        aggregate_path=args.aggregate,
        materialized_path=args.materialized,
        cleanup_ng_run=not args.no_cleanup,
    )
    print(f"Snapshot created: {out}")
    print(f"  Contents: {sorted(p.name for p in out.iterdir())}")


if __name__ == "__main__":
    main()
