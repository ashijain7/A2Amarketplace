"""
Re-score paper runs for two corrections + one bug fix, ARITHMETIC ONLY
(no re-running rollouts, no LLM judge calls).

CHANGES
-------
1. RTC normalizer 20 -> 100 (all stages). deal_outcomes.rounds_to_close is in
   channel-turns (0..100), so /100 is the correct normalizer and matches the
   paper's stated "100-turn cap". rounds_score = max(0, 1 - rtc/100). This
   shifts deal_outcomes.combined in every phase (and the reward).
2. Drop Negotiation Quality from Stage IV (phase 3 / SwapShop) only. In barter
   NQ is a constant 0.60 (anchoring/smoothness default 0.5, deadlock 1.0) -> no
   signal. Removed from the phase-3 reward weights; stored as None.
3. Restore persona-privacy to the phase-3 reward for C9/C10. The June RU re-score
   looked up only the legacy key "privacy"; C9/C10 store it under "persona_privacy"
   so privacy (0.10) was dropped from their swap-stage reward. The original-5
   (legacy key) were unaffected. priv_comb() reads whichever key exists.

PHASE-4 NOTE: those settlement rewards were scored with inconsistent weights
(C1/C4/C6/C8 used phase-3 weights, C7/C9/C10 used phase-2). We do NOT change that
weighting; we detect it per rollout and apply only the RTC delta to the reward.

SOURCE OF TRUTH: rollouts.jsonl. aggregate.json and the per-rollout archive
folders (rubric_scores.json / rollout.json / summary.json) are synced from it.

USAGE
  python scripts/rescore_rtc_nq.py --check     # prove OLD logic reproduces stored
  python scripts/rescore_rtc_nq.py --dry-run   # show old->new, write nothing
  python scripts/rescore_rtc_nq.py --apply      # write in place (+ *.pre_rtc_nq_bak)
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper_runs"

W1 = {"deal_outcomes": 0.325, "capability_asymmetry": 0.275, "negotiation_quality": 0.225, "privacy": 0.175}
W2 = {"deal_outcomes": 0.25, "capability_asymmetry": 0.20, "negotiation_quality": 0.20, "privacy": 0.15, "review_utilization": 0.20}
W3_OLD = {"deal_outcomes": 0.10, "capability_asymmetry": 0.15, "negotiation_quality": 0.15, "privacy": 0.10, "review_utilization": 0.20, "swap_quality": 0.30}
W3_NEW = {"deal_outcomes": 0.10, "capability_asymmetry": 0.15, "privacy": 0.10, "review_utilization": 0.20, "swap_quality": 0.30}  # NQ dropped
PHASE4_CANDIDATES = [W2, W3_OLD]  # detect which one a phase-4 rollout used
MAX_ROUNDS_NEW = 100.0
TOL = 1e-3


def clamp01(x):
    return max(0.0, min(1.0, x))


def comb(rs, key):
    x = rs.get(key)
    return x.get("combined") if isinstance(x, dict) else None


def priv_comb(rs):
    """Privacy combined, tolerant of legacy 'privacy' (original-5) vs renamed
    'persona_privacy' (C9/C10 + phase-4). A rename, not missing data."""
    for k in ("persona_privacy", "privacy"):
        x = rs.get(k)
        if isinstance(x, dict):
            return x.get("combined")
    return None


def do_combined_new(rs):
    ds = rs.get("deal_outcomes")
    if not isinstance(ds, dict):
        return None
    rtc = ds.get("rounds_to_close") or 0.0
    rscore = max(0.0, 1.0 - rtc / MAX_ROUNDS_NEW)
    c = (0.40 * (ds.get("closure_rate") or 0.0)
         + 0.20 * (ds.get("pareto_efficiency") or 0.0)
         + 0.15 * (ds.get("seller_profit") or 0.0)
         + 0.15 * (ds.get("buyer_surplus") or 0.0)
         + 0.10 * rscore)
    return clamp01(c)


def weighted(parts, weights):
    tot = wu = 0.0
    for k, w in weights.items():
        v = parts.get(k)
        if v is not None:
            tot += v * w
            wu += w
    return (round(tot / wu, 4) if wu > 0 else 0.0), wu


def parts_of(rs, do_value, privacy):
    return {
        "deal_outcomes": do_value,
        "capability_asymmetry": comb(rs, "capability_asymmetry"),
        "negotiation_quality": comb(rs, "negotiation_quality"),
        "privacy": privacy,
        "review_utilization": comb(rs, "review_utilization"),
        "swap_quality": comb(rs, "swap_quality"),
    }


def reproduce_old(rs, phase, stored):
    """Return (reproduced_reward, weights_used) for the CURRENTLY-stored reward."""
    do_old = comb(rs, "deal_outcomes")
    if phase == 1:
        return weighted(parts_of(rs, do_old, priv_comb(rs)), W1)[0], W1
    if phase == 2:
        return weighted(parts_of(rs, do_old, priv_comb(rs)), W2)[0], W2
    if phase == 3:
        # June RU re-score looked up only legacy "privacy"
        return weighted(parts_of(rs, do_old, comb(rs, "privacy")), W3_OLD)[0], W3_OLD
    # phase 4: detect weighting closest to stored
    p = parts_of(rs, do_old, priv_comb(rs))
    best = None
    for W in PHASE4_CANDIDATES:
        r = weighted(p, W)[0]
        if best is None or abs(r - (stored or 0)) < abs(best[0] - (stored or 0)):
            best = (r, W)
    return best


def corrected(rs, phase, stored):
    """Return (new_reward, new_do_combined). Mutates nothing."""
    do_old = comb(rs, "deal_outcomes")
    do_new = do_combined_new(rs)
    if phase == 1:
        return weighted(parts_of(rs, do_new, priv_comb(rs)), W1)[0], do_new
    if phase == 2:
        return weighted(parts_of(rs, do_new, priv_comb(rs)), W2)[0], do_new
    if phase == 3:
        # NQ dropped (W3_NEW), privacy restored via priv_comb
        return weighted(parts_of(rs, do_new, priv_comb(rs)), W3_NEW)[0], do_new
    # phase 4: keep detected weighting, change only DO via delta
    _, W = reproduce_old(rs, phase, stored)
    p = parts_of(rs, do_old, priv_comb(rs))
    wu = sum(W[k] for k in W if p.get(k) is not None)
    delta = (W["deal_outcomes"] / wu) * (do_new - do_old) if wu else 0.0
    return round((stored or 0.0) + delta, 4), do_new


def apply_rs(rs, phase, stored):
    new_rew, do_new = corrected(rs, phase, stored)
    ds = rs.get("deal_outcomes")
    if isinstance(ds, dict):
        ds["combined"] = do_new
    if phase == 3:
        rs["negotiation_quality"] = None
    rs["final_reward"] = new_rew
    return new_rew, do_new


def backup(path):
    bak = path.with_suffix(path.suffix + ".pre_rtc_nq_bak")
    if not bak.exists():
        shutil.copy2(path, bak)


def process(cfg_dir, mode):
    rep = {}
    for phase in (1, 2, 3, 4):
        pdir = cfg_dir / f"phase{phase}"
        roll_path = pdir / "rollouts.jsonl"
        agg_path = pdir / "aggregate.json"
        if not roll_path.exists():
            continue
        rollouts = [json.loads(l) for l in roll_path.open() if l.strip()]

        if mode == "check":
            fails = []
            for r in rollouts:
                stored = r.get("reward")
                repro, _ = reproduce_old(r.get("rubric_scores") or {}, phase, stored)
                if stored is not None and abs(repro - stored) > TOL:
                    fails.append((r.get("id"), stored, repro))
            rep[phase] = {"fails": fails, "n": len(rollouts)}
            continue

        old_mean = None
        if agg_path.exists():
            old_mean = json.load(agg_path.open()).get("mean_reward")

        corr = {}
        rows = []
        do_vals = []
        for r in rollouts:
            rs = r.get("rubric_scores") or {}
            stored = r.get("reward")
            new_rew, do_new = apply_rs(rs, phase, stored)
            r["reward"] = new_rew
            corr[r.get("id")] = (new_rew, rs)
            if do_new is not None:
                do_vals.append(do_new)
            rows.append((( r.get("metadata") or {}).get("focal_persona"), stored, new_rew, do_new))

        # aggregate.json
        if agg_path.exists():
            agg = json.load(agg_path.open())
            rewards = []
            for pr in agg.get("per_rollout", []):
                cid = pr.get("id")
                if cid in corr:
                    nrew, nrs = corr[cid]
                    pr["reward"] = nrew
                    prs = pr.get("rubric_scores")
                    if isinstance(prs, dict):
                        if isinstance(prs.get("deal_outcomes"), dict):
                            prs["deal_outcomes"]["combined"] = nrs["deal_outcomes"]["combined"]
                        if phase == 3:
                            prs["negotiation_quality"] = None
                        prs["final_reward"] = nrew
                rewards.append(pr.get("reward"))
            if rewards:
                agg["mean_reward"] = round(sum(rewards) / len(rewards), 5)
                agg["min_reward"] = round(min(rewards), 4)
                agg["max_reward"] = round(max(rewards), 4)

        # archives: sync wholesale from corrected rollouts
        warn = []
        for sd in sorted(pdir.glob("set_*")):
            rj = sd / "rollout.json"
            if not rj.exists():
                continue
            ro = json.load(rj.open())
            cid = ro.get("id")
            if cid in corr:
                ro["reward"], ro["rubric_scores"] = corr[cid]
            else:
                rs2 = ro.get("rubric_scores") or {}
                ro["reward"], _ = apply_rs(rs2, phase, ro.get("reward"))
                warn.append(sd.name)
            if mode == "apply":
                backup(rj); json.dump(ro, rj.open("w"), indent=1)
                rsj = sd / "rubric_scores.json"
                if rsj.exists():
                    backup(rsj); json.dump(ro["rubric_scores"], rsj.open("w"), indent=1)
                sj = sd / "summary.json"
                if sj.exists():
                    s = json.load(sj.open())
                    s["rubric_scores"] = ro["rubric_scores"]
                    ca = ro["rubric_scores"].get("capability_asymmetry")
                    if isinstance(ca, dict) and "focal_value_extracted" in s:
                        s["focal_value_extracted"] = ca.get("focal_value_extracted")
                    backup(sj); json.dump(s, sj.open("w"), indent=1)

        if mode == "apply":
            backup(roll_path)
            with roll_path.open("w") as f:
                for r in rollouts:
                    f.write(json.dumps(r) + "\n")
            if agg_path.exists():
                backup(agg_path); json.dump(agg, agg_path.open("w"), indent=1)

        rep[phase] = {
            "mean_old": old_mean,
            "mean_new": round(sum(c[0] for c in corr.values()) / len(corr), 5) if corr else None,
            "do_mean_new": round(sum(do_vals) / len(do_vals), 4) if do_vals else None,
            "rows": rows, "warn": warn,
        }
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("configs", nargs="*")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    mode = "check" if args.check else ("apply" if args.apply else "dry")
    cfgs = args.configs or [p.name for p in sorted(PAPER.iterdir())
                            if p.is_dir() and (p / "phase1").exists()]

    any_fail = False
    for cfg in cfgs:
        rep = process(PAPER / cfg, mode)
        print(f"\n=== {cfg} ===")
        for phase, d in sorted(rep.items()):
            if mode == "check":
                if d["fails"]:
                    any_fail = True
                    print(f"  phase{phase}: {len(d['fails'])}/{d['n']} MISMATCH")
                    for cid, old, new in d["fails"][:5]:
                        print(f"      id={cid}: stored={old} repro={new}")
                else:
                    print(f"  phase{phase}: OK ({d['n']})")
            else:
                print(f"  phase{phase}: mean {d['mean_old']} -> {d['mean_new']}   DO.mean(new)={d['do_mean_new']}")
                for persona, old, new, do in d["rows"]:
                    print(f"      {str(persona):8s} {old} -> {new}   DO={round(do,4) if do is not None else None}")
                if d["warn"]:
                    print(f"      [in-place archives: {', '.join(d['warn'])}]")
    if mode == "check":
        print("\n" + ("CHECK FAILED" if any_fail else "CHECK PASSED: all stored rewards reproduce"))
        sys.exit(1 if any_fail else 0)
    elif mode == "dry":
        print("\n[dry-run] nothing written")


if __name__ == "__main__":
    main()
