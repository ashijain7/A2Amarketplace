#!/usr/bin/env bash
# Kill any running ng_run, wait for port 11000 to free, then restart in the background.
# Health-checks the new instance and errors loud if it doesn't come up.
#
# Usage:
#   bash scripts/restart_ng_run.sh
#
# Reads env.yaml at restart time → use this AFTER editing env.yaml::policy_model_name.
# Logs go to output_paper_runs.log (truncated each restart).

set -e

NG_HEAD_PORT=11000
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NEMO_GYM_DIR="/Users/ashi.jain/Documents/nemo_gym_lib"
LOG_FILE="$PROJECT_DIR/output_paper_runs.log"
HEALTH_TIMEOUT=120

cd "$PROJECT_DIR"

# Source .env so OPENROUTER_API_KEY is available to ng_run
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

echo "[$(date +%H:%M:%S)] restart_ng_run: starting"
echo "[$(date +%H:%M:%S)] policy_model_name: $(grep policy_model_name env.yaml | tr -d ' ')"

# --- step 1: kill anything currently using port 11000 -----------------------

EXISTING=$(pgrep -f "ng_run" || true)
if [ -n "$EXISTING" ]; then
  echo "[$(date +%H:%M:%S)] found existing ng_run PIDs: $(echo "$EXISTING" | tr '\n' ' ')"
  echo "$EXISTING" | xargs kill -TERM 2>/dev/null || true
  sleep 3
  STILL=$(pgrep -f "ng_run" || true)
  if [ -n "$STILL" ]; then
    echo "[$(date +%H:%M:%S)] some ng_run survived TERM, sending KILL: $(echo "$STILL" | tr '\n' ' ')"
    echo "$STILL" | xargs kill -KILL 2>/dev/null || true
    sleep 2
  fi
fi

# Verify port is free
for i in $(seq 1 15); do
  if ! lsof -i ":$NG_HEAD_PORT" -sTCP:LISTEN > /dev/null 2>&1; then
    break
  fi
  echo "[$(date +%H:%M:%S)] port $NG_HEAD_PORT still bound, waiting..."
  sleep 1
done
if lsof -i ":$NG_HEAD_PORT" -sTCP:LISTEN > /dev/null 2>&1; then
  echo "ERROR: port $NG_HEAD_PORT still in use after 15s — investigate before retrying."
  lsof -i ":$NG_HEAD_PORT" -sTCP:LISTEN
  exit 1
fi
echo "[$(date +%H:%M:%S)] port $NG_HEAD_PORT is free"

# --- step 2: relaunch ng_run in the background ------------------------------

CONFIG_PATHS="[$NEMO_GYM_DIR/resources_servers/marketplace/configs/marketplace.yaml,$NEMO_GYM_DIR/responses_api_models/openai_model/configs/openai_model.yaml]"

# Cap focal at 50 tool calls per rollout (~100 channel events total).
# Without this, Sonnet self-play can loop indefinitely on certain personas
# (e.g. Kai in C1 P2 went past 280 events with no focal_done signal).
FOCAL_MAX_STEPS=50
# When settlement is on, the 50 above is the PUBLIC-market budget; the focal
# needs extra calls afterwards to settle its deals (pay / confirm / talk in the
# private room). So raise the hard total and tell the server the public cap.
# The marketplace endpoints (post_listing/offer/...) refuse past FOCAL_PUBLIC_MAX,
# so the extra calls can ONLY be spent on settlement — a payment budget separate
# from public shopping. Each settlement call CAN invoke the live counterparty
# (scammer), so keep it bounded; observed usage is ~4-9 calls even for 3-deal sets.
if [ "${ENABLE_SETTLEMENT:-no}" = "yes" ]; then
  FOCAL_PUBLIC_MAX_STEPS="${FOCAL_PUBLIC_MAX_STEPS:-50}"
  FOCAL_MAX_STEPS=$(( FOCAL_PUBLIC_MAX_STEPS + 30 ))   # public 50 + 30 dedicated payment calls
  export FOCAL_PUBLIC_MAX_STEPS
  echo "[$(date +%H:%M:%S)] settlement on: public cap=$FOCAL_PUBLIC_MAX_STEPS, total max_steps=$FOCAL_MAX_STEPS"
fi

# Install our runtime patch into ALL NeMo Gym subserver venvs as
# sitecustomize.py. Python's site.py auto-loads sitecustomize at startup,
# applying the patch before any user code runs. Required for Opus 4.7
# focal runs (Opus returns service_tier='standard' which NeMo Gym's
# schema otherwise rejects). Safe no-op for non-Opus focals.
#
# The validation happens in BOTH subservers:
#  - policy_model       — validates OpenRouter's response before forwarding
#  - simple_agent       — re-validates the response it receives from policy_model
# Both venvs need the patch installed.
FOCAL_MODEL=$(grep "policy_model_name" env.yaml | sed 's/.*policy_model_name:[[:space:]]*//')
PATCH_SOURCE="$PROJECT_DIR/scripts/nemo_gym_runtime_patch.py"
if echo "$FOCAL_MODEL" | grep -qi "opus"; then
  for VENV_BASE in \
      "$NEMO_GYM_DIR/responses_api_models/openai_model" \
      "$NEMO_GYM_DIR/responses_api_agents/simple_agent" \
      "$NEMO_GYM_DIR/resources_servers/marketplace"
  do
    SITE_DIR="$VENV_BASE/.venv/lib/python3.12/site-packages"
    if [ -f "$PATCH_SOURCE" ] && [ -d "$SITE_DIR" ]; then
      cp "$PATCH_SOURCE" "$SITE_DIR/sitecustomize.py"
      echo "[$(date +%H:%M:%S)] installed runtime patch → $(basename $VENV_BASE)/.venv/.../sitecustomize.py"
    fi
  done
else
  echo "[$(date +%H:%M:%S)] skipping runtime patch (focal=$FOCAL_MODEL — not Opus)"
fi

echo "[$(date +%H:%M:%S)] launching ng_run (logs → $LOG_FILE)"
echo "[$(date +%H:%M:%S)] focal max_steps cap: $FOCAL_MAX_STEPS"

# Truncate log so each restart starts clean
: > "$LOG_FILE"

nohup .venv/bin/ng_run "+config_paths=$CONFIG_PATHS" \
  "+marketplace_agent.responses_api_agents.simple_agent.max_steps=$FOCAL_MAX_STEPS" \
  > "$LOG_FILE" 2>&1 &

NG_PID=$!
echo "[$(date +%H:%M:%S)] ng_run launched with PID $NG_PID"

# --- step 3: health-check ---------------------------------------------------

echo "[$(date +%H:%M:%S)] health-checking port $NG_HEAD_PORT (timeout ${HEALTH_TIMEOUT}s)..."
for i in $(seq 1 "$HEALTH_TIMEOUT"); do
  if curl -s "http://127.0.0.1:$NG_HEAD_PORT/global_config_dict_yaml" > /dev/null 2>&1; then
    echo "[$(date +%H:%M:%S)] ✓ ng_run is healthy on port $NG_HEAD_PORT (took ${i}s)"
    exit 0
  fi
  # Quick sanity: did the process die already?
  if ! kill -0 "$NG_PID" 2>/dev/null; then
    echo "ERROR: ng_run PID $NG_PID died during startup. Tail of log:"
    tail -50 "$LOG_FILE"
    exit 2
  fi
  sleep 1
done

echo "ERROR: ng_run did not respond on port $NG_HEAD_PORT within ${HEALTH_TIMEOUT}s."
echo "Tail of $LOG_FILE:"
tail -50 "$LOG_FILE"
exit 3
