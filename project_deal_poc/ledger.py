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
    """One closed deal."""
    deal_id: str
    seller: str
    buyer: str
    item_id: str            # the seller's item_id
    item_name: str          # human-readable
    price: float
    seller_floor: float     # the seller's floor at time of deal (for analysis)
    buyer_ceiling: float    # the specific matched want's ceiling (for analysis)
    turn: int


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
    ) -> Deal:
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
        )
        self._next_deal_num += 1
        self.deals.append(deal)
        self.sold_item_ids.add(item_id)
        self._save()
        return deal

    def is_sold(self, item_id: str) -> bool:
        return item_id in self.sold_item_ids

    def is_want_fulfilled(self, want_id: str) -> bool:
        return want_id in self.fulfilled_want_ids

    def fulfill_want(self, want_id: str):
        self.fulfilled_want_ids.add(want_id)
        self._save()

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
