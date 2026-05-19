from unittest.mock import MagicMock, patch

from marketplace.channel import Channel
from marketplace.ledger import Ledger
from resources_server.opponent_runner import OpponentRunner


def _make_personas():
    return [
        {"name": "Alice", "items_to_sell": [], "items_to_buy": [], "style": "x"},
        {"name": "Bob", "items_to_sell": [], "items_to_buy": [], "style": "y"},
        {"name": "Carol", "items_to_sell": [], "items_to_buy": [], "style": "z"},
    ]


def test_opponent_runner_round_robin_picks_each_opponent(tmp_path):
    channel = Channel(path=tmp_path / "ch.jsonl")
    channel.clear()
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()

    personas = _make_personas()
    prompts = {p["name"]: f"system for {p['name']}" for p in personas}

    runner = OpponentRunner(
        focal_name="Alice",
        personas=personas,
        prompts=prompts,
        channel=channel,
        ledger=ledger,
        opponents_model="fake-model",
    )

    picked = [runner._pick_next_opponent() for _ in range(4)]
    names = [p["name"] for p in picked]
    # Round-robin over Bob, Carol (Alice excluded as focal)
    assert names == ["Bob", "Carol", "Bob", "Carol"]


def test_opponent_runner_skips_focal_when_picking(tmp_path):
    channel = Channel(path=tmp_path / "ch.jsonl")
    channel.clear()
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()

    personas = _make_personas()
    prompts = {p["name"]: f"system" for p in personas}

    runner = OpponentRunner("Alice", personas, prompts, channel, ledger, "fake-model")
    for _ in range(10):
        assert runner._pick_next_opponent()["name"] != "Alice"


def test_run_one_turn_writes_an_event_to_channel(tmp_path):
    channel = Channel(path=tmp_path / "ch.jsonl")
    channel.clear()
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()

    personas = _make_personas()
    prompts = {p["name"]: f"system" for p in personas}

    runner = OpponentRunner("Alice", personas, prompts, channel, ledger, "fake-model")

    fake_response = '{"action": "pass", "target": null, "price": null, "message": "skip"}'
    with patch("resources_server.opponent_runner.call_llm", return_value=fake_response):
        runner.run_one_turn(current_turn=1)

    assert len(channel.events) == 1
    assert channel.events[0].action == "pass"
    assert channel.events[0].agent in {"Bob", "Carol"}


def test_run_n_turns_executes_correct_count(tmp_path):
    channel = Channel(path=tmp_path / "ch.jsonl")
    channel.clear()
    ledger = Ledger(path=tmp_path / "deals.json")
    ledger.clear()

    personas = _make_personas()
    prompts = {p["name"]: f"system" for p in personas}

    runner = OpponentRunner("Alice", personas, prompts, channel, ledger, "fake-model")
    fake_response = '{"action": "pass", "target": null, "price": null, "message": "skip"}'
    with patch("resources_server.opponent_runner.call_llm", return_value=fake_response):
        runner.run_n_turns(n=3, starting_turn=1)

    assert len(channel.events) == 3
