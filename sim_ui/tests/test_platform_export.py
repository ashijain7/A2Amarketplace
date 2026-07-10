import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import platform_export


def _run_capture_server(captured):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n)
            captured.append({"auth": self.headers.get("Authorization"),
                             "body": json.loads(body)})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"success": true}')

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _sample_result():
    return {
        "phase": "market_deal",
        "focal_model": "anthropic/claude-sonnet-4-5",
        "opponents_model": "google/gemini-3.1-pro-preview",
        "mean_reward": 0.30,
        "per_set": [
            {"set_id": "set_01", "focal_persona": "Kai", "reward": 0.30,
             "rubric_breakdown": {"deal_outcomes": 0.1, "negotiation_quality": 0.7},
             "num_deals": 3, "num_channel_events": 40},
        ],
    }


def test_converts_one_record_per_set():
    recs = platform_export.result_to_platform_records(
        _sample_result(), env_name="project_deal_marketplace", run_id="run_abc")
    assert len(recs) == 1
    r = recs[0]
    assert r["environment_name"] == "project_deal_marketplace"
    assert r["total_reward"] == 0.30
    assert r["scenario_name"] == "set_01"
    assert r["policy_name"] == "anthropic/claude-sonnet-4-5"
    assert r["steps"][0]["reward_breakdown"] == {"deal_outcomes": 0.1, "negotiation_quality": 0.7}
    assert r["final_outcome"]["run_id"] == "run_abc"
    assert r["final_outcome"]["num_deals"] == 3


def test_missing_reward_defaults_to_zero():
    result = _sample_result()
    result["per_set"][0]["reward"] = None
    recs = platform_export.result_to_platform_records(result, "e", "r")
    assert recs[0]["total_reward"] == 0.0


def test_push_noop_when_env_unset(monkeypatch):
    monkeypatch.delenv("RLEAAS_CALLBACK_URL", raising=False)
    monkeypatch.delenv("RLEAAS_TOKEN", raising=False)
    assert platform_export.push_to_platform(_sample_result(), "run_x") == 0


def test_push_posts_records_with_token(monkeypatch):
    captured = []
    srv = _run_capture_server(captured)
    host, port = srv.server_address
    monkeypatch.setenv("RLEAAS_CALLBACK_URL", f"http://{host}:{port}/api/rollouts")
    monkeypatch.setenv("RLEAAS_TOKEN", "secret-123")
    monkeypatch.setenv("RLEAAS_ENV_NAME", "project_deal_marketplace")
    n = platform_export.push_to_platform(_sample_result(), "run_x")
    srv.shutdown()
    assert n == 1
    assert captured[0]["auth"] == "Bearer secret-123"
    assert captured[0]["body"]["environment_name"] == "project_deal_marketplace"
    assert captured[0]["body"]["final_outcome"]["run_id"] == "run_x"


def test_push_never_raises_on_malformed_result(monkeypatch):
    monkeypatch.setenv("RLEAAS_CALLBACK_URL", "http://127.0.0.1:1/none")
    monkeypatch.setenv("RLEAAS_TOKEN", "t")
    # per_set is not a list -> conversion would blow up; must be swallowed -> 0
    assert platform_export.push_to_platform({"per_set": "not-a-list"}, "run_x") == 0


def test_none_rubric_values_dropped():
    result = _sample_result()
    result["per_set"][0]["rubric_breakdown"] = {
        "deal_outcomes": 0.1, "swap_quality": None, "transactional_integrity": None}
    recs = platform_export.result_to_platform_records(result, "e", "r")
    bd = recs[0]["steps"][0]["reward_breakdown"]
    assert bd == {"deal_outcomes": 0.1}
    assert all(v is not None for v in bd.values())
