#!/usr/bin/env python3
"""Salvage completed-but-unbanked marketplace folders into a phase-4 rollouts.jsonl.

Some rollouts run all the way through negotiation + settlement but NeMo Gym never
banks them (the re-launch-on-stall loop abandons them). Their data is intact on disk
(channel.jsonl + deals.json + settlement.json). This rebuilds the state from those
files, scores it with the existing verifier stack (qwen judge), and writes a standard
rollouts.jsonl record — so settlement_aggregate.py / settlement_per_set.py can then
produce the same phase-4 folder structure as every other config.

Caveats (salvage limits, not bugs): the focal's raw transcript was never saved, so the
record's `response` is a placeholder; `_focal_lookups` isn't persisted, so review_utilization
is scored against an empty lookup list (slight under-count). Scores otherwise are real.

Usage: python scripts/salvage_phase4.py            # score + print only (dry run)
       python scripts/salvage_phase4.py --write     # also write rollouts.jsonl
"""
import json, sys, dataclasses
from types import SimpleNamespace
from pathlib import Path

from marketplace.channel import Channel, ChannelEvent
from marketplace.ledger import Ledger
from resources_server.settlement.state import SettlementStore, SettlementRecord
from resources_server.app import _verify_for_state, MarketplaceServer

JUDGE = MarketplaceServer.JUDGE_MODEL  # qwen/qwen3.6-27b

BACKUP = Path("results/_backups/c7_salvage_2026-06-18")
OUT_DIR = Path("results/paper_runs/C7_gemini_vs_gpt55/phase4")
TASK_FILE = Path("tasks/settlement_focal_G_vs_X_p2.jsonl")

# folder prefix -> task line index (set_01=Kai line0, set_02=Rex line1)
TARGETS = [("4d359a", 0), ("f7de2a", 1)]


def _filter(cls, d):
    valid = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in d.items() if k in valid}


def load_channel(path: Path) -> Channel:
    ch = Channel(path=path)          # __init__ does not touch the file
    ch.events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            ch.events.append(ChannelEvent(**_filter(ChannelEvent, json.loads(line))))
    return ch


def load_settlement(path: Path):
    data = json.loads(path.read_text())
    store = SettlementStore(path)
    store.records = {}
    for r in data.get("records", []):
        rec = SettlementRecord(**_filter(SettlementRecord, r))
        store.records[rec.deal_id] = rec
    bal = data.get("balances", {})
    settlement = SimpleNamespace(store=store, bank=SimpleNamespace(balances=bal))
    return settlement, bal


def salvage(folder_prefix: str, task_idx: int) -> dict:
    folder = next(BACKUP.glob(f"{folder_prefix}*"))
    task = json.loads(TASK_FILE.read_text().splitlines()[task_idx])
    meta = task["metadata"]
    personas = json.loads(Path(meta["personas_path"]).read_text())
    focal = meta["focal_persona"]

    ch = load_channel(folder / "channel.jsonl")
    ledger = Ledger.load(folder / "deals.json")
    settlement, balances = load_settlement(folder / "settlement.json")
    lookups = [e for e in ch.events if e.agent == focal and "lookup" in (e.action or "")]

    state = SimpleNamespace(
        focal_name=focal, personas=personas, channel=ch, ledger=ledger,
        settlement=settlement, judge_model=JUDGE, phase=int(meta.get("phase", 2)),
        _focal_lookups=lookups,
    )
    # _verify_for_state returns the full data block:
    # {reward, rubric_scores, channel_events, deals, settlement_records, settlement_balances, personas}
    verify = _verify_for_state(state)

    record = {
        "id": task_idx,
        "metadata": meta,
        "responses_create_params": task.get("responses_create_params", {}),
        "response": {"output": [], "usage": {}, "_salvaged": True,
                     "_source_folder": folder.name},
        **verify,
    }
    return record


def main():
    write = "--write" in sys.argv
    records = []
    for prefix, idx in TARGETS:
        rec = salvage(prefix, idx)
        records.append(rec)
        print(f"[{prefix}] set={rec['metadata'].get('set_id')} focal={rec['metadata'].get('focal_persona')} "
              f"reward={rec['reward']} rubrics={list(rec['rubric_scores'].keys())}", flush=True)
    if write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / "rollouts.jsonl"
        out.write_text("".join(json.dumps(r) + "\n" for r in records))
        print(f"WROTE {len(records)} records -> {out}", flush=True)
    else:
        print("(dry run — pass --write to emit rollouts.jsonl)", flush=True)


if __name__ == "__main__":
    main()
