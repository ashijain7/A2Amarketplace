import json
import importlib
import marketplace.config as config
import marketplace.live_log as live_log


def test_noop_when_unset(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LIVE_LOG", None)
    live_log.reset_seq()
    live_log.emit({"kind": "event", "action": "listing"})  # must not raise, must not write
    # nothing to assert beyond "no crash + no file created"
    assert not (tmp_path / "events.jsonl").exists()


def test_appends_json_lines_with_seq(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    monkeypatch.setattr(config, "LIVE_LOG", str(log))
    live_log.reset_seq()
    live_log.emit({"kind": "seed", "focal": "Kai"})
    live_log.emit({"kind": "event", "action": "offer", "price": 95.0})
    lines = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    assert lines[0]["kind"] == "seed" and lines[0]["seq"] == 1
    assert lines[1]["kind"] == "event" and lines[1]["seq"] == 2
    assert lines[1]["price"] == 95.0


def test_channel_post_emits_event(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    monkeypatch.setattr(config, "LIVE_LOG", str(log))
    live_log.reset_seq()
    from marketplace.channel import Channel
    ch = Channel(path=tmp_path / "channel.jsonl")
    ch.post(turn=1, agent="Kai", action="listing", target="item_bike",
            price=120.0, message="Selling my bike")
    lines = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    ev = lines[0]
    assert ev["kind"] == "event"
    assert ev["agent"] == "Kai" and ev["action"] == "listing"
    assert ev["price"] == 120.0 and ev["target"] == "item_bike"
