"""
Truncate a rollouts.jsonl to the first N channel events per rollout, then
re-run the rubric verifiers on the truncated state.

This is the post-hoc equivalent of setting max_steps=N at runtime — used
to make pre-cap (C1 P1, C1 P2) and post-cap (C1 P3+) runs comparable.

Usage:
    python scripts/truncate_and_rescore.py \\
        --in  results/paper_runs/C1_sonnet_vs_sonnet/phase1/rollouts.jsonl \\
        --out results/paper_runs/C1_sonnet_vs_sonnet/phase1/rollouts_truncated.jsonl \\
        --max-events 100 \\
        --phase 1

What it does for each rollout:
  1. Truncates channel_events to the first `--max-events` entries (default 100).
  2. Drops deals whose `turn` field is beyond the truncation point.
  3. Rebuilds Channel + Ledger objects from the truncated lists.
  4. Calls verifiers.compute_*() to score the truncated state.
  5. Recomputes the weighted final_reward.
  6. Writes a new rollouts_truncated.jsonl with the new rubric_scores
     while preserving original rollout metadata.

The output file is the "comparable" dataset; the original rollouts.jsonl
is preserved untouched so the cap can be revised later if needed.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Make project importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from marketplace.channel import Channel, ChannelEvent
from marketplace.ledger import Ledger, Deal
from resources_server import verifiers


def _build_channel_from_events(events: list[dict]) -> Channel:
    """Construct an in-memory Channel from a list of event dicts (truncated)."""
    ch = Channel(path=Path("/tmp/_truncate_channel.jsonl"))  # disposable on-disk path
    ch.events = []
    for ev in events:
        ce = ChannelEvent(
            turn=ev.get("turn", 0),
            event_id=ev.get("event_id", ""),
            agent=ev.get("agent", ""),
            action=ev.get("action", "pass"),
            target=ev.get("target"),
            price=ev.get("price"),
            message=ev.get("message", ""),
            timestamp=ev.get("timestamp", ""),
            wants=ev.get("wants"),
            image_path=ev.get("image_path"),
            swap_item_id=ev.get("swap_item_id"),
        )
        ch.events.append(ce)
    return ch


def _build_ledger_from_deals(deals: list[dict], max_turn: int) -> Ledger:
    """Construct an in-memory Ledger from a list of deal dicts, keeping only
    deals whose `turn` is within the truncation window."""
    lg = Ledger(path=Path("/tmp/_truncate_deals.json"))
    lg.deals = []
    lg.sold_item_ids = set()
    lg.fulfilled_want_ids = set()
    for d in deals:
        turn = d.get("turn", 0)
        if turn > max_turn:
            continue
        # Reconstruct a Deal — fields differ slightly by phase, so be permissive.
        deal = Deal(
            deal_id=d.get("deal_id", f"deal_t{turn}"),
            seller=d.get("seller", ""),
            buyer=d.get("buyer", ""),
            item_id=d.get("item_id", ""),
            item_name=d.get("item_name", d.get("item_id", "")),
            price=d.get("price", 0.0),
            seller_floor=d.get("seller_floor", 0.0),
            buyer_ceiling=d.get("buyer_ceiling", 0.0),
            turn=turn,
        )
        # Phase 3 swap-deal optional fields
        for opt in ("deal_type", "item_b_id", "item_b_name", "item_b_floor",
                    "item_a_ceiling"):
            if opt in d:
                setattr(deal, opt, d[opt])
        lg.deals.append(deal)
        if deal.item_id:
            lg.sold_item_ids.add(deal.item_id)
        # We don't have want_id mappings here — approximate via post-deal want
        # fulfillment by item match. This may slightly under-count fulfilled
        # wants if want_ids matter, but the rubrics don't depend on this for
        # closure metrics (those use deals_closed directly).
    return lg


def _rescore_one_rollout(rollout: dict, max_events: int, phase: int,
                          judge_model: str) -> dict:
    """Return a rescored copy of `rollout` after truncating to `max_events`."""
    events = rollout.get("channel_events", []) or []
    truncated_events = events[:max_events]
    last_turn = max((e.get("turn", 0) for e in truncated_events), default=0)

    channel = _build_channel_from_events(truncated_events)
    ledger = _build_ledger_from_deals(rollout.get("deals", []) or [], last_turn)

    personas = rollout.get("personas", [])
    md = rollout.get("metadata", {})
    focal_name = md.get("focal_persona")
    focal = next((p for p in personas if p.get("name") == focal_name), None)
    if focal is None:
        raise RuntimeError(f"focal persona '{focal_name}' missing in rollout {md.get('task_id')}")

    # Compute each rubric from the truncated state.
    rubric_scores = {
        "deal_outcomes": verifiers.compute_deal_outcomes(
            focal=focal, channel=channel, ledger=ledger, all_personas=personas
        ),
        "capability_asymmetry": verifiers.compute_capability_asymmetry(
            focal=focal, channel=channel, ledger=ledger,
            judge_model=judge_model,
        ),
        "negotiation_quality": verifiers.compute_negotiation_quality(
            focal=focal, channel=channel, ledger=ledger,
        ),
        "privacy": verifiers.compute_privacy(
            focal=focal, channel=channel, judge_model=judge_model,
        ),
    }

    # Phase 2 adds review_utilization. The focal_lookups list is NOT persisted
    # into channel_events (lookups are silent server-side queries), so we
    # cannot perfectly reconstruct it from the truncated state. Two cases:
    #   - If the original rollout already has rubric_scores.review_utilization,
    #     reuse it (best-effort: assumes lookups roughly occurred in first 100).
    #   - Otherwise, score with empty lookup list (lookups_made=0).
    if phase >= 2:
        orig_ru = (rollout.get("rubric_scores") or {}).get("review_utilization")
        if orig_ru is not None:
            rubric_scores["review_utilization"] = orig_ru
            rubric_scores["review_utilization"]["_carried_forward_from_full_run"] = True
        else:
            rubric_scores["review_utilization"] = verifiers.compute_review_utilization(
                focal=focal, channel=channel, personas=personas,
                focal_lookups=[],
            )

    # Phase 3 adds swap_quality
    if phase >= 3:
        rubric_scores["swap_quality"] = verifiers.compute_swap_quality(
            focal=focal, ledger=ledger,
        )

    # compute_final_reward expects {rubric_name: combined_scalar}, not dicts.
    combined_parts = {
        "deal_outcomes": rubric_scores["deal_outcomes"].get("combined"),
        "capability_asymmetry": rubric_scores["capability_asymmetry"].get("combined"),
        "negotiation_quality": rubric_scores["negotiation_quality"].get("combined"),
        "privacy": rubric_scores["privacy"].get("combined"),
        "review_utilization": (rubric_scores.get("review_utilization") or {}).get("combined") if phase >= 2 else None,
        "swap_quality": (rubric_scores.get("swap_quality") or {}).get("combined") if phase >= 3 else None,
    }
    final_reward = verifiers.compute_final_reward(combined_parts, phase=phase)
    rubric_scores["final_reward"] = final_reward

    # Build the new rollout dict — preserve everything except the rescored fields.
    new = dict(rollout)
    new["channel_events"] = truncated_events
    new["deals"] = [d for d in (rollout.get("deals") or []) if d.get("turn", 0) <= last_turn]
    new["rubric_scores"] = rubric_scores
    new["reward"] = final_reward
    new["_truncation"] = {
        "max_events": max_events,
        "original_events": len(events),
        "truncated_to": len(truncated_events),
        "max_turn_kept": last_turn,
    }
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", type=Path, required=True,
                    help="Input rollouts.jsonl (one rollout per line)")
    ap.add_argument("--out", dest="out_path", type=Path, required=True,
                    help="Output rollouts_truncated.jsonl")
    ap.add_argument("--max-events", type=int, default=100,
                    help="Truncate each rollout's channel_events to this many entries")
    ap.add_argument("--phase", type=int, required=True, choices=[1, 2, 3])
    ap.add_argument("--judge-model", type=str,
                    default=os.getenv("JUDGE_MODEL", "openai/gpt-4o-2024-11-20"))
    args = ap.parse_args()

    rollouts_in = [json.loads(l) for l in args.in_path.open()]
    print(f"Loaded {len(rollouts_in)} rollouts from {args.in_path}")

    rollouts_out = []
    for i, r in enumerate(rollouts_in):
        md = r.get("metadata") or {}
        set_id = md.get("set_id", f"row{i}")
        focal = md.get("focal_persona", "?")
        new = _rescore_one_rollout(r, max_events=args.max_events,
                                    phase=args.phase, judge_model=args.judge_model)
        print(
            f"  {set_id:6s} {focal:10s} "
            f"events {new['_truncation']['original_events']:3d} → "
            f"{new['_truncation']['truncated_to']:3d}   "
            f"reward {r.get('reward')} → {new['reward']}"
        )
        rollouts_out.append(new)

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    with args.out_path.open("w") as f:
        for r in rollouts_out:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(rollouts_out)} truncated rollouts to {args.out_path}")


if __name__ == "__main__":
    main()
