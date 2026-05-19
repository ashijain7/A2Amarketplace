import json
from pathlib import Path
from analysis.compare import aggregate_phase_1


def _write_run(root: Path, run_id: str, summary: dict):
    d = root / run_id
    d.mkdir(parents=True)
    (d / "summary.json").write_text(json.dumps(summary))


def test_aggregate_phase_1_groups_by_config(tmp_path):
    base = {
        "approach": 2, "phase": 1,
        "rubric_scores": {
            "deal_outcomes": 0.8, "capability_asymmetry": 0.6,
            "advantage_ratio": None, "negotiation_quality": 0.7,
            "privacy": 1.0, "review_utilization": None, "final_reward": 0.75,
        },
    }
    mixed = {**base, "rubric_scores": {**base["rubric_scores"],
                                        "advantage_ratio": 2.0, "final_reward": 0.6}}
    mixed_b = {**base, "rubric_scores": {**base["rubric_scores"],
                                          "advantage_ratio": 3.0, "final_reward": 0.5}}

    _write_run(tmp_path, "a2_phase1_all_sonnet_set01_seed42_20260515_1400",
               {**base, "config": {"model_config":"all_sonnet"}})
    _write_run(tmp_path, "a2_phase1_mixed_set03_seed42_20260515_1410",
               {**mixed, "config": {"model_config":"mixed"}})
    _write_run(tmp_path, "a2_phase1_mixed_set04_seed43_20260515_1420",
               {**mixed_b, "config": {"model_config":"mixed"}})
    _write_run(tmp_path, "a2_phase1_all_haiku_set05_seed44_20260515_1430",
               {**base, "config": {"model_config":"all_haiku"}})

    out = aggregate_phase_1(runs_root=tmp_path)
    assert out["total_rollouts"] == 4
    assert out["configs"]["mixed"]["rollout_count"] == 2
    assert out["configs"]["mixed"]["mean_advantage_ratio"] == 2.5
    assert out["headline"]["advantage_ratio"] == 2.5
