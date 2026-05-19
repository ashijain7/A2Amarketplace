"""Marketplace scheduler — per-agent model dispatch.

Adapted from project_deal_poc.scheduler. Instead of a single global model
this loop reads `models_by_agent[agent_name]` for each turn's LLM call.
"""

import random
from dataclasses import dataclass
from typing import Optional

from . import config
from .agent import run_turn, AgentDecision
from .channel import Channel, ChannelEvent
from .ledger import Ledger


@dataclass
class RunResult:
    stop_reason: str         # 'all_agents_done' | 'stall' | 'max_turns'
    turns_used: int


# --- helpers (copied verbatim from PoC, see project_deal_poc/scheduler.py) --

def _is_agent_done(agent_name, personas_by_name, ledger):
    p = personas_by_name[agent_name]
    has_items_to_sell = any(
        not ledger.is_sold(i["item_id"]) for i in p.get("items_to_sell", [])
    )
    has_wants_open = any(
        not ledger.is_want_fulfilled(w["want_id"]) for w in p.get("items_to_buy", [])
    )
    return not (has_items_to_sell or has_wants_open)


def _find_item_in_persona(persona, item_id):
    for i in persona.get("items_to_sell", []):
        if i["item_id"] == item_id:
            return i
    return None


def _reject(agent_name, reason, channel, turn):
    channel.post(turn, agent_name, "reject", None, None, f"(action rejected: {reason})")
    return False, reason


def _resolve_acceptance(accepting_agent, target_event, channel):
    if target_event.action == "listing":
        listing = target_event
        return listing.agent, accepting_agent, listing.target, listing.price, listing
    if target_event.action in ("offer", "counter"):
        listing = channel.get_event(target_event.target)
        if not listing or listing.action != "listing":
            return None, None, None, None, None
        if accepting_agent == listing.agent:
            seller, buyer = listing.agent, target_event.agent
        elif accepting_agent == target_event.agent:
            return None, None, None, None, None
        else:
            if target_event.action == "counter" and target_event.agent == listing.agent:
                seller, buyer = listing.agent, accepting_agent
            else:
                return None, None, None, None, None
        return seller, buyer, listing.target, target_event.price, listing
    return None, None, None, None, None


def _validate_and_apply(decision, agent_name, persona, personas_by_name, channel, ledger, turn):
    action = decision.action
    if action == "pass":
        channel.post(turn, agent_name, "pass", None, None, decision.message or "(pass)")
        return True, "passed"

    if action == "listing":
        item_id = decision.target
        if item_id is None:
            return _reject(agent_name, "listing without item_id", channel, turn)
        my_item = _find_item_in_persona(persona, item_id)
        if my_item is None:
            return _reject(agent_name, f"listing nonexistent item '{item_id}'", channel, turn)
        if ledger.is_sold(item_id):
            return _reject(agent_name, f"listing already-sold item '{item_id}'", channel, turn)
        already_listed = any(
            e.action == "listing" and e.target == item_id and not ledger.is_sold(item_id)
            for e in channel.events
        )
        if already_listed:
            return _reject(agent_name, f"item '{item_id}' is already listed", channel, turn)
        if decision.price is None or decision.price < my_item["floor_price"]:
            return _reject(agent_name,
                f"listing price ${decision.price} below floor ${my_item['floor_price']}",
                channel, turn)
        channel.post(turn, agent_name, "listing", item_id, decision.price, decision.message)
        return True, "listed"

    if action in ("offer", "counter"):
        listing_id = decision.target
        listing = channel.get_event(listing_id) if listing_id else None
        if not listing or listing.action != "listing":
            return _reject(agent_name, f"{action} against non-listing '{listing_id}'", channel, turn)
        if ledger.is_sold(listing.target):
            return _reject(agent_name, f"{action} on sold item '{listing.target}'", channel, turn)
        if action == "offer" and listing.agent == agent_name:
            return _reject(agent_name, "offering on your own listing", channel, turn)
        if action == "offer":
            max_declined = channel.max_declined_price_for(listing_id, agent_name)
            if max_declined is not None and decision.price is not None and decision.price <= max_declined:
                return _reject(agent_name,
                    f"offer price ${decision.price} at or below previously declined ${max_declined}",
                    channel, turn)
        if action == "counter":
            seller = listing.agent
            offerers = {o.agent for o in channel.offers_on_listing(listing_id)}
            if agent_name != seller and agent_name not in offerers:
                return _reject(agent_name, "counter on listing you're not party to", channel, turn)
        if decision.price is None:
            return _reject(agent_name, f"{action} without price", channel, turn)
        channel.post(turn, agent_name, action, listing_id, decision.price, decision.message)
        return True, action

    if action == "decline":
        target = decision.target
        ref = channel.get_event(target) if target else None
        if not ref:
            return _reject(agent_name, f"decline on unknown event '{target}'", channel, turn)
        channel.post(turn, agent_name, "decline", target, None, decision.message)
        return True, "declined"

    if action == "accept":
        target_id = decision.target
        target_event = channel.get_event(target_id) if target_id else None
        if not target_event:
            return _reject(agent_name, f"accept on unknown event '{target_id}'", channel, turn)
        seller, buyer, item_id, price, _listing = _resolve_acceptance(agent_name, target_event, channel)
        if seller is None:
            return _reject(agent_name, f"could not resolve acceptance of '{target_id}'", channel, turn)
        if ledger.is_sold(item_id):
            return _reject(agent_name, f"accept on already-sold item '{item_id}'", channel, turn)
        if seller == buyer:
            return _reject(agent_name, "accept resolves seller == buyer", channel, turn)
        seller_persona = personas_by_name[seller]
        seller_item = _find_item_in_persona(seller_persona, item_id)
        if seller_item is None:
            return _reject(agent_name, f"accept references unknown item '{item_id}'", channel, turn)
        if price < seller_item["floor_price"]:
            return _reject(agent_name,
                f"accept price ${price} below seller floor ${seller_item['floor_price']}",
                channel, turn)
        buyer_persona = personas_by_name[buyer]
        open_wants = [w for w in buyer_persona.get("items_to_buy", [])
                      if not ledger.is_want_fulfilled(w["want_id"])]
        matching = [w for w in open_wants if w["ceiling_price"] >= price]
        if open_wants and not matching:
            return _reject(agent_name,
                f"accept price ${price} above all of {buyer}'s remaining ceilings",
                channel, turn)
        best_want = max(matching, key=lambda w: w["ceiling_price"]) if matching else None
        buyer_ceiling = best_want["ceiling_price"] if best_want else 0
        channel.post(turn, agent_name, "accept", target_id, price, decision.message)
        ledger.record_deal(
            seller=seller, buyer=buyer,
            item_id=item_id, item_name=seller_item["name"],
            price=price, seller_floor=seller_item["floor_price"],
            buyer_ceiling=buyer_ceiling, turn=turn,
        )
        if best_want:
            ledger.fulfill_want(best_want["want_id"])
        return True, "sealed"

    return _reject(agent_name, f"unknown action '{action}'", channel, turn)


# --- main loop -------------------------------------------------------------

def run_marketplace_loop(
    personas: list[dict],
    agent_prompts: dict[str, str],
    models_by_agent: dict[str, str],
    channel: Channel,
    ledger: Ledger,
    seed: Optional[int] = None,
    stall_limit: int = config.STALL_LIMIT,
    max_turns: int = 10_000,
) -> RunResult:
    """Run the marketplace until everyone's done or it stalls.

    `models_by_agent` maps agent name -> OpenRouter model string. Every turn
    looks up the acting agent's model and passes it to run_turn().
    """
    if seed is not None:
        random.seed(seed)

    personas_by_name = {p["name"]: p for p in personas}
    productive = {"listing", "offer", "counter", "accept"}
    turns_since_progress = 0
    stop_reason = "max_turns"
    round_queue: list[str] = []
    turn = 0

    for turn in range(1, max_turns + 1):
        active = [n for n in personas_by_name if not _is_agent_done(n, personas_by_name, ledger)]
        if not active:
            stop_reason = "all_agents_done"
            turn -= 1
            break

        while round_queue:
            cand = round_queue.pop(0)
            if not _is_agent_done(cand, personas_by_name, ledger):
                agent_name = cand
                break
        else:
            round_queue = random.sample(active, len(active))
            agent_name = round_queue.pop(0)

        persona = personas_by_name[agent_name]
        sysprompt = agent_prompts[agent_name]
        model = models_by_agent[agent_name]

        try:
            decision = run_turn(
                agent_name=agent_name,
                system_prompt=sysprompt,
                persona=persona,
                channel=channel,
                ledger=ledger,
                model=model,
            )
        except Exception as e:
            channel.post(turn, agent_name, "pass", None, None, f"(error: {e})")
            turns_since_progress += 1
            if turns_since_progress >= stall_limit:
                stop_reason = "stall"
                break
            continue

        accepted, _ = _validate_and_apply(
            decision, agent_name, persona, personas_by_name, channel, ledger, turn
        )
        if accepted and decision.action in productive:
            turns_since_progress = 0
        elif decision.action == "pass":
            turns_since_progress += 1

        if turns_since_progress >= stall_limit:
            stop_reason = "stall"
            break

    return RunResult(stop_reason=stop_reason, turns_used=turn if turn > 0 else 0)
