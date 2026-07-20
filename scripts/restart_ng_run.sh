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
NEMO_GYM_DIR="$PROJECT_DIR/nemo_gym_lib"
LOG_FILE="$PROJECT_DIR/output_paper_runs.log"
HEALTH_TIMEOUT=120

cd "$PROJECT_DIR"

# Source .env so OPENROUTER_API_KEY is available to ng_run.
# A value already in the environment WINS over the file: the host injects the key at run
# time (e.g. `docker run -e OPENROUTER_API_KEY=...`), and `source` would otherwise assign
# the file's value straight over the top of it — silently, with no error, leaving the run
# using the wrong key. The environment is an instruction; a file baked into the image is
# only a default.
if [ -f "$PROJECT_DIR/.env" ]; then
  _injected_openrouter_key="${OPENROUTER_API_KEY:-}"
  set -a
  source "$PROJECT_DIR/.env"
  set +a
  if [ -n "$_injected_openrouter_key" ]; then
    export OPENROUTER_API_KEY="$_injected_openrouter_key"
  fi
  unset _injected_openrouter_key
fi

echo "[$(date +%H:%M:%S)] restart_ng_run: starting"
echo "[$(date +%H:%M:%S)] policy_model_name: $(grep policy_model_name env.yaml | tr -d ' ')"

# --- step 1: kill anything currently using port 11000 -----------------------

EXISTING=$(pgrep -f "bin/ng_run" || true)
if [ -n "$EXISTING" ]; then
  echo "[$(date +%H:%M:%S)] found existing ng_run PIDs: $(echo "$EXISTING" | tr '\n' ' ')"
  echo "$EXISTING" | xargs kill -TERM 2>/dev/null || true
  sleep 3
  STILL=$(pgrep -f "bin/ng_run" || true)
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
FOCAL_MAX_STEPS="${FOCAL_MAX_STEPS:-50}"   # env-overridable (adapter sets ceil(max_turns/2)); default 50
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

# Install our runtime patches into ALL NeMo Gym subserver venvs. site.py executes the
# .pth's import line at interpreter startup, so the patches land before any user code
# builds a schema. NeMo Gym's own source is never modified.
#
# The whole nemo_gym_patches PACKAGE goes in, next to the .pth that imports it — a new
# fix is a new module in that package. The earlier version copied a single patch file
# onto sitecustomize.py, which was wrong twice over:
#   1. sitecustomize is ONE name, so patch #2 would silently overwrite patch #1.
#   2. Python imports only the FIRST sitecustomize on sys.path, and Ubuntu ships
#      /usr/lib/python3.12/sitecustomize.py (apport) ahead of every venv's
#      site-packages. The venv-local copy was shadowed and never ran at all — so the
#      Opus 4.7 fix has been silently inactive on Linux since the port. It worked on
#      macOS, which ships no system sitecustomize. A .pth cannot be shadowed.
#
# Unconditional by design. Every patch only WIDENS a schema (accepts a value NeMo Gym
# used to reject), so there is no focal model it can harm. The old `if opus` gate left
# the previous run's file installed while printing "skipping runtime patch" — a claim
# that contradicted the files on disk.
#
# The validation happens in BOTH subservers:
#  - policy_model       — validates OpenRouter's response before forwarding
#  - simple_agent       — re-validates the response it receives from policy_model
# Both venvs need the patches installed.
PATCH_PKG="$PROJECT_DIR/scripts/nemo_gym_patches"
PATCH_PTH="$PROJECT_DIR/scripts/zz_nemo_gym_patches.pth"
for VENV_BASE in \
    "$NEMO_GYM_DIR/responses_api_models/openai_model" \
    "$NEMO_GYM_DIR/responses_api_agents/simple_agent" \
    "$NEMO_GYM_DIR/resources_servers/marketplace"
do
  SITE_DIR="$VENV_BASE/.venv/lib/python3.12/site-packages"
  if [ -d "$PATCH_PKG" ] && [ -f "$PATCH_PTH" ] && [ -d "$SITE_DIR" ]; then
    # Replace the package wholesale, so a patch deleted from the repo also leaves the venv.
    rm -rf "$SITE_DIR/nemo_gym_patches"
    cp -r "$PATCH_PKG" "$SITE_DIR/nemo_gym_patches"
    cp "$PATCH_PTH" "$SITE_DIR/zz_nemo_gym_patches.pth"
    # Leftover from the shadowed mechanism; harmless but misleading if anyone finds it.
    rm -f "$SITE_DIR/sitecustomize.py"
    echo "[$(date +%H:%M:%S)] installed runtime patches → $(basename $VENV_BASE)/.venv/.../nemo_gym_patches"
  fi
done

# Ray object store: a container's /dev/shm defaults to only 64MB (RLEaaS's docker
# run / k8s pod won't enlarge it). Cap Ray's object store small and let Ray fall
# back to /tmp so ng_run boots without needing --shm-size. Harmless on the host
# (marketplace payloads are tiny JSON). Override-able via the same env name.
export RAY_object_store_memory="${RAY_object_store_memory:-134217728}"   # 128MB

echo "[$(date +%H:%M:%S)] launching ng_run (logs → $LOG_FILE)"
echo "[$(date +%H:%M:%S)] focal max_steps cap: $FOCAL_MAX_STEPS  ray_object_store=${RAY_object_store_memory}"

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
