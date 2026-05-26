"""
Phase 3 swap-validity logic.

A swap proposal is valid when the proposer's item belongs to a category
the target listing has declared it would accept (in its `wants` array).

This is intentionally small — category-level matching only, not item-level
matching. The agents can still propose semantically nonsense swaps within
a valid category, and that's part of what the verifier scores.
"""

from typing import Optional


VALID_CATEGORIES = {"tops", "bottoms", "dresses", "outerwear", "shoes", "bags"}


def normalize_category(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    c = c.strip().lower()
    return c if c in VALID_CATEGORIES else None


def is_valid_swap(my_item_category: str,
                  listing_wants: list[str]) -> tuple[bool, str]:
    """Return (ok, reason). ok=True means proposing this swap is allowed.

    Validation:
      - my_item_category must be a known category
      - listing_wants must contain at least one matching category
    """
    my_cat = normalize_category(my_item_category)
    if my_cat is None:
        return False, f"unknown category for proposer's item: '{my_item_category}'"
    norm_wants = {normalize_category(w) for w in (listing_wants or [])}
    norm_wants.discard(None)
    if not norm_wants:
        return False, "listing has no declared wants — cannot accept swaps"
    if my_cat not in norm_wants:
        return False, (
            f"category '{my_cat}' not in listing wants "
            f"{sorted(norm_wants)}"
        )
    return True, "match"


def items_match_persona_want(item_category: str,
                              persona_wants: list[dict]) -> Optional[dict]:
    """Find the persona's want entry that matches a given item category.
    Returns the matching want dict, or None.

    Used by the verifier to look up the persona's `ceiling_price` (private
    valuation) for whatever they swapped FOR.
    """
    cat = normalize_category(item_category)
    if cat is None:
        return None
    for w in persona_wants or []:
        if normalize_category(w.get("want_category")) == cat:
            return w
    return None
