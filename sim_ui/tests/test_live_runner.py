import json
import os
import sys
from pathlib import Path

from sim_ui import live_runner


def test_stream_tails_log_and_finishes(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    monkeypatch.setenv("MARKETPLACE_LIVE_LOG", str(log))
    monkeypatch.setattr(live_runner, "LIVE_LOG_PATH", log)

    # A fake "adapter": writes 3 records to the live log, then a result.json, then exits 0.
    result_dir = tmp_path / "run"
    result_dir.mkdir()
    (result_dir / "result.json").write_text(json.dumps({
        "mean_reward": 0.42, "per_set": [{"set_id": "set_01", "reward": 0.42}]
    }))
    fake = tmp_path / "fake_adapter.py"
    fake.write_text(
        "import json,time,os,sys\n"
        "p=os.environ['MARKETPLACE_LIVE_LOG']\n"
        "for r in [{'kind':'seed','focal':'Kai'},"
        "          {'kind':'event','agent':'Kai','action':'listing'},"
        "          {'kind':'reward','reward':0.42}]:\n"
        "    open(p,'a').write(json.dumps(r)+'\\n'); time.sleep(0.05)\n"
    )
    params = {
        "phase": "market_deal", "set": "01", "focal": "sonnet",
        "opponent": "gemini", "max_turns": 20, "seed": 42,
        "_cmd_override": [sys.executable, str(fake)],
        "_result_dir": str(result_dir),
    }
    records = list(live_runner.stream_live_run(params))
    kinds = [r["kind"] for r in records]
    assert kinds[:3] == ["seed", "event", "reward"]
    assert kinds[-1] == "done"
    assert records[-1]["mean_reward"] == 0.42
