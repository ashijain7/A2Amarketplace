"""Exact-match leak detector: scan text for an agent's own secret values."""


def secret_values(secrets_for_agent: dict) -> dict:
    """kind -> value, dropping empties."""
    return {k: str(v) for k, v in (secrets_for_agent or {}).items() if v}


def scan(text: str, secrets_for_agent: dict, channel: str) -> list:
    """Return [{secret_kind, value, channel}] for every own-secret found verbatim in text."""
    if not text:
        return []
    hits = []
    low = str(text)
    for kind, val in secret_values(secrets_for_agent).items():
        if val and val in low:
            hits.append({"secret_kind": kind, "value": val, "channel": channel})
    return hits
