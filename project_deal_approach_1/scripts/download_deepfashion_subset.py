"""
Phase 3 Step 1 — Download a curated DeepFashion subset for the swap-shop.

Streams `lirus18/deepfashion_with_captions` from HuggingFace, classifies
each image by keyword-matching its caption, samples N images per category,
resizes to 512px on the long edge (JPEG quality 80), and writes them
under data/item_images/<category>/<id>.jpg.

Also writes data/item_images/manifest.json with id → {caption, category}
so the persona-generation script can map items to images deterministically.

The result is ~150 images, ~50–150 KB each, total ~20 MB on disk.
"""

import io
import json
import random
import re
from pathlib import Path

from datasets import load_dataset
from PIL import Image

DATASET = "lirus18/deepfashion_with_captions"
OUT_ROOT = Path(__file__).parent.parent / "data" / "item_images"
MAX_LONG_EDGE = 512
JPEG_QUALITY = 80
SAMPLE_SEED = 42
MAX_SCAN = 4000  # how many rows to scan from the stream before we stop

# Category buckets: (category_dir_name, list_of_caption_keywords)
CATEGORIES: list[tuple[str, list[str], int]] = [
    # (folder_name, keywords any-of, target image count)
    ("tops",      ["t-shirt", "tee shirt", "tee", "blouse", "shirt", "tank top", "top "], 30),
    ("bottoms",   ["jeans", "pants", "trousers", "shorts", "skirt"], 30),
    ("dresses",   ["dress", "gown", "jumpsuit"], 20),
    ("shoes",     ["shoes", "boots", "sneakers", "sandals", "heels", "loafers"], 25),
    ("outerwear", ["jacket", "coat", "blazer", "hoodie", "sweater", "cardigan"], 20),
    ("bags",      ["bag", "purse", "tote", "backpack", "handbag"], 25),
]
TARGET_TOTAL = sum(n for _, _, n in CATEGORIES)


def classify(caption: str) -> str | None:
    """Map a caption to one of our category folders. Returns None if no match.

    First-match wins — caption keywords are searched in CATEGORIES order, so
    earlier categories (tops) win over later ones (e.g., a caption like
    'shirt dress' goes to tops, not dresses)."""
    cap = caption.lower()
    for folder, keywords, _target in CATEGORIES:
        if any(kw in cap for kw in keywords):
            return folder
    return None


def slugify(caption: str, max_len: int = 40) -> str:
    """Make a short filename slug from a caption."""
    s = re.sub(r"[^a-z0-9]+", "_", caption.lower()).strip("_")
    return s[:max_len] or "item"


def resize_jpeg(img: Image.Image) -> bytes:
    """Resize to MAX_LONG_EDGE, return JPEG bytes."""
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_LONG_EDGE:
        scale = MAX_LONG_EDGE / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    targets = {folder: target for folder, _, target in CATEGORIES}
    saved: dict[str, list[dict]] = {f: [] for f in targets}
    seen_slugs: set[str] = set()

    print(f"Streaming {DATASET}...")
    print(f"Target: {TARGET_TOTAL} images across {len(CATEGORIES)} categories")
    print(f"Output root: {OUT_ROOT}")
    print()

    ds = load_dataset(DATASET, split="train", streaming=True)
    ds = ds.shuffle(seed=SAMPLE_SEED, buffer_size=1000)

    scanned = 0
    for ex in ds:
        scanned += 1
        if scanned > MAX_SCAN:
            print(f"Scanned {MAX_SCAN} rows; stopping early.")
            break
        if all(len(v) >= targets[k] for k, v in saved.items()):
            print(f"All targets met after scanning {scanned} rows.")
            break

        caption = ex.get("caption", "") or ""
        cat = classify(caption)
        if cat is None or len(saved[cat]) >= targets[cat]:
            continue

        slug = slugify(caption)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        img = ex.get("image")
        if img is None:
            continue
        try:
            jpeg_bytes = resize_jpeg(img)
        except Exception as e:
            print(f"  skip ({type(e).__name__}): {caption[:80]}")
            continue

        item_id = f"{cat}_{len(saved[cat])+1:03d}_{slug[:24]}"
        cat_dir = OUT_ROOT / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        out_path = cat_dir / f"{item_id}.jpg"
        out_path.write_bytes(jpeg_bytes)

        saved[cat].append({
            "item_id": item_id,
            "category": cat,
            "caption": caption,
            "relative_path": str(out_path.relative_to(OUT_ROOT.parent.parent)),
            "size_kb": round(len(jpeg_bytes) / 1024, 1),
        })

        if scanned % 200 == 0:
            counts = {k: len(v) for k, v in saved.items()}
            print(f"  scanned {scanned} — saved {sum(counts.values())} so far  {counts}")

    # Final summary
    print("\n=== summary ===")
    total = 0
    for k, items in saved.items():
        total += len(items)
        print(f"  {k:10s}  {len(items)}/{targets[k]}")
    print(f"  TOTAL     {total}/{TARGET_TOTAL}")

    # Manifest
    manifest = {
        "dataset": DATASET,
        "max_long_edge": MAX_LONG_EDGE,
        "jpeg_quality": JPEG_QUALITY,
        "sample_seed": SAMPLE_SEED,
        "categories": {k: v for k, v in saved.items()},
    }
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nWrote manifest -> {OUT_ROOT / 'manifest.json'}")
    print(f"Total bytes on disk: ~{sum(it['size_kb'] for items in saved.values() for it in items) / 1024:.1f} MB")


if __name__ == "__main__":
    main()
