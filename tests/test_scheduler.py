import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.channel import Channel
from project_deal_poc.ledger import Ledger
from project_deal_poc.agent import AgentDecision
from project_deal_poc.scheduler import _validate_and_apply


def make_channel():
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    c = Channel(path=Path(tmp.name))
    c.clear()
    return c


def make_ledger():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    l = Ledger(path=Path(tmp.name))
    l.clear()
    return l


PERSONAS = {
    "Dexter": {
        "name": "Dexter",
        "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
        "items_to_buy": [{"want_id": "headphones_w1", "description": "Headphones", "ceiling_price": 50}],
        "style": "Direct.",
    }
}


def test_invalid_action_posts_reject_not_pass():
    """When an action is invalid, scheduler should post a reject event, not a pass."""
    c = make_channel()
    l = make_ledger()

    decision = AgentDecision(
        action="listing",
        target="nonexistent_item",
        price=100,
        message="Listing a fake item",
        raw={},
    )

    _validate_and_apply(decision, "Dexter", PERSONAS["Dexter"], PERSONAS, c, l, turn=1)

    assert len(c.events) == 1
    assert c.events[0].action == "reject", f"Expected reject, got {c.events[0].action}"
    assert c.events[0].event_id.startswith("rjt_")


def test_rejected_action_does_not_increment_stall_counter():
    """A rejected action should not count as a stall turn."""
    c = make_channel()
    l = make_ledger()

    # Invalid listing → gets rejected
    decision = AgentDecision(
        action="listing",
        target="fake_item",
        price=100,
        message="fake",
        raw={},
    )
    accepted, _ = _validate_and_apply(decision, "Dexter", PERSONAS["Dexter"], PERSONAS, c, l, turn=1)

    assert accepted is False
    assert decision.action != "pass", "original decision was not a pass — stall should not increment"


def test_genuine_pass_should_be_identified_as_stall():
    """A genuine pass decision should increment the stall counter."""
    c = make_channel()
    l = make_ledger()

    decision = AgentDecision(
        action="pass",
        target=None,
        price=None,
        message="(pass)",
        raw={},
    )
    accepted, _ = _validate_and_apply(decision, "Dexter", PERSONAS["Dexter"], PERSONAS, c, l, turn=1)

    assert accepted is True
    assert decision.action == "pass", "genuine pass should be identified for stall tracking"


def test_offer_at_declined_price_is_rejected():
    """An offer at or below a previously declined price should be rejected."""
    c = make_channel()
    l = make_ledger()

    personas = {
        "Dexter": {
            "name": "Dexter",
            "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
            "items_to_buy": [],
            "style": "Direct.",
        },
        "Mika": {
            "name": "Mika",
            "items_to_sell": [],
            "items_to_buy": [{"want_id": "camera_w1", "description": "Camera", "ceiling_price": 70}],
            "style": "Friendly.",
        },
    }

    # Dexter lists camera
    list_decision = AgentDecision("listing", "camera_01", 65, "Camera $65", {})
    _validate_and_apply(list_decision, "Dexter", personas["Dexter"], personas, c, l, turn=1)

    # Mika offers $50
    offer_decision = AgentDecision("offer", "lst_001", 50, "Offering $50", {})
    _validate_and_apply(offer_decision, "Mika", personas["Mika"], personas, c, l, turn=2)

    # Dexter declines
    decline_decision = AgentDecision("decline", "off_002", None, "Too low", {})
    _validate_and_apply(decline_decision, "Dexter", personas["Dexter"], personas, c, l, turn=3)

    # Mika tries to offer $50 again — should be rejected
    reoffer_decision = AgentDecision("offer", "lst_001", 50, "Still $50?", {})
    accepted, reason = _validate_and_apply(reoffer_decision, "Mika", personas["Mika"], personas, c, l, turn=4)

    assert accepted is False, "re-offer at declined price should be rejected"
    assert "declined" in reason.lower(), f"rejection reason should mention declined: {reason}"


def test_offer_above_declined_price_is_allowed():
    """An offer above a previously declined price should be allowed."""
    c = make_channel()
    l = make_ledger()

    personas = {
        "Dexter": {
            "name": "Dexter",
            "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
            "items_to_buy": [],
            "style": "Direct.",
        },
        "Mika": {
            "name": "Mika",
            "items_to_sell": [],
            "items_to_buy": [{"want_id": "camera_w1", "description": "Camera", "ceiling_price": 70}],
            "style": "Friendly.",
        },
    }

    # Dexter lists
    _validate_and_apply(AgentDecision("listing", "camera_01", 65, "Camera", {}),
                        "Dexter", personas["Dexter"], personas, c, l, turn=1)
    # Mika offers $50
    _validate_and_apply(AgentDecision("offer", "lst_001", 50, "$50", {}),
                        "Mika", personas["Mika"], personas, c, l, turn=2)
    # Dexter declines
    _validate_and_apply(AgentDecision("decline", "off_002", None, "No", {}),
                        "Dexter", personas["Dexter"], personas, c, l, turn=3)
    # Mika offers $60 — higher than declined $50, should be accepted
    accepted, _ = _validate_and_apply(AgentDecision("offer", "lst_001", 60, "$60", {}),
                                       "Mika", personas["Mika"], personas, c, l, turn=4)

    assert accepted is True, "offer above declined price should be allowed"


from project_deal_poc.scheduler import _pick_next_agent_rotation


def test_rotation_gives_each_agent_one_turn_per_round():
    """Every agent should appear once before any agent appears twice."""
    agents = ["Alice", "Bob", "Carol", "Dave"]
    queue = []
    seen_in_round: list[str] = []

    for _ in range(len(agents) * 3):  # 3 full rounds
        agent, queue = _pick_next_agent_rotation(agents, queue)
        assert agent not in seen_in_round, f"{agent} appeared twice before round reset"
        seen_in_round.append(agent)
        if len(seen_in_round) == len(agents):
            seen_in_round = []  # round complete, reset


def test_rotation_skips_finished_agents():
    """Agents no longer in active list should not be returned."""
    agents_full = ["Alice", "Bob", "Carol"]
    agents_reduced = ["Alice", "Carol"]  # Bob finished mid-round
    queue = []

    # Run two turns from full list to populate queue
    _, queue = _pick_next_agent_rotation(agents_full, queue)
    _, queue = _pick_next_agent_rotation(agents_full, queue)

    # Now Bob finishes — next picks should only return Alice or Carol
    for _ in range(6):
        agent, queue = _pick_next_agent_rotation(agents_reduced, queue)
        assert agent in agents_reduced, f"Finished agent returned: {agent}"
