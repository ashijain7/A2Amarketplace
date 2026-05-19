import json
from pathlib import Path

from analysis.compare import aggregate_runs, write_phase_summary


def _write_summary(folder: Path, config: str, set_id: str, focal: str,
                   reward: float, value_extracted: float):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "summary.json").write_text(json.dumps({
        "run_id": folder.name,
        "approach": 1, "phase": 1,
        "config": {"model_config": config, "persona_set": set_id,
                   "focal_persona": focal},
        "rubric_scores": {
            "deal_outcomes": 0.7,
            "capability_asymmetry": 0.5,
            "negotiation_quality": 0.8,
            "privacy": None,
            "review_utilization": None,
            "final_reward": reward,
        },
        "focal_value_extracted": value_extracted,
        "deal_count": 2,
    }))


def test_aggregate_runs_groups_by_config(tmp_path):
    _write_summary(tmp_path / "r1", "focal_S_vs_S", "set_01", "Maya", 0.8, 10.0)
    _write_summary(tmp_path / "r2", "focal_S_vs_S", "set_01", "Derek", 0.7, 12.0)
    _write_summary(tmp_path / "r3", "focal_H_vs_S", "set_01", "Maya", 0.5, 14.2)
    _write_summary(tmp_path / "r4", "focal_S_vs_H", "set_01", "Maya", 0.9, 31.7)

    agg = aggregate_runs(runs_dir=tmp_path, phase=1)
    assert agg["phase"] == 1
    assert agg["total_rollouts"] == 4
    assert "focal_S_vs_S" in agg["configs"]
    assert agg["configs"]["focal_S_vs_S"]["rollout_count"] == 2


def test_aggregate_runs_computes_asymmetry_delta(tmp_path):
    _write_summary(tmp_path / "r1", "focal_H_vs_S", "set_01", "Maya", 0.5, 14.2)
    _write_summary(tmp_path / "r2", "focal_S_vs_H", "set_01", "Maya", 0.9, 31.7)
    agg = aggregate_runs(runs_dir=tmp_path, phase=1)
    a = agg["asymmetry_test"]
    assert abs(a["focal_S_vs_H_mean_value_extracted"] - 31.7) < 1e-6
    assert abs(a["focal_H_vs_S_mean_value_extracted"] - 14.2) < 1e-6
    assert abs(a["delta"] - 17.5) < 1e-6


def test_write_phase_summary_creates_file(tmp_path):
    _write_summary(tmp_path / "r1", "focal_S_vs_S", "set_01", "Maya", 0.8, 10.0)
    out = tmp_path / "out" / "phase_1_summary.json"
    write_phase_summary(runs_dir=tmp_path, out_path=out, phase=1)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["phase"] == 1
