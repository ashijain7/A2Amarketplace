#!/usr/bin/env bash
# Run ONE settlement rollout under NeMo Gym. Usage:
#   scripts/run_settlement.sh <config_name> <phase> <scam: on|off>
set -e
CONFIG="${1:-focal_S_vs_S}"; PHASE="${2:-1}"; SCAM="${3:-on}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$PROJECT_DIR"
set -a; source .env; set +a

export MARKETPLACE_PHASE="$PHASE"
export ENABLE_SETTLEMENT=yes
[ "$SCAM" = "on" ] && export SETTLEMENT_SCAM=yes || export SETTLEMENT_SCAM=no

# 1-rollout task file: single config, set_01's first focal, seed 42.
TASK_FILE="tasks/settlement_smoke_${CONFIG}_p${PHASE}.jsonl"
.venv/bin/python tasks/generate_tasks.py --phase "$PHASE" --config "$CONFIG" \
  --focal-count 1 --seeds 42 --out "$TASK_FILE"
# keep only the set_01 line so it's a single rollout
head -n 1 "$TASK_FILE" > "${TASK_FILE}.one" && mv "${TASK_FILE}.one" "$TASK_FILE"

OUT="results/payment_runs/${CONFIG}_p${PHASE}_smoke"
mkdir -p "$OUT" data results/runs
echo "→ restarting ng_run (settlement=$ENABLE_SETTLEMENT scam=$SETTLEMENT_SCAM)"
bash scripts/restart_ng_run.sh

.venv/bin/ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath="$PWD/$TASK_FILE" \
  +output_jsonl_fpath="$PWD/$OUT/rollouts.jsonl" \
  +limit=1 +num_repeats=1 +resume_from_cache=False 2>&1 | tee "$OUT/rollout.log"

echo "✓ done — rollouts at $OUT/rollouts.jsonl ; settlement record at data/ng_run/*/settlement.json"
