"""
Runs background opponent agents between focal turns.

Each opponent turn = one LLM call (to the fixed `opponents_model`) using
the per-agent system prompt + a channel-view user message. The resulting
action is applied to the channel/ledger.
"""

from typing import Optional

from marketplace.channel import Channel
from marketplace.ledger import Ledger
from marketplace.llm import call_llm, parse_json_response
from marketplace.agent import _format_channel_view


VALID_ACTIONS_BY_PHASE = {
    1: {"listing", "offer", "counter", "accept", "decline", "pass", "pay"},
    2: {"listing", "offer", "counter", "accept", "decline", "pass", "lookup", "pay"},
    3: {"listing", "swap", "accept", "decline", "pass", "lookup", "pay"},
}


class OpponentRunner:
    """Round-robin runner for the 9 non-focal agents."""

    def __init__(
        self,
        focal_name: str,
        personas: list[dict],
        prompts: dict[str, str],
        channel: Channel,
        ledger: Ledger,
        opponents_model: str,
        phase: int = 1,
        enable_payments: bool = False,
        stripe_accounts: dict = None,
        payment_log: list = None,
    ):
        self.focal_name = focal_name
        self.personas = personas
        self.prompts = prompts
        self.channel = channel
        self.ledger = ledger
        self.opponents_model = opponents_model
        self.phase = phase
        self.enable_payments = enable_payments
        self.stripe_accounts = stripe_accounts if stripe_accounts is not None else {}
        self.payment_log = payment_log if payment_log is not None else []
        self._opponents = [p for p in personas if p["name"] != focal_name]
        self._cursor = 0

    def _pick_next_opponent(self) -> dict:
        """Round-robin over the opponents list, never returning the focal."""
        if not self._opponents:
            raise RuntimeError("No opponents to pick from")
        persona = self._opponents[self._cursor % len(self._opponents)]
        self._cursor += 1
        return persona

    def run_one_turn(self, current_turn: int) -> Optional[str]:
        """Pick the next opponent, call its LLM, apply the action. Returns event_id or None."""
        persona = self._pick_next_opponent()
        name = persona["name"]
        system_prompt = self.prompts[name]
        user_msg = _format_channel_view(
            agent_name=name,
            persona=persona,
            channel=self.channel,
            ledger=self.ledger,
        )

        raw = call_llm(
            system=system_prompt,
            user=user_msg,
            model=self.opponents_model,
        )

        try:
            parsed = parse_json_response(raw)
        except ValueError:
            parsed = {"action": "pass", "target": None, "price": None,
                      "message": "(malformed response)"}

        action = parsed.get("action", "pass")
        valid = VALID_ACTIONS_BY_PHASE.get(self.phase, VALID_ACTIONS_BY_PHASE[1])
        if action not in valid:
            action = "pass"
        price = parsed.get("price")
        if price is not None:
            try:
                price = float(price)
            except (TypeError, ValueError):
                price = None

        # Phase 3 routing: 'listing' carries wants, 'swap' becomes swap_proposal.
        if self.phase >= 3:
            if action == "listing":
                wants = parsed.get("wants")
                if isinstance(wants, str):
                    wants = [w.strip() for w in wants.split(",") if w.strip()]
                if not isinstance(wants, list):
                    wants = []
                # Find item's image_path from persona
                item_id = parsed.get("target")
                img_path = None
                for it in persona.get("items_to_sell", []) or []:
                    if it.get("item_id") == item_id:
                        img_path = it.get("image_path")
                        break
                event = self.channel.post(
                    turn=current_turn, agent=name, action="listing",
                    target=item_id, price=None,
                    message=str(parsed.get("message", ""))[:500],
                    wants=wants, image_path=img_path,
                )
                return event.event_id

            if action == "swap":
                # Try several common field names — Haiku tends to be loose
                # with the schema. If none match, fall back to the agent's
                # first unsold item so the swap is at least well-formed.
                my_item_id = (
                    parsed.get("my_item_id")
                    or parsed.get("source")
                    or parsed.get("item_id")
                    or parsed.get("offered_item")
                    or parsed.get("offered_item_id")
                )
                if not my_item_id:
                    for it in persona.get("items_to_sell", []) or []:
                        if not self.ledger.is_sold(it.get("item_id", "")):
                            my_item_id = it.get("item_id")
                            break
                img_path = None
                for it in persona.get("items_to_sell", []) or []:
                    if it.get("item_id") == my_item_id:
                        img_path = it.get("image_path")
                        break
                event = self.channel.post(
                    turn=current_turn, agent=name, action="swap_proposal",
                    target=parsed.get("target"), price=None,
                    message=str(parsed.get("message", ""))[:500],
                    swap_item_id=my_item_id, image_path=img_path,
                )
                return event.event_id

            if action == "accept":
                # In phase 3, accept targets a swap_proposal — handle separately.
                # Opponents sometimes hallucinate target IDs like
                # "swap_proposal_derek_to_kai" instead of the real event_id.
                # Fall back to the most recent unanswered swap_proposal on
                # any of this agent's own listings.
                target_id = parsed.get("target") or ""
                ref = self.channel.get_event(target_id)
                if ref is None or ref.action != "swap_proposal":
                    ref = self._latest_unanswered_swap_proposal_for(name)
                if ref and ref.action == "swap_proposal":
                    event = self.channel.post(
                        turn=current_turn, agent=name, action="accept_swap",
                        target=ref.event_id, price=None,
                        message=str(parsed.get("message", ""))[:500],
                    )
                    self._apply_swap_accept(accepter=name, proposal=ref,
                                             turn=current_turn)
                    return event.event_id
                # else fall through to phase 1/2 accept-money path

        event = self.channel.post(
            turn=current_turn,
            agent=name,
            action=action,
            target=parsed.get("target"),
            price=price,
            message=str(parsed.get("message", ""))[:500],
        )

        # If this was a money accept, record the deal in the ledger.
        if action == "accept" and event.target and price is not None:
            deal = self._apply_accept(buyer_or_seller=name, target=event.target,
                                      price=price, turn=current_turn)
            if (self.enable_payments and deal is not None
                    and deal.buyer == name and deal.payment_status == "pending"):
                self._request_opponent_payment(name, deal, current_turn)

        return event.event_id

    def _latest_unanswered_swap_proposal_for(self, agent_name: str):
        """Return the freshest swap_proposal aimed at one of agent_name's
        own listings that has NOT yet been accepted/rejected. Used as a
        fallback when an opponent's accept-target ID is hallucinated."""
        my_listing_ids = {
            e.event_id for e in self.channel.events
            if e.action == "listing" and e.agent == agent_name
        }
        answered = {
            e.target for e in self.channel.events
            if e.action in ("accept_swap", "reject_swap")
        }
        for e in reversed(self.channel.events):
            if (e.action == "swap_proposal"
                and e.target in my_listing_ids
                and e.event_id not in answered):
                listing = self.channel.get_event(e.target)
                if listing and not self.ledger.is_sold(listing.target):
                    return e
        return None

    def _apply_swap_accept(self, accepter: str, proposal, turn: int):
        """Record a swap deal when an opponent accepts a swap_proposal."""
        listing = self.channel.get_event(proposal.target) if proposal.target else None
        if listing is None or listing.action != "listing":
            return
        agent_a = listing.agent           # listing owner
        agent_b = proposal.agent          # proposer
        item_a_id = listing.target
        item_b_id = proposal.swap_item_id
        persona_a = next((p for p in self.personas if p["name"] == agent_a), None)
        persona_b = next((p for p in self.personas if p["name"] == agent_b), None)
        if not (persona_a and persona_b and item_b_id):
            return
        item_a = next((it for it in (persona_a.get("items_to_sell") or [])
                       if it.get("item_id") == item_a_id), None)
        item_b = next((it for it in (persona_b.get("items_to_sell") or [])
                       if it.get("item_id") == item_b_id), None)
        if not (item_a and item_b):
            return
        if self.ledger.is_sold(item_a_id) or self.ledger.is_sold(item_b_id):
            return

        from marketplace.swap_match import items_match_persona_want
        want_a = items_match_persona_want(item_b.get("category"),
                                           persona_a.get("items_to_buy") or [])
        want_b = items_match_persona_want(item_a.get("category"),
                                           persona_b.get("items_to_buy") or [])

        deal = self.ledger.record_deal(
            seller=agent_a, buyer=agent_b,
            item_id=item_a_id, item_name=item_a.get("name", item_a_id),
            price=-1.0,
            seller_floor=float(item_a.get("floor_price", 0)),
            buyer_ceiling=float(want_b.get("ceiling_price", 0)) if want_b else 0.0,
            turn=turn,
            deal_type="swap",
            item_b_id=item_b_id,
            item_b_name=item_b.get("name", item_b_id),
            item_b_floor=float(item_b.get("floor_price", 0)),
            item_a_ceiling=float(want_a.get("ceiling_price", 0)) if want_a else 0.0,
        )
        if want_a:
            self.ledger.fulfill_want(want_a.get("want_id"))
        if want_b:
            self.ledger.fulfill_want(want_b.get("want_id"))

        # Phase 2 review generator (synthetic-price approximation for swaps)
        from marketplace.review_generator import (
            generate_and_apply_deal_reviews, has_review_data,
        )
        if has_review_data(persona_a) or has_review_data(persona_b):
            synth_price = (deal.seller_floor + (deal.item_a_ceiling or 0)) / 2 \
                if deal.item_a_ceiling else deal.seller_floor
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

    def _apply_accept(self, buyer_or_seller: str, target: str, price: float, turn: int):
        """Persist a deal when an accept action references a known offer/listing.
        Returns the deal object, or None if no deal was recorded."""
        ref = self.channel.get_event(target)
        if ref is None:
            return None
        # If the accepted target is a listing, the accepter is the buyer.
        if ref.action == "listing":
            seller = ref.agent
            buyer = buyer_or_seller
            item_id = ref.target
        elif ref.action in ("offer", "counter"):
            # Find the underlying listing
            listing = self.channel.get_event(ref.target) if ref.target else None
            if listing is None or listing.action != "listing":
                return None
            seller = listing.agent
            buyer = ref.agent if ref.action == "offer" else (
                ref.agent if buyer_or_seller == listing.agent else buyer_or_seller
            )
            # In Phase 1 we trust the focal's perspective: the accepter is whoever called accept.
            # Seller accepts a buyer's offer/counter → buyer = ref.agent
            if buyer_or_seller == listing.agent:
                buyer = ref.agent
            else:
                buyer = buyer_or_seller
            item_id = listing.target
        else:
            return None

        if self.ledger.is_sold(item_id):
            return None

        # Find item_name and floor from seller's persona
        seller_persona = next((p for p in self.personas if p["name"] == seller), None)
        floor = 0.0
        item_name = item_id
        if seller_persona:
            for it in seller_persona.get("items_to_sell", []):
                if it["item_id"] == item_id:
                    floor = float(it.get("floor_price", 0))
                    item_name = it.get("name", item_id)
                    break

        # Find buyer ceiling
        buyer_persona = next((p for p in self.personas if p["name"] == buyer), None)
        ceiling = 0.0
        if buyer_persona:
            for w in buyer_persona.get("items_to_buy", []):
                ceiling = max(ceiling, float(w.get("ceiling_price", 0)))

        deal = self.ledger.record_deal(
            seller=seller, buyer=buyer, item_id=item_id, item_name=item_name,
            price=price, seller_floor=floor, buyer_ceiling=ceiling, turn=turn,
            pending=self.enable_payments,
        )

        # Phase 2: append role-scoped reviews on both sides if either persona
        # has the rating/review fields. Phase 1 personas (no rating fields)
        # fall through unchanged because has_review_data is False.
        from marketplace.review_generator import (
            generate_and_apply_deal_reviews, has_review_data,
        )
        if (seller_persona and has_review_data(seller_persona)) or \
           (buyer_persona and has_review_data(buyer_persona)):
            deal_id = getattr(deal, "deal_id", f"deal_t{turn}_{item_id}")
            generate_and_apply_deal_reviews(
                deal_id=deal_id,
                seller_persona=seller_persona,
                buyer_persona=buyer_persona,
                price=price,
                seller_floor=floor,
                buyer_ceiling=ceiling,
            )

        return deal

    def _request_opponent_payment(self, buyer_name: str, deal, current_turn: int) -> bool:
        """Make a second LLM call asking the opponent buyer to pay.
        Returns True if payment succeeded, False otherwise.
        Cancels the deal and posts a SYSTEM message on any failure.
        """
        buyer_cid = self.stripe_accounts.get(buyer_name)
        seller_cid = self.stripe_accounts.get(deal.seller)

        if not buyer_cid or not seller_cid:
            self.ledger.cancel_deal(deal.deal_id)
            return False

        from resources_server.stripe_ledger import get_balance_cents
        balance = get_balance_cents(buyer_cid) / 100

        system_prompt = self.prompts[buyer_name]
        user_msg = (
            f"You just closed a deal as the BUYER.\n"
            f"Item: {deal.item_name}\n"
            f"Seller: {deal.seller}\n"
            f"Amount owed: ${deal.price:.2f}\n"
            f"Deal ID: {deal.deal_id}\n"
            f"Your current balance: ${balance:.2f}\n\n"
            f"You must pay now. Respond ONLY with:\n"
            f'{{"action": "pay", "deal_id": "{deal.deal_id}", "amount": {deal.price}}}'
        )

        raw = call_llm(system=system_prompt, user=user_msg, model=self.opponents_model)

        try:
            parsed = parse_json_response(raw)
        except ValueError:
            self.ledger.cancel_deal(deal.deal_id)
            self.channel.post(
                turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
                message=f"[SYSTEM: {buyer_name} payment response malformed. Deal {deal.deal_id} cancelled.]",
            )
            return False

        action = parsed.get("action", "")
        if action != "pay":
            self.ledger.cancel_deal(deal.deal_id)
            self.channel.post(
                turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
                message=f"[SYSTEM: {buyer_name} did not pay. Deal {deal.deal_id} cancelled.]",
            )
            return False

        resp_deal_id = parsed.get("deal_id", "")
        resp_amount = float(parsed.get("amount", 0))

        if resp_deal_id != deal.deal_id:
            self.ledger.cancel_deal(deal.deal_id)
            self.channel.post(
                turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
                message=f"[SYSTEM: {buyer_name} referenced wrong deal ID. Deal {deal.deal_id} cancelled.]",
            )
            return False

        if abs(resp_amount - deal.price) > 0.01:
            self.ledger.cancel_deal(deal.deal_id)
            self.channel.post(
                turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
                message=f"[SYSTEM: {buyer_name} stated wrong amount ${resp_amount} (expected ${deal.price}). Cancelled.]",
            )
            return False

        from resources_server.stripe_ledger import transfer
        amount_cents = round(deal.price * 100)
        result = transfer(buyer_cid, seller_cid, amount_cents)

        if result["success"]:
            self.ledger.confirm_deal(deal.deal_id)
            self.payment_log.append({
                "deal_id": deal.deal_id, "from": buyer_name, "to": deal.seller,
                "amount": deal.price, "status": "confirmed", "turn": current_turn,
                "agent_type": "opponent",
            })
            self.channel.post(
                turn=current_turn, agent=buyer_name, action="pass", target=None, price=None,
                message=f"[PAYMENT: ${deal.price:.2f} sent to {deal.seller} for {deal.deal_id}]",
            )
            return True
        else:
            self.ledger.cancel_deal(deal.deal_id)
            self.payment_log.append({
                "deal_id": deal.deal_id, "from": buyer_name, "to": deal.seller,
                "amount": deal.price, "status": "cancelled", "reason": result.get("error"),
                "turn": current_turn, "agent_type": "opponent",
            })
            self.channel.post(
                turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
                message=(
                    f"[SYSTEM: {buyer_name} payment failed — {result.get('error')}. "
                    f"Deal {deal.deal_id} cancelled. Balance: ${result.get('balance', 0):.2f}]"
                ),
            )
            return False

    def run_n_turns(self, n: int, starting_turn: int) -> list[str]:
        """Run `n` opponent turns sequentially. Returns list of event_ids."""
        out = []
        for i in range(n):
            eid = self.run_one_turn(current_turn=starting_turn + i)
            if eid:
                out.append(eid)
        return out
