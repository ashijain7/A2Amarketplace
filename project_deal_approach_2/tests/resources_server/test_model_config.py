import pytest
from resources_server.model_config import (
    assign_models, MODEL_SONNET, MODEL_HAIKU, VALID_CONFIGS,
)


PERSONAS = [{"name": f"P{i}"} for i in range(10)]


def test_all_sonnet_assigns_sonnet_to_everyone():
    out = assign_models(PERSONAS, "all_sonnet")
    assert all(v == MODEL_SONNET for v in out.values())
    assert set(out.keys()) == {f"P{i}" for i in range(10)}


def test_all_haiku_assigns_haiku_to_everyone():
    out = assign_models(PERSONAS, "all_haiku")
    assert all(v == MODEL_HAIKU for v in out.values())


def test_mixed_splits_5_sonnet_5_haiku_by_index():
    out = assign_models(PERSONAS, "mixed")
    for i in range(5):
        assert out[f"P{i}"] == MODEL_SONNET
    for i in range(5, 10):
        assert out[f"P{i}"] == MODEL_HAIKU


def test_invalid_config_raises():
    with pytest.raises(ValueError):
        assign_models(PERSONAS, "nonsense")


def test_valid_configs_complete():
    assert VALID_CONFIGS == {"all_sonnet", "mixed", "all_haiku"}
