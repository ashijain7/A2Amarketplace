"""
Main entry point for the marketplace run.

Usage:
    uv run deal                                          # uses existing personas.json, generates if missing
    uv run deal --model anthropic/claude-haiku-4-5
    uv run deal --max-turns 80 --seed 42
"""

import argparse
import json
import shutil
from datetime import datetime, timezone

from . import config
from .analyze import main as run_analysis
from .build_agents import build_agent_prompts, load_personas
from .interview import generate_personas, validate_personas
from .scheduler import run_marketplace
from .summarize import build_summary, write_summary


def main():
    parser = argparse.ArgumentParser(description="Run the Project Deal PoC marketplace.")
    parser.add_argument("--model", default=config.DEFAULT_MODEL,
                        help="OpenRouter model string for the agents.")
    parser.add_argument("--max-turns", type=int, default=config.MAX_TURNS)
    parser.add_argument("--stall-limit", type=int, default=config.STALL_LIMIT)
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible runs.")
    parser.add_argument("--scheduler", default="rotation", choices=["rotation", "random"],
                        help="rotation: shuffled round-robin (default). random: pure random.")
    parser.add_argument("--persona-set", type=int, default=None, metavar="N",
                        help="Use frozen persona set N (1-5) from personas/set_0N.json.")
    parser.add_argument("--regenerate-personas", action="store_true",
                        help="Generate fresh personas before running (ignores --persona-set).")
    args = parser.parse_args()

    config.require_api_key()

    run_id = "run_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if args.regenerate_personas:
        print("[run] Regenerating personas...")
        personas = generate_personas(n=config.DEFAULT_NUM_PERSONAS)
        warnings = validate_personas(personas)
        if warnings:
            for w in warnings:
                print(f"  - {w}")
        config.PERSONAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.PERSONAS_PATH.write_text(json.dumps(personas, indent=2))
        print(f"[run] Wrote {len(personas)} personas to {config.PERSONAS_PATH}\n")
    elif args.persona_set is not None:
        set_path = config.PERSONAS_DIR / f"set_{args.persona_set:02d}.json"
        if not set_path.exists():
            raise FileNotFoundError(
                f"Persona set {args.persona_set} not found at {set_path}.\n"
                f"Run: python -m project_deal_poc.personas.generate_sets"
            )
        personas = json.loads(set_path.read_text())
        config.PERSONAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.PERSONAS_PATH.write_text(json.dumps(personas, indent=2))
        print(f"[run] Loaded {len(personas)} personas from frozen set {args.persona_set}: {set_path}\n")
    elif config.PERSONAS_PATH.exists():
        personas = load_personas()
        print(f"[run] Loaded {len(personas)} personas from {config.PERSONAS_PATH}")
        print(f"[run] Tip: use --persona-set 1 for a reproducible frozen set.\n")
    else:
        print("[run] No personas file found — generating fresh personas...")
        personas = generate_personas(n=config.DEFAULT_NUM_PERSONAS)
        warnings = validate_personas(personas)
        if warnings:
            for w in warnings:
                print(f"  - {w}")
        config.PERSONAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.PERSONAS_PATH.write_text(json.dumps(personas, indent=2))
        print(f"[run] Wrote {len(personas)} personas to {config.PERSONAS_PATH}\n")

    agent_prompts = build_agent_prompts(personas)
    print(f"[run] Built {len(agent_prompts)} agent system prompts.")

    channel, ledger, stop_reason = run_marketplace(
        personas=personas,
        agent_prompts=agent_prompts,
        model=args.model,
        max_turns=args.max_turns,
        stall_limit=args.stall_limit,
        seed=args.seed,
        scheduler=args.scheduler,
    )

    print("\n" + "=" * 60)
    print(" POST-RUN ANALYSIS")
    print("=" * 60 + "\n")
    run_analysis()

    # Build and write summary.json
    summary = build_summary(
        run_id=run_id,
        model=args.model,
        persona_set=args.persona_set,
        scheduler=args.scheduler,
        seed=args.seed,
        max_turns=args.max_turns,
        stall_limit=args.stall_limit,
        channel=channel,
        ledger=ledger,
        personas=personas,
        stop_reason=stop_reason,
    )
    write_summary(summary)
    print(f"\n[run] Summary written to {config.SUMMARY_PATH}")

    # Archive this run to data/runs/{run_id}/
    run_dir = config.RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    for src in (config.CHANNEL_PATH, config.DEALS_PATH,
                config.PERSONAS_PATH, config.SUMMARY_PATH):
        if src.exists():
            shutil.copy2(src, run_dir / src.name)
    print(f"[run] Run archived to {run_dir}")


if __name__ == "__main__":
    main()
