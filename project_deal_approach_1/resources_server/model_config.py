"""Maps experiment config names to per-agent model assignments."""

from marketplace import config as mp_config

SONNET = mp_config.DEFAULT_MODEL  # "anthropic/claude-sonnet-4-5"
HAIKU = mp_config.HAIKU_MODEL     # "anthropic/claude-haiku-4-5"

CONFIG_NAMES = [
    "focal_S_vs_S",
    "focal_H_vs_S",
    "focal_S_vs_H",
    "focal_H_vs_H",
]

_CONFIGS = {
    "focal_S_vs_S": {"focal_model": SONNET, "opponents_model": SONNET},
    "focal_H_vs_S": {"focal_model": HAIKU, "opponents_model": SONNET},
    "focal_S_vs_H": {"focal_model": SONNET, "opponents_model": HAIKU},
    "focal_H_vs_H": {"focal_model": HAIKU, "opponents_model": HAIKU},
}


def get_model_config(name: str) -> dict:
    """Return {focal_model, opponents_model} for a named config."""
    if name not in _CONFIGS:
        raise ValueError(
            f"Unknown model config: {name}. Choices: {sorted(_CONFIGS.keys())}"
        )
    return dict(_CONFIGS[name])
