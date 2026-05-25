import pytest

from resources_server.model_config import (
    get_model_config,
    CONFIG_NAMES,
    SONNET,
    HAIKU,
    OPUS,
    GEMINI,
    GEMINI_FLASH,
    GPT5_5,
)


def test_all_configs_exist():
    assert set(CONFIG_NAMES) == {
        "focal_S_vs_S", "focal_H_vs_S", "focal_S_vs_H", "focal_H_vs_H",
        "focal_O_vs_H", "focal_H_vs_O", "focal_S_vs_G", "focal_G_vs_S",
        "focal_O_vs_G", "focal_G_vs_X",
        "focal_G35_vs_X",
    }


def test_focal_G_vs_X():
    cfg = get_model_config("focal_G_vs_X")
    assert cfg["focal_model"] == GEMINI
    assert cfg["opponents_model"] == GPT5_5
    assert GPT5_5 == "openai/gpt-5.5"


def test_focal_O_vs_H():
    cfg = get_model_config("focal_O_vs_H")
    assert cfg["focal_model"] == OPUS
    assert cfg["opponents_model"] == HAIKU


def test_focal_H_vs_O():
    cfg = get_model_config("focal_H_vs_O")
    assert cfg["focal_model"] == HAIKU
    assert cfg["opponents_model"] == OPUS


def test_focal_S_vs_G():
    cfg = get_model_config("focal_S_vs_G")
    assert cfg["focal_model"] == SONNET
    assert cfg["opponents_model"] == GEMINI


def test_focal_G_vs_S():
    cfg = get_model_config("focal_G_vs_S")
    assert cfg["focal_model"] == GEMINI
    assert cfg["opponents_model"] == SONNET


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


def test_focal_G35_vs_X():
    cfg = get_model_config("focal_G35_vs_X")
    assert cfg["focal_model"] == GEMINI_FLASH
    assert cfg["opponents_model"] == GPT5_5
    assert GEMINI_FLASH == "google/gemini-3.5-flash"
