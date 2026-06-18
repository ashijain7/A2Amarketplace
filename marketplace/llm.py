"""
Thin wrapper around the OpenAI SDK pointed at OpenRouter.

All LLM calls in the project go through call_llm(). This keeps API
plumbing in one place so swapping providers or models is trivial.
"""

import json
import time
from typing import Optional
from openai import OpenAI

from . import config


_client: Optional[OpenAI] = None


class LLMCallError(RuntimeError):
    """Raised when an LLM call cannot produce a usable response after retries.

    Callers (especially the privacy judges) MUST NOT swallow this into a
    benign default — a failed check is not evidence of a clean result."""


def get_client() -> OpenAI:
    """Lazy-init the OpenAI client pointed at OpenRouter."""
    global _client
    if _client is None:
        config.require_api_key()
        _client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            timeout=90.0,      # fail fast on a stalled connection (SDK default is ~10 min)
            max_retries=0,     # call_llm owns retry/backoff — don't double-retry per stall
        )
    return _client


def call_llm(
    system: str,
    user: str,
    model: str = config.DEFAULT_MODEL,
    temperature: float = config.LLM_TEMPERATURE,
    max_tokens: int = config.LLM_MAX_TOKENS,
    max_attempts: int = 4,
    extra_body: dict | None = None,
) -> str:
    """Make a chat-completion call and return the raw text response.

    Retries on BOTH failure modes — a raised exception (timeout, rate-limit,
    transient network/provider error) and an empty envelope (`choices`
    missing, no message, or empty content, as observed with some models via
    OpenRouter) — with exponential backoff. If every attempt fails, it RAISES
    LLMCallError rather than returning "". This is deliberate: previously a
    persistent failure returned "", which downstream judges read as "no leak"
    / "no violation", silently biasing scores toward a clean result. A check
    that did not run must surface, not masquerade as a passing check.
    """
    client = get_client()
    last_err = "unknown error"
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body or {},
            )
            choices = getattr(response, "choices", None) or []
            if choices:
                msg = getattr(choices[0], "message", None)
                content = getattr(msg, "content", None) if msg is not None else None
                if content:
                    return content
            last_err = "empty response (no choices / message / content)"
        except Exception as e:  # noqa: BLE001 — retry any provider error
            last_err = f"{type(e).__name__}: {e}"
        if attempt < max_attempts:
            time.sleep(min(2 ** (attempt - 1), 8))  # 1s, 2s, 4s, 8s
    raise LLMCallError(
        f"call_llm failed after {max_attempts} attempts ({model}): {last_err}"
    )


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
