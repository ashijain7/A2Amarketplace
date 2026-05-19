from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from resources_server.app import build_app
from marketplace.scheduler import RunResult


def test_run_marketplace_endpoint_returns_full_result(tmp_path, monkeypatch):
    fake_personas = [
        {"name": f"P{i}",
         "items_to_sell": [{"item_id": f"item_{i}", "name": "x", "floor_price": 10}],
         "items_to_buy": [{"want_id": f"w_{i}", "description": "y", "ceiling_price": 20}],
         "style": "x"}
        for i in range(10)
    ]
    monkeypatch.setattr("resources_server.app.load_persona_set", lambda name: fake_personas)
    monkeypatch.setattr("marketplace.config.PERSONAS_DIR", tmp_path)

    def fake_loop(*args, **kwargs):
        return RunResult(stop_reason="all_agents_done", turns_used=7)

    with patch("resources_server.app.run_marketplace_loop", side_effect=fake_loop):
        with patch("marketplace.agent.call_llm", return_value='{"action":"pass"}'):
            client = TestClient(build_app())
            r = client.post(
                "/run_marketplace",
                json={"persona_set": "set_03", "model_config": "mixed", "seed": 42},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert "deals" in body
            assert "channel_log" in body
            assert "per_agent_gains" in body
            assert body["turns_used"] == 7
            assert body["stop_reason"] == "all_agents_done"
            assert set(body["per_agent_gains"]) == {f"P{i}" for i in range(10)}


def test_run_marketplace_rejects_bad_config(monkeypatch):
    monkeypatch.setattr("resources_server.app.load_persona_set", lambda name: [{"name":"X"}])
    client = TestClient(build_app())
    r = client.post(
        "/run_marketplace",
        json={"persona_set": "set_03", "model_config": "BAD", "seed": 42},
    )
    assert r.status_code == 400
