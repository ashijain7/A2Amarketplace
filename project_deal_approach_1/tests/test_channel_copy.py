from pathlib import Path
import tempfile

from marketplace.channel import Channel, ChannelEvent
from marketplace.ledger import Ledger, Deal


def test_channel_can_post_and_query_event(tmp_path):
    ch = Channel(path=tmp_path / "ch.jsonl")
    ch.clear()
    ev = ch.post(turn=1, agent="Maya", action="listing", target="blender_01",
                 price=40.0, message="Selling my blender")
    assert ev.event_id.startswith("lst_")
    assert ch.get_event(ev.event_id) is ev
    assert len(ch.active_listings(sold_item_ids=set())) == 1


def test_ledger_records_and_marks_sold(tmp_path):
    ld = Ledger(path=tmp_path / "deals.json")
    ld.clear()
    d = ld.record_deal(
        seller="Maya", buyer="Derek",
        item_id="blender_01", item_name="Blender",
        price=40.0, seller_floor=35.0, buyer_ceiling=50.0, turn=2,
    )
    assert d.deal_id == "deal_001"
    assert ld.is_sold("blender_01")
    assert not ld.is_sold("nonexistent")
