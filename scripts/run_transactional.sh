#!/usr/bin/env bash
# Run transactional rollout(s) under NeMo Gym, in the paper-run output format,
# segregated under results/transactional_runs/<config>/phase4/.
#
# Usage:
#   scripts/run_transactional.sh <config_name> <phase> <scam: on|off> [n_sets] [set_line]
#     n_sets defaults to 1 (a single smoke rollout, set_01 seed 42).
#     Pass 5 to run all five persona sets (the real Phase-4 grid per config).
set -e
CONFIG="${1:-focal_S_vs_S}"; PHASE="${2:-1}"; SCAM="${3:-on}"; NSETS="${4:-1}"; SET_LINE="${5:-}"
# SET_LINE (5th arg): run ONLY that 1-indexed set line (set_01=1 Kai, 2 Rex, 3 Marcus, 4 Omar,
# 5 Taj). When given, NSETS is ignored. When empty, the first NSETS sets run.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$PROJECT_DIR"
set -a; source .env; set +a

export MARKETPLACE_PHASE="$PHASE"
export ENABLE_SETTLEMENT=yes
[ "$SCAM" = "on" ] && export SETTLEMENT_SCAM=yes || export SETTLEMENT_SCAM=no
# set SETTLEMENT_DECLINE=yes in the env to decline the FOCAL's first payment once (recovery test)
export SETTLEMENT_DECLINE="${SETTLEMENT_DECLINE:-no}"

# --- output naming (decoupled from the internal marketplace CONFIG/PHASE) -----
# The transactional experiment is project "Phase 4"; the marketplace itself runs at
# MARKETPLACE_PHASE=$PHASE (=1) under the hood. Map the internal config to a display name.
case "$CONFIG" in
  focal_S_vs_S) OUT_CONFIG="sonnet_vs_sonnet" ;;
  *)            OUT_CONFIG="$CONFIG" ;;
esac
TXN_PHASE=4

PY=".venv/bin/python"
OUT_DIR="results/transactional_runs/${OUT_CONFIG}/phase${TXN_PHASE}"
ROLLOUTS_OUT="$OUT_DIR/rollouts.jsonl"
mkdir -p "$OUT_DIR" data results/runs

# --- task file (1 set = smoke; 5 = full per-config grid) ------------------
TASK_FILE="tasks/settlement_${CONFIG}_p${PHASE}.jsonl"
$PY tasks/generate_tasks.py --phase "$PHASE" --config "$CONFIG" \
  --focal-count 1 --seeds 42 --out "$TASK_FILE" >/dev/null
if [ -n "$SET_LINE" ]; then
  sed -n "${SET_LINE}p" "$TASK_FILE" > "${TASK_FILE}.n" && mv "${TASK_FILE}.n" "$TASK_FILE"
else
  head -n "$NSETS" "$TASK_FILE" > "${TASK_FILE}.n" && mv "${TASK_FILE}.n" "$TASK_FILE"
fi
NLINES=$(wc -l < "$TASK_FILE" | tr -d ' ')

echo "============================================================"
echo "  Transactional run: $OUT_CONFIG / phase $TXN_PHASE / scam=$SCAM  ($NLINES rollout(s))"
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
$PY scripts/settlement_aggregate.py "$ROLLOUTS_OUT" "$OUT_DIR" "$OUT_CONFIG" "$TXN_PHASE" "$SCAM" "$WALL"

# --- per-set folders (paper shape: set_NN_<focal>/ + private_rooms/) -------
if [ -s "$ROLLOUTS_OUT" ]; then
  $PY scripts/settlement_per_set.py --in "$ROLLOUTS_OUT" --out-dir "$OUT_DIR" || true
fi

# --- quick validator: rooms mandatory, pay-gate intact, scammer took its turn ---
echo ""
echo "── transactional validation ──"
$PY scripts/settlement_validate.py || true

echo ""
echo "✓ done — output segregated under $OUT_DIR/"
echo "    rollouts.jsonl · aggregate.json · INSIGHTS.md · set_NN_<focal>/ (+ private_rooms/) · rollout.log"
echo "    raw payment play-by-play: data/ng_run/*/settlement.json"
