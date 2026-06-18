#!/usr/bin/env bash
# Sequential + RESUMABLE variant of run_transactional.sh.
#
# WHY: gemini-3.1-pro-preview stalls under concurrent load (5 rollouts firing
# simultaneous calls is the stall trigger). This runs the rollouts ONE AT A TIME
# (num_samples_in_parallel=1) so the preview endpoint is never hit concurrently,
# and RESUMES (resume_from_cache=True) so every completed rollout is banked and
# skipped on re-run. If it dies/stalls, just re-run the SAME command — it continues
# from the rollouts already finished (rollout-level resume; mid-rollout resume is
# not possible — the focal transcript isn't persisted until a rollout completes).
#
# Usage: scripts/run_sequential.sh <config> <proj_phase> <scam: on|off> [n_sets]
#   e.g. scripts/run_sequential.sh focal_G_vs_X 4 on 5
set -e
CONFIG="${1:-focal_G_vs_X}"; PROJ_PHASE="${2:-4}"; SCAM="${3:-on}"; NSETS="${4:-5}"
# PAR (5th arg) = how many rollouts run concurrently. 1 = sequential (safe for flaky
# preview endpoints like gemini-pro). Set to n_sets to run all in parallel (fine for
# stable endpoints like Opus/Sonnet). Resume works regardless of PAR.
PAR="${5:-1}"
case "$PROJ_PHASE" in
  4) MP_PHASE=2 ;;
  5) MP_PHASE=1 ;;
  *) echo "ERROR: phase must be 4 or 5; got '$PROJ_PHASE'"; exit 1 ;;
esac
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$PROJECT_DIR"
set -a; source .env; set +a

export MARKETPLACE_PHASE="$MP_PHASE"
export ENABLE_SETTLEMENT=yes
[ "$SCAM" = "on" ] && export SETTLEMENT_SCAM=yes || export SETTLEMENT_SCAM=no
export SETTLEMENT_DECLINE="${SETTLEMENT_DECLINE:-no}"

case "$CONFIG" in
  focal_S_vs_S)   CONFIG_DIR="C1_sonnet_vs_sonnet" ;;
  focal_S_vs_G)   CONFIG_DIR="C4_sonnet_vs_gemini" ;;
  focal_G_vs_S)   CONFIG_DIR="C5_gemini_vs_sonnet" ;;
  focal_O_vs_G)   CONFIG_DIR="C6_opus_vs_gemini" ;;
  focal_G_vs_X)   CONFIG_DIR="C7_gemini_vs_gpt55" ;;
  focal_G35_vs_X) CONFIG_DIR="C8_gemini35_vs_gpt55" ;;
  focal_O_vs_X)   CONFIG_DIR="C9_opus48_vs_gpt55" ;;
  *)              CONFIG_DIR="$CONFIG" ;;
esac

PY=".venv/bin/python"
OUT_DIR="results/paper_runs/${CONFIG_DIR}/phase${PROJ_PHASE}"
ROLLOUTS_OUT="$OUT_DIR/rollouts.jsonl"
mkdir -p "$OUT_DIR" data results/runs

# Task file (deterministic: seed 42 -> stable ids, so resume matches across re-runs).
TASK_FILE="tasks/settlement_${CONFIG}_p${MP_PHASE}.jsonl"
$PY tasks/generate_tasks.py --phase "$MP_PHASE" --config "$CONFIG" \
  --focal-count 1 --seeds 42 --out "$TASK_FILE" >/dev/null
head -n "$NSETS" "$TASK_FILE" > "${TASK_FILE}.n" && mv "${TASK_FILE}.n" "$TASK_FILE"
NLINES=$(wc -l < "$TASK_FILE" | tr -d ' ')

# Focal (policy) model for this config.
FOCAL_MODEL=$($PY -c "from resources_server.model_config import get_model_config as g; print(g('$CONFIG')['focal_model'])")
sed -i.bak "s|^policy_model_name:.*|policy_model_name: ${FOCAL_MODEL}|" env.yaml && rm -f env.yaml.bak

DONE=0; [ -f "$ROLLOUTS_OUT" ] && DONE=$(wc -l < "$ROLLOUTS_OUT" | tr -d ' ')
echo "============================================================"
echo "  SEQUENTIAL run: $CONFIG_DIR / phase $PROJ_PHASE / scam=$SCAM"
echo "  focal: $FOCAL_MODEL   concurrency: $PAR ($([ "$PAR" = "1" ] && echo "sequential" || echo "$PAR in parallel"))"
echo "  resume: ON   already banked: ${DONE}/${NLINES}"
echo "  output: $OUT_DIR"
echo "============================================================"

bash scripts/restart_ng_run.sh

START=$(date +%s)
# num_samples_in_parallel=$PAR -> concurrency (1=sequential, n=parallel).
# resume_from_cache=True       -> never clears output; skips rollouts already in it.
.venv/bin/ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath="$PWD/$TASK_FILE" \
  +output_jsonl_fpath="$PWD/$ROLLOUTS_OUT" \
  +limit="$NLINES" +num_repeats=1 \
  +num_samples_in_parallel=$PAR \
  +resume_from_cache=True 2>&1 | tee -a "$OUT_DIR/rollout.log"
WALL=$(( $(date +%s) - START ))
BANKED=0; [ -f "$ROLLOUTS_OUT" ] && BANKED=$(wc -l < "$ROLLOUTS_OUT" | tr -d ' ')
echo "✓ sequential pass done in ${WALL}s — ${BANKED}/${NLINES} rollouts banked"

# Aggregate / per-set / archive (same helpers as run_transactional.sh).
if [ -s "$ROLLOUTS_OUT" ]; then
  $PY scripts/archive_run.py --input "$ROLLOUTS_OUT" --runs-dir results/runs/ || true
  $PY scripts/settlement_aggregate.py "$ROLLOUTS_OUT" "$OUT_DIR" "$CONFIG_DIR" "$PROJ_PHASE" "$SCAM" "$WALL" || true
  $PY scripts/settlement_per_set.py --in "$ROLLOUTS_OUT" --out-dir "$OUT_DIR" || true
fi

if [ "$BANKED" -lt "$NLINES" ]; then
  echo "⚠ ${BANKED}/${NLINES} done — re-run the SAME command to resume the remaining $((NLINES-BANKED))."
fi
