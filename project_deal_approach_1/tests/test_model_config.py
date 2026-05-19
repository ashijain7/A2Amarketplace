import pytest

from resources_server.model_config import (
    get_model_config,
    CONFIG_NAMES,
    SONNET,
    HAIKU,
)


def test_all_four_configs_exist():
    assert set(CONFIG_NAMES) == {
        "focal_S_vs_S", "focal_H_vs_S", "focal_S_vs_H", "focal_H_vs_H",
    }


def test_focal_S_vs_S_returns_sonnet_sonnet():
    cfg = get_model_config("focal_S_vs_S")
    assert cfg["focal_model"] == SONNET
    assert cfg["opponents_model"] == SONNET


def test_focal_H_vs_S_returns_haiku_focal_sonnet_opponents():
    cfg = get_model_config("focal_H_vs_S")
    assert cfg["focal_model"] == HAIKU
    assert cfg["opponents_model"] == SONNET


def test_focal_S_vs_H_returns_sonnet_focal_haiku_opponents():
    cfg = get_model_config("focal_S_vs_H")
    assert cfg["focal_model"] == SONNET
    assert cfg["opponents_model"] == HAIKU


def test_focal_H_vs_H_returns_haiku_haiku():
    cfg = get_model_config("focal_H_vs_H")
    assert cfg["focal_model"] == HAIKU
    assert cfg["opponents_model"] == HAIKU


def test_unknown_config_raises():
    with pytest.raises(ValueError):
        get_model_config("nonsense")
