"""In transaction mode the focal's payment work must show up in its own step list.

The agent writes to two books. Listings, offers, counters and accepts go to the public
channel; pay / submit_otp / confirm_receipt / say_in_room / get_status go to the private
settlement room and touch the channel not at all. `focal_actions` was built from the
channel alone, so the mode whose whole point is paying reported only the shopping half —
a run that closed one deal and then spent nine calls dodging a look-alike handle read as
"3 steps". The reward was never wrong (transactional_integrity is computed from the
settlement records directly); the story told about it was.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adapter  # noqa: E402


def _plan(**over):
    base = dict(
        phase="transaction", set="03", focal="sonnet", opponent="sonnet",
        max_turns=20, seed=42, scammer="on", record=False,
    )
    base.update(over)
    return adapter.build_plan(argparse.Namespace(**base))


def _rollout(channel=(), settlement_actions=None, focal="Kai"):
    row = {
        "metadata": {"set_id": "set_03", "focal_persona": focal},
        "reward": 0.5,
        "rubric_scores": {},
        "channel_events": list(channel),
        "deals": [],
    }
    if settlement_actions is not None:
        row["settlement_actions"] = settlement_actions
    return row


def _write(tmp_path, *rows):
    p = tmp_path / "rollouts.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def test_payment_calls_are_counted_as_focal_steps(tmp_path):
    path = _write(tmp_path, _rollout(
        channel=[{"agent": "Kai", "action": "listing", "target": "item_1", "price": 40}],
        settlement_actions=[
            {"seq": 1, "action": "say_in_room", "target": "deal_1"},
            {"seq": 2, "action": "choose_method", "target": "deal_1"},
            {"seq": 3, "action": "pay", "target": "deal_1", "price": 40},
        ],
    ))

    out = adapter.extract_results(path, _plan(), ["sonnet"])
    ps = out["per_set"][0]

    assert ps["num_focal_steps"] == 4, "1 public action + 3 payment calls"
    assert [a["action"] for a in ps["focal_actions"]] == [
        "listing", "say_in_room", "choose_method", "pay",
    ]


def test_the_public_half_still_comes_first(tmp_path):
    """Settlement only opens once a deal has closed, so its calls belong after the
    channel's — the step list has to read as the run actually happened."""
    path = _write(tmp_path, _rollout(
        channel=[
            {"agent": "Kai", "action": "listing", "target": "item_1"},
            {"agent": "Diego", "action": "offer", "target": "item_1"},
            {"agent": "Kai", "action": "accept", "target": "item_1"},
        ],
        settlement_actions=[{"seq": 9, "action": "confirm_receipt", "target": "deal_1"}],
    ))

    actions = adapter.extract_results(path, _plan(), ["sonnet"])["per_set"][0]["focal_actions"]

    assert [a["action"] for a in actions] == ["listing", "accept", "confirm_receipt"]


def test_settlement_calls_are_tagged_so_the_two_books_stay_distinguishable(tmp_path):
    path = _write(tmp_path, _rollout(
        channel=[{"agent": "Kai", "action": "listing", "target": "item_1"}],
        settlement_actions=[{"seq": 1, "action": "pay", "target": "deal_1"}],
    ))

    actions = adapter.extract_results(path, _plan(), ["sonnet"])["per_set"][0]["focal_actions"]

    assert actions[0].get("where") == "market"
    assert actions[1].get("where") == "settlement"


def test_a_run_without_settlement_is_unchanged(tmp_path):
    """market_deal / review / swap_shop never build a Settlement, so the key is absent
    and the step list must stay exactly what it was."""
    path = _write(tmp_path, _rollout(
        channel=[
            {"agent": "Kai", "action": "listing", "target": "item_1", "price": 40},
            {"agent": "Diego", "action": "offer", "target": "item_1", "price": 30},
        ],
    ))

    ps = adapter.extract_results(path, _plan(phase="market_deal"), ["sonnet"])["per_set"][0]

    assert ps["num_focal_steps"] == 1
    assert ps["focal_actions"] == [
        {"action": "listing", "target": "item_1", "price": 40, "where": "market"}
    ]


def test_an_older_rollout_without_the_key_does_not_break(tmp_path):
    """Every rollout on disk predates the settlement log. They must still load — just
    with the public half only, as before."""
    path = _write(tmp_path, _rollout(
        channel=[{"agent": "Kai", "action": "listing", "target": "item_1"}],
        settlement_actions=None,
    ))

    ps = adapter.extract_results(path, _plan(), ["sonnet"])["per_set"][0]

    assert ps["num_focal_steps"] == 1
