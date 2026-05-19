from unittest.mock import patch, MagicMock
from marketplace.llm import call_llm, parse_json_response


def test_call_llm_passes_model_through():
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"action":"pass"}'))]
    with patch("marketplace.llm.get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = fake_resp
        out = call_llm(system="s", user="u", model="anthropic/claude-haiku-4-5")
        assert out == '{"action":"pass"}'
        kwargs = mock_client.return_value.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "anthropic/claude-haiku-4-5"


def test_parse_json_response_strips_fences():
    text = "```json\n{\"action\": \"pass\"}\n```"
    assert parse_json_response(text) == {"action": "pass"}
