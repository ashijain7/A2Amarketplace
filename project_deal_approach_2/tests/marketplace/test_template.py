from pathlib import Path
from marketplace import config


def test_agent_template_has_private_placeholder():
    text = Path(config.AGENT_TEMPLATE_PATH).read_text()
    assert "{private_info_block}" in text
    assert "{name}" in text
    assert "{items_to_sell_block}" in text
    assert "{items_to_buy_block}" in text
    assert "{style}" in text


def test_agent_template_renders_with_empty_private():
    text = Path(config.AGENT_TEMPLATE_PATH).read_text()
    rendered = text.format(
        name="Maya",
        items_to_sell_block="  (none)",
        items_to_buy_block="  (none)",
        style="chatty",
        private_info_block="",
    )
    assert "Maya" in rendered
