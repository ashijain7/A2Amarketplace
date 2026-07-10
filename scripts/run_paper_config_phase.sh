#!/usr/bin/env bash
# Run one (config, phase) pair end-to-end for the paper experiment matrix.
#
# Usage:
#   bash scripts/run_paper_config_phase.sh <config_name> <phase>
#
#   <config_name>  one of: focal_S_vs_S focal_O_vs_H focal_H_vs_O focal_S_vs_G focal_G_vs_S focal_O_vs_G focal_G_vs_X focal_G35_vs_X
#   <phase>        1 | 2 | 3
#
# What it does (all automated):
#   1. Pre-flight: env, credit balance (>=$20 required)
#   2. Edit env.yaml::policy_model_name to the focal model for this config
#   3. Restart ng_run (bash scripts/restart_ng_run.sh) and health-check
#   4. Run 5 rollouts (one per persona set)
#   5. Archive per-rollout folders
#   6. Aggregate
#   7. Write stub INSIGHTS.md template (Claude fills in the analysis)
#   8. Log credit balance + delta into data/credit_log.jsonl
#
# Output:
#   results/paper_runs/<config_dir>/phase<N>/
#       rollouts.jsonl
#       materialized_inputs.jsonl
#       aggregate.json
#       INSIGHTS.md          ← stub template; analysis written after run

set -e

CONFIG="${1:?usage: $0 <config_name> <phase>}"
PHASE="${2:?usage: $0 <config_name> <phase>}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# --- map config_name → (focal_model, friendly_dir) -------------------------

case "$CONFIG" in
  focal_S_vs_S) FOCAL_MODEL="anthropic/claude-sonnet-4-5"; CONFIG_DIR="C1_sonnet_vs_sonnet" ;;
  focal_O_vs_H) FOCAL_MODEL="anthropic/claude-opus-4-7";   CONFIG_DIR="C2_opus_vs_haiku"  ;;
  focal_H_vs_O) FOCAL_MODEL="anthropic/claude-haiku-4-5";  CONFIG_DIR="C3_haiku_vs_opus"  ;;
  focal_S_vs_G) FOCAL_MODEL="anthropic/claude-sonnet-4-5"; CONFIG_DIR="C4_sonnet_vs_gemini" ;;
  focal_G_vs_S) FOCAL_MODEL="google/gemini-3.1-pro-preview"; CONFIG_DIR="C5_gemini_vs_sonnet" ;;
  focal_O_vs_G) FOCAL_MODEL="anthropic/claude-opus-4-7"; CONFIG_DIR="C6_opus_vs_gemini" ;;
  focal_G_vs_X) FOCAL_MODEL="google/gemini-3.1-pro-preview"; CONFIG_DIR="C7_gemini_vs_gpt55" ;;
  focal_G35_vs_X) FOCAL_MODEL="google/gemini-3.5-flash"; CONFIG_DIR="C8_gemini35_vs_gpt55" ;;
  focal_O_vs_X) FOCAL_MODEL="anthropic/claude-opus-4.8"; CONFIG_DIR="C9_opus48_vs_gpt55" ;;
  focal_X_vs_O48) FOCAL_MODEL="openai/gpt-5.5"; CONFIG_DIR="C10_gpt55_vs_opus48" ;;
  *) echo "ERROR: unknown config '$CONFIG'"; exit 1 ;;
esac

case "$PHASE" in
  1|2|3) ;;
  *) echo "ERROR: phase must be 1, 2, or 3 (got '$PHASE')"; exit 1 ;;
esac

export MARKETPLACE_PHASE="$PHASE"

TASK_FILE="tasks/paper_runs/${CONFIG}_phase${PHASE}.jsonl"
OUT_DIR="results/paper_runs/${CONFIG_DIR}/phase${PHASE}"
ROLLOUTS_OUT="$OUT_DIR/rollouts.jsonl"
AGG_OUT="$OUT_DIR/aggregate.json"
INSIGHTS="$OUT_DIR/INSIGHTS.md"
CREDIT_LOG="data/credit_log.jsonl"

mkdir -p "$OUT_DIR" data results/runs

echo "============================================================"
echo "  Paper run: $CONFIG  /  phase $PHASE"
echo "  focal_model: $FOCAL_MODEL"
echo "  output:      $OUT_DIR"
echo "============================================================"

# --- step 1: env + credit pre-flight ---------------------------------------

if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "ERROR: .env missing at $PROJECT_DIR/.env"
  exit 1
fi
set -a; source "$PROJECT_DIR/.env"; set +a
if [ -z "$OPENROUTER_API_KEY" ]; then echo "ERROR: OPENROUTER_API_KEY not set"; exit 1; fi
echo "✓ env loaded"

if [ ! -d "$PROJECT_DIR/.venv" ]; then echo "ERROR: .venv missing"; exit 1; fi
PY=".venv/bin/python"

if [ ! -s "$TASK_FILE" ]; then
  echo "ERROR: task file missing: $TASK_FILE"
  exit 1
fi
NLINES=$(wc -l < "$TASK_FILE")
echo "✓ task file: $TASK_FILE ($NLINES rollouts)"

# Credit check (capture pre-run balance for delta logging)
CREDIT_BEFORE=$(curl -s -X GET https://openrouter.ai/api/v1/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  | "$PY" -c "import sys,json; d=json.load(sys.stdin).get('data',{}); lr=d.get('limit_remaining'); print(lr if lr is not None else 'uncapped')")
USAGE_BEFORE=$(curl -s -X GET https://openrouter.ai/api/v1/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('usage',0))")
echo "✓ credit remaining: \$$CREDIT_BEFORE  (usage so far: \$$USAGE_BEFORE)"

if [ "$CREDIT_BEFORE" != "uncapped" ]; then
  if ! "$PY" -c "import sys; sys.exit(0 if float('$CREDIT_BEFORE') >= 20 else 1)"; then
    echo "ERROR: credit balance \$$CREDIT_BEFORE is below \$20 floor — aborting."
    exit 1
  fi
fi

# --- step 2: set env.yaml::policy_model_name -------------------------------

sed -i.bak "s|policy_model_name:.*|policy_model_name: $FOCAL_MODEL|" env.yaml && rm -f env.yaml.bak
echo "✓ env.yaml policy_model_name set to: $(grep policy_model_name env.yaml | tr -d ' ')"

# --- step 3: restart ng_run with the new focal -----------------------------

echo "→ restarting ng_run with fresh state"
bash scripts/restart_ng_run.sh

# --- step 4: run rollouts --------------------------------------------------

echo ""
echo "→ collecting $NLINES rollouts"
START_TS=$(date +%s)
.venv/bin/ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath="$PWD/$TASK_FILE" \
  +output_jsonl_fpath="$PWD/$ROLLOUTS_OUT" \
  +limit="$NLINES" \
  +num_repeats=1 \
  +resume_from_cache=True 2>&1 | tee -a "$OUT_DIR/rollout.log"
END_TS=$(date +%s)
WALL_SECS=$((END_TS - START_TS))
echo "✓ rollouts done in ${WALL_SECS}s"

# --- step 5: archive per-rollout folders -----------------------------------

if [ -s "$ROLLOUTS_OUT" ]; then
  .venv/bin/python scripts/archive_run.py --input "$ROLLOUTS_OUT" --runs-dir results/runs/
  echo "✓ archived per-rollout folders into results/runs/"
fi

# --- step 6: aggregate (per-phase summary used to live in results/aggregates) ---

# We write a focused per-config-phase aggregate next to the rollouts.
.venv/bin/python -c "
import json
from pathlib import Path
src = Path('$ROLLOUTS_OUT')
out = Path('$AGG_OUT')
rollouts = [json.loads(l) for l in src.open()]
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs)/len(xs) if xs else None
agg = {
    'config_name': '$CONFIG',
    'phase': $PHASE,
    'focal_model': '$FOCAL_MODEL',
    'rollout_count': len(rollouts),
    'mean_reward': mean([r.get('reward') for r in rollouts]),
    'min_reward':  min([r.get('reward') for r in rollouts], default=None),
    'max_reward':  max([r.get('reward') for r in rollouts], default=None),
    'per_rollout': [
        {
            'id': r.get('id'),
            'set_id': (r.get('metadata') or {}).get('set_id'),
            'focal_persona': (r.get('metadata') or {}).get('focal_persona'),
            'reward': r.get('reward'),
            'rubric_scores': r.get('rubric_scores'),
            'num_deals': len(r.get('deals') or []),
            'num_channel_events': len(r.get('channel_events') or []),
        }
        for r in rollouts
    ],
}
out.write_text(json.dumps(agg, indent=2))
print(f'wrote {out}: mean_reward={agg[\"mean_reward\"]}')
"

# --- step 6.5: per-set channel + deals + summary files ---------------------

if [ -s "$ROLLOUTS_OUT" ]; then
  .venv/bin/python scripts/extract_per_set_channels.py \
    --in "$ROLLOUTS_OUT" \
    --out-dir "$OUT_DIR/per_set/"
fi

# NOTE: truncation+rescore step has been removed. Since restart_ng_run.sh
# now sets simple_agent.max_steps=50, every rollout natively runs within
# ~100 channel events. The post-hoc truncation we used for C1 P1/P2 (which
# ran before the cap was active) is no longer needed and would just add
# noise from non-deterministic judge re-calls.

# --- step 7: post-run credit delta + INSIGHTS stub -------------------------

CREDIT_AFTER=$(curl -s -X GET https://openrouter.ai/api/v1/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  | "$PY" -c "import sys,json; d=json.load(sys.stdin).get('data',{}); lr=d.get('limit_remaining'); print(lr if lr is not None else 'uncapped')")
USAGE_AFTER=$(curl -s -X GET https://openrouter.ai/api/v1/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('usage',0))")

# Compute spend (usage delta)
SPEND=$("$PY" -c "print(round(float('$USAGE_AFTER') - float('$USAGE_BEFORE'), 6))")

echo "✓ credit after: \$$CREDIT_AFTER  (spend this run: \$$SPEND, wall ${WALL_SECS}s)"

# Append to credit log
"$PY" -c "
import json, datetime, pathlib
log = pathlib.Path('$CREDIT_LOG')
log.parent.mkdir(parents=True, exist_ok=True)
row = {
    'ts': datetime.datetime.now().isoformat(timespec='seconds'),
    'config': '$CONFIG',
    'phase': $PHASE,
    'focal_model': '$FOCAL_MODEL',
    'rollouts': $NLINES,
    'credit_before': '$CREDIT_BEFORE',
    'credit_after':  '$CREDIT_AFTER',
    'usage_before':  float('$USAGE_BEFORE'),
    'usage_after':   float('$USAGE_AFTER'),
    'spend':         float('$SPEND'),
    'wall_secs':     $WALL_SECS,
}
with log.open('a') as f:
    f.write(json.dumps(row) + '\n')
print(f'logged → {log}')
"

# INSIGHTS.md stub (analysis is filled in by Claude after the run completes)
if [ ! -f "$INSIGHTS" ]; then
cat > "$INSIGHTS" <<EOF
# INSIGHTS — $CONFIG / phase $PHASE

**Focal model:** $FOCAL_MODEL
**Opponents:** see model_config.py for the field
**Rollouts:** $NLINES (one per persona set, seed 42)
**Spend:** \$$SPEND
**Wall time:** ${WALL_SECS}s

## Aggregate

\`\`\`
$( "$PY" -c "import json; d=json.load(open('$AGG_OUT')); print(json.dumps({k:v for k,v in d.items() if k!='per_rollout'}, indent=2))" )
\`\`\`

## Per-rollout summary

| set | focal | reward | deals | events |
|-----|-------|-------:|------:|-------:|
$( "$PY" -c "
import json
for r in json.load(open('$AGG_OUT'))['per_rollout']:
    rew = r['reward']
    print(f\"| {r['set_id']} | {r['focal_persona']} | {rew:.3f} | {r['num_deals']} | {r['num_channel_events']} |\" if rew is not None else f\"| {r['set_id']} | {r['focal_persona']} | n/a | {r['num_deals']} | {r['num_channel_events']} |\")
" )

## Findings

_(filled in after reading the transcripts)_

## Notable rollouts

_(quote 1-2 surprising deals or stalls)_

EOF
echo "✓ wrote $INSIGHTS (stub)"
fi

echo ""
echo "Done: $CONFIG / phase $PHASE"
