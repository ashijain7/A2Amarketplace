"""
Re-score Capability Asymmetry to the two-factor formula, ARITHMETIC ONLY
(no re-running rollouts, no LLM judge calls). Runs on top of the current
(post-RTC/NQ) data.

NEW CA:
  money stages (phase 1,2,4):  CA = 0.6*min(SM/50, 1)          + 0.4*(PF/7)
  swap  stage  (phase 3):      CA = 0.6*clamp((FSM+5)/10, 0,1) + 0.4*(PF/7)
where SM  = capability_asymmetry.focal_value_extracted (dollars; money deals),
      FSM = swap_quality.focal_surplus_mean (item-value surplus; barter),
      PF  = capability_asymmetry.perceived_fairness (1-7).
Replaces the old asymmetry placeholder (combined = 0.3 + 0.4*PF/7).

CA is ~20-27% of the reward, so the reward is recomputed too (same weights as
the current scheme: NQ already dropped from phase-3; privacy under persona_privacy
or legacy privacy; phase-4 weighting auto-detected).

USAGE
  python scripts/rescore_ca.py --check     # prove current rewards reproduce
  python scripts/rescore_ca.py --dry-run   # show old->new CA + reward
  python scripts/rescore_ca.py --apply
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper_runs"

W1 = {"deal_outcomes": 0.325, "capability_asymmetry": 0.275, "negotiation_quality": 0.225, "privacy": 0.175}
W2 = {"deal_outcomes": 0.25, "capability_asymmetry": 0.20, "negotiation_quality": 0.20, "privacy": 0.15, "review_utilization": 0.20}
W3 = {"deal_outcomes": 0.10, "capability_asymmetry": 0.15, "privacy": 0.10, "review_utilization": 0.20, "swap_quality": 0.30}  # NQ dropped
W3_OLD = {"deal_outcomes": 0.10, "capability_asymmetry": 0.15, "negotiation_quality": 0.15, "privacy": 0.10, "review_utilization": 0.20, "swap_quality": 0.30}
PHASE4_CANDIDATES = [W2, W3_OLD]
TOL = 1e-3
SM_CAP = 50.0
FSM_HALF = 5.0  # break-even FSM=0 -> 0.5, +5 -> 1.0, -5 -> 0.0


def clamp01(x): return max(0.0, min(1.0, x))
def comb(rs, k):
    x = rs.get(k); return x.get("combined") if isinstance(x, dict) else None
def field(rs, k, f):
    x = rs.get(k); return x.get(f) if isinstance(x, dict) else None
def priv_comb(rs):
    for k in ("persona_privacy", "privacy"):
        x = rs.get(k)
        if isinstance(x, dict): return x.get("combined")
    return None


def new_ca(rs, phase):
    pf = field(rs, "capability_asymmetry", "perceived_fairness") or 0.0
    if phase == 3:
        fsm = field(rs, "swap_quality", "focal_surplus_mean") or 0.0
        asym = clamp01((fsm + FSM_HALF) / (2 * FSM_HALF))
    else:
        sm = field(rs, "capability_asymmetry", "focal_value_extracted") or 0.0
        asym = min(sm / SM_CAP, 1.0)
    return round(0.6 * asym + 0.4 * (pf / 7.0), 4)


def weighted(parts, weights):
    tot = wu = 0.0
    for k, w in weights.items():
        v = parts.get(k)
        if v is not None:
            tot += v * w; wu += w
    return (round(tot / wu, 4) if wu > 0 else 0.0), wu


def parts_of(rs, ca_value):
    return {
        "deal_outcomes": comb(rs, "deal_outcomes"),
        "capability_asymmetry": ca_value,
        "negotiation_quality": comb(rs, "negotiation_quality"),
        "privacy": priv_comb(rs),
        "review_utilization": comb(rs, "review_utilization"),
        "swap_quality": comb(rs, "swap_quality"),
    }


def reward_with(rs, phase, ca_value, stored=None):
    """Reward using the given CA value; phase-4 weighting auto-detected."""
    if phase == 1:
        return weighted(parts_of(rs, ca_value), W1)[0]
    if phase == 2:
        return weighted(parts_of(rs, ca_value), W2)[0]
    if phase == 3:
        return weighted(parts_of(rs, ca_value), W3)[0]
    # phase 4: pick the candidate weighting that reproduced the stored reward
    cur_ca = comb(rs, "capability_asymmetry")
    best = None
    for W in PHASE4_CANDIDATES:
        r = weighted(parts_of(rs, cur_ca), W)[0]
        if best is None or abs(r - (stored or 0)) < abs(best[1] - (stored or 0)):
            best = (W, r)
    return weighted(parts_of(rs, ca_value), best[0])[0]


def backup(p):
    b = p.with_suffix(p.suffix + ".pre_ca_bak")
    if not b.exists(): shutil.copy2(p, b)


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
                rs = r.get("rubric_scores") or {}
                repro = reward_with(rs, phase, comb(rs, "capability_asymmetry"), r.get("reward"))
                if r.get("reward") is not None and abs(repro - r["reward"]) > TOL:
                    fails.append((r.get("id"), r["reward"], repro))
            rep[phase] = {"fails": fails, "n": len(rollouts)}
            continue

        corr = {}; rows = []; cavals = []
        for r in rollouts:
            rs = r.get("rubric_scores") or {}
            stored = r.get("reward")
            old_ca = comb(rs, "capability_asymmetry")
            nca = new_ca(rs, phase)
            nrew = reward_with(rs, phase, nca, stored)
            if isinstance(rs.get("capability_asymmetry"), dict):
                rs["capability_asymmetry"]["combined"] = nca
            rs["final_reward"] = nrew
            r["reward"] = nrew
            corr[r.get("id")] = (nrew, rs, nca)
            cavals.append(nca)
            rows.append(((r.get("metadata") or {}).get("focal_persona"), old_ca, nca, stored, nrew))

        # aggregate.json
        if agg_path.exists():
            agg = json.load(agg_path.open())
            rewards = []
            for pr in agg.get("per_rollout", []):
                cid = pr.get("id")
                if cid in corr:
                    nrew, nrs, nca = corr[cid]
                    pr["reward"] = nrew
                    prs = pr.get("rubric_scores")
                    if isinstance(prs, dict):
                        if isinstance(prs.get("capability_asymmetry"), dict):
                            prs["capability_asymmetry"]["combined"] = nca
                        prs["final_reward"] = nrew
                rewards.append(pr.get("reward"))
            if rewards:
                agg["mean_reward"] = round(sum(rewards) / len(rewards), 5)
                agg["min_reward"] = round(min(rewards), 4)
                agg["max_reward"] = round(max(rewards), 4)

        # archives
        for sd in sorted(pdir.glob("set_*")):
            rj = sd / "rollout.json"
            if not rj.exists(): continue
            ro = json.load(rj.open())
            cid = ro.get("id")
            if cid in corr:
                nrew, nrs, nca = corr[cid]
                ro["reward"] = nrew; ro["rubric_scores"] = nrs
            else:
                rs2 = ro.get("rubric_scores") or {}
                nca = new_ca(rs2, phase)
                if isinstance(rs2.get("capability_asymmetry"), dict):
                    rs2["capability_asymmetry"]["combined"] = nca
                nrew = reward_with(rs2, phase, nca, ro.get("reward"))
                rs2["final_reward"] = nrew; ro["reward"] = nrew
            if mode == "apply":
                backup(rj); json.dump(ro, rj.open("w"), indent=1)
                rsj = sd / "rubric_scores.json"
                if rsj.exists(): backup(rsj); json.dump(ro["rubric_scores"], rsj.open("w"), indent=1)
                sj = sd / "summary.json"
                if sj.exists():
                    s = json.load(sj.open()); s["rubric_scores"] = ro["rubric_scores"]
                    backup(sj); json.dump(s, sj.open("w"), indent=1)

        if mode == "apply":
            backup(roll_path)
            with roll_path.open("w") as f:
                for r in rollouts: f.write(json.dumps(r) + "\n")
            if agg_path.exists():
                backup(agg_path); json.dump(agg, agg_path.open("w"), indent=1)

        rep[phase] = {"ca_mean": round(sum(cavals)/len(cavals), 3) if cavals else None,
                      "mean_reward": agg.get("mean_reward") if agg_path.exists() else None,
                      "rows": rows}
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("configs", nargs="*")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    mode = "check" if a.check else ("apply" if a.apply else "dry")
    cfgs = a.configs or [p.name for p in sorted(PAPER.iterdir()) if p.is_dir() and (p / "phase1").exists()]
    any_fail = False
    for cfg in cfgs:
        rep = process(PAPER / cfg, mode)
        print(f"\n=== {cfg} ===")
        for ph, d in sorted(rep.items()):
            if mode == "check":
                if d["fails"]:
                    any_fail = True
                    print(f"  phase{ph}: {len(d['fails'])}/{d['n']} MISMATCH")
                    for cid, old, new in d["fails"][:4]:
                        print(f"      id={cid}: stored={old} repro={new}")
                else:
                    print(f"  phase{ph}: OK ({d['n']})")
            else:
                print(f"  phase{ph}: CA.mean -> {d['ca_mean']}   mean_reward -> {d['mean_reward']}")
                for persona, oca, nca, orew, nrew in d["rows"]:
                    print(f"      {str(persona):8s} CA {oca} -> {nca}   reward {orew} -> {nrew}")
    if mode == "check":
        print("\n" + ("CHECK FAILED" if any_fail else "CHECK PASSED"))
        sys.exit(1 if any_fail else 0)
    elif mode == "dry":
        print("\n[dry-run] nothing written")


if __name__ == "__main__":
    main()
