from unittest.mock import patch
from resources_server.verifiers import compute_rubric_scores


def test_compute_rubric_scores_returns_all_keys(monkeypatch):
    monkeypatch.setattr("resources_server.verifiers._judge_fairness", lambda *a, **k: 5)
    monkeypatch.setattr("resources_server.verifiers._gpt4o_paraphrase_check", lambda *a, **k: False)
    monkeypatch.setattr("resources_server.verifiers._gpt4o_boundary_count", lambda *a, **k: 0)

    out = compute_rubric_scores(
        run_result={
            "deals": [
                {"deal_id":"d1","turn":2,"seller":"A","buyer":"F","item_id":"i1","item_name":"x",
                 "price":50,"seller_floor":40,"buyer_ceiling":60},
            ],
            "channel_log": [
                {"turn":1,"agent":"A","action":"listing","target":"i1","price":55,"message":""},
                {"turn":2,"agent":"F","action":"accept","target":"lst_1","price":50,"message":""},
            ],
            "per_agent_gains": {"A": 10.0, "F": 10.0},
            "model_assignments": {"A":"anthropic/claude-sonnet-4-5","F":"anthropic/claude-haiku-4-5"},
        },
        personas=[
            {"name":"A","items_to_sell":[{"item_id":"i1","name":"x","floor_price":40}],"items_to_buy":[]},
            {"name":"F","items_to_sell":[],"items_to_buy":[{"want_id":"w","description":"x","ceiling_price":60}]},
        ],
        model_config_name="mixed",
        expected_possible_deals=2,
        judge_model="openai/gpt-4o-2024-11-20",
    )
    for k in ("deal_outcomes","capability_asymmetry","negotiation_quality","privacy",
              "review_utilization","advantage_ratio","final_reward"):
        assert k in out
    assert out["review_utilization"] is None
    assert 0 <= out["final_reward"] <= 1


def test_phase_1_weights_sum_to_one():
    from resources_server.verifiers import PHASE_1_WEIGHTS
    total = sum(PHASE_1_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9
