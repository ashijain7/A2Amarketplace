"""Map model config name -> per-agent model assignment."""

MODEL_SONNET = "anthropic/claude-sonnet-4-5"
MODEL_HAIKU = "anthropic/claude-haiku-4-5"

VALID_CONFIGS = {"all_sonnet", "mixed", "all_haiku"}


def assign_models(personas: list[dict], model_config: str) -> dict[str, str]:
    """Return {agent_name: model_string} for the given config.

    For 'mixed': personas[0..4] -> Sonnet, personas[5..9] -> Haiku.
    """
    if model_config not in VALID_CONFIGS:
        raise ValueError(
            f"unknown model_config '{model_config}'; valid: {sorted(VALID_CONFIGS)}"
        )
    if model_config == "all_sonnet":
        return {p["name"]: MODEL_SONNET for p in personas}
    if model_config == "all_haiku":
        return {p["name"]: MODEL_HAIKU for p in personas}
    # mixed
    out: dict[str, str] = {}
    for idx, p in enumerate(personas):
        out[p["name"]] = MODEL_SONNET if idx < 5 else MODEL_HAIKU
    return out
