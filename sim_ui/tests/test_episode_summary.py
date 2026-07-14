"""The end-of-episode footer must state only what happened.

The rows this replaced were hardcoded: "Reputation: checked before dealing" printed
on runs that never looked anyone up, "Mutual win: each got a wanted item" on runs
that closed zero swaps, and "Scam resistance: refused ..." on runs that took the
bait. Each test below is that specific lie, made impossible.
"""
import glob
import json
from pathlib import Path

import pytest

from sim_ui.ui.logic import classify_mode, episode_summary, _rollout_to_episode

ROOT = Path(__file__).resolve().parents[2]


def _rollouts():
    for f in sorted(glob.glob(str(ROOT / "results/paper_runs/*/phase*/rollouts.jsonl"))):
        for line in open(f):
            line = line.strip()
            if line:
                yield json.loads(line)


@pytest.fixture(scope="module")
def episodes():
    out = []
    for r in _rollouts():
        ep = _rollout_to_episode(r)
        out.append((r, ep, classify_mode(r)))
    # 139 here: the 140th is the salvaged run, which lives in its own rollout.json
    # rather than a rollouts.jsonl. It is covered by test_every_episode_ships_a_summary.
    assert len(out) == 139
    return out


def _row(ep, label):
    return next((r for r in ep.summary if r[0] == label), None)


def test_reputation_row_matches_whether_it_actually_looked_anyone_up(episodes):
    for rollout, ep, mode in episodes:
        if mode != "review":
            continue
        n = ((rollout["rubric_scores"].get("review_utilization") or {})
             .get("lookups_made") or 0)
        row = _row(ep, "Reputation check")
        assert row, "review episode must state whether it checked reputations"
        if n == 0:
            assert row[1] == "No — never looked anyone up" and row[2] == "bad"
            assert _row(ep, "lookup_agent")[1] == "Unused"
        else:
            assert str(n) in row[1] and row[2] == "good"


def test_mutual_win_row_is_never_claimed_without_a_swap(episodes):
    claimed = 0
    for rollout, ep, mode in episodes:
        if mode != "swap":
            continue
        sq = rollout["rubric_scores"].get("swap_quality") or {}
        closed, mwr = sq.get("swaps_closed") or 0, sq.get("mutual_win_rate")
        row = _row(ep, "Mutual win")
        assert row
        if closed == 0:
            assert row[1] == "No — closed no swaps" and row[2] == "bad"
        elif mwr == 1.0:
            assert row[2] == "good"
            claimed += 1
        else:
            assert row[2] in ("bad", "neutral"), "a partial/failed swap is not a win"
    # the corpus does contain genuine mutual wins — otherwise this test proves nothing
    assert claimed > 0


def test_scam_resistance_row_matches_what_the_settlement_record_says(episodes):
    fooled_seen = 0
    for rollout, ep, mode in episodes:
        if mode != "transaction":
            continue
        recs = [d.settlement for d in ep.deals if d.settlement]
        row = _row(ep, "Scam resistance")
        if not recs:
            assert row is None or row[1] == "No scam attempted"
            continue
        fooled = any(s.get("paid_wrong_owner") or s.get("released_unpaid") for s in recs)
        assert row, "a settled transaction episode must state the scam outcome"
        if fooled:
            assert row[1].startswith("No") and row[2] == "bad"
            fooled_seen += 1
        elif any(s.get("scam_on") for s in recs):
            assert row[1].startswith("Yes") and row[2] == "good"
    assert fooled_seen > 0, "the corpus has episodes that took the bait — flag them"


def test_role_and_prices_come_from_the_deals_actually_closed(episodes):
    for rollout, ep, mode in episodes:
        if mode == "swap":
            continue
        sold = [d for d in ep.deals if d.seller == ep.focal]
        bought = [d for d in ep.deals if d.buyer == ep.focal]
        role = _row(ep, "Role")[1]
        expect = ("Buyer & seller" if sold and bought else
                  "Seller" if sold else "Buyer" if bought else "Closed nothing")
        assert role == expect

        assert _row(ep, "Deals closed")[1] == str(len(ep.deals))
        price = _row(ep, "Closed price")
        if not ep.deals:
            assert price is None, "no deals closed — do not print a closing price"
        else:
            for d in ep.deals:                      # every closed price is shown
                assert (f"${d.price:.0f}" if float(d.price).is_integer()
                        else f"${d.price:.1f}") in price[1]


def test_every_episode_ships_a_summary():
    episodes = json.loads((ROOT / "sim_ui/web/episodes.json").read_text())["episodes"]
    empty = [k for k, e in episodes.items() if not e.get("summary")]
    assert not empty, f"episodes with no summary: {empty[:5]}"
