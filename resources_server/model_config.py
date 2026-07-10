"""Maps experiment config names to per-agent model assignments."""

import os

from marketplace import config as mp_config

SONNET = mp_config.DEFAULT_MODEL  # "anthropic/claude-sonnet-4-5"
HAIKU = mp_config.HAIKU_MODEL     # "anthropic/claude-haiku-4-5"
OPUS = mp_config.OPUS_MODEL       # "anthropic/claude-opus-4-7"
OPUS_48 = mp_config.OPUS_48_MODEL # "anthropic/claude-opus-4.8"
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
    "focal_O_vs_X",
    "focal_X_vs_O48",
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
    "focal_O_vs_X": {"focal_model": OPUS_48, "opponents_model": GPT5_5},
    "focal_X_vs_O48": {"focal_model": GPT5_5, "opponents_model": OPUS_48},
}


def get_model_config(name: str) -> dict:
    """Return {focal_model, opponents_model} for a named config.

    The opponents_model can be overridden at runtime via the
    MARKETPLACE_OPPONENTS_MODEL env var (set by the adapter before the stack
    boots). This lets a caller pick any opponent field without editing this
    committed table or regenerating task files. No override -> table value.
    """
    if name not in _CONFIGS:
        raise ValueError(
            f"Unknown model config: {name}. Choices: {sorted(_CONFIGS.keys())}"
        )
    cfg = dict(_CONFIGS[name])
    override = os.getenv("MARKETPLACE_OPPONENTS_MODEL")
    if override:
        cfg["opponents_model"] = override
    return cfg
