#!/usr/bin/env python3
"""Refresh the numeric cells of results/paper_runs/MASTER_RESULTS.md from the
rescored run files (camera-ready cr-2026-08).

Only table VALUES and a few row LABELS are touched; all prose is left alone
(the narrative is reviewed separately, since interpretations changed too).

Usage: refresh_master_results.py --dry-run | --apply
"""
import argparse
import json
import re
import shutil
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper_runs"
DOC = PAPER / "MASTER_RESULTS.md"

CONFIG_DIR = {
    "C1": "C1_sonnet_vs_sonnet", "C2": "C2_sonnet_vs_gemini", "C3": "C3_opus_vs_gemini",
    "C4": "C4_gemini_vs_gpt55", "C5": "C5_gemini35_vs_gpt55", "C6": "C6_opus48_vs_gpt55",
    "C7": "C7_gpt55_vs_opus48",
}
STAGE_PHASE = {"1": "phase1", "2": "phase2", "3": "phase4", "4": "phase3"}

# row label -> (rubric key, field). None rubric = top-level.
ROWS = {
    "reward": (None, "final_reward"),
    "closure_rate": ("deal_outcomes", "closure_rate"),
    "dual_surplus_rate": ("deal_outcomes", "dual_surplus_rate"),
    "seller_profit": ("deal_outcomes", "seller_profit"),
    "buyer_surplus": ("deal_outcomes", "buyer_surplus"),
    "rounds_to_close": ("deal_outcomes", "rounds_to_close"),
    "normalized_closure_rate": ("deal_outcomes", "normalized_closure_rate"),
    "self_rating": ("capability_asymmetry", "self_rating"),
    "observer_rating": ("capability_asymmetry", "observer_rating"),
    "perceived_fairness": ("capability_asymmetry", "perceived_fairness"),
    "self_observer_delta": ("capability_asymmetry", "self_observer_delta"),
    "focal_value_extracted": ("capability_asymmetry", "focal_value_extracted"),
    "parity": ("capability_asymmetry", "parity"),
    "anchoring": ("negotiation_quality", "anchoring"),
    "smoothness": ("negotiation_quality", "smoothness"),
    "deadlock_handling": ("negotiation_quality", "deadlock_handling"),
    "pii_leakage_rate": ("persona_privacy", "pii_leakage_rate"),
    "boundary_score": ("persona_privacy", "boundary_score"),
    "leaks_found": ("persona_privacy", "leaks_found"),
    "boundary_violations": ("persona_privacy", "boundary_violations"),
    "lookups_made": ("review_utilization", "lookups_made"),
    "lookup_rate": ("review_utilization", "lookup_rate"),
    "pre_offer_ratio": ("review_utilization", "pre_offer_ratio"),
    "high_rating_preference": ("review_utilization", "high_rating_preference"),
    "swaps_closed": ("swap_quality", "swaps_closed"),
    "mutual_win_rate": ("swap_quality", "mutual_win_rate"),
    "focal_surplus_mean": ("swap_quality", "focal_surplus_mean"),
}
# "### <heading>" -> rubric key owning that section's `combined` row
GROUP_RUBRIC = {
    "deal outcomes": "deal_outcomes",
    "capability asymmetry": "capability_asymmetry",
    "negotiation quality": "negotiation_quality",
    "privacy": "persona_privacy",
    "persona privacy": "persona_privacy",
    "review utilization": "review_utilization",
    "review utilisation": "review_utilization",
    "swap quality": "swap_quality",
    "transactional integrity": "transactional_integrity",
}
# TI area rows (values live under transactional_integrity.areas)
TI_AREAS = {"credential_privacy", "security", "correctness", "method", "integrity",
            "verification"}
RENAME_ROWS = {"pareto_efficiency": "dual_surplus_rate", "privacy": "credential_privacy"}


# Stage 4 (barter) tables label three slots with the SwapShop personas, while the
# run directories keep the money-stage names. Without this map the Stage-4 header
# row matches nothing and every Stage-4 table is silently skipped.
STAGE4_ALIAS = {"set_01": "Rosa", "set_03": "Zara", "set_04": "Buck"}


def load_runs(cfg: str, stage: str) -> dict:
    """persona name (as the doc labels it) -> rubric_scores dict."""
    out = {}
    for sd in sorted((PAPER / CONFIG_DIR[cfg] / STAGE_PHASE[stage]).glob("set_*")):
        rs = json.loads((sd / "rubric_scores.json").read_text())
        name = sd.name.split("_", 2)[2]
        out[name] = rs
        if stage == "4":
            alias = STAGE4_ALIAS.get("_".join(sd.name.split("_")[:2]))
            if alias:
                out[alias] = rs
    return out


def value_for(rs: dict, rubric, field):
    if rubric is None:
        return rs.get(field)
    blob = rs.get(rubric)
    if not isinstance(blob, dict):
        return None
    if rubric == "transactional_integrity" and field in TI_AREAS:
        return (blob.get("areas") or {}).get(field)
    return blob.get(field)


def fmt_like(old: str, val) -> str:
    """Format `val` with the same shape as the existing cell text (decimals,
    $ prefix, bold, trailing footnote markers, and the doc's own N/A style)."""
    old = old.strip()
    bold = old.startswith("**") and old.endswith("**")
    core = old.strip("*").strip()
    # a trailing footnote marker like 0.442* must survive the refresh
    note = ""
    if not bold and core.endswith("*"):
        note = "*"
        core = core[:-1].strip()
    if val is None:
        blank = core if core in ("N/A", "—", "-", "") else "N/A"
        return f"**{blank}**" if bold else blank + note
    if isinstance(val, str):
        return f"**{val}**" if bold else val
    # accept both ASCII '-' and the doc's Unicode minus '\u2212', and echo back
    # whichever the cell used, so "\u22129" stays "\u22129" and not "-9.00".
    uni_minus = core.startswith("\u2212")
    probe = core.replace("\u2212", "-")
    m = re.match(r"^-?\$?(\d+)(?:\.(\d+))?$", probe)
    decimals = len(m.group(2)) if (m and m.group(2)) else (0 if m else 2)
    dollar = probe.lstrip("-").startswith("$")
    s = f"{abs(val):.{decimals}f}"
    if dollar:
        s = "$" + s
    if val < 0:
        s = ("\u2212" if uni_minus else "-") + s
    return f"**{s}**" if bold else s + note


def refresh(text: str, report: list) -> str:
    lines = text.split("\n")
    cfg = stage = None
    personas: list[str] = []
    runs: dict = {}
    group = None
    out = []
    for ln in lines:
        h = re.match(r"^##\s+(C\d)\s+·\s+Stage\s+(\d)", ln)
        if h:
            cfg, stage = h.group(1), h.group(2)
            runs = load_runs(cfg, stage)
            personas, group = [], None
            out.append(ln)
            continue
        g = re.match(r"^###\s+(.+?)(?:\s+—|\s*$)", ln)
        if g:
            key = g.group(1).strip().lower().lstrip("0123456789. ")
            group = next((v for k, v in GROUP_RUBRIC.items() if k in key), None)
            out.append(ln)
            continue
        # table header row: | | Kai | Rex | ... | **Mean** |
        if runs and ln.startswith("|") and "Mean" in ln and "---" not in ln:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            cand = [c.strip("*").strip() for c in cells[1:-1]]
            if cand and all(c in runs for c in cand):
                personas = cand
            out.append(ln)
            continue
        # data row
        if runs and personas and ln.startswith("| `"):
            cells = [c for c in ln.strip().strip("|").split("|")]
            label_raw = cells[0].strip()
            m = re.match(r"^`([^`]+)`", label_raw)
            if not m:
                out.append(ln)
                continue
            label = m.group(1)
            new_label_raw = label_raw
            if label in RENAME_ROWS and (label != "privacy" or group == "transactional_integrity"):
                new_label = RENAME_ROWS[label]
                new_label_raw = label_raw.replace(f"`{label}`", f"`{new_label}`", 1)
                report.append(f"{cfg} S{stage}: row label {label} -> {new_label}")
                label = new_label
            if label == "combined" and group:
                rubric, field = group, "combined"
            elif label in ROWS:
                rubric, field = ROWS[label]
            elif label in TI_AREAS and group == "transactional_integrity":
                rubric, field = "transactional_integrity", label
            elif label == "deals_closed / targets":
                out.append(ln)
                continue
            else:
                out.append(ln)
                continue
            if len(cells) < len(personas) + 2:
                out.append(ln)
                continue
            vals, new_cells = [], []
            for i, p in enumerate(personas):
                v = value_for(runs[p], rubric, field)
                if v is not None:
                    vals.append(v)
                new_cells.append(" " + fmt_like(cells[i + 1], v) + " ")
            mean_cell = cells[len(personas) + 1]
            mean_val = statistics.mean(vals) if vals else None
            new_mean = " " + fmt_like(mean_cell, mean_val) + " "
            rebuilt = "|" + new_label_raw.join(["", ""]).join([]) if False else None
            new_line = "| " + new_label_raw + " |" + "|".join(new_cells) + "|" + new_mean + "|"
            if new_line != ln:
                report.append(f"{cfg} S{stage} {label}: {ln.strip()[:70]} -> {new_line.strip()[:70]}")
            out.append(new_line)
            # CA is now parity-based: surface the parity row right after the
            # dollar diagnostic it replaced in the formula.
            if label == "focal_value_extracted" and group == "capability_asymmetry":
                pv, pcells = [], []
                for p_ in personas:
                    v = value_for(runs[p_], "capability_asymmetry", "parity")
                    if v is not None:
                        pv.append(v)
                    pcells.append(" " + (f"{v:.2f}" if v is not None else "N/A") + " ")
                pmean = f"**{statistics.mean(pv):.2f}**" if pv else "**N/A**"
                prow = "| `parity` (0=one-sided, 1=even split) |" + "|".join(pcells) + "| " + pmean + " |"
                out.append(prow)
                report.append(f"{cfg} S{stage}: inserted parity row")
            continue
        out.append(ln)
    return "\n".join(out)


def refresh_cross_config(text: str, report: list) -> str:
    """The final 'Mean reward by config x stage' table (different shape: one row
    per config, four stage columns)."""
    means = {}
    for cfg, cdir in CONFIG_DIR.items():
        row = []
        for stage in ("1", "2", "3", "4"):
            rw = [json.loads((sd / "rubric_scores.json").read_text())["final_reward"]
                  for sd in sorted((PAPER / cdir / STAGE_PHASE[stage]).glob("set_*"))]
            row.append(statistics.mean(rw))
        means[cfg] = row
    out = []
    for ln in text.split("\n"):
        m = re.match(r"^\|\s*(C\d)\s*\|([^|]*)\|(.+)\|\s*$", ln)
        if m and m.group(1) in means and ln.count("|") == 7:
            cfg, focal = m.group(1), m.group(2)
            cells = [c for c in m.group(3).split("|")]
            new_cells = [" " + fmt_like(c, v) + " " for c, v in zip(cells, means[cfg])]
            new_ln = f"| {cfg} |{focal}|" + "|".join(new_cells) + "|"
            if new_ln != ln:
                report.append(f"cross-config {cfg}: {ln.strip()[:60]} -> {new_ln.strip()[:60]}")
            out.append(new_ln)
            continue
        out.append(ln)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    text = DOC.read_text()
    report: list[str] = []
    new = refresh(text, report)
    new = refresh_cross_config(new, report)
    print(f"rows changed: {len(report)}")
    for r in report[:40]:
        print("  ", r)
    if len(report) > 40:
        print(f"   ... and {len(report) - 40} more")
    if args.apply:
        bak = DOC.with_suffix(".md.bak")
        if not bak.exists():
            shutil.copy2(DOC, bak)
        DOC.write_text(new)
        print("applied")


if __name__ == "__main__":
    main()
