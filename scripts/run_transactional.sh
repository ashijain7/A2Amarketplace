#!/usr/bin/env bash
# Run transactional rollout(s) under NeMo Gym, in the paper-run output format,
# segregated under results/paper_runs/<CONFIG_DIR>/phase{4,5}/.
#
# Usage:
#   scripts/run_transactional.sh <config_name> <proj_phase> <scam: on|off> [n_sets] [set_line]
#     proj_phase: 4 = transaction + review (marketplace phase 2); 5 = transaction only (phase 1)
#     n_sets defaults to 1 (a single smoke rollout, set_01 seed 42).
#     Pass 5 to run all five persona sets (the real Phase-4/5 grid per config).
set -e
CONFIG="${1:-focal_S_vs_S}"; PROJ_PHASE="${2:-4}"; SCAM="${3:-on}"; NSETS="${4:-1}"; SET_LINE="${5:-}"
# project phase 4 = transaction + review (marketplace phase 2); 5 = transaction only (phase 1)
case "$PROJ_PHASE" in
  4) MP_PHASE=2 ;;
  5) MP_PHASE=1 ;;
  *) echo "ERROR: phase must be 4 (txn+review) or 5 (txn-only); got '$PROJ_PHASE'"; exit 1 ;;
esac
# SET_LINE (5th arg): run ONLY that 1-indexed set line (set_01=1 Kai, 2 Rex, 3 Marcus, 4 Omar,
# 5 Taj). When given, NSETS is ignored. When empty, the first NSETS sets run.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$PROJECT_DIR"
set -a; source .env; set +a

export MARKETPLACE_PHASE="$MP_PHASE"
export ENABLE_SETTLEMENT=yes
[ "$SCAM" = "on" ] && export SETTLEMENT_SCAM=yes || export SETTLEMENT_SCAM=no
# set SETTLEMENT_DECLINE=yes in the env to decline the FOCAL's first payment once (recovery test)
export SETTLEMENT_DECLINE="${SETTLEMENT_DECLINE:-no}"

# --- output naming (paper-run tree: results/paper_runs/<CONFIG_DIR>/phase{4,5}/) -----
case "$CONFIG" in
  focal_S_vs_S)   CONFIG_DIR="C1_sonnet_vs_sonnet" ;;
  focal_O_vs_H)   CONFIG_DIR="C2_opus_vs_haiku" ;;
  focal_H_vs_O)   CONFIG_DIR="C3_haiku_vs_opus" ;;
  focal_S_vs_G)   CONFIG_DIR="C4_sonnet_vs_gemini" ;;
  focal_G_vs_S)   CONFIG_DIR="C5_gemini_vs_sonnet" ;;
  focal_O_vs_G)   CONFIG_DIR="C6_opus_vs_gemini" ;;
  focal_G_vs_X)   CONFIG_DIR="C7_gemini_vs_gpt55" ;;
  focal_G35_vs_X) CONFIG_DIR="C8_gemini35_vs_gpt55" ;;
  focal_O_vs_X)   CONFIG_DIR="C9_opus48_vs_gpt55" ;;
  focal_X_vs_O48) CONFIG_DIR="C10_gpt55_vs_opus48" ;;
  *)              CONFIG_DIR="$CONFIG" ;;
esac

PY=".venv/bin/python"
OUT_DIR="results/paper_runs/${CONFIG_DIR}/phase${PROJ_PHASE}"
ROLLOUTS_OUT="$OUT_DIR/rollouts.jsonl"
mkdir -p "$OUT_DIR" data results/runs

# --- task file (1 set = smoke; 5 = full per-config grid) ------------------
TASK_FILE="tasks/settlement_${CONFIG}_p${MP_PHASE}.jsonl"
$PY tasks/generate_tasks.py --phase "$MP_PHASE" --config "$CONFIG" \
  --focal-count 1 --seeds 42 --out "$TASK_FILE" >/dev/null
if [ -n "$SET_LINE" ]; then
  sed -n "${SET_LINE}p" "$TASK_FILE" > "${TASK_FILE}.n" && mv "${TASK_FILE}.n" "$TASK_FILE"
else
  head -n "$NSETS" "$TASK_FILE" > "${TASK_FILE}.n" && mv "${TASK_FILE}.n" "$TASK_FILE"
fi
NLINES=$(wc -l < "$TASK_FILE" | tr -d ' ')

echo "============================================================"
echo "  Transactional run: $CONFIG_DIR / phase $PROJ_PHASE / scam=$SCAM  ($NLINES rollout(s))"
echo "  output: $OUT_DIR"
echo "============================================================"

# --- set the focal (policy) model to match this config --------------------
# Previously sonnet-only (relied on env.yaml). Derive the config's focal from
# model_config so any config (opus / gemini / etc.) runs with the correct focal.
FOCAL_MODEL=$($PY -c "from resources_server.model_config import get_model_config as g; print(g('$CONFIG')['focal_model'])")
sed -i.bak "s|^policy_model_name:.*|policy_model_name: ${FOCAL_MODEL}|" env.yaml && rm -f env.yaml.bak
echo "→ focal model for $CONFIG: $FOCAL_MODEL (written to env.yaml)"

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
$PY scripts/settlement_aggregate.py "$ROLLOUTS_OUT" "$OUT_DIR" "$CONFIG_DIR" "$PROJ_PHASE" "$SCAM" "$WALL"

# --- per-set folders (paper shape: set_NN_<focal>/ + private_rooms/) -------
if [ -s "$ROLLOUTS_OUT" ]; then
  $PY scripts/settlement_per_set.py --in "$ROLLOUTS_OUT" --out-dir "$OUT_DIR" || true
fi

# --- quick validator: rooms mandatory, pay-gate intact, scammer took its turn ---
echo ""
echo "── transactional validation ──"
$PY scripts/settlement_validate.py "$ROLLOUTS_OUT" || true

echo ""
echo "✓ done — output segregated under $OUT_DIR/"
echo "    rollouts.jsonl · aggregate.json · INSIGHTS.md · set_NN_<focal>/ (+ private_rooms/) · rollout.log"
echo "    raw payment play-by-play: data/ng_run/*/settlement.json"
