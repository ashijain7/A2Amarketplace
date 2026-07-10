import json
import sys
from unittest.mock import Mock

import pytest

from sim_ui import run_api


def _fake_adapter(tmp_path, result_dir):
    result_dir.mkdir(exist_ok=True)
    (result_dir / "result.json").write_text(json.dumps(
        {"mean_reward": 0.42, "focal_model": "m", "opponents_model": "o",
         "per_set": [{"set_id": "set_01", "reward": 0.42}]}))
    fake = tmp_path / "fake_adapter.py"
    fake.write_text("import sys; sys.exit(0)\n")
    return [sys.executable, str(fake)]


def test_run_blocking_returns_reward(tmp_path):
    result_dir = tmp_path / "run_id_dir"
    cmd = _fake_adapter(tmp_path, result_dir)
    params = {"phase": "market_deal", "set": "01", "focal": "sonnet",
              "opponent": "gemini", "max_turns": 20, "seed": 42,
              "_cmd_override": cmd, "_result_dir": str(result_dir)}
    out = run_api.run_blocking(params)
    assert out["mean_reward"] == 0.42
    assert out["run_id"] == "run_id_dir"


def test_run_blocking_raises_on_failure(tmp_path):
    result_dir = tmp_path / "run_fail"
    result_dir.mkdir()
    fake = tmp_path / "boom.py"
    fake.write_text("import sys; sys.exit(2)\n")
    params = {"phase": "market_deal", "set": "01", "focal": "sonnet",
              "opponent": "gemini", "max_turns": 20, "seed": 42,
              "_cmd_override": [sys.executable, str(fake)],
              "_result_dir": str(result_dir)}
    with pytest.raises(run_api.RunFailed):
        run_api.run_blocking(params)


def test_run_blocking_busy_raises(tmp_path, monkeypatch):
    # Pretend the single-flight lock is already held.
    mock_lock = Mock()
    mock_lock.acquire.return_value = False
    monkeypatch.setattr(run_api, "_LOCK", mock_lock)
    with pytest.raises(run_api.RunInProgress):
        run_api.run_blocking({"phase": "market_deal", "set": "01",
                              "focal": "s", "opponent": "g",
                              "max_turns": 20, "seed": 42})


def test_run_blocking_timeout_raises(tmp_path, monkeypatch):
    fake = tmp_path / "sleeper.py"
    fake.write_text("import time; time.sleep(30)\n")
    monkeypatch.setattr(run_api, "_cap_seconds", lambda params: 0)  # cap = instant
    params = {"phase": "market_deal", "set": "01", "focal": "s", "opponent": "g",
              "max_turns": 20, "seed": 42,
              "_cmd_override": [sys.executable, str(fake)],
              "_result_dir": str(tmp_path)}
    with pytest.raises(run_api.RunFailed) as ei:
        run_api.run_blocking(params)
    assert "time limit" in str(ei.value)


def test_run_blocking_captures_log_tail_on_failure(tmp_path, monkeypatch):
    # Exercise the REAL (non-override) path: build_adapter_cmd -> a failing script
    # that writes a marker to stderr; run_blocking must redirect it to adapter.log
    # and surface it in RunFailed.log_tail. Stack checks/teardown are mocked so no
    # real ng_run is touched.
    fake = tmp_path / "failing.py"
    fake.write_text("import sys; print('BOOM-MARKER', file=sys.stderr); sys.exit(2)\n")
    monkeypatch.setattr(run_api.live_runner, "_build_adapter_cmd",
                        lambda p: [sys.executable, str(fake)])
    monkeypatch.setattr(run_api, "_stack_running", lambda: False)
    monkeypatch.setattr(run_api.live_runner, "_teardown_stack", lambda: None)
    params = {"phase": "market_deal", "set": "01", "focal": "s", "opponent": "g",
              "max_turns": 20, "seed": 42}
    with pytest.raises(run_api.RunFailed) as ei:
        run_api.run_blocking(params)
    assert "BOOM-MARKER" in ei.value.log_tail
