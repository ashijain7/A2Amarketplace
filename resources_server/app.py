"""
Marketplace Resources Server for Approach 1 Phase 1.

Exposes 6 tool endpoints the focal agent calls. Each tool mutates the
channel/ledger, then runs N opponent turns to advance the marketplace.
At end-of-rollout, /verify computes rubric scores.

Lifecycle under NeMo Gym:
  1. NeMo Gym boots the server via setup_webserver() (inherits /seed_session,
     /verify, /aggregate_metrics + session middleware from SimpleResourcesServer).
  2. Per-rollout: simple_agent POSTs /seed_session with task metadata. We
     create a MarketplaceState keyed by request.session["session_id"].
  3. Tool calls (POST /post_listing etc.) look up the per-session state.
  4. POST /verify scores the rubrics for that session and cleans up state.

For backwards compatibility, attach_state(state) installs a "default" session
state so legacy tests / scripts that hit tool endpoints directly (without a
seed_session call) keep working.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict

from marketplace.channel import Channel
from marketplace.ledger import Ledger
from marketplace.build_agents import build_agent_prompts
from resources_server.opponent_runner import OpponentRunner


OPPONENT_TURNS_PER_FOCAL_ACTION = 1  # was 2 — reduced to keep context lean for 60-task scalability
_DEFAULT_SESSION_KEY = "__default__"


@dataclass
class MarketplaceState:
    """All per-rollout state held by the server."""
    focal_name: str
    personas: list[dict]
    opponents_model: str
    focal_model: str
    judge_model: str
    seed: int
    set_id: str
    config_name: str
    data_dir: Path
    phase: int = 1

    channel: Channel = field(init=False)
    ledger: Ledger = field(init=False)
    prompts: dict = field(init=False)
    runner: OpponentRunner = field(init=False)
    _turn: int = 0
    # Phase 2: per-rollout log of every lookup_agent call by the focal.
    # Used by the review_utilization rubric.
    _focal_lookups: list = field(default_factory=list)
    settlement: object = None

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.channel = Channel(path=self.data_dir / "channel.jsonl")
        self.channel.clear()
        self.ledger = Ledger(path=self.data_dir / "deals.json")
        self.ledger.clear()
        self.prompts = build_agent_prompts(self.personas)
        self.runner = OpponentRunner(
            focal_name=self.focal_name,
            personas=self.personas,
            prompts=self.prompts,
            channel=self.channel,
            ledger=self.ledger,
            opponents_model=self.opponents_model,
            phase=self.phase,
        )
        from marketplace import config as mp_config
        if mp_config.ENABLE_SETTLEMENT and self.phase in (1, 2):
            from resources_server.settlement import Settlement
            self.settlement = Settlement(
                personas=self.personas, focal_name=self.focal_name,
                seed=self.seed, data_dir=self.data_dir,
                scam_on=mp_config.SETTLEMENT_SCAM, dud_payers=mp_config.SETTLEMENT_DUD,
            )
            self.runner.settlement = self.settlement

    def next_turn(self) -> int:
        self._turn += 1
        return self._turn


# --- Request/response schemas ----------------------------------------

class PostListingBody(BaseModel):
    item_id: str
    price: float
    message: str = ""


class MakeOfferBody(BaseModel):
    target_listing_id: str
    price: float
    message: str = ""


class CounterOfferBody(BaseModel):
    target_offer_id: str
    price: float
    message: str = ""


class AcceptOfferBody(BaseModel):
    target_offer_id: str
    message: str = ""


class RejectOfferBody(BaseModel):
    target_offer_id: str
    message: str = ""


class PassBody(BaseModel):
    message: str = ""


class LookupAgentBody(BaseModel):
    name: str
    role: str  # "seller" | "buyer"


# Phase 3 swap bodies
class PostListingPhase3Body(BaseModel):
    item_id: str
    wants: list[str]      # categories the lister accepts in trade
    message: str = ""


class ProposeSwapBody(BaseModel):
    target_listing_id: str
    my_item_id: str
    message: str = ""


class AcceptSwapBody(BaseModel):
    target_proposal_id: str
    message: str = ""


class RejectSwapBody(BaseModel):
    target_proposal_id: str
    message: str = ""


# --- Shared helpers used by both legacy build_app() and MarketplaceServer ----

def _is_focal_done(state: MarketplaceState) -> bool:
    """True iff the focal has sold all their items AND fulfilled all their wants."""
    focal = next(
        (p for p in state.personas if p.get("name") == state.focal_name), None
    )
    if focal is None:
        return False
    items_to_sell = focal.get("items_to_sell", [])
    items_to_buy = focal.get("items_to_buy", [])
    sold = state.ledger.sold_item_ids
    fulfilled = state.ledger.fulfilled_want_ids
    all_sold = all(it.get("item_id") in sold for it in items_to_sell)
    all_bought = all(w.get("want_id") in fulfilled for w in items_to_buy)
    if getattr(state, "settlement", None) is not None:
        if state.settlement.has_pending_for(state.focal_name):
            return False
    return all_sold and all_bought


def _role_rating_for_event(personas: list[dict], agent: str, action: str) -> Optional[float]:
    """Phase 2: return the actor's role-scoped rating for this event type.
    Listings show the lister's seller_rating; offers/counters show the
    offerer's buyer_rating; other actions return None. Phase 1 personas
    have no rating fields and this returns None for everyone.
    """
    persona = next((p for p in personas if p.get("name") == agent), None)
    if not persona:
        return None
    if action == "listing":
        return persona.get("seller_rating")
    if action in ("offer", "counter"):
        return persona.get("buyer_rating")
    return None


def _state_snapshot(state: MarketplaceState) -> dict:
    """Return the marketplace state the focal agent sees after each tool call.

    Always returns a plain dict (JSON-serialised as a string by FastAPI).
    Images are embedded upfront in the initial task prompt (see generate_tasks.py
    build_initial_user_message_multimodal), not repeated in every tool response.
    """
    active = []
    for e in state.channel.active_listings(state.ledger.sold_item_ids):
        rating = _role_rating_for_event(state.personas, e.agent, "listing")
        entry = {"event_id": e.event_id, "agent": e.agent, "item_id": e.target,
                 "price": e.price, "message": e.message}
        if rating is not None:
            entry["seller_rating"] = rating
        if e.wants is not None:
            entry["wants"] = e.wants
        if e.image_path is not None:
            entry["image_path"] = e.image_path
        active.append(entry)
    recent_events = []
    for e in state.channel.recent(20):
        entry = {"event_id": e.event_id, "turn": e.turn, "agent": e.agent,
                 "action": e.action, "target": e.target, "price": e.price,
                 "message": e.message}
        rating = _role_rating_for_event(state.personas, e.agent, e.action)
        if rating is not None:
            entry["actor_rating"] = rating
        if e.wants is not None:
            entry["wants"] = e.wants
        if e.image_path is not None:
            entry["image_path"] = e.image_path
        if e.swap_item_id is not None:
            entry["swap_item_id"] = e.swap_item_id
            # Surface the proposer's item category so the focal can match
            # it against its own want_categories without guessing. This is
            # the most-asked-for info during a swap decision.
            proposer = next(
                (p for p in state.personas if p.get("name") == e.agent), None
            )
            if proposer:
                for it in proposer.get("items_to_sell", []) or []:
                    if it.get("item_id") == e.swap_item_id:
                        entry["swap_item_category"] = it.get("category")
                        entry["swap_item_name"] = it.get("name")
                        break
        recent_events.append(entry)
    deals = []
    for d in state.ledger.deals:
        deal_entry = {
            "deal_id": d.deal_id, "seller": d.seller, "buyer": d.buyer,
            "item_id": d.item_id, "price": d.price, "turn": d.turn,
        }
        if getattr(d, "deal_type", "money") == "swap":
            deal_entry["deal_type"] = "swap"
            deal_entry["item_b_id"] = d.item_b_id
        deals.append(deal_entry)
    snapshot = {
        "active_listings": active,
        "recent_events": recent_events,
        "deals": deals,
        "turn": state._turn,
    }
    # Auto-terminate hint: when the focal has finished all their business,
    # we signal the LLM that it may stop calling tools. simple_agent ends
    # the rollout when the LLM produces a message without a tool call.
    if _is_focal_done(state):
        snapshot["focal_done"] = True
        snapshot["hint"] = (
            "Your marketplace business is COMPLETE — all your items are sold "
            "and all your wants are fulfilled. Reply with a final summary "
            "message (do NOT call another tool) to end this rollout."
        )

    if getattr(state, "settlement", None) is not None:
        snapshot["settlement"] = state.settlement.focal_snapshot()
    return snapshot


def _run_opponents(state: MarketplaceState):
    starting_turn = state._turn + 1
    state.runner.run_n_turns(
        n=OPPONENT_TURNS_PER_FOCAL_ACTION,
        starting_turn=starting_turn,
    )
    state._turn = starting_turn + OPPONENT_TURNS_PER_FOCAL_ACTION - 1


def _apply_post_listing(state: MarketplaceState, body: PostListingBody) -> dict:
    turn = state.next_turn()
    state.channel.post(
        turn=turn, agent=state.focal_name, action="listing",
        target=body.item_id, price=body.price, message=body.message,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_post_listing_any(state: MarketplaceState, payload: dict) -> dict:
    """Dispatch post_listing by payload shape.

    Phase 1/2 payload: {item_id, price, message}
    Phase 3 payload:   {item_id, wants, message}
    """
    if "wants" in payload and "price" not in payload:
        body = PostListingPhase3Body(**payload)
        return _apply_post_listing_phase3(state, body)
    body = PostListingBody(**payload)
    return _apply_post_listing(state, body)


def _apply_make_offer(state: MarketplaceState, body: MakeOfferBody) -> dict:
    turn = state.next_turn()
    state.channel.post(
        turn=turn, agent=state.focal_name, action="offer",
        target=body.target_listing_id, price=body.price, message=body.message,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_counter_offer(state: MarketplaceState, body: CounterOfferBody) -> dict:
    turn = state.next_turn()
    ref = state.channel.get_event(body.target_offer_id)
    listing_target = ref.target if ref else body.target_offer_id
    state.channel.post(
        turn=turn, agent=state.focal_name, action="counter",
        target=listing_target, price=body.price, message=body.message,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_accept_offer(state: MarketplaceState, body: AcceptOfferBody) -> dict:
    turn = state.next_turn()
    ref = state.channel.get_event(body.target_offer_id)
    accepted_price = ref.price if ref and ref.price is not None else 0.0
    state.channel.post(
        turn=turn, agent=state.focal_name, action="accept",
        target=body.target_offer_id, price=accepted_price, message=body.message,
    )
    if ref:
        state.runner._apply_accept(
            buyer_or_seller=state.focal_name,
            target=body.target_offer_id,
            price=accepted_price,
            turn=turn,
        )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_reject_offer(state: MarketplaceState, body: RejectOfferBody) -> dict:
    turn = state.next_turn()
    state.channel.post(
        turn=turn, agent=state.focal_name, action="decline",
        target=body.target_offer_id, price=None, message=body.message,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_pass(state: MarketplaceState, body: PassBody) -> dict:
    turn = state.next_turn()
    state.channel.post(
        turn=turn, agent=state.focal_name, action="pass",
        target=None, price=None, message=body.message,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _focal_persona(state: MarketplaceState) -> dict | None:
    return next((p for p in state.personas if p.get("name") == state.focal_name), None)


def _find_item(persona: dict, item_id: str) -> dict | None:
    for it in (persona or {}).get("items_to_sell", []) or []:
        if it.get("item_id") == item_id:
            return it
    return None


def _apply_post_listing_phase3(state: MarketplaceState, body: PostListingPhase3Body) -> dict:
    turn = state.next_turn()
    focal = _focal_persona(state)
    item = _find_item(focal, body.item_id) if focal else None
    image_path = item.get("image_path") if item else None
    state.channel.post(
        turn=turn, agent=state.focal_name, action="listing",
        target=body.item_id, price=None, message=body.message,
        wants=list(body.wants or []),
        image_path=image_path,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_propose_swap(state: MarketplaceState, body: ProposeSwapBody) -> dict:
    """Focal proposes to trade my_item_id for the listing target_listing_id."""
    from marketplace.swap_match import is_valid_swap, normalize_category

    turn = state.next_turn()
    focal = _focal_persona(state)
    my_item = _find_item(focal, body.my_item_id) if focal else None
    listing = state.channel.get_event(body.target_listing_id)

    # Validation: my_item must exist, listing must exist + be a listing
    if my_item is None:
        state.channel.post(
            turn=turn, agent=state.focal_name, action="pass",
            target=None, price=None,
            message=f"[swap rejected: my_item_id '{body.my_item_id}' not found]",
        )
        _run_opponents(state)
        return _state_snapshot(state)
    if listing is None or listing.action != "listing":
        state.channel.post(
            turn=turn, agent=state.focal_name, action="pass",
            target=None, price=None,
            message=f"[swap rejected: target {body.target_listing_id} is not a listing]",
        )
        _run_opponents(state)
        return _state_snapshot(state)

    # Category match against listing's declared wants
    ok, reason = is_valid_swap(my_item.get("category"), listing.wants or [])
    if not ok:
        state.channel.post(
            turn=turn, agent=state.focal_name, action="pass",
            target=None, price=None,
            message=f"[swap rejected: {reason}]",
        )
        _run_opponents(state)
        return _state_snapshot(state)

    image_path = my_item.get("image_path")
    state.channel.post(
        turn=turn, agent=state.focal_name, action="swap_proposal",
        target=body.target_listing_id, price=None, message=body.message,
        swap_item_id=body.my_item_id,
        image_path=image_path,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_accept_swap(state: MarketplaceState, body: AcceptSwapBody) -> dict:
    """Focal accepts a swap proposal on its own listing. Closes the deal."""
    turn = state.next_turn()
    proposal = state.channel.get_event(body.target_proposal_id)
    if proposal is None or proposal.action != "swap_proposal":
        state.channel.post(
            turn=turn, agent=state.focal_name, action="pass",
            target=None, price=None,
            message=f"[swap accept failed: {body.target_proposal_id} not a swap_proposal]",
        )
        _run_opponents(state)
        return _state_snapshot(state)

    # Resolve the listing and both items
    listing = state.channel.get_event(proposal.target) if proposal.target else None
    if listing is None or listing.action != "listing":
        state.channel.post(
            turn=turn, agent=state.focal_name, action="pass",
            target=None, price=None,
            message=f"[swap accept failed: listing not found]",
        )
        _run_opponents(state)
        return _state_snapshot(state)

    agent_a = listing.agent             # listing owner (focal in this path)
    agent_b = proposal.agent            # proposer
    item_a_id = listing.target          # listing's item
    item_b_id = proposal.swap_item_id   # proposer's item

    persona_a = next((p for p in state.personas if p["name"] == agent_a), None)
    persona_b = next((p for p in state.personas if p["name"] == agent_b), None)
    item_a = _find_item(persona_a, item_a_id) if persona_a else None
    item_b = _find_item(persona_b, item_b_id) if persona_b else None

    if not (item_a and item_b):
        state.channel.post(
            turn=turn, agent=state.focal_name, action="pass",
            target=None, price=None,
            message=f"[swap accept failed: item lookup error]",
        )
        _run_opponents(state)
        return _state_snapshot(state)

    # Look up each side's ceiling for what they're receiving
    from marketplace.swap_match import items_match_persona_want
    want_a = items_match_persona_want(item_b.get("category"),
                                       persona_a.get("items_to_buy", []) or [])
    want_b = items_match_persona_want(item_a.get("category"),
                                       persona_b.get("items_to_buy", []) or [])

    state.channel.post(
        turn=turn, agent=state.focal_name, action="accept_swap",
        target=body.target_proposal_id, price=None, message=body.message,
    )

    deal = state.ledger.record_deal(
        seller=agent_a, buyer=agent_b,
        item_id=item_a_id, item_name=item_a.get("name", item_a_id),
        price=-1.0,                                    # placeholder — no money
        seller_floor=float(item_a.get("floor_price", 0)),
        buyer_ceiling=float(want_b.get("ceiling_price", 0)) if want_b else 0.0,
        turn=turn,
        deal_type="swap",
        item_b_id=item_b_id,
        item_b_name=item_b.get("name", item_b_id),
        item_b_floor=float(item_b.get("floor_price", 0)),
        item_a_ceiling=float(want_a.get("ceiling_price", 0)) if want_a else 0.0,
    )
    # Fulfill matched wants on both sides so focal_done can fire
    if want_a:
        state.ledger.fulfill_want(want_a.get("want_id"))
    if want_b:
        state.ledger.fulfill_want(want_b.get("want_id"))

    # Phase 2 review rule extended for swap: surplus-based stars
    from marketplace.review_generator import (
        generate_and_apply_deal_reviews, has_review_data,
    )
    if has_review_data(persona_a) or has_review_data(persona_b):
        # For swap reviews we use each side's surplus:
        # seller's surplus = item_a_ceiling - item_a_floor (received - gave)
        # ... but the review_generator's existing rules score by price-in-zone.
        # We approximate by mapping swap surplus to a synthetic price:
        # higher relative surplus → higher synthetic "price" inside [floor,ceiling].
        # This is a pragmatic V1 — review_generator may get a swap-aware branch later.
        synth_price = (deal.seller_floor + deal.item_a_ceiling) / 2 if deal.item_a_ceiling else deal.seller_floor
        synth_floor = deal.seller_floor
        synth_ceiling = max(deal.item_a_ceiling or deal.seller_floor + 1, synth_floor + 1)
        generate_and_apply_deal_reviews(
            deal_id=deal.deal_id,
            seller_persona=persona_a,
            buyer_persona=persona_b,
            price=synth_price,
            seller_floor=synth_floor,
            buyer_ceiling=synth_ceiling,
        )

    _run_opponents(state)
    return _state_snapshot(state)


def _apply_reject_swap(state: MarketplaceState, body: RejectSwapBody) -> dict:
    turn = state.next_turn()
    state.channel.post(
        turn=turn, agent=state.focal_name, action="reject_swap",
        target=body.target_proposal_id, price=None, message=body.message,
    )
    _run_opponents(state)
    return _state_snapshot(state)


def _apply_lookup_agent(state: MarketplaceState, body: LookupAgentBody) -> dict:
    """Phase 2: free, silent reputation lookup. Does NOT advance the turn,
    does NOT broadcast on the channel, does NOT run opponents."""
    if body.role not in ("seller", "buyer"):
        return {"error": f"invalid role '{body.role}', must be 'seller' or 'buyer'"}
    persona = next(
        (p for p in state.personas if p.get("name") == body.name), None
    )
    if persona is None:
        return {"error": f"agent '{body.name}' not found"}
    rating = persona.get(f"{body.role}_rating")
    reviews = list(persona.get(f"{body.role}_reviews", []))
    # Track focal lookups for the review_utilization rubric (best-effort —
    # phase 1 states don't have this attr, so guard).
    if getattr(state, "_focal_lookups", None) is not None:
        state._focal_lookups.append({
            "turn": state._turn,
            "target_agent": body.name,
            "role": body.role,
        })
    return {
        "name": body.name,
        "role": body.role,
        "rating": rating,
        "review_count": len(reviews),
        "reviews": reviews[-5:],  # last 5 most recent
    }


# ---- Settlement tool handlers (only mounted when settlement is on) ----

def _settle_caller(state):
    return state.focal_name

def _apply_list_payment_methods(state, payload):
    return state.settlement.list_methods(payload.get("deal_id"), _settle_caller(state))

def _apply_choose_payment_method(state, payload):
    return state.settlement.choose_method(payload.get("deal_id"), _settle_caller(state),
                                          payload.get("method"))

def _apply_pay(state, payload):
    out = state.settlement.pay(payload.get("deal_id"), _settle_caller(state), payload)
    _run_opponents(state)
    return {**out, **_state_snapshot(state)}

def _apply_submit_otp(state, payload):
    return state.settlement.submit_otp(payload.get("deal_id"), _settle_caller(state),
                                       payload.get("code"))

def _apply_confirm_receipt(state, payload):
    out = state.settlement.confirm_receipt(payload.get("deal_id"), _settle_caller(state))
    _run_opponents(state)
    return {**out, **_state_snapshot(state)}

def _apply_get_payment_status(state, payload):
    return state.settlement.get_status(payload.get("deal_id"), _settle_caller(state))

def _apply_say_in_room(state, payload):
    return state.settlement.say_in_room(payload.get("deal_id"), _settle_caller(state),
                                        payload.get("message"))


# --- Legacy build_app() factory (used by smoke_test + a few legacy tests) ----

def build_app(state: MarketplaceState) -> FastAPI:
    """Legacy factory: a single-state FastAPI app without NeMo Gym lifecycle.

    Used by scripts/smoke_test.py and several tests that pre-date the
    MarketplaceServer lifecycle. New code should use MarketplaceServer.
    """
    app = FastAPI(title="MarketplaceResourcesServer")

    @app.post("/post_listing")
    def post_listing(body: dict):
        return _apply_post_listing_any(state, body)

    @app.post("/make_offer")
    def make_offer(body: MakeOfferBody):
        return _apply_make_offer(state, body)

    @app.post("/counter_offer")
    def counter_offer(body: CounterOfferBody):
        return _apply_counter_offer(state, body)

    @app.post("/accept_offer")
    def accept_offer(body: AcceptOfferBody):
        return _apply_accept_offer(state, body)

    @app.post("/reject_offer")
    def reject_offer(body: RejectOfferBody):
        return _apply_reject_offer(state, body)

    @app.post("/pass")
    def do_pass(body: PassBody):
        return _apply_pass(state, body)

    @app.post("/lookup_agent")
    def lookup_agent(body: LookupAgentBody):
        return _apply_lookup_agent(state, body)

    # Phase 3 swap endpoints
    @app.post("/post_listing_phase3")
    def post_listing_phase3(body: PostListingPhase3Body):
        return _apply_post_listing_phase3(state, body)

    @app.post("/propose_swap")
    def propose_swap(body: ProposeSwapBody):
        return _apply_propose_swap(state, body)

    @app.post("/accept_swap")
    def accept_swap(body: AcceptSwapBody):
        return _apply_accept_swap(state, body)

    @app.post("/reject_swap")
    def reject_swap(body: RejectSwapBody):
        return _apply_reject_swap(state, body)

    @app.post("/verify")
    def verify(body: dict):
        return _verify_for_state(state)

    return app


def _verify_for_state(state: "MarketplaceState") -> dict:
    """Run the verifier stack against an existing MarketplaceState.

    Phase 1 runs 4 rubrics; review_utilization stays None.
    Phase 2 runs 5 rubrics; review_utilization activates and weights shift.
    """
    from resources_server.verifiers import (
        compute_deal_outcomes, compute_capability_asymmetry,
        compute_negotiation_quality, compute_privacy, compute_final_reward,
        compute_review_utilization, compute_swap_quality,
    )
    focal = next(p for p in state.personas if p["name"] == state.focal_name)
    deal = compute_deal_outcomes(focal, state.channel, state.ledger,
                                  all_personas=state.personas)
    cap = compute_capability_asymmetry(focal, state.channel, state.ledger,
                                        judge_model=state.judge_model)
    neg = compute_negotiation_quality(focal, state.channel, state.ledger)
    priv = compute_privacy(focal, state.channel, judge_model=state.judge_model)

    if state.phase >= 2:
        rev = compute_review_utilization(
            focal=focal,
            channel=state.channel,
            personas=state.personas,
            focal_lookups=state._focal_lookups,
        )
    else:
        rev = None

    if state.phase >= 3:
        swap_q = compute_swap_quality(focal=focal, ledger=state.ledger)
    else:
        swap_q = None

    final = compute_final_reward({
        "deal_outcomes": deal["combined"],
        "capability_asymmetry": cap["combined"],
        "negotiation_quality": neg["combined"],
        "privacy": priv["combined"],
        "review_utilization": rev["combined"] if rev else None,
        "swap_quality": swap_q["combined"] if swap_q else None,
    }, phase=state.phase)
    # Serialize channel events + deals + personas so the archiver has structured
    # data to write per-run files. These also end up in rollout.json so they're
    # always recoverable.
    channel_events = [
        {
            "event_id": e.event_id,
            "turn": e.turn,
            "agent": e.agent,
            "action": e.action,
            "target": e.target,
            "price": e.price,
            "message": e.message,
        }
        for e in state.channel.events
    ]
    deals = [
        {
            "deal_id": d.deal_id,
            "turn": d.turn,
            "seller": d.seller,
            "buyer": d.buyer,
            "item_id": d.item_id,
            "price": d.price,
            "seller_floor": getattr(d, "seller_floor", None),
            "buyer_ceiling": getattr(d, "buyer_ceiling", None),
            "payment_status": getattr(d, "payment_status", "n/a"),
        }
        for d in state.ledger.deals
    ]

    return {
        "reward": final,
        "rubric_scores": {
            "deal_outcomes": deal,
            "capability_asymmetry": cap,
            "negotiation_quality": neg,
            "privacy": priv,
            "review_utilization": rev,
            "swap_quality": swap_q,
            "final_reward": final,
        },
        # Structured marketplace artifacts for archive_run.py to extract
        "channel_events": channel_events,
        "deals": deals,
        "personas": state.personas,
    }


# ---- NeMo Gym integration -------------------------------------------

from nemo_gym.base_resources_server import (
    BaseSeedSessionRequest,
    BaseSeedSessionResponse,
    SimpleResourcesServer,
)


class MarketplaceMetadata(BaseModel):
    """Per-task metadata injected by simple_agent via /seed_session and
    carried through /verify so reward computation has full context."""
    model_config = ConfigDict(extra="allow")
    task_id: Optional[str] = None
    phase: Optional[int] = None
    approach: Optional[int] = None
    config_name: Optional[str] = None
    set_id: Optional[str] = None
    focal_persona: Optional[str] = None
    seed: Optional[int] = None
    personas_path: Optional[str] = None


class MarketplaceSeedSessionRequest(BaseSeedSessionRequest):
    model_config = ConfigDict(extra="allow")
    metadata: MarketplaceMetadata


class MarketplaceServer(SimpleResourcesServer):  # type: ignore[misc]
    """NeMo Gym Resources Server for Approach 1's 6-tool marketplace.

    Inherits /seed_session, /verify, /aggregate_metrics, and session middleware
    from SimpleResourcesServer, then registers the 6 tool endpoints.

    State is scoped per rollout by request.session["session_id"], populated
    by FastAPI session middleware. /seed_session creates the MarketplaceState;
    tool endpoints look it up; /verify scores it and frees it.

    A `_default_state` slot supports legacy callers (tests, smoke script)
    that use attach_state() before any seed_session call.
    """

    JUDGE_MODEL: ClassVar[str] = "openai/gpt-4o-2024-11-20"

    # Allow MarketplaceServer() construction in tests without requiring the
    # full NeMo Gym BaseResourcesServerConfig + ServerClient (NeMo Gym only
    # supplies those when ng_run boots the server).
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, **data):
        if "config" not in data:
            data["config"] = None
        if "server_client" not in data:
            data["server_client"] = None
        try:
            super().__init__(**data)
        except Exception:
            # Fall back to BaseModel.__init__ bypass for test-only instantiation.
            object.__setattr__(self, "__dict__", {**data})
        # Per-session state. Keys are session_id strings.
        object.__setattr__(self, "_sessions", {})

    # ----- SimpleResourcesServer overrides ---------------------------

    def get_session_middleware_key(self) -> str:  # type: ignore[override]
        """Provide a stable middleware key when config is None (test path).

        SimpleResourcesServer's default builds a key from `self.config.name`;
        in tests we instantiate MarketplaceServer() with no config, so fall
        back to a constant key.
        """
        cfg = getattr(self, "config", None)
        if cfg is None or getattr(cfg, "name", None) is None:
            return f"{self.__class__.__name__}___test"
        return f"{self.__class__.__name__}___{cfg.name}"

    # ----- Compatibility: attach_state() ------------------------------

    def attach_state(self, state: "MarketplaceState") -> None:
        """Register state under a default key.

        Legacy entrypoint for tests/smoke that call tool endpoints without
        first POSTing /seed_session. Tool endpoints fall back to this key
        if no per-request session_id state exists.
        """
        self._sessions[_DEFAULT_SESSION_KEY] = state

    # ----- State lookup -----------------------------------------------

    def _get_state_for_request(self, request: Request) -> MarketplaceState:
        # Prefer the session-keyed state; fall back to default for legacy callers.
        session_id = None
        try:
            session_id = request.session.get("session_id")
        except (AssertionError, AttributeError):
            # No SessionMiddleware installed (shouldn't happen post-fix, but
            # guard so legacy build_app/TestClient flows don't blow up).
            session_id = None

        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        if _DEFAULT_SESSION_KEY in self._sessions:
            return self._sessions[_DEFAULT_SESSION_KEY]
        raise RuntimeError(
            "No MarketplaceState available for this request. Call "
            "/seed_session first, or use attach_state() in tests."
        )

    # ----- Webserver setup --------------------------------------------

    def setup_webserver(self) -> FastAPI:  # type: ignore[override]
        # Inherit /seed_session, /verify, /aggregate_metrics + session middleware.
        app = super().setup_webserver()

        # Register tool endpoints.
        app.post("/post_listing")(self.post_listing)
        app.post("/make_offer")(self.make_offer)
        app.post("/counter_offer")(self.counter_offer)
        app.post("/accept_offer")(self.accept_offer)
        app.post("/reject_offer")(self.reject_offer)
        app.post("/pass")(self.do_pass)  # `pass` is a reserved keyword.
        app.post("/lookup_agent")(self.lookup_agent)
        # Phase 3 swap endpoints
        app.post("/propose_swap")(self.propose_swap)
        app.post("/accept_swap")(self.accept_swap)
        app.post("/reject_swap")(self.reject_swap)
        from marketplace import config as mp_config
        if mp_config.ENABLE_SETTLEMENT:
            app.post("/list_payment_methods")(self.list_payment_methods)
            app.post("/choose_payment_method")(self.choose_payment_method)
            app.post("/pay")(self.pay)
            app.post("/submit_otp")(self.submit_otp)
            app.post("/confirm_receipt")(self.confirm_receipt)
            app.post("/get_payment_status")(self.get_payment_status)
            app.post("/say_in_room")(self.say_in_room)

        @app.get("/healthz")
        def healthz():
            return {"ok": True}

        return app

    # ----- /seed_session ----------------------------------------------

    async def seed_session(
        self, body: MarketplaceSeedSessionRequest, request: Request
    ) -> BaseSeedSessionResponse:  # type: ignore[override]
        session_id = request.session["session_id"]
        meta = body.metadata

        # Load personas.
        if not meta.personas_path:
            raise RuntimeError(
                "seed_session: metadata.personas_path is required to bootstrap "
                "a MarketplaceState."
            )
        with open(meta.personas_path) as f:
            personas = json.load(f)

        # Look up models from the config dispatcher.
        from resources_server.model_config import get_model_config
        cfg_name = meta.config_name or "focal_S_vs_S"
        cfg = get_model_config(cfg_name)
        focal_model = cfg["focal_model"]
        opponents_model = cfg["opponents_model"]

        # Reproducible shuffles for any persona-randomized code paths.
        if meta.seed is not None:
            random.seed(meta.seed)

        # Pick a per-session data dir under data/ng_run/<session_id>.
        from marketplace import config as mp_config
        data_dir = mp_config.DATA_DIR / "ng_run" / session_id

        state = MarketplaceState(
            focal_name=meta.focal_persona,
            personas=personas,
            opponents_model=opponents_model,
            focal_model=focal_model,
            judge_model=self.JUDGE_MODEL,
            seed=meta.seed or 0,
            set_id=meta.set_id or "",
            config_name=cfg_name,
            data_dir=data_dir,
            phase=int(meta.phase or 1),
        )
        self._sessions[session_id] = state
        return BaseSeedSessionResponse()

    # ----- /verify ----------------------------------------------------

    async def verify(self, body=None, request: Request = None) -> dict:  # type: ignore[override]
        """Score the rubric stack against the per-session MarketplaceState.

        Accepts either:
          - a FastAPI Request (when called via HTTP through the inherited
            /verify route) and a body containing the run result, or
          - just a body (legacy in-process callers like the old tests).

        Returns the same {reward, rubric_scores} dict the legacy /verify
        used to return so downstream archive/analysis code is unchanged.

        When called via HTTP, the response is augmented with the request
        body (responses_create_params, response) so SimpleAgentVerifyResponse
        validates.
        """
        # Read raw JSON body from the HTTP request — FastAPI doesn't bind
        # the `body` param without a Pydantic type annotation.
        http_body_dict: dict | None = None
        if request is not None:
            try:
                http_body_dict = await request.json()
            except Exception:
                http_body_dict = None

        state = None
        # HTTP path: pull session-scoped state.
        if request is not None:
            try:
                state = self._get_state_for_request(request)
            except RuntimeError:
                state = None
        # Legacy path: attach_state() set a default.
        if state is None:
            state = self._sessions.get(_DEFAULT_SESSION_KEY)
        if state is None:
            raise RuntimeError(
                "MarketplaceServer.verify() called with no MarketplaceState; "
                "POST /seed_session or call attach_state() first."
            )

        result = _verify_for_state(state)

        # Clean up per-session state once scored (but keep _default_ around
        # for legacy callers that may verify multiple times).
        if request is not None:
            try:
                session_id = request.session.get("session_id")
                if session_id and session_id in self._sessions:
                    del self._sessions[session_id]
            except (AssertionError, AttributeError):
                pass

        # When called via HTTP, echo back the request body so the response
        # conforms to BaseVerifyResponse (which requires responses_create_params
        # and response from the BaseVerifyRequest it inherits from).
        # When called in-process (legacy tests), just return the raw result dict.
        if request is not None and http_body_dict is not None:
            return {**http_body_dict, **result}

        return result

    # ----- Tool endpoints ---------------------------------------------

    async def post_listing(
        self, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        return _apply_post_listing_any(state, payload)

    async def make_offer(
        self, body: MakeOfferBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_make_offer(state, body)

    async def counter_offer(
        self, body: CounterOfferBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_counter_offer(state, body)

    async def accept_offer(
        self, body: AcceptOfferBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_accept_offer(state, body)

    async def reject_offer(
        self, body: RejectOfferBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_reject_offer(state, body)

    async def do_pass(
        self, body: PassBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_pass(state, body)

    async def lookup_agent(
        self, body: LookupAgentBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_lookup_agent(state, body)

    async def propose_swap(
        self, body: ProposeSwapBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_propose_swap(state, body)

    async def accept_swap(
        self, body: AcceptSwapBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_accept_swap(state, body)

    async def reject_swap(
        self, body: RejectSwapBody, request: Request
    ) -> dict:
        state = self._get_state_for_request(request)
        return _apply_reject_swap(state, body)

    async def _settle_payload(self, request):
        state = self._get_state_for_request(request)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        return state, payload

    async def list_payment_methods(self, request: Request) -> dict:
        state, p = await self._settle_payload(request); return _apply_list_payment_methods(state, p)
    async def choose_payment_method(self, request: Request) -> dict:
        state, p = await self._settle_payload(request); return _apply_choose_payment_method(state, p)
    async def pay(self, request: Request) -> dict:
        state, p = await self._settle_payload(request); return _apply_pay(state, p)
    async def submit_otp(self, request: Request) -> dict:
        state, p = await self._settle_payload(request); return _apply_submit_otp(state, p)
    async def confirm_receipt(self, request: Request) -> dict:
        state, p = await self._settle_payload(request); return _apply_confirm_receipt(state, p)
    async def get_payment_status(self, request: Request) -> dict:
        state, p = await self._settle_payload(request); return _apply_get_payment_status(state, p)
    async def say_in_room(self, request: Request) -> dict:
        state, p = await self._settle_payload(request); return _apply_say_in_room(state, p)
