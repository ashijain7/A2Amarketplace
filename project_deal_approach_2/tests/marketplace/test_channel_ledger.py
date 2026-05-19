from marketplace.channel import Channel
from marketplace.ledger import Ledger


def test_channel_post_and_retrieve(tmp_path):
    ch = Channel(path=tmp_path / "channel.jsonl")
    ch.clear()
    ev = ch.post(turn=1, agent="Maya", action="listing", target="blender_01", price=35.0, message="hi")
    assert ev.event_id.startswith("lst_")
    assert ch.get_event(ev.event_id).agent == "Maya"


def test_ledger_record_and_query(tmp_path):
    lg = Ledger(path=tmp_path / "deals.json")
    lg.clear()
    deal = lg.record_deal(
        seller="Maya", buyer="Derek",
        item_id="blender_01", item_name="Ninja blender",
        price=40.0, seller_floor=35, buyer_ceiling=50,
        turn=3,
    )
    assert deal.deal_id == "deal_001"
    assert lg.is_sold("blender_01") is True
