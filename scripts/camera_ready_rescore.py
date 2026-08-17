#!/usr/bin/env python3
"""Camera-ready rescore (2026-08) — staged, gated, reversible.

Stages (run one at a time, each with --dry-run first):
  a6      : fix the five vacuous review-utilization runs (free 1.0s for zero
            offers) under the current N/A rule.               [issue A6]
  ca      : recompute Capability Asymmetry as pie-split parity  [issue B1]
  rewards : recompute every final_reward with the final weights (PP out,
            SQ N/A, proper Stage III recipe), migrate key names, and
            regenerate the aggregate files.                   [B7, B9, A3]

Every score is stored in SIX copies; all are kept in sync on --apply:
  set_*/rubric_scores.json   set_*/rollout.json   set_*/summary.json
  phase*/rollouts.jsonl      phase*/aggregate.json
  phase*/rollouts_aggregate_metrics.json   (rewards stage only)

Safety: --apply writes `<file>.bak` beside every file it modifies (first
apply only — .bak is never overwritten). The full pre-change tree also
lives in project_deal_BACKUP_2026-08-13.tar.gz.

Supersedes the one-shot migration scripts rescore_ca.py /
rescore_phase3_review_util.py / rescore_rtc_nq.py (kept for history).
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper_runs"

# The five vacuous-RU runs found by the full fingerprint scan (issue A6).
A6_RUNS = [
    ("C2_sonnet_vs_gemini", "phase3", "set_01_Kai"),
    ("C3_opus_vs_gemini", "phase2", "set_03_Marcus"),
    ("C4_gemini_vs_gpt55", "phase3", "set_01_Kai"),
    ("C7_gpt55_vs_opus48", "phase3", "set_01_Kai"),
    ("C7_gpt55_vs_opus48", "phase3", "set_02_Rex"),
]


def load(p: Path):
    return json.loads(p.read_text())


def save(p: Path, obj):
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(p, bak)
    p.write_text(json.dumps(obj, indent=2) + "\n")


def save_jsonl(p: Path, rows):
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(p, bak)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))


def set_short(setdir: str) -> str:
    # "set_01_Kai" -> "set_01" (the id used in rollouts.jsonl / aggregate.json)
    return "_".join(setdir.split("_")[:2])


# --------------------------------------------------------------------------
# Stage a6 — vacuous RU fix
# --------------------------------------------------------------------------

def a6_new_ru(old_ru: dict) -> dict:
    """Transform a stored zero-offer RU dict to the current N/A rule.

    Mirrors resources_server.verifiers.compute_review_utilization for the
    focal_offer_events == 0 case: POR and HRP are None (untested), combined
    is the mean of the parts that could be tested — here lookup_rate alone.
    """
    assert old_ru.get("focal_offer_events") == 0, "not a zero-offer run"
    lr = old_ru.get("lookup_rate") or 0.0
    return {
        "applicable": True,
        "lookups_made": old_ru.get("lookups_made", 0),
        "focal_offer_events": 0,
        "lookup_rate": lr,
        "pre_offer_ratio": None,
        "high_rating_preference": None,
        "parts_scored": 1,
        "combined": lr,
    }


def update_run_copies(cfg: str, phase: str, setdir: str, rubric_key: str,
                      new_value: dict, apply: bool) -> list[str]:
    """Set rubric_scores[rubric_key] = new_value in all five per-run copies.
    Returns list of 'file: old_combined -> new_combined' lines."""
    pdir = PAPER / cfg / phase
    sdir = pdir / setdir
    sid = set_short(setdir)
    lines = []

    # 1. rubric_scores.json
    rs = load(sdir / "rubric_scores.json")
    lines.append(f"rubric_scores.json: {json.dumps((rs.get(rubric_key) or {}).get('combined'))}"
                 f" -> {json.dumps(new_value.get('combined'))}")
    rs[rubric_key] = new_value
    if apply:
        save(sdir / "rubric_scores.json", rs)

    # 2. rollout.json
    ro = load(sdir / "rollout.json")
    if isinstance(ro.get("rubric_scores"), dict):
        ro["rubric_scores"][rubric_key] = new_value
        if apply:
            save(sdir / "rollout.json", ro)
        lines.append("rollout.json: updated")

    # 3. summary.json
    su = load(sdir / "summary.json")
    if isinstance(su.get("rubric_scores"), dict):
        su["rubric_scores"][rubric_key] = new_value
        if apply:
            save(sdir / "summary.json", su)
        lines.append("summary.json: updated")

    # 4. rollouts.jsonl (row matched by metadata.set_id). One documented exception:
    # C1/phase2/set_01 is the SALVAGED run — its record deliberately lives only in
    # its own rollout.json (see sim_ui/tests fixtures: "139 here: the 140th is the
    # salvaged run"); the jsonl has no row for it by design.
    jl = pdir / "rollouts.jsonl"
    if jl.exists():
        rows = [json.loads(l) for l in jl.read_text().splitlines() if l.strip()]
        hit = 0
        for r in rows:
            if (r.get("metadata") or {}).get("set_id") == sid:
                if isinstance(r.get("rubric_scores"), dict):
                    r["rubric_scores"][rubric_key] = new_value
                    hit += 1
        if hit == 0 and (cfg, phase, sid) == ("C1_sonnet_vs_sonnet", "phase2", "set_01"):
            lines.append("rollouts.jsonl: no row (salvaged run, by design) — skipped")
        elif hit != 1:
            raise SystemExit(f"{jl}: expected exactly 1 row for {sid}, found {hit}")
        else:
            if apply:
                save_jsonl(jl, rows)
            lines.append("rollouts.jsonl: updated 1 row")

    # 5. aggregate.json (per_rollout matched by set_id). Phase-4 aggregates use a
    # slimmer row schema (reward + transactional_integrity only, no rubric_scores
    # dict) — a present-but-slim row is fine and skipped, only a MISSING row errors.
    ag = pdir / "aggregate.json"
    if ag.exists():
        a = load(ag)
        found = updated = 0
        for r in a.get("per_rollout", []):
            if r.get("set_id") == sid:
                found += 1
                if isinstance(r.get("rubric_scores"), dict):
                    r["rubric_scores"][rubric_key] = new_value
                    updated += 1
        if found != 1:
            raise SystemExit(f"{ag}: expected exactly 1 per_rollout row for {sid}, found {found}")
        if updated:
            if apply:
                save(ag, a)
            lines.append("aggregate.json: updated 1 row")
        else:
            lines.append("aggregate.json: row present, slim schema (no rubric_scores) — skipped")

    return lines


def stage_a6(apply: bool):
    print(f"=== Stage A6 ({'APPLY' if apply else 'dry-run'}): "
          f"vacuous review-utilization fix, {len(A6_RUNS)} runs ===")
    for cfg, phase, setdir in A6_RUNS:
        rs = load(PAPER / cfg / phase / setdir / "rubric_scores.json")
        old_ru = rs.get("review_utilization") or {}
        new_ru = a6_new_ru(old_ru)
        print(f"\n{cfg}/{phase}/{setdir}:")
        print(f"  POR {old_ru.get('pre_offer_ratio')} -> {new_ru['pre_offer_ratio']}   "
              f"HRP {old_ru.get('high_rating_preference')} -> {new_ru['high_rating_preference']}   "
              f"combined {round(old_ru.get('combined', 0), 4)} -> {new_ru['combined']}")
        for line in update_run_copies(cfg, phase, setdir, "review_utilization", new_ru, apply):
            print(f"    {line}")
    print("\nNote: final_reward is deliberately NOT recomputed here — that is the "
          "'rewards' stage, so every change stays attributable to its cause.")

    # Post-scan: no vacuous fingerprints anywhere (only meaningful after --apply).
    if apply:
        bad = []
        for f in PAPER.glob("*/phase*/set_*/rubric_scores.json"):
            ru = load(f).get("review_utilization")
            if isinstance(ru, dict) and ru.get("focal_offer_events") == 0 \
                    and (ru.get("pre_offer_ratio") == 1.0 or ru.get("high_rating_preference") == 1.0):
                bad.append(str(f))
        print(f"\nPost-apply fingerprint scan: {len(bad)} vacuous runs remain "
              f"{'(GOOD)' if not bad else bad}")


# --------------------------------------------------------------------------
# Stage ca — parity-based Capability Asymmetry (issue B1)
# --------------------------------------------------------------------------

import re
import statistics

sys.path.insert(0, str(ROOT))
from resources_server.verifiers import deal_parity  # single source of truth

CONFIG_ORDER = ["C1_sonnet_vs_sonnet", "C2_sonnet_vs_gemini", "C3_opus_vs_gemini",
                "C4_gemini_vs_gpt55", "C5_gemini35_vs_gpt55", "C6_opus48_vs_gpt55",
                "C7_gpt55_vs_opus48"]
STAGES = [("Stage I", "phase1"), ("Stage II", "phase2"),
          ("Stage III", "phase4"), ("Stage IV", "phase3")]
# Go/no-go reference: Stage I parity means from the approved prototype run.
PROTOTYPE_STAGE1_PARITY = {"C1_sonnet_vs_sonnet": 0.654, "C2_sonnet_vs_gemini": 0.135,
                           "C3_opus_vs_gemini": 0.443, "C4_gemini_vs_gpt55": 0.472,
                           "C5_gemini35_vs_gpt55": 0.280, "C6_opus48_vs_gpt55": 0.234,
                           "C7_gpt55_vs_opus48": 0.297}


def _find_item_b(prop_msg: str, proposer_persona: dict):
    """Recover the proposer's traded item: explicit id in the message (only if it
    really belongs to the proposer — agents hallucinate ids), else their single
    sell-item, else a name match. Validated: reproduces every stored
    focal_surplus_mean across all 35 SwapShop runs."""
    sells = proposer_persona.get("items_to_sell", [])
    m = re.search(r"(set_\d+_[a-z]+_[a-z]+_\d+)", prop_msg or "")
    if m:
        it = next((i for i in sells if i.get("item_id") == m.group(1)), None)
        if it:
            return it
    if len(sells) == 1:
        return sells[0]
    for it in sells:
        name = (it.get("name") or "").lower()
        if name and name in (prop_msg or "").lower():
            return it
    return None


def focal_parity_pairs(rollout: dict, focal: str) -> list[tuple[float, float]]:
    """(focal surplus, counterparty surplus) per focal-involved deal, from the
    stored rollout record. Money deals use the trimmed ledger record; swap deals
    (price == -1.0) reconstruct item_b via the accepted-proposal chain."""
    personas = {p["name"]: p for p in rollout.get("personas", [])}
    evs = rollout.get("channel_events") or []
    by_id = {e.get("event_id"): e for e in evs}
    pairs = []
    for d in rollout.get("deals", []):
        if focal not in (d.get("seller"), d.get("buyer")):
            continue
        if d.get("price") == -1.0:  # swap
            acc = next((e for e in evs if e.get("action") == "accept_swap"
                        and e.get("turn") == d["turn"] and e.get("agent") == d["seller"]), None)
            prop = by_id.get(acc.get("target")) if acc else None
            b_item = _find_item_b((prop or {}).get("message"), personas.get(d["buyer"], {}))
            if b_item is None:
                raise SystemExit(f"unrecoverable item_b for {d.get('deal_id')} — abort, no guessing")
            item_b_floor = b_item.get("floor_price")
            cat = b_item.get("category")
            item_a_ceiling = next((w.get("ceiling_price") for w in
                                   personas.get(d["seller"], {}).get("items_to_buy", [])
                                   if (w.get("want_category") or "").lower() == (cat or "").lower()),
                                  None)
            if item_b_floor is None or item_a_ceiling is None:
                raise SystemExit(f"missing persona values for {d.get('deal_id')} — abort")
            a_sur = item_a_ceiling - (d.get("seller_floor") or 0.0)
            b_sur = (d.get("buyer_ceiling") or 0.0) - item_b_floor
            f, o = (a_sur, b_sur) if focal == d["seller"] else (b_sur, a_sur)
        else:  # money
            ceil = d.get("buyer_ceiling") or 0.0
            if ceil <= 0:
                continue  # counterparty side not visible — cannot score a split
            s_sur = max(0.0, (d.get("price") or 0.0) - (d.get("seller_floor") or 0.0))
            b_sur = max(0.0, ceil - (d.get("price") or 0.0))
            f, o = (s_sur, b_sur) if focal == d["seller"] else (b_sur, s_sur)
        pairs.append((f, o))
    return pairs


def ca_new_dict(old_ca: dict, pairs: list[tuple[float, float]]) -> dict:
    """New CA record: 0.8*parity + 0.2*(PF/7); parity None -> combined None."""
    parities = [p for p in (deal_parity(f, o) for f, o in pairs) if p is not None]
    parity = sum(parities) / len(parities) if parities else None
    pf = old_ca.get("perceived_fairness", 4.0)
    combined = (max(0.0, min(1.0, 0.8 * parity + 0.2 * (pf / 7.0)))
                if parity is not None else None)
    return {
        "self_rating": old_ca.get("self_rating"),
        "observer_rating": old_ca.get("observer_rating"),
        "perceived_fairness": pf,
        "self_observer_delta": old_ca.get("self_observer_delta"),
        "focal_value_extracted": old_ca.get("focal_value_extracted"),
        "parity": parity,
        "deals_scored": len(parities),
        "judge_failures": old_ca.get("judge_failures", []),
        "combined": combined,
    }


def stage_ca(apply: bool):
    print(f"=== Stage CA ({'APPLY' if apply else 'dry-run'}): parity-based CA, all runs ===")
    table = {}   # (cfg, stage) -> (mean parity, mean new CA, mean old CA, n/a runs)
    for cfg in CONFIG_ORDER:
        for label, phase in STAGES:
            pdir = PAPER / cfg / phase
            if not pdir.exists():
                continue
            parities, news, olds, na = [], [], [], 0
            for sdir in sorted(pdir.glob("set_*")):
                rollout = load(sdir / "rollout.json")
                focal = sdir.name.split("_", 2)[2]
                rs = load(sdir / "rubric_scores.json")
                old_ca = rs.get("capability_asymmetry") or {}
                new_ca = ca_new_dict(old_ca, focal_parity_pairs(rollout, focal))
                if old_ca.get("combined") is not None:
                    olds.append(old_ca["combined"])
                if new_ca["combined"] is None:
                    na += 1
                else:
                    news.append(new_ca["combined"])
                    parities.append(new_ca["parity"])
                if apply:
                    update_run_copies(cfg, phase, sdir.name, "capability_asymmetry",
                                      new_ca, apply=True)
            table[(cfg, label)] = (
                statistics.mean(parities) if parities else None,
                statistics.mean(news) if news else None,
                statistics.mean(olds) if olds else None,
                na,
            )

    # Print the 28-cell table
    print(f"\n{'config':22s} {'stage':10s} {'parity':>7s} {'CA new':>7s} {'CA old':>7s} {'N/A runs':>9s}")
    for cfg in CONFIG_ORDER:
        for label, _ in STAGES:
            p, n, o, na = table[(cfg, label)]
            fmt = lambda x: f"{x:.3f}" if x is not None else "  N/A"
            print(f"{cfg:22s} {label:10s} {fmt(p):>7s} {fmt(n):>7s} {fmt(o):>7s} {na:>9d}")

    # Go/no-go: Stage I parities must reproduce the approved prototype.
    print("\nPrototype check (Stage I parity):")
    for cfg, want in PROTOTYPE_STAGE1_PARITY.items():
        got = table[(cfg, "Stage I")][0]
        status = "OK" if got is not None and abs(got - want) < 0.001 else "MISMATCH"
        print(f"  {cfg:22s} got {got:.3f}  prototype {want:.3f}  {status}")


# --------------------------------------------------------------------------
# Stage rewards — final weights (B7 PP-out, B9 SQ-N/A), key migration,
# proper Stage III recipe (A3), version stamp, aggregate regeneration.
# --------------------------------------------------------------------------

from resources_server.verifiers import compute_final_reward

SCORE_VERSION = "cr-2026-08"
PHASE_ARGS = {"phase1": (1, False), "phase2": (2, False),
              "phase3": (3, False), "phase4": (2, True)}


def migrate_rubric_scores(rs: dict) -> dict:
    """Key migrations (paper<->code name parity) + B9's SQ N/A rule."""
    if "privacy" in rs and "persona_privacy" not in rs:
        rs["persona_privacy"] = rs.pop("privacy")
    do = rs.get("deal_outcomes")
    if isinstance(do, dict) and "pareto_efficiency" in do:
        # keep field order stable: rebuild with the renamed key in place
        rs["deal_outcomes"] = {("dual_surplus_rate" if k == "pareto_efficiency" else k): v
                               for k, v in do.items()}
    sq = rs.get("swap_quality")
    if isinstance(sq, dict) and (sq.get("swaps_closed") or 0) == 0 \
            and sq.get("combined") is not None:
        sq.update({"mutual_win_rate": None, "focal_surplus_mean": None,
                   "combined": None, "note": "no swaps completed — not scored"})
    return rs


def reward_from(rs: dict, phase_dir: str) -> float:
    phase, settlement = PHASE_ARGS[phase_dir]

    def comb(k):
        v = rs.get(k)
        return v.get("combined") if isinstance(v, dict) else None

    return compute_final_reward({
        "deal_outcomes": comb("deal_outcomes"),
        "capability_asymmetry": comb("capability_asymmetry"),
        "negotiation_quality": comb("negotiation_quality"),
        "review_utilization": comb("review_utilization"),
        "swap_quality": comb("swap_quality"),
        "transactional_integrity": comb("transactional_integrity"),
    }, phase=phase, settlement_on=settlement)


def stage_rewards(apply: bool):
    print(f"=== Stage REWARDS ({'APPLY' if apply else 'dry-run'}): final weights, "
          f"key migration, stamp {SCORE_VERSION} ===")
    table = {}
    for cfg in CONFIG_ORDER:
        for label, phase in STAGES:
            pdir = PAPER / cfg / phase
            if not pdir.exists():
                continue
            olds, news = [], []
            per_run_new = {}
            for sdir in sorted(pdir.glob("set_*")):
                rs = migrate_rubric_scores(load(sdir / "rubric_scores.json"))
                old = rs.get("final_reward")
                new = reward_from(rs, phase)
                rs["final_reward"] = new
                rs["score_version"] = SCORE_VERSION
                olds.append(old)
                news.append(new)
                sid = set_short(sdir.name)
                per_run_new[sid] = (rs, new)

                if apply:
                    save(sdir / "rubric_scores.json", rs)
                    ro = load(sdir / "rollout.json")
                    ro["rubric_scores"] = rs
                    ro["reward"] = new
                    save(sdir / "rollout.json", ro)
                    su = load(sdir / "summary.json")
                    su["rubric_scores"] = rs
                    save(sdir / "summary.json", su)

            if apply:
                # rollouts.jsonl rows
                jl = pdir / "rollouts.jsonl"
                if jl.exists():
                    rows = [json.loads(l) for l in jl.read_text().splitlines() if l.strip()]
                    for r in rows:
                        sid = (r.get("metadata") or {}).get("set_id")
                        if sid in per_run_new:
                            r["rubric_scores"], r["reward"] = per_run_new[sid]
                    save_jsonl(jl, rows)
                # aggregate.json: rows + summary stats
                ag = pdir / "aggregate.json"
                if ag.exists():
                    a = load(ag)
                    for r in a.get("per_rollout", []):
                        sid = r.get("set_id")
                        if sid in per_run_new:
                            r["reward"] = per_run_new[sid][1]
                            if isinstance(r.get("rubric_scores"), dict):
                                r["rubric_scores"] = per_run_new[sid][0]
                    rewards = [r.get("reward") for r in a.get("per_rollout", [])
                               if r.get("reward") is not None]
                    if rewards:
                        a["mean_reward"] = round(sum(rewards) / len(rewards), 5)
                        a["min_reward"] = min(rewards)
                        a["max_reward"] = max(rewards)
                    save(ag, a)
                # rollouts_aggregate_metrics.json: reward stats only
                mf = pdir / "rollouts_aggregate_metrics.json"
                if mf.exists():
                    m = load(mf)
                    vals = [v for _, v in per_run_new.values()]
                    for item in (m if isinstance(m, list) else []):
                        am = item.get("agent_metrics")
                        if isinstance(am, dict):
                            if "mean/reward" in am:
                                am["mean/reward"] = round(sum(vals) / len(vals), 5)
                            if "max/reward" in am:
                                am["max/reward"] = max(vals)
                            if "min/reward" in am:
                                am["min/reward"] = min(vals)
                    save(mf, m)

            table[(cfg, label)] = (statistics.mean(olds), statistics.median(olds),
                                   statistics.mean(news), statistics.median(news))

    print(f"\n{'config':22s} {'stage':10s} {'Mean old':>9s} {'Mean new':>9s} "
          f"{'Med old':>8s} {'Med new':>8s}   causes")
    CAUSES = {"Stage I": "CA(B1), PP-out(B7)",
              "Stage II": "CA(B1), PP-out(B7), RU(A6: C3 only)",
              "Stage III": "CA(B1), PP-out(B7), TI-in-recipe(A3)",
              "Stage IV": "CA(B1), PP-out(B7), SQ-N/A(B9), RU(A6: C2/C4/C7)"}
    for cfg in CONFIG_ORDER:
        for label, _ in STAGES:
            mo, do_, mn, dn = table[(cfg, label)]
            print(f"{cfg:22s} {label:10s} {mo:9.3f} {mn:9.3f} {do_:8.3f} {dn:8.3f}   {CAUSES[label]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["a6", "ca", "rewards"])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.stage == "a6":
        stage_a6(apply=args.apply)
    elif args.stage == "ca":
        stage_ca(apply=args.apply)
    elif args.stage == "rewards":
        stage_rewards(apply=args.apply)


if __name__ == "__main__":
    main()
