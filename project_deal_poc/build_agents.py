"""
Turn personas into per-agent system prompts.

This is the "custom agent per person" step from Project Deal. The same
Claude model gets a different system prompt per persona, which is the
only thing that differentiates the 6 agents.

This module exports a single function that returns a dict mapping
name -> system_prompt. The scheduler imports this.
"""

import json
from typing import Any

from . import config


def _format_sell_items(items: list[dict]) -> str:
    if not items:
        return "  (no items to sell)"
    lines = []
    for item in items:
        lines.append(
            f"  - item_id: {item['item_id']}\n"
            f"    name: {item['name']}\n"
            f"    floor_price: ${item['floor_price']} (NEVER sell below this)"
        )
    return "\n".join(lines)


def _format_buy_items(items: list[dict]) -> str:
    if not items:
        return "  (no items to buy)"
    lines = []
    for want in items:
        lines.append(
            f"  - want_id: {want['want_id']}\n"
            f"    looking for: {want['description']}\n"
            f"    ceiling_price: ${want['ceiling_price']} (NEVER pay above this)"
        )
    return "\n".join(lines)


def build_agent_prompts(personas: list[dict]) -> dict[str, str]:
    """
    Build {name: system_prompt} for every persona.

    The template comes from prompts/agent_template.txt. We just slot
    each persona's specifics into the placeholders.
    """
    template = config.AGENT_TEMPLATE_PATH.read_text()
    prompts: dict[str, str] = {}

    for p in personas:
        prompt = template.format(
            name=p["name"],
            items_to_sell_block=_format_sell_items(p.get("items_to_sell", [])),
            items_to_buy_block=_format_buy_items(p.get("items_to_buy", [])),
            style=p.get("style", "Reasonable and direct."),
        )
        prompts[p["name"]] = prompt

    return prompts


def load_personas() -> list[dict]:
    """Load personas.json. Raises if it doesn't exist."""
    if not config.PERSONAS_PATH.exists():
        raise FileNotFoundError(
            f"No personas file at {config.PERSONAS_PATH}.\n"
            f"Run: python -m project_deal_poc.interview"
        )
    return json.loads(config.PERSONAS_PATH.read_text())


if __name__ == "__main__":
    # Smoke test: load personas and print first agent's system prompt
    personas = load_personas()
    prompts = build_agent_prompts(personas)
    first_name = next(iter(prompts))
    print(f"Built {len(prompts)} agent prompts.")
    print(f"\n--- System prompt for {first_name} ---\n")
    print(prompts[first_name])
