"""
Phase 2: templated review generation for closed deals.

When a deal closes between a seller S and a buyer B at price P:
  - B writes a review of S (added to S.seller_reviews, S.seller_rating updates)
  - S writes a review of B (added to B.buyer_reviews, B.buyer_rating updates)

Reviews are picked from a small templated pool based on where the closing
price fell in the bid-ask zone [floor, ceiling]. No LLM call — deterministic,
cheap, easy to audit.

Rating recalculation is a running average over the persona's review list:
    new_rating = (old_rating * n_existing + this_star) / (n_existing + 1)

Mutates the persona dicts in place so subsequent state snapshots and
lookup_agent calls return the updated reputation.
"""

from __future__ import annotations

import hashlib
import random
from typing import Optional


# === Review pools by star rating ============================================
# Each review is short (1-2 lines, <150 chars) and written from the
# counterparty's perspective about a single transaction.

SELLER_REVIEWS_BY_STAR: dict[int, list[str]] = {
    5: [
        "Accepted my first reasonable offer — great seller.",
        "Sold at a great price, no fuss.",
        "Patient and friendly, smooth handoff.",
        "Honest about the item, easy deal.",
    ],
    4: [
        "Held the line but ultimately fair on price.",
        "Reasonable seller, met in the middle.",
        "Polite and direct, no surprises.",
        "Some back-and-forth but landed at a fair price.",
    ],
    3: [
        "Tough negotiator, took several rounds.",
        "Firm on price — took some convincing.",
        "Didn't move much but eventually closed.",
        "OK transaction, not the most flexible.",
    ],
    2: [
        "Pushed the price right to my limit.",
        "Wouldn't budge — paid more than I wanted.",
        "Squeezed me on price but completed the deal.",
    ],
}

BUYER_REVIEWS_BY_STAR: dict[int, list[str]] = {
    5: [
        "Paid close to asking, no haggling.",
        "Decisive and fair on price.",
        "Polite buyer, made a strong first offer.",
        "Easy to work with, would sell to again.",
    ],
    4: [
        "Polite buyer, reasonable offer.",
        "Some negotiation but agreed at a fair price.",
        "Communicative and made a decent offer.",
        "Bargained a bit but landed quickly.",
    ],
    3: [
        "Pushed the price down but agreed in the end.",
        "Took a few rounds to reach a price.",
        "Asked for a discount, accepted my counter.",
        "Bargained hard but reasonable.",
    ],
    2: [
        "Lowballed but ultimately accepted my counter.",
        "Negotiated hard — barely above my floor.",
        "Pressed for a deep discount.",
    ],
}


# === Star scoring from deal economics =======================================

def _seller_star_from_deal(price: float, floor: float, ceiling: float) -> int:
    """How well did the seller do? Higher star = closer to ceiling (good for seller).

    Returns 2..5.
    """
    if ceiling is None or floor is None or ceiling <= floor:
        return 4  # neutral fallback when zone is undefined
    pos = (price - floor) / (ceiling - floor)  # 0 = floor, 1 = ceiling
    pos = max(0.0, min(1.0, pos))
    if pos >= 0.85:
        return 5
    if pos >= 0.55:
        return 4
    if pos >= 0.25:
        return 3
    return 2


def _buyer_star_from_deal(price: float, floor: float, ceiling: float) -> int:
    """How well did the buyer do? Higher star (from seller's POV) = paid more.

    Returns 2..5. This is the SELLER's rating of the buyer — so a buyer who
    paid near the ceiling gets a high star from the seller's perspective
    ("decisive, fair on price"), while a buyer who lowballed gets 2-3.
    """
    if ceiling is None or floor is None or ceiling <= floor:
        return 4
    pos = (price - floor) / (ceiling - floor)
    pos = max(0.0, min(1.0, pos))
    if pos >= 0.75:
        return 5
    if pos >= 0.45:
        return 4
    if pos >= 0.20:
        return 3
    return 2


# === Public API =============================================================

def _pick_review(pool: list[str], deal_id: str, side: str) -> str:
    """Deterministically pick a review from the pool, keyed on deal+side so
    re-runs reproduce the same review text."""
    h = hashlib.sha256(f"{deal_id}|{side}".encode()).digest()
    seed = int.from_bytes(h[:8], "big")
    return random.Random(seed).choice(pool)


def update_running_rating(persona: dict, role: str, new_star: float) -> None:
    """Update persona's role_rating field with a new star value as a running
    average over the existing reviews. Rounds to one decimal."""
    rating_key = f"{role}_rating"
    reviews_key = f"{role}_reviews"
    n_existing = len(persona.get(reviews_key, []))
    old_rating = float(persona.get(rating_key, 4.0))
    new_avg = (old_rating * n_existing + new_star) / (n_existing + 1)
    persona[rating_key] = round(new_avg, 1)


def generate_and_apply_deal_reviews(
    *,
    deal_id: str,
    seller_persona: Optional[dict],
    buyer_persona: Optional[dict],
    price: float,
    seller_floor: float,
    buyer_ceiling: float,
) -> dict:
    """Generate reviews for both sides of a closed deal and mutate the
    persona dicts in place.

    Returns a dict describing what was applied (for logging/tests):
        {
          "seller_review": {"star": int, "text": str, "applied_to": seller_name},
          "buyer_review":  {"star": int, "text": str, "applied_to": buyer_name},
        }

    If either persona is None, this is a no-op for that side.
    """
    out = {}

    if seller_persona is not None:
        s_star = _seller_star_from_deal(price, seller_floor, buyer_ceiling)
        s_text = _pick_review(SELLER_REVIEWS_BY_STAR[s_star], deal_id, "seller")
        seller_persona.setdefault("seller_reviews", [])
        update_running_rating(seller_persona, "seller", s_star)
        seller_persona["seller_reviews"].append(s_text)
        out["seller_review"] = {
            "star": s_star, "text": s_text,
            "applied_to": seller_persona.get("name"),
        }

    if buyer_persona is not None:
        b_star = _buyer_star_from_deal(price, seller_floor, buyer_ceiling)
        b_text = _pick_review(BUYER_REVIEWS_BY_STAR[b_star], deal_id, "buyer")
        buyer_persona.setdefault("buyer_reviews", [])
        update_running_rating(buyer_persona, "buyer", b_star)
        buyer_persona["buyer_reviews"].append(b_text)
        out["buyer_review"] = {
            "star": b_star, "text": b_text,
            "applied_to": buyer_persona.get("name"),
        }

    return out


def has_review_data(persona: dict) -> bool:
    """True iff this persona has phase-2 review fields (used to gate
    reputation features so phase 1 personas pass through unchanged)."""
    return "seller_rating" in persona or "buyer_rating" in persona
