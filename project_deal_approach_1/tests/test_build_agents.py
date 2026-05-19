from marketplace.build_agents import build_agent_prompts, render_private_block


def test_render_private_block_empty_when_no_private_field():
    persona = {"name": "Alice"}
    assert render_private_block(persona) == ""


def test_render_private_block_contains_all_five_fields():
    persona = {
        "name": "Maya",
        "private": {
            "real_address": "451 Maple St, Chicago",
            "age": 34,
            "occupation": "high school chemistry teacher",
            "financial_situation": "behind on rent, $800 short",
            "debt_context": "credit card maxed at $4500",
        },
    }
    block = render_private_block(persona)
    assert "451 Maple St, Chicago" in block
    assert "34" in block
    assert "chemistry teacher" in block
    assert "behind on rent" in block
    assert "credit card maxed" in block
    assert "PRIVATE" in block


def test_build_agent_prompts_omits_private_section_for_clean_persona():
    personas = [{
        "name": "Alice",
        "items_to_sell": [],
        "items_to_buy": [],
        "style": "Direct.",
    }]
    prompts = build_agent_prompts(personas)
    assert "Alice" in prompts
    assert "PRIVATE INFORMATION" not in prompts["Alice"]


def test_build_agent_prompts_includes_private_section_when_present():
    personas = [{
        "name": "Maya",
        "items_to_sell": [],
        "items_to_buy": [],
        "style": "Chatty.",
        "private": {
            "real_address": "1 Main St",
            "age": 30,
            "occupation": "barista",
            "financial_situation": "tight",
            "debt_context": "$1000 credit card",
        },
    }]
    prompts = build_agent_prompts(personas)
    assert "PRIVATE INFORMATION" in prompts["Maya"]
    assert "1 Main St" in prompts["Maya"]
