"""Central configuration for Approach 1 marketplace core.

Phase-aware paths: the MARKETPLACE_PHASE env var selects which phase's
personas + agent templates to load. Defaults to "1".

Set in your shell or wrapper script:
    export MARKETPLACE_PHASE=1   # phase 1 (basic negotiation)
    export MARKETPLACE_PHASE=2   # phase 2 (+ reviews)
    export MARKETPLACE_PHASE=3   # phase 3 (swapshop)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PHASE = os.getenv("MARKETPLACE_PHASE", "1")  # selects phase-specific resources

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
PROMPTS_DIR = ROOT / "marketplace" / "prompts"
PERSONAS_DIR = ROOT / f"personas_phase{PHASE}"     # phase-scoped
RESULTS_DIR = ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"

CHANNEL_PATH = DATA_DIR / "channel.jsonl"
DEALS_PATH = DATA_DIR / "deals.json"

AGENT_TEMPLATE_PATH = PROMPTS_DIR / f"agent_template_phase{PHASE}.txt"            # opponent (JSON output)
AGENT_TEMPLATE_FOCAL_PATH = PROMPTS_DIR / f"agent_template_focal_phase{PHASE}.txt"  # focal (tool calling)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"
HAIKU_MODEL = "anthropic/claude-haiku-4-5"
OPUS_MODEL = "anthropic/claude-opus-4-7"
GEMINI_MODEL = "google/gemini-3.1-pro-preview"
GEMINI_FLASH_MODEL = "google/gemini-3.5-flash"
GPT5_5_MODEL = "openai/gpt-5.5"
JUDGE_MODEL = "openai/gpt-4o-2024-11-20"

MAX_TURNS = 120
STALL_LIMIT = 10
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 800


def require_api_key():
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Export it or put it in a .env file."
        )
