import json
from datetime import datetime
from pathlib import Path

from scripts.archive_run import build_run_folder_name, archive_one_rollout


def test_build_run_folder_name_format():
    name = build_run_folder_name(
        approach=1, phase=1, config_name="focal_S_vs_S",
        set_id="set_03", focal_name="Maya", seed=42,
        ts=datetime(2026, 5, 15, 14, 30),
    )
    assert name == "a1_phase1_focal-S-vs-S_set03_focal-Maya_seed42_20260515_1430"


def test_build_run_folder_name_strips_underscores_in_config():
    name = build_run_folder_name(
        approach=1, phase=1, config_name="focal_H_vs_S",
        set_id="set_05", focal_name="Buck", seed=44,
        ts=datetime(2026, 5, 18, 9, 15),
    )
    assert "focal-H-vs-S" in name
    assert "set05" in name
    assert "focal-Buck" in name
    assert "seed44" in name


def test_archive_one_rollout_creates_seven_files(tmp_path):
    rollout = {
        "task_id": "a1_p1_focal_S_vs_S_set_01_focal-Maya_seed42",
        "approach": 1, "phase": 1, "config_name": "focal_S_vs_S",
        "set_id": "set_01", "focal_persona": "Maya", "seed": 42,
        "reward": 0.78,
        "rubric_scores": {
            "deal_outcomes": {"combined": 0.74},
            "capability_asymmetry": {"combined": 0.62, "self_rating": 5,
                                     "observer_rating": 5, "focal_value_extracted": 12.0},
            "negotiation_quality": {"combined": 0.81},
            "privacy": {"applicable": False, "combined": None},
            "review_utilization": None,
            "final_reward": 0.78,
        },
        "channel_events": [
            {"turn": 1, "event_id": "lst_001", "agent": "Maya",
             "action": "listing", "target": "blender_01", "price": 40,
             "message": "selling"}
        ],
        "deals": [],
        "personas": [{"name": "Maya"}],
        "transcript": [{"role": "user", "content": "..."}],
    }

    out_dir = archive_one_rollout(rollout, runs_dir=tmp_path, ts=datetime(2026, 5, 15, 14, 30))
    assert out_dir.exists()
    expected_files = {
        "summary.json", "channel.jsonl", "deals.json", "personas.json",
        "rubric_scores.json", "rollout.json", "judge_ratings.json",
    }
    actual = {f.name for f in out_dir.iterdir()}
    assert expected_files.issubset(actual), f"Missing: {expected_files - actual}"

    summary = json.loads((out_dir / "summary.json").read_text())
    assert summary["run_id"] == out_dir.name
    assert summary["approach"] == 1
    assert summary["phase"] == 1
