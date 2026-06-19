"""
Re-score the review_utilization rubric on existing PHASE 3 (SwapShop) runs.

WHY THIS EXISTS
---------------
compute_review_utilization counted only money-phase offer actions
("offer", "counter", "accept") when building focal_offer_events. SwapShop
uses "swap_proposal" / "accept_swap", so focal_offer_events was always
EMPTY in phase 3, which forced pre_offer_ratio and high_rating_preference
to their "no offers -> 1.0" defaults. An agent that never looked up a
single review still scored 0.667 (lookup_rate 0 + 1.0 + 1.0)/3.

The live scorer is now fixed (swap actions added to the offer filter).
But the focal's lookups were never persisted to any channel file -- only
the aggregate count survived. So to re-score existing runs we rebuild the
focal's lookup ORDER and swap-offer counterparties from the stored
response.output trace (the focal's tool-call sequence) plus the channel
events. This was validated to align 1:1 with the channel events on all
35 phase-3 rollouts, and the recovered lookup counts match the stored
lookups_made exactly.

The metric DEFINITION is unchanged: three sub-scores
(lookup_rate, pre_offer_ratio, high_rating_preference), unweighted mean.
We only correct the inputs so the number stops being hollow. Per-rollout
final_reward is then recomputed with the unchanged phase-3 weights.

USAGE
-----
  python scripts/rescore_phase3_review_util.py            # all configs
  python scripts/rescore_phase3_review_util.py C1_sonnet_vs_sonnet
  python scripts/rescore_phase3_review_util.py --dry-run  # report only

Writes in place. Backs up rollouts.jsonl + aggregate.json to *.pre_ru_bak
(only if a backup does not already exist).
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAPER_RUNS = ROOT / "results" / "paper_runs"

# Mirror of resources_server.verifiers.PHASE_3_WEIGHTS / compute_final_reward.
# Inlined so this re-score script has no heavy import chain (config/dotenv).
# DEPRECATED: superseded by scripts/rescore_rtc_nq.py (RTC /100 + NQ-drop +
# privacy-key fix). Kept for provenance. Weights below are aligned to the current
# phase-3 scheme (NQ dropped) so re-running this cannot reintroduce the old bugs.
PHASE_3_WEIGHTS = {
    "deal_outcomes": 0.10,
    "capability_asymmetry": 0.15,
    "privacy": 0.10,
    "review_utilization": 0.20,
    "swap_quality": 0.30,
}


def compute_final_reward(scores: dict, phase: int = 3) -> float:
    """Weighted mean over non-None rubrics; weight renormalized. (phase 3)"""
    total = 0.0
    weight_used = 0.0
    for key, w in PHASE_3_WEIGHTS.items():
        val = scores.get(key)
        if val is not None:
            total += val * w
            weight_used += w
    return round(total / weight_used, 4) if weight_used > 0 else 0.0

# Focal swap actions that count as "offer events" (decision: both proposing
# and accepting a swap, mirroring the money phase's offer + accept).
SWAP_OFFER_ACTIONS = ("swap_proposal", "accept_swap")


def _focal_function_calls(response: dict) -> list[tuple[str, dict]]:
    """Ordered (name, args) for every function_call in the focal's output."""
    calls = []
    for it in (response or {}).get("output") or []:
        if it.get("type") != "function_call":
            continue
        try:
            args = json.loads(it.get("arguments") or "{}")
        except (json.JSONDecodeError, TypeError):
            args = {}
        calls.append((it.get("name"), args))
    return calls


def _recompute_review_utilization(rollout: dict) -> dict:
    """Rebuild review_utilization from the response trace + channel events.

    Returns the new review_utilization dict. Order-based: a counterparty is
    'looked up before the offer' iff its lookup appears earlier in the
    focal's tool-call stream than the successful swap offer to it.
    """
    md = rollout.get("metadata") or {}
    focal_name = md.get("focal_persona")
    personas = rollout.get("personas") or []
    ce = rollout.get("channel_events") or []

    # event_id -> owner maps for resolving the counterparty of a swap.
    listing_owner = {e["event_id"]: e["agent"]
                     for e in ce if e.get("action") == "listing"}
    proposal_author = {e["event_id"]: e["agent"]
                       for e in ce if e.get("action") == "swap_proposal"}

    # The focal's channel events, in order. Each non-lookup focal tool call
    # produces exactly one of these (lookup_agent produces none) -- so we can
    # align the call stream with the channel to know which calls SUCCEEDED.
    focal_ch = [e for e in ce if e.get("agent") == focal_name]

    calls = _focal_function_calls(rollout.get("response"))
    n_nonlookup = sum(1 for n, _ in calls if n != "lookup_agent")
    if n_nonlookup != len(focal_ch):
        raise RuntimeError(
            f"alignment mismatch for {md.get('set_id')}/{focal_name}: "
            f"{n_nonlookup} non-lookup calls vs {len(focal_ch)} channel events"
        )

    n_lookups = 0
    looked_up: set[str] = set()
    offers: list[tuple[str, bool]] = []  # (counterparty, looked_up_before)
    ci = 0
    for name, args in calls:
        if name == "lookup_agent":
            n_lookups += 1
            tgt = args.get("name")
            if tgt:
                looked_up.add(tgt)
            continue
        ev = focal_ch[ci]
        ci += 1
        act = ev.get("action")
        if act not in SWAP_OFFER_ACTIONS:
            continue
        if act == "swap_proposal":
            cp = listing_owner.get(ev.get("target"))
        else:  # accept_swap
            cp = proposal_author.get(ev.get("target"))
        if not cp or cp == focal_name:
            continue
        offers.append((cp, cp in looked_up))

    lookup_rate = min(1.0, n_lookups / 3.0)

    if not offers:
        pre_offer_ratio = 1.0
    else:
        pre_offer_ratio = sum(1 for _, prior in offers if prior) / len(offers)

    # high_rating_preference: of offers to counterparties with a rating,
    # what fraction went to ones rated >= 4.0. Mirrors the live scorer by
    # reading seller_rating for the counterparty.
    rating_of = {p.get("name"): p.get("seller_rating") for p in personas}
    n_rated = 0
    n_high = 0
    for cp, _ in offers:
        r = rating_of.get(cp)
        if r is None:
            continue
        n_rated += 1
        if r >= 4.0:
            n_high += 1
    high_rating_preference = (n_high / n_rated) if n_rated else 1.0

    combined = (lookup_rate + pre_offer_ratio + high_rating_preference) / 3.0

    return {
        "applicable": True,
        "lookups_made": n_lookups,
        "focal_offer_events": len(offers),
        "lookup_rate": lookup_rate,
        "pre_offer_ratio": pre_offer_ratio,
        "high_rating_preference": high_rating_preference,
        "combined": combined,
    }


def _combined_parts(rubric_scores: dict) -> dict:
    """{rubric_name: combined_scalar} for compute_final_reward (phase 3)."""
    def comb(k):
        d = rubric_scores.get(k)
        return d.get("combined") if isinstance(d, dict) else None
    # privacy is stored under "persona_privacy" (newer configs) or legacy "privacy".
    priv = next((rubric_scores[k].get("combined")
                 for k in ("persona_privacy", "privacy")
                 if isinstance(rubric_scores.get(k), dict)), None)
    return {
        "deal_outcomes": comb("deal_outcomes"),
        "capability_asymmetry": comb("capability_asymmetry"),
        "privacy": priv,
        "review_utilization": comb("review_utilization"),
        "swap_quality": comb("swap_quality"),
    }


def _rescore_config(phase3_dir: Path, dry_run: bool) -> dict:
    roll_path = phase3_dir / "rollouts.jsonl"
    agg_path = phase3_dir / "aggregate.json"
    rollouts = [json.loads(l) for l in roll_path.open()]

    changes = []
    by_id = {}
    for r in rollouts:
        md = r.get("metadata") or {}
        old_ru = (r.get("rubric_scores") or {}).get("review_utilization") or {}
        new_ru = _recompute_review_utilization(r)
        # Sanity: recovered lookup count must match what was recorded live.
        if old_ru.get("lookups_made") is not None \
                and new_ru["lookups_made"] != old_ru["lookups_made"]:
            raise RuntimeError(
                f"lookups_made mismatch {md.get('set_id')}/{md.get('focal_persona')}: "
                f"recovered {new_ru['lookups_made']} vs stored {old_ru['lookups_made']}"
            )
        r["rubric_scores"]["review_utilization"] = new_ru
        new_reward = compute_final_reward(
            _combined_parts(r["rubric_scores"]), phase=3
        )
        old_reward = r.get("reward")
        r["rubric_scores"]["final_reward"] = new_reward
        r["reward"] = new_reward
        by_id[r.get("id")] = r
        changes.append({
            "set_id": md.get("set_id"),
            "focal": md.get("focal_persona"),
            "lookups": new_ru["lookups_made"],
            "ru_old": round(old_ru.get("combined", 0.0), 3),
            "ru_new": round(new_ru["combined"], 3),
            "por": round(new_ru["pre_offer_ratio"], 3),
            "hrp": round(new_ru["high_rating_preference"], 3),
            "reward_old": round(old_reward, 4) if old_reward is not None else None,
            "reward_new": round(new_reward, 4),
        })

    # Rebuild aggregate.json: same schema/order, only values change.
    agg = json.load(agg_path.open())
    rewards = []
    for pr in agg.get("per_rollout", []):
        resc = by_id.get(pr.get("id"))
        if resc is None:
            rewards.append(pr.get("reward"))
            continue
        pr["reward"] = resc["reward"]
        pr["rubric_scores"] = resc["rubric_scores"]
        rewards.append(resc["reward"])
    if rewards:
        agg["mean_reward"] = round(sum(rewards) / len(rewards), 5)
        agg["min_reward"] = round(min(rewards), 4)
        agg["max_reward"] = round(max(rewards), 4)

    if not dry_run:
        bak = roll_path.parent / (roll_path.name + ".pre_ru_bak")
        if not bak.exists():
            shutil.copy2(roll_path, bak)
        with roll_path.open("w") as f:
            for r in rollouts:
                f.write(json.dumps(r) + "\n")
        agg_bak = agg_path.parent / (agg_path.name + ".pre_ru_bak")
        if not agg_bak.exists():
            shutil.copy2(agg_path, agg_bak)
        json.dump(agg, agg_path.open("w"), indent=1)

    return {"changes": changes, "mean_reward": agg.get("mean_reward")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("configs", nargs="*",
                    help="Config dir names (default: all with a phase3 dir)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.configs:
        dirs = [PAPER_RUNS / c / "phase3" for c in args.configs]
    else:
        dirs = sorted(p / "phase3" for p in PAPER_RUNS.iterdir()
                      if (p / "phase3" / "rollouts.jsonl").exists())

    for d in dirs:
        if not (d / "rollouts.jsonl").exists():
            print(f"SKIP (no rollouts): {d}")
            continue
        cfg = d.parent.name
        res = _rescore_config(d, args.dry_run)
        print(f"\n=== {cfg}  (new mean_reward={res['mean_reward']}) ===")
        print(f"  {'set':7s} {'focal':8s} {'looks':>5s}  "
              f"{'RU old':>6s} {'RU new':>6s}  {'POR':>4s} {'HRP':>4s}  "
              f"{'rew old':>7s} {'rew new':>7s}")
        for c in res["changes"]:
            print(f"  {c['set_id']:7s} {c['focal']:8s} {c['lookups']:5d}  "
                  f"{c['ru_old']:6.3f} {c['ru_new']:6.3f}  "
                  f"{c['por']:4.2f} {c['hrp']:4.2f}  "
                  f"{str(c['reward_old']):>7s} {c['reward_new']:7.4f}")
    if args.dry_run:
        print("\n[dry-run] no files written")


if __name__ == "__main__":
    main()
