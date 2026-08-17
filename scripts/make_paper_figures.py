#!/usr/bin/env python3
"""Regenerate the paper's aggregate result figures from the rescored data.

Design rules applied (reviewer issues C3/C4 + accessibility):
  * NO embedded chart titles — the caption in the LaTeX carries the title, so the
    figure never duplicates it in a different font/register (issue C4).
  * Value axes start at ZERO — no truncated baselines exaggerating differences
    (issue C3: the old settlement chart started at 0.75).
  * One hue for a single series; two validated categorical hues + a legend for
    grouped charts. No red/green encoding (colour-vision safety); every series is
    also direct-labelled, so identity is never colour-alone.
  * Recessive grid/axes, consistent type sizes, generous label room.
  * N/A is drawn as an explicit gap with an "n/a" tick, never as zero.

Usage: make_paper_figures.py [--outdir A2A_COLM_2026]
"""
import argparse
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper_runs"

# validated categorical slots (light surface) — see dataviz references/palette.md
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d8d7d2"

CONFIGS = [
    ("C1", "C1_sonnet_vs_sonnet", "Sonnet 4.5\nvs Sonnet 4.5"),
    ("C2", "C2_sonnet_vs_gemini", "Sonnet 4.5\nvs Gemini 3.1 Pro"),
    ("C3", "C3_opus_vs_gemini", "Opus 4.7\nvs Gemini 3.1 Pro"),
    ("C4", "C4_gemini_vs_gpt55", "Gemini 3.1 Pro\nvs GPT-5.5"),
    ("C5", "C5_gemini35_vs_gpt55", "Gemini 3.5 Flash\nvs GPT-5.5"),
    ("C6", "C6_opus48_vs_gpt55", "Opus 4.8\nvs GPT-5.5"),
    ("C7", "C7_gpt55_vs_opus48", "GPT-5.5\nvs Opus 4.8"),
]
STAGES = [("I", "phase1"), ("II", "phase2"), ("III", "phase4"), ("IV", "phase3")]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.titlesize": 9,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.facecolor": "white", "savefig.facecolor": "white",
})


def runs(cdir, phase):
    return [json.loads((sd / "rubric_scores.json").read_text())
            for sd in sorted((PAPER / cdir / phase).glob("set_*"))]


def dim_mean(rows, key):
    vals = [(r.get(key) or {}).get("combined") if isinstance(r.get(key), dict) else None
            for r in rows]
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def sub_mean(rows, rubric, field):
    vals = []
    for r in rows:
        b = r.get(rubric)
        if isinstance(b, dict) and b.get(field) is not None:
            vals.append(b[field])
    return statistics.mean(vals) if vals else None


def reward_mean(cdir, phase):
    return statistics.mean(r["final_reward"] for r in runs(cdir, phase))


def strip(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)


# ---------------------------------------------------------------- figure B
def fig_trajectory(out):
    fig, axes = plt.subplots(2, 4, figsize=(11, 4.6), sharey=True)
    for ax, (cid, cdir, label) in zip(axes.flat, CONFIGS):
        ys = [reward_mean(cdir, ph) for _, ph in STAGES]
        ax.plot(range(4), ys, color=BLUE, lw=2, marker="o", ms=6,
                mfc=BLUE, mec="white", mew=1.2, zorder=3)
        for i, y in enumerate(ys):                       # direct labels, not a legend
            ax.annotate(f"{y:.2f}", (i, y), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=7.5, color=MUTED)
        ax.set_title(f"{cid} · {label}", fontsize=8.5, color=INK, linespacing=1.3)
        ax.set_xticks(range(4), [s for s, _ in STAGES])
        ax.set_xlim(-0.45, 3.45)      # keeps the first/last value labels off the frame
        ax.set_ylim(0, 0.78)
        ax.grid(axis="x", visible=False)
        strip(ax)
    axes.flat[-1].set_visible(False)
    for ax in (axes[0][0], axes[1][0]):
        ax.set_ylabel("final score", color=INK)
    fig.supxlabel("stage", fontsize=9, color=INK, y=0.02)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "draft_B_smallmultiples.png", dpi=200)
    plt.close(fig)
    print("  draft_B_smallmultiples.png   (y-axis from 0; no embedded title)")


# ---------------------------------------------------------------- figure H
def fig_settlement(out):
    data = sorted(((cid, dim_mean(runs(cdir, "phase4"), "transactional_integrity"), lab)
                   for cid, cdir, lab in CONFIGS), key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ys = range(len(data))
    ax.barh(list(ys), [d[1] for d in data], color=BLUE, height=0.62, zorder=3)
    ax.set_yticks(list(ys), [f"{d[0]} · {d[2].replace(chr(10), ' ')}" for d in data], fontsize=8)
    for y, d in zip(ys, data):
        ax.annotate(f"{d[1]:.2f}", (d[1], y), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    ax.set_xlim(0, 1.0)                                   # issue C3: baseline at zero
    ax.set_xlabel("transactional-integrity score", color=INK)
    ax.grid(axis="y", visible=False)
    strip(ax)
    fig.tight_layout()
    fig.savefig(out / "draft_H_settlement_safety.png", dpi=200)
    plt.close(fig)
    print("  draft_H_settlement_safety.png  (baseline now 0, single hue, C3 fixed)")


def _grouped(out, name, series, ylabel, ymax, note):
    """Two-series grouped bars with direct labels and an n/a marker."""
    fig, ax = plt.subplots(figsize=(8.4, 3.5))
    xs = range(len(CONFIGS))
    w = 0.38
    for k, (slabel, vals, color) in enumerate(series):
        off = (k - 0.5) * w
        for x, v in zip(xs, vals):
            if v is None:
                ax.annotate("n/a", (x + off, 0), xytext=(0, 4), textcoords="offset points",
                            ha="center", fontsize=7.5, color=MUTED, style="italic")
                continue
            ax.bar(x + off, v, width=w * 0.92, color=color, zorder=3,
                   label=slabel if x == 0 else None)
            ax.annotate(f"{v:.2f}" if ymax <= 1 else f"{v:.0f}", (x + off, v),
                        xytext=(0, 3), textcoords="offset points", ha="center",
                        fontsize=7.5, color=MUTED)
    ax.set_xticks(list(xs), [f"{c[0]}\n{c[2]}" for c in CONFIGS], fontsize=7.5,
                  linespacing=1.25)
    ax.set_ylim(0, ymax)
    ax.set_ylabel(ylabel, color=INK)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    strip(ax)
    fig.tight_layout()
    fig.savefig(out / name, dpi=200)
    plt.close(fig)
    print(f"  {name}  {note}")


def fig_review_util(out):
    s2 = [dim_mean(runs(c[1], "phase2"), "review_utilization") for c in CONFIGS]
    s4 = [dim_mean(runs(c[1], "phase3"), "review_utilization") for c in CONFIGS]
    _grouped(out, "draft_I_review_util.png",
             [("Stage II (reviews)", s2, BLUE), ("Stage IV (SwapShop)", s4, ORANGE)],
             "review-utilization score", 1.0, "(rescored: zero-offer runs no longer credited)")


def fig_value(out):
    s1 = [sub_mean(runs(c[1], "phase1"), "capability_asymmetry", "focal_value_extracted")
          for c in CONFIGS]
    s2 = [sub_mean(runs(c[1], "phase2"), "capability_asymmetry", "focal_value_extracted")
          for c in CONFIGS]
    _grouped(out, "draft_J_value_captured.png",
             [("Stage I (trading)", s1, BLUE), ("Stage II (reviews)", s2, ORANGE)],
             "surplus margin captured (\\$)", 32, "(reported diagnostic, not scored)")


# ---------------------------------------------------------------- figure K
def fig_closure_vs_dsr(out):
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    pts = []
    for cid, cdir, lab in CONFIGS:
        rows = runs(cdir, "phase1")
        pts.append((cid, sub_mean(rows, "deal_outcomes", "closure_rate"),
                    sub_mean(rows, "deal_outcomes", "dual_surplus_rate")))
    ax.scatter([p[1] for p in pts], [p[2] for p in pts], s=70, color=BLUE,
               edgecolor="white", linewidth=1.2, zorder=3)
    # Merge labels for coincident points: C2 and C6 land on exactly the same
    # (closure, dual-surplus) coordinates, so separate labels would overprint.
    groups: dict = {}
    for cid, x, y in pts:
        groups.setdefault((round(x, 3), round(y, 3)), []).append(cid)
    for (x, y), cids in groups.items():
        dx, dy = (-10, 8) if x > 0.8 else (8, 6)
        ha = "right" if x > 0.8 else "left"
        ax.annotate("\u00b7".join(cids), (x, y), xytext=(dx, dy),
                    textcoords="offset points", fontsize=8.5, color=INK, ha=ha)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("closure rate", color=INK)
    ax.set_ylabel("dual-surplus rate", color=INK)
    strip(ax)
    fig.tight_layout()
    fig.savefig(out / "draft_K_closure_vs_dsr.png", dpi=200)
    plt.close(fig)
    print("  draft_K_closure_vs_dsr.png   (both axes 0-1; labels offset from frame)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(ROOT / "A2A_COLM_2026"))
    args = ap.parse_args()
    out = Path(args.outdir)
    print(f"writing figures to {out}")
    fig_trajectory(out)
    fig_settlement(out)
    fig_review_util(out)
    fig_value(out)
    fig_closure_vs_dsr(out)


if __name__ == "__main__":
    main()
