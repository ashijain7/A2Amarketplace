"""Maps experiment config names to per-agent model assignments."""

from marketplace import config as mp_config

SONNET = mp_config.DEFAULT_MODEL  # "anthropic/claude-sonnet-4-5"
HAIKU = mp_config.HAIKU_MODEL     # "anthropic/claude-haiku-4-5"
OPUS = mp_config.OPUS_MODEL       # "anthropic/claude-opus-4-7"
GEMINI = mp_config.GEMINI_MODEL   # "google/gemini-3.1-pro-preview"
GPT5_5 = mp_config.GPT5_5_MODEL   # "openai/gpt-5.5"
GEMINI_FLASH = mp_config.GEMINI_FLASH_MODEL  # "google/gemini-3.5-flash"

CONFIG_NAMES = [
    "focal_S_vs_S",
    "focal_H_vs_S",
    "focal_S_vs_H",
    "focal_H_vs_H",
    "focal_O_vs_H",
    "focal_H_vs_O",
    "focal_S_vs_G",
    "focal_G_vs_S",
    "focal_O_vs_G",
    "focal_G_vs_X",
    "focal_G35_vs_X",
    "focal_S_vs_S_pay",
    "focal_S_vs_G_pay",
    "focal_O_vs_G_pay",
    "focal_G_vs_X_pay",
    "focal_G35_vs_X_pay",
]

_CONFIGS = {
    "focal_S_vs_S": {"focal_model": SONNET, "opponents_model": SONNET},
    "focal_H_vs_S": {"focal_model": HAIKU, "opponents_model": SONNET},
    "focal_S_vs_H": {"focal_model": SONNET, "opponents_model": HAIKU},
    "focal_H_vs_H": {"focal_model": HAIKU, "opponents_model": HAIKU},
    "focal_O_vs_H": {"focal_model": OPUS, "opponents_model": HAIKU},
    "focal_H_vs_O": {"focal_model": HAIKU, "opponents_model": OPUS},
    "focal_S_vs_G": {"focal_model": SONNET, "opponents_model": GEMINI},
    "focal_G_vs_S": {"focal_model": GEMINI, "opponents_model": SONNET},
    "focal_O_vs_G": {"focal_model": OPUS, "opponents_model": GEMINI},
    "focal_G_vs_X": {"focal_model": GEMINI, "opponents_model": GPT5_5},
    "focal_G35_vs_X": {"focal_model": GEMINI_FLASH, "opponents_model": GPT5_5},
    "focal_S_vs_S_pay":   {"focal_model": SONNET,       "opponents_model": SONNET,  "enable_payments": True},
    "focal_S_vs_G_pay":   {"focal_model": SONNET,       "opponents_model": GEMINI,  "enable_payments": True},
    "focal_O_vs_G_pay":   {"focal_model": OPUS,         "opponents_model": GEMINI,  "enable_payments": True},
    "focal_G_vs_X_pay":   {"focal_model": GEMINI,       "opponents_model": GPT5_5,  "enable_payments": True},
    "focal_G35_vs_X_pay": {"focal_model": GEMINI_FLASH, "opponents_model": GPT5_5,  "enable_payments": True},
}


def get_model_config(name: str) -> dict:
    """Return {focal_model, opponents_model} for a named config."""
    if name not in _CONFIGS:
        raise ValueError(
            f"Unknown model config: {name}. Choices: {sorted(_CONFIGS.keys())}"
        )
    cfg = dict(_CONFIGS[name])
    cfg.setdefault("enable_payments", False)
    return cfg
