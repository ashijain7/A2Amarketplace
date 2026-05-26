"""
Re-score the privacy rubric on existing rollouts using the fixed
compute_privacy logic.

WHY THIS EXISTS
---------------
The pre-fix `compute_privacy` had three bugs that produced false-positive
"leak" reports on Phase 1/2/3 runs:
  1. Searched the formatted transcript (which includes turn markers like
     '[t36]') so an `age: 36` private value matched the turn-36 prefix.
  2. Used a naive substring match, so any numeric value matched inside
     larger numbers or alphanumeric IDs.
  3. Searched the WHOLE channel (every agent), so an opponent mentioning
     a value got attributed to the focal.

The fixed `compute_privacy` (a) restricts to the focal's own message
text, (b) uses a word-boundary regex, and (c) keeps boundary_violations
unchanged. This script applies that fix to existing rollouts.jsonl
files in-place (with a .bak backup) and rebuilds per-run summary.json.

USAGE
-----
  python scripts/rescore_privacy.py results/phase1/run_5tasks_*/rollouts.jsonl
  python scripts/rescore_privacy.py results/phase2/.../rollouts.jsonl
  python scripts/rescore_privacy.py results/phase3/.../rollouts.jsonl

Pass --dry-run to just report deltas without writing.
Pass --include-paraphrase to ALSO re-run the GPT-4o paraphrase judge
(requires API credit; defaults to off).

The script:
  - reads the snapshot's rollouts.jsonl
  - reconstructs a Channel from each rollout's channel_events
  - pulls the focal persona from rollout.personas
  - re-runs compute_privacy with the fixed code (stubbing the
    paraphrase judge to return False UNLESS --include-paraphrase)
  - preserves the OLD boundary_violations + boundary_score
    (those values were correct; only the exact/paraphrase leak
    detection had bugs)
  - updates rubric_scores.privacy AND final_reward
  - writes corrected rollouts.jsonl (with .bak of original)
  - rebuilds per-run summary.json files
  - prints before/after comparison
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from marketplace.channel import Channel, ChannelEvent
from resources_server.verifiers import compute_privacy, compute_final_reward


def _reconstruct_channel(channel_events: list[dict], tmp_path: Path) -> Channel:
    """Build a Channel object from a list of dict events (as stored in
    rollouts.jsonl)."""
    ch = Channel(path=tmp_path / "tmp_channel.jsonl")
    ch.clear()
    for ev in channel_events:
        # Skip 'timestamp' on reconstruct — irrelevant for verifier
        ch.events.append(ChannelEvent(
            turn=ev.get("turn", 0),
            event_id=ev.get("event_id", ""),
            agent=ev.get("agent", ""),
            action=ev.get("action", "pass"),
            target=ev.get("target"),
            price=ev.get("price"),
            message=ev.get("message", "") or "",
            wants=ev.get("wants"),
            image_path=ev.get("image_path"),
            swap_item_id=ev.get("swap_item_id"),
        ))
    return ch


def _recompute_one(rollout: dict, include_paraphrase: bool, tmp_path: Path) -> dict:
    """Return a copy of the rollout with corrected privacy + final_reward."""
    md = rollout.get("metadata", {})
    focal_name = md.get("focal_persona")
    personas = rollout.get("personas") or []
    focal = next((p for p in personas if p.get("name") == focal_name), None)
    if focal is None:
        return rollout

    ch = _reconstruct_channel(rollout.get("channel_events", []) or [], tmp_path)
    old_priv = (rollout.get("rubric_scores") or {}).get("privacy") or {}
    old_boundary_violations = old_priv.get("boundary_violations", 0) or 0

    # Stub the paraphrase judge unless explicitly enabled. Stub boundary
    # judge to RETURN the original value (it was correct).
    paraphrase_patch = patch(
        "resources_server.verifiers._judge_paraphrase_match",
        side_effect=(None if include_paraphrase else (lambda *_a, **_kw: False)),
    )
    boundary_patch = patch(
        "resources_server.verifiers._judge_boundary_violations",
        return_value=int(old_boundary_violations),
    )
    with paraphrase_patch as _pp, boundary_patch as _bp:
        if include_paraphrase:
            # Pass-through to real judge function
            _pp.side_effect = None
        new_priv = compute_privacy(focal, ch, judge_model=focal.get("__judge", "openai/gpt-4o-2024-11-20"))

    new_rs = dict(rollout.get("rubric_scores") or {})
    new_rs["privacy"] = new_priv

    # Recompute final_reward with corrected privacy combined.
    phase = int(md.get("phase") or 1)
    parts = {
        "deal_outcomes": (new_rs.get("deal_outcomes") or {}).get("combined")
                          if isinstance(new_rs.get("deal_outcomes"), dict)
                          else new_rs.get("deal_outcomes"),
        "capability_asymmetry": (new_rs.get("capability_asymmetry") or {}).get("combined")
                                if isinstance(new_rs.get("capability_asymmetry"), dict)
                                else new_rs.get("capability_asymmetry"),
        "negotiation_quality": (new_rs.get("negotiation_quality") or {}).get("combined")
                                if isinstance(new_rs.get("negotiation_quality"), dict)
                                else new_rs.get("negotiation_quality"),
        "privacy": new_priv.get("combined"),
        "review_utilization": (new_rs.get("review_utilization") or {}).get("combined")
                              if isinstance(new_rs.get("review_utilization"), dict)
                              else new_rs.get("review_utilization"),
        "swap_quality": (new_rs.get("swap_quality") or {}).get("combined")
                        if isinstance(new_rs.get("swap_quality"), dict)
                        else new_rs.get("swap_quality"),
    }
    new_final = compute_final_reward(parts, phase=phase)
    new_rs["final_reward"] = new_final

    out = dict(rollout)
    out["rubric_scores"] = new_rs
    out["reward"] = new_final
    return out


def _summarize_delta(old: dict, new: dict) -> str:
    op = old.get("rubric_scores", {}).get("privacy") or {}
    np = new.get("rubric_scores", {}).get("privacy") or {}
    md = new.get("metadata", {})
    name = md.get("focal_persona", "?")
    old_leaks = op.get("leaks_found", "?")
    new_leaks = np.get("leaks_found", "?")
    old_c = op.get("combined")
    new_c = np.get("combined")
    old_r = old.get("reward")
    new_r = new.get("reward")

    def _f(x):
        if x is None:
            return "N/A"
        return f"{x:.3f}" if isinstance(x, float) else str(x)

    return (
        f"  {name:8s}  leaks: {old_leaks}→{new_leaks}   "
        f"privacy.combined: {_f(old_c)}→{_f(new_c)}   "
        f"reward: {_f(old_r)}→{_f(new_r)}"
    )


def rescore_jsonl(path: Path, include_paraphrase: bool, dry_run: bool) -> None:
    path = Path(path)
    if not path.exists():
        print(f"  SKIP — not found: {path}")
        return
    rollouts = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rollouts:
        print(f"  SKIP — empty: {path}")
        return

    tmp = path.parent / "_rescore_tmp"
    tmp.mkdir(exist_ok=True)

    print(f"\n=== {path} ({len(rollouts)} rollouts) ===")
    new_rollouts = []
    for r in rollouts:
        new_r = _recompute_one(r, include_paraphrase=include_paraphrase, tmp_path=tmp)
        new_rollouts.append(new_r)
        print(_summarize_delta(r, new_r))

    # Cleanup tmp
    shutil.rmtree(tmp, ignore_errors=True)

    if dry_run:
        print("  (dry-run — no write)")
        return

    bak = path.with_suffix(path.suffix + ".pre_privacy_rescore.bak")
    if not bak.exists():
        shutil.copy2(path, bak)
        print(f"  → backup: {bak.name}")
    with path.open("w") as f:
        for r in new_rollouts:
            f.write(json.dumps(r) + "\n")
    print(f"  → wrote corrected: {path.name}")


def rearchive_snapshot(rollouts_path: Path) -> None:
    """Rebuild the per-run summary.json files under <snapshot>/runs/ from
    the corrected rollouts.jsonl. Uses the existing archive_run helper."""
    from scripts.archive_run import archive_jsonl
    snapshot_dir = rollouts_path.parent
    runs_dir = snapshot_dir / "runs"
    if not runs_dir.exists():
        print(f"  (no runs/ dir to re-archive at {runs_dir})")
        return
    # Wipe existing per-run folders for clean re-archive
    for sub in runs_dir.iterdir():
        if sub.is_dir():
            shutil.rmtree(sub)
    archive_jsonl(rollouts_path, runs_dir=runs_dir)
    print(f"  → re-archived {len(list(runs_dir.iterdir()))} per-run folders")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+",
                    help="Path(s) to rollouts.jsonl OR snapshot directories.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print deltas, don't write.")
    ap.add_argument("--include-paraphrase", action="store_true",
                    help="Also re-run the GPT-4o paraphrase judge (costs API credit).")
    ap.add_argument("--no-rearchive", action="store_true",
                    help="Skip rebuilding per-run summary.json files after rescore.")
    args = ap.parse_args()

    paths = []
    for t in args.targets:
        p = Path(t)
        if p.is_dir():
            cand = p / "rollouts.jsonl"
            if cand.exists():
                paths.append(cand)
            else:
                print(f"  SKIP {p}: no rollouts.jsonl inside")
        else:
            paths.append(p)

    for path in paths:
        rescore_jsonl(path, include_paraphrase=args.include_paraphrase,
                       dry_run=args.dry_run)
        if not args.dry_run and not args.no_rearchive:
            rearchive_snapshot(path)


if __name__ == "__main__":
    main()
