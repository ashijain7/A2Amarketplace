"""Tests for MarketplaceServer (NeMo Gym SimpleResourcesServer parity wrapper).

Mirrors Approach 2's MarketplaceServer pattern: a thin wrapper around the
existing build_app() / verifiers so `ng_run` can drive A1's Resources Server
directly. The 6 tool endpoints from build_app() must be registered, and the
class must be a SimpleResourcesServer subclass.
"""

from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nemo_gym.base_resources_server import SimpleResourcesServer
from resources_server.app import MarketplaceServer, MarketplaceState


def _bootstrap_state(tmp_path: Path) -> MarketplaceState:
    personas = [
        {"name": "Alice", "items_to_sell": [
            {"item_id": "blender_01", "name": "Blender", "floor_price": 30}],
         "items_to_buy": [], "style": "x"},
        {"name": "Bob", "items_to_sell": [],
         "items_to_buy": [
             {"want_id": "blender_w1", "description": "blender",
              "ceiling_price": 60}],
         "style": "y"},
    ]
    return MarketplaceState(
        focal_name="Alice",
        personas=personas,
        opponents_model="fake-model",
        focal_model="fake-model",
        judge_model="fake-judge",
        seed=42,
        set_id="set_01",
        config_name="focal_S_vs_S",
        data_dir=tmp_path,
    )


def test_marketplace_server_is_subclass_of_simple_resources_server():
    assert issubclass(MarketplaceServer, SimpleResourcesServer)


def test_marketplace_server_can_be_instantiated_for_tests():
    server = MarketplaceServer()
    assert server is not None


def test_setup_webserver_registers_six_tool_endpoints(tmp_path):
    server = MarketplaceServer()
    server.attach_state(_bootstrap_state(tmp_path))

    app = server.setup_webserver()
    assert isinstance(app, FastAPI)

    routes = {r.path for r in app.routes}
    for expected in (
        "/post_listing",
        "/make_offer",
        "/counter_offer",
        "/accept_offer",
        "/reject_offer",
        "/pass",
        "/verify",
    ):
        assert expected in routes, f"missing route {expected}"


def test_setup_webserver_inherits_nemo_gym_lifecycle_endpoints(tmp_path):
    """Verify SimpleResourcesServer's /seed_session, /verify, /aggregate_metrics
    endpoints are inherited (this is the bug the refactor fixes: previously
    setup_webserver() built a fresh FastAPI without calling super())."""
    server = MarketplaceServer()
    app = server.setup_webserver()
    routes = {r.path for r in app.routes}
    for expected in ("/seed_session", "/verify", "/aggregate_metrics"):
        assert expected in routes, f"missing lifecycle route {expected}"


def test_setup_webserver_routes_are_callable(tmp_path):
    server = MarketplaceServer()
    server.attach_state(_bootstrap_state(tmp_path))
    app = server.setup_webserver()
    client = TestClient(app)

    fake = '{"action": "pass", "target": null, "price": null, "message": "ok"}'
    with patch("resources_server.opponent_runner.call_llm", return_value=fake):
        r = client.post("/pass", json={"message": "noop"})
    assert r.status_code == 200


async def test_verify_extracts_run_result_from_body(tmp_path):
    """The async verify() entrypoint should call the existing verifier stack
    against the attached MarketplaceState."""
    server = MarketplaceServer()
    server.attach_state(_bootstrap_state(tmp_path))

    class _Body:
        run_result = {}
        metadata = {}

    with patch("resources_server.verifiers.call_llm", return_value="4"):
        out = await server.verify(_Body())
    assert "reward" in out
    assert 0.0 <= out["reward"] <= 1.0
    assert "rubric_scores" in out


def test_seed_session_then_tool_call_flow(tmp_path, monkeypatch):
    """End-to-end: POST /seed_session, then call a tool endpoint, then verify
    that state was scoped to the test's session_id cookie."""
    import json as _json

    personas = [
        {"name": "Alice", "items_to_sell": [
            {"item_id": "blender_01", "name": "Blender", "floor_price": 30}],
         "items_to_buy": [], "style": "x"},
        {"name": "Bob", "items_to_sell": [],
         "items_to_buy": [
             {"want_id": "blender_w1", "description": "blender",
              "ceiling_price": 60}],
         "style": "y"},
    ]
    personas_path = tmp_path / "personas.json"
    personas_path.write_text(_json.dumps(personas))

    # Redirect data dir so the server doesn't clobber the real data/.
    from marketplace import config as mp_config
    monkeypatch.setattr(mp_config, "DATA_DIR", tmp_path / "data")

    server = MarketplaceServer()
    app = server.setup_webserver()
    client = TestClient(app)

    seed_body = {
        "metadata": {
            "task_id": "t1", "phase": 1, "approach": 1,
            "config_name": "focal_S_vs_S", "set_id": "set_01",
            "focal_persona": "Alice", "seed": 42,
            "personas_path": str(personas_path),
        }
    }
    r = client.post("/seed_session", json=seed_body)
    assert r.status_code == 200, r.text

    # After /seed_session, the TestClient has a session_id cookie. A tool
    # call must find the per-session MarketplaceState.
    fake = '{"action": "pass", "target": null, "price": null, "message": "ok"}'
    with patch("resources_server.opponent_runner.call_llm", return_value=fake):
        r = client.post("/pass", json={"message": "noop"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "active_listings" in body
    assert "recent_events" in body
