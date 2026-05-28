import pytest
from pathlib import Path
from marketplace.ledger import Ledger


@pytest.fixture
def ledger(tmp_path):
    return Ledger(path=tmp_path / "deals.json")


def _make_deal(ledger, pending=False):
    return ledger.record_deal(
        seller="Kai", buyer="Marcus", item_id="itm_kb",
        item_name="Keyboard", price=45.0,
        seller_floor=35.0, buyer_ceiling=55.0, turn=1,
        pending=pending,
    )


def test_record_deal_default_status_na(ledger):
    deal = _make_deal(ledger, pending=False)
    assert deal.payment_status == "n/a"
    assert "itm_kb" in ledger.sold_item_ids


def test_record_deal_pending_not_sold(ledger):
    deal = _make_deal(ledger, pending=True)
    assert deal.payment_status == "pending"
    assert "itm_kb" not in ledger.sold_item_ids


def test_confirm_deal_marks_sold(ledger):
    deal = _make_deal(ledger, pending=True)
    result = ledger.confirm_deal(deal.deal_id)
    assert result is True
    assert deal.payment_status == "confirmed"
    assert "itm_kb" in ledger.sold_item_ids


def test_cancel_deal_stays_available(ledger):
    deal = _make_deal(ledger, pending=True)
    result = ledger.cancel_deal(deal.deal_id)
    assert result is True
    assert deal.payment_status == "cancelled"
    assert "itm_kb" not in ledger.sold_item_ids


def test_cancel_nonexistent_deal_returns_false(ledger):
    assert ledger.cancel_deal("deal_999") is False


def test_pending_deals_for_buyer(ledger):
    _make_deal(ledger, pending=True)
    pending = ledger.pending_deals_for_buyer("Marcus")
    assert len(pending) == 1
    assert pending[0].item_id == "itm_kb"


def test_pending_deals_excludes_confirmed(ledger):
    deal = _make_deal(ledger, pending=True)
    ledger.confirm_deal(deal.deal_id)
    assert ledger.pending_deals_for_buyer("Marcus") == []
