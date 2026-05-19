import json
from pathlib import Path

from tasks.generate_tasks import build_task_entries, write_tasks, MARKETPLACE_TOOLS


def _patch_personas_dir(monkeypatch):
    # personas/ was renamed to personas_phase1/ when phase-scoped folders
    # were introduced. Tests point at that concrete directory.
    monkeypatch.setattr(
        "tasks.generate_tasks.PERSONAS_DIR",
        Path(__file__).parent.parent / "personas_phase1",
    )


def test_generate_phase1_produces_60_tasks(monkeypatch):
    """Phase 1: 5 sets × 4 configs × 1 focal × 3 seeds = 60."""
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    assert len(entries) == 60


def test_generate_phase2_produces_180_tasks(monkeypatch):
    """Phase 2: 5 sets × 4 configs × 3 focals × 3 seeds = 180."""
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=2, focal_count=3)
    assert len(entries) == 180


def test_focal_count_changes_task_count(monkeypatch):
    """The focal_count parameter scales the entry count linearly."""
    _patch_personas_dir(monkeypatch)
    p1 = build_task_entries(phase=1, focal_count=1)
    p2 = build_task_entries(phase=2, focal_count=3)
    assert len(p1) == 60
    assert len(p2) == 180
    assert len(p2) == 3 * len(p1)


def test_build_task_entries_default_focal_count_is_three(monkeypatch):
    """Default (no focal_count arg) preserves Phase 2 / back-compat behavior."""
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=2)
    assert len(entries) == 180


def test_entry_has_top_level_id_and_responses_create_params(monkeypatch):
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    e = entries[0]
    assert e["id"] == 0
    assert "responses_create_params" in e
    assert "metadata" in e


def test_ids_are_sequential(monkeypatch):
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    ids = [e["id"] for e in entries]
    assert ids == list(range(len(entries)))


def test_responses_create_params_shape(monkeypatch):
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    rcp = entries[0]["responses_create_params"]
    # input has exactly 2 messages: system then user
    assert isinstance(rcp["input"], list)
    assert len(rcp["input"]) == 2
    assert rcp["input"][0]["role"] == "system"
    assert rcp["input"][1]["role"] == "user"
    assert isinstance(rcp["input"][0]["content"], str)
    assert isinstance(rcp["input"][1]["content"], str)
    # tools list has 6 function tools
    assert isinstance(rcp["tools"], list)
    assert len(rcp["tools"]) == 6
    # parallel_tool_calls is explicitly False
    assert rcp["parallel_tool_calls"] is False


def test_tools_are_valid_openai_function_tools(monkeypatch):
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    tools = entries[0]["responses_create_params"]["tools"]
    expected_names = {
        "post_listing", "make_offer", "counter_offer",
        "accept_offer", "reject_offer", "pass",
    }
    actual_names = {t["name"] for t in tools}
    assert actual_names == expected_names
    for t in tools:
        assert t["type"] == "function"
        assert t["strict"] is True
        assert "description" in t
        params = t["parameters"]
        assert params["type"] == "object"
        assert params["additionalProperties"] is False
        assert "properties" in params
        assert "required" in params


def test_system_prompt_includes_focal_name_and_template_pieces(monkeypatch):
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    e = entries[0]
    focal_name = e["metadata"]["focal_persona"]
    sys_content = e["responses_create_params"]["input"][0]["content"]
    assert focal_name in sys_content
    # Template-driven section headers should appear
    assert "ITEMS" in sys_content
    assert "NEGOTIATION STYLE" in sys_content


def test_initial_user_message_is_empty_marketplace_view(monkeypatch):
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    user_content = entries[0]["responses_create_params"]["input"][1]["content"]
    # Section header changed when phase 3 was added — accept either heading.
    assert "YOUR ITEMS" in user_content
    assert "YOUR WANTS" in user_content
    assert "OTHER AGENTS" in user_content
    assert "CHANNEL HISTORY" in user_content
    # Marketplace is empty at task start
    assert "empty" in user_content.lower() or "just opened" in user_content.lower()


def test_metadata_carries_archiver_fields(monkeypatch):
    _patch_personas_dir(monkeypatch)
    entries = build_task_entries(phase=1, focal_count=1)
    md = entries[0]["metadata"]
    for key in ("task_id", "phase", "approach", "config_name",
                "set_id", "focal_persona", "seed", "personas_path"):
        assert key in md
    assert md["phase"] == 1
    assert md["approach"] == 1
    assert md["config_name"] in {
        "focal_S_vs_S", "focal_H_vs_S", "focal_S_vs_H", "focal_H_vs_H",
    }


def test_write_tasks_phase1_produces_60_line_jsonl(tmp_path, monkeypatch):
    _patch_personas_dir(monkeypatch)
    out = tmp_path / "tasks_phase1.jsonl"
    write_tasks(phase=1, out_path=out, focal_count=1)
    lines = out.read_text().splitlines()
    assert len(lines) == 60
    rec = json.loads(lines[0])
    assert rec["id"] == 0
    assert rec["metadata"]["phase"] == 1
    assert len(rec["responses_create_params"]["tools"]) == 6


def test_write_tasks_phase2_produces_180_line_jsonl(tmp_path, monkeypatch):
    _patch_personas_dir(monkeypatch)
    out = tmp_path / "tasks_phase2.jsonl"
    write_tasks(phase=2, out_path=out, focal_count=3)
    lines = out.read_text().splitlines()
    assert len(lines) == 180
    rec = json.loads(lines[0])
    assert rec["id"] == 0
    assert rec["metadata"]["phase"] == 2


def test_marketplace_tools_module_constant_is_six(monkeypatch):
    assert len(MARKETPLACE_TOOLS) == 6
