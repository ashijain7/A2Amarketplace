"""Camera-ready scoring rules: PP out of the Mean (B7), SQ N/A for zero swaps (B9)."""
from resources_server import verifiers as V


def test_privacy_not_in_any_weight_vector():
    for w in (V.PHASE_1_WEIGHTS, V.PHASE_2_WEIGHTS, V.PHASE_3_WEIGHTS, V.TRANSACTION_WEIGHTS):
        assert "privacy" not in w and "persona_privacy" not in w


def test_reward_renormalizes_without_privacy():
    scores = {"deal_outcomes": 0.4, "capability_asymmetry": 0.6, "negotiation_quality": 0.5}
    r = V.compute_final_reward(scores, phase=1)
    expected = (0.325 * 0.4 + 0.275 * 0.6 + 0.225 * 0.5) / 0.825
    assert abs(r - round(expected, 4)) < 1e-9


def test_reward_skips_none_dimension():
    # A None dimension (N/A) redistributes its weight — same run, CA missing.
    scores = {"deal_outcomes": 0.4, "capability_asymmetry": None, "negotiation_quality": 0.5}
    r = V.compute_final_reward(scores, phase=1)
    expected = (0.325 * 0.4 + 0.225 * 0.5) / (0.325 + 0.225)
    assert abs(r - round(expected, 4)) < 1e-9


def test_swap_quality_none_when_no_swaps():
    class EmptyLedger:
        deals = []

    sq = V.compute_swap_quality(
        {"name": "X", "items_to_sell": [], "items_to_buy": []}, EmptyLedger()
    )
    assert sq["combined"] is None
    assert sq["swaps_closed"] == 0
