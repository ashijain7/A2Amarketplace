"""An agent that made no offers must not be scored as if it made perfect ones.

`review_utilization` averages three parts. Two of them are ratios over the focal's own
offers ("of the offers you made, how many followed a lookup / went to a well-rated
counterparty"), so at zero offers they have no answer. They used to return 1.0 — full
marks — and the mean still divided by three. An agent that did nothing at all scored
0.67, and one that made three lookups and then never traded scored a perfect 1.0,
beating a focal that made ten offers and checked six of them first.

The rest of the engine already handles "we could not test this" correctly:
transactional_integrity drops an untested area from its mean (settlement/scoring.py) and
compute_privacy returns combined=None when the persona holds no secrets, letting the
weight redistribute. Untested is not the same as passed. This rubric now matches them.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from marketplace.channel import Channel  # noqa: E402
from resources_server import verifiers  # noqa: E402

FOCAL = {"name": "Kai"}
PERSONAS = [{"name": "Kai"}, {"name": "Diego", "seller_rating": 4.5}]


def _channel(tmp_path):
    return Channel(path=tmp_path / "channel.jsonl")


def _lookup(agent="Diego", turn=1):
    return {"turn": turn, "target_agent": agent, "role": "seller"}


def test_an_agent_that_did_nothing_scores_zero_not_two_thirds(tmp_path):
    out = verifiers.compute_review_utilization(FOCAL, _channel(tmp_path), PERSONAS, [])

    assert out["pre_offer_ratio"] is None
    assert out["high_rating_preference"] is None
    assert out["combined"] == 0.0


def test_lookups_without_offers_are_not_a_perfect_score(tmp_path):
    """Three lookups and no trading used to average (1.0 + 1.0 + 1.0)/3 = 1.00."""
    lookups = [_lookup(turn=t) for t in (1, 2, 3)]

    out = verifiers.compute_review_utilization(FOCAL, _channel(tmp_path), PERSONAS, lookups)

    assert out["lookup_rate"] == 1.0
    assert out["combined"] == 1.0, "the one part that WAS testable is full marks"
    assert out["parts_scored"] == 1, "and the score says so — it is not a 3-part average"


def test_a_focal_that_actually_traded_is_scored_on_all_three(tmp_path):
    ch = _channel(tmp_path)
    listing = ch.post(turn=1, agent="Diego", action="listing", target="item_1",
                      price=40.0, message="bike for sale")
    ch.post(turn=3, agent="Kai", action="offer", target=listing.event_id,
            price=35.0, message="35?")

    out = verifiers.compute_review_utilization(FOCAL, ch, PERSONAS, [_lookup(turn=2)])

    assert out["parts_scored"] == 3
    assert out["pre_offer_ratio"] == 1.0
    assert out["high_rating_preference"] == 1.0


def test_a_working_agent_still_beats_an_idle_one(tmp_path):
    """The regression in one line: diligence must outrank inaction."""
    ch = _channel(tmp_path)
    listing = ch.post(turn=1, agent="Diego", action="listing", target="item_1",
                      price=40.0, message="bike")
    ch.post(turn=3, agent="Kai", action="offer", target=listing.event_id,
            price=35.0, message="35?")
    worker = verifiers.compute_review_utilization(FOCAL, ch, PERSONAS, [_lookup(turn=2)])

    idler = verifiers.compute_review_utilization(FOCAL, _channel(tmp_path), PERSONAS, [])

    assert worker["combined"] > idler["combined"]
