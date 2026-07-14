"""OpenRouter model catalog — used to validate a custom model BEFORE a run boots.

Why this exists: the model picker lets you type any `provider/model` slug. A typo
used to cost a full stack boot (~15s + a Ray cluster) before failing, and a model
with no tool-calling support was worse — it booted, played the marketplace by never
posting a listing or making an offer, scored ~0, and charged you for it.

So both models are checked here first:
  1. does the slug exist on OpenRouter?          (catches typos, suggests near matches)
  2. does it advertise `tools` support?          (76 of 343 models cannot call tools)

Deliberately soft: if OpenRouter itself is unreachable we SKIP validation and let
the run proceed. Our own network blip must not block a run that would have worked.

Short aliases (`sonnet`, `opus`) are ours, resolved by adapter.py, and are not
checked here — sim_ui's venv cannot import the engine (no python-dotenv).
"""
from __future__ import annotations

import difflib
import json
import time
import urllib.request
from typing import Callable, Optional

MODELS_URL = "https://openrouter.ai/api/v1/models"
TTL_S = 3600            # the list changes when models ship, not by the minute
TIMEOUT_S = 8

_cache: Optional[dict] = None      # {"at": epoch, "models": {id: {...}}}

_UNSET = object()          # "fetch it yourself" — distinct from None ("unavailable")
_UNKNOWN = object()        # "could not reach OpenRouter" — distinct from None ("404")


def _fetch() -> dict:
    req = urllib.request.Request(MODELS_URL, headers={"User-Agent": "a2a-marketplace"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        data = json.loads(r.read().decode())
    return {m["id"]: m for m in data.get("data", []) if m.get("id")}


def catalog(fetch: Callable[[], dict] = _fetch, force: bool = False) -> Optional[dict]:
    """{slug: model} from OpenRouter, cached for an hour. None if unreachable."""
    global _cache
    now = time.time()
    if not force and _cache and now - _cache["at"] < TTL_S:
        return _cache["models"]
    try:
        models = fetch()
    except Exception:
        return _cache["models"] if _cache else None      # stale beats nothing
    _cache = {"at": now, "models": models}
    return models


def reset_cache() -> None:
    global _cache
    _cache = None
    _probe_cache.clear()


def supports_tools(model: dict) -> bool:
    return "tools" in (model.get("supported_parameters") or [])


def _fetch_one(slug: str) -> Optional[dict]:
    """Ask OpenRouter about ONE model. Returns a model-like dict, or None on 404."""
    url = f"{MODELS_URL}/{slug}/endpoints"
    req = urllib.request.Request(url, headers={"User-Agent": "a2a-marketplace"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            data = json.loads(r.read().decode()).get("data") or {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    eps = data.get("endpoints") or []
    params = sorted({p for e in eps for p in (e.get("supported_parameters") or [])})
    return {"id": data.get("id") or slug, "name": data.get("name") or slug,
            "supported_parameters": params}


_probe_cache: dict = {}


def probe(slug: str, fetch_one: Callable[[str], Optional[dict]] = _fetch_one):
    """Look a single slug up directly. Returns the model dict, None if OpenRouter
    says 404, or _UNKNOWN if we could not reach OpenRouter at all.

    This exists because **the model LIST is not the whole truth**: OpenRouter
    accepts aliases that it does not list. `anthropic/claude-sonnet-4-5` (dashes)
    is absent from /models yet resolves to `claude-sonnet-4.5` and works — and it
    is the slug our own config.py ships. A list-only check would reject models that
    genuinely run, which is worse than the typo it was meant to catch.
    """
    if slug in _probe_cache:
        return _probe_cache[slug]
    try:
        m = fetch_one(slug)
    except Exception:
        return _UNKNOWN                     # network problem — do not condemn the slug
    _probe_cache[slug] = m
    return m


def validate(slug: str, models: Optional[dict],
             fetch_one: Callable[[str], Optional[dict]] = _fetch_one) -> Optional[str]:
    """None if the model is usable; otherwise a message saying why it is not.

    Returns None (i.e. allow) when `models` is None — the list could not be
    fetched, and a run that would have worked must not be blocked by that.
    """
    slug = (slug or "").strip()
    if not slug:
        return "No model selected."
    if "/" not in slug:
        # a short alias (sonnet/opus/...) — adapter.py resolves these, and they are
        # ours, so there is nothing to look up.
        return None
    if models is None:
        return None

    m = models.get(slug)
    if m is None:
        # not in the list — that does NOT mean it does not exist (see probe()).
        m = probe(slug, fetch_one)
        if m is _UNKNOWN:
            return None                     # cannot check ⇒ allow
        if m is None:
            near = difflib.get_close_matches(slug, list(models), n=3, cutoff=0.6)
            if not near:
                prefix = slug.split("/")[0] + "/"
                near = [k for k in models if k.startswith(prefix)][:3]
            hint = f" Did you mean {', '.join(near)}?" if near else ""
            return f"'{slug}' is not a model on OpenRouter.{hint}"

    if not supports_tools(m):
        return (f"'{slug}' cannot call tools, so it cannot trade in the marketplace "
                f"(it would never post a listing or make an offer). Pick a "
                f"tool-calling model.")
    return None


def validate_pair(focal: str, opponent: str, models=_UNSET, **kw) -> Optional[str]:
    """Check both sides. Returns the first problem, or None if the run may start.

    Pass models=None to mean "the catalog is unavailable" (everything is allowed).
    Omit it and the catalog is fetched.
    """
    if models is _UNSET:
        models = catalog()
    for label, slug in (("Evaluated model", focal), ("Opponent model", opponent)):
        err = validate(slug, models, **kw)
        if err:
            return f"{label}: {err}"
    return None


def tool_calling_models(models=_UNSET) -> list[dict]:
    """The pickable models — id + display name, tool-callers only."""
    if models is _UNSET:
        models = catalog()
    if not models:
        return []
    return sorted(
        ({"id": m["id"], "name": m.get("name") or m["id"]}
         for m in models.values() if supports_tools(m)),
        key=lambda m: m["id"])
