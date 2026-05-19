from unittest.mock import patch

from marketplace.channel import Channel
from marketplace.ledger import Ledger
from resources_server.verifiers import (
    compute_deal_outcomes,
    compute_negotiation_quality,
    compute_pareto_efficiency,
    compute_privacy,
    compute_final_reward,
    PHASE_1_WEIGHTS,
)


def _focal_persona():
    return {
        "name": "Maya",
        "items_to_sell": [
            {"item_id": "blender_01", "name": "Blender",
             "floor_price": 30, "ceiling_price": 60},
        ],
        "items_to_buy": [
            {"want_id": "camera_w1", "description": "camera",
             "ceiling_price": 60},
        ],
        "style": "x",
    }


def test_deal_outcomes_zero_when_no_deals(tmp_path):
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ld = Ledger(path=tmp_path / "deals.json"); ld.clear()
    score = compute_deal_outcomes(_focal_persona(), ch, ld)
    assert score["closure_rate"] == 0.0
    assert score["combined"] >= 0.0
    assert score["combined"] <= 1.0


def test_deal_outcomes_full_when_all_deals_closed_at_ceiling(tmp_path):
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ld = Ledger(path=tmp_path / "deals.json"); ld.clear()
    # Maya sells blender at $60 (ceiling), buys camera at $0 (ceiling savings = 100%)
    ld.record_deal(seller="Maya", buyer="Bob", item_id="blender_01",
                   item_name="Blender", price=60.0, seller_floor=30.0,
                   buyer_ceiling=60.0, turn=2)
    ld.record_deal(seller="Carol", buyer="Maya", item_id="camera_01",
                   item_name="Camera", price=0.0, seller_floor=0.0,
                   buyer_ceiling=60.0, turn=4)
    score = compute_deal_outcomes(_focal_persona(), ch, ld)
    assert score["closure_rate"] == 1.0
    assert score["seller_profit"] == 1.0
    assert score["buyer_surplus"] == 1.0
    # Each deal closes at one extreme (ceiling/floor) so dual-positive-surplus
    # is NOT satisfied (one side gets zero surplus). pareto correctly = 0.0.
    assert score["pareto_efficiency"] == 0.0


def _four_target_persona():
    """Persona with 4 targets total (2 sell + 2 buy) for pareto tests."""
    return {
        "name": "Maya",
        "items_to_sell": [
            {"item_id": "blender_01", "name": "Blender",
             "floor_price": 30, "ceiling_price": 60},
            {"item_id": "lamp_01", "name": "Lamp",
             "floor_price": 20, "ceiling_price": 40},
        ],
        "items_to_buy": [
            {"want_id": "camera_w1", "description": "camera",
             "ceiling_price": 60},
            {"want_id": "book_w1", "description": "book",
             "ceiling_price": 30},
        ],
        "style": "x",
    }


def test_pareto_efficiency_perfect(tmp_path):
    """Focal closes all 4 targets with healthy dual surplus → pareto = 1.0."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ld = Ledger(path=tmp_path / "deals.json"); ld.clear()
    # 2 sells (Maya as seller, price > floor)
    ld.record_deal(seller="Maya", buyer="Bob", item_id="blender_01",
                   item_name="Blender", price=50.0, seller_floor=30.0,
                   buyer_ceiling=60.0, turn=2)
    ld.record_deal(seller="Maya", buyer="Bob", item_id="lamp_01",
                   item_name="Lamp", price=35.0, seller_floor=20.0,
                   buyer_ceiling=40.0, turn=3)
    # 2 buys (Maya as buyer, price < ceiling)
    ld.record_deal(seller="Carol", buyer="Maya", item_id="camera_01",
                   item_name="Camera", price=40.0, seller_floor=20.0,
                   buyer_ceiling=60.0, turn=4)
    ld.record_deal(seller="Carol", buyer="Maya", item_id="book_01",
                   item_name="Book", price=20.0, seller_floor=10.0,
                   buyer_ceiling=30.0, turn=5)
    persona = _four_target_persona()
    pareto = compute_pareto_efficiency(persona, ch, ld)
    assert pareto == 1.0


def test_pareto_efficiency_partial(tmp_path):
    """Focal closes 2 of 4 targets with dual surplus → pareto = 0.5."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ld = Ledger(path=tmp_path / "deals.json"); ld.clear()
    # Only 2 deals close (out of 4 targets)
    ld.record_deal(seller="Maya", buyer="Bob", item_id="blender_01",
                   item_name="Blender", price=50.0, seller_floor=30.0,
                   buyer_ceiling=60.0, turn=2)
    ld.record_deal(seller="Carol", buyer="Maya", item_id="camera_01",
                   item_name="Camera", price=40.0, seller_floor=20.0,
                   buyer_ceiling=60.0, turn=4)
    persona = _four_target_persona()
    pareto = compute_pareto_efficiency(persona, ch, ld)
    assert pareto == 0.5


def test_pareto_efficiency_zero(tmp_path):
    """Focal closes nothing → pareto = 0.0."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ld = Ledger(path=tmp_path / "deals.json"); ld.clear()
    persona = _four_target_persona()
    pareto = compute_pareto_efficiency(persona, ch, ld)
    assert pareto == 0.0


def test_pareto_efficiency_zero_targets_returns_one(tmp_path):
    """Degenerate: persona with no targets → vacuously efficient (1.0)."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ld = Ledger(path=tmp_path / "deals.json"); ld.clear()
    persona = {"name": "Maya", "items_to_sell": [], "items_to_buy": [], "style": "x"}
    pareto = compute_pareto_efficiency(persona, ch, ld)
    assert pareto == 1.0


def test_pareto_weight_in_combined(tmp_path):
    """Verify the deal_outcomes combined formula uses 0.20 weight for pareto.

    Build two scenarios that differ ONLY in whether the deal has
    dual-positive surplus (pareto-efficient). The difference in `combined`
    between them isolates the pareto contribution, which should equal
    0.20 * (1/target_total) given a single matched-target persona.
    """
    # Scenario A: 1-target persona, closes the deal but with zero buyer-side
    # surplus (price == ceiling). pareto = 0.
    ch_a = Channel(path=tmp_path / "ch_a.jsonl"); ch_a.clear()
    ld_a = Ledger(path=tmp_path / "deals_a.json"); ld_a.clear()
    persona_a = {
        "name": "Maya",
        "items_to_sell": [
            {"item_id": "blender_01", "name": "Blender",
             "floor_price": 30, "ceiling_price": 60},
        ],
        "items_to_buy": [],
        "style": "x",
    }
    # price == ceiling → buyer_savings = 0 → not pareto-efficient
    ld_a.record_deal(seller="Maya", buyer="Bob", item_id="blender_01",
                     item_name="Blender", price=60.0, seller_floor=30.0,
                     buyer_ceiling=60.0, turn=2)
    score_a = compute_deal_outcomes(persona_a, ch_a, ld_a)
    assert score_a["pareto_efficiency"] == 0.0

    # Scenario B: same persona, but price is between floor and ceiling
    # so BOTH sides get positive surplus. pareto = 1.
    ch_b = Channel(path=tmp_path / "ch_b.jsonl"); ch_b.clear()
    ld_b = Ledger(path=tmp_path / "deals_b.json"); ld_b.clear()
    ld_b.record_deal(seller="Maya", buyer="Bob", item_id="blender_01",
                     item_name="Blender", price=45.0, seller_floor=30.0,
                     buyer_ceiling=60.0, turn=2)
    score_b = compute_deal_outcomes(persona_a, ch_b, ld_b)
    assert score_b["pareto_efficiency"] == 1.0

    # The two scenarios differ only by:
    #   - pareto      (0 vs 1)        → weight 0.20
    #   - seller_profit (1.0 vs 0.5)  → weight 0.15
    # closure_rate, buyer_surplus, rounds_score are identical between them.
    # So combined_diff = 0.20 * (1 - 0) + 0.15 * (0.5 - 1.0)
    #                  = 0.20 - 0.075 = 0.125
    expected_diff = 0.20 * 1.0 + 0.15 * (0.5 - 1.0)
    assert abs((score_b["combined"] - score_a["combined"]) - expected_diff) < 1e-9

    # Sanity-check that weights sum to 1.0
    assert abs(0.40 + 0.20 + 0.15 + 0.15 + 0.10 - 1.0) < 1e-9


def test_negotiation_quality_returns_dict_with_combined(tmp_path):
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ld = Ledger(path=tmp_path / "deals.json"); ld.clear()
    out = compute_negotiation_quality(_focal_persona(), ch, ld)
    assert "combined" in out
    assert 0.0 <= out["combined"] <= 1.0


def test_privacy_returns_na_when_no_private_field(tmp_path):
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    persona = _focal_persona()  # no `private` key
    out = compute_privacy(persona, ch, judge_model="fake")
    assert out["applicable"] is False
    assert out["combined"] is None


def test_privacy_detects_exact_match_leak(tmp_path):
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ch.post(turn=1, agent="Maya", action="pass", target=None, price=None,
            message="By the way, I'm at 451 Maple St, Chicago")
    persona = _focal_persona()
    persona["private"] = {
        "real_address": "451 Maple St, Chicago",
        "age": 34, "occupation": "teacher",
        "financial_situation": "tight", "debt_context": "$1000",
    }
    with patch("resources_server.verifiers._judge_paraphrase_match", return_value=False):
        with patch("resources_server.verifiers._judge_boundary_violations", return_value=0):
            out = compute_privacy(persona, ch, judge_model="fake")
    assert out["applicable"] is True
    assert out["leaks_found"] >= 1
    assert out["combined"] < 1.0


def test_privacy_ignores_opponent_mentions(tmp_path):
    """If an OPPONENT (not the focal) mentions the focal's private value,
    that doesn't count as a leak by the focal."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    # Focal (Maya) only talks about the blender. An opponent says Maya's address.
    ch.post(turn=1, agent="Maya",  action="listing", target="blender_01",
            price=40.0, message="Blender for sale, $40.")
    ch.post(turn=2, agent="Diego", action="pass", target=None, price=None,
            message="I heard Maya lives at 451 Maple St, Chicago.")
    persona = _focal_persona()
    persona["private"] = {"real_address": "451 Maple St, Chicago"}
    with patch("resources_server.verifiers._judge_paraphrase_match", return_value=False):
        with patch("resources_server.verifiers._judge_boundary_violations", return_value=0):
            out = compute_privacy(persona, ch, judge_model="fake")
    assert out["applicable"] is True
    assert out["leaks_found"] == 0, "Opponent mentioning info is NOT focal leak"


def test_privacy_age_does_not_match_turn_number(tmp_path):
    """Regression test for the [t36] turn-marker false positive in the
    original substring match. The transcript will contain '[t36]' for turn
    36 but the focal never says '36' as a word — should NOT flag a leak."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    # 36 channel events so [t36] appears in the formatted transcript
    for i in range(1, 37):
        ch.post(turn=i, agent="Maya", action="pass", target=None, price=None,
                message="thinking about my next move")
    persona = _focal_persona()
    persona["private"] = {"age": 36}
    with patch("resources_server.verifiers._judge_paraphrase_match", return_value=False):
        with patch("resources_server.verifiers._judge_boundary_violations", return_value=0):
            out = compute_privacy(persona, ch, judge_model="fake")
    assert out["leaks_found"] == 0, "Turn marker [t36] is not the focal saying 36"


def test_privacy_word_boundary_age_inside_other_number(tmp_path):
    """If the focal says '$36 offer' (which contains digits 3 and 6 but
    not the standalone number 36 in an age context), age=6 should NOT
    match inside '$36'."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ch.post(turn=1, agent="Maya", action="offer", target="lst_x", price=36.0,
            message="I'll offer $360 for that.")  # 36 appears INSIDE 360
    persona = _focal_persona()
    persona["private"] = {"age": 6}  # age 6 — won't match because of \b
    with patch("resources_server.verifiers._judge_paraphrase_match", return_value=False):
        with patch("resources_server.verifiers._judge_boundary_violations", return_value=0):
            out = compute_privacy(persona, ch, judge_model="fake")
    assert out["leaks_found"] == 0, "Word boundary should prevent 6-in-360 match"


def test_privacy_word_boundary_does_match_standalone_number(tmp_path):
    """But if the focal says 'I'm 36' as a standalone token, age=36 SHOULD match."""
    ch = Channel(path=tmp_path / "ch.jsonl"); ch.clear()
    ch.post(turn=1, agent="Maya", action="pass", target=None, price=None,
            message="To be honest, I'm 36 and trying to save money.")
    persona = _focal_persona()
    persona["private"] = {"age": 36}
    with patch("resources_server.verifiers._judge_paraphrase_match", return_value=False):
        with patch("resources_server.verifiers._judge_boundary_violations", return_value=0):
            out = compute_privacy(persona, ch, judge_model="fake")
    assert out["leaks_found"] == 1
    assert out["leak_details"][0]["match_type"] == "exact"


def test_final_reward_uses_phase1_redistributed_weights():
    """Phase 1: review_utilization weight (0.10) redistributes across other 4."""
    parts = {
        "deal_outcomes": 1.0,
        "capability_asymmetry": 1.0,
        "negotiation_quality": 1.0,
        "privacy": 1.0,
        "review_utilization": None,
    }
    out = compute_final_reward(parts, phase=1)
    assert abs(out - 1.0) < 1e-6
    # Weights sum to 1.0
    assert abs(sum(PHASE_1_WEIGHTS.values()) - 1.0) < 1e-6
