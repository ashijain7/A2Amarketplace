#!/usr/bin/env python3
"""Relabel the config-ID badges baked into the transcript-panel figures.

The panels were rendered with the old dispatch IDs (C4/C6/C7/C8/C9/C10). The
camera-ready renumbers configurations sequentially C1-C7 (issue A10), so the
badges must follow. Nothing else in the images is touched: each badge is redrawn
in place with the same geometry, fill and type treatment.

  fig2_crossvendor : C4 -> C2, C6 -> C3
  fig3_withinfamily: C7 -> C4, C8 -> C5
  fig4_mirrored    : C9 -> C6, C10 -> C7   (C10's chip is wider; it is redrawn at
                                            the standard two-character width)

Usage: relabel_transcript_badges.py [--preview] [--apply]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "A2A_COLM_2026"

BADGE_FILL = (47, 111, 222)      # sampled from the originals
PAGE_BG = (255, 255, 255)
W, H, RADIUS = 67, 37, 12        # standard two-character chip
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf",
]

# file -> [(x, y, old_label, new_label), ...]  (x, y = top-left of the chip)
BADGES = {
    "fig2_crossvendor.png": [(60, 199, "C4", "C2"), (60, 2155, "C6", "C3")],
    "fig3_withinfamily.png": [(60, 199, "C7", "C4"), (60, 2086, "C8", "C5")],
    "fig4_mirrored.png": [(60, 199, "C9", "C6"), (60, 2264, "C10", "C7")],
}


def load_font():
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    import matplotlib
    return str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans-Bold.ttf")


# Measured from the untouched originals: the white glyphs occupy 30x18 px inside
# the 67x37 chip (45% of its width, 49% of its height). DejaVu Sans Bold at 24 px
# reproduces that cap height exactly; matching the height is what makes the patch
# invisible at print size.
FONT_SIZE = 24


def fit_font(path, text, box_w, box_h):
    f = ImageFont.truetype(path, FONT_SIZE)
    l, t, r, b = f.getbbox(text)
    return (f, r - l, b - t, l, t)


def redraw(img: Image.Image, x, y, old, new, font_path):
    d = ImageDraw.Draw(img)
    # Erase past the OLD chip's full width — the three-character "C10" chip is
    # 80 px wide, so a 67 px erase left a blue sliver behind. The model name that
    # follows starts at ~x+94, so clearing to x+88 is safe.
    d.rectangle([x - 3, y - 3, x + 88, y + H + 3], fill=PAGE_BG)
    d.rounded_rectangle([x, y, x + W - 1, y + H - 1], radius=RADIUS, fill=BADGE_FILL)
    font, tw, th, lx, ty = fit_font(font_path, new, W, H)
    d.text((x + (W - tw) / 2 - lx, y + (H - th) / 2 - ty), new,
           font=font, fill=PAGE_BG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="write a before/after sheet only")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    font_path = load_font()
    print(f"font: {font_path}")

    strips = []
    for name, badges in BADGES.items():
        src = FIGDIR / name
        img = Image.open(src).convert("RGB")
        for x, y, old, new in badges:
            before = img.crop((x - 6, y - 6, x + 100, y + H + 6)).resize((424, 196), Image.NEAREST)
            redraw(img, x, y, old, new, font_path)
            after = img.crop((x - 6, y - 6, x + 100, y + H + 6)).resize((424, 196), Image.NEAREST)
            sheet = Image.new("RGB", (880, 196), PAGE_BG)
            sheet.paste(before, (0, 0)); sheet.paste(after, (448, 0))
            strips.append((f"{name}  {old} -> {new}", sheet))
            print(f"  {name}: {old} -> {new}")
        if args.apply:
            bak = src.with_suffix(".png.bak")
            if not bak.exists():
                Image.open(src).save(bak)
            img.save(src)
    if strips:
        total = Image.new("RGB", (880, 196 * len(strips)), PAGE_BG)
        for i, (_, s) in enumerate(strips):
            total.paste(s, (0, i * 196))
        out = Path("/tmp/claude-1000/-home-azureuser-A2A-RL/bcc987e4-2cc0-482d-8927-b6444f25559e"
                   "/scratchpad/badge_before_after.png")
        total.save(out)
        print(f"preview (left=before, right=after): {out}")
    print("APPLIED" if args.apply else "preview only — rerun with --apply")


if __name__ == "__main__":
    main()
