"""Scoped, symmetric, formatting-preserving focal-name swap for SwapShop (phase3).

Reads the pre-swap snapshot from the backup and writes raw-text-swapped content
into the live tree, so the ONLY change is the capitalized name tokens (no JSON
re-serialization, no formatting churn). Base64 image blobs are masked out before
swapping and restored after, so image data is never altered.

Per-set swaps (phase3 only):
  set_01: Rosa <-> Kai      set_03: Zara <-> Marcus      set_04: Buck <-> Omar
  set_02 / set_05: unchanged.
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BK = ROOT / "results/_backups/phase3_rename_20260619_rename"
BK_PR = BK / "paper_runs"
PR = ROOT / "results/paper_runs"

B64 = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
# (old_focal, new_focal, old_dirname, new_dirname)
PAIRS = {
    "set_01": ("Rosa", "Kai", "set_01_Rosa", "set_01_Kai"),
    "set_03": ("Zara", "Marcus", "set_03_Zara", "set_03_Marcus"),
    "set_04": ("Buck", "Omar", "set_04_Buck", "set_04_Omar"),
}
SKIP_SUFFIX = {".md", ".log"}


def _is_bak(name: str) -> bool:
    return name.endswith("bak")


def symswap(text: str, a: str, b: str) -> str:
    """Exchange capitalized names a<->b, leaving base64 blobs untouched."""
    blobs = []

    def stash(m):
        blobs.append(m.group(0))
        return f"\x02{len(blobs) - 1}\x03"

    masked = B64.sub(stash, text)
    swapped = masked.replace(a, "\x01").replace(b, a).replace("\x01", b)
    return re.sub(r"\x02(\d+)\x03", lambda m: blobs[int(m.group(1))], swapped)


def oneway(text: str, a: str, b: str) -> str:
    """Replace a->b only (for aggregate files that hold focal labels only)."""
    blobs = []

    def stash(m):
        blobs.append(m.group(0))
        return f"\x02{len(blobs) - 1}\x03"

    masked = B64.sub(stash, text)
    swapped = masked.replace(a, b)
    return re.sub(r"\x02(\d+)\x03", lambda m: blobs[int(m.group(1))], swapped)


def main():
    changed = 0
    # 1. persona source files
    for s, (old, new, _, _) in PAIRS.items():
        src = BK / "personas_phase3" / f"{s}.json"
        dst = ROOT / "personas_phase3" / f"{s}.json"
        dst.write_text(symswap(src.read_text(), old, new))
        changed += 1

    # 2. per-config phase3 data
    for bk_phase3 in sorted(BK_PR.glob("*/phase3")):
        cfg = bk_phase3.parent.name
        live_phase3 = PR / cfg / "phase3"

        # 2a. swapped set folders
        for s, (old, new, od, nd) in PAIRS.items():
            bdir = bk_phase3 / od
            ldir = live_phase3 / nd
            ldir.mkdir(parents=True, exist_ok=True)
            for bf in sorted(bdir.iterdir()):
                lf = ldir / bf.name
                if bf.suffix in SKIP_SUFFIX or _is_bak(bf.name):
                    shutil.copyfile(bf, lf)  # byte-identical
                else:
                    lf.write_text(symswap(bf.read_text(), old, new))
                    changed += 1

        # 2b. per-line mixed jsonl (scope each line by metadata.set_id)
        for fn in ("rollouts.jsonl", "rollouts_materialized_inputs.jsonl"):
            bf = bk_phase3 / fn
            if not bf.exists():
                continue
            out = []
            for line in bf.read_text().splitlines(keepends=True):
                stripped = line.strip()
                if not stripped:
                    out.append(line)
                    continue
                sid = json.loads(stripped)["metadata"]["set_id"]
                if sid in PAIRS:
                    old, new, _, _ = PAIRS[sid]
                    out.append(symswap(line, old, new))
                else:
                    out.append(line)  # set_02/set_05 untouched, byte-identical
            (live_phase3 / fn).write_text("".join(out))
            changed += 1

        # 2c. aggregate.json holds focal labels only -> one-way per pair
        agg = bk_phase3 / "aggregate.json"
        if agg.exists():
            t = agg.read_text()
            for s, (old, new, _, _) in PAIRS.items():
                t = oneway(t, old, new)
            (live_phase3 / "aggregate.json").write_text(t)
            changed += 1

        # 2d. files with no names -> restore byte-identical from backup
        for fn in ("rollouts_aggregate_metrics.json",):
            bf = bk_phase3 / fn
            if bf.exists():
                shutil.copyfile(bf, live_phase3 / fn)

    print(f"wrote {changed} swapped files")


if __name__ == "__main__":
    main()
