#!/usr/bin/env python3
"""Quick post-run validator for a settlement run — no rollout, just reads the output.

Asserts the things the rebuild guarantees, so a broken run fails LOUDLY instead of
silently producing 1.0s:
  - the focal closed at least one settlement deal
  - every focal deal has a non-empty private room
  - every focal-BUYER deal paid a recipient that was actually spoken in the room (pay-gate)
  - on a scam run, every focal deal saw at least one scammer attempt

Usage:
  scripts/settlement_validate.py [path/to/settlement.json] [--focal NAME]
  (with no path, uses the newest data/ng_run/*/settlement.json)
"""
import glob
import json
import os
import sys
from collections import Counter


def _newest_settlement():
    files = glob.glob("data/ng_run/*/settlement.json")
    return max(files, key=os.path.getmtime) if files else None


def _infer_focal(records):
    """The focal is the one party present in EVERY focal record."""
    counts = Counter()
    for r in records:
        counts[r["buyer"]] += 1
        counts[r["seller"]] += 1
    full = [name for name, c in counts.items() if c == len(records)]
    return full[0] if len(full) == 1 else None


def validate(path, focal=None):
    data = json.load(open(path))
    records = data.get("records") or data.get("deals") or []
    focal = focal or _infer_focal(records)
    fails, warns = [], []

    if not records:
        warns.append("focal closed no settlement deals (nothing to validate)")
    if focal is None:
        warns.append("could not infer the focal — pass --focal NAME to check pay-gate/rooms")
        records = []

    scam_run = any(r.get("scam_on") for r in records)

    for r in records:
        did = r.get("deal_id")
        room = r.get("room", [])
        is_buyer = r.get("buyer") == focal

        if len(room) == 0:
            fails.append(f"{did}: empty room (the room is supposed to be mandatory)")

        if is_buyer and r.get("stage") in ("PAID", "CONFIRMED"):
            recip = r.get("recipient_typed")
            seen = any(str(recip) in (m.get("text") or "") for m in room)
            if recip and not seen:
                fails.append(f"{did}: paid '{recip}' but it was never spoken in the room (pay-gate breach)")

        if scam_run and r.get("scam_on"):
            attempted = r.get("scam_injections", 0) > 0 or bool(r.get("scam_tactics"))
            if not attempted:
                fails.append(f"{did}: scam run but the scammer never took a turn")

    print(f"validating: {path}")
    print(f"focal: {focal}   deals: {len(records)}   scam_run: {scam_run}")
    for w in warns:
        print(f"  WARN  {w}")
    for f in fails:
        print(f"  FAIL  {f}")
    if not fails:
        print(f"  PASS  all {len(records)} focal deals have a real room"
              + (" + a scammer turn" if scam_run else "") + "; pay-gate intact")
    return 0 if not fails else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--focal"]
    focal = None
    if "--focal" in sys.argv:
        i = sys.argv.index("--focal")
        focal = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        args = [a for a in args if a != focal]
    path = args[0] if args else _newest_settlement()
    if not path or not os.path.exists(path):
        print("no settlement.json found")
        sys.exit(2)
    sys.exit(validate(path, focal))
