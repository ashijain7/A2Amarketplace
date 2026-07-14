"""A run is only saved to the platform if it was asked for.

Short exploratory runs score far below full-length ones — a 10-turn run scored 0.17 where
the same set scores ~0.36 at full length, because the agent never gets to close its deals.
Recording every experiment would drag down every average computed from the store, and
nobody would remember afterwards which rows were "just testing". So the push is opt-in.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adapter  # noqa: E402


def _args(**over):
    base = dict(
        phase="market_deal",
        set="01",
        focal="sonnet",
        opponent="gemini",
        max_turns=20,
        seed=42,
        scammer="on",
        record=False,
    )
    base.update(over)
    return argparse.Namespace(**base)


def test_record_is_off_by_default():
    assert adapter.build_plan(_args())["record"] is False


def test_record_can_be_asked_for():
    assert adapter.build_plan(_args(record=True))["record"] is True


def test_a_caller_without_the_flag_still_works():
    """A bare namespace (older callers, tests) must not blow up — and must not record."""
    args = argparse.Namespace(
        phase="market_deal", set="01", focal="sonnet", opponent="gemini",
        max_turns=20, seed=42,
    )

    assert adapter.build_plan(args)["record"] is False


def test_the_cli_defaults_to_not_recording():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")

    assert ap.parse_args([]).record is False
    assert ap.parse_args(["--record"]).record is True
