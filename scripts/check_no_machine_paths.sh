#!/usr/bin/env bash
# Fail if any of project_deal's own source carries an absolute machine path
# (/Users/... or /home/<user>). Portable-path rule: derive from an anchor
# (config.ROOT / PROJECT_DIR), never hardcode a machine dir. Run before packaging.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
hits=$(grep -rnE "/Users/|/home/[a-z]" \
  --include=*.py --include=*.sh --include=*.yaml --include=*.jsonl \
  --exclude-dir=.venv --exclude-dir=nemo_gym_lib --exclude-dir=.git \
  --exclude-dir=results --exclude-dir=data --exclude-dir=outputs \
  --exclude=check_no_machine_paths.sh . || true)
FOUND=0
if [ -n "$hits" ]; then
  echo "BAD: absolute machine path(s) found — use a derived/relative path:"
  echo "$hits"
  FOUND=1
fi

# --- Forked nemo_gym dirs: our own edits must stay machine-path-free too.
# (The ~85 stock upstream servers are intentionally NOT scanned — their tests
#  legitimately contain /Users paths.)
FORKED_DIRS=(
  "nemo_gym_lib/resources_servers/marketplace"
  "nemo_gym_lib/responses_api_agents/simple_agent"
  "nemo_gym_lib/responses_api_models/openai_model"
)
for d in "${FORKED_DIRS[@]}"; do
  if [ -d "$d" ]; then
    fhits=$(grep -rnE "/Users/|/home/[a-z]" "$d" \
             --include='*.py' --include='*.sh' --include='*.yaml' --include='*.yml' \
             --include='*.txt' --include='*.jsonl' \
             --exclude-dir=.venv --exclude-dir=build --exclude-dir=cache \
             --exclude-dir=__pycache__ --exclude-dir=.git 2>/dev/null || true)
    if [ -n "$fhits" ]; then
      echo "MACHINE PATH in forked nemo_gym dir:"
      echo "$fhits"
      FOUND=1
    fi
  fi
done

if [ "$FOUND" -ne 0 ]; then
  exit 1
fi
echo "OK: no absolute machine paths in project_deal source."
