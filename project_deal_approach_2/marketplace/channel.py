"""
The marketplace channel: an append-only JSONL log.

Every action any agent takes becomes one line in channel.jsonl. This
is the equivalent of Project Deal's Slack channel — a single shared
record everyone reads from and writes to.

We use append-only on disk for auditability. In-memory we keep a list
that mirrors the file for fast reads during a run.
"""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import config


@dataclass
class ChannelEvent:
    """One row in channel.jsonl."""
    turn: int
    event_id: str            # unique id for this event (used as offer_id/listing_id)
    agent: str               # which agent posted it
    action: str              # "listing" | "offer" | "counter" | "accept" | "decline" | "pass"
    target: Optional[str]    # referenced listing_id, offer_id, or item_id
    price: Optional[float]
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class Channel:
    """In-memory + on-disk channel state."""

    def __init__(self, path: Path = config.CHANNEL_PATH):
        self.path = path
        self.events: list[ChannelEvent] = []
        self._next_event_num = 1

    def clear(self):
        """Wipe channel for a fresh run."""
        self.events = []
        self._next_event_num = 1
        if self.path.exists():
            self.path.unlink()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def _make_event_id(self, action: str) -> str:
        prefix = {
            "listing": "lst",
            "offer": "off",
            "counter": "ctr",
            "accept": "acc",
            "decline": "dec",
            "pass": "psh",
            "reject": "rjt",
        }.get(action, "evt")
        eid = f"{prefix}_{self._next_event_num:03d}"
        self._next_event_num += 1
        return eid

    def post(
        self,
        turn: int,
        agent: str,
        action: str,
        target: Optional[str],
        price: Optional[float],
        message: str,
    ) -> ChannelEvent:
        event = ChannelEvent(
            turn=turn,
            event_id=self._make_event_id(action),
            agent=agent,
            action=action,
            target=target,
            price=price,
            message=message,
        )
        self.events.append(event)
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(event)) + "\n")
        return event

    # -- Queries the scheduler uses ----------------------------------

    def get_event(self, event_id: str) -> Optional[ChannelEvent]:
        for e in self.events:
            if e.event_id == event_id:
                return e
        return None

    def active_listings(self, sold_item_ids: set[str]) -> list[ChannelEvent]:
        """Listings whose item hasn't been sold yet."""
        return [
            e for e in self.events
            if e.action == "listing" and e.target not in sold_item_ids
        ]

    def offers_on_listing(self, listing_id: str) -> list[ChannelEvent]:
        """All open offers/counters tied to a given listing."""
        return [
            e for e in self.events
            if e.action in ("offer", "counter") and e.target == listing_id
        ]

    def recent(self, n: int = 12) -> list[ChannelEvent]:
        """Last n events, for the rolling-context window an agent sees."""
        return self.events[-n:]

    def max_declined_price_for(self, listing_id: str, offerer_name: str) -> float | None:
        """
        Return the highest price the seller has declined from offerer_name on listing_id.
        Used to prevent re-offers at or below a declined price.
        """
        declined_prices = []
        for e in self.events:
            if e.action != "decline" or not e.target:
                continue
            ref = self.get_event(e.target)
            if ref is None or ref.agent != offerer_name:
                continue
            if ref.action not in ("offer", "counter"):
                continue
            # Check that this offer/counter was on our listing
            listing = self.get_event(ref.target) if ref.target else None
            if listing and listing.event_id == listing_id and ref.price is not None:
                declined_prices.append(ref.price)
        return max(declined_prices) if declined_prices else None
