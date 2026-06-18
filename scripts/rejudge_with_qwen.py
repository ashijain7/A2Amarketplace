#!/usr/bin/env python3
"""Re-judge existing paper-run rollouts with the qwen judge (surgical, no re-simulation).

The phase-1/2/3/4 paper runs were scored with the hardcoded gpt-4o judge (the scorer
ignored env.yaml until commit e738c0e flipped JUDGE_MODEL to qwen3.6-27b). This re-runs
ONLY the two judge-dependent rubrics — capability_asymmetry and privacy — with qwen, on
the SAVED transcripts in each rollout record, recombines the reward, and rebuilds every
derived view. Each rule-based score (deal_outcomes / negotiation_quality /
review_utilization / swap_quality / transactional_integrity) is kept byte-identical.

What gets rewritten per cell (full consistency):
  - rollouts.jsonl            (the per-record source)
  - aggregate.json            (overall mean/min/max reward + per-rollout)
  - phases 1-3: each set_NN_<focal>/ folder's rollout.json / rubric_scores.json /
                judge_ratings.json / summary.json
  - phase 4:    rebuilt by settlement_aggregate.py + settlement_per_set.py
                (aggregate.json, INSIGHTS.md, set folders)

The gpt-4o version of each phase folder is copied to results/_backups/ before any write.

Usage:
  python scripts/rejudge_with_qwen.py                       # dry-run ALL cells: print old->new, write nothing
  python scripts/rejudge_with_qwen.py --only C1_sonnet_vs_sonnet:1   # dry-run one cell
  python scripts/rejudge_with_qwen.py --write              # back up, re-score, re-aggregate (all cells)
  python scripts/rejudge_with_qwen.py --only C1_sonnet_vs_sonnet:1 --write
"""
import json, sys, shutil, subprocess, dataclasses
from types import SimpleNamespace
from pathlib import Path

from marketplace.channel import Channel, ChannelEvent
from resources_server.verifiers import (
    compute_capability_asymmetry, compute_privacy, compute_final_reward,
)
from resources_server.app import MarketplaceServer

JUDGE = MarketplaceServer.JUDGE_MODEL  # qwen/qwen3.6-27b
PR = Path("results/paper_runs")
BACKUP_ROOT = Path("results/_backups/gpt4o_prejudge_2026-06-18")
PY = ".venv/bin/python"

# config_dir -> phases to re-judge (C7 phase-4 already qwen, so it's excluded here)
MATRIX = [
    ("C1_sonnet_vs_sonnet",  [1, 2, 3, 4]),
    ("C4_sonnet_vs_gemini",  [1, 2, 3, 4]),
    ("C6_opus_vs_gemini",    [1, 2, 3, 4]),
    ("C8_gemini35_vs_gpt55", [1, 2, 3, 4]),
    ("C7_gemini_vs_gpt55",   [1, 2, 3]),
]


def _filter(cls, d):
    valid = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in d.items() if k in valid}


def _channel(events):
    ch = Channel(path=Path("/tmp/_rejudge_ch"))   # __init__ does not touch the file
    ch.events = [ChannelEvent(**_filter(ChannelEvent, e)) for e in events]
    return ch


def _ledger(deals):
    def num(x):
        return x if isinstance(x, (int, float)) else 0.0
    return SimpleNamespace(deals=[SimpleNamespace(
        seller=d.get("seller"), buyer=d.get("buyer"),
        price=num(d.get("price")), seller_floor=num(d.get("seller_floor")),
        buyer_ceiling=num(d.get("buyer_ceiling"))) for d in deals])


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def rejudge_record(r, phase):
    """Recompute ONLY capability_asymmetry + privacy with qwen, then the reward.
    Mutates r in place. Returns (old_reward, new_reward, new_cap, new_priv)."""
    rs = r.get("rubric_scores") or {}
    personas = r.get("personas") or []
    fname = (r.get("metadata") or {}).get("focal_persona")
    focal = next((p for p in personas if p.get("name") == fname), None)
    if focal is None:
        raise ValueError(f"focal {fname!r} not found in personas")

    ch = _channel(r.get("channel_events") or [])
    led = _ledger(r.get("deals") or [])

    new_cap = compute_capability_asymmetry(focal, ch, led, judge_model=JUDGE)
    new_priv = compute_privacy(focal, ch, judge_model=JUDGE)
    priv_key = "persona_privacy" if "persona_privacy" in rs else "privacy"

    def comb(k):
        v = rs.get(k)
        return v.get("combined") if isinstance(v, dict) else None

    new_reward = compute_final_reward({
        "deal_outcomes": comb("deal_outcomes"),
        "capability_asymmetry": new_cap["combined"],
        "negotiation_quality": comb("negotiation_quality"),
        "privacy": new_priv["combined"],
        "review_utilization": comb("review_utilization"),
        "swap_quality": comb("swap_quality"),
    }, phase)

    old_reward = r.get("reward")
    rs["capability_asymmetry"] = new_cap
    rs[priv_key] = new_priv
    if "final_reward" in rs:
        rs["final_reward"] = new_reward
    r["rubric_scores"] = rs
    r["reward"] = new_reward
    return old_reward, new_reward, new_cap, new_priv


def update_set_folder(phase_dir, r, new_cap, new_priv):
    """Phases 1-3: rewrite the per-set folder's score files from the re-scored record."""
    md = r.get("metadata") or {}
    folder = phase_dir / f"{md.get('set_id')}_{md.get('focal_persona')}"
    if not folder.is_dir():
        return False
    rs = r["rubric_scores"]
    (folder / "rollout.json").write_text(json.dumps(r, indent=2))
    (folder / "rubric_scores.json").write_text(json.dumps(rs, indent=2))
    (folder / "judge_ratings.json").write_text(json.dumps({
        "self_rating": new_cap["self_rating"],
        "observer_rating": new_cap["observer_rating"],
        "perceived_fairness": new_cap["perceived_fairness"],
        "self_observer_delta": new_cap["self_observer_delta"],
    }, indent=2))
    sp = folder / "summary.json"
    if sp.exists():
        s = json.loads(sp.read_text())
        srs = s.get("rubric_scores") or {}
        if "capability_asymmetry" in srs:
            srs["capability_asymmetry"] = new_cap["combined"]
        pk = next((k for k in ("persona_privacy", "privacy") if k in srs), None)
        if pk:
            srs[pk] = new_priv["combined"]
        if "final_reward" in srs:
            srs["final_reward"] = r["reward"]
        s["rubric_scores"] = srs
        if "focal_value_extracted" in s:
            s["focal_value_extracted"] = new_cap["focal_value_extracted"]
        sp.write_text(json.dumps(s, indent=2))
    return True


def aggregate_123(phase_dir, records):
    """Rebuild the simple per-config-phase aggregate.json (same shape as the run script),
    preserving config_name / phase / focal_model from the existing aggregate."""
    agg_path = phase_dir / "aggregate.json"
    base = json.loads(agg_path.read_text()) if agg_path.exists() else {}
    rewards = [r.get("reward") for r in records]
    nz = [x for x in rewards if x is not None]
    agg = {
        "config_name": base.get("config_name"),
        "phase": base.get("phase"),
        "focal_model": base.get("focal_model"),
        "rollout_count": len(records),
        "mean_reward": _mean(rewards),
        "min_reward": min(nz, default=None),
        "max_reward": max(nz, default=None),
        "per_rollout": [{
            "id": r.get("id"),
            "set_id": (r.get("metadata") or {}).get("set_id"),
            "focal_persona": (r.get("metadata") or {}).get("focal_persona"),
            "reward": r.get("reward"),
            "rubric_scores": r.get("rubric_scores"),
            "num_deals": len(r.get("deals") or []),
            "num_channel_events": len(r.get("channel_events") or []),
        } for r in records],
    }
    agg_path.write_text(json.dumps(agg, indent=2))


def aggregate_phase4(phase_dir, config):
    """Phase 4: regenerate aggregate.json + INSIGHTS.md + set folders via the settlement helpers."""
    roll = str(phase_dir / "rollouts.jsonl")
    subprocess.run([PY, "scripts/settlement_aggregate.py", roll, str(phase_dir),
                    config, "4", "on", "0"], check=True)
    subprocess.run([PY, "scripts/settlement_per_set.py", "--in", roll,
                    "--out-dir", str(phase_dir)], check=True)


def process_cell(config, phase, write):
    phase_dir = PR / config / f"phase{phase}"
    roll = phase_dir / "rollouts.jsonl"
    if not roll.exists():
        print(f"  SKIP {config}/phase{phase}: no rollouts.jsonl")
        return None
    records = [json.loads(l) for l in roll.open() if l.strip()]
    print(f"\n=== {config} / phase{phase}  ({len(records)} rollouts) ===")

    olds, news, extras = [], [], []
    for r in records:
        old, new, cap, priv = rejudge_record(r, phase)
        olds.append(old); news.append(new); extras.append((r, cap, priv))
        m = r.get("metadata") or {}
        print(f"  {m.get('set_id')} {str(m.get('focal_persona')):8s} "
              f"reward {old:.4f} -> {new:.4f}  (Δ{new - old:+.4f})")
    print(f"  mean reward {_mean(olds):.4f} -> {_mean(news):.4f}  "
          f"(Δ{_mean(news) - _mean(olds):+.4f})")

    if not write:
        return (_mean(olds), _mean(news))

    # back up the gpt-4o phase folder, then write
    dest = BACKUP_ROOT / config / f"phase{phase}"
    if not dest.exists():
        shutil.copytree(phase_dir, dest)
        print(f"  backed up gpt-4o -> {dest}")
    roll.write_text("".join(json.dumps(r) + "\n" for r in records))

    if phase == 4:
        aggregate_phase4(phase_dir, config)
    else:
        for r, cap, priv in extras:
            update_set_folder(phase_dir, r, cap, priv)
        aggregate_123(phase_dir, records)
    print(f"  wrote qwen scores + aggregate")
    return (_mean(olds), _mean(news))


def main():
    write = "--write" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]   # e.g. C1_sonnet_vs_sonnet:1

    cells = []
    for config, phases in MATRIX:
        for ph in phases:
            if only:
                oc, _, op = only.partition(":")
                if oc != config or (op and int(op) != ph):
                    continue
            cells.append((config, ph))

    print(f"judge = {JUDGE}   mode = {'WRITE' if write else 'DRY-RUN'}   cells = {len(cells)}")
    for config, ph in cells:
        process_cell(config, ph, write)
    if not write:
        print("\n(dry run — pass --write to back up + apply)")


if __name__ == "__main__":
    main()
