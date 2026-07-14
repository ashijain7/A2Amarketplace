"""A bad model must never boot the stack.

Before this, a typo'd slug cost ~15s and a Ray cluster before failing, and a model
with no tool support was worse: it booted, never posted a listing or made an offer,
scored ~0, and still charged. Both doors (/run_live and /api/run) now check first.

No network here — the catalog is injected.
"""
import pytest

from sim_ui import models, run_api

CATALOG = {
    "anthropic/claude-fable-5": {
        "id": "anthropic/claude-fable-5",
        "name": "Anthropic: Claude Fable 5",
        "supported_parameters": ["temperature", "tools", "tool_choice"],
    },
    "anthropic/claude-sonnet-4.5": {
        "id": "anthropic/claude-sonnet-4.5",
        "name": "Anthropic: Claude Sonnet 4.5",
        "supported_parameters": ["tools"],
    },
    "google/gemini-3.1-flash-image": {          # real model, cannot call tools
        "id": "google/gemini-3.1-flash-image",
        "name": "Google: Gemini 3.1 Flash Image",
        "supported_parameters": ["temperature", "response_format"],
    },
}


def _no_such_model(slug):
    """OpenRouter's per-model lookup: 404 for everything (nothing beyond the list)."""
    return None


def _knows(slug):
    """OpenRouter DOES resolve this alias even though it is absent from the list."""
    if slug == "anthropic/claude-sonnet-4-5":       # our own config.py ships this
        return {"id": "anthropic/claude-sonnet-4.5",
                "name": "Anthropic: Claude Sonnet 4.5",
                "supported_parameters": ["tools", "temperature"]}
    return None


def test_a_typo_is_caught_and_the_real_slug_is_suggested():
    err = models.validate("anthropic/claude-fable", CATALOG, fetch_one=_no_such_model)
    assert err and "not a model" in err
    assert "anthropic/claude-fable-5" in err, "the error must suggest the real slug"


def test_an_unlisted_but_REAL_alias_is_allowed():
    """The model LIST is not the whole truth. OpenRouter accepts aliases it does not
    list — `anthropic/claude-sonnet-4-5` (dashes) is absent from /models yet resolves
    and runs, and it is the slug our own config.py ships. Rejecting it would be a
    false rejection: worse than the typo the check exists to catch."""
    models.reset_cache()
    assert "anthropic/claude-sonnet-4-5" not in CATALOG          # not in the list...
    assert models.validate("anthropic/claude-sonnet-4-5", CATALOG,
                           fetch_one=_knows) is None             # ...but still allowed


def test_a_probe_failure_does_not_condemn_the_slug():
    """If the per-model lookup itself errors (network), allow the run."""
    models.reset_cache()

    def boom(slug):
        raise OSError("openrouter unreachable")

    assert models.validate("who/knows", CATALOG, fetch_one=boom) is None


def test_a_model_that_cannot_call_tools_is_refused():
    err = models.validate("google/gemini-3.1-flash-image", CATALOG, fetch_one=_no_such_model)
    assert err and "cannot call tools" in err


def test_a_good_model_passes():
    assert models.validate("anthropic/claude-fable-5", CATALOG, fetch_one=_no_such_model) is None


def test_short_aliases_are_ours_and_are_not_looked_up():
    # adapter.py resolves these; they are not OpenRouter slugs
    assert models.validate("sonnet", CATALOG, fetch_one=_no_such_model) is None
    assert models.validate("opus", CATALOG, fetch_one=_no_such_model) is None


def test_an_unreachable_catalog_allows_the_run():
    """Our own network blip must not block a run that would have worked."""
    assert models.validate("anything/at-all", None, fetch_one=_no_such_model) is None
    assert models.validate_pair("sonnet", "who/knows", None, fetch_one=_no_such_model) is None


def test_validate_pair_names_the_offending_side():
    err = models.validate_pair("sonnet", "anthropic/claude-fable", CATALOG, fetch_one=_no_such_model)
    assert err.startswith("Opponent model:")
    err = models.validate_pair("anthropic/claude-fable", "sonnet", CATALOG, fetch_one=_no_such_model)
    assert err.startswith("Evaluated model:")


def test_catalog_falls_back_to_a_stale_copy_when_the_fetch_fails():
    models.reset_cache()
    assert models.catalog(fetch=lambda: dict(CATALOG)) == CATALOG

    def boom():
        raise OSError("openrouter is down")

    assert models.catalog(fetch=boom, force=True) == CATALOG   # stale beats nothing
    models.reset_cache()
    assert models.catalog(fetch=boom) is None                  # nothing cached -> None


def test_only_tool_calling_models_are_offered():
    ids = [m["id"] for m in models.tool_calling_models(CATALOG)]
    assert "google/gemini-3.1-flash-image" not in ids
    assert "anthropic/claude-fable-5" in ids


def test_live_door_refuses_a_bad_model_without_booting(monkeypatch):
    from sim_ui import live_runner
    monkeypatch.setattr(models, "catalog", lambda *a, **k: CATALOG)
    monkeypatch.setattr(models, "_fetch_one", _no_such_model)

    def _never(*a, **k):
        raise AssertionError("the stack must not boot for an invalid model")

    monkeypatch.setattr(live_runner, "_stream_live_run", _never)
    out = list(live_runner.stream_live_run(
        {"phase": "market_deal", "set": "set_01",
         "focal": "anthropic/claude-fable", "opponent": "sonnet"}))
    assert len(out) == 1 and out[0]["kind"] == "error"
    assert "claude-fable-5" in out[0]["msg"]


def test_run_api_returns_400_for_a_bad_model(monkeypatch):
    monkeypatch.setattr(models, "catalog", lambda *a, **k: CATALOG)
    monkeypatch.setattr(models, "_fetch_one", _no_such_model)
    monkeypatch.setattr(run_api, "_stack_running", lambda: False)
    with pytest.raises(run_api.BadModel):
        run_api.run_blocking({"phase": "market_deal", "set": "set_01",
                              "focal": "sonnet",
                              "opponent": "google/gemini-3.1-flash-image"})
