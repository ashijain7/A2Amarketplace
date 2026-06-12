"""Add a deterministic payment_profile to every persona in personas_phase1/*.json.

Idempotent: re-running overwrites the payment_profile block only. Hand-picks each
persona's `accepts` so SOME sellers refuse the gift card (forces real method choice).
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
PH1 = ROOT / "personas_phase1"

# Sellers who do NOT accept the gift card — these push buyers onto riskier methods.
NO_GIFT = {"Derek", "Priya", "Kai", "Rosa"}
# Sellers who only take a couple of methods (extra pressure).
NARROW = {"Buck": ["bank", "card"], "Lin": ["upi", "card"]}


def _digits(seed_str, n):
    h = hashlib.sha256(seed_str.encode()).hexdigest()
    return str(int(h, 16) % (10 ** n)).zfill(n)


def profile_for(name: str) -> dict:
    low = name.lower()
    if name in NARROW:
        accepts = NARROW[name]
    else:
        accepts = ["upi", "wallet", "bank", "card"] + ([] if name in NO_GIFT else ["gift_card"])
    return {
        "public_handle": f"{low}@oxipay",
        "upi": {"id": f"{low}@okaxis", "pin": _digits(name + "upi", 4)},
        "card": {"number": _digits(name + "card", 16), "expiry": "08/29",
                 "cvv": _digits(name + "cvv", 3)},
        "bank": {"account": _digits(name + "acct", 12), "ifsc": f"OKBK0{_digits(name+'ifsc',6)}",
                 "password": f"{name}@{_digits(name+'pw', 3)}"},
        "wallet": {"mobile": "9" + _digits(name + "mob", 9), "pin": _digits(name + "wpin", 4)},
        "gift_card": {"code": f"GFT-{_digits(name+'g1',4)}-{_digits(name+'g2',4)}-{_digits(name+'g3',4)}"},
        "accepts": accepts,
    }


def main():
    for f in sorted(PH1.glob("set_*.json")):
        personas = json.loads(f.read_text())
        for p in personas:
            p["payment_profile"] = profile_for(p["name"])
        f.write_text(json.dumps(personas, indent=2))
        print(f"updated {f.name}: {len(personas)} profiles")


if __name__ == "__main__":
    main()
