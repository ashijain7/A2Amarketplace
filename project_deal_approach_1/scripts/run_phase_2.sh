#!/usr/bin/env bash
# Run Phase 2 end-to-end: pre-flight, rollouts, archive, aggregate, snapshot.
#
# Usage:
#   bash scripts/run_phase_2.sh validate # 2 tasks (smoke test during development)
#   bash scripts/run_phase_2.sh 5task    # 5 tasks (1 per set, focal_S_vs_H, seed 42)
#   bash scripts/run_phase_2.sh 20task   # 20 tasks (5 sets × 4 configs × 1 focal × seed 42)
#
# Assumptions:
#   - You are running from project_deal_approach_1/ directory
#   - .venv is set up
#   - .env file at ../.env has OPENROUTER_API_KEY
#   - ng_run is RUNNING in a separate terminal
#
# What this does for both modes:
#   1. Pre-flight: env, key, credit balance, server health, task file
#   2. Set MARKETPLACE_PHASE=2 → personas_phase2/, agent_template_phase{2}*.txt
#   3. Run rollouts (single batch for 5task; sonnet+haiku batches for 20task)
#   4. Archive per-rollout folders
#   5. Aggregate across rollouts
#   6. Snapshot the whole thing into results/phase2/run_*_TIMESTAMP/
#   7. Print headline summary
#
# Server lifecycle: this script does NOT start or stop ng_run. You run ng_run
# in Terminal 1 and this script in Terminal 2.

set -e

MODE="${1:-5task}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

export MARKETPLACE_PHASE=2

# --- pre-flight ---------------------------------------------------------

echo "============================================================"
echo "  Phase 2 — mode: $MODE   (MARKETPLACE_PHASE=$MARKETPLACE_PHASE)"
echo "============================================================"

if [ ! -f "$PROJECT_DIR/../.env" ]; then
  echo "ERROR: ../.env not found"
  exit 1
fi
set -a
source "$PROJECT_DIR/../.env"
set +a

if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "ERROR: OPENROUTER_API_KEY not set after sourcing .env"
  exit 1
fi
echo "✓ env loaded (key: ${OPENROUTER_API_KEY:0:14}...)"

if [ ! -d "$PROJECT_DIR/.venv" ]; then
  echo "ERROR: .venv missing"
  exit 1
fi
PY=".venv/bin/python"
echo "✓ venv present"

# Validate mode early (so we fail fast on typos)
if [ "$MODE" = "validate" ]; then
  MIN_CREDIT=30
elif [ "$MODE" = "5task" ]; then
  MIN_CREDIT=70
elif [ "$MODE" = "20task" ]; then
  MIN_CREDIT=280
else
  echo "ERROR: unknown mode '$MODE'. Use 'validate', '5task', or '20task'."
  exit 1
fi

# Check credit balance. OpenRouter returns limit_remaining=null for uncapped keys.
CREDIT_REMAINING=$(curl -s -X GET https://openrouter.ai/api/v1/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  | "$PY" -c "
import sys, json
d = json.load(sys.stdin).get('data', {})
lr = d.get('limit_remaining')
print('uncapped' if lr is None else lr)
")
echo "✓ OpenRouter credit remaining: $CREDIT_REMAINING"

if [ "$CREDIT_REMAINING" = "uncapped" ]; then
  echo "✓ key is uncapped — skipping budget gate"
else
  HAS_BUDGET=$("$PY" -c "print(int(float('$CREDIT_REMAINING') >= $MIN_CREDIT))")
  if [ "$HAS_BUDGET" != "1" ]; then
    echo "WARNING: Estimated need \$$MIN_CREDIT for $MODE mode (have \$$CREDIT_REMAINING)."
    echo "         Continuing anyway — interrupt now if you want to abort."
    sleep 3
  fi
fi

# Check ng_run is up
NG_HEAD_PORT=11000
if ! curl -s "http://127.0.0.1:$NG_HEAD_PORT/global_config_dict_yaml" > /dev/null 2>&1; then
  echo "ERROR: ng_run does not appear to be running on port $NG_HEAD_PORT"
  echo "       Start it in another terminal first:"
  echo "       ng_run \"+config_paths=[/Users/ashijain/Documents/nemo_gym_lib/resources_servers/marketplace/configs/marketplace.yaml,/Users/ashijain/Documents/nemo_gym_lib/responses_api_models/openai_model/configs/openai_model.yaml]\" 2>&1 | tee output.log"
  exit 1
fi
echo "✓ ng_run head server reachable on port $NG_HEAD_PORT"

# Resolve task file
if [ "$MODE" = "validate" ]; then
  TASKS_FILE="tasks/phase2_validate.jsonl"
  EXPECTED_LINES=2
  SNAPSHOT_KIND="validate"
  SNAPSHOT_CONFIG_TAG="focalSvH"
  SNAPSHOT_SEED_TAG="seed42"
elif [ "$MODE" = "5task" ]; then
  TASKS_FILE="tasks/phase2_5task.jsonl"
  EXPECTED_LINES=5
  SNAPSHOT_KIND="5tasks"
  SNAPSHOT_CONFIG_TAG="focalSvH"
  SNAPSHOT_SEED_TAG="seed42"
elif [ "$MODE" = "20task" ]; then
  TASKS_FILE="tasks/phase2_20task.jsonl"
  EXPECTED_LINES=20
  SNAPSHOT_KIND="20tasks"
  SNAPSHOT_CONFIG_TAG="allconfigs"
  SNAPSHOT_SEED_TAG="seed42"
fi

if [ ! -f "$TASKS_FILE" ]; then
  echo "ERROR: task file $TASKS_FILE not found"
  echo "       Generate it with:"
  if [ "$MODE" = "validate" ]; then
    echo "         MARKETPLACE_PHASE=2 .venv/bin/python tasks/generate_tasks.py \\"
    echo "             --phase 2 --focal-count 1 --config-filter focal_S_vs_H --seeds 42 \\"
    echo "             --out tasks/phase2_validate.jsonl"
    echo "         # then trim to 2 tasks for smoke (or write a 2-task subset directly)"
  elif [ "$MODE" = "5task" ]; then
    echo "         MARKETPLACE_PHASE=2 .venv/bin/python tasks/generate_tasks.py \\"
    echo "             --phase 2 --focal-count 1 --config-filter focal_S_vs_H --seeds 42 \\"
    echo "             --out tasks/phase2_5task.jsonl"
  else
    echo "         MARKETPLACE_PHASE=2 .venv/bin/python tasks/generate_tasks.py \\"
    echo "             --phase 2 --focal-count 1 --seeds 42 \\"
    echo "             --out tasks/phase2_20task.jsonl"
  fi
  exit 1
fi
ACTUAL_LINES=$(wc -l < "$TASKS_FILE")
if [ "$ACTUAL_LINES" -ne "$EXPECTED_LINES" ]; then
  echo "ERROR: $TASKS_FILE has $ACTUAL_LINES lines, expected $EXPECTED_LINES"
  exit 1
fi
echo "✓ task file $TASKS_FILE: $ACTUAL_LINES tasks"

mkdir -p results/phase_2 results/runs results/aggregates tasks/batches "results/phase1"

# --- split task file by focal model -------------------------------------

SONNET_BATCH="tasks/batches/phase2_${MODE}_sonnet_focal.jsonl"
HAIKU_BATCH="tasks/batches/phase2_${MODE}_haiku_focal.jsonl"

grep '"config_name": "focal_S_' "$TASKS_FILE" > "$SONNET_BATCH" || touch "$SONNET_BATCH"
grep '"config_name": "focal_H_' "$TASKS_FILE" > "$HAIKU_BATCH" || touch "$HAIKU_BATCH"
N_SONNET=$(wc -l < "$SONNET_BATCH")
N_HAIKU=$(wc -l < "$HAIKU_BATCH")
echo "✓ split into batches: $N_SONNET Sonnet-focal, $N_HAIKU Haiku-focal"

# --- helper: set policy_model_name in env.yaml -------------------------

set_env_model() {
  local model="$1"
  sed -i '' "s|policy_model_name:.*|policy_model_name: $model|" env.yaml
  grep "policy_model_name" env.yaml
}

# --- Batch A: Sonnet focal ---------------------------------------------

SONNET_OUT="results/phase_2/phase2_${MODE}_sonnet_focal_rollouts.jsonl"
HAIKU_OUT="results/phase_2/phase2_${MODE}_haiku_focal_rollouts.jsonl"

if [ "$N_SONNET" -gt 0 ]; then
  echo ""
  echo "============================================================"
  echo "  Batch A — Sonnet focal ($N_SONNET tasks)"
  echo "============================================================"
  set_env_model "anthropic/claude-sonnet-4-5"
  echo ""
  echo "  NOTE: env.yaml is now Sonnet. If ng_run was started while it was on Haiku,"
  echo "        you MUST restart ng_run now for the change to take effect."
  echo "        (Sleep 5s to give you a chance to ctrl-C if needed.)"
  sleep 5

  .venv/bin/ng_collect_rollouts \
    +agent_name=marketplace_agent \
    +input_jsonl_fpath="$PWD/$SONNET_BATCH" \
    +output_jsonl_fpath="$PWD/$SONNET_OUT" \
    +limit="$N_SONNET" \
    +num_repeats=1 \
    +resume_from_cache=True 2>&1 | tee -a output_phase2.log
fi

# --- Batch B: Haiku focal (only if 20task mode) ------------------------

if [ "$N_HAIKU" -gt 0 ]; then
  echo ""
  echo "============================================================"
  echo "  Batch B — Haiku focal ($N_HAIKU tasks)"
  echo "============================================================"
  echo ""
  echo "  Stop ng_run (Ctrl+C in Terminal 1), edit env.yaml to use Haiku,"
  echo "  restart ng_run, then press ENTER here to continue."
  echo ""
  set_env_model "anthropic/claude-haiku-4-5"
  read -p "  Press ENTER when ng_run is back up with Haiku policy_model... " _

  .venv/bin/ng_collect_rollouts \
    +agent_name=marketplace_agent \
    +input_jsonl_fpath="$PWD/$HAIKU_BATCH" \
    +output_jsonl_fpath="$PWD/$HAIKU_OUT" \
    +limit="$N_HAIKU" \
    +num_repeats=1 \
    +resume_from_cache=True 2>&1 | tee -a output_phase2.log
fi

# Restore env.yaml to Sonnet (default)
set_env_model "anthropic/claude-sonnet-4-5"

# --- Archive ----------------------------------------------------------

echo ""
echo "============================================================"
echo "  Archiving per-rollout folders into results/runs/"
echo "============================================================"
if [ -s "$SONNET_OUT" ]; then
  .venv/bin/python scripts/archive_run.py --input "$SONNET_OUT" --runs-dir results/runs/
fi
if [ -s "$HAIKU_OUT" ]; then
  .venv/bin/python scripts/archive_run.py --input "$HAIKU_OUT" --runs-dir results/runs/
fi
echo "✓ archived. results/runs/ now has $(ls results/runs/ | wc -l | xargs) folder(s)"

# --- Aggregate --------------------------------------------------------

echo ""
echo "============================================================"
echo "  Aggregating across all runs"
echo "============================================================"
.venv/bin/python analysis/compare.py --phase 2
echo "✓ aggregator wrote results/aggregates/phase_2_summary.json"

# --- Pretty-print per-rollout rubrics ---------------------------------

echo ""
echo "============================================================"
echo "  Per-rollout rubric scores"
echo "============================================================"
if [ -s "$SONNET_OUT" ]; then
  echo "--- Sonnet-focal batch ---"
  .venv/bin/python scripts/show_results.py "$SONNET_OUT"
fi
if [ -s "$HAIKU_OUT" ]; then
  echo "--- Haiku-focal batch ---"
  .venv/bin/python scripts/show_results.py "$HAIKU_OUT"
fi

# --- Snapshot into results/phase2/run_*_TIMESTAMP/ --------------------

echo ""
echo "============================================================"
echo "  Snapshotting run into results/phase2/"
echo "============================================================"
if [ -s "$SONNET_OUT" ]; then
  .venv/bin/python scripts/snapshot_run.py \
    --phase 2 \
    --rollouts "$SONNET_OUT" \
    --kind "$SNAPSHOT_KIND" \
    --config-tag "$SNAPSHOT_CONFIG_TAG" \
    --seed-tag "$SNAPSHOT_SEED_TAG"
fi
if [ -s "$HAIKU_OUT" ]; then
  .venv/bin/python scripts/snapshot_run.py \
    --phase 2 \
    --rollouts "$HAIKU_OUT" \
    --kind "${SNAPSHOT_KIND}_haiku" \
    --config-tag "$SNAPSHOT_CONFIG_TAG" \
    --seed-tag "$SNAPSHOT_SEED_TAG"
fi

# --- Headline aggregate -----------------------------------------------

echo ""
echo "============================================================"
echo "  Headline (cross-config means + asymmetry test)"
echo "============================================================"
.venv/bin/python -c "
import json
data = json.load(open('results/aggregates/phase_2_summary.json'))
print()
print(f\"Total rollouts: {data.get('total_rollouts')}\")
print()
print('Per-config means:')
for cfg, stats in (data.get('configs') or {}).items():
    mr = stats.get('mean_reward')
    rc = stats.get('rollout_count')
    print(f'  {cfg:18s}: mean_reward={mr if mr is None else f\"{mr:.3f}\"}  (n={rc})')
print()
asym = data.get('asymmetry_test') or {}
if asym:
    print('Asymmetry test (S_vs_H vs H_vs_S):')
    print(f'  S_vs_H value extracted: {asym.get(\"focal_S_vs_H_mean_value_extracted\")}')
    print(f'  H_vs_S value extracted: {asym.get(\"focal_H_vs_S_mean_value_extracted\")}')
    print(f'  ratio:                  {asym.get(\"ratio\")}')
    interp = asym.get('interpretation')
    if interp:
        print(f'  interpretation: {interp}')
"

echo ""
echo "Done."
