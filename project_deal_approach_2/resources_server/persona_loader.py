"""Load a persona set by name (e.g., 'set_03')."""

import json
from pathlib import Path

from marketplace import config

PERSONAS_DIR = config.PERSONAS_DIR


def load_persona_set(name: str) -> list[dict]:
    """Read personas/{name}.json. Raises FileNotFoundError if missing."""
    path = Path(PERSONAS_DIR) / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"persona set not found: {path}")
    return json.loads(path.read_text())
