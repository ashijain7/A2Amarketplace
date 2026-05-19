"""
Thin wrapper around the OpenAI SDK pointed at OpenRouter.

All LLM calls in the project go through call_llm(). This keeps API
plumbing in one place so swapping providers or models is trivial.
"""

import json
from typing import Optional
from openai import OpenAI

from . import config


_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Lazy-init the OpenAI client pointed at OpenRouter."""
    global _client
    if _client is None:
        config.require_api_key()
        _client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
        )
    return _client


def call_llm(
    system: str,
    user: str,
    model: str = config.DEFAULT_MODEL,
    temperature: float = config.LLM_TEMPERATURE,
    max_tokens: int = config.LLM_MAX_TOKENS,
) -> str:
    """Make a single chat-completion call. Returns the raw text response."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def parse_json_response(text: str) -> dict:
    """
    Parse a JSON object out of an LLM response, tolerating common
    quirks: leading/trailing prose, markdown fences, trailing commas.
    Raises ValueError if nothing parseable is found.
    """
    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        # remove opening fence (```json or ```)
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        # remove closing fence
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back: find the first { and last } and try that slice
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response:\n{text[:500]}")


def parse_json_array_response(text: str) -> list:
    """Same as parse_json_response but for JSON arrays."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON array from LLM response:\n{text[:500]}")
