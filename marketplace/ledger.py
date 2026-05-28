"""
The deal ledger.

Tracks which items have been sold and records the final list of deals.
This is the equivalent of Project Deal's "settlement" — once a deal is
sealed it goes here and the item is marked unavailable.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from . import config


@dataclass
class Deal:
    """One closed deal.

    Phase 1/2 (money trades):
        seller, buyer, item_id, item_name, price, seller_floor, buyer_ceiling.
    Phase 3 (swap trades):
        deal_type='swap'; agent_a sold item_id to agent_b in exchange for
        item_b_id. Money-side fields (price, ceilings) carry the agents'
        PRIVATE valuations so the verifier can compute swap surplus.
    """
    deal_id: str
    seller: str
    buyer: str
    item_id: str            # phase 1/2: seller's item_id; phase 3: agent_a's item
    item_name: str          # human-readable
    price: float            # phase 1/2: deal price; phase 3: -1.0 placeholder (no money)
    seller_floor: float     # seller/agent_a's private valuation of their item
    buyer_ceiling: float    # buyer/agent_b's private ceiling for the matched want
    turn: int
    # Phase 3 swap-specific fields (None in phase 1/2)
    deal_type: str = "money"           # "money" | "swap"
    item_b_id: str | None = None       # agent_b's item given in trade
    item_b_name: str | None = None
    item_b_floor: float | None = None  # agent_b's private valuation of their item
    item_a_ceiling: float | None = None  # agent_a's private ceiling for item_b's category
    payment_status: str = "n/a"   # "n/a" | "pending" | "confirmed" | "cancelled"


class Ledger:
    def __init__(self, path: Path = config.DEALS_PATH):
        self.path = path
        self.deals: list[Deal] = []
        self.sold_item_ids: set[str] = set()       # seller item_ids only
        self.fulfilled_want_ids: set[str] = set()  # buyer want_ids only
        self._next_deal_num = 1

    def clear(self):
        self.deals = []
        self.sold_item_ids = set()
        self.fulfilled_want_ids = set()
        self._next_deal_num = 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._save()

    def record_deal(
        self,
        seller: str,
        buyer: str,
        item_id: str,
        item_name: str,
        price: float,
        seller_floor: float,
        buyer_ceiling: float,
        turn: int,
        deal_type: str = "money",
        item_b_id: str | None = None,
        item_b_name: str | None = None,
        item_b_floor: float | None = None,
        item_a_ceiling: float | None = None,
        pending: bool = False,
    ) -> Deal:
        status = "pending" if pending else "n/a"
        deal = Deal(
            deal_id=f"deal_{self._next_deal_num:03d}",
            seller=seller,
            buyer=buyer,
            item_id=item_id,
            item_name=item_name,
            price=price,
            seller_floor=seller_floor,
            buyer_ceiling=buyer_ceiling,
            turn=turn,
            deal_type=deal_type,
            item_b_id=item_b_id,
            item_b_name=item_b_name,
            item_b_floor=item_b_floor,
            item_a_ceiling=item_a_ceiling,
            payment_status=status,
        )
        self._next_deal_num += 1
        self.deals.append(deal)
        if not pending:
            self.sold_item_ids.add(item_id)
            # In a swap, both items become "sold" (unavailable for further trades).
            if deal_type == "swap" and item_b_id:
                self.sold_item_ids.add(item_b_id)
        self._save()
        return deal

    def is_sold(self, item_id: str) -> bool:
        return item_id in self.sold_item_ids

    def is_want_fulfilled(self, want_id: str) -> bool:
        return want_id in self.fulfilled_want_ids

    def fulfill_want(self, want_id: str):
        self.fulfilled_want_ids.add(want_id)
        self._save()

    def confirm_deal(self, deal_id: str) -> bool:
        """Mark a pending deal as confirmed and mark item as sold."""
        for deal in self.deals:
            if deal.deal_id == deal_id:
                deal.payment_status = "confirmed"
                self.sold_item_ids.add(deal.item_id)
                if deal.deal_type == "swap" and deal.item_b_id:
                    self.sold_item_ids.add(deal.item_b_id)
                self._save()
                return True
        return False

    def cancel_deal(self, deal_id: str) -> bool:
        """Cancel a pending deal — item stays available."""
        for deal in self.deals:
            if deal.deal_id == deal_id:
                deal.payment_status = "cancelled"
                self.sold_item_ids.discard(deal.item_id)
                self._save()
                return True
        return False

    def pending_deals_for_buyer(self, buyer_name: str) -> list:
        """Return all deals with status='pending' where buyer_name is the buyer."""
        return [
            d for d in self.deals
            if d.buyer == buyer_name and d.payment_status == "pending"
        ]

    def _save(self):
        data = {
            "deals": [asdict(d) for d in self.deals],
            "fulfilled_want_ids": list(self.fulfilled_want_ids),
        }
        self.path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = config.DEALS_PATH) -> "Ledger":
        l = cls(path)
        if path.exists():
            raw = json.loads(path.read_text())
            if isinstance(raw, list):
                # backward compat: old format was a plain list of deals
                l.deals = [Deal(**d) for d in raw]
                l.sold_item_ids = {d.item_id for d in l.deals}
            else:
                l.deals = [Deal(**d) for d in raw.get("deals", [])]
                l.sold_item_ids = {d.item_id for d in l.deals}
                l.fulfilled_want_ids = set(raw.get("fulfilled_want_ids", []))
            l._next_deal_num = len(l.deals) + 1
        return l
