from resources_server.gains import compute_per_agent_gains
from marketplace.ledger import Ledger


def test_seller_gain_is_price_minus_floor(tmp_path):
    lg = Ledger(path=tmp_path / "d.json"); lg.clear()
    lg.record_deal(
        seller="Maya", buyer="Derek",
        item_id="b", item_name="Blender",
        price=50, seller_floor=35, buyer_ceiling=60, turn=1,
    )
    personas = [
        {"name": "Maya",
         "items_to_sell": [{"item_id": "b", "name": "Blender", "floor_price": 35}],
         "items_to_buy": []},
        {"name": "Derek",
         "items_to_sell": [],
         "items_to_buy": [{"want_id": "w1", "description": "blender", "ceiling_price": 60}]},
    ]
    gains = compute_per_agent_gains(personas, lg.deals)
    # Maya: seller surplus 50 - 35 = 15
    assert gains["Maya"] == 15.0
    # Derek: buyer surplus 60 - 50 = 10
    assert gains["Derek"] == 10.0


def test_zero_gain_for_uninvolved_agent(tmp_path):
    lg = Ledger(path=tmp_path / "d.json"); lg.clear()
    personas = [{"name": "Quiet", "items_to_sell": [], "items_to_buy": []}]
    gains = compute_per_agent_gains(personas, lg.deals)
    assert gains["Quiet"] == 0.0
