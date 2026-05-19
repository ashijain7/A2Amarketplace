"""
Generate summary.json for a completed marketplace run.

Called automatically by run.py after each run. Produces a structured JSON
file with every metric that matters for the paper: deal outcomes, negotiation
efficiency, per-agent breakdown, reject breakdown, and run config.
"""

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .channel import Channel
from .ledger import Ledger


def build_summary(
    run_id: str,
    model: str,
    persona_set: int | None,
    scheduler: str,
    seed: int | None,
    max_turns: int,
    stall_limit: int,
    channel: Channel,
    ledger: Ledger,
    personas: list[dict],
    stop_reason: str,
) -> dict:
    """Build the full summary dict from a completed run."""

    personas_by_name = {p["name"]: p for p in personas}

    # --- Channel event counts ---
    action_counts: dict[str, int] = defaultdict(int)
    for e in channel.events:
        action_counts[e.action] += 1

    # --- Deal metrics ---
    deals = ledger.deals
    n_deals = len(deals)
    total_value = sum(d.price for d in deals)
    avg_price = total_value / n_deals if n_deals else 0.0
    avg_seller_margin = (
        sum(d.price - d.seller_floor for d in deals) / n_deals if n_deals else 0.0
    )
    avg_buyer_savings = (
        sum(d.buyer_ceiling - d.price for d in deals if d.buyer_ceiling) / n_deals
        if n_deals else 0.0
    )
    total_events = len(channel.events)
    message_economy = total_events / n_deals if n_deals else 0.0

    constraint_violations = sum(
        1 for d in deals
        if d.price < d.seller_floor or (d.buyer_ceiling and d.price > d.buyer_ceiling)
    )

    deal_list = [
        {
            "deal_id": d.deal_id,
            "turn": d.turn,
            "seller": d.seller,
            "buyer": d.buyer,
            "item": d.item_name,
            "price": d.price,
            "seller_floor": d.seller_floor,
            "buyer_ceiling": d.buyer_ceiling,
            "seller_margin": round(d.price - d.seller_floor, 2),
            "buyer_savings": round(d.buyer_ceiling - d.price, 2) if d.buyer_ceiling else None,
        }
        for d in deals
    ]

    # --- Per-agent breakdown ---
    by_agent: dict[str, dict] = {
        name: {
            "items_sold": 0,
            "items_unsold": 0,
            "wants_fulfilled": 0,
            "wants_unfulfilled": 0,
            "total_revenue": 0.0,
            "total_spent": 0.0,
        }
        for name in personas_by_name
    }

    for d in deals:
        if d.seller in by_agent:
            by_agent[d.seller]["items_sold"] += 1
            by_agent[d.seller]["total_revenue"] += d.price
        if d.buyer in by_agent:
            by_agent[d.buyer]["wants_fulfilled"] += 1
            by_agent[d.buyer]["total_spent"] += d.price

    for p in personas:
        name = p["name"]
        for item in p.get("items_to_sell", []):
            if not ledger.is_sold(item["item_id"]):
                by_agent[name]["items_unsold"] += 1
        for want in p.get("items_to_buy", []):
            if not ledger.is_want_fulfilled(want["want_id"]):
                by_agent[name]["wants_unfulfilled"] += 1

    for name in by_agent:
        by_agent[name]["net"] = round(
            by_agent[name]["total_revenue"] - by_agent[name]["total_spent"], 2
        )

    # --- Reject breakdown ---
    reject_events = [e for e in channel.events if e.action == "reject"]
    reject_reasons: dict[str, int] = defaultdict(int)
    for e in reject_events:
        # message format: "(action rejected: <reason>)"
        match = re.search(r'\(action rejected: (.+)\)', e.message)
        reason = match.group(1) if match else e.message
        # Bucket by first ~6 words for readability
        short = " ".join(reason.split()[:6])
        reject_reasons[short] += 1

    # --- Unfulfilled items and wants ---
    unsold_items = []
    unfulfilled_wants = []
    for p in personas:
        for item in p.get("items_to_sell", []):
            if not ledger.is_sold(item["item_id"]):
                unsold_items.append({
                    "agent": p["name"],
                    "item_id": item["item_id"],
                    "name": item["name"],
                    "floor": item["floor_price"],
                })
        for want in p.get("items_to_buy", []):
            if not ledger.is_want_fulfilled(want["want_id"]):
                unfulfilled_wants.append({
                    "agent": p["name"],
                    "want_id": want["want_id"],
                    "description": want["description"],
                    "ceiling": want["ceiling_price"],
                })

    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "model": model,
            "persona_set": persona_set,
            "scheduler": scheduler,
            "seed": seed,
            "max_turns": max_turns,
            "stall_limit": stall_limit,
        },
        "agents": list(personas_by_name.keys()),
        "run": {
            "total_events": total_events,
            "stop_reason": stop_reason,
            "deals_closed": n_deals,
            "total_value_traded": round(total_value, 2),
            "constraint_violations": constraint_violations,
        },
        "channel_stats": {
            action: action_counts.get(action, 0)
            for action in ("listing", "offer", "counter", "accept", "decline", "reject", "pass")
        },
        "deal_metrics": {
            "count": n_deals,
            "total_value": round(total_value, 2),
            "avg_price": round(avg_price, 2),
            "avg_seller_margin": round(avg_seller_margin, 2),
            "avg_buyer_savings": round(avg_buyer_savings, 2),
            "message_economy": round(message_economy, 1),
        },
        "deals": deal_list,
        "per_agent": by_agent,
        "rejects": {
            "total": len(reject_events),
            "by_reason": dict(reject_reasons),
        },
        "unfulfilled": {
            "unsold_items": unsold_items,
            "unfulfilled_wants": unfulfilled_wants,
        },
    }


def write_summary(summary: dict, path: Path = config.SUMMARY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2))
