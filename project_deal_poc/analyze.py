"""
Post-run analyzer.

Reads deals.json and channel.jsonl and prints a human-readable summary:
  - Per-deal breakdown with floor/ceiling annotations
  - Per-agent outcomes
  - Channel statistics
  - A short transcript excerpt for each deal

Usage:
    python -m project_deal_poc.analyze
"""

import json
from collections import defaultdict
from dataclasses import dataclass

from . import config
from .build_agents import load_personas
from .channel import Channel, ChannelEvent
from .ledger import Ledger


def _load_channel() -> Channel:
    """Reconstruct channel from the on-disk JSONL."""
    c = Channel()
    if not config.CHANNEL_PATH.exists():
        return c
    with config.CHANNEL_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            c.events.append(ChannelEvent(**data))
    c._next_event_num = len(c.events) + 1
    return c


def main():
    if not config.DEALS_PATH.exists():
        print("No deals file found. Run the marketplace first.")
        return

    personas = load_personas()
    personas_by_name = {p["name"]: p for p in personas}
    ledger = Ledger.load()
    channel = _load_channel()

    print("=" * 60)
    print(" Project Deal PoC — Run Summary")
    print("=" * 60)

    # --- Channel stats ---
    action_counts: dict[str, int] = defaultdict(int)
    for e in channel.events:
        action_counts[e.action] += 1
    print(f"\nChannel events: {len(channel.events)} total")
    for action in ("listing", "offer", "counter", "accept", "decline", "reject", "pass"):
        print(f"  {action:8} {action_counts.get(action, 0)}")

    # --- Deals ---
    print(f"\nDeals closed: {len(ledger.deals)}")
    if not ledger.deals:
        print("  (none)")
    for d in ledger.deals:
        margin_seller = d.price - d.seller_floor
        margin_buyer = d.buyer_ceiling - d.price if d.buyer_ceiling else None
        print(f"\n  {d.deal_id} (turn {d.turn}):")
        print(f"    {d.seller} → {d.buyer}: '{d.item_name}'")
        print(f"    price: ${d.price}")
        print(f"    seller floor: ${d.seller_floor}  (margin: +${margin_seller:.2f})")
        if margin_buyer is not None:
            print(f"    buyer ceiling: ${d.buyer_ceiling}  (savings: ${margin_buyer:.2f})")

    # --- Per-agent breakdown ---
    print("\n--- Per-agent outcomes ---")
    by_agent: dict[str, dict] = {
        name: {"sold": [], "bought": [], "unsold": [], "unbought": []}
        for name in personas_by_name
    }
    for d in ledger.deals:
        by_agent[d.seller]["sold"].append(d)
        by_agent[d.buyer]["bought"].append(d)
    for p in personas:
        name = p["name"]
        for i in p.get("items_to_sell", []):
            if not ledger.is_sold(i["item_id"]):
                by_agent[name]["unsold"].append(i)
        for w in p.get("items_to_buy", []):
            if not ledger.is_want_fulfilled(w["want_id"]):
                by_agent[name]["unbought"].append(w)

    for name, info in by_agent.items():
        print(f"\n  {name}:")
        if info["sold"]:
            for d in info["sold"]:
                print(f"    SOLD     '{d.item_name}' to {d.buyer} for ${d.price}")
        if info["bought"]:
            for d in info["bought"]:
                print(f"    BOUGHT   '{d.item_name}' from {d.seller} for ${d.price}")
        if info["unsold"]:
            for i in info["unsold"]:
                print(f"    unsold   '{i['name']}' (floor ${i['floor_price']})")
        if info["unbought"]:
            for w in info["unbought"]:
                print(f"    unbought {w['description']} (ceiling ${w['ceiling_price']})")

    # --- A few transcript excerpts ---
    if ledger.deals and channel.events:
        print("\n--- Transcript excerpts (around each deal) ---")
        for d in ledger.deals[:3]:
            print(f"\n  Around {d.deal_id} (turn {d.turn}):")
            window = [e for e in channel.events if abs(e.turn - d.turn) <= 3]
            relevant = [e for e in window if e.agent in (d.seller, d.buyer)]
            for e in relevant[-6:]:
                print(f"    [t{e.turn}] {e.agent} ({e.action}): {e.message[:120]}")

    # --- Constraint check ---
    print("\n--- Constraint check ---")
    violations = 0
    for d in ledger.deals:
        if d.price < d.seller_floor:
            violations += 1
            print(f"  VIOLATION {d.deal_id}: price ${d.price} below seller floor ${d.seller_floor}")
        if d.buyer_ceiling and d.price > d.buyer_ceiling:
            violations += 1
            print(f"  VIOLATION {d.deal_id}: price ${d.price} above buyer ceiling ${d.buyer_ceiling}")
    if violations == 0:
        print("  All deals respected floors and ceilings. ✓")


if __name__ == "__main__":
    main()
