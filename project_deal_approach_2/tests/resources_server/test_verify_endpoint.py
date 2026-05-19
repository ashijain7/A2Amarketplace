from unittest.mock import patch
from resources_server.app import MarketplaceServer


def test_marketplace_server_verify_returns_reward(monkeypatch):
    server = MarketplaceServer()

    fake_run_result = {
        "deals": [
            {"deal_id":"d1","turn":2,"seller":"A","buyer":"F","item_id":"i1","item_name":"x",
             "price":50,"seller_floor":40,"buyer_ceiling":60},
        ],
        "channel_log": [
            {"turn":1,"agent":"A","action":"listing","target":"i1","price":55,"message":""},
            {"turn":2,"agent":"F","action":"accept","target":"lst_1","price":50,"message":""},
        ],
        "per_agent_gains": {"A":10.0, "F":10.0},
        "model_assignments": {"A":"anthropic/claude-sonnet-4-5","F":"anthropic/claude-haiku-4-5"},
    }
    fake_personas = [
        {"name":"A","items_to_sell":[{"item_id":"i1","name":"x","floor_price":40}],"items_to_buy":[]},
        {"name":"F","items_to_sell":[],"items_to_buy":[{"want_id":"w","description":"x","ceiling_price":60}]},
    ]

    monkeypatch.setattr("resources_server.app.load_persona_set", lambda n: fake_personas)
    monkeypatch.setattr("resources_server.verifiers._judge_fairness", lambda *a, **k: 5)
    monkeypatch.setattr("resources_server.verifiers._gpt4o_paraphrase_check", lambda *a, **k: False)
    monkeypatch.setattr("resources_server.verifiers._gpt4o_boundary_count", lambda *a, **k: 0)

    out = server.verify_inline(
        run_result=fake_run_result,
        persona_set="set_01",
        model_config_name="mixed",
        seed=42,
        expected_possible_deals=3,
    )
    assert "reward" in out
    assert 0 <= out["reward"] <= 1
    assert out["rubric_scores"]["advantage_ratio"] is not None
