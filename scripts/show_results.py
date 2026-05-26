#!/usr/bin/env python3
"""
Pretty-print rubric scores from a rollouts JSONL file.

Usage:
  python scripts/show_results.py [path/to/rollouts.jsonl]

Defaults to results/phase_1/validate_rollouts.jsonl when no path is given.
"""

import json
import sys
from pathlib import Path


def _get_combined(rubric_dict, key):
    """Pull the combined score for a rubric, handling both dict-and-flat formats."""
    v = rubric_dict.get(key)
    if isinstance(v, dict):
        return v.get("combined")
    return v


def _fmt(x):
    if x is None:
        return "N/A"
    if isinstance(x, (int, float)):
        return f"{x:.3f}"
    return str(x)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "results/phase_1/validate_rollouts.jsonl"
    p = Path(path)
    if not p.exists():
        print(f"ERROR: {p} not found")
        sys.exit(1)

    rows = [json.loads(line) for line in p.open()]
    if not rows:
        print(f"ERROR: {p} is empty")
        sys.exit(1)

    rows.sort(key=lambda r: r.get("id", 0))

    print(f"\n{'=' * 70}")
    print(f"Rubric scores from: {p}")
    print(f"Rollouts: {len(rows)}")
    print(f"{'=' * 70}\n")

    for r in rows:
        md = r.get("metadata", {})
        outputs = r.get("response", {}).get("output", [])
        n_calls = sum(1 for m in outputs if m.get("type") == "function_call")
        rs = r.get("rubric_scores", {})

        print(f"Task {r.get('id')}: {md.get('task_id', '?')}")
        print(f"  focal={md.get('focal_persona', '?')}  config={md.get('config_name', '?')}  seed={md.get('seed', '?')}")
        print(f"  reward:               {_fmt(r.get('reward'))}")
        print(f"  tool_calls:           {n_calls}  ({len(outputs)} total messages)")
        print(f"  deal_outcomes:        {_fmt(_get_combined(rs, 'deal_outcomes'))}")

        # Show deal sub-components if available
        do = rs.get("deal_outcomes")
        if isinstance(do, dict):
            print(f"    closure_rate:       {_fmt(do.get('closure_rate'))}  ({do.get('deals_closed','?')}/{do.get('targets_total','?')} targets closed)")
            achievable = do.get("achievable_targets")
            ncr = do.get("normalized_closure_rate")
            if achievable is not None:
                print(f"    achievable_targets: {achievable} of {do.get('targets_total','?')}")
                print(f"    normalized_closure: {_fmt(ncr)}  (closed / achievable — skill-isolated)")
            print(f"    pareto_efficiency:  {_fmt(do.get('pareto_efficiency'))}")
            print(f"    seller_profit:      {_fmt(do.get('seller_profit'))}")
            print(f"    buyer_surplus:      {_fmt(do.get('buyer_surplus'))}")

        print(f"  capability_asymmetry: {_fmt(_get_combined(rs, 'capability_asymmetry'))}")
        print(f"  negotiation_quality:  {_fmt(_get_combined(rs, 'negotiation_quality'))}")
        print(f"  privacy:              {_fmt(_get_combined(rs, 'privacy'))}")

        # Phase 2: review_utilization. Hidden in phase 1 (None or absent).
        rev = rs.get("review_utilization")
        if isinstance(rev, dict):
            print(f"  review_utilization:   {_fmt(rev.get('combined'))}")
            print(f"    lookups_made:       {rev.get('lookups_made')}  (lookup_rate={_fmt(rev.get('lookup_rate'))})")
            print(f"    pre_offer_ratio:    {_fmt(rev.get('pre_offer_ratio'))}  (of focal offers preceded by a lookup)")
            print(f"    high_rating_pref:   {_fmt(rev.get('high_rating_preference'))}  (offers sent to >=4.0★)")

        # Phase 3: swap_quality. Hidden in phase 1/2 (None or absent).
        sq = rs.get("swap_quality")
        if isinstance(sq, dict):
            print(f"  swap_quality:         {_fmt(sq.get('combined'))}")
            print(f"    swaps_closed:       {sq.get('swaps_closed')}  (focal-involved swaps)")
            print(f"    mutual_win_rate:    {_fmt(sq.get('mutual_win_rate'))}  (both sides got + surplus)")
            print(f"    focal_surplus_mean: {_fmt(sq.get('focal_surplus_mean'))}  ($ value over what given up)")
        print()


if __name__ == "__main__":
    main()
