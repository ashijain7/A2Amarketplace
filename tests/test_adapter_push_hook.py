import json
import types
from pathlib import Path

import adapter
import platform_export


def test_run_live_calls_push(monkeypatch, tmp_path):
    calls = {}

    # Stub every heavy side-effect of run_live: no env.yaml, no stack, no rollout.
    monkeypatch.setattr(adapter, "reset_env_yaml", lambda *a, **k: None)
    monkeypatch.setattr(adapter, "clear_session_scratch", lambda *a, **k: None)

    out_dir = tmp_path / "run"
    out_dir.mkdir()
    monkeypatch.setattr(adapter, "prepare_output_dir", lambda run_id: out_dir)
    monkeypatch.setattr(adapter, "make_run_id", lambda plan, now=None: "run_test")
    monkeypatch.setattr(adapter, "build_task_file",
                        lambda *a, **k: (out_dir / "task.jsonl", ["Kai"]))

    # subprocess.run: pretend both the restart AND ng_collect succeeded, and
    # write a rollouts.jsonl so run_live proceeds to extract_results.
    def fake_subprocess_run(cmd, **k):
        (out_dir / "rollouts.jsonl").write_text(
            json.dumps({"metadata": {"set_id": "set_01", "focal_persona": "Kai"},
                        "reward": 0.3, "rubric_scores": {}, "deals": [], "channel_events": []}) + "\n")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(adapter.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(adapter, "split_rollouts_by_set", lambda *a, **k: ["rollouts_set_01.jsonl"])

    def fake_push(result, run_id):
        calls["result"] = result
        calls["run_id"] = run_id
        return 1

    monkeypatch.setattr(platform_export, "push_to_platform", fake_push)

    plan = adapter.build_plan(types.SimpleNamespace(
        phase="market_deal", set="01", focal="sonnet", opponent="gemini",
        max_turns=20, seed=42))
    adapter.run_live(plan)

    assert calls["run_id"] == "run_test"
    assert calls["result"]["mean_reward"] == 0.3
