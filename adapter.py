#!/usr/bin/env python3
"""adapter.py — the RLEaaS "Run button" for the project_deal marketplace.

One command -> one fresh, trustworthy reward. Translates 4 user choices
(phase, set, focal, opponent) into the engine's internal knobs, runs one fresh
rollout per set, and writes result.json.

This file is sub-task 2a: the CLI + input->internal MAPPING + --dry-run only.
It executes nothing yet. Live execution (reset env.yaml, restart the stack, run
the rollout, extract the reward) is wired in sub-tasks 2b-2e.

Run via uv, from the project_deal dir:
    uv run python adapter.py --phase transaction --set 03 \
        --focal opus --opponent gpt --max-turns 100 --dry-run
"""

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Single source of truth for the model strings (no duplicated literals).
from marketplace import config as mp_config

import platform_export

# project_deal root (this file lives at its top level).
ROOT = Path(__file__).resolve().parent

# The env var the adapter exports before boot so the resources server picks up
# the chosen opponent model (read in resources_server/model_config.py).
OPPONENTS_ENV = "MARKETPLACE_OPPONENTS_MODEL"

# Isolated per-run output lives here — NEVER the git-tracked results/paper_runs/.
ADAPTER_RUNS_DIR = ROOT / "results" / "adapter_runs"

# Per-rollout marketplace scratch the server writes under here; cleared each run.
SESSION_SCRATCH_DIR = ROOT / "data" / "ng_run"


# --- mappings: user-facing choice -> engine internals -----------------

# phase name -> (MARKETPLACE_PHASE value, ENABLE_SETTLEMENT).
# Note the deliberate remap: the adapter's phase names do NOT line up with the
# internal phase numbers (transaction is base phase 2 + a flag; swap_shop is
# internal phase 3). That mismatch is exactly why --phase takes a name, not a number.
PHASE_MAP = {
    "market_deal": ("1", False),
    "review":      ("2", False),
    "transaction": ("2", True),   # always base phase 2 + settlement
    "swap_shop":   ("3", False),
}

# short alias -> full "provider/model" string. A full string with a "/" is
# accepted as-is, so any OpenRouter model works even without an alias.
MODEL_ALIASES = {
    "sonnet":       mp_config.DEFAULT_MODEL,       # anthropic/claude-sonnet-4-5
    "haiku":        mp_config.HAIKU_MODEL,         # anthropic/claude-haiku-4-5
    "opus":         mp_config.OPUS_48_MODEL,       # latest opus -> 4.8
    "opus48":       mp_config.OPUS_48_MODEL,       # anthropic/claude-opus-4.8
    "opus47":       mp_config.OPUS_MODEL,          # anthropic/claude-opus-4-7
    "gemini":       mp_config.GEMINI_MODEL,        # google/gemini-3.1-pro-preview
    "gemini-flash": mp_config.GEMINI_FLASH_MODEL,  # google/gemini-3.5-flash
    "gemini35":     mp_config.GEMINI_FLASH_MODEL,
    "gpt":          mp_config.GPT5_5_MODEL,        # openai/gpt-5.5
    "gpt55":        mp_config.GPT5_5_MODEL,
}

SETS = ["set_01", "set_02", "set_03", "set_04", "set_05"]

# Where to source the canonical task lines (the focal opening prompt per set) for
# each mode. focal_S_vs_S is the canonical source: the persona prompt is
# model-agnostic (it names the persona + items/wants + rules, never the model),
# and the actual models are overridden elsewhere (focal via env.yaml, opponent
# via MARKETPLACE_OPPONENTS_MODEL). transaction uses the settlement task, whose
# prompt carries the extra payment/settlement instructions.
MODE_TASK_SOURCE = {
    "market_deal": "tasks/paper_runs/focal_S_vs_S_phase1.jsonl",
    "review":      "tasks/paper_runs/focal_S_vs_S_phase2.jsonl",
    "swap_shop":   "tasks/paper_runs/focal_S_vs_S_phase3.jsonl",
    "transaction": "tasks/settlement_focal_S_vs_S_p2.jsonl",
}


def resolve_model(x: str) -> str:
    if x in MODEL_ALIASES:
        return MODEL_ALIASES[x]
    if "/" in x:                       # already a full provider/model string
        return x
    raise SystemExit(
        f"unknown model '{x}'. aliases: {sorted(MODEL_ALIASES)} "
        f"— or pass a full 'provider/model' string."
    )


def normalize_sets(s: str) -> list[str]:
    if s == "all":
        return list(SETS)
    norm = s if s.startswith("set_") else f"set_{s.zfill(2)}"
    if norm not in SETS:
        raise SystemExit(f"unknown set '{s}'. choices: {SETS} or 'all'.")
    return [norm]


def reset_env_yaml(focal_model: str, target: Path | None = None,
                   example: Path | None = None) -> Path:
    """Rewrite env.yaml FRESH from env.yaml.example, with policy_model_name set
    to the chosen focal. API keys stay as ${oc.env:OPENROUTER_API_KEY} — no
    secret is written to disk, and the value is read from the process env at
    boot. Resetting from the example each run guarantees no stale focal from a
    previous or overlapping run leaks in (env.yaml is a single shared file)."""
    target = Path(target) if target else ROOT / "env.yaml"
    example = Path(example) if example else ROOT / "env.yaml.example"
    out = []
    for ln in example.read_text().splitlines():
        if ln.strip().startswith("policy_model_name:"):
            out.append(f"policy_model_name: {focal_model}")
        else:
            out.append(ln)
    target.write_text("\n".join(out) + "\n")
    return target


def _short(model: str) -> str:
    """Filesystem-safe short tag for a model string (last path segment)."""
    return re.sub(r"[^A-Za-z0-9.-]", "-", model.split("/")[-1])


def make_run_id(plan: dict, now: datetime | None = None) -> str:
    """Readable, unique-per-invocation run id: mode_focal_vs_opp_set_timestamp."""
    ts = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    setspec = "all" if len(plan["sets"]) > 1 else plan["sets"][0]
    return (f"{plan['phase_name']}_{_short(plan['focal_model'])}"
            f"_vs_{_short(plan['opponents_model'])}_{setspec}_{ts}")


def prepare_output_dir(run_id: str) -> Path:
    """Create + return the isolated output dir for this run. Kept out of the
    git-tracked results/paper_runs/ so runs never overwrite, append to, or dirty
    the committed results."""
    d = ADAPTER_RUNS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def clear_session_scratch() -> Path:
    """Wipe leftover per-rollout marketplace scratch (data/ng_run/) so a new run
    cannot read stale session state. The server recreates it per rollout."""
    if SESSION_SCRATCH_DIR.exists():
        shutil.rmtree(SESSION_SCRATCH_DIR)
    SESSION_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_SCRATCH_DIR


def build_task_file(phase_name: str, sets: list[str], seed: int,
                    out_path: Path) -> tuple[Path, list[str]]:
    """Assemble the N-line task file for the chosen mode + sets.

    Sources each set's line (id, focal opening prompt, metadata) from the
    canonical committed task for this mode, then makes it portable + honors the
    chosen seed:
      - DROPS the baked-in personas_path — seed_session self-heals from
        phase + set_id, so no absolute machine path travels in the task.
      - sets metadata.seed to the requested seed.
    Returns (out_path, [focal_persona per set]).
    """
    src = ROOT / MODE_TASK_SOURCE[phase_name]
    if not src.exists():
        raise SystemExit(f"canonical task source missing: {src}")
    by_set = {}
    for ln in src.read_text().splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        by_set[d["metadata"]["set_id"]] = d

    lines, focals = [], []
    for s in sets:
        if s not in by_set:
            raise SystemExit(f"set '{s}' not found in {src}")
        d = by_set[s]
        d["metadata"].pop("personas_path", None)   # force portable self-heal
        d["metadata"]["seed"] = seed
        lines.append(json.dumps(d))
        focals.append(d["metadata"].get("focal_persona"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    return out_path, focals


def build_plan(args) -> dict:
    if args.phase not in PHASE_MAP:
        raise SystemExit(
            f"unknown phase '{args.phase}'. choices: {list(PHASE_MAP)}"
        )
    if args.max_turns < 1:
        raise SystemExit("--max-turns must be >= 1")

    phase_num, settlement = PHASE_MAP[args.phase]
    return {
        "phase_name": args.phase,
        "marketplace_phase": phase_num,
        "enable_settlement": settlement,
        "focal_model": resolve_model(args.focal),
        "opponents_model": resolve_model(args.opponent),
        "sets": normalize_sets(args.set),
        "max_turns": args.max_turns,
        # 1 focal call -> 1 opponent turn -> 2 market turns; odd rounds up.
        "focal_max_steps": math.ceil(args.max_turns / 2),
        "seed": args.seed,
        # getattr (not args.scammer) so callers that build a bare args namespace
        # without --scammer (e.g. pre-existing tests) keep the argparse default: ON.
        "scammer": getattr(args, "scammer", "on") == "on",
        # Save this run's reward to the platform. Default OFF — see run_live().
        "record": bool(getattr(args, "record", False)),
        "out_dir": "results/adapter_runs/<runid>",
    }


def print_plan(p: dict) -> None:
    settle = (" + ENABLE_SETTLEMENT=yes"
              + (" + SETTLEMENT_SCAM=yes" if p["scammer"] else " + SETTLEMENT_SCAM=no")) \
        if p["enable_settlement"] else ""
    print("PLAN (dry-run, nothing executed):")
    print(f"  phase        {p['phase_name']:<12} -> MARKETPLACE_PHASE={p['marketplace_phase']}{settle}")
    print(f"  focal        {p['focal_model']:<30} (env.yaml policy_model_name)")
    print(f"  opponent     {p['opponents_model']:<30} (MARKETPLACE_OPPONENTS_MODEL)")
    print(f"  max-turns    {p['max_turns']:<12} -> focal max_steps = {p['focal_max_steps']}")
    print(f"  set(s)       {', '.join(p['sets'])}  -> personas_phase{p['marketplace_phase']}/<set>.json")
    print(f"  seed         {p['seed']}")
    print(f"  output       {p['out_dir']}/result.json")
    print(f"  cache        OFF (resume_from_cache=False)")
    n = len(p["sets"])
    print(f"  would: reset env.yaml -> restart stack (once) -> run {n} rollout(s) -> write result.json")


def _stack_env(plan: dict) -> dict:
    """Process env for the stack boot: phase, settlement, opponent override, cap.
    Inherits os.environ (which already has OPENROUTER_API_KEY via config's
    load_dotenv) so the servers can resolve ${oc.env:OPENROUTER_API_KEY}."""
    env = os.environ.copy()
    env["MARKETPLACE_PHASE"] = plan["marketplace_phase"]
    env[OPPONENTS_ENV] = plan["opponents_model"]
    env["FOCAL_MAX_STEPS"] = str(plan["focal_max_steps"])
    if plan["enable_settlement"]:
        env["ENABLE_SETTLEMENT"] = "yes"
        # In settlement, the public-market cap is separate from the payment budget.
        env["FOCAL_PUBLIC_MAX_STEPS"] = str(plan["focal_max_steps"])
        # The man-in-the-middle scammer is a SEPARATE flag from settlement. Every
        # cached paper run had it ON (the legacy shell scripts set it); the adapter
        # never did, so live transaction runs were silently scam-free. Default ON.
        env["SETTLEMENT_SCAM"] = "yes" if plan.get("scammer", True) else "no"
    else:
        env["ENABLE_SETTLEMENT"] = "no"
        env["SETTLEMENT_SCAM"] = "no"
    return env


def extract_results(rollouts_path: Path, plan: dict, focals: list[str]) -> dict:
    """Read the rollouts and distill one small, authoritative result dict.
    Logs the ACTUAL focal/opponent (from the adapter inputs), not the canonical
    task label."""
    rows = [json.loads(l) for l in rollouts_path.read_text().splitlines() if l.strip()]
    per_set = []
    for r in rows:
        m = r.get("metadata") or {}
        breakdown = {
            k: (v.get("combined") if isinstance(v, dict) else v)
            for k, v in (r.get("rubric_scores") or {}).items()
            if k != "final_reward"
        }
        # What the EVALUATED agent did, as opposed to what the market did around it.
        # `num_deals` counts every deal in the marketplace — most of them between
        # opponents — so it says nothing about the agent under test.
        focal = m.get("focal_persona")
        events = r.get("channel_events") or []
        focal_steps = sum(1 for e in events if e.get("agent") == focal)
        focal_deals = sum(
            1
            for d in (r.get("deals") or [])
            if focal in (d.get("buyer"), d.get("seller"))
        )
        per_set.append({
            "set_id": m.get("set_id"),
            "focal_persona": focal,
            "reward": r.get("reward"),
            "rubric_breakdown": breakdown,
            "num_deals": len(r.get("deals") or []),
            "num_focal_deals": focal_deals,
            "num_focal_steps": focal_steps,
            "num_channel_events": len(events),
        })
    rewards = [p["reward"] for p in per_set if p["reward"] is not None]
    mean = round(sum(rewards) / len(rewards), 4) if rewards else None
    return {
        "phase": plan["phase_name"],
        "marketplace_phase": plan["marketplace_phase"],
        "enable_settlement": plan["enable_settlement"],
        "scammer": plan["scammer"],
        "focal_model": plan["focal_model"],
        "opponents_model": plan["opponents_model"],
        "max_turns": plan["max_turns"],
        "focal_max_steps": plan["focal_max_steps"],
        "seed": plan["seed"],
        "sets": plan["sets"],
        "num_sets": len(per_set),
        "mean_reward": mean,
        "per_set": per_set,
    }


def split_rollouts_by_set(rollouts_path: Path, out_dir: Path) -> list[str]:
    """Additionally write each rollout line to its own rollouts_<set_id>.jsonl
    (one rollout per file), alongside the combined rollouts.jsonl (kept as-is —
    other code, and the live-run episode reconstruction, read the combined
    file). Purely additive: never changes what's in rollouts.jsonl itself.
    Returns the list of per-set filenames written (relative to out_dir)."""
    written = []
    for line in rollouts_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        set_id = (row.get("metadata") or {}).get("set_id") or "unknown"
        fname = f"rollouts_{set_id}.jsonl"
        (out_dir / fname).write_text(line + "\n")
        written.append(fname)
    return written


def run_live(plan: dict) -> Path:
    """Execute one fresh run end to end and write result.json. Returns its path."""
    run_id = make_run_id(plan)
    out_dir = prepare_output_dir(run_id)
    started_at = time.time()
    print(f"[adapter] run_id={run_id}")

    # 1. fresh env.yaml (focal)   2. clear scratch   3. build task
    reset_env_yaml(plan["focal_model"])
    clear_session_scratch()
    task_path, focals = build_task_file(
        plan["phase_name"], plan["sets"], plan["seed"], out_dir / "task.jsonl")
    print(f"[adapter] task: {len(plan['sets'])} set(s) {plan['sets']} focals={focals}")

    env = _stack_env(plan)

    # 4. (re)start the stack with the chosen phase/settlement/opponent/cap
    print(f"[adapter] restarting stack (phase={plan['marketplace_phase']} "
          f"settlement={plan['enable_settlement']} cap={plan['focal_max_steps']} "
          f"opponent={plan['opponents_model']}) ...")
    r = subprocess.run(["bash", "scripts/restart_ng_run.sh"], cwd=str(ROOT), env=env)
    if r.returncode != 0:
        raise SystemExit(f"stack failed to start (restart_ng_run.sh exit {r.returncode})")

    # 5. run the rollout(s) — FRESH (cache off)
    rollouts = out_dir / "rollouts.jsonl"
    n = len(plan["sets"])
    print(f"[adapter] collecting {n} rollout(s), cache OFF ...")
    cmd = [
        str(ROOT / ".venv" / "bin" / "ng_collect_rollouts"),
        "+agent_name=marketplace_agent",
        f"+input_jsonl_fpath={task_path}",
        f"+output_jsonl_fpath={rollouts}",
        f"+limit={n}", "+num_repeats=1", "+resume_from_cache=False",
    ]
    with open(out_dir / "rollout.log", "w") as log:
        rr = subprocess.run(cmd, cwd=str(ROOT), env=env, stdout=log,
                            stderr=subprocess.STDOUT)
    if rr.returncode != 0 or not rollouts.exists():
        raise SystemExit(f"rollout collection failed (see {out_dir/'rollout.log'})")

    # 5b. also split into one rollouts_<set_id>.jsonl per set (additive; the
    # combined rollouts.jsonl above is untouched and remains the source other
    # code — e.g. the live-run episode reconstruction — reads from).
    per_set_files = split_rollouts_by_set(rollouts, out_dir)
    print(f"[adapter] per-set rollout files: {per_set_files}")

    # 6. distill -> result.json
    result = extract_results(rollouts, plan, focals)
    result["per_set_files"] = per_set_files
    # How long the run really took. The platform otherwise fills its Duration column with
    # `steps * 0.7` — a guess that reads like a measurement.
    result["duration_s"] = round(time.time() - started_at, 1)
    result_path = out_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[adapter] mean_reward={result['mean_reward']}  ->  {result_path}")

    # Announce this finished run to the RLEaaS platform. OFF unless the run was explicitly
    # marked to be recorded: a short exploratory run scores far below a full-length one
    # (a 10-turn run scored 0.17 where the same set scores ~0.36 at full length), so
    # recording every experiment would quietly drag down every average computed from the
    # store — and nobody would remember afterwards which rows were "just testing".
    # Still env-gated too (no-op unless RLEAAS_CALLBACK_URL + RLEAAS_TOKEN are set), and
    # best-effort: a failed push never fails the run.
    if not plan.get("record"):
        print("[adapter] not recorded (use --record to save this run to the platform)")
    else:
        try:
            pushed = platform_export.push_to_platform(result, run_id)
            if pushed:
                print(f"[adapter] pushed {pushed} rollout record(s) to the platform")
            else:
                print("[adapter] --record set, but the platform callback is not configured")
        except Exception as e:  # noqa: BLE001
            print(f"[adapter] platform push skipped: {e}")

    return result_path


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="adapter.py",
        description="project_deal marketplace -> one fresh reward.",
    )
    ap.add_argument("--phase", required=True,
                    help="market_deal | review | transaction | swap_shop")
    ap.add_argument("--set", required=True,
                    help="01..05, set_01.., or 'all'")
    ap.add_argument("--focal", required=True,
                    help="model alias (sonnet/opus/gemini/gpt/...) or full provider/model")
    ap.add_argument("--opponent", required=True,
                    help="model alias or full provider/model (shared by all 9 opponents)")
    ap.add_argument("--max-turns", type=int, default=100, dest="max_turns",
                    help="market turns; focal calls = ceil(max_turns/2). default 100")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--scammer", choices=["on", "off"], default="on",
                    help="transaction only: run the man-in-the-middle scammer. "
                         "default ON (the paper runs were scam-on). Ignored outside transaction.")
    ap.add_argument("--record", action="store_true",
                    help="save this run's reward to the RLEaaS platform. OFF by default: "
                         "a short exploratory run scores far below a full-length one, so "
                         "recording every experiment would drag down every average.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the resolved plan and exit; run nothing")
    args = ap.parse_args()

    plan = build_plan(args)
    if args.dry_run:
        print_plan(plan)
        return
    run_live(plan)


if __name__ == "__main__":
    main()
