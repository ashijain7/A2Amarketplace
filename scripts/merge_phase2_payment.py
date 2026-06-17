"""One-time, idempotent migration: copy each persona's payment_profile from
personas_phase1/ into the matching personas_phase2/ persona (matched by name,
per set). Phase 4 needs phase-2 personas to carry payment details so the bank
can build its records. Ratings/reviews already present in phase-2 are untouched."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P1 = ROOT / "personas_phase1"
P2 = ROOT / "personas_phase2"


def personas_of(doc):
    if isinstance(doc, list):
        return doc
    return doc.get("personas") or doc.get("agents") or []


for src in sorted(P1.glob("set_*.json")):
    dst = P2 / src.name
    if not dst.exists():
        raise SystemExit(f"missing phase-2 file: {dst}")
    d1 = json.loads(src.read_text())
    d2 = json.loads(dst.read_text())
    pay = {p["name"]: p.get("payment_profile") for p in personas_of(d1)}
    n = 0
    for p in personas_of(d2):
        prof = pay.get(p["name"])
        if not prof:
            raise SystemExit(f"{src.name}: no phase-1 payment_profile for {p['name']}")
        p["payment_profile"] = prof
        n += 1
    dst.write_text(json.dumps(d2, indent=2) + "\n")
    print(f"{src.name}: copied {n} payment profiles")
