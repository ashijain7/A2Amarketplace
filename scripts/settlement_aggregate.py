"""Build aggregate.json + INSIGHTS.md for a settlement run.

Same shape as the paper-run aggregate, extended with the Transactional-Integrity
scores (5 areas + combined) and a per-rollout settlement play-by-play summary
(method chosen, reached CONFIRMED?, chat leaks, scam outcome).

Usage: settlement_aggregate.py <rollouts.jsonl> <out_dir> <config> <phase> <scam> <wall_secs>
"""

import json
import os
import sys


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _ti(r):
    return (r.get("rubric_scores") or {}).get("transactional_integrity")


def _settle_summary(r):
    recs = r.get("settlement_records") or []
    # a leak is a secret that appeared in chat (room/public), NOT the pay tool
    chat_leaks = sum(
        len([e for e in (x.get("exposed_secret") or []) if e.get("channel") != "pay_tool"])
        for x in recs
    )
    return {
        "num_settlement_deals": len(recs),
        "confirmed": sum(1 for x in recs if x.get("stage") == "CONFIRMED"),
        "methods": [x.get("chosen_method") for x in recs],
        "chat_leaks": chat_leaks,
        "scam_outcomes": [x.get("outcome") for x in recs if x.get("scam_on")],
    }


def main():
    rollouts_path, out_dir, config, phase, scam, wall = sys.argv[1:7]
    rollouts = []
    if os.path.exists(rollouts_path):
        rollouts = [json.loads(l) for l in open(rollouts_path) if l.strip()]

    per = []
    for r in rollouts:
        t = _ti(r)
        per.append({
            "id": r.get("id"),
            "set_id": (r.get("metadata") or {}).get("set_id"),
            "focal_persona": (r.get("metadata") or {}).get("focal_persona"),
            "reward": r.get("reward"),
            "transactional_integrity": (
                {"combined": t.get("combined"), "areas": t.get("areas"),
                 "measures": t.get("measures")} if t else None),
            "settlement": _settle_summary(r),
            "num_deals": len(r.get("deals") or []),
        })

    agg = {
        "config_name": config, "phase": int(phase), "scam": scam,
        "rollout_count": len(rollouts),
        "mean_reward": _mean([r.get("reward") for r in rollouts]),
        "mean_transactional_integrity": _mean([(_ti(r) or {}).get("combined") for r in rollouts]),
        "per_rollout": per,
    }
    os.makedirs(out_dir, exist_ok=True)
    agg_path = os.path.join(out_dir, "aggregate.json")
    with open(agg_path, "w") as f:
        f.write(json.dumps(agg, indent=2))

    # ---- INSIGHTS.md (paper template + a Settlement section) ----
    L = []
    L.append(f"# INSIGHTS — settlement / {config} / phase {phase} (scam {scam})\n")
    L.append(f"**Rollouts:** {agg['rollout_count']}  ·  **Wall:** {wall}s")
    L.append(f"**Mean reward:** {agg['mean_reward']}  ·  "
             f"**Mean Transactional Integrity:** {agg['mean_transactional_integrity']}\n")
    L.append("## Per-rollout settlement\n")
    L.append("| set | focal | TI | deals | confirmed | methods | chat leaks | scam outcomes |")
    L.append("|-----|-------|---:|------:|----------:|---------|-----------:|---------------|")
    for r in per:
        ti = r.get("transactional_integrity") or {}
        s = r.get("settlement") or {}
        tic = ti.get("combined")
        tic = "n/a" if tic is None else round(tic, 3)
        methods = ", ".join(str(m) for m in (s.get("methods") or [])) or "—"
        scams = ", ".join(str(o) for o in (s.get("scam_outcomes") or [])) or "—"
        L.append(
            f"| {r.get('set_id')} | {r.get('focal_persona')} | {tic} | "
            f"{s.get('num_settlement_deals')} | {s.get('confirmed')} | {methods} | "
            f"{s.get('chat_leaks')} | {scams} |"
        )
    L.append("\n## Area scores (per rollout)\n")
    for r in per:
        ti = r.get("transactional_integrity") or {}
        L.append(f"- **{r.get('focal_persona')}**: {ti.get('areas')}")
    L.append("\n## Findings\n\n_(filled in after reading the transcripts + data/ng_run/*/settlement.json)_\n")
    with open(os.path.join(out_dir, "INSIGHTS.md"), "w") as f:
        f.write("\n".join(L))

    print(f"wrote {agg_path} + INSIGHTS.md  (mean_TI={agg['mean_transactional_integrity']})")


if __name__ == "__main__":
    main()
