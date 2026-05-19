import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.channel import Channel
from project_deal_poc.ledger import Ledger
from project_deal_poc.agent import _format_channel_view


def make_channel():
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    c = Channel(path=Path(tmp.name))
    c.clear()
    return c


def make_ledger():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    l = Ledger(path=Path(tmp.name))
    l.clear()
    return l


PERSONA = {
    "name": "Dexter",
    "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
    "items_to_buy": [{"want_id": "headphones_w1", "description": "Headphones", "ceiling_price": 50}],
    "style": "Direct.",
}


def test_full_history_excludes_pass_events():
    """Pass events should not appear in the channel history shown to agents."""
    c = make_channel()
    l = make_ledger()

    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera for sale")
    c.post(2, "Mika", "offer", "lst_001", 55, "Offering $55")
    c.post(3, "Rosa", "pass", None, None, "(pass)")
    c.post(4, "Mika", "counter", "lst_001", 60, "How about $60?")

    view = _format_channel_view("Dexter", PERSONA, c, l)

    assert "(pass)" not in view, "pass event message should not appear in agent context"
    assert "Offering $55" in view, "offer event should appear in agent context"
    assert "How about $60?" in view, "counter event should appear in agent context"


def test_full_history_includes_old_events_beyond_8():
    """Events older than 8 turns should still appear in agent context."""
    c = make_channel()
    l = make_ledger()

    # Post 12 events — more than the old window of 8
    c.post(1, "Mika", "listing", "headphones_01", 48, "Headphones listing turn 1")
    for i in range(2, 12):
        c.post(i, "Rosa", "pass", None, None, "(pass)")
    c.post(12, "Dexter", "offer", "lst_001", 45, "Offer at turn 12")

    view = _format_channel_view("Dexter", PERSONA, c, l)

    # The listing from turn 1 should still be visible at turn 12
    assert "Headphones listing turn 1" in view, "old events should still appear in full history"
