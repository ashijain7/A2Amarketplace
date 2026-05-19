import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.ledger import Ledger


def test_unbought_uses_want_fulfilled_not_is_sold():
    """Unfulfilled wants should be detected with is_want_fulfilled, not is_sold."""
    ledger = Ledger.__new__(Ledger)
    ledger.deals = []
    ledger.sold_item_ids = set()
    ledger.fulfilled_want_ids = {"headphones_w1"}
    ledger._next_deal_num = 1
    ledger.path = Path("/tmp/test_deals.json")

    persona = {
        "name": "Dexter",
        "items_to_buy": [
            {"want_id": "headphones_w1", "description": "Headphones", "ceiling_price": 50},
            {"want_id": "books_w1", "description": "Books", "ceiling_price": 15},
        ]
    }

    unbought = [
        w for w in persona.get("items_to_buy", [])
        if not ledger.is_want_fulfilled(w["want_id"])
    ]

    want_ids = [w["want_id"] for w in unbought]
    assert "headphones_w1" not in want_ids, "fulfilled want should not appear as unbought"
    assert "books_w1" in want_ids, "unfulfilled want should appear as unbought"


def test_analyze_bug_is_sold_wrong_for_wants():
    """Demonstrates the bug: is_sold returns False for want IDs, making everything look unfulfilled."""
    ledger = Ledger.__new__(Ledger)
    ledger.deals = []
    ledger.sold_item_ids = set()
    ledger.fulfilled_want_ids = {"headphones_w1"}
    ledger._next_deal_num = 1
    ledger.path = Path("/tmp/test_deals.json")

    assert ledger.is_sold("headphones_w1") is False      # confirms the bug exists
    assert ledger.is_want_fulfilled("headphones_w1") is True  # correct answer
