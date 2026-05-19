"""Central paths and tunable constants for the marketplace package."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent  # project_deal_approach_2/
PROMPTS_DIR = ROOT / "marketplace" / "prompts"
PERSONAS_DIR = ROOT / "personas"

# Per-run temp paths (used by Channel/Ledger when no path is provided).
DATA_DIR = ROOT / "data"
CHANNEL_PATH = DATA_DIR / "channel.jsonl"
DEALS_PATH = DATA_DIR / "deals.json"

AGENT_TEMPLATE_PATH = PROMPTS_DIR / "agent_template.txt"

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Defaults used when a per-agent model isn't supplied.
DEFAULT_MODEL = "anthropic/claude-haiku-4-5"

# Marketplace constants
STALL_LIMIT = 10
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 800


def require_api_key():
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to .env or export it."
        )
