"""
Build personas_phase3/ from personas_phase2/ + the DeepFashion image set.

Each persona is rewritten so its items_to_sell and items_to_buy reference
clothing items with image paths. The transformation is **deterministic**
(seeded by persona name + set_id) so re-runs reproduce the same assignment.

Inputs:
  personas_phase2/set_*.json  — persona shells (name, style, ratings, reviews)
  data/item_images/manifest.json  — 100 fashion items across 4 categories

Outputs:
  personas_phase3/set_*.json  — same shape as phase 2 + image_path / category /
                                want_category on items.

Schema:
  {
    "name": ...,
    "style": ...,
    "items_to_sell": [{
      "item_id":     "set01_kai_dress_01",
      "name":        "Black dress with sequined sleeves",
      "category":    "dresses",
      "floor_price": 38,                          // PRIVATE valuation
      "image_path":  "data/item_images/dresses/..jpg"
    }],
    "items_to_buy": [{
      "want_id":        "set01_kai_want_top",
      "description":    "Looking for tops or blouses",
      "want_category":  "tops",
      "ceiling_price":  30                        // PRIVATE valuation
    }, ...],
    "seller_rating":  4.6,
    "seller_reviews": [...],   // preserved from phase 2
    "buyer_rating":   4.7,
    "buyer_reviews":  [...]
  }

Guarantee: every persona has at least one tradeable counterparty in its
set. The script aborts if it can't produce a closed want-graph.
"""

import hashlib
import json
import random
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
SRC = ROOT / "personas_phase2"
DST = ROOT / "personas_phase3"
MANIFEST = ROOT / "data" / "item_images" / "manifest.json"
SETS = ["set_01", "set_02", "set_03", "set_04", "set_05"]

# Internal valuation ranges per category — used for both seller floors and
# buyer ceilings. Floors are drawn from the lower half; ceilings from the
# upper half — so the bid-ask zones overlap and swaps can be win-win.
VALUE_RANGES = {
    "tops":      (15, 40),
    "bottoms":   (25, 60),
    "dresses":   (30, 80),
    "outerwear": (40, 100),
}


def _seeded_rng(*keys) -> random.Random:
    """Deterministic RNG from a stable string key."""
    h = hashlib.sha256("|".join(str(k) for k in keys).encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def _shorten_caption(caption: str, category: str) -> str:
    """Turn 'a woman wearing a blue top and white pants' into 'blue top'.

    Heuristic: find the first phrase like '<color/material> <category-singular>'
    in the caption. If nothing matches, fall back to a generic name.
    """
    cap = caption.lower()
    # category names appear in captions sometimes plural sometimes not
    singular_map = {
        "tops": ["top", "shirt", "blouse", "t-shirt", "tee", "tank top"],
        "bottoms": ["pants", "jeans", "trousers", "shorts", "skirt"],
        "dresses": ["dress", "gown", "jumpsuit"],
        "outerwear": ["jacket", "coat", "hoodie", "sweater", "cardigan", "blazer"],
    }
    candidates = singular_map.get(category, [])
    # Try to grab one or two preceding adjectives
    for kw in candidates:
        m = re.search(r"(\b\w+\b)?\s*(\b\w+\b)?\s*\b" + re.escape(kw) + r"\b", cap)
        if m:
            adj1 = m.group(1) or ""
            adj2 = m.group(2) or ""
            # Skip articles/fillers
            adj1 = "" if adj1 in {"a", "an", "the", "in", "with", "wearing"} else adj1
            adj2 = "" if adj2 in {"a", "an", "the", "in", "with", "wearing"} else adj2
            phrase = " ".join(x for x in [adj1, adj2, kw] if x)
            return phrase.strip().title()
    # Fallback
    return category[:-1].title() if category.endswith("s") else category.title()


def _pick_value(rng: random.Random, category: str, role: str) -> int:
    """role='seller' → lower half of range (floor); 'buyer' → upper half (ceiling)."""
    lo, hi = VALUE_RANGES[category]
    mid = (lo + hi) // 2
    if role == "seller":
        return rng.randint(lo, mid)
    else:
        return rng.randint(mid, hi)


def assign_set(set_id: str, personas: list[dict],
               images_by_cat: dict[str, list[dict]]) -> list[dict]:
    """For one set of 10 personas, produce phase 3 personas.

    Strategy:
      1. Sort personas by name (stable order).
      2. Assign each persona a sell-category in a round-robin across the
         4 categories — guarantees ~equal sell distribution.
      3. Pick a specific image for the sell-item using a per-(set, persona) seed.
      4. Give each persona 2 wants drawn from the categories OTHER personas
         in this set are selling (guarantees a buyer for every seller).
      5. Make sure each persona's wants don't include their own category
         (no point wanting what you're selling).
    """
    personas_sorted = sorted(personas, key=lambda p: p["name"])
    categories = list(VALUE_RANGES.keys())  # ['tops','bottoms','dresses','outerwear']

    # Round-robin sell assignment
    sell_cats = {}
    for i, p in enumerate(personas_sorted):
        sell_cats[p["name"]] = categories[i % len(categories)]

    # All categories present in this set's seller pool
    present_cats = set(sell_cats.values())

    out: list[dict] = []
    image_cursors: dict[str, int] = defaultdict(int)  # per-cat index into image list

    for p in personas_sorted:
        rng = _seeded_rng(set_id, p["name"])
        sell_cat = sell_cats[p["name"]]
        # Pick image deterministically per (set, persona). Cycle through images.
        imgs = images_by_cat[sell_cat]
        img_idx = (image_cursors[sell_cat] + _seeded_rng(set_id, p["name"], "img_offset")
                   .randint(0, len(imgs) - 1)) % len(imgs)
        image_cursors[sell_cat] += 1
        image = imgs[img_idx]

        item_short_name = _shorten_caption(image["caption"], sell_cat)
        item_id = f"{set_id}_{p['name'].lower()}_{sell_cat}_01"

        sell_item = {
            "item_id":      item_id,
            "name":         item_short_name,
            "category":     sell_cat,
            "floor_price":  _pick_value(rng, sell_cat, "seller"),
            "image_path":   image["relative_path"],
        }

        # Wants: pick 2 categories that someone else in the set is selling
        # (so a deal is feasible). Exclude own sell-category.
        eligible = [c for c in present_cats if c != sell_cat]
        wants = rng.sample(eligible, k=min(2, len(eligible)))
        items_to_buy = []
        for j, w in enumerate(wants):
            want_id = f"{set_id}_{p['name'].lower()}_want_{w}"
            items_to_buy.append({
                "want_id":         want_id,
                "description":     f"Looking for {w}",
                "want_category":   w,
                "ceiling_price":   _pick_value(rng, w, "buyer"),
            })

        phase3 = dict(p)  # preserve name, style, ratings, reviews
        phase3["items_to_sell"] = [sell_item]
        phase3["items_to_buy"] = items_to_buy
        out.append(phase3)

    return out


def validate_set(personas: list[dict]) -> list[str]:
    """Sanity-check the want-graph closure. Returns a list of warnings."""
    warnings: list[str] = []
    sell_cats = set()
    for p in personas:
        for it in p["items_to_sell"]:
            sell_cats.add(it["category"])

    for p in personas:
        wants = {w["want_category"] for w in p["items_to_buy"]}
        # Every want should match at least one other persona's sell-category
        for w in wants:
            sellers = [q["name"] for q in personas
                       if q["name"] != p["name"]
                       and any(it["category"] == w for it in q["items_to_sell"])]
            if not sellers:
                warnings.append(
                    f"  {p['name']}: wants '{w}' but no other persona in this set sells it"
                )
    return warnings


def main():
    if not MANIFEST.exists():
        raise SystemExit(f"Image manifest missing: {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text())
    images_by_cat = {k: v for k, v in manifest["categories"].items()}
    total_imgs = sum(len(v) for v in images_by_cat.values())
    print(f"Image pool: {total_imgs} images across {len(images_by_cat)} categories")
    for k, v in images_by_cat.items():
        print(f"  {k}: {len(v)}")
    print()

    DST.mkdir(parents=True, exist_ok=True)
    all_warnings = []
    for set_id in SETS:
        src_path = SRC / f"{set_id}.json"
        personas = json.loads(src_path.read_text())
        phase3 = assign_set(set_id, personas, images_by_cat)
        warnings = validate_set(phase3)
        all_warnings.extend((set_id, w) for w in warnings)
        out_path = DST / f"{set_id}.json"
        out_path.write_text(json.dumps(phase3, indent=2))
        print(f"  {set_id}: {len(phase3)} personas -> {out_path.name}")

    if all_warnings:
        print(f"\n⚠️  Want-graph warnings ({len(all_warnings)}):")
        for set_id, w in all_warnings:
            print(f"  [{set_id}] {w}")
    else:
        print("\n✓ All want-graphs closed — every persona has tradeable counterparties.")


if __name__ == "__main__":
    main()
