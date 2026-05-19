"""Per-agent gain = seller surplus (price - floor) + buyer surplus (ceiling - price)."""

from marketplace.ledger import Deal


def compute_per_agent_gains(personas: list[dict], deals: list[Deal]) -> dict[str, float]:
    gains: dict[str, float] = {p["name"]: 0.0 for p in personas}
    for d in deals:
        seller_surplus = d.price - d.seller_floor
        buyer_surplus = (d.buyer_ceiling - d.price) if d.buyer_ceiling else 0
        if d.seller in gains:
            gains[d.seller] += float(seller_surplus)
        if d.buyer in gains:
            gains[d.buyer] += float(buyer_surplus)
    return {k: round(v, 2) for k, v in gains.items()}
