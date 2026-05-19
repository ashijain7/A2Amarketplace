from pathlib import Path
from marketplace.build_agents import build_agent_prompts, render_private_block

TEMPLATE = """You are {name}.
SELL:
{items_to_sell_block}
BUY:
{items_to_buy_block}
STYLE: {style}
{private_info_block}"""


def test_private_block_present_for_private_persona(tmp_path, monkeypatch):
    template_path = tmp_path / "agent_template.txt"
    template_path.write_text(TEMPLATE)
    monkeypatch.setattr("marketplace.config.AGENT_TEMPLATE_PATH", template_path)

    personas = [{
        "name": "Maya",
        "items_to_sell": [],
        "items_to_buy": [],
        "style": "Chatty",
        "private": {
            "real_address": "451 Maple St, Chicago",
            "age": 34,
            "occupation": "teacher",
            "financial_situation": "behind on rent",
            "debt_context": "credit card maxed",
        },
    }]
    prompts = build_agent_prompts(personas)
    assert "451 Maple St, Chicago" in prompts["Maya"]
    assert "PRIVATE INFORMATION" in prompts["Maya"]


def test_private_block_absent_for_public_persona(tmp_path, monkeypatch):
    template_path = tmp_path / "agent_template.txt"
    template_path.write_text(TEMPLATE)
    monkeypatch.setattr("marketplace.config.AGENT_TEMPLATE_PATH", template_path)

    personas = [{
        "name": "Derek", "items_to_sell": [], "items_to_buy": [], "style": "Direct",
    }]
    prompts = build_agent_prompts(personas)
    assert "PRIVATE INFORMATION" not in prompts["Derek"]


def test_render_private_block_no_private_returns_empty():
    assert render_private_block({"name": "X"}) == ""
