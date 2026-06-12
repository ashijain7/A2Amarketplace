"""Per-deal payment state: the stages, the record, and the on-disk store."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

STAGES = ["AGREED", "METHOD_CHOSEN", "AWAITING_OTP", "PAID", "CONFIRMED", "FAILED"]

# Forward-only: which stages a given stage may move to.
_ALLOWED = {
    "AGREED": {"METHOD_CHOSEN"},
    "METHOD_CHOSEN": {"AWAITING_OTP", "PAID", "FAILED", "METHOD_CHOSEN"},  # re-choose allowed
    "AWAITING_OTP": {"PAID", "FAILED"},
    "PAID": {"CONFIRMED"},
    "FAILED": {"METHOD_CHOSEN"},   # retry
    "CONFIRMED": set(),
}


@dataclass
class SettlementRecord:
    deal_id: str
    buyer: str
    seller: str
    item_id: str
    amount: float
    seller_accepts: list
    stage: str = "AGREED"
    chosen_method: str | None = None
    instrument_used: str | None = None
    amount_typed: float | None = None
    recipient_typed: str | None = None
    attempt_count: int = 0
    method_vs_accepted: bool | None = None
    otp_code: str | None = None
    scam_on: bool = False
    scam_type: str | None = None
    outcome: str = "open"
    exposed_secret: list = field(default_factory=list)   # {secret_kind, value, channel}
    room: list = field(default_factory=list)             # {turn, speaker, spoofed_as, is_scammer, text}

    def can_move(self, to: str) -> bool:
        return to in _ALLOWED.get(self.stage, set())


class SettlementStore:
    """Holds every deal's SettlementRecord; persists to settlement.json."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.records: dict[str, SettlementRecord] = {}

    def add(self, rec: SettlementRecord):
        self.records[rec.deal_id] = rec
        self.save()

    def get(self, deal_id: str) -> SettlementRecord | None:
        return self.records.get(deal_id)

    def for_party(self, name: str) -> list[SettlementRecord]:
        return [r for r in self.records.values() if r.buyer == name or r.seller == name]

    def save(self, balances: dict | None = None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"records": [asdict(r) for r in self.records.values()]}
        if balances is not None:
            data["balances"] = balances
        self.path.write_text(json.dumps(data, indent=2))
