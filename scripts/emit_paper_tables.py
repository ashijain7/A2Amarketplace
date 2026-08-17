#!/usr/bin/env python3
"""Emit the paper's LaTeX table rows from the rescored run data (cr-2026-08).

Single source of truth for every number printed in the camera-ready tables, so
the paper cannot drift from results/paper_runs/ again.

Emits:
  tab:marketdeal  — Stages I-III dimension scores + Mean/Med (main paper)
  tab:swapshop    — Stage IV dimension scores + Mean/Med (main paper)
  tab:app-*       — appendix sub-metric blocks, incl. the NEW Stage III
                    marketplace block required by A11-2
  tab:weights     — the per-stage weight appendix required by A3

Usage: emit_paper_tables.py [--out FILE]
"""
import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper_runs"

# paper order = Table 1 order; label is what prints in the leftmost column
CONFIGS = [
    ("C1", "C1_sonnet_vs_sonnet", "Sonnet 4.5 (vs Sonnet 4.5)", "Symmetric self-play"),
    ("C2", "C2_sonnet_vs_gemini", "Sonnet 4.5 (vs Gemini 3.1 Pro Preview)", "Cross-vendor pairing"),
    ("C3", "C3_opus_vs_gemini", "Opus 4.7 (vs Gemini 3.1 Pro Preview)", None),
    ("C4", "C4_gemini_vs_gpt55", "Gemini 3.1 Pro Preview (vs GPT-5.5)", "Within-family generation"),
    ("C5", "C5_gemini35_vs_gpt55", "Gemini 3.5 Flash (vs GPT-5.5)", None),
    ("C6", "C6_opus48_vs_gpt55", "Opus 4.8 (vs GPT-5.5)", "Mirrored pairing"),
    ("C7", "C7_gpt55_vs_opus48", "GPT-5.5 (vs Opus 4.8)", None),
]
STAGES = [("I", "phase1"), ("II", "phase2"), ("III", "phase4"), ("IV", "phase3")]
DIMS_BY_STAGE = {
    "I":   ["deal_outcomes", "capability_asymmetry", "negotiation_quality", "persona_privacy"],
    "II":  ["deal_outcomes", "capability_asymmetry", "review_utilization",
            "negotiation_quality", "persona_privacy"],
    "III": ["deal_outcomes", "capability_asymmetry", "review_utilization",
            "negotiation_quality", "persona_privacy", "transactional_integrity"],
    "IV":  ["swap_quality", "deal_outcomes", "capability_asymmetry",
            "review_utilization", "persona_privacy"],
}


def runs(cfg_dir: str, phase: str) -> list[dict]:
    return [json.loads((sd / "rubric_scores.json").read_text())
            for sd in sorted((PAPER / cfg_dir / phase).glob("set_*"))]


def comb(rs: dict, key: str):
    v = rs.get(key)
    return v.get("combined") if isinstance(v, dict) else None


def mean_of(rows: list[dict], key: str):
    vals = [comb(r, key) for r in rows]
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def sub(rows: list[dict], rubric: str, field: str):
    """Mean of a sub-metric over the runs where it is scored."""
    vals = []
    for r in rows:
        blob = r.get(rubric)
        if isinstance(blob, dict):
            v = blob.get(field)
            if v is not None:
                vals.append(v)
    return statistics.mean(vals) if vals else None


def f2(v, dash="---"):
    return dash if v is None else f"{v:.2f}"


def f3(v, dash="---"):
    return dash if v is None else f"{v:.3f}"


def f1(v, dash="---"):
    return dash if v is None else f"{v:.1f}"


def colourise(col_vals: list, cells: list[list[str]], idx: int, lower_better: bool = False):
    """Tint the unique best (green) and unique worst (orange) cell of one column,
    matching the paper's existing convention. A tie is left uncoloured — with six
    configs at 1.00 there is no single 'best' worth marking.

    Every cell of the column must be present: a column with any missing value is
    ranked over a subset of the rows, which puts the green badge on a cell that is
    not the column extreme. Callers screen for that; the assert keeps it honest.
    """
    nums = [(i, v) for i, v in enumerate(col_vals) if v is not None]
    if len(nums) < 2:
        return
    assert len(nums) == len(col_vals), "colourise() called on a partial column"
    best, worst = (min, max) if lower_better else (max, min)
    hi = best(v for _, v in nums)
    lo = worst(v for _, v in nums)
    if hi == lo:
        return
    if sum(1 for _, v in nums if v == hi) == 1:
        i = next(i for i, v in nums if v == hi)
        cells[i][idx] = "\\cellcolor{bestcell}" + cells[i][idx]
    if sum(1 for _, v in nums if v == lo) == 1:
        i = next(i for i, v in nums if v == lo)
        cells[i][idx] = "\\cellcolor{worstcell}" + cells[i][idx]


def n_scored(rows: list[dict], key: str) -> int:
    """How many runs the dimension was actually scored on (N/A rule, B9/A4)."""
    return sum(1 for r in rows if comb(r, key) is not None)


def emit_main_tables(out: list):
    out.append("% ==== Table 3 (tab:marketdeal): Stages I-III dimension scores ====")
    out.append("% cols: DO CA RU NQ PP TI  Mean Med  (RU absent in Stage I; TI Stage III only)")
    all_cells, all_raw, all_n = [], [], []
    for cid, cdir, label, group in CONFIGS:
        cells, raw, ns = [], [], []
        for st, ph in [("I", "phase1"), ("II", "phase2"), ("III", "phase4")]:
            rows = runs(cdir, ph)
            rewards = [r["final_reward"] for r in rows]
            for d in DIMS_BY_STAGE[st]:
                v = mean_of(rows, d)
                cells.append(f2(v)); raw.append(v); ns.append(n_scored(rows, d))
            cells.append(f2(statistics.mean(rewards))); raw.append(None); ns.append(None)
            cells.append(f2(statistics.median(rewards))); raw.append(None); ns.append(None)
        all_cells.append(cells); all_raw.append(raw); all_n.append(ns)
    # Mean/Med are never shaded. Neither is a dimension whose configs rest on
    # different numbers of runs — CA is not scored in a run that closed no deal,
    # so those cells are not comparable across rows (same rule as Table 4).
    for idx in range(len(all_raw[0])):
        col = [r[idx] for r in all_raw]
        if any(v is None for v in col) or len({r[idx] for r in all_n}) > 1:
            continue
        colourise(col, all_cells, idx)
    for (cid, cdir, label, group), cells in zip(CONFIGS, all_cells):
        if group:
            out.append(f"\\textit{{{group}}} \\\\")
        out.append(f"{label} & " + " & ".join(cells) + " \\\\")
    out.append("")

    out.append("% ==== Table 4 (tab:swapshop): Stage IV dimension scores ====")
    out.append("% cols: SQ DO CA RU PP  Mean Med")
    out.append("% SQ/CA print as 'score~(n)' when scored on fewer than 5 runs — a run with")
    out.append("% no swaps (no deals) is N/A, not 0; the count keeps that visible. Caption")
    out.append("% must say: SQ measures the quality of swaps that happened; whether the agent")
    out.append("% traded at all is carried by closure rate inside DO.")
    all_cells, all_raw = [], []
    for cid, cdir, label, group in CONFIGS:
        rows = runs(cdir, "phase3")
        rewards = [r["final_reward"] for r in rows]
        cells, raw = [], []
        for d in DIMS_BY_STAGE["IV"]:
            # SQ and CA are N/A for runs with no swaps/deals. The per-run counts are
            # not printed; the caption carries the scope instead, and a dash marks a
            # configuration that closed no swap at all.
            v = f2(mean_of(rows, d))
            raw.append(mean_of(rows, d))
            cells.append(v)
        cells += [f2(statistics.mean(rewards)), f2(statistics.median(rewards))]
        raw += [None, None]
        all_cells.append(cells); all_raw.append(raw)
    # Do NOT colour SQ or CA here: in Stage IV they are scored on different numbers
    # of runs per config (see the ~(n) annotations), so a "best" badge would invite
    # exactly the misreading the counts exist to prevent — 1.00 from two swaps is
    # not a better barter record than 0.60 from five.
    UNCOMPARABLE = {DIMS_BY_STAGE["IV"].index("swap_quality"),
                    DIMS_BY_STAGE["IV"].index("capability_asymmetry")}
    for idx in range(len(all_raw[0])):
        if idx not in UNCOMPARABLE:
            colourise([r[idx] for r in all_raw], all_cells, idx)
    for (cid, cdir, label, group), cells in zip(CONFIGS, all_cells):
        if group:
            out.append(f"\\textit{{{group}}} \\\\")
        out.append(f"{label} & " + " & ".join(cells) + " \\\\")
    out.append("")


APP_BLOCKS = {
    "I": [("CR", "deal_outcomes", "closure_rate", f2), ("DSR", "deal_outcomes", "dual_surplus_rate", f2),
          ("SP", "deal_outcomes", "seller_profit", f2), ("BS", "deal_outcomes", "buyer_surplus", f2),
          ("RTC", "deal_outcomes", "rounds_to_close", f1),
          ("nCR", "deal_outcomes", "normalized_closure_rate", f2),
          ("DO", "deal_outcomes", "combined", f2),
          ("Par", "capability_asymmetry", "parity", f2),
          ("SR", "capability_asymmetry", "self_rating", f1),
          ("OR", "capability_asymmetry", "observer_rating", f1),
          ("PF", "capability_asymmetry", "perceived_fairness", f1),
          ("$\\Delta$", "capability_asymmetry", "self_observer_delta", f1),
          ("SM", "capability_asymmetry", "focal_value_extracted", f1),
          ("CA", "capability_asymmetry", "combined", f2),
          ("An", "negotiation_quality", "anchoring", f2),
          ("Sm", "negotiation_quality", "smoothness", f2),
          ("DH", "negotiation_quality", "deadlock_handling", f2),
          ("NQ", "negotiation_quality", "combined", f2),
          ("PLR", "persona_privacy", "pii_leakage_rate", f2),
          ("BndS", "persona_privacy", "boundary_score", f2),
          ("PP", "persona_privacy", "combined", f2)],
}
APP_BLOCKS["II"] = APP_BLOCKS["I"][:14] + [
    ("LM", "review_utilization", "lookups_made", f1),
    ("LR", "review_utilization", "lookup_rate", f2),
    ("POR", "review_utilization", "pre_offer_ratio", f2),
    ("HRP", "review_utilization", "high_rating_preference", f2),
    ("RU", "review_utilization", "combined", f2)] + APP_BLOCKS["I"][14:]
# A11-2: the previously-missing Stage III marketplace sub-metrics
APP_BLOCKS["III-market"] = APP_BLOCKS["II"]
APP_BLOCKS["III-settle"] = [
    ("CrP", "transactional_integrity", "credential_privacy", f2),
    ("ScR", "transactional_integrity", "security", f2),
    ("StC", "transactional_integrity", "correctness", f2),
    ("Acc", "transactional_integrity", "integrity", f2),
    ("Vrf", "transactional_integrity", "verification", f2),
    ("SMC", "transactional_integrity", "method", f2),
    ("TI", "transactional_integrity", "combined", f2)]
APP_BLOCKS["IV"] = [
    ("SwC", "swap_quality", "swaps_closed", f1), ("MWR", "swap_quality", "mutual_win_rate", f2),
    ("FSM", "swap_quality", "focal_surplus_mean", f1), ("SQ", "swap_quality", "combined", f2),
    ("CR", "deal_outcomes", "closure_rate", f2), ("DO", "deal_outcomes", "combined", f2),
    ("Par", "capability_asymmetry", "parity", f2),
    ("PF", "capability_asymmetry", "perceived_fairness", f1),
    ("$\\Delta$", "capability_asymmetry", "self_observer_delta", f1),
    ("CA", "capability_asymmetry", "combined", f2),
    ("LM", "review_utilization", "lookups_made", f1),
    ("LR", "review_utilization", "lookup_rate", f2),
    ("POR", "review_utilization", "pre_offer_ratio", f2),
    ("HRP", "review_utilization", "high_rating_preference", f2),
    ("RU", "review_utilization", "combined", f2),
    ("PP", "persona_privacy", "combined", f2)]


def ti_value(rows, field):
    vals = []
    for r in rows:
        ti = r.get("transactional_integrity")
        if isinstance(ti, dict):
            v = (ti.get("areas") or {}).get(field) if field != "combined" else ti.get("combined")
            if v is not None:
                vals.append(v)
    return statistics.mean(vals) if vals else None


def emit_appendix(out: list):
    for stage, phase, title in [("I", "phase1", "Stage~I --- Basic Trading"),
                                ("II", "phase2", "Stage~II --- Review-Assisted"),
                                ("III-market", "phase4", "Stage~III --- marketplace sub-metrics (NEW, issue A11-2)"),
                                ("III-settle", "phase4", "Stage~III --- Payment \\& Settlement"),
                                ("IV", "phase3", "Stage~IV --- SwapShop")]:
        block = APP_BLOCKS[stage]
        out.append(f"% ==== Appendix block: {title} ====")
        out.append("% header: " + " & ".join(h for h, _, _, _ in block))
        # Columns whose cells average different numbers of runs cannot be ranked
        # against each other, so they are left unshaded (as in Table 4). This is a
        # decision about the whole COLUMN, not about individual cells: dropping only
        # the short-n cells from the ranking leaves the green badge on whichever
        # full-n cell happens to lead, which is not the column's best value.
        RUN_RESTRICTED = {"parity", "combined", "swaps_closed", "mutual_win_rate",
                          "focal_surplus_mean", "pre_offer_ratio", "high_rating_preference"}
        # Reported for context, not scored — the caption says ratings and counts are
        # left uncoloured, and a best/worst badge on them asserts a direction the
        # paper does not claim (a larger self-observer gap is not "better"; nor is a
        # larger surplus margin, which B1 demoted to a diagnostic).
        NEVER_SHADE = {"rounds_to_close", "normalized_closure_rate", "self_rating",
                       "observer_rating", "perceived_fairness", "self_observer_delta",
                       "focal_value_extracted", "lookups_made"}
        LOWER_BETTER = {"pii_leakage_rate"}
        all_cells, all_raw = [], []
        for cid, cdir, label, group in CONFIGS:
            rows = runs(cdir, phase)
            cells, raw = [], []
            for _, rubric, field, fmt in block:
                v = (ti_value(rows, field) if rubric == "transactional_integrity"
                     else sub(rows, rubric, field))
                cells.append(fmt(v))
                n_all = len(rows)
                n_have = sum(1 for r in rows
                             if isinstance(r.get(rubric), dict)
                             and (r[rubric].get(field) is not None
                                  or (rubric == "transactional_integrity"
                                      and (r[rubric].get("areas") or {}).get(field) is not None)))
                raw.append(v if n_have == n_all else None)
            all_cells.append(cells); all_raw.append(raw)
        for idx, (_, _, field, _) in enumerate(block):
            col = [r[idx] for r in all_raw]
            if field in RUN_RESTRICTED or field in NEVER_SHADE or any(v is None for v in col):
                continue
            colourise(col, all_cells, idx, lower_better=field in LOWER_BETTER)
        for (cid, cdir, label, group), cells in zip(CONFIGS, all_cells):
            if group:
                out.append(f"\\textit{{{group}}} \\\\")
            out.append(f"{label} & " + " & ".join(cells) + " \\\\")
        out.append("")


def emit_weights(out: list):
    import sys
    sys.path.insert(0, str(ROOT))
    from resources_server import verifiers as V
    out.append("% ==== Weights appendix (issue A3) — read live from verifiers.py ====")
    names = [("Deal Outcomes", "deal_outcomes"), ("Capability Asymmetry", "capability_asymmetry"),
             ("Negotiation Quality", "negotiation_quality"), ("Review Utilization", "review_utilization"),
             ("Transactional Integrity", "transactional_integrity"), ("Swap Quality", "swap_quality")]
    tables = [("Stage~I", V.PHASE_1_WEIGHTS), ("Stage~II", V.PHASE_2_WEIGHTS),
              ("Stage~III", V.TRANSACTION_WEIGHTS), ("Stage~IV", V.PHASE_3_WEIGHTS)]
    out.append("Dimension & " + " & ".join(t for t, _ in tables) + " \\\\")
    # Printed weights are rescaled so each stage's column sums to one. The scoring
    # code keeps the raw values (whose comments record where they came from, e.g.
    # Stage III = Stage II x 0.70); compute_final_reward divides by the weight it
    # actually applied, so scaling a column changes no reward — verified reward-for-
    # reward over all 140 runs. Printing the raw values would show columns summing
    # to 0.825/0.85/0.895/0.75, the hole left when Persona Privacy was dropped (B7).
    for label, key in names:
        cells = [f"{w[key] / sum(w.values()):.3f}" if key in w else "---" for _, w in tables]
        out.append(f"{label} & " + " & ".join(cells) + " \\\\")
    # Persona Privacy has no row: it carries no weight in any stage (B7). The
    # table caption states that, so a row saying so here would only repeat it.
    out.append("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "A2A_COLM_2026" / "generated_tables.tex"))
    args = ap.parse_args()
    out: list[str] = ["% AUTO-GENERATED by scripts/emit_paper_tables.py — do not hand-edit.",
                      "% Source: results/paper_runs/*/phase*/set_*/rubric_scores.json (cr-2026-08)", ""]
    emit_main_tables(out)
    emit_appendix(out)
    emit_weights(out)
    Path(args.out).write_text("\n".join(out) + "\n")
    print(f"wrote {args.out} ({len(out)} lines)")


if __name__ == "__main__":
    main()
