import json
from pathlib import Path
from scripts.archive_run import archive_rollout, build_run_id


def test_build_run_id_format():
    rid = build_run_id(
        phase=1, model_config="mixed", persona_set="set_03",
        seed=42, when="20260515_1430",
    )
    assert rid == "a2_phase1_mixed_set03_seed42_20260515_1430"


def test_archive_creates_seven_files_for_homogeneous(tmp_path):
    rollout = {
        "metadata": {
            "persona_set": "set_01", "model_config": "all_sonnet",
            "seed": 42, "expected_possible_deals": 8,
        },
        "run_result": {
            "deals": [{"deal_id":"d1","turn":1,"seller":"A","buyer":"B",
                       "item_id":"i","item_name":"x","price":50,
                       "seller_floor":40,"buyer_ceiling":60}],
            "channel_log": [],
            "per_agent_gains": {"A": 10.0, "B": 10.0},
            "model_assignments": {"A":"anthropic/claude-sonnet-4-5",
                                  "B":"anthropic/claude-sonnet-4-5"},
            "turns_used": 5, "stop_reason": "all_agents_done",
        },
        "reward": 0.7,
        "rubric_scores": {"deal_outcomes": {"combined": 0.8},
                          "capability_asymmetry": {"combined": 0.6,
                              "per_agent_self_rating": {"A":5,"B":5},
                              "per_agent_observer_rating": {"A":5,"B":5}},
                          "advantage_ratio": None,
                          "negotiation_quality": {"combined":0.7},
                          "privacy": {"combined":1.0, "per_agent":{}},
                          "review_utilization": None,
                          "final_reward": 0.7},
    }
    personas = [{"name":"A"}, {"name":"B"}]
    out_dir = archive_rollout(
        rollout=rollout, personas=personas,
        out_root=tmp_path, when="20260515_1430",
    )
    files = {p.name for p in out_dir.iterdir()}
    assert {"summary.json","channel.jsonl","deals.json","personas.json",
            "rubric_scores.json","rollout.json","judge_ratings.json"} <= files
    # No model_advantage.json for non-mixed
    assert "model_advantage.json" not in files
    summary = json.loads((out_dir / "summary.json").read_text())
    assert summary["approach"] == 2
    assert summary["phase"] == 1


def test_archive_creates_model_advantage_for_mixed(tmp_path):
    rollout = {
        "metadata": {"persona_set":"set_03","model_config":"mixed","seed":42,
                     "expected_possible_deals":8},
        "run_result": {
            "deals": [], "channel_log": [],
            "per_agent_gains": {"A":30.0,"B":10.0},
            "model_assignments": {"A":"anthropic/claude-sonnet-4-5",
                                  "B":"anthropic/claude-haiku-4-5"},
            "turns_used": 3, "stop_reason":"stall",
        },
        "reward": 0.5,
        "rubric_scores": {
            "advantage_ratio": 3.0,
            "deal_outcomes":{"combined":0.5},
            "capability_asymmetry":{"combined":0.5,
                "sonnet_perceived_fairness":5.0,"haiku_perceived_fairness":3.0,
                "per_agent_self_rating":{"A":5,"B":3},
                "per_agent_observer_rating":{"A":5,"B":3}},
            "negotiation_quality":{"combined":0.4},
            "privacy":{"combined":1.0,"per_agent":{}},
            "review_utilization": None, "final_reward":0.5,
        },
    }
    personas = [{"name":"A"}, {"name":"B"}]
    out_dir = archive_rollout(rollout, personas, tmp_path, when="20260515_1430")
    assert (out_dir / "model_advantage.json").exists()
    adv = json.loads((out_dir / "model_advantage.json").read_text())
    assert adv["advantage_ratio"] == 3.0
    assert adv["sonnet_mean_gain"] == 30.0
    assert adv["haiku_mean_gain"] == 10.0
