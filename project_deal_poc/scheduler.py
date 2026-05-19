"""
The marketplace scheduler.

Mirrors Project Deal's "random loop": on each turn we pick an active
agent uniformly at random, run its turn, validate its action against
the ledger, and append the result to the channel. If the action seals
a deal, we record it and mark the item sold.

Stopping conditions:
  - max_turns reached, OR
  - no agent has remaining business (all items sold AND all wants
    closed), OR
  - stall_limit consecutive turns with no listing/offer/accept event.
"""

import random
from typing import Optional

from . import config
from .agent import run_turn, AgentDecision
from .channel import Channel, ChannelEvent
from .ledger import Ledger


# ---------- Helpers for action validation ---------- #

def _is_agent_done(agent_name: str, personas_by_name: dict, ledger: Ledger) -> bool:
    """An agent has no business left if all items sold AND all wants closed."""
    p = personas_by_name[agent_name]
    has_items_to_sell = any(
        not ledger.is_sold(i["item_id"])
        for i in p.get("items_to_sell", [])
    )
    has_wants_open = any(
        not ledger.is_want_fulfilled(w["want_id"])
        for w in p.get("items_to_buy", [])
    )
    return not (has_items_to_sell or has_wants_open)


def _find_item_in_persona(persona: dict, item_id: str) -> Optional[dict]:
    for i in persona.get("items_to_sell", []):
        if i["item_id"] == item_id:
            return i
    return None


def _validate_and_apply(
    decision: AgentDecision,
    agent_name: str,
    persona: dict,
    personas_by_name: dict,
    channel: Channel,
    ledger: Ledger,
    turn: int,
) -> tuple[bool, str]:
    """
    Validate the decision against current state and apply side effects
    (post to channel, seal deal). Returns (accepted, reason).

    If the action is invalid (e.g., accepting an already-sold item),
    we post a 'pass' on the agent's behalf and return (False, reason).
    """

    action = decision.action

    # --- pass: always valid ---
    if action == "pass":
        channel.post(turn, agent_name, "pass", None, None, decision.message or "(pass)")
        return True, "passed"

    # --- listing: must be your own un-sold item ---
    if action == "listing":
        item_id = decision.target
        if item_id is None:
            return _reject(agent_name, "listing without item_id", channel, turn)
        my_item = _find_item_in_persona(persona, item_id)
        if my_item is None:
            return _reject(agent_name, f"listing nonexistent item '{item_id}'", channel, turn)
        if ledger.is_sold(item_id):
            return _reject(agent_name, f"listing already-sold item '{item_id}'", channel, turn)
        # Don't allow duplicate active listings of the same item
        already_listed = any(
            e.action == "listing" and e.target == item_id and not ledger.is_sold(item_id)
            for e in channel.events
        )
        if already_listed:
            return _reject(agent_name, f"item '{item_id}' is already listed", channel, turn)
        if decision.price is None or decision.price < my_item["floor_price"]:
            return _reject(
                agent_name,
                f"listing price ${decision.price} below floor ${my_item['floor_price']}",
                channel,
                turn,
            )
        channel.post(turn, agent_name, "listing", item_id, decision.price, decision.message)
        return True, "listed"

    # --- offer / counter: must reference an active listing ---
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
            if max_declined is not None and decision.price <= max_declined:
                return _reject(
                    agent_name,
                    f"offer price ${decision.price} at or below previously declined ${max_declined}",
                    channel,
                    turn,
                )
        if action == "counter":
            # Counters can come from either side, but you can only counter
            # if you're a participant in this negotiation (seller or prior offerer).
            seller = listing.agent
            offerers = {o.agent for o in channel.offers_on_listing(listing_id)}
            if agent_name != seller and agent_name not in offerers:
                return _reject(
                    agent_name, f"counter on listing you're not party to", channel, turn
                )
        if decision.price is None:
            return _reject(agent_name, f"{action} without price", channel, turn)
        channel.post(turn, agent_name, action, listing_id, decision.price, decision.message)
        return True, action

    # --- decline: just a signal, no state change ---
    if action == "decline":
        target = decision.target
        ref = channel.get_event(target) if target else None
        if not ref:
            return _reject(agent_name, f"decline on unknown event '{target}'", channel, turn)
        channel.post(turn, agent_name, "decline", target, None, decision.message)
        return True, "declined"

    # --- accept: the critical case — seals a deal ---
    if action == "accept":
        target_id = decision.target
        target_event = channel.get_event(target_id) if target_id else None
        if not target_event:
            return _reject(agent_name, f"accept on unknown event '{target_id}'", channel, turn)

        # Figure out who is the seller, who is the buyer, what's the price, what's the item.
        seller, buyer, item_id, price, listing_event = _resolve_acceptance(
            agent_name, target_event, channel
        )

        if seller is None:
            return _reject(
                agent_name,
                f"could not resolve acceptance of '{target_id}'",
                channel,
                turn,
            )

        # Sanity: the item must not already be sold
        if ledger.is_sold(item_id):
            return _reject(agent_name, f"accept on already-sold item '{item_id}'", channel, turn)

        # Sanity: buyer must not be seller
        if seller == buyer:
            return _reject(agent_name, "accept resolves seller == buyer", channel, turn)

        # Sanity: price must respect seller's floor
        seller_persona = personas_by_name[seller]
        seller_item = _find_item_in_persona(seller_persona, item_id)
        if seller_item is None:
            return _reject(agent_name, f"accept references unknown item '{item_id}'", channel, turn)
        if price < seller_item["floor_price"]:
            return _reject(
                agent_name,
                f"accept price ${price} below seller floor ${seller_item['floor_price']}",
                channel,
                turn,
            )

        # Find the specific want that matches this purchase.
        # "Matching" = ceiling >= price. Pick the one with highest ceiling
        # so we don't close a cheap want when the buyer has a more expensive one open.
        buyer_persona = personas_by_name[buyer]
        open_wants = [
            w for w in buyer_persona.get("items_to_buy", [])
            if not ledger.is_want_fulfilled(w["want_id"])
        ]
        matching_wants = [w for w in open_wants if w["ceiling_price"] >= price]
        if open_wants and not matching_wants:
            return _reject(
                agent_name,
                f"accept price ${price} above all of {buyer}'s remaining ceilings",
                channel,
                turn,
            )
        best_want = max(matching_wants, key=lambda w: w["ceiling_price"]) if matching_wants else None
        buyer_ceiling = best_want["ceiling_price"] if best_want else 0

        # All checks pass — post the accept and record the deal.
        channel.post(turn, agent_name, "accept", target_id, price, decision.message)
        deal = ledger.record_deal(
            seller=seller,
            buyer=buyer,
            item_id=item_id,
            item_name=seller_item["name"],
            price=price,
            seller_floor=seller_item["floor_price"],
            buyer_ceiling=buyer_ceiling,
            turn=turn,
        )

        # Fulfill the matched want so this agent stops bidding for it.
        if best_want:
            ledger.fulfill_want(best_want["want_id"])

        print(
            f"  [SEAL] turn {turn}: {seller} sold '{seller_item['name']}' to {buyer} for ${price} "
            f"(floor ${seller_item['floor_price']}, ceil ${buyer_ceiling})"
        )
        return True, f"sealed deal {deal.deal_id}"

    return _reject(agent_name, f"unknown action '{action}'", channel, turn)


def _resolve_acceptance(
    accepting_agent: str,
    target_event: ChannelEvent,
    channel: Channel,
):
    """
    Figure out seller/buyer/item/price for an 'accept' event.

    Cases:
      A) target is an 'offer' or 'counter' from another agent:
         The accepting agent is the recipient of that proposal.
         - If the underlying listing belongs to accepting_agent
           (they're the seller), then buyer = target_event.agent.
         - If accepting_agent is a prospective buyer accepting the
           seller's counter, then seller = target_event.agent
           (the seller who countered), and buyer = accepting_agent.
      B) target is a 'listing' itself:
         The accepting agent is buying at the listing's asking price.
         seller = listing.agent, buyer = accepting_agent.
    """
    if target_event.action == "listing":
        listing = target_event
        seller = listing.agent
        buyer = accepting_agent
        return seller, buyer, listing.target, listing.price, listing

    if target_event.action in ("offer", "counter"):
        listing = channel.get_event(target_event.target)
        if not listing or listing.action != "listing":
            return None, None, None, None, None

        if accepting_agent == listing.agent:
            # The seller is accepting a buyer's offer/counter.
            seller = listing.agent
            buyer = target_event.agent
        elif accepting_agent == target_event.agent:
            # Self-accept of your own offer — invalid.
            return None, None, None, None, None
        else:
            # Someone unrelated trying to accept. We allow it only if
            # accepting_agent is the buyer accepting a seller's counter.
            if target_event.action == "counter" and target_event.agent == listing.agent:
                seller = listing.agent
                buyer = accepting_agent
            else:
                return None, None, None, None, None

        return seller, buyer, listing.target, target_event.price, listing

    return None, None, None, None, None


def _reject(agent_name: str, reason: str, channel: Channel, turn: int):
    print(f"  [reject] {agent_name} turn {turn}: {reason}")
    channel.post(
        turn, agent_name, "reject", None, None,
        f"(action rejected: {reason})",
    )
    return False, reason


# ---------- Rotation scheduler helper ---------- #

def _pick_next_agent_rotation(active: list[str], queue: list[str]) -> tuple[str, list[str]]:
    """Pop the next agent from the rotation queue, rebuilding if empty. Returns (agent, queue)."""
    if not queue:
        queue = random.sample(active, len(active))
    while queue:
        candidate = queue.pop(0)
        if candidate in active:
            return candidate, queue
    return random.choice(active), []


# ---------- Main loop ---------- #

def run_marketplace(
    personas: list[dict],
    agent_prompts: dict[str, str],
    model: str = config.DEFAULT_MODEL,
    max_turns: int = config.MAX_TURNS,
    stall_limit: int = config.STALL_LIMIT,
    seed: Optional[int] = None,
    scheduler: str = "rotation",
) -> tuple[Channel, Ledger, str]:
    """Run the marketplace end to end. Returns (channel, ledger, stop_reason).
    stop_reason is one of: 'all_agents_done', 'stall', 'max_turns'.
    """
    if seed is not None:
        random.seed(seed)

    personas_by_name = {p["name"]: p for p in personas}
    channel = Channel()
    ledger = Ledger()
    channel.clear()
    ledger.clear()

    productive_actions = {"listing", "offer", "counter", "accept"}
    turns_since_progress = 0
    stop_reason = "max_turns"

    print(f"\n=== Marketplace run ===")
    print(f"Agents: {list(personas_by_name)}")
    print(f"Model: {model}")
    print(f"Max turns: {max_turns}, stall limit: {stall_limit}\n")

    round_queue: list[str] = []

    for turn in range(1, max_turns + 1):
        # Pick an active agent
        active = [
            name for name in personas_by_name
            if not _is_agent_done(name, personas_by_name, ledger)
        ]
        if not active:
            print(f"\n[scheduler] All agents done at turn {turn - 1}.")
            stop_reason = "all_agents_done"
            break

        if scheduler == "rotation":
            while round_queue:
                candidate = round_queue.pop(0)
                if not _is_agent_done(candidate, personas_by_name, ledger):
                    agent_name = candidate
                    break
            else:
                round_queue = random.sample(active, len(active))
                agent_name = round_queue.pop(0)
        else:
            agent_name = random.choice(active)
        persona = personas_by_name[agent_name]
        sysprompt = agent_prompts[agent_name]

        print(f"\n[turn {turn}] {agent_name} acting...")
        try:
            decision = run_turn(
                agent_name=agent_name,
                system_prompt=sysprompt,
                persona=persona,
                channel=channel,
                ledger=ledger,
                model=model,
            )
            if decision.action != "pass":
                print(f"  → {decision.action.upper()}: {decision.message[:120]}")
        except Exception as e:
            print(f"  [error] {agent_name}: {e}")
            channel.post(turn, agent_name, "pass", None, None, f"(error: {e})")
            continue

        accepted, _reason = _validate_and_apply(
            decision, agent_name, persona, personas_by_name, channel, ledger, turn
        )

        # Track stall — only genuine passes count, not rejected attempts
        if accepted and decision.action in productive_actions:
            turns_since_progress = 0
        elif decision.action == "pass":
            turns_since_progress += 1

        if turns_since_progress >= stall_limit:
            print(f"\n[scheduler] Stalled — {stall_limit} turns without progress. Stopping.")
            stop_reason = "stall"
            break

    print(f"\n=== Run finished ===")
    print(f"Turns played: {len(channel.events)}")
    print(f"Deals closed: {len(ledger.deals)}")
    return channel, ledger, stop_reason
