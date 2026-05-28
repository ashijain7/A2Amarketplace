import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from resources_server.app import MarketplaceServer, MarketplaceState


def _make_state(tmp_path, enable_payments=True, focal="Marcus"):
    personas = [
        {"name": "Marcus", "items_to_sell": [{"item_id": "kb", "name": "Keyboard",
          "floor_price": 35}], "items_to_buy": [], "style": "direct"},
        {"name": "Kai", "items_to_sell": [], "items_to_buy": [{"want_id": "w1",
          "description": "keyboard", "ceiling_price": 55}], "style": "direct"},
    ]
    state = MarketplaceState(
        focal_name=focal, personas=personas, opponents_model="x",
        focal_model="x", judge_model="x", seed=0, set_id="s1",
        config_name="test", data_dir=tmp_path, phase=1,
        enable_payments=enable_payments,
        stripe_accounts={"Marcus": "cus_marcus", "Kai": "cus_kai"},
    )
    return state


def _pending_deal(state):
    return state.ledger.record_deal(
        seller="Kai", buyer="Marcus", item_id="kb",
        item_name="Keyboard", price=45.0,
        seller_floor=35.0, buyer_ceiling=55.0, turn=1, pending=True,
    )


# ---- check_balance tests ----

def test_check_balance_returns_balance(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    app = server.setup_webserver()
    client = TestClient(app)
    with patch("resources_server.stripe_ledger.get_balance_cents", return_value=15000):
        resp = client.post("/check_balance", json={})
    assert resp.status_code == 200
    assert resp.json()["balance"] == 150.0
    assert resp.json()["agent"] == "Marcus"


def test_check_balance_skipped_when_payments_off(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path, enable_payments=False)
    server.attach_state(state)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/check_balance", json={})
    assert resp.json()["skipped"] is True


# ---- transfer_funds tests ----

def test_transfer_funds_success(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state)
    app = server.setup_webserver()
    client = TestClient(app)
    with patch("resources_server.stripe_ledger.transfer",
               return_value={"success": True, "amount": 45.0,
                             "sender_new_balance": 105.0, "receiver_new_balance": 195.0}):
        resp = client.post("/transfer_funds", json={
            "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
        })
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert state.ledger.deals[0].payment_status == "confirmed"
    assert len(state.payment_log) == 1


def test_transfer_funds_insufficient_funds_cancels_deal(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state)
    app = server.setup_webserver()
    client = TestClient(app)
    with patch("resources_server.stripe_ledger.transfer",
               return_value={"success": False, "error": "insufficient_funds",
                             "balance": 20.0, "needed": 45.0, "shortfall": 25.0}):
        resp = client.post("/transfer_funds", json={
            "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
        })
    assert resp.json()["success"] is False
    assert state.ledger.deals[0].payment_status == "cancelled"


def test_transfer_funds_wrong_buyer_blocked(tmp_path):
    # Kai is focal but Marcus is the buyer on the deal
    server = MarketplaceServer()
    state = _make_state(tmp_path, focal="Kai")
    server.attach_state(state)
    deal = _pending_deal(state)  # buyer=Marcus
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
    })
    assert "not the buyer" in resp.json()["error"]


def test_transfer_funds_wrong_amount_blocked(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Kai", "amount": 40.0, "deal_id": deal.deal_id
    })
    assert "does not match" in resp.json()["error"]


def test_transfer_funds_wrong_seller_blocked(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Marcus", "amount": 45.0, "deal_id": deal.deal_id
    })
    assert "not the seller" in resp.json()["error"]


def test_transfer_funds_double_payment_blocked(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state)
    state.ledger.confirm_deal(deal.deal_id)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
    })
    assert "already paid" in resp.json()["error"]


# ---- verify_payment tests ----

def test_verify_payment_pending_shows_what_focal_owes(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/verify_payment", json={"deal_id": deal.deal_id})
    data = resp.json()
    assert data["paid"] is False
    assert data["you_are"] == "buyer"
    assert data["you_owe"] == 45.0
    assert data["owe_to"] == "Kai"


def test_verify_payment_confirmed(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state)
    state.ledger.confirm_deal(deal.deal_id)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/verify_payment", json={"deal_id": deal.deal_id})
    assert resp.json()["paid"] is True


def test_verify_payment_unknown_deal(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/verify_payment", json={"deal_id": "deal_999"})
    assert "not found" in resp.json()["error"]
