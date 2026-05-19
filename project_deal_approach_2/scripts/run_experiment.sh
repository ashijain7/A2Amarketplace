#!/usr/bin/env bash
set -euo pipefail

# Usage: bash scripts/run_experiment.sh phase_1
PHASE="${1:-phase_1}"

cd "$(dirname "$0")/.."

if [ "$PHASE" = "phase_1" ]; then
    OUT_ROLLOUTS="results/phase_1/all_rollouts.jsonl"
    mkdir -p results/phase_1

    # Generate tasks if not present
    if [ ! -s tasks/marketdeal_tasks.jsonl ]; then
        python tasks/generate_tasks.py --phase 1
    fi

    # Start the NeMo Gym Resources Server in background
    ng_run "+config_paths=[resources_server/configs/marketplace.yaml]" &
    NG_PID=$!
    trap "kill $NG_PID 2>/dev/null || true" EXIT
    sleep 5

    # Run all 45 rollouts
    ng_collect_rollouts \
        +agent_name=marketplace_agent \
        +input_jsonl_fpath=tasks/marketdeal_tasks.jsonl \
        +output_jsonl_fpath="$OUT_ROLLOUTS" \
        +limit=45 \
        +num_repeats=1

    # Archive each rollout to results/runs/
    python scripts/archive_run.py --rollouts "$OUT_ROLLOUTS" \
        --out-root results/runs
else
    echo "Unknown phase: $PHASE"
    exit 1
fi
