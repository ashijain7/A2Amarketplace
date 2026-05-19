"""
Central configuration for the Project Deal PoC.

All paths, model names, and tunable constants live here so the rest of
the code stays focused on logic. No LLM calls happen in this file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# -- Paths ---------------------------------------------------------------

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PROMPTS_DIR = ROOT / "prompts"

PERSONAS_PATH = DATA_DIR / "personas.json"
PERSONAS_DIR = ROOT / "personas"
CHANNEL_PATH = DATA_DIR / "channel.jsonl"
DEALS_PATH = DATA_DIR / "deals.json"
SUMMARY_PATH = DATA_DIR / "summary.json"
RUNS_DIR = DATA_DIR / "runs"

INTERVIEWER_PROMPT_PATH = PROMPTS_DIR / "interviewer.txt"
AGENT_TEMPLATE_PATH = PROMPTS_DIR / "agent_template.txt"

# -- OpenRouter API config -----------------------------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Default model for both interviewer and marketplace agents.
# Swap to "anthropic/claude-haiku-4.5" to test the invisible-disadvantage angle.
DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"

# Some tasks (like persona generation) benefit from a stronger model.
INTERVIEWER_MODEL = DEFAULT_MODEL

# -- Marketplace constants ----------------------------------------------

MAX_TURNS = 120             # hard cap on scheduler iterations
STALL_LIMIT = 10            # end run if this many turns pass with no listing/offer/deal
DEFAULT_NUM_PERSONAS = 10   # number of agents to generate by default

# Per-call LLM settings
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 800

# -- Sanity check -------------------------------------------------------

def require_api_key():
    """Call this from any entrypoint that needs the API."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set.\n"
            "Either export it in your shell or create a .env file "
            "(see .env.example) in the project root."
        )
