# C8 (Gemini 3.5 Flash vs GPT-5.5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fifth paper config (C8: `google/gemini-3.5-flash` focal vs 9× `openai/gpt-5.5` opponents), run it across all 3 phases × 5 persona sets (15 rollouts), and produce writeups matching existing C1/C4/C6/C7 depth, including a rewrite of `CROSS_CONFIG_COMPARISON.md` to cover 5 configs × 3 phases.

**Architecture:** The existing pipeline is already config-driven. C8 is added by four small patches (one Python constant, one config-dict entry, one shell-case branch, three regenerated task files), then run via the existing `scripts/run_paper_config_phase.sh`. Writeups follow the established structure in `results/paper_runs/C7_gemini_vs_gpt55/`.

**Tech Stack:** Python 3.12, `uv`, NeMo Gym, OpenRouter, pytest, bash. The focal model talks via the OpenRouter OpenAI-compatible endpoint.

**Approved design spec:** `docs/superpowers/specs/2026-05-25-c8-gemini35-vs-gpt55-design.md` (committed in `689e7cb`).

---

## File map

**Files modified:**
- `project_deal_approach_1/marketplace/config.py` (add 1 constant)
- `project_deal_approach_1/resources_server/model_config.py` (add 1 alias, 1 entry to `_CONFIGS`, 1 entry to `CONFIG_NAMES`)
- `project_deal_approach_1/scripts/run_paper_config_phase.sh` (add 1 case branch)
- `project_deal_approach_1/tests/test_model_config.py` (add 1 test, update existing assertion)
- `project_deal_approach_1/results/paper_runs/CROSS_CONFIG_COMPARISON.md` (rewrite to 5 configs)

**Files created:**
- `project_deal_approach_1/tasks/paper_runs/focal_G35_vs_X_phase{1,2,3}.jsonl` (3 files via `generate_tasks.py`)
- `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase{1,2,3}/INSIGHTS.md` (3 files)
- `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/COMPARISON.md`
- `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase{1,2,3}/{aggregate.json,rollouts.jsonl,rollouts_aggregate_metrics.json,rollouts_materialized_inputs.jsonl,rollout.log,set_NN_<focal>/...}` (auto-written by the run script)

---

## Task 1: Add `GEMINI_FLASH_MODEL` constant to marketplace config

**Files:**
- Modify: `project_deal_approach_1/marketplace/config.py:36-41`

- [ ] **Step 1: Add the constant**

Edit `project_deal_approach_1/marketplace/config.py`. Locate the model-constant block (lines 36-41):

```python
DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"
HAIKU_MODEL = "anthropic/claude-haiku-4-5"
OPUS_MODEL = "anthropic/claude-opus-4-7"
GEMINI_MODEL = "google/gemini-3.1-pro-preview"
GPT5_5_MODEL = "openai/gpt-5.5"
JUDGE_MODEL = "openai/gpt-4o-2024-11-20"
```

Insert a new line between `GEMINI_MODEL` and `GPT5_5_MODEL`:

```python
DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"
HAIKU_MODEL = "anthropic/claude-haiku-4-5"
OPUS_MODEL = "anthropic/claude-opus-4-7"
GEMINI_MODEL = "google/gemini-3.1-pro-preview"
GEMINI_FLASH_MODEL = "google/gemini-3.5-flash"
GPT5_5_MODEL = "openai/gpt-5.5"
JUDGE_MODEL = "openai/gpt-4o-2024-11-20"
```

- [ ] **Step 2: Verify the import works**

Run from `project_deal_approach_1/`:

```bash
.venv/bin/python -c "from marketplace.config import GEMINI_FLASH_MODEL; print(GEMINI_FLASH_MODEL)"
```

Expected: `google/gemini-3.5-flash`

- [ ] **Step 3: Do NOT commit yet** — bundled with Task 2 commit.

---

## Task 2: Add `focal_G35_vs_X` entry to `resources_server/model_config.py` (TDD)

**Files:**
- Modify: `project_deal_approach_1/tests/test_model_config.py:13-19` (update `test_all_configs_exist`) and append a new test
- Modify: `project_deal_approach_1/resources_server/model_config.py:5-9, 11-22, 24-35`

- [ ] **Step 1: Write the failing test**

Edit `project_deal_approach_1/tests/test_model_config.py`. Add `GEMINI_FLASH` to the imports at the top:

```python
from resources_server.model_config import (
    get_model_config,
    CONFIG_NAMES,
    SONNET,
    HAIKU,
    OPUS,
    GEMINI,
    GEMINI_FLASH,
    GPT5_5,
)
```

Update `test_all_configs_exist` (around line 13) to include `focal_G35_vs_X`:

```python
def test_all_configs_exist():
    assert set(CONFIG_NAMES) == {
        "focal_S_vs_S", "focal_H_vs_S", "focal_S_vs_H", "focal_H_vs_H",
        "focal_O_vs_H", "focal_H_vs_O", "focal_S_vs_G", "focal_G_vs_S",
        "focal_O_vs_G", "focal_G_vs_X",
        "focal_G35_vs_X",
    }
```

Add a new test at the bottom of the file:

```python
def test_focal_G35_vs_X():
    cfg = get_model_config("focal_G35_vs_X")
    assert cfg["focal_model"] == GEMINI_FLASH
    assert cfg["opponents_model"] == GPT5_5
    assert GEMINI_FLASH == "google/gemini-3.5-flash"
```

- [ ] **Step 2: Run the failing test**

```bash
cd project_deal_approach_1 && .venv/bin/pytest tests/test_model_config.py -v
```

Expected: `ImportError: cannot import name 'GEMINI_FLASH' from 'resources_server.model_config'`. Both new and existing tests fail.

- [ ] **Step 3: Add the alias and config entry**

Edit `project_deal_approach_1/resources_server/model_config.py`.

After line 9 (`GPT5_5 = mp_config.GPT5_5_MODEL`), add:

```python
GEMINI_FLASH = mp_config.GEMINI_FLASH_MODEL  # "google/gemini-3.5-flash"
```

Append `"focal_G35_vs_X"` to the `CONFIG_NAMES` list (the list ends at line 22 with `"focal_G_vs_X",`). New list:

```python
CONFIG_NAMES = [
    "focal_S_vs_S",
    "focal_H_vs_S",
    "focal_S_vs_H",
    "focal_H_vs_H",
    "focal_O_vs_H",
    "focal_H_vs_O",
    "focal_S_vs_G",
    "focal_G_vs_S",
    "focal_O_vs_G",
    "focal_G_vs_X",
    "focal_G35_vs_X",
]
```

Append the new entry to the `_CONFIGS` dict (after line 34, the `focal_G_vs_X` line). New entry:

```python
    "focal_G35_vs_X": {"focal_model": GEMINI_FLASH, "opponents_model": GPT5_5},
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd project_deal_approach_1 && .venv/bin/pytest tests/test_model_config.py -v
```

Expected: all tests pass, including `test_focal_G35_vs_X` and the updated `test_all_configs_exist`.

- [ ] **Step 5: Run the full test suite**

```bash
cd project_deal_approach_1 && .venv/bin/pytest tests/ -q
```

Expected: all tests pass. If `test_generate_tasks.py` fails due to the new config name being in `CONFIG_NAMES`, capture the failure mode — `generate_tasks.py` iterates `CONFIG_NAMES`, so the new entry may cause it to attempt task generation for configs without task files. That's acceptable and gets resolved in Task 4.

If a generate-tasks test fails with a hard error (not just a missing-file warning), STOP and read the failure before continuing.

- [ ] **Step 6: Commit Tasks 1 + 2 together**

```bash
git add project_deal_approach_1/marketplace/config.py \
        project_deal_approach_1/resources_server/model_config.py \
        project_deal_approach_1/tests/test_model_config.py
git commit -m "$(cat <<'EOF'
feat(config): add focal_G35_vs_X (Gemini 3.5 Flash vs GPT-5.5)

Adds GEMINI_FLASH_MODEL constant and wires it into the C8 paper config.
Test coverage in test_model_config.py mirrors existing focal_G_vs_X tests.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add `focal_G35_vs_X` case branch to the run script

**Files:**
- Modify: `project_deal_approach_1/scripts/run_paper_config_phase.sh:36-45`

- [ ] **Step 1: Add the new case branch**

Edit `project_deal_approach_1/scripts/run_paper_config_phase.sh`. The current case block ends like this (lines 43-45):

```bash
  focal_G_vs_X) FOCAL_MODEL="google/gemini-3.1-pro-preview"; CONFIG_DIR="C7_gemini_vs_gpt55" ;;
  *) echo "ERROR: unknown config '$CONFIG'"; exit 1 ;;
esac
```

Insert one new branch between the C7 line and the catch-all:

```bash
  focal_G_vs_X) FOCAL_MODEL="google/gemini-3.1-pro-preview"; CONFIG_DIR="C7_gemini_vs_gpt55" ;;
  focal_G35_vs_X) FOCAL_MODEL="google/gemini-3.5-flash"; CONFIG_DIR="C8_gemini35_vs_gpt55" ;;
  *) echo "ERROR: unknown config '$CONFIG'"; exit 1 ;;
esac
```

- [ ] **Step 2: Dry-run verify the script accepts the new config**

Run from `project_deal_approach_1/`:

```bash
bash -n scripts/run_paper_config_phase.sh   # syntax check
grep "focal_G35_vs_X" scripts/run_paper_config_phase.sh
```

Expected: no syntax errors; the grep finds exactly one line.

- [ ] **Step 3: Update the usage comment at the top of the script**

The header comment (line 7) lists the valid config names. Edit it to include `focal_G35_vs_X`:

Before:
```bash
#   <config_name>  one of: focal_S_vs_S focal_O_vs_H focal_H_vs_O focal_S_vs_G focal_G_vs_S
```

After:
```bash
#   <config_name>  one of: focal_S_vs_S focal_O_vs_H focal_H_vs_O focal_S_vs_G focal_G_vs_S focal_O_vs_G focal_G_vs_X focal_G35_vs_X
```

- [ ] **Step 4: Commit**

```bash
git add project_deal_approach_1/scripts/run_paper_config_phase.sh
git commit -m "$(cat <<'EOF'
feat(scripts): add focal_G35_vs_X case to run_paper_config_phase.sh

Maps the C8 config name to its focal model slug and output folder
(C8_gemini35_vs_gpt55). Also brings the usage comment up to date with
all currently wired configs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Generate C8 task files for all three phases

**Files:**
- Create: `project_deal_approach_1/tasks/paper_runs/focal_G35_vs_X_phase1.jsonl`
- Create: `project_deal_approach_1/tasks/paper_runs/focal_G35_vs_X_phase2.jsonl`
- Create: `project_deal_approach_1/tasks/paper_runs/focal_G35_vs_X_phase3.jsonl`

- [ ] **Step 1: Generate Phase 1 task file**

Run from `project_deal_approach_1/`:

```bash
.venv/bin/python tasks/generate_tasks.py --phase 1 --config-filter focal_G35_vs_X
```

Expected output: a confirmation that `tasks/paper_runs/focal_G35_vs_X_phase1.jsonl` was written with 5 lines (one per persona set).

- [ ] **Step 2: Verify Phase 1 task file**

```bash
wc -l tasks/paper_runs/focal_G35_vs_X_phase1.jsonl
head -1 tasks/paper_runs/focal_G35_vs_X_phase1.jsonl | .venv/bin/python -c "import sys, json; d = json.loads(sys.stdin.read()); print(d['metadata']['config_name'], d['metadata']['set_id'], d['metadata']['focal_persona'])"
```

Expected:
- Line count: `5`
- First-line metadata: `focal_G35_vs_X set_01 Kai`

- [ ] **Step 3: Generate Phase 2 task file**

```bash
.venv/bin/python tasks/generate_tasks.py --phase 2 --config-filter focal_G35_vs_X
wc -l tasks/paper_runs/focal_G35_vs_X_phase2.jsonl
```

Expected: 5 lines.

- [ ] **Step 4: Generate Phase 3 task file**

```bash
.venv/bin/python tasks/generate_tasks.py --phase 3 --config-filter focal_G35_vs_X
wc -l tasks/paper_runs/focal_G35_vs_X_phase3.jsonl
```

Expected: 5 lines.

- [ ] **Step 5: Diff against C7 to confirm content parity**

The C8 task files should be byte-identical to C7's except for `metadata.config_name` and `metadata.task_id` fields. Verify by extracting non-metadata fields:

```bash
.venv/bin/python -c "
import json
for phase in (1, 2, 3):
    a = [json.loads(l) for l in open(f'tasks/paper_runs/focal_G_vs_X_phase{phase}.jsonl')]
    b = [json.loads(l) for l in open(f'tasks/paper_runs/focal_G35_vs_X_phase{phase}.jsonl')]
    assert len(a) == len(b) == 5, (phase, len(a), len(b))
    for ra, rb in zip(a, b):
        assert ra['responses_create_params'] == rb['responses_create_params'], (phase, ra['id'])
        assert ra['metadata']['set_id'] == rb['metadata']['set_id']
        assert ra['metadata']['focal_persona'] == rb['metadata']['focal_persona']
        assert rb['metadata']['config_name'] == 'focal_G35_vs_X'
    print(f'phase {phase}: 5 rollouts, content-identical to C7 except config_name/task_id')
"
```

Expected: 3 lines confirming parity.

- [ ] **Step 6: Commit the new task files**

```bash
git add project_deal_approach_1/tasks/paper_runs/focal_G35_vs_X_phase{1,2,3}.jsonl
git commit -m "$(cat <<'EOF'
chore(tasks): generate focal_G35_vs_X task files for phases 1-3

5 rollouts per phase, one per persona set, seed=42. Content is identical
to C7's task files except for metadata.config_name and metadata.task_id.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Pre-flight — slug verification

**Files:** none (read-only network check)

- [ ] **Step 1: Source the API key**

Run from `project_deal_approach_1/`:

```bash
set -a; source .env; set +a
echo "OPENROUTER_API_KEY length: ${#OPENROUTER_API_KEY}"
```

Expected: a non-zero length (typically 60-80 chars).

- [ ] **Step 2: 1-token chat completion against `google/gemini-3.5-flash`**

```bash
curl -sS https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemini-3.5-flash",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 1
  }' | .venv/bin/python -c "import sys, json; d = json.loads(sys.stdin.read()); print('status_ok' if d.get('choices') else f'ERROR: {d}')"
```

Expected: `status_ok`. If `ERROR:`, STOP — slug is wrong or model is unavailable. Re-check OpenRouter listing.

- [ ] **Step 3: Tool-call schema sanity check**

```bash
curl -sS https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemini-3.5-flash",
    "messages": [{"role": "user", "content": "Use the ping tool."}],
    "tools": [{"type": "function", "function": {"name": "ping", "description": "test", "parameters": {"type": "object", "properties": {}, "required": []}}}],
    "max_tokens": 50
  }' | .venv/bin/python -c "import sys, json; d = json.loads(sys.stdin.read()); ch = d.get('choices', [{}])[0]; tc = ch.get('message', {}).get('tool_calls'); print('tool_call_ok' if tc else f'WARN no tool_calls: {ch}')"
```

Expected: `tool_call_ok`. If `WARN`, the model accepted the schema but didn't choose to call the tool — usually fine, but flag in the smoke-test review.

- [ ] **Step 4: Do NOT commit anything** — this task is read-only verification.

---

## Task 6: Pre-flight — 1-rollout smoke test (Phase 1, set_01)

**Files:**
- Create: `project_deal_approach_1/data/smoke_test_c8/rollouts.jsonl` (temporary)

- [ ] **Step 1: Confirm `ng_run` is running**

The smoke test uses the same NeMo Gym server the full runs use. From `project_deal_approach_1/`:

```bash
curl -sS http://localhost:8000/healthz || echo "ng_run not running"
```

Expected: a JSON health-check response. If `ng_run not running`, start it first:

```bash
bash scripts/restart_ng_run.sh
```

Wait for `restart_ng_run.sh` to print its healthy-on-port line before continuing.

- [ ] **Step 2: Point env.yaml at the new focal**

```bash
sed -i '' "s|policy_model_name:.*|policy_model_name: google/gemini-3.5-flash|" env.yaml
grep policy_model_name env.yaml
```

Expected: `policy_model_name: google/gemini-3.5-flash`

You will also need to restart `ng_run` so it picks up the new env.yaml:

```bash
bash scripts/restart_ng_run.sh
```

- [ ] **Step 3: Prepare a 1-rollout subset of the Phase 1 task file**

```bash
mkdir -p data/smoke_test_c8
head -1 tasks/paper_runs/focal_G35_vs_X_phase1.jsonl > data/smoke_test_c8/input.jsonl
wc -l data/smoke_test_c8/input.jsonl
```

Expected: `1 data/smoke_test_c8/input.jsonl`

- [ ] **Step 4: Run the smoke test**

```bash
export MARKETPLACE_PHASE=1
.venv/bin/ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath="$PWD/data/smoke_test_c8/input.jsonl" \
  +output_jsonl_fpath="$PWD/data/smoke_test_c8/rollouts.jsonl" \
  +limit=1 \
  +num_repeats=1 \
  +resume_from_cache=False 2>&1 | tail -50
```

Expected: the script completes without raising; the last lines show `1/1 rollouts collected` (or similar from NeMo Gym).

- [ ] **Step 5: Verify the smoke-test rollout**

```bash
.venv/bin/python -c "
import json
r = json.loads(open('data/smoke_test_c8/rollouts.jsonl').readline())
n_events = len(r.get('channel_events') or [])
reward = r.get('reward')
tool_calls = sum(1 for e in (r.get('channel_events') or []) if e.get('event_type') in ('listing','offer','counter','accept','reject','pass'))
print(f'reward={reward}  events={n_events}  focal_tool_calls={tool_calls}  exit_clean={r.get(\"truncated\") is not True}')
assert reward is not None, 'reward must be non-null'
assert tool_calls >= 3, f'expected >=3 focal tool calls, got {tool_calls}'
print('SMOKE TEST PASSED')
"
```

Expected: prints `... SMOKE TEST PASSED`. If it fails, STOP and investigate before paying for the full 15-rollout run.

- [ ] **Step 6: Clean up smoke-test artefacts (do NOT commit)**

```bash
rm -rf data/smoke_test_c8
```

The smoke-test data is intentionally not committed — it's a throwaway pre-flight check.

---

## Task 7: Run Phase 1 (5 rollouts)

**Files:**
- Auto-created: `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase1/...`

- [ ] **Step 1: Run the phase**

From `project_deal_approach_1/`:

```bash
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 1 2>&1 | tee /tmp/c8_phase1.log
```

The script auto-handles: env.yaml edit, ng_run restart, 5 rollouts via `ng_collect_rollouts`, per-rollout archiving, aggregate.json, INSIGHTS stub, credit log row.

Expected wall time: ~5-15 minutes. Expected spend: ~$3-7.

- [ ] **Step 2: Verify Phase 1 outputs**

```bash
ls results/paper_runs/C8_gemini35_vs_gpt55/phase1/
.venv/bin/python -c "
import json
agg = json.load(open('results/paper_runs/C8_gemini35_vs_gpt55/phase1/aggregate.json'))
assert agg['rollout_count'] == 5, agg
assert agg['mean_reward'] is not None, agg
print(f'mean_reward={agg[\"mean_reward\"]:.3f}  rollouts={agg[\"rollout_count\"]}')
for r in agg['per_rollout']:
    print(f'  {r[\"set_id\"]:7} {r[\"focal_persona\"]:8} reward={r[\"reward\"]}')
"
ls results/paper_runs/C8_gemini35_vs_gpt55/phase1/per_set/ 2>/dev/null || echo "per_set extraction may have been skipped"
tail -1 data/credit_log.jsonl | .venv/bin/python -c "import sys, json; r = json.loads(sys.stdin.read()); print(f'spend=\${r[\"spend\"]}  wall={r[\"wall_secs\"]}s')"
```

Expected:
- 5 rollouts with non-null rewards
- credit_log row shows non-zero spend

If any rollout has a null reward, capture the rollout id and check `phase1/rollout.log` for the failure mode before proceeding.

- [ ] **Step 3: Stage the data files (commit comes after writeup in Task 10)**

Do NOT commit the rollouts yet — they'll be committed alongside their INSIGHTS analysis in Task 10. Just keep them on disk.

---

## Task 8: Run Phase 2 (5 rollouts)

**Files:**
- Auto-created: `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase2/...`

- [ ] **Step 1: Run the phase**

```bash
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 2 2>&1 | tee /tmp/c8_phase2.log
```

Phase 2 introduces star ratings + lookup tool. Watch the log for `choices=None` retries (the C7 P2 hiccup with GPT-5.5 opponents). The script's underlying `marketplace/llm.py` retry should handle them silently.

Expected wall time: ~7-20 minutes. Expected spend: ~$4-9.

- [ ] **Step 2: Verify Phase 2 outputs**

```bash
.venv/bin/python -c "
import json
agg = json.load(open('results/paper_runs/C8_gemini35_vs_gpt55/phase2/aggregate.json'))
assert agg['rollout_count'] == 5
print(f'mean_reward={agg[\"mean_reward\"]:.3f}')
for r in agg['per_rollout']:
    print(f'  {r[\"set_id\"]:7} {r[\"focal_persona\"]:8} reward={r[\"reward\"]}')
"
```

Expected: 5 rollouts with non-null rewards.

- [ ] **Step 3: Sanity-check lookup-tool usage (paper claim #4)**

```bash
.venv/bin/python -c "
import json
rollouts = [json.loads(l) for l in open('results/paper_runs/C8_gemini35_vs_gpt55/phase2/rollouts.jsonl')]
total_lookups = 0
for r in rollouts:
    for e in (r.get('channel_events') or []):
        if e.get('event_type') == 'lookup_agent' or 'lookup' in str(e.get('tool_name', '')).lower():
            total_lookups += 1
print(f'total_lookups across 5 rollouts: {total_lookups}  mean_per_rollout: {total_lookups/5:.2f}')
"
```

Note the result for the writeup. Per the design spec, this number drives the headline finding for C8: if 0.0, paper claim #4 hardens to "Gemini-family pattern across generations"; if >0, claim becomes "fixed in 3.5 Flash."

---

## Task 9: Run Phase 3 (5 rollouts)

**Files:**
- Auto-created: `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase3/...`

- [ ] **Step 1: Confirm Phase 3 image inputs work with Gemini 3.5 Flash**

Phase 3 uses DeepFashion image inputs in the initial prompt. Gemini 3.5 Flash is multimodal per OpenRouter, but verify with a small image-call test:

```bash
.venv/bin/python -c "
import os, base64, requests
from pathlib import Path
img_path = next(Path('personas_phase3').rglob('*.jpg'), None) or next(Path('personas_phase3').rglob('*.png'), None)
if not img_path:
    print('NO IMAGE FOUND — phase3 personas may not be image-bearing; proceed cautiously')
    raise SystemExit
b64 = base64.b64encode(img_path.read_bytes()).decode()
mime = 'image/jpeg' if str(img_path).endswith('.jpg') else 'image/png'
r = requests.post(
    'https://openrouter.ai/api/v1/chat/completions',
    headers={'Authorization': f'Bearer {os.environ[\"OPENROUTER_API_KEY\"]}'},
    json={
        'model': 'google/gemini-3.5-flash',
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': 'Describe this image in one word.'},
            {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}},
        ]}],
        'max_tokens': 20,
    },
)
print('image_ok' if r.json().get('choices') else f'WARN: {r.json()}')
" || echo "image test failed; check Phase 3 caveats"
```

Expected: `image_ok`. If `WARN`, document Phase 3 as degraded (text-only) in the writeup methodology caveats; do not abort the run — the rollout will still produce text-only results.

- [ ] **Step 2: Run the phase**

```bash
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 3 2>&1 | tee /tmp/c8_phase3.log
```

Expected wall time: ~7-20 minutes. Expected spend: ~$4-9.

- [ ] **Step 3: Verify Phase 3 outputs**

```bash
.venv/bin/python -c "
import json
agg = json.load(open('results/paper_runs/C8_gemini35_vs_gpt55/phase3/aggregate.json'))
assert agg['rollout_count'] == 5
print(f'mean_reward={agg[\"mean_reward\"]:.3f}')
for r in agg['per_rollout']:
    print(f'  {r[\"set_id\"]:7} {r[\"focal_persona\"]:8} reward={r[\"reward\"]}')
"
```

Expected: 5 rollouts with non-null rewards. Phase 3 personas are Kai/Rex/Zara/Buck/Taj (Zara and Buck replace Marcus and Omar).

- [ ] **Step 4: Tally total C8 spend**

```bash
.venv/bin/python -c "
import json
rows = [json.loads(l) for l in open('data/credit_log.jsonl')]
c8_rows = [r for r in rows if r['config'] == 'focal_G35_vs_X']
total = sum(r['spend'] for r in c8_rows)
print(f'C8 total spend across {len(c8_rows)} phases: \${total:.2f}')
"
```

Expected: a number in the ~$15-25 range per the design budget.

---

## Task 10: Write Phase 1 INSIGHTS.md

**Files:**
- Modify (replace stub): `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase1/INSIGHTS.md`

The run script auto-writes a stub INSIGHTS.md with aggregate header + per-rollout table + empty findings sections. Replace it with a complete writeup matching the C7 phase1 INSIGHTS structure.

- [ ] **Step 1: Read the reference**

```bash
cat results/paper_runs/C7_gemini_vs_gpt55/phase1/INSIGHTS.md
```

This is the model. C8 phase1/INSIGHTS.md must have the same sections in the same order, same vocabulary, same level of detail (~250 lines).

- [ ] **Step 2: Gather the C8 P1 data**

```bash
cat results/paper_runs/C8_gemini35_vs_gpt55/phase1/aggregate.json
.venv/bin/python -c "
import json
rollouts = [json.loads(l) for l in open('results/paper_runs/C8_gemini35_vs_gpt55/phase1/rollouts.jsonl')]
for r in rollouts:
    md = r.get('metadata') or {}
    print(f\"=== {md.get('set_id')} / {md.get('focal_persona')} ===\")
    print(f\"  reward={r.get('reward')}  deals={len(r.get('deals') or [])}  events={len(r.get('channel_events') or [])}\")
    print(f\"  rubrics: {json.dumps(r.get('rubric_scores') or {}, indent=4)}\")
"
ls results/paper_runs/C8_gemini35_vs_gpt55/phase1/set_*/
```

- [ ] **Step 3: Read 1-2 channel transcripts for narrative quotes**

```bash
cat results/paper_runs/C8_gemini35_vs_gpt55/phase1/set_03_Marcus/channel.jsonl | head -80
cat results/paper_runs/C8_gemini35_vs_gpt55/phase1/set_05_Taj/channel.jsonl | head -80
```

Pick 1-2 surprising moments (deals, stalls, persona behaviour) to quote in the writeup.

- [ ] **Step 4: Write the full INSIGHTS.md**

Required sections, in this order:

1. Header: `# INSIGHTS — focal_G35_vs_X / phase 1` with focal, opponents, rollouts, spend, wall time, JSON aggregate.
2. `## Per-rollout summary` — markdown table (set / focal / reward / deals / events).
3. `## The 5 things that matter most` — five numbered narrative bullets specific to C8 P1 (e.g., closure rate vs C7, lookup-tool baseline since P1 has no tool, per-persona standouts, opponent-vendor effects with GPT-5.5, cost efficiency).
4. `## The master table` — full rubric breakdown across all 5 rollouts.
5. `## Per-persona breakdown` — one short subsection per persona (Kai / Rex / Marcus / Omar / Taj).
6. `## Notable rollouts` — 1-2 quoted transcript moments.
7. `## What stayed constant / what changed (vs C7 P1)`.
8. `## Methodology caveats` — must include the tier-confound caveat from spec §8.4.

The numbers in the writeup must match the aggregate.json exactly. Layman English: avoid jargon-only labels; explain `Pareto`, `Δ`, `normalized closure` in plain words on first use per the C7 style.

- [ ] **Step 5: Verify the writeup**

```bash
wc -l results/paper_runs/C8_gemini35_vs_gpt55/phase1/INSIGHTS.md
grep -c "^## " results/paper_runs/C8_gemini35_vs_gpt55/phase1/INSIGHTS.md
```

Expected:
- Line count: 200-300 (matches C7's 249 lines for `phase1/INSIGHTS.md` ± 50)
- Section count: 6-9 `## ` headings

---

## Task 11: Write Phase 2 INSIGHTS.md

**Files:**
- Modify (replace stub): `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase2/INSIGHTS.md`

- [ ] **Step 1: Read the reference**

```bash
cat results/paper_runs/C7_gemini_vs_gpt55/phase2/INSIGHTS.md
```

- [ ] **Step 2: Gather the C8 P2 data**

```bash
cat results/paper_runs/C8_gemini35_vs_gpt55/phase2/aggregate.json
.venv/bin/python -c "
import json
rollouts = [json.loads(l) for l in open('results/paper_runs/C8_gemini35_vs_gpt55/phase2/rollouts.jsonl')]
total_lookups = 0
for r in rollouts:
    md = r.get('metadata') or {}
    lookups_here = sum(1 for e in (r.get('channel_events') or []) if 'lookup' in str(e.get('tool_name', e.get('event_type', ''))).lower())
    total_lookups += lookups_here
    print(f\"{md.get('set_id')} {md.get('focal_persona'):8} reward={r.get('reward')} lookups={lookups_here}\")
print(f'TOTAL LOOKUPS: {total_lookups}  MEAN: {total_lookups/5:.2f}')
"
```

- [ ] **Step 3: Write the full INSIGHTS.md**

Same structure as Task 10's section list. The Phase 2 specific narrative MUST address:
- The lookup-tool engagement number (zero or non-zero) and what it means for paper claim #4
- Sell-side resilience vs C6 Opus's catastrophic 0/5 in C6 P2
- Star-rating filter behaviour
- Closure rate compared to C7 P2 (0.40)

- [ ] **Step 4: Verify**

```bash
wc -l results/paper_runs/C8_gemini35_vs_gpt55/phase2/INSIGHTS.md
```

Expected: 200-300 lines.

---

## Task 12: Write Phase 3 INSIGHTS.md

**Files:**
- Modify (replace stub): `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/phase3/INSIGHTS.md`

- [ ] **Step 1: Read the reference**

```bash
cat results/paper_runs/C7_gemini_vs_gpt55/phase3/INSIGHTS.md
```

- [ ] **Step 2: Gather the C8 P3 data**

```bash
cat results/paper_runs/C8_gemini35_vs_gpt55/phase3/aggregate.json
.venv/bin/python -c "
import json
rollouts = [json.loads(l) for l in open('results/paper_runs/C8_gemini35_vs_gpt55/phase3/rollouts.jsonl')]
for r in rollouts:
    md = r.get('metadata') or {}
    swaps = [d for d in (r.get('deals') or []) if d.get('type') == 'swap' or d.get('deal_type') == 'barter']
    print(f\"{md.get('set_id')} {md.get('focal_persona'):8} reward={r.get('reward')} swaps={len(swaps)}\")
"
```

- [ ] **Step 3: Write the full INSIGHTS.md**

Phase 3 narrative MUST cover:
- Mutual-win count (compare to C7 P3 = 2, C6 P3 = 0)
- Whether Gemini 3.5 Flash proposes swaps proactively (the C6 P3 failure mode was Opus refusing to propose)
- Phase 3 personas (Kai/Rex/Zara/Buck/Taj — different from P1/P2)
- Privacy holds (compare against the C7 P3 Zara leak)
- The image-input note if Step 1 of Task 9 flagged anything

- [ ] **Step 4: Verify**

```bash
wc -l results/paper_runs/C8_gemini35_vs_gpt55/phase3/INSIGHTS.md
```

Expected: 200-300 lines.

---

## Task 13: Write the C8 COMPARISON.md

**Files:**
- Create: `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/COMPARISON.md`

- [ ] **Step 1: Read the reference**

```bash
cat results/paper_runs/C7_gemini_vs_gpt55/COMPARISON.md
```

Target: ~250 lines, same 13 sections as C7's COMPARISON.md.

- [ ] **Step 2: Pull all C8 aggregates into one view**

```bash
.venv/bin/python -c "
import json
for ph in (1, 2, 3):
    a = json.load(open(f'results/paper_runs/C8_gemini35_vs_gpt55/phase{ph}/aggregate.json'))
    print(f'phase {ph}: mean_reward={a[\"mean_reward\"]:.3f}  rollouts={a[\"rollout_count\"]}')
    for r in a['per_rollout']:
        print(f'  {r[\"set_id\"]:7} {r[\"focal_persona\"]:8} reward={r[\"reward\"]:.3f}  deals={r[\"num_deals\"]}')
"
```

- [ ] **Step 3: Write the COMPARISON.md**

Required sections (mirror the 13 sections in C7 COMPARISON.md):

1. `# C8 (Gemini 3.5 Flash vs GPT-5.5) — Phase 1 vs Phase 2 vs Phase 3` + summary table.
2. `## What this document does`
3. `## The C8 story in three phases` — one paragraph per phase.
4. `## The 5 things that matter most`
5. `## The master table` — reward, closure, normalized closure, Pareto, value extracted, mean Δ, privacy, mutual wins, cost per phase.
6. `## Why phase transitions happened` (the measurement-vs-reality explanation, like C7 §"Why Phase 3 rebounded").
7. `## Closure trajectory`
8. `## Per-persona phase progression`
9. `## What stayed constant in C8 / What changed dramatically`
10. `## C8 vs the other configs` — 5-config row table.
11. `## Self-perception story across phases`
12. `## Methodology caveats` — must include tier-confound paragraph from spec §8.4.
13. `## Files` + closing italic summary.

- [ ] **Step 4: Verify**

```bash
wc -l results/paper_runs/C8_gemini35_vs_gpt55/COMPARISON.md
grep -c "^## " results/paper_runs/C8_gemini35_vs_gpt55/COMPARISON.md
```

Expected: 200-280 lines, 11-13 `## ` headings.

---

## Task 14: Rewrite CROSS_CONFIG_COMPARISON.md to 5 configs

**Files:**
- Modify (rewrite): `project_deal_approach_1/results/paper_runs/CROSS_CONFIG_COMPARISON.md`

- [ ] **Step 1: Re-read the current 4-config version**

```bash
cat results/paper_runs/CROSS_CONFIG_COMPARISON.md
```

This is ~560 lines. The rewrite preserves the same structure but adds a 5th column (C8) to every table and a per-persona heatmap gains 3 columns (C8 P1, C8 P2, C8 P3).

- [ ] **Step 2: Collect the master metric matrix across all 5 configs × 3 phases**

```bash
.venv/bin/python <<'PY'
import json
from pathlib import Path
configs = ['C1_sonnet_vs_sonnet', 'C4_sonnet_vs_gemini', 'C6_opus_vs_gemini', 'C7_gemini_vs_gpt55', 'C8_gemini35_vs_gpt55']
print('config              p1_reward  p2_reward  p3_reward  total_spend')
for c in configs:
    base = Path(f'results/paper_runs/{c}')
    rewards = []
    spend = 0
    for ph in (1, 2, 3):
        agg = json.load(open(base / f'phase{ph}' / 'aggregate.json'))
        rewards.append(agg['mean_reward'])
    log_rows = [json.loads(l) for l in open('data/credit_log.jsonl')]
    config_name_map = {
        'C1_sonnet_vs_sonnet': 'focal_S_vs_S',
        'C4_sonnet_vs_gemini': 'focal_S_vs_G',
        'C6_opus_vs_gemini': 'focal_O_vs_G',
        'C7_gemini_vs_gpt55': 'focal_G_vs_X',
        'C8_gemini35_vs_gpt55': 'focal_G35_vs_X',
    }
    spend = sum(r['spend'] for r in log_rows if r['config'] == config_name_map[c])
    print(f'{c:22}  {rewards[0]:.3f}    {rewards[1]:.3f}    {rewards[2]:.3f}    ${spend:.2f}')
PY
```

This is your headline matrix data. Cross-check it against the rewards already cited in each per-config COMPARISON.md to catch any drift.

- [ ] **Step 3: Rewrite the doc**

Sections to rewrite (each: change 4-column tables to 5-column, add C8 narrative line):

- "What are the four configurations?" → **five**; add C8 row (`Gemini 3.5 Flash` focal, `9× GPT-5.5`, "Newer Gemini generation test").
- "The 5 things the paper claims" — **revise claim #4** based on C8's actual lookup-tool number. If C8 lookups = 0, harden the claim ("Gemini-family pattern across two generations"). If C8 lookups > 0, reframe ("Gemini 3.1 ignored; Gemini 3.5 Flash engages — generation effect"). Cite the actual C8 number.
- "The headline matrix" — extend table to 5 rows × 3 phases = **15 cells**. Update the "config mean" column and the "Phase mean" row. Update the prose ("C7 is the unique config" sentence may need adjustment if C8 also breaks monotonic decline).
- "The key comparison — why Opus failed where Sonnet didn't" — unchanged narrative, but if its table cites cross-config numbers, extend to include C8 columns.
- All 9 rubric-by-rubric tables — add C8 columns. Each subsection's prose adds 1-2 sentences placing C8 next to the existing pattern.
- "Per-persona heatmap — all 12 cells" → **all 15 cells**.
- "Sell-rate trajectories" — add C8 row.
- "Cost comparison" — add C8 row. Update the "C7 is the cheapest" claim if C8 came in lower or higher.
- "Safety-relevant findings" — extend if C8 produced new safety findings (e.g., bad-swap miss like C7 P3 Rex).
- "What stayed constant across all 12 cells" → **15 cells**.
- "Methodology caveats" — add the tier-confound paragraph from spec §8.4.
- Closing italic paragraph — add one sentence summarising C8's role.

Keep the same plain-English voice the existing 4-config doc uses.

- [ ] **Step 4: Verify the rewrite**

```bash
wc -l results/paper_runs/CROSS_CONFIG_COMPARISON.md
grep -c "^## " results/paper_runs/CROSS_CONFIG_COMPARISON.md
grep -c "C8" results/paper_runs/CROSS_CONFIG_COMPARISON.md
grep -c "gemini-3.5\|gemini 3.5\|Gemini 3.5" results/paper_runs/CROSS_CONFIG_COMPARISON.md
```

Expected:
- Line count: 600-700 (currently 558; growth ~20% for the new column).
- Section count: roughly the same (no section deletions).
- "C8" appears in every table — at least 25 mentions.
- "Gemini 3.5" appears in the configuration list, claim #4, and the methodology caveats — at least 5 mentions.

- [ ] **Step 5: Internal consistency check**

For every number cited in narrative text, grep that number against the table it should come from:

```bash
.venv/bin/python <<'PY'
# Sanity: pick 5 numbers from each per-config COMPARISON, confirm they're in CROSS_CONFIG.
import re, pathlib
cross = pathlib.Path('results/paper_runs/CROSS_CONFIG_COMPARISON.md').read_text()
for c in ['C1_sonnet_vs_sonnet', 'C4_sonnet_vs_gemini', 'C6_opus_vs_gemini', 'C7_gemini_vs_gpt55', 'C8_gemini35_vs_gpt55']:
    per = pathlib.Path(f'results/paper_runs/{c}/COMPARISON.md').read_text()
    nums = re.findall(r'\b0\.\d{2,3}\b', per)[:8]
    missing = [n for n in nums if n not in cross]
    print(f'{c}: {len(nums)-len(missing)}/{len(nums)} numbers found in cross-config')
PY
```

Expected: most numbers from each per-config doc appear in the cross-config doc. A few misses are fine (the cross-config aggregates some metrics rather than copying every number).

---

## Task 15: Final pytest + commit + memory update

**Files:**
- Updated: `project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/...` (all new)
- Modified: `project_deal_approach_1/results/paper_runs/CROSS_CONFIG_COMPARISON.md`

- [ ] **Step 1: Run the full test suite**

```bash
cd project_deal_approach_1 && .venv/bin/pytest tests/ -q
```

Expected: all tests pass. If any test references the old 4-config list or specific cross-config numbers, update those tests to match the new state.

- [ ] **Step 2: Stage all C8 data + writeup files**

```bash
git add project_deal_approach_1/results/paper_runs/C8_gemini35_vs_gpt55/ \
        project_deal_approach_1/results/paper_runs/CROSS_CONFIG_COMPARISON.md \
        project_deal_approach_1/data/credit_log.jsonl
git status --short | head -40
```

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(c8): add Gemini 3.5 Flash vs GPT-5.5 config and rewrite cross-config doc

- 15 rollouts collected (5 personas × 3 phases) under focal_G35_vs_X
- Per-phase INSIGHTS.md + per-config COMPARISON.md matching C7 depth
- CROSS_CONFIG_COMPARISON.md rewritten from 4 → 5 configs
- Tier confound (Flash vs Pro) documented in methodology caveats

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Update auto-memory**

The memory file `MEMORY.md` indexes `paper_runs_plan.md`, which currently describes a 5-config plan that listed C2/C3/C5. The actual experiment now spans C1/C4/C6/C7/C8. Update the project memory to reflect what shipped:

Edit `/Users/ashi.jain/.claude/projects/-Users-ashi-jain-Documents-project-deal/memory/paper_runs_plan.md`:

Replace the "5 model configs" list and "output layout" block with the as-shipped state:

```markdown
**The 5 model configs (as shipped — differs from earlier plan):**
- C1 `focal_S_vs_S` — Sonnet 4.5 focal vs Sonnet 4.5 field (self-play baseline)
- C4 `focal_S_vs_G` — Sonnet 4.5 focal vs Gemini 3.1 Pro Preview field
- C6 `focal_O_vs_G` — Opus 4.7 focal vs Gemini 3.1 Pro Preview field
- C7 `focal_G_vs_X` — Gemini 3.1 Pro focal vs GPT-5.5 field
- C8 `focal_G35_vs_X` — Gemini 3.5 Flash focal vs GPT-5.5 field (added 2026-05-25)
```

This memory edit is its own act — do NOT commit it (memory lives outside the repo).

- [ ] **Step 5: Final report**

Print a one-screen summary for the user:

```bash
.venv/bin/python <<'PY'
import json
from pathlib import Path
print('=== C8 Complete ===')
for ph in (1, 2, 3):
    a = json.load(open(f'results/paper_runs/C8_gemini35_vs_gpt55/phase{ph}/aggregate.json'))
    print(f'  Phase {ph}: mean_reward={a["mean_reward"]:.3f}  rollouts={a["rollout_count"]}')
rows = [json.loads(l) for l in open('data/credit_log.jsonl')]
total = sum(r['spend'] for r in rows if r['config'] == 'focal_G35_vs_X')
print(f'  Total spend: ${total:.2f}')
print('Files:')
for p in sorted(Path('results/paper_runs/C8_gemini35_vs_gpt55').rglob('*.md')):
    print(f'  {p}')
print(f'  results/paper_runs/CROSS_CONFIG_COMPARISON.md (rewritten)')
PY
```

This closes out the C8 work end-to-end.

---

## Self-review notes

**Spec coverage check:**

| Spec section | Covered by |
|---|---|
| §4 C8 definition | Task 1-4 |
| §5.1 marketplace/config.py | Task 1 |
| §5.2 model_config.py | Task 2 |
| §5.3 run_paper_config_phase.sh | Task 3 |
| §5.4 task files | Task 4 |
| §6 pre-flight | Tasks 5, 6 |
| §7 run sequence | Tasks 7, 8, 9 |
| §8.1 INSIGHTS structure | Tasks 10, 11, 12 |
| §8.2 COMPARISON structure | Task 13 |
| §8.3 CROSS_CONFIG rewrite | Task 14 |
| §8.4 tier-confound caveat | Tasks 10-14 (all writeups) |
| §9 folder layout | Task 7-9 auto, Task 13 manual |
| §10 error handling | Inherits from existing script (Tasks 7-9), image fallback Task 9 step 1 |
| §11 testing & validation | Tasks 2 step 5, 15 step 1, per-task verification steps |

All spec sections map to at least one task. No placeholders. No undefined methods or types — all file paths are concrete and verified.
