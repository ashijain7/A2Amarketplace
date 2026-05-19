"""
Build personas_phase2/ from personas_phase1/ by adding seller/buyer rating
and review fields.

Each persona gets:
  - seller_rating : float in [3.5, 4.8], one decimal, deterministic from name
  - seller_reviews: 2-3 short strings (1-2 lines each, <=150 chars)
  - buyer_rating  : float in [3.5, 4.8]
  - buyer_reviews : 2-3 short strings

Reviews are templated and sampled with a name-seeded RNG so the same persona
always gets the same baseline reputation across runs. Re-run this script
freely; output is reproducible.

Usage:
    python scripts/generate_phase2_personas.py
"""

import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "personas_phase1"
DST = ROOT / "personas_phase2"
SETS = ["set_01", "set_02", "set_03", "set_04", "set_05"]


# === Review pools ===========================================================
# Each entry: (text, min_rating)  — only used when persona's rating >= min_rating
# Reviews are written from the perspective of the OTHER party in a past deal.

SELLER_REVIEWS_POSITIVE = [
    "Quick reply, item exactly as described.",
    "Smooth transaction at a fair price.",
    "Honest about condition — would buy again.",
    "Held firm but ultimately fair on price.",
    "Polite throughout, easy seller.",
    "Item shipped fast, clean handoff.",
    "Clear listing and met me at a reasonable price.",
    "No drama, no hidden issues. Solid.",
    "Patient with my questions before I committed.",
    "Knew their item's value and stood by it — fair seller.",
]

SELLER_REVIEWS_MIXED = [
    "Took a while to respond but item was OK.",
    "A bit firm on price but description was accurate.",
    "Communicative but slow to decide on counter-offers.",
    "Listing photos could've been better — item itself fine.",
    "Decent transaction, nothing special either way.",
]

SELLER_REVIEWS_NEGATIVE = [
    "Slow to respond — almost gave up.",
    "Price didn't budge at all, felt overpriced.",
    "Pushed back on every small ask.",
]

BUYER_REVIEWS_POSITIVE = [
    "Paid promptly, easy buyer.",
    "Polite and decisive — knew what they wanted.",
    "No haggling, straight to the deal.",
    "Clear communication throughout.",
    "Fair on the first offer, no time wasted.",
    "Friendly buyer, smooth pickup.",
    "Made a reasonable offer right away.",
    "Trusted the listing and didn't nitpick.",
    "Easy to work with, would sell to again.",
    "Patient buyer, accommodating on details.",
]

BUYER_REVIEWS_MIXED = [
    "Bargained hard but fair in the end.",
    "Took a few rounds to land on a price.",
    "Asked a lot of questions before committing.",
    "Polite but slow to decide.",
    "Pushed for a discount but accepted reasonable price.",
]

BUYER_REVIEWS_NEGATIVE = [
    "Lowballed initially, took several rounds.",
    "Backed out after asking lots of questions.",
    "Took forever to make a decision.",
]


def _seeded_rng(name: str, role: str) -> random.Random:
    """Deterministic per-(persona, role) RNG so the same person/role always
    gets the same baseline."""
    h = hashlib.sha256(f"{name}|{role}".encode()).digest()
    seed = int.from_bytes(h[:8], "big")
    return random.Random(seed)


def _generate_rating(name: str, role: str) -> float:
    """Rating in [3.5, 4.8], one decimal, biased by persona name."""
    rng = _seeded_rng(name, role + "/rating")
    # 0.6 weight on the upper band so most agents have decent reputations
    if rng.random() < 0.6:
        return round(rng.uniform(4.0, 4.8), 1)
    else:
        return round(rng.uniform(3.5, 4.0), 1)


def _generate_reviews(name: str, role: str, rating: float) -> list[str]:
    """Pick 2-3 reviews matching the rating bucket."""
    rng = _seeded_rng(name, role + "/reviews")
    if role == "seller":
        pos, mix, neg = SELLER_REVIEWS_POSITIVE, SELLER_REVIEWS_MIXED, SELLER_REVIEWS_NEGATIVE
    else:
        pos, mix, neg = BUYER_REVIEWS_POSITIVE, BUYER_REVIEWS_MIXED, BUYER_REVIEWS_NEGATIVE

    n_reviews = rng.choice([2, 3])
    if rating >= 4.5:
        # 2-3 strongly positive
        return rng.sample(pos, k=n_reviews)
    elif rating >= 4.0:
        # mostly positive, one mixed
        out = rng.sample(pos, k=max(1, n_reviews - 1))
        out.append(rng.choice(mix))
        rng.shuffle(out)
        return out
    else:
        # one positive, one mixed, maybe one negative
        out = [rng.choice(pos), rng.choice(mix)]
        if n_reviews == 3:
            out.append(rng.choice(neg))
        rng.shuffle(out)
        return out


def enrich_persona(persona: dict) -> dict:
    """Return a new dict = persona + rating/review fields. Original untouched."""
    out = dict(persona)
    name = persona["name"]
    seller_rating = _generate_rating(name, "seller")
    buyer_rating = _generate_rating(name, "buyer")
    out["seller_rating"] = seller_rating
    out["seller_reviews"] = _generate_reviews(name, "seller", seller_rating)
    out["buyer_rating"] = buyer_rating
    out["buyer_reviews"] = _generate_reviews(name, "buyer", buyer_rating)
    return out


def main():
    DST.mkdir(parents=True, exist_ok=True)
    total = 0
    for set_id in SETS:
        src_path = SRC / f"{set_id}.json"
        dst_path = DST / f"{set_id}.json"
        personas = json.loads(src_path.read_text())
        enriched = [enrich_persona(p) for p in personas]
        dst_path.write_text(json.dumps(enriched, indent=2))
        total += len(enriched)
        print(f"  {set_id}: wrote {len(enriched)} personas → {dst_path.name}")
    print(f"Done. {total} personas enriched.")


if __name__ == "__main__":
    main()
