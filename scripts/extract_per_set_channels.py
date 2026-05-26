"""
For each rollout in a rollouts.jsonl, write its channel events to a
separate per-set file like `set_01_channel.jsonl`.

This makes it easy to inspect a specific persona-set's full transcript
without scrolling through the combined rollouts.jsonl.

Usage:
    python scripts/extract_per_set_channels.py \\
        --in  results/paper_runs/C1_sonnet_vs_sonnet/phase1/rollouts.jsonl \\
        --out-dir results/paper_runs/C1_sonnet_vs_sonnet/phase1/

Writes:
    <out-dir>/set_01_channel.jsonl   (with focal_persona-prefixed lines if multiple per set)
    <out-dir>/set_01_deals.json
    ... for each set in the input.

The original rollouts.jsonl is left untouched.
"""

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", type=Path, required=True,
                    help="Input rollouts.jsonl (one rollout per line)")
    ap.add_argument("--out-dir", type=Path, required=True,
                    help="Directory where per-set files are written")
    args = ap.parse_args()

    rollouts = [json.loads(l) for l in args.in_path.open()]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for r in rollouts:
        md = r.get("metadata") or {}
        set_id = md.get("set_id") or "unknown"
        focal = md.get("focal_persona") or "unknown"
        events = r.get("channel_events", []) or []
        deals = r.get("deals", []) or []

        # Sometimes deals is a dict {"deals": [...], "fulfilled_want_ids": [...]}
        if isinstance(deals, dict):
            deals = deals.get("deals", [])

        channel_path = args.out_dir / f"{set_id}_channel.jsonl"
        deals_path = args.out_dir / f"{set_id}_deals.json"

        with channel_path.open("w") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        with deals_path.open("w") as f:
            json.dump({"focal": focal, "set_id": set_id, "deals": deals},
                      f, indent=2)

        # Also write a tiny summary card per set for quick reference
        summary_path = args.out_dir / f"{set_id}_summary.json"
        with summary_path.open("w") as f:
            json.dump({
                "set_id": set_id,
                "focal_persona": focal,
                "reward": r.get("reward"),
                "rubric_scores": r.get("rubric_scores"),
                "n_events": len(events),
                "n_deals": len(deals),
                "task_id": md.get("task_id"),
                "truncation": r.get("_truncation"),
            }, f, indent=2)

        written.append((set_id, focal, len(events), len(deals)))
        print(f"  {set_id} ({focal}): {len(events)} events, {len(deals)} deals → "
              f"{channel_path.name}, {deals_path.name}, {summary_path.name}")

    print(f"\nWrote per-set files for {len(written)} rollouts to {args.out_dir}")


if __name__ == "__main__":
    main()
