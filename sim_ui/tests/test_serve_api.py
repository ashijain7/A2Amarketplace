import pytest
from fastapi.testclient import TestClient

from sim_ui import serve, run_api


@pytest.fixture
def client():
    return TestClient(serve.build_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_run_ok(client, monkeypatch):
    monkeypatch.setattr(run_api, "run_blocking",
                        lambda params: {"mean_reward": 0.5, "run_id": "r1"})
    r = client.post("/api/run", json={"phase": "market_deal", "set": "01",
                                      "focal": "sonnet", "opponent": "gemini"})
    assert r.status_code == 200
    assert r.json()["mean_reward"] == 0.5


def test_run_busy_returns_409(client, monkeypatch):
    def _busy(params):
        raise run_api.RunInProgress("run in progress")
    monkeypatch.setattr(run_api, "run_blocking", _busy)
    r = client.post("/api/run", json={"phase": "market_deal", "set": "01",
                                      "focal": "s", "opponent": "g"})
    assert r.status_code == 409


def test_run_failed_returns_500_with_tail(client, monkeypatch):
    def _fail(params):
        raise run_api.RunFailed("adapter exited 2", "boom-tail")
    monkeypatch.setattr(run_api, "run_blocking", _fail)
    r = client.post("/api/run", json={"phase": "market_deal", "set": "01",
                                      "focal": "s", "opponent": "g"})
    assert r.status_code == 500
    assert r.json()["log_tail"] == "boom-tail"


def test_static_still_served(client):
    # The "/" static mount must still work after /api/* routes are registered.
    r = client.get("/")
    assert r.status_code == 200


def test_port_precedence(monkeypatch):
    monkeypatch.setenv("PORT", "7001")
    monkeypatch.setenv("A2A_UI_PORT", "8001")
    assert serve._port() == 7001
    monkeypatch.delenv("PORT", raising=False)
    assert serve._port() == 8001
    monkeypatch.delenv("A2A_UI_PORT", raising=False)
    assert serve._port() == 8000
