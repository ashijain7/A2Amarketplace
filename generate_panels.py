#!/usr/bin/env python3
"""Generate three conversation panel images for the paper figure."""

from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = "Association_for_Computing_Machinery__ACM____SIG_Proceedings_Template"

# ── Colors ──────────────────────────────────────────────────────────────
C_PAGE     = (245, 246, 248)
C_CARD     = (255, 255, 255)
C_SHADOW   = (210, 214, 220)
C_DIVIDER  = (229, 231, 235)

C_BADGE_BG   = (232, 240, 254)
C_BADGE_TXT  = (37,  99,  235)
C_TITLE      = (17,  24,  39)
C_SUBTITLE   = (107, 114, 128)

C_FOCAL_DOT  = (59,  130, 246)
C_OPP_DOT    = (156, 163, 175)
C_AGENT_TXT  = (55,  65,  81)
C_TURN       = (156, 163, 175)

C_FOCAL_BG   = (239, 246, 255)
C_FOCAL_TXT  = (30,  64,  175)
C_OPP_BG     = (249, 250, 251)
C_OPP_BDR    = (209, 213, 219)
C_OPP_TXT    = (55,  65,  81)

C_CHIP_BG    = (254, 243, 199)
C_CHIP_TXT   = (120, 53,  15)
C_LOOK_BG    = (220, 252, 231)
C_LOOK_TXT   = (22,  101, 52)

C_DEAL_BG    = (220, 252, 231)
C_DEAL_TXT   = (21,  128, 61)

C_MET_BG     = (249, 250, 251)
C_MET_KEY    = (75,  85,  99)
C_MET_GREEN  = (5,   150, 105)
C_MET_RED    = (180, 60,  20)
C_MET_GRAY   = (107, 114, 128)

# ── Dimensions ──────────────────────────────────────────────────────────
SCALE        = 1            # layout scale (keep at 1 — upscale at export)
IMG_W        = 520
CARD_X       = 22
CARD_W       = IMG_W - CARD_X * 2

BUBBLE_MAX_W = 300
AV_SIZE      = 28

def load_font(size, bold=False):
    paths = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

def tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def th(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]

def wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if tw(draw, test, font) <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]

def rr(draw, xy, r, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill,
                            outline=outline, width=width)

def make_panel(data, output_path, fixed_img_h=None, extra_gap=0):
    # ── Pre-calculate height ─────────────────────────────────────────────
    # We'll draw to a tall canvas then crop.
    WORKING_H = 1200 * SCALE
    img  = Image.new("RGB", (IMG_W, WORKING_H), C_PAGE)
    draw = ImageDraw.Draw(img)

    # Fonts
    fB   = load_font(12)   # badge
    fT   = load_font(15)   # title
    fSub = load_font(11)   # subtitle
    fAg  = load_font(11)   # agent label
    fTrn = load_font(10)   # turn label
    fMsg = load_font(13)   # bubble text
    fChp = load_font(10)   # chip text
    fDl  = load_font(13)   # deal text
    fMk  = load_font(12)   # metrics key
    fMv  = load_font(12)   # metrics value

    x  = CARD_X + 20   # content left margin
    y  = CARD_X + 24   # start below card top

    s = SCALE
    # ── Badge ────────────────────────────────────────────────────────────
    bdg = data["badge"]
    bw  = tw(draw, bdg, fB) + 20*s
    rr(draw, [x, y, x + bw, y + 22*s], r=11*s, fill=C_BADGE_BG)
    draw.text((x + 10*s, y + 5*s), bdg, font=fB, fill=C_BADGE_TXT)
    y += 32*s

    # ── Title ────────────────────────────────────────────────────────────
    draw.text((x, y), data["title"], font=fT, fill=C_TITLE)
    y += 22*s

    # ── Subtitle ─────────────────────────────────────────────────────────
    draw.text((x, y), data["subtitle"], font=fSub, fill=C_SUBTITLE)
    y += 20*s

    # ── Divider ──────────────────────────────────────────────────────────
    y += 8*s
    draw.line([(CARD_X + 20*s, y), (CARD_X + CARD_W - 20*s, y)],
              fill=C_DIVIDER, width=s)
    y += 14*s

    # ── Agents row ───────────────────────────────────────────────────────
    draw.ellipse([x, y + 4*s, x + 10*s, y + 14*s], fill=C_FOCAL_DOT)
    fl = f"{data['focal_name']} ({data['focal_model']}, evaluated agent — {data['focal_role']})"
    draw.text((x + 15*s, y + s), fl, font=fAg, fill=C_AGENT_TXT)
    y += 20*s
    draw.ellipse([x, y + 4*s, x + 10*s, y + 14*s], outline=C_OPP_DOT, width=2*s)
    ol = f"{data['opp_name']} ({data['opp_model']}, opponent — {data['opp_role']})"
    draw.text((x + 15*s, y + s), ol, font=fAg, fill=C_AGENT_TXT)
    y += 28*s

    # ── Conversation ─────────────────────────────────────────────────────
    LINE_H = 17
    gap    = int(14 * SCALE + extra_gap)
    y     += int(extra_gap)

    for turn in data["turns"]:
        is_focal = turn["who"] == "focal"
        msg   = turn["msg"]
        chip  = turn.get("chip")
        ctype = turn.get("chip_type", "action")

        lines   = wrap(draw, msg, fMsg, BUBBLE_MAX_W - 20*s)
        bub_h   = len(lines) * LINE_H + 14*s + (22*s if chip else 0)
        av_init = data["focal_initial"] if is_focal else data["opp_initial"]

        if is_focal:
            ax = CARD_X + 20*s
            bx = ax + AV_SIZE + 8*s
            draw.ellipse([ax, y, ax + AV_SIZE, y + AV_SIZE], fill=C_FOCAL_DOT)
            draw.text((ax + AV_SIZE // 2 - 4*s, y + 7*s), av_init,
                      font=fChp, fill=(255, 255, 255))
            rr(draw, [bx, y, bx + BUBBLE_MAX_W, y + bub_h], r=10*s, fill=C_FOCAL_BG)
            ty = y + 8*s
            for ln in lines:
                draw.text((bx + 10*s, ty), ln, font=fMsg, fill=C_FOCAL_TXT)
                ty += LINE_H
            if chip:
                cf  = C_LOOK_BG if ctype == "lookup" else C_CHIP_BG
                ct  = C_LOOK_TXT if ctype == "lookup" else C_CHIP_TXT
                cw_ = tw(draw, chip, fChp) + 14*s
                rr(draw, [bx + 8*s, ty + 2*s, bx + 8*s + cw_, ty + 18*s], r=8*s, fill=cf)
                draw.text((bx + 15*s, ty + 4*s), chip, font=fChp, fill=ct)
        else:
            ax = CARD_X + CARD_W - 20*s - AV_SIZE
            bx = ax - 8*s - BUBBLE_MAX_W
            draw.ellipse([ax, y, ax + AV_SIZE, y + AV_SIZE], fill=C_OPP_DOT)
            draw.text((ax + AV_SIZE // 2 - 4*s, y + 7*s), av_init,
                      font=fChp, fill=(255, 255, 255))
            rr(draw, [bx, y, bx + BUBBLE_MAX_W, y + bub_h],
               r=10*s, fill=C_OPP_BG, outline=C_OPP_BDR, width=s)
            ty = y + 8*s
            for ln in lines:
                draw.text((bx + 10*s, ty), ln, font=fMsg, fill=C_OPP_TXT)
                ty += LINE_H
            if chip:
                cf  = C_LOOK_BG if ctype == "lookup" else C_CHIP_BG
                ct  = C_LOOK_TXT if ctype == "lookup" else C_CHIP_TXT
                cw_ = tw(draw, chip, fChp) + 14*s
                rr(draw, [bx + 8*s, ty + 2*s, bx + 8*s + cw_, ty + 18*s], r=8*s, fill=cf)
                draw.text((bx + 15*s, ty + 4*s), chip, font=fChp, fill=ct)

        y += bub_h + gap

    # ── Deal banner ──────────────────────────────────────────────────────
    y += int(6*s + extra_gap)
    rr(draw, [CARD_X + 20*s, y, CARD_X + CARD_W - 20*s, y + 38*s], r=8*s, fill=C_DEAL_BG)
    draw.ellipse([CARD_X + 30*s, y + 9*s, CARD_X + 50*s, y + 29*s], fill=C_DEAL_TXT)
    draw.text((CARD_X + 35*s, y + 12*s), "✓", font=fDl, fill=(255, 255, 255))
    draw.text((CARD_X + 58*s, y + 11*s), data["deal_text"], font=fDl, fill=C_DEAL_TXT)
    y += 50*s

    # ── Metrics ──────────────────────────────────────────────────────────
    met_top = y
    met_rows = data["metrics"]
    met_h    = len(met_rows) * 24*s + 20*s
    rr(draw, [CARD_X + 20*s, met_top, CARD_X + CARD_W - 20*s, met_top + met_h],
       r=8*s, fill=C_MET_BG)
    my = met_top + 12*s
    for key, val, col in met_rows:
        draw.text((CARD_X + 32*s, my), key, font=fMk, fill=C_MET_KEY)
        vc = {"green": C_MET_GREEN, "red": C_MET_RED, "gray": C_MET_GRAY}[col]
        vw = tw(draw, val, fMv)
        draw.text((CARD_X + CARD_W - 32*s - vw, my), val, font=fMv, fill=vc)
        my += 24*s
    y = met_top + met_h + 22*s

    # ── Draw card outline (crop canvas to content) ───────────────────────
    content_card_h = y - CARD_X + 4
    content_img_h  = content_card_h + CARD_X * 2

    # If a fixed height is requested, expand the card to fill it
    IMG_H  = fixed_img_h if fixed_img_h else content_img_h
    CARD_H = IMG_H - CARD_X * 2

    final = Image.new("RGB", (IMG_W, IMG_H), C_PAGE)
    fd    = ImageDraw.Draw(final)

    # shadow
    rr(fd, [CARD_X + 4, CARD_X + 4, CARD_X + CARD_W + 4, CARD_X + CARD_H + 4],
       r=16, fill=C_SHADOW)
    # card bg
    rr(fd, [CARD_X, CARD_X, CARD_X + CARD_W, CARD_X + CARD_H], r=16, fill=C_CARD)

    # Paste drawn content onto final card
    final.paste(img.crop((0, 0, IMG_W, content_img_h)), (0, 0))
    # Re-draw card outline on top (to clean up corners)
    rr(fd, [CARD_X, CARD_X, CARD_X + CARD_W, CARD_X + CARD_H],
       r=16, fill=None, outline=C_DIVIDER, width=1)

    if output_path:
        # Upscale 2× with LANCZOS for sharp print quality, same layout
        out_img = final.resize((IMG_W * 2, IMG_H * 2), Image.LANCZOS)
        out_img.save(output_path, "PNG", dpi=(300, 300))
        print(f"Saved {output_path}  ({IMG_W*2}x{IMG_H*2} @ 300 DPI)")
    return IMG_H


# ── Panel definitions ─────────────────────────────────────────────────────

PANELS = [
    {
        "badge":       "MarketDeal — Stage I",
        "title":       "Marcus sells a speaker · Sonnet vs Gemini",
        "subtitle":    "Buying and selling · no reviews tool · Config C4",
        "focal_name":  "Marcus", "focal_model": "Sonnet 4.5",
        "focal_role":  "selling", "focal_initial": "M",
        "opp_name":    "Isla",   "opp_model":   "Gemini 3.1 Pro",
        "opp_role":    "buying", "opp_initial":  "I",
        "turns": [
            {"who": "focal",
             "msg": "JBL Bluetooth speaker for sale - waterproof, red, excellent condition. Asking $45.",
             "chip": "post_listing"},
            {"who": "opponent",
             "msg": "Hi Marcus! That red JBL speaker sounds absolutely perfect! I’m on a tight budget — would you let it go for $25? I’d be so grateful!",
             "chip": "make_offer"},
            {"who": "focal",
             "msg": "Hi Isla, I appreciate your interest! $25 is too low for me. I can come down to $35, which is a fair price for this quality speaker.",
             "chip": "counter_offer"},
            {"who": "opponent",
             "msg": "Oh my gosh, you’ve got yourself a deal! $35 works perfectly for me. I can’t wait to use it!",
             "chip": "accept_offer"},
        ],
        "deal_text": "Deal closed. Marcus receives $35.",
        "metrics": [
            ("Surplus above floor",      "$7",                    "green"),
            ("Turns to close",           "18",                    "gray"),
            ("Why Gemini accepted fast", "Accepts first counter", "red"),
        ],
    },
    {
        "badge":       "MarketDeal — Stage II",
        "title":       "Omar checks rep · Gemini 3.5 Flash vs GPT-5.5",
        "subtitle":    "Buying and selling · reviews tool active · Config C8",
        "focal_name":  "Omar",  "focal_model": "Gemini 3.5 Flash",
        "focal_role":  "buying", "focal_initial": "O",
        "opp_name":    "Buck",  "opp_model":   "GPT-5.5",
        "opp_role":    "selling", "opp_initial":  "B",
        "turns": [
            {"who": "opponent",
             "msg": "Howdy folks, I’m listing a basic tool set — hammer, screwdrivers, and wrench — for $45. Solid little kit for household fixes.",
             "chip": "post_listing"},
            {"who": "focal",
             "msg": "Checking Buck’s seller reputation before making an offer.",
             "chip": "lookup_agent", "chip_type": "lookup"},
            {"who": "focal",
             "msg": "Hi Buck, I saw your tool set listing. My ceiling budget is $42. Would you accept $38 for it if everything is in good shape?",
             "chip": "make_offer"},
            {"who": "opponent",
             "msg": "Omar, I appreciate the $38 offer, but this tool set is worth a bit more. Meet me at $42 and you’ve got yourself a deal.",
             "chip": "counter_offer"},
            {"who": "focal",
             "msg": "Hi Buck! $42 sounds fair — that matches my ceiling and I could really use a solid household kit. I accept!",
             "chip": "accept_offer"},
        ],
        "deal_text": "Deal closed. Omar pays $42.",
        "metrics": [
            ("Buyer surplus",       "$0 (paid ceiling)",  "gray"),
            ("Lookup before offer", "Yes — 3.9★ checked", "green"),
            ("Tool engagement",     "Active",              "green"),
        ],
    },
    {
        "badge":       "SwapShop — Stage III",
        "title":       "Taj swaps a sweater · Sonnet vs Gemini",
        "subtitle":    "Pure barter · no prices · Config C4",
        "focal_name":  "Taj",   "focal_model": "Sonnet 4.5",
        "focal_role":  "swapping", "focal_initial": "T",
        "opp_name":    "Kade",  "opp_model":   "Gemini 3.1 Pro",
        "opp_role":    "swapping", "opp_initial":  "K",
        "turns": [
            {"who": "focal",
             "msg": "Hi everyone! Trading my White Sweater (outerwear). Looking for bottoms or dresses in good condition. Open to offers!",
             "chip": "post_listing"},
            {"who": "opponent",
             "msg": "Offering my Brown Floral Dress for your White Sweater.",
             "chip": "propose_swap"},
            {"who": "focal",
             "msg": "Perfect! I’d love to trade my White Sweater for your Brown Floral Dress. Deal!",
             "chip": "accept_swap"},
        ],
        "deal_text": "Swap closed. Taj receives Brown Floral Dress.",
        "metrics": [
            ("Mutual win",     "Yes — both got stated want", "green"),
            ("Turns to close", "5",                          "green"),
            ("Price axis",     "None — pure barter",         "gray"),
        ],
    },
]

stage_names = ["I", "II", "III"]

# Pass 1 — measure natural heights
heights = []
for panel in PANELS:
    h = make_panel(panel, output_path=None)
    heights.append(h)

uniform_h = max(heights)
print(f"Natural heights: {heights}  →  uniform height: {uniform_h}px")

# Pass 2 — regenerate with distributed extra gap (no blank space)
for i, (panel, nat_h) in enumerate(zip(PANELS, heights)):
    extra        = uniform_h - nat_h
    # gap positions: 1 before first bubble + N between bubbles + 1 before deal
    n_gap_slots  = len(panel["turns"]) + 2
    extra_gap    = extra / n_gap_slots
    out = os.path.join(OUT_DIR, f"panel_{i+1}_stage{stage_names[i]}.png")
    make_panel(panel, out, fixed_img_h=uniform_h, extra_gap=extra_gap)

print("\nAll 3 panels generated at uniform size.")

# ── Combine into one wide image ──────────────────────────────────────────
panels_imgs = [
    Image.open(os.path.join(OUT_DIR, f"panel_{i+1}_stage{stage_names[i]}.png"))
    for i in range(3)
]
gap_px   = 30 * 2   # panels are already 2× upscaled
total_w  = sum(p.width for p in panels_imgs) + gap_px * 2
total_h  = panels_imgs[0].height
combined = Image.new("RGB", (total_w, total_h), (235, 236, 238))
x_off = 0
for p in panels_imgs:
    combined.paste(p, (x_off, 0))
    x_off += p.width + gap_px

combined_path = os.path.join(OUT_DIR, "combined_stage_diagram.png")
combined.save(combined_path, "PNG", dpi=(300, 300))
print(f"Combined: {combined_path}  ({total_w}x{total_h} @ 300 DPI)")
