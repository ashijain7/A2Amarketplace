"""What a recorded live run looks like once it reaches the platform.

A live row and a cached row describe the same thing and are shown in the same list, so
they have to speak the same language — same policy line, same stage/set label, same
outcome wording. Two vocabularies for one environment is a bug you only notice later.
"""

import platform_export as px


def _result(**over):
    base = {
        "phase": "market_deal",
        "focal_model": "anthropic/claude-sonnet-4-5",
        "opponents_model": "google/gemini-3.1-pro-preview",
        "max_turns": 100,
        "duration_s": 240.0,
        "per_set": [
            {
                "set_id": "set_01",
                "focal_persona": "Kai",
                "reward": 0.32,
                "rubric_breakdown": {"deal_outcomes": 0.4, "swap_quality": None},
                "num_deals": 6,
                "num_focal_deals": 2,
                "num_focal_steps": 44,
                "num_channel_events": 78,
            }
        ],
    }
    base.update(over)
    return base


def test_the_row_names_who_was_evaluated_and_who_they_faced():
    rec = px.result_to_platform_records(_result(), "A2A_Marketplace", "run_1")[0]

    assert rec["policy_name"] == "Sonnet 4.5 (evaluated) vs Gemini 3.1 Pro"
    assert rec["checkpoint_label"] == "MarketDeal · Stage I · Set 01"
    assert rec["scenario_name"] == "MarketDeal · Stage I — Set 01 (Basic trading)"


def test_the_run_names_itself_so_a_retry_is_not_a_second_run():
    recs = px.result_to_platform_records(_result(), "A2A_Marketplace", "run_1")

    assert recs[0]["id"] == "run_1__set_01"


def test_steps_are_the_agents_own_actions_not_the_markets_traffic():
    rec = px.result_to_platform_records(_result(), "A2A_Marketplace", "run_1")[0]

    assert rec["total_steps"] == 44, "should be the focal's actions, not 78 channel events"


def test_the_outcome_says_what_the_agent_actually_did():
    rec = px.result_to_platform_records(_result(), "A2A_Marketplace", "run_1")[0]
    assert rec["final_environment_state"]["status"] == "2 deals closed"

    no_deal = _result()
    no_deal["per_set"][0]["num_focal_deals"] = 0
    rec = px.result_to_platform_records(no_deal, "A2A_Marketplace", "run_1")[0]
    assert rec["final_environment_state"]["status"] == "no deal closed"

    one = _result()
    one["per_set"][0]["num_focal_deals"] = 1
    rec = px.result_to_platform_records(one, "A2A_Marketplace", "run_1")[0]
    assert rec["final_environment_state"]["status"] == "1 deal closed"


def test_a_measured_duration_is_reported_and_shared_across_the_sets():
    """One run over 5 sets is 5 rollouts — the run's time is divided, not repeated."""
    five = _result()
    five["per_set"] = [dict(five["per_set"][0], set_id=f"set_0{i}") for i in range(1, 6)]

    recs = px.result_to_platform_records(five, "A2A_Marketplace", "run_1")

    assert [r["duration_s"] for r in recs] == [48.0] * 5


def test_an_untimed_run_carries_no_duration_at_all():
    """Absent, not null — a null would tell the platform 'this run has no duration'."""
    untimed = _result(duration_s=None)

    rec = px.result_to_platform_records(untimed, "A2A_Marketplace", "run_1")[0]

    assert "duration_s" not in rec


def test_null_rubrics_are_dropped():
    """The platform types reward_breakdown as float-valued; a None would 422 the push."""
    rec = px.result_to_platform_records(_result(), "A2A_Marketplace", "run_1")[0]

    assert "swap_quality" not in rec["final_environment_state"]
    assert all(v is not None for v in rec["steps"][0]["reward_breakdown"].values())


def test_an_unknown_model_still_reads_sensibly():
    odd = _result(focal_model="someprovider/brand-new-model-9")

    rec = px.result_to_platform_records(odd, "A2A_Marketplace", "run_1")[0]

    assert rec["policy_name"].startswith("brand-new-model-9 (evaluated)")
