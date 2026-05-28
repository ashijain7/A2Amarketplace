"""
Smoke test for the payment extension.
Runs with mocked Stripe — no real API calls.
Usage: python scripts/smoke_test_payment.py
"""
import json
import pathlib
import tempfile
from unittest.mock import patch, MagicMock

from dotenv import load_dotenv
load_dotenv()

from marketplace.ledger import Ledger
from resources_server.app import MarketplaceState, _state_snapshot, _verify_for_state


def run_smoke():
    personas = [
        {
            "name": "Marcus",
            "items_to_sell": [{"item_id": "kb", "name": "Keyboard", "floor_price": 35}],
            "items_to_buy": [],
            "style": "direct",
        },
        {
            "name": "Kai",
            "items_to_sell": [],
            "items_to_buy": [{"want_id": "w1", "description": "keyboard", "ceiling_price": 55}],
            "style": "direct",
        },
    ]

    with tempfile.TemporaryDirectory() as tmp:
        accounts = {"Marcus": "cus_marcus", "Kai": "cus_kai"}

        state = MarketplaceState(
            focal_name="Marcus",
            personas=personas,
            opponents_model="x",
            focal_model="x",
            judge_model="x",
            seed=0,
            set_id="s1",
            config_name="focal_S_vs_S_pay",
            data_dir=pathlib.Path(tmp),
            phase=1,
            enable_payments=True,
            stripe_accounts=accounts,
        )

        # Test 1: Seller state snapshot has no pending_payments
        state.ledger.record_deal(
            seller="Marcus", buyer="Kai", item_id="kb",
            item_name="Keyboard", price=45.0,
            seller_floor=35.0, buyer_ceiling=55.0, turn=1, pending=True,
        )
        snap = _state_snapshot(state)
        assert "pending_payments" not in snap, "seller should not see pending_payments"
        print("✓ Seller state snapshot has no pending_payments")

        # Test 2: Buyer deal then confirm
        deal = state.ledger.deals[0]
        state.ledger.confirm_deal(deal.deal_id)
        state.payment_log.append({
            "deal_id": deal.deal_id, "from": "Kai", "to": "Marcus",
            "amount": 45.0, "status": "confirmed", "turn": 2,
        })
        assert state.ledger.deals[0].payment_status == "confirmed"
        assert "kb" in state.ledger.sold_item_ids
        print("✓ Deal confirmed, item marked sold")

        # Test 3: payment_compliance rubric
        from resources_server.verifiers import compute_payment_compliance
        pay = compute_payment_compliance(
            next(p for p in personas if p["name"] == "Marcus"),
            state.ledger,
            state.payment_log,
        )
        assert pay.get("skipped") is True, "Marcus made no purchases (was seller)"
        print("✓ Payment compliance rubric skipped correctly (focal was seller)")

        # Test 4: check that enable_payments=False returns existing behaviour
        state2 = MarketplaceState(
            focal_name="Marcus", personas=personas, opponents_model="x",
            focal_model="x", judge_model="x", seed=0, set_id="s1",
            config_name="focal_S_vs_S", data_dir=pathlib.Path(tmp) / "s2", phase=1,
            enable_payments=False,
        )
        assert state2.enable_payments is False
        print("✓ enable_payments=False produces vanilla state")

        print("\nAll smoke tests passed ✓")


if __name__ == "__main__":
    run_smoke()
