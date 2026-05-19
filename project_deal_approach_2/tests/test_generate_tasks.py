import json
from pathlib import Path
from tasks.generate_tasks import build_phase_1_tasks, SEEDS, CONFIGS, SET_NAMES


def test_phase_1_produces_45_tasks():
    tasks = build_phase_1_tasks(possible_deals_by_set={s: 8 for s in SET_NAMES})
    assert len(tasks) == 5 * 3 * 3
    metadatas = [t["metadata"] for t in tasks]
    assert {m["model_config"] for m in metadatas} == {"all_sonnet", "mixed", "all_haiku"}
    assert {m["persona_set"] for m in metadatas} == set(SET_NAMES)
    assert set(SEEDS) == {m["seed"] for m in metadatas}


def test_task_has_tool_definition():
    tasks = build_phase_1_tasks(possible_deals_by_set={s: 8 for s in SET_NAMES})
    t = tasks[0]
    assert "responses_create_params" in t
    rcp = t["responses_create_params"]
    assert "input" in rcp and "tools" in rcp
    assert rcp["tools"][0]["function"]["name"] == "run_marketplace"


def test_seeds_are_42_43_44():
    assert SEEDS == [42, 43, 44]
