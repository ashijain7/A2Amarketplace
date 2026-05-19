from unittest.mock import patch

from fastapi.testclient import TestClient

from resources_server.app import build_app, MarketplaceState


def _bootstrap_state(tmp_path):
    personas = [
        {"name": "Alice", "items_to_sell": [
            {"item_id": "blender_01", "name": "Blender", "floor_price": 30}],
         "items_to_buy": [], "style": "x"},
        {"name": "Bob", "items_to_sell": [],
         "items_to_buy": [
             {"want_id": "blender_w1", "description": "blender",
              "ceiling_price": 60}],
         "style": "y"},
        {"name": "Carol", "items_to_sell": [], "items_to_buy": [], "style": "z"},
    ]
    state = MarketplaceState(
        focal_name="Alice",
        personas=personas,
        opponents_model="fake-model",
        focal_model="fake-model",
        judge_model="fake-judge",
        seed=42,
        set_id="set_01",
        config_name="focal_S_vs_S",
        data_dir=tmp_path,
    )
    return state


def test_post_listing_returns_state(tmp_path):
    state = _bootstrap_state(tmp_path)
    app = build_app(state)
    client = TestClient(app)

    fake = '{"action": "pass", "target": null, "price": null, "message": "ok"}'
    with patch("resources_server.opponent_runner.call_llm", return_value=fake):
        r = client.post("/post_listing", json={
            "item_id": "blender_01", "price": 45, "message": "Selling blender",
        })
    assert r.status_code == 200
    body = r.json()
    assert "active_listings" in body
    assert any(lst["item_id"] == "blender_01" for lst in body["active_listings"])


def test_make_offer_records_offer_event(tmp_path):
    state = _bootstrap_state(tmp_path)
    app = build_app(state)
    client = TestClient(app)

    fake = '{"action": "pass", "target": null, "price": null, "message": "ok"}'
    with patch("resources_server.opponent_runner.call_llm", return_value=fake):
        client.post("/post_listing", json={
            "item_id": "blender_01", "price": 45, "message": "selling",
        })
        listing_id = state.channel.events[0].event_id
        r = client.post("/make_offer", json={
            "target_listing_id": listing_id, "price": 40, "message": "buying",
        })
    assert r.status_code == 200
    assert any(e.action == "offer" and e.price == 40 for e in state.channel.events)


def test_pass_endpoint_adds_pass_event(tmp_path):
    state = _bootstrap_state(tmp_path)
    app = build_app(state)
    client = TestClient(app)

    fake = '{"action": "pass", "target": null, "price": null, "message": "ok"}'
    with patch("resources_server.opponent_runner.call_llm", return_value=fake):
        r = client.post("/pass", json={"message": "nothing to do"})
    assert r.status_code == 200
    assert any(e.action == "pass" and e.agent == "Alice"
               for e in state.channel.events)


def test_verify_endpoint_returns_reward(tmp_path):
    state = _bootstrap_state(tmp_path)
    app = build_app(state)
    client = TestClient(app)

    # No deals, no actions — should still return a numeric reward.
    with patch("resources_server.verifiers.call_llm", return_value="4"):
        r = client.post("/verify", json={})
    assert r.status_code == 200
    body = r.json()
    assert "reward" in body
    assert 0.0 <= body["reward"] <= 1.0
    assert "rubric_scores" in body
