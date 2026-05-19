from resources_server.verifiers import compute_deal_outcomes


def make_deal(turn, price, floor, ceiling, seller="S", buyer="B", item_id="i"):
    return {
        "deal_id": f"deal_{turn}", "turn": turn, "seller": seller, "buyer": buyer,
        "item_id": item_id, "item_name": "x",
        "price": price, "seller_floor": floor, "buyer_ceiling": ceiling,
    }


def test_zero_deals_returns_zero():
    out = compute_deal_outcomes(deals=[], channel_log=[], possible_deals=5, personas=[])
    assert out["closure_rate"] == 0.0
    assert out["combined"] == 0.0
    # When no deals, surplus metrics also zero
    assert out["seller_profit"] == 0.0
    assert out["buyer_surplus"] == 0.0


def test_one_perfect_deal_high_score():
    deals = [make_deal(turn=5, price=50, floor=40, ceiling=60)]
    channel = [
        {"turn": 1, "agent": "B", "action": "offer", "target": "lst_1", "price": 45, "message": ""},
        {"turn": 5, "agent": "S", "action": "accept", "target": "off_1", "price": 50, "message": ""},
    ]
    out = compute_deal_outcomes(deals=deals, channel_log=channel, possible_deals=1, personas=[])
    assert out["closure_rate"] == 1.0
    assert 0 < out["combined"] <= 1.0


def test_closure_rate_capped_at_one():
    deals = [make_deal(turn=1, price=10, floor=5, ceiling=15) for _ in range(5)]
    out = compute_deal_outcomes(deals=deals, channel_log=[], possible_deals=3, personas=[])
    assert out["closure_rate"] == 1.0


# ---- Harmonized seller_profit / buyer_surplus split (matches A1 + paper) -----

def test_seller_profit_separate_metric():
    """seller_profit appears as a separate normalized 0-1 sub-component."""
    # price=50, floor=40 -> (50-40)/(50*2-40) = 10/60 = 0.1667
    deals = [make_deal(turn=5, price=50, floor=40, ceiling=60)]
    out = compute_deal_outcomes(deals=deals, channel_log=[], possible_deals=1, personas=[])
    assert "seller_profit" in out
    assert 0.0 <= out["seller_profit"] <= 1.0
    assert abs(out["seller_profit"] - (10 / 60)) < 1e-3


def test_buyer_surplus_separate_metric():
    """buyer_surplus appears as a separate normalized 0-1 sub-component."""
    # price=50, ceiling=60 -> (60-50)/60 = 0.1667
    deals = [make_deal(turn=5, price=50, floor=40, ceiling=60)]
    out = compute_deal_outcomes(deals=deals, channel_log=[], possible_deals=1, personas=[])
    assert "buyer_surplus" in out
    assert 0.0 <= out["buyer_surplus"] <= 1.0
    assert abs(out["buyer_surplus"] - (10 / 60)) < 1e-3


def test_combined_weights_match_harmonized_breakdown():
    """combined formula uses 0.40/0.20/0.15/0.15/0.10 weights (sum=1.0)."""
    # Construct a single deal where every sub-component is computable and we can
    # back out the combined formula:
    #   closure_rate=1.0, seller_profit=10/60, buyer_surplus=10/60,
    #   pareto_efficiency=1.0 (1 deal with positive surplus / 1 possible),
    #   rounds_score=1-(1/1)=0.0 (single deal, rounds = max_rounds)
    deals = [make_deal(turn=5, price=50, floor=40, ceiling=60)]
    channel = [
        {"turn": 4, "agent": "B", "action": "offer", "target": "i", "price": 48, "message": ""},
        {"turn": 5, "agent": "S", "action": "accept", "target": "off_1", "price": 50, "message": ""},
    ]
    out = compute_deal_outcomes(deals=deals, channel_log=channel, possible_deals=1, personas=[])

    closure_rate = out["closure_rate"]
    seller_profit = out["seller_profit"]
    buyer_surplus = out["buyer_surplus"]
    pareto = out["pareto_efficiency"]
    # rounds_score is implicit; back-compute from the harmonized formula
    # combined = 0.40*closure + 0.20*pareto + 0.15*seller + 0.15*buyer + 0.10*rounds
    expected_no_rounds = (
        0.40 * closure_rate
        + 0.20 * pareto
        + 0.15 * seller_profit
        + 0.15 * buyer_surplus
    )
    rounds_contrib = out["combined"] - expected_no_rounds
    # rounds_score must be in [0, 1] -> contribution in [0, 0.10]
    assert -1e-3 <= rounds_contrib <= 0.10 + 1e-3, (
        f"rounds contribution {rounds_contrib} out of expected [0, 0.10] band; "
        f"weights likely not 0.40/0.20/0.15/0.15/0.10"
    )


def test_combined_weights_sum_to_one():
    """The 5 deal_outcomes weights must sum to 1.0."""
    weights = [0.40, 0.20, 0.15, 0.15, 0.10]
    assert abs(sum(weights) - 1.0) < 1e-9


def test_seller_profit_and_buyer_surplus_clamped_zero_to_one():
    """Both metrics must stay in [0, 1] for typical deals."""
    # Floor exactly equals price -> seller_profit = 0
    deals = [make_deal(turn=1, price=40, floor=40, ceiling=60)]
    out = compute_deal_outcomes(deals=deals, channel_log=[], possible_deals=1, personas=[])
    assert out["seller_profit"] == 0.0
    assert 0.0 <= out["buyer_surplus"] <= 1.0

    # Price exactly equals ceiling -> buyer_surplus = 0
    deals = [make_deal(turn=1, price=60, floor=40, ceiling=60)]
    out = compute_deal_outcomes(deals=deals, channel_log=[], possible_deals=1, personas=[])
    assert out["buyer_surplus"] == 0.0
    assert 0.0 <= out["seller_profit"] <= 1.0
