"""
A single agent's turn in the marketplace.

Given an agent's name, system prompt, and the current channel + ledger
state, this module:
  1. Builds a human-readable "what's happening in the marketplace" view
  2. Calls the LLM
  3. Parses the structured action response
  4. Returns a validated AgentDecision the scheduler can act on

The scheduler is what actually mutates state. This module is pure
turn-logic.
"""

from dataclasses import dataclass
from typing import Optional

from . import config
from .channel import Channel, ChannelEvent
from .ledger import Ledger
from .llm import call_llm, parse_json_response


@dataclass
class AgentDecision:
    action: str                  # listing | offer | counter | accept | decline | pass
    target: Optional[str]
    price: Optional[float]
    message: str
    raw: dict                    # the full parsed JSON, for logging


VALID_ACTIONS = {"listing", "offer", "counter", "accept", "decline", "pass"}


def _format_channel_view(
    agent_name: str,
    persona: dict,
    channel: Channel,
    ledger: Ledger,
) -> str:
    """Build the per-turn context message sent as the user prompt."""
    lines = []
    lines.append(f"You are {agent_name}. It is now your turn in the marketplace.\n")

    # --- Status of your own listings ---
    my_item_ids = {i["item_id"] for i in persona.get("items_to_sell", [])}
    my_active_listings = [
        e for e in channel.events
        if e.action == "listing"
        and e.agent == agent_name
        and e.target in my_item_ids
        and not ledger.is_sold(e.target)
    ]
    my_unlisted = [
        i for i in persona.get("items_to_sell", [])
        if not ledger.is_sold(i["item_id"])
        and not any(e.target == i["item_id"] for e in my_active_listings)
    ]

    lines.append("=== YOUR ITEMS TO SELL ===")
    if my_unlisted:
        lines.append("Not yet listed:")
        for i in my_unlisted:
            lines.append(f"  - {i['item_id']}: {i['name']} (floor ${i['floor_price']})")
    if my_active_listings:
        lines.append("Currently listed:")
        for lst in my_active_listings:
            offers = channel.offers_on_listing(lst.event_id)
            offers_str = ""
            if offers:
                # Show only the latest offer/counter per other agent
                latest_by_agent: dict[str, ChannelEvent] = {}
                for o in offers:
                    latest_by_agent[o.agent] = o
                offers_str = "; offers: " + ", ".join(
                    f"{o.agent} ${o.price} (id {o.event_id})"
                    for o in latest_by_agent.values()
                )
            lines.append(
                f"  - listing {lst.event_id}: item {lst.target} asking ${lst.price}{offers_str}"
            )
    if not my_unlisted and not my_active_listings:
        lines.append("  (you have no items left to sell)")
    lines.append("")

    # --- What you want to buy and what's available ---
    lines.append("=== YOUR WANTS ===")
    open_wants = [w for w in persona.get("items_to_buy", [])
                  if not ledger.is_want_fulfilled(w["want_id"])]
    if open_wants:
        for w in open_wants:
            lines.append(f"  - {w['want_id']}: {w['description']} (ceiling ${w['ceiling_price']})")
    else:
        lines.append("  (you have no remaining wants)")
    lines.append("")

    # --- Other agents' active listings ---
    lines.append("=== ACTIVE LISTINGS FROM OTHER AGENTS ===")
    others = [
        e for e in channel.active_listings(ledger.sold_item_ids)
        if e.agent != agent_name
    ]
    if others:
        for lst in others:
            # Show your own latest offer on it, if any
            your_offers = [
                o for o in channel.offers_on_listing(lst.event_id)
                if o.agent == agent_name
            ]
            you_str = ""
            if your_offers:
                latest = your_offers[-1]
                you_str = f"; your latest {latest.action}: ${latest.price} (id {latest.event_id})"
            # Show any seller counter to you
            counter_str = ""
            seller_counters = [
                o for o in channel.events
                if o.action == "counter"
                and o.target == lst.event_id
                and o.agent == lst.agent
            ]
            if seller_counters:
                latest_c = seller_counters[-1]
                counter_str = f"; seller's counter to you: ${latest_c.price} (id {latest_c.event_id})"
            lines.append(
                f"  - {lst.event_id} from {lst.agent}: '{lst.message[:80]}' asking ${lst.price}{you_str}{counter_str}"
            )
    else:
        lines.append("  (no active listings from others)")
    lines.append("")

    # --- Deals already closed (so agent doesn't try to buy sold items) ---
    if ledger.deals:
        lines.append("=== DEALS ALREADY CLOSED ===")
        for d in ledger.deals[-5:]:
            lines.append(f"  - {d.seller} sold '{d.item_name}' to {d.buyer} for ${d.price}")
        lines.append("")

    # --- Full channel history (excluding pass events) ---
    lines.append("=== FULL CHANNEL HISTORY (oldest first, pass actions excluded) ===")
    history = [e for e in channel.events if e.action != "pass"]
    if history:
        for e in history:
            lines.append(f"  [turn {e.turn}] {e.agent} ({e.action}): {e.message[:120]}")
    else:
        lines.append("  (channel is empty — you can post the first listing)")
    lines.append("")

    lines.append(
        "Decide your single action for this turn and respond with the JSON object only."
    )

    return "\n".join(lines)


def run_turn(
    agent_name: str,
    system_prompt: str,
    persona: dict,
    channel: Channel,
    ledger: Ledger,
    model: str = config.DEFAULT_MODEL,
) -> AgentDecision:
    """Run one agent turn end-to-end. Returns a validated decision."""
    user_msg = _format_channel_view(agent_name, persona, channel, ledger)

    raw_text = call_llm(
        system=system_prompt,
        user=user_msg,
        model=model,
    )

    try:
        parsed = parse_json_response(raw_text)
    except ValueError as e:
        # Defensive fallback: treat unparseable response as a pass
        print(f"[agent] {agent_name}: unparseable response, treating as pass. ({e})")
        return AgentDecision(
            action="pass",
            target=None,
            price=None,
            message="(malformed response, passing turn)",
            raw={"error": str(e), "raw": raw_text[:300]},
        )

    action = parsed.get("action", "pass")
    if action not in VALID_ACTIONS:
        print(f"[agent] {agent_name}: invalid action '{action}', treating as pass.")
        action = "pass"

    price = parsed.get("price")
    if price is not None:
        try:
            price = float(price)
        except (TypeError, ValueError):
            price = None

    return AgentDecision(
        action=action,
        target=parsed.get("target"),
        price=price,
        message=parsed.get("message", "")[:500],
        raw=parsed,
    )
