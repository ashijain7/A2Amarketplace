import json
import types

import adapter
import platform_export
import pytest


@pytest.fixture
def stubbed_run(monkeypatch, tmp_path):
    """run_live with every heavy side-effect stubbed: no env.yaml, no stack, no LLM."""
    calls = {}

    monkeypatch.setattr(adapter, "reset_env_yaml", lambda *a, **k: None)
    monkeypatch.setattr(adapter, "clear_session_scratch", lambda *a, **k: None)

    out_dir = tmp_path / "run"
    out_dir.mkdir()
    monkeypatch.setattr(adapter, "prepare_output_dir", lambda run_id: out_dir)
    monkeypatch.setattr(adapter, "make_run_id", lambda plan, now=None: "run_test")
    monkeypatch.setattr(adapter, "build_task_file",
                        lambda *a, **k: (out_dir / "task.jsonl", ["Kai"]))

    def fake_subprocess_run(cmd, **k):
        (out_dir / "rollouts.jsonl").write_text(
            json.dumps({"metadata": {"set_id": "set_01", "focal_persona": "Kai"},
                        "reward": 0.3, "rubric_scores": {}, "deals": [],
                        "channel_events": []}) + "\n")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(adapter.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(adapter, "split_rollouts_by_set",
                        lambda *a, **k: ["rollouts_set_01.jsonl"])

    def fake_push(result, run_id):
        calls["result"] = result
        calls["run_id"] = run_id
        return 1

    monkeypatch.setattr(platform_export, "push_to_platform", fake_push)
    return calls, out_dir


def _plan(**over):
    args = dict(phase="market_deal", set="01", focal="sonnet", opponent="gemini",
                max_turns=20, seed=42)
    args.update(over)
    return adapter.build_plan(types.SimpleNamespace(**args))


def test_a_run_is_not_recorded_unless_asked(stubbed_run):
    """The default: an exploratory run reaches the platform never."""
    calls, _ = stubbed_run

    adapter.run_live(_plan())

    assert calls == {}, "an unrecorded run must not push anything"


def test_run_live_pushes_when_recording(stubbed_run):
    calls, _ = stubbed_run

    adapter.run_live(_plan(record=True))

    assert calls["run_id"] == "run_test"
    assert calls["result"]["mean_reward"] == 0.3


def test_a_recorded_run_reports_how_long_it_took(stubbed_run):
    """Otherwise the platform fills the Duration column with a guess (steps * 0.7)."""
    calls, _ = stubbed_run

    adapter.run_live(_plan(record=True))

    assert isinstance(calls["result"]["duration_s"], float)
    assert calls["result"]["duration_s"] >= 0
