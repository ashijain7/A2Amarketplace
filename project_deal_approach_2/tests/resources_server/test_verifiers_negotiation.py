from resources_server.verifiers import compute_negotiation_quality


def test_no_offers_returns_neutral():
    out = compute_negotiation_quality(channel_log=[], personas=[])
    assert 0 <= out["combined"] <= 1
    assert out["system_anchoring"] == 0.0


def test_anchoring_positive_when_opening_far_from_floor_or_ceiling():
    channel = [
        {"turn": 1, "agent": "S", "action": "listing", "target": "i", "price": 100, "message": ""},
        {"turn": 2, "agent": "B", "action": "offer", "target": "lst_1", "price": 30, "message": ""},
        {"turn": 3, "agent": "S", "action": "counter", "target": "lst_1", "price": 90, "message": ""},
        {"turn": 4, "agent": "B", "action": "counter", "target": "lst_1", "price": 50, "message": ""},
        {"turn": 5, "agent": "S", "action": "accept", "target": "ctr_2", "price": 50, "message": ""},
    ]
    personas = [
        {"name": "S", "items_to_sell": [{"item_id": "i", "name": "x", "floor_price": 40}],
         "items_to_buy": []},
        {"name": "B", "items_to_sell": [],
         "items_to_buy": [{"want_id": "w", "description": "x", "ceiling_price": 60}]},
    ]
    out = compute_negotiation_quality(channel_log=channel, personas=personas)
    assert out["system_anchoring"] > 0
    assert out["system_smoothness"] >= 0
    assert 0 <= out["combined"] <= 1
