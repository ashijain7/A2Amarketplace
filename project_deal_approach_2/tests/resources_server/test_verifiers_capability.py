from unittest.mock import patch
from resources_server.verifiers import (
    compute_capability_asymmetry, compute_advantage_ratio,
)
from resources_server.model_config import MODEL_SONNET, MODEL_HAIKU


def test_advantage_ratio_homogeneous_returns_none():
    gains = {"A": 10.0, "B": 5.0}
    models = {"A": MODEL_SONNET, "B": MODEL_SONNET}
    assert compute_advantage_ratio(gains, models, "all_sonnet") is None


def test_advantage_ratio_mixed_computes_sonnet_over_haiku():
    gains = {"A": 30.0, "B": 30.0, "C": 30.0, "D": 30.0, "E": 30.0,
             "F": 10.0, "G": 10.0, "H": 10.0, "I": 10.0, "J": 10.0}
    models = {"A": MODEL_SONNET, "B": MODEL_SONNET, "C": MODEL_SONNET,
              "D": MODEL_SONNET, "E": MODEL_SONNET,
              "F": MODEL_HAIKU, "G": MODEL_HAIKU, "H": MODEL_HAIKU,
              "I": MODEL_HAIKU, "J": MODEL_HAIKU}
    ratio = compute_advantage_ratio(gains, models, "mixed")
    assert ratio == 3.0


def test_capability_asymmetry_mixed_uses_judge_calls():
    gains = {"A": 30.0, "B": 10.0}
    models = {"A": MODEL_SONNET, "B": MODEL_HAIKU}
    channel = [{"agent": "A", "action": "offer", "message": "x"}]
    deals = []

    judge_outputs = {"self": 5, "observer": 4}
    def fake_judge(prompt: str, *args, **kw) -> int:
        return judge_outputs["self"] if "you played" in prompt.lower() else judge_outputs["observer"]

    with patch("resources_server.verifiers._judge_fairness", side_effect=fake_judge):
        out = compute_capability_asymmetry(
            per_agent_gains=gains,
            model_assignments=models,
            model_config_name="mixed",
            channel_log=channel,
            deals=deals,
            judge_model="openai/gpt-4o-2024-11-20",
        )
    assert out["advantage_ratio"] == 3.0
    assert "sonnet_perceived_fairness" in out
    assert "haiku_perceived_fairness" in out
    assert 0 <= out["combined"] <= 1
