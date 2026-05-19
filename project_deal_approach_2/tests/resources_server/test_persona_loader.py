import json
import pytest
from resources_server.persona_loader import load_persona_set


def test_load_persona_set_returns_list(tmp_path, monkeypatch):
    p = tmp_path / "set_01.json"
    p.write_text(json.dumps([{"name": "Maya"}]))
    monkeypatch.setattr("resources_server.persona_loader.PERSONAS_DIR", tmp_path)
    out = load_persona_set("set_01")
    assert out == [{"name": "Maya"}]


def test_load_persona_set_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("resources_server.persona_loader.PERSONAS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load_persona_set("set_99")
