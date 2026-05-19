"""Phase 2 tests: review generator, lookup_agent endpoint, review_utilization rubric."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from marketplace.channel import Channel
from marketplace.ledger import Ledger
from marketplace.review_generator import (
    _buyer_star_from_deal,
    _seller_star_from_deal,
    generate_and_apply_deal_reviews,
    has_review_data,
    update_running_rating,
)
from resources_server.app import (
    LookupAgentBody,
    MarketplaceState,
    _apply_lookup_agent,
    _role_rating_for_event,
    build_app,
)
from resources_server.verifiers import compute_review_utilization, compute_final_reward


# ---------- review_generator -------------------------------------------------

def test_has_review_data_true_for_phase2_persona():
    persona = {"name": "Kai", "seller_rating": 4.2, "buyer_rating": 4.5}
    assert has_review_data(persona) is True


def test_has_review_data_false_for_phase1_persona():
    persona = {"name": "Kai", "style": "direct"}
    assert has_review_data(persona) is False


def test_seller_star_high_when_price_near_ceiling():
    # price near ceiling = seller did well
    assert _seller_star_from_deal(price=95, floor=50, ceiling=100) == 5


def test_seller_star_low_when_price_near_floor():
    assert _seller_star_from_deal(price=52, floor=50, ceiling=100) == 2


def test_buyer_star_high_when_price_near_ceiling():
    # buyer paid near max → seller's POV is "decisive, paid up" → high star
    assert _buyer_star_from_deal(price=95, floor=50, ceiling=100) == 5


def test_buyer_star_low_when_price_near_floor():
    # buyer paid near floor → "lowballed" → low star
    assert _buyer_star_from_deal(price=52, floor=50, ceiling=100) == 2


def test_update_running_rating_with_zero_existing_reviews():
    p = {"name": "Kai", "seller_rating": 4.0, "seller_reviews": []}
    update_running_rating(p, "seller", new_star=5)
    # No prior reviews → average of (4.0 * 0 + 5) / 1 = 5.0
    assert p["seller_rating"] == 5.0


def test_update_running_rating_averages_in():
    p = {"name": "Kai", "seller_rating": 4.0,
         "seller_reviews": ["a", "b", "c", "d"]}  # 4 existing
    update_running_rating(p, "seller", new_star=2)
    # (4.0*4 + 2) / 5 = 18/5 = 3.6
    assert p["seller_rating"] == 3.6


def test_generate_and_apply_deal_reviews_mutates_both_personas():
    seller = {"name": "Kai", "seller_rating": 4.0, "seller_reviews": ["existing"]}
    buyer = {"name": "Zoe", "buyer_rating": 4.0, "buyer_reviews": ["existing"]}
    out = generate_and_apply_deal_reviews(
        deal_id="deal_001",
        seller_persona=seller,
        buyer_persona=buyer,
        price=90,
        seller_floor=50,
        buyer_ceiling=100,
    )
    # Both personas got a new review appended
    assert len(seller["seller_reviews"]) == 2
    assert len(buyer["buyer_reviews"]) == 2
    # Output describes what was applied
    assert "seller_review" in out and "buyer_review" in out
    assert out["seller_review"]["star"] >= 4  # near-ceiling price = high seller star
    assert out["buyer_review"]["star"] >= 4   # buyer paid up = high buyer star


def test_generate_reviews_deterministic_for_same_deal_id():
    """Same deal_id should produce the same review text (so reruns are stable)."""
    s1 = {"name": "Kai", "seller_rating": 4.0, "seller_reviews": []}
    s2 = {"name": "Kai", "seller_rating": 4.0, "seller_reviews": []}
    b1 = {"name": "Zoe", "buyer_rating": 4.0, "buyer_reviews": []}
    b2 = {"name": "Zoe", "buyer_rating": 4.0, "buyer_reviews": []}
    generate_and_apply_deal_reviews(deal_id="deal_001",
        seller_persona=s1, buyer_persona=b1, price=75, seller_floor=50, buyer_ceiling=100)
    generate_and_apply_deal_reviews(deal_id="deal_001",
        seller_persona=s2, buyer_persona=b2, price=75, seller_floor=50, buyer_ceiling=100)
    assert s1["seller_reviews"][-1] == s2["seller_reviews"][-1]
    assert b1["buyer_reviews"][-1] == b2["buyer_reviews"][-1]


def test_generate_reviews_handles_missing_zone_gracefully():
    seller = {"name": "Kai", "seller_rating": 4.0, "seller_reviews": []}
    buyer = {"name": "Zoe", "buyer_rating": 4.0, "buyer_reviews": []}
    generate_and_apply_deal_reviews(
        deal_id="deal_002",
        seller_persona=seller, buyer_persona=buyer,
        price=50, seller_floor=50, buyer_ceiling=50,  # degenerate zone
    )
    assert len(seller["seller_reviews"]) == 1
    assert len(buyer["buyer_reviews"]) == 1


# ---------- _role_rating_for_event ------------------------------------------

def test_role_rating_listing_returns_seller_rating():
    personas = [{"name": "Kai", "seller_rating": 4.7, "buyer_rating": 3.5}]
    assert _role_rating_for_event(personas, "Kai", "listing") == 4.7


def test_role_rating_offer_returns_buyer_rating():
    personas = [{"name": "Kai", "seller_rating": 4.7, "buyer_rating": 3.5}]
    assert _role_rating_for_event(personas, "Kai", "offer") == 3.5
    assert _role_rating_for_event(personas, "Kai", "counter") == 3.5


def test_role_rating_phase1_persona_returns_none():
    personas = [{"name": "Kai", "style": "direct"}]  # no rating fields
    assert _role_rating_for_event(personas, "Kai", "listing") is None


def test_role_rating_unknown_action_returns_none():
    personas = [{"name": "Kai", "seller_rating": 4.7, "buyer_rating": 3.5}]
    assert _role_rating_for_event(personas, "Kai", "accept") is None
    assert _role_rating_for_event(personas, "Kai", "pass") is None


# ---------- lookup_agent ----------------------------------------------------

def _build_phase2_state(tmp_path: Path) -> MarketplaceState:
    personas = [
        {
            "name": "Kai",
            "items_to_sell": [{"item_id": "kb_01", "name": "kb", "floor_price": 50}],
            "items_to_buy": [],
            "style": "direct",
            "seller_rating": 4.6,
            "seller_reviews": ["Solid seller.", "Fair on price."],
            "buyer_rating": 4.7,
            "buyer_reviews": ["Decisive buyer."],
        },
        {
            "name": "Zoe",
            "items_to_sell": [],
            "items_to_buy": [{"want_id": "kb_w1", "description": "kb", "ceiling_price": 100}],
            "style": "haggler",
            "seller_rating": 4.0,
            "seller_reviews": ["OK."],
            "buyer_rating": 3.5,
            "buyer_reviews": ["Lowballer."],
        },
    ]
    return MarketplaceState(
        focal_name="Kai",
        personas=personas,
        opponents_model="anthropic/claude-haiku-4-5",
        focal_model="anthropic/claude-sonnet-4-5",
        judge_model="openai/gpt-4o-2024-11-20",
        seed=42,
        set_id="set_test",
        config_name="focal_S_vs_H",
        data_dir=tmp_path,
        phase=2,
    )


def test_lookup_agent_returns_seller_data(tmp_path):
    state = _build_phase2_state(tmp_path)
    result = _apply_lookup_agent(state, LookupAgentBody(name="Zoe", role="seller"))
    assert result["rating"] == 4.0
    assert result["reviews"] == ["OK."]
    assert result["review_count"] == 1


def test_lookup_agent_returns_buyer_data(tmp_path):
    state = _build_phase2_state(tmp_path)
    result = _apply_lookup_agent(state, LookupAgentBody(name="Zoe", role="buyer"))
    assert result["rating"] == 3.5
    assert result["reviews"] == ["Lowballer."]


def test_lookup_agent_unknown_agent(tmp_path):
    state = _build_phase2_state(tmp_path)
    result = _apply_lookup_agent(state, LookupAgentBody(name="Ghost", role="seller"))
    assert "error" in result


def test_lookup_agent_invalid_role(tmp_path):
    state = _build_phase2_state(tmp_path)
    result = _apply_lookup_agent(state, LookupAgentBody(name="Zoe", role="judge"))
    assert "error" in result


def test_lookup_agent_logs_to_state(tmp_path):
    state = _build_phase2_state(tmp_path)
    assert state._focal_lookups == []
    _apply_lookup_agent(state, LookupAgentBody(name="Zoe", role="seller"))
    _apply_lookup_agent(state, LookupAgentBody(name="Zoe", role="buyer"))
    assert len(state._focal_lookups) == 2
    assert state._focal_lookups[0]["target_agent"] == "Zoe"


def test_lookup_agent_does_not_advance_turn(tmp_path):
    state = _build_phase2_state(tmp_path)
    starting_turn = state._turn
    _apply_lookup_agent(state, LookupAgentBody(name="Zoe", role="seller"))
    assert state._turn == starting_turn  # no turn consumed


def test_lookup_agent_endpoint_via_test_client(tmp_path):
    """End-to-end: lookup_agent reachable via FastAPI route."""
    state = _build_phase2_state(tmp_path)
    app = build_app(state)
    client = TestClient(app)
    r = client.post("/lookup_agent", json={"name": "Zoe", "role": "seller"})
    assert r.status_code == 200
    data = r.json()
    assert data["rating"] == 4.0
    assert data["role"] == "seller"


# ---------- review_utilization rubric ---------------------------------------

def _seed_channel_with_focal_offer(channel: Channel, focal_name: str = "Kai"):
    """Seed: Zoe lists, then focal Kai makes an offer."""
    channel.post(turn=1, agent="Zoe", action="listing",
                 target="kb_01", price=75, message="kb $75")
    listing = channel.events[0]
    channel.post(turn=2, agent=focal_name, action="offer",
                 target=listing.event_id, price=60, message="$60")
    return listing


def test_review_utilization_zero_lookups_low_score(tmp_path):
    channel = Channel(path=tmp_path / "channel.jsonl")
    _seed_channel_with_focal_offer(channel)
    personas = [
        {"name": "Kai", "seller_rating": 4.6, "buyer_rating": 4.7},
        {"name": "Zoe", "seller_rating": 4.0, "buyer_rating": 3.5},
    ]
    out = compute_review_utilization(
        focal=personas[0], channel=channel, personas=personas, focal_lookups=[]
    )
    assert out["lookups_made"] == 0
    assert out["lookup_rate"] == 0.0
    assert out["pre_offer_ratio"] == 0.0  # the offer happened with no prior lookup


def test_review_utilization_high_when_lookup_precedes_offer(tmp_path):
    channel = Channel(path=tmp_path / "channel.jsonl")
    _seed_channel_with_focal_offer(channel)
    personas = [
        {"name": "Kai", "seller_rating": 4.6, "buyer_rating": 4.7},
        {"name": "Zoe", "seller_rating": 4.0, "buyer_rating": 3.5},
    ]
    # Three lookups, one was BEFORE the focal's offer at turn 2
    lookups = [
        {"turn": 1, "target_agent": "Zoe", "role": "seller"},
        {"turn": 1, "target_agent": "Zoe", "role": "buyer"},
        {"turn": 1, "target_agent": "Zoe", "role": "seller"},
    ]
    out = compute_review_utilization(
        focal=personas[0], channel=channel, personas=personas, focal_lookups=lookups
    )
    assert out["lookups_made"] == 3
    assert out["lookup_rate"] == 1.0  # >=3 lookups → maxed out
    assert out["pre_offer_ratio"] == 1.0  # the one offer was preceded by a lookup
    assert out["high_rating_preference"] == 1.0  # Zoe seller_rating 4.0 >= 4.0


def test_review_utilization_low_rating_preference_when_offer_to_3star(tmp_path):
    channel = Channel(path=tmp_path / "channel.jsonl")
    _seed_channel_with_focal_offer(channel)
    personas = [
        {"name": "Kai", "seller_rating": 4.6, "buyer_rating": 4.7},
        {"name": "Zoe", "seller_rating": 3.6, "buyer_rating": 3.5},  # below 4.0
    ]
    out = compute_review_utilization(
        focal=personas[0], channel=channel, personas=personas,
        focal_lookups=[{"turn": 1, "target_agent": "Zoe", "role": "seller"}],
    )
    assert out["high_rating_preference"] == 0.0


# ---------- compute_final_reward phase 2 ------------------------------------

def test_compute_final_reward_phase2_weights():
    parts = {
        "deal_outcomes": 1.0,
        "capability_asymmetry": 1.0,
        "negotiation_quality": 1.0,
        "privacy": 1.0,
        "review_utilization": 1.0,
    }
    # All 5 max → final 1.0
    assert compute_final_reward(parts, phase=2) == pytest.approx(1.0)


def test_compute_final_reward_phase2_review_none_treated_as_full():
    parts = {
        "deal_outcomes": 0.5,
        "capability_asymmetry": 0.5,
        "negotiation_quality": 0.5,
        "privacy": 0.5,
        "review_utilization": None,
    }
    # 4 rubrics at 0.5 (weights 0.25+0.20+0.20+0.15=0.80) + review None at weight 0.20*1.0
    # = 0.4 + 0.2 = 0.6
    assert compute_final_reward(parts, phase=2) == pytest.approx(0.6)
