#!/usr/bin/env python3
"""Quick post-run validator for a transactional run — no rollout, just reads the output.

Asserts the things the rebuild guarantees, so a broken run fails LOUDLY instead of
silently producing 1.0s:
  - every focal deal has a non-empty private room
  - every focal-BUYER deal paid a recipient that was actually spoken in the room (pay-gate)
  - on a scam run, every focal deal saw at least one scammer attempt

Validates THIS run's data — from its rollouts.jsonl, where each rollout carries its OWN
settlement_records + focal. A run that closed no focal deals says so honestly instead of
falsely passing on a stale file left over from a previous run.

Usage:
  scripts/settlement_validate.py <rollouts.jsonl>                  # preferred — this run
  scripts/settlement_validate.py <settlement.json> [--focal NAME]  # ad-hoc single set
"""
import json
import os
import sys
from collections import Counter


def _infer_focal(records):
    """The focal is the one party present in EVERY focal record (for ad-hoc settlement.json)."""
    counts = Counter()
    for r in records:
        counts[r["buyer"]] += 1
        counts[r["seller"]] += 1
    full = [name for name, c in counts.items() if c == len(records)]
    return full[0] if len(full) == 1 else None


def _check_set(records, focal, label):
    """Validate one focal's settlement records. Prints results; returns the fail count."""
    fails, warns = [], []
    if not records:
        warns.append("focal closed no settlement deals — nothing to validate (run produced no signal)")
    if focal is None and records:
        warns.append("could not infer the focal — pass --focal NAME")
        records = []
    scam_run = any(r.get("scam_on") for r in records)

    for r in records:
        did = r.get("deal_id")
        room = r.get("room", [])
        if len(room) == 0:
            fails.append(f"{did}: empty room (the room is supposed to be mandatory)")
        if r.get("buyer") == focal and r.get("stage") in ("PAID", "CONFIRMED"):
            recip = r.get("recipient_typed")
            if recip and not any(str(recip) in (m.get("text") or "") for m in room):
                fails.append(f"{did}: paid '{recip}' but it was never spoken in the room (pay-gate breach)")
        if scam_run and r.get("scam_on"):
            if not (r.get("scam_injections", 0) > 0 or r.get("scam_tactics")):
                fails.append(f"{did}: scam run but the scammer never took a turn")

    print(f"  {label}: focal={focal}  deals={len(records)}  scam_run={scam_run}")
    for w in warns:
        print(f"    WARN  {w}")
    for f in fails:
        print(f"    FAIL  {f}")
    if records and not fails:
        print(f"    PASS  all {len(records)} focal deals have a real room"
              + (" + a scammer turn" if scam_run else "") + "; pay-gate intact")
    return len(fails)


def validate_rollouts(path):
    """Validate every rollout in a rollouts.jsonl using its OWN settlement_records + focal."""
    print(f"validating run: {path}")
    rollouts = [json.loads(l) for l in open(path) if l.strip()]
    if not rollouts:
        print("  FAIL  no rollouts in file")
        return 1
    fails = 0
    for r in rollouts:
        md = r.get("metadata") or {}
        fails += _check_set(r.get("settlement_records") or [], md.get("focal_persona"),
                            md.get("set_id") or "set")
    return 0 if fails == 0 else 1


def validate_settlement_json(path, focal=None):
    data = json.load(open(path))
    records = data.get("records") or data.get("deals") or []
    print(f"validating file: {path}")
    return 0 if _check_set(records, focal or _infer_focal(records), "set") == 0 else 1


if __name__ == "__main__":
    argv = sys.argv[1:]
    focal = None
    if "--focal" in argv:
        i = argv.index("--focal")
        focal = argv[i + 1] if i + 1 < len(argv) else None
        argv = [a for a in argv if a not in ("--focal", focal)]
    if not argv or not os.path.exists(argv[0]):
        print("usage: settlement_validate.py <rollouts.jsonl | settlement.json>")
        sys.exit(2)
    path = argv[0]
    sys.exit(validate_rollouts(path) if path.endswith(".jsonl")
             else validate_settlement_json(path, focal))
