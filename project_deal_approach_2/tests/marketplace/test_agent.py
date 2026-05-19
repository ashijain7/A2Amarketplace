from unittest.mock import patch
from marketplace.agent import run_turn, AgentDecision, VALID_ACTIONS
from marketplace.channel import Channel
from marketplace.ledger import Ledger


def test_valid_actions_set():
    assert VALID_ACTIONS == {"listing", "offer", "counter", "accept", "decline", "pass"}


def test_run_turn_returns_decision_with_model_passed(tmp_path):
    persona = {
        "name": "Maya",
        "items_to_sell": [{"item_id": "blender_01", "name": "Blender", "floor_price": 35}],
        "items_to_buy": [],
        "style": "Friendly",
    }
    ch = Channel(path=tmp_path / "channel.jsonl"); ch.clear()
    lg = Ledger(path=tmp_path / "deals.json"); lg.clear()

    fake_text = '{"action":"listing","target":"blender_01","price":35,"message":"hi"}'
    with patch("marketplace.agent.call_llm", return_value=fake_text) as mock_call:
        decision = run_turn(
            agent_name="Maya",
            system_prompt="sys",
            persona=persona,
            channel=ch,
            ledger=lg,
            model="anthropic/claude-haiku-4-5",
        )
    assert isinstance(decision, AgentDecision)
    assert decision.action == "listing"
    assert mock_call.call_args.kwargs["model"] == "anthropic/claude-haiku-4-5"


def test_unparseable_response_returns_pass(tmp_path):
    persona = {"name": "Maya", "items_to_sell": [], "items_to_buy": [], "style": ""}
    ch = Channel(path=tmp_path / "channel.jsonl"); ch.clear()
    lg = Ledger(path=tmp_path / "deals.json"); lg.clear()
    with patch("marketplace.agent.call_llm", return_value="not json"):
        decision = run_turn("Maya", "sys", persona, ch, lg, model="haiku")
    assert decision.action == "pass"
