#!/usr/bin/env bash
# Run settlement rollout(s) under NeMo Gym, in the paper-run output format,
# segregated under results/settlement_runs/<config>/phase<N>/.
#
# Usage:
#   scripts/run_settlement.sh <config_name> <phase> <scam: on|off> [n_sets]
#     n_sets defaults to 1 (a single smoke rollout, set_01 seed 42).
#     Pass 5 to run all five persona sets (the real Phase-4 grid per config).
set -e
CONFIG="${1:-focal_S_vs_S}"; PHASE="${2:-1}"; SCAM="${3:-on}"; NSETS="${4:-1}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$PROJECT_DIR"
set -a; source .env; set +a

export MARKETPLACE_PHASE="$PHASE"
export ENABLE_SETTLEMENT=yes
[ "$SCAM" = "on" ] && export SETTLEMENT_SCAM=yes || export SETTLEMENT_SCAM=no

PY=".venv/bin/python"
OUT_DIR="results/settlement_runs/${CONFIG}/phase${PHASE}"
ROLLOUTS_OUT="$OUT_DIR/rollouts.jsonl"
mkdir -p "$OUT_DIR" data results/runs

# --- task file (1 set = smoke; 5 = full per-config grid) ------------------
TASK_FILE="tasks/settlement_${CONFIG}_p${PHASE}.jsonl"
$PY tasks/generate_tasks.py --phase "$PHASE" --config "$CONFIG" \
  --focal-count 1 --seeds 42 --out "$TASK_FILE" >/dev/null
head -n "$NSETS" "$TASK_FILE" > "${TASK_FILE}.n" && mv "${TASK_FILE}.n" "$TASK_FILE"
NLINES=$(wc -l < "$TASK_FILE" | tr -d ' ')

echo "============================================================"
echo "  Settlement run: $CONFIG / phase $PHASE / scam=$SCAM  ($NLINES rollout(s))"
echo "  output: $OUT_DIR"
echo "============================================================"

# --- restart the NeMo Gym server with settlement env ----------------------
echo "→ restarting ng_run (ENABLE_SETTLEMENT=$ENABLE_SETTLEMENT SETTLEMENT_SCAM=$SETTLEMENT_SCAM)"
bash scripts/restart_ng_run.sh

# --- collect rollouts -----------------------------------------------------
START=$(date +%s)
.venv/bin/ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath="$PWD/$TASK_FILE" \
  +output_jsonl_fpath="$PWD/$ROLLOUTS_OUT" \
  +limit="$NLINES" +num_repeats=1 +resume_from_cache=False 2>&1 | tee "$OUT_DIR/rollout.log"
WALL=$(( $(date +%s) - START ))
echo "✓ rollouts done in ${WALL}s"

# --- archive per-rollout folders (same helper as paper runs) --------------
if [ -s "$ROLLOUTS_OUT" ]; then
  $PY scripts/archive_run.py --input "$ROLLOUTS_OUT" --runs-dir results/runs/ || true
fi

# --- aggregate.json + INSIGHTS.md (paper shape + settlement scores) -------
$PY scripts/settlement_aggregate.py "$ROLLOUTS_OUT" "$OUT_DIR" "$CONFIG" "$PHASE" "$SCAM" "$WALL"

# --- per-set channels/deals (same helper as paper runs) -------------------
if [ -s "$ROLLOUTS_OUT" ]; then
  $PY scripts/extract_per_set_channels.py --in "$ROLLOUTS_OUT" --out-dir "$OUT_DIR/per_set/" || true
fi

# --- quick validator: rooms mandatory, pay-gate intact, scammer took its turn ---
echo ""
echo "── settlement validation ──"
$PY scripts/settlement_validate.py || true

echo ""
echo "✓ done — output segregated under $OUT_DIR/"
echo "    rollouts.jsonl · aggregate.json · INSIGHTS.md · per_set/ · rollout.log"
echo "    raw payment play-by-play: data/ng_run/*/settlement.json"
