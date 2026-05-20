"""Phase 3 tests: swap mechanic, swap_match validation, swap_quality rubric,
multimodal task generation, ledger swap records."""

import json
from pathlib import Path

import pytest

from marketplace.channel import Channel
from marketplace.ledger import Deal, Ledger
from marketplace.swap_match import (
    is_valid_swap, items_match_persona_want, normalize_category,
)
from resources_server.app import (
    AcceptSwapBody, MarketplaceState, PostListingPhase3Body, ProposeSwapBody,
    RejectSwapBody, _apply_accept_swap, _apply_post_listing_phase3,
    _apply_propose_swap, _apply_reject_swap, build_app,
)
from resources_server.verifiers import (
    PHASE_3_WEIGHTS, compute_final_reward, compute_swap_quality,
)
from tasks.generate_tasks import (
    PROPOSE_SWAP_TOOL, ACCEPT_SWAP_TOOL, REJECT_SWAP_TOOL,
    POST_LISTING_PHASE3_TOOL, tools_for_phase,
)


# ---- swap_match ------------------------------------------------------------

def test_normalize_category_canonicalizes_known():
    assert normalize_category("Tops") == "tops"
    assert normalize_category("  outerwear  ") == "outerwear"


def test_normalize_category_rejects_unknown():
    assert normalize_category("toys") is None
    assert normalize_category("") is None
    assert normalize_category(None) is None


def test_is_valid_swap_matching_category():
    ok, _ = is_valid_swap("dresses", ["tops", "dresses"])
    assert ok is True


def test_is_valid_swap_no_match():
    ok, reason = is_valid_swap("dresses", ["tops", "bottoms"])
    assert ok is False
    assert "not in listing wants" in reason


def test_is_valid_swap_empty_wants():
    ok, reason = is_valid_swap("tops", [])
    assert ok is False
    assert "no declared wants" in reason


def test_is_valid_swap_unknown_proposer_category():
    ok, reason = is_valid_swap("electronics", ["tops"])
    assert ok is False
    assert "unknown category" in reason


def test_items_match_persona_want_finds_match():
    persona_wants = [
        {"want_id": "w1", "want_category": "tops", "ceiling_price": 30},
        {"want_id": "w2", "want_category": "dresses", "ceiling_price": 60},
    ]
    found = items_match_persona_want("dresses", persona_wants)
    assert found is not None
    assert found["want_id"] == "w2"


def test_items_match_persona_want_no_match():
    persona_wants = [{"want_id": "w1", "want_category": "tops", "ceiling_price": 30}]
    assert items_match_persona_want("outerwear", persona_wants) is None


# ---- tool catalog ---------------------------------------------------------

def test_phase3_has_6_tools_with_swap_trio():
    tools = tools_for_phase(3)
    names = {t["name"] for t in tools}
    assert names == {
        "post_listing", "propose_swap", "accept_swap", "reject_swap",
        "pass", "lookup_agent",
    }


def test_phase3_post_listing_has_wants_not_price():
    tool = next(t for t in tools_for_phase(3) if t["name"] == "post_listing")
    props = tool["parameters"]["properties"]
    assert "wants" in props
    assert "price" not in props
    assert props["wants"]["type"] == "array"


def test_propose_swap_requires_my_item_id_and_target():
    p = PROPOSE_SWAP_TOOL["parameters"]
    assert set(p["required"]) == {"target_listing_id", "my_item_id", "message"}


def test_accept_swap_requires_proposal_id():
    a = ACCEPT_SWAP_TOOL["parameters"]
    assert "target_proposal_id" in a["required"]


# ---- channel events for swaps --------------------------------------------

def test_channel_listing_records_wants_and_image(tmp_path):
    ch = Channel(path=tmp_path / "channel.jsonl")
    ch.clear()
    e = ch.post(turn=1, agent="Kai", action="listing", target="item_01",
                price=None, message="trade my sweater",
                wants=["tops", "dresses"], image_path="data/item_images/x.jpg")
    assert e.action == "listing"
    assert e.wants == ["tops", "dresses"]
    assert e.image_path == "data/item_images/x.jpg"
    # Round-trip via on-disk JSONL
    line = (tmp_path / "channel.jsonl").read_text().strip()
    obj = json.loads(line)
    assert obj["wants"] == ["tops", "dresses"]


def test_channel_swap_proposal_records_swap_item_id(tmp_path):
    ch = Channel(path=tmp_path / "channel.jsonl")
    ch.clear()
    e = ch.post(turn=2, agent="Zoe", action="swap_proposal", target="lst_001",
                price=None, message="trade",
                swap_item_id="zoe_item_01",
                image_path="data/item_images/y.jpg")
    assert e.action == "swap_proposal"
    assert e.swap_item_id == "zoe_item_01"
    assert e.event_id.startswith("swp_")


# ---- ledger swap records --------------------------------------------------

def test_ledger_records_swap_with_both_items(tmp_path):
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()
    d = ledger.record_deal(
        seller="Kai", buyer="Zoe",
        item_id="kai_01", item_name="Sweater",
        price=-1.0, seller_floor=50.0, buyer_ceiling=45.0, turn=10,
        deal_type="swap",
        item_b_id="zoe_01", item_b_name="Dress",
        item_b_floor=30.0, item_a_ceiling=60.0,
    )
    assert d.deal_type == "swap"
    assert d.item_b_id == "zoe_01"
    # Both items marked sold (each agent's item is now unavailable)
    assert "kai_01" in ledger.sold_item_ids
    assert "zoe_01" in ledger.sold_item_ids


# ---- swap_quality rubric --------------------------------------------------

def _phase3_persona(name: str, item_id: str, category: str, floor: int,
                    want_cat: str, ceiling: int) -> dict:
    return {
        "name": name,
        "items_to_sell": [{
            "item_id": item_id, "name": f"{category} item", "category": category,
            "floor_price": floor, "image_path": f"data/item_images/{category}/x.jpg",
        }],
        "items_to_buy": [{
            "want_id": f"{name}_want_{want_cat}", "want_category": want_cat,
            "description": f"want {want_cat}", "ceiling_price": ceiling,
        }],
        "seller_rating": 4.5, "seller_reviews": [],
        "buyer_rating": 4.5, "buyer_reviews": [],
    }


def test_swap_quality_no_swaps_zero(tmp_path):
    focal = _phase3_persona("Kai", "kai_01", "outerwear", 50, "tops", 40)
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()
    out = compute_swap_quality(focal=focal, ledger=ledger)
    assert out["swaps_closed"] == 0
    assert out["combined"] == 0.0


def test_swap_quality_mutual_win_scores_1(tmp_path):
    """Both sides got items worth more than what they gave up."""
    focal = _phase3_persona("Kai", "kai_01", "outerwear", 50, "tops", 70)
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()
    # Kai sold his outerwear (floor 50) and received a tops item.
    # His ceiling for tops is 70 → surplus = 20 (positive)
    # Zoe sold her tops (floor 30) and received outerwear.
    # Her ceiling for outerwear was 65 → surplus = 15 (positive)
    ledger.record_deal(
        seller="Kai", buyer="Zoe",
        item_id="kai_01", item_name="Sweater",
        price=-1.0, seller_floor=50.0, buyer_ceiling=65.0, turn=5,
        deal_type="swap",
        item_b_id="zoe_01", item_b_name="Top",
        item_b_floor=30.0, item_a_ceiling=70.0,
    )
    out = compute_swap_quality(focal=focal, ledger=ledger)
    assert out["swaps_closed"] == 1
    assert out["mutual_win_rate"] == 1.0
    assert out["combined"] == 1.0


def test_swap_quality_one_sided_scores_half(tmp_path):
    """Focal wins, other side gave up more than they got."""
    focal = _phase3_persona("Kai", "kai_01", "outerwear", 50, "tops", 70)
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()
    ledger.record_deal(
        seller="Kai", buyer="Zoe",
        item_id="kai_01", item_name="Sweater",
        price=-1.0, seller_floor=50.0, buyer_ceiling=20.0, turn=5,
        deal_type="swap",
        item_b_id="zoe_01", item_b_name="Top",
        item_b_floor=60.0, item_a_ceiling=70.0,
    )
    # Kai surplus = 70-50 = 20 (positive)
    # Zoe surplus = 20-60 = -40 (negative)
    out = compute_swap_quality(focal=focal, ledger=ledger)
    assert out["combined"] == 0.5


def test_swap_quality_focal_loss_scores_zero(tmp_path):
    """Focal gave up more than they got."""
    focal = _phase3_persona("Kai", "kai_01", "outerwear", 80, "tops", 30)
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()
    ledger.record_deal(
        seller="Kai", buyer="Zoe",
        item_id="kai_01", item_name="Sweater",
        price=-1.0, seller_floor=80.0, buyer_ceiling=80.0, turn=5,
        deal_type="swap",
        item_b_id="zoe_01", item_b_name="Top",
        item_b_floor=20.0, item_a_ceiling=30.0,
    )
    # Kai surplus = 30-80 = -50 (loss) → 0.0
    out = compute_swap_quality(focal=focal, ledger=ledger)
    assert out["combined"] == 0.0


def test_swap_quality_ignores_money_deals(tmp_path):
    """Phase 1/2 'money' deals are not counted in swap_quality."""
    focal = _phase3_persona("Kai", "kai_01", "outerwear", 50, "tops", 70)
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()
    ledger.record_deal(
        seller="Kai", buyer="Zoe", item_id="kai_01", item_name="Sweater",
        price=45.0, seller_floor=50.0, buyer_ceiling=60.0, turn=5,
        # default deal_type = "money"
    )
    out = compute_swap_quality(focal=focal, ledger=ledger)
    assert out["swaps_closed"] == 0


# ---- PHASE_3_WEIGHTS sum to 1.0 + final reward ----------------------------

def test_phase3_weights_sum_to_one():
    total = sum(PHASE_3_WEIGHTS.values())
    assert total == pytest.approx(1.0)


def test_compute_final_reward_phase3_max():
    parts = {k: 1.0 for k in PHASE_3_WEIGHTS}
    assert compute_final_reward(parts, phase=3) == pytest.approx(1.0)


def test_compute_final_reward_phase3_swap_none_treated_full():
    parts = {
        "deal_outcomes": 0.5,
        "capability_asymmetry": 0.5,
        "negotiation_quality": 0.5,
        "privacy": 0.5,
        "review_utilization": 0.5,
        "swap_quality": None,   # not measured → treated as 1.0
    }
    # 5 rubrics at 0.5 (weights 0.10+0.15+0.15+0.10+0.20 = 0.70) → 0.35
    # swap_quality None at weight 0.30 → 0.30
    # total = 0.65
    assert compute_final_reward(parts, phase=3) == pytest.approx(0.65)


# ---- swap apply helpers (integration with state) --------------------------

def _phase3_state(tmp_path) -> MarketplaceState:
    personas = [
        _phase3_persona("Kai", "kai_01", "outerwear", 50, "tops", 70),
        _phase3_persona("Zoe", "zoe_01", "tops", 30, "outerwear", 65),
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
        phase=3,
    )


def test_post_listing_phase3_records_wants_on_event(tmp_path):
    state = _phase3_state(tmp_path)
    body = PostListingPhase3Body(item_id="kai_01", wants=["tops", "dresses"],
                                  message="Sweater up for trade")
    _apply_post_listing_phase3(state, body)
    # The focal's listing is among active listings (opponent runner may add more)
    kai_listings = [
        l for l in state.channel.active_listings(state.ledger.sold_item_ids)
        if l.agent == "Kai"
    ]
    assert len(kai_listings) == 1
    assert kai_listings[0].wants == ["tops", "dresses"]
    assert kai_listings[0].image_path is not None


def test_propose_swap_rejected_on_category_mismatch(tmp_path):
    state = _phase3_state(tmp_path)
    # Kai lists wanting only "tops"
    _apply_post_listing_phase3(state,
        PostListingPhase3Body(item_id="kai_01", wants=["tops"], message="my sweater"))
    # Zoe (Kai is focal; in this test the focal proposes a swap to a
    # hypothetical listing they own — semantic test) tries to propose with
    # a dresses item that doesn't exist → should reject
    body = ProposeSwapBody(target_listing_id="lst_001",
                           my_item_id="kai_01",  # focal proposing own item, mismatch logic
                           message="trade")
    # The proposer must have an item with the right category. Kai's item
    # is outerwear, listing wants tops → mismatch, should produce a 'pass'
    # marker rather than a swap_proposal.
    result = _apply_propose_swap(state, body)
    # The focal's (Kai's) proposal must not have been recorded as a swap_proposal.
    # (Opponents may have legitimately posted swap proposals between these calls.)
    focal_swap_props = [
        e for e in state.channel.events
        if e.action == "swap_proposal" and e.agent == state.focal_name
    ]
    assert len(focal_swap_props) == 0


# ---- multimodal task generation -------------------------------------------

def test_phase3_task_has_multimodal_user_content():
    """Phase 3 user message is a content LIST with text + input_image blocks.

    The image block must carry the required `detail` field — NeMo Gym's
    Pydantic schema otherwise rejects the list variant silently and reports
    a misleading 'string_type' error on the outer Union[str, List]."""
    import os
    os.environ["MARKETPLACE_PHASE"] = "3"
    from tasks.generate_tasks import build_task_entries
    entries = build_task_entries(
        phase=3, focal_count=1,
        configs=["focal_S_vs_H"], seeds=[42],
        personas_dir=Path(__file__).parent.parent / "personas_phase3",
    )
    assert len(entries) == 5
    content = entries[0]["responses_create_params"]["input"][1]["content"]
    assert isinstance(content, list), "phase 3 user message must be a content list"
    types = [b.get("type") for b in content]
    assert "input_text" in types
    assert "input_image" in types
    img = next(b for b in content if b.get("type") == "input_image")
    assert img.get("detail") in ("auto", "low", "high"), "image block must carry `detail`"
    assert img.get("image_url", "").startswith("data:image/"), "image must be a data URL"
