from unittest.mock import patch
from marketplace.scheduler import run_marketplace_loop, RunResult
from marketplace.channel import Channel
from marketplace.ledger import Ledger


def test_run_marketplace_loop_passes_per_agent_model(tmp_path):
    personas = [
        {"name": "Maya", "items_to_sell": [], "items_to_buy": [], "style": "x"},
        {"name": "Derek", "items_to_sell": [], "items_to_buy": [], "style": "y"},
    ]
    prompts = {"Maya": "p1", "Derek": "p2"}
    models = {"Maya": "anthropic/claude-sonnet-4-5", "Derek": "anthropic/claude-haiku-4-5"}

    ch = Channel(path=tmp_path / "channel.jsonl"); ch.clear()
    lg = Ledger(path=tmp_path / "deals.json"); lg.clear()

    # With no items/wants every agent is "done" immediately -> loop ends instantly.
    result = run_marketplace_loop(
        personas=personas, agent_prompts=prompts,
        models_by_agent=models,
        channel=ch, ledger=lg, seed=42,
    )
    assert isinstance(result, RunResult)
    assert result.stop_reason == "all_agents_done"
    assert result.turns_used == 0


def test_run_marketplace_loop_uses_correct_model_per_agent(tmp_path):
    personas = [
        {"name": "Maya",
         "items_to_sell": [{"item_id": "blender_01", "name": "B", "floor_price": 10}],
         "items_to_buy": [], "style": "x"},
    ]
    prompts = {"Maya": "p"}
    models = {"Maya": "anthropic/claude-sonnet-4-5"}
    ch = Channel(path=tmp_path / "channel.jsonl"); ch.clear()
    lg = Ledger(path=tmp_path / "deals.json"); lg.clear()

    fake = '{"action":"pass","target":null,"price":null,"message":"."}'
    with patch("marketplace.agent.call_llm", return_value=fake) as mock_call:
        run_marketplace_loop(
            personas=personas, agent_prompts=prompts,
            models_by_agent=models, channel=ch, ledger=lg, seed=1,
            stall_limit=2,
        )
    used_models = [c.kwargs["model"] for c in mock_call.call_args_list]
    assert used_models, "expected at least one call"
    assert all(m == "anthropic/claude-sonnet-4-5" for m in used_models)
