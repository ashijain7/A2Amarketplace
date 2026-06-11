"""
READ-ONLY privacy re-score comparison.

Re-runs the FIXED compute_privacy (edge-tolerant exact match + currency
match + tightened paraphrase judge + live boundary judge, all fail-loud)
over every paper-run rollout and prints old-vs-new for the privacy rubric.
Writes nothing — this is the comparison pass the user reviews before any
in-place rescore.

Usage:
  python scripts/compare_privacy_rescore.py
  python scripts/compare_privacy_rescore.py results/paper_runs/C7_gemini_vs_gpt55
"""

import glob
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from marketplace.channel import Channel, ChannelEvent
from marketplace import config
from resources_server.verifiers import compute_privacy


def reconstruct_channel(events, tmp_path):
    ch = Channel(path=tmp_path / "tmp.jsonl")
    ch.clear()
    for ev in events or []:
        ch.events.append(ChannelEvent(
            turn=ev.get("turn", 0), event_id=ev.get("event_id", ""),
            agent=ev.get("agent", ""), action=ev.get("action", "pass"),
            target=ev.get("target"), price=ev.get("price"),
            message=ev.get("message", "") or "", wants=ev.get("wants"),
            image_path=ev.get("image_path"), swap_item_id=ev.get("swap_item_id"),
        ))
    return ch


def main():
    targets = sys.argv[1:] or ["results/paper_runs"]
    files = []
    for t in targets:
        p = Path(t)
        files += [Path(f) for f in glob.glob(str(p / "**/rollouts.jsonl"), recursive=True)] \
            if p.is_dir() else [p]
    files = sorted(set(files))

    tmp = Path(tempfile.mkdtemp())
    rows, changed, errors = [], [], []
    n_applic = 0

    for f in files:
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            md = r.get("metadata", {})
            old = (r.get("rubric_scores") or {}).get("privacy") or {}
            if not old.get("applicable"):
                continue
            n_applic += 1
            focal_name = md.get("focal_persona")
            focal = next((p for p in (r.get("personas") or [])
                          if p.get("name") == focal_name), None)
            tag = f"{f.parent.parent.name}/{f.parent.name}/{focal_name}"
            if not focal or not focal.get("private"):
                errors.append(f"{tag}: focal/private missing")
                continue
            ch = reconstruct_channel(r.get("channel_events"), tmp)
            try:
                new = compute_privacy(focal, ch, judge_model=config.JUDGE_MODEL)
            except Exception as e:  # fail-loud surfaced — record, don't fake clean
                errors.append(f"{tag}: JUDGE ERROR {type(e).__name__}: {e}")
                continue
            row = (tag, old.get("leaks_found", 0), new["leaks_found"],
                   old.get("combined"), new["combined"],
                   old.get("boundary_violations", 0), new["boundary_violations"],
                   new.get("leak_details"))
            rows.append(row)
            if (old.get("leaks_found", 0) != new["leaks_found"]
                    or old.get("boundary_violations", 0) != new["boundary_violations"]):
                changed.append(row)

    print(f"\nApplicable rollouts re-scored: {n_applic}   errors: {len(errors)}\n")
    print(f"{'run':45} {'leaks o→n':10} {'priv o→n':16} {'bnd o→n':8}")
    print("-" * 90)
    for tag, ol, nl, oc, nc, ob, nb, det in rows:
        mark = "  <==" if (ol != nl or ob != nb) else ""
        oc_s = f"{oc:.3f}" if isinstance(oc, float) else str(oc)
        nc_s = f"{nc:.3f}" if isinstance(nc, float) else str(nc)
        print(f"{tag:45} {ol}→{nl:<8} {oc_s}→{nc_s:<10} {ob}→{nb}{mark}")
        if det:
            print(f"      detail: {det}")

    clean_new = sum(1 for r in rows if r[2] == 0)
    print("\n=== SUMMARY ===")
    print(f"  applicable: {len(rows)}")
    print(f"  scored 1.00 / no leak (new): {clean_new}/{len(rows)}")
    print(f"  rows that CHANGED vs recorded: {len(changed)}")
    for c in changed:
        print(f"    CHANGED {c[0]}: leaks {c[1]}→{c[2]}, bnd {c[5]}→{c[6]}, priv {c[3]}→{c[4]}")
    if errors:
        print(f"  ERRORS ({len(errors)}):")
        for e in errors:
            print("    ", e)


if __name__ == "__main__":
    main()
