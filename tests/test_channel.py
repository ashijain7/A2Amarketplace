import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.channel import Channel


def make_channel():
    """Create a channel backed by a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    c = Channel(path=Path(tmp.name))
    c.clear()
    return c


def test_reject_event_gets_rjt_prefix():
    """Posting a reject action should produce an event_id starting with rjt_."""
    c = make_channel()
    event = c.post(1, "Dexter", "reject", None, None, "action rejected: invalid target")
    assert event.event_id.startswith("rjt_"), f"Expected rjt_ prefix, got {event.event_id}"


def test_pass_event_gets_psh_prefix():
    """Posting a pass action should still produce an event_id starting with psh_."""
    c = make_channel()
    event = c.post(1, "Dexter", "pass", None, None, "(pass)")
    assert event.event_id.startswith("psh_"), f"Expected psh_ prefix, got {event.event_id}"


def test_max_declined_price_for_returns_none_when_no_declines():
    """Returns None when no offers from agent have been declined on a listing."""
    c = make_channel()
    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera $65")   # lst_001
    c.post(2, "Mika", "offer", "lst_001", 55, "Offering $55")        # off_002

    result = c.max_declined_price_for("lst_001", "Mika")
    assert result is None


def test_max_declined_price_for_returns_declined_price():
    """Returns the price of a declined offer."""
    c = make_channel()
    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera $65")    # lst_001
    c.post(2, "Mika", "offer", "lst_001", 50, "Offering $50")        # off_002
    c.post(3, "Dexter", "decline", "off_002", None, "No thanks")     # dec_003

    result = c.max_declined_price_for("lst_001", "Mika")
    assert result == 50.0


def test_max_declined_price_for_returns_highest_when_multiple():
    """Returns the highest declined price when multiple offers were declined."""
    c = make_channel()
    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera $65")    # lst_001
    c.post(2, "Mika", "offer", "lst_001", 45, "Try $45")             # off_002
    c.post(3, "Dexter", "decline", "off_002", None, "Too low")       # dec_003
    c.post(4, "Mika", "offer", "lst_001", 50, "Try $50")             # off_004
    c.post(5, "Dexter", "decline", "off_004", None, "Still no")      # dec_005

    result = c.max_declined_price_for("lst_001", "Mika")
    assert result == 50.0
