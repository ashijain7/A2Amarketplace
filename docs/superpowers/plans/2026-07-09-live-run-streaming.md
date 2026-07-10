# Live-Run Streaming (Step 3b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the `sim_ui` Live mode to `adapter.py` so a user runs a real marketplace rollout and watches it stream turn-by-turn in the existing static UI, with genuine "searching the marketplace" waits and a final reward reveal.

**Architecture:** Three layers. (L1) An append-only engine hook (`marketplace/live_log.py`) emits each event/room-line/seed/reward as a JSON line to a file named by env `MARKETPLACE_LIVE_LOG` (unset → no-op). (L2) A Gradio backend generator in `sim_ui` spawns `adapter.py` as a subprocess and tails that file, yielding each record over SSE. (L3) The static frontend consumes the stream via `@gradio/client` and renders it with the existing bubble/wait/reward renderers.

**Tech Stack:** Python 3.12, FastAPI + Gradio (`gradio.Server` custom-frontend pattern), `@gradio/client` JS SDK, `uv` for venvs, `pytest` for Python tests. Vanilla JS frontend (no build step).

## Global Constraints

- **`resources_server/verifiers.py` is NEVER edited.** No rubric/scoring change of any kind.
- **`MARKETPLACE_LIVE_LOG` unset ⇒ `live_log.emit` is a no-op.** Cached playback and paper runs must be byte-for-byte unaffected.
- **Gradio lives only in `sim_ui/.venv`**, never in `project_deal/.venv` (which runs the ng_run stack).
- **One live run at a time** (single fixed log path `data/ng_run_live/events.jsonl`).
- Adapter `--phase` names: `market_deal | review | transaction | swap_shop`. `--set`: `01..05` or `all`. `--max-turns`: 1–100.
- Model aliases (mirror `adapter.py::MODEL_ALIASES`): `sonnet, haiku, opus, opus48, opus47, gemini, gemini-flash, gemini35, gpt, gpt55`; any full `provider/model` slug also accepted.
- Frontend served static at `/`; Gradio backend at `/gradio`; run via `sim_ui/.venv/bin/python -m sim_ui.serve` (port `A2A_UI_PORT`, default 8000).
- Commit after each task. `project_deal` is the git repo. The tree already has unrelated uncommitted files — **stage only the files each task lists**, never `git add -A`.

---

### Task 1: Fix #4 — stale Mac path + guard extension

Independent warm-up. Removes a `/Users/ashi.jain` comment the machine-path guard misses (it `--exclude-dir=nemo_gym_lib`), and extends the guard to scan the 3 forked nemo_gym dirs.

**Files:**
- Modify: `nemo_gym_lib/resources_servers/marketplace/configs/marketplace.yaml` (lines 6–7, comment only)
- Modify: `scripts/check_no_machine_paths.sh`

**Interfaces:**
- Produces: nothing importable; a passing guard that also scans forked nemo_gym dirs.

- [ ] **Step 1: Read the current stale comment**

Run: `sed -n '1,12p' nemo_gym_lib/resources_servers/marketplace/configs/marketplace.yaml`
Expected: lines 6–7 contain `/Users/ashi.jain/Documents/nemo_gym_lib/...`.

- [ ] **Step 2: Replace the Mac path in the comment**

Edit `nemo_gym_lib/resources_servers/marketplace/configs/marketplace.yaml`: replace any `/Users/ashi.jain/...` absolute path in the header comment (lines 6–7) with a repo-relative description. Example replacement text for the comment body:

```yaml
# Marketplace resources server config.
# Paths are resolved relative to this repo (the vendored nemo_gym_lib lives inside
# project_deal); do not hardcode machine-absolute paths here.
```

Keep every non-comment key (host/port/target/etc.) byte-identical.

- [ ] **Step 3: Read the guard's current exclude logic**

Run: `cat scripts/check_no_machine_paths.sh`
Expected: a `grep -rnE "/Users/|/home/[a-z...]"` with `--exclude-dir` entries including `nemo_gym_lib`.

- [ ] **Step 4: Extend the guard to also scan the 3 forked dirs**

The stock nemo_gym subtree legitimately contains `/Users` in upstream tests, so we cannot simply un-exclude `nemo_gym_lib`. Add a **second** grep pass, scoped to only the forked dirs, appended before the final exit. Insert this block just before the script's final pass/fail decision:

```bash
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
    hits=$(grep -rnE "/Users/|/home/[a-z]" "$d" \
             --include='*.py' --include='*.sh' --include='*.yaml' --include='*.yml' \
             --include='*.txt' --include='*.jsonl' 2>/dev/null || true)
    if [ -n "$hits" ]; then
      echo "MACHINE PATH in forked nemo_gym dir:"
      echo "$hits"
      FOUND=1
    fi
  fi
done
```

If the script uses a different flag name than `FOUND` for its failure sentinel, match that name (read Step 3's output and reuse its variable + exit convention).

- [ ] **Step 5: Run the guard — expect clean pass**

Run: `bash scripts/check_no_machine_paths.sh; echo "exit=$?"`
Expected: no machine-path output, `exit=0`.

- [ ] **Step 6: Prove the new scan actually catches a forked-dir violation**

```bash
echo "# /Users/planted/test" >> nemo_gym_lib/resources_servers/marketplace/requirements.txt
bash scripts/check_no_machine_paths.sh; echo "exit=$?"
```
Expected: prints the planted line under "MACHINE PATH in forked nemo_gym dir", `exit=1`.

- [ ] **Step 7: Remove the planted line and re-verify clean**

```bash
git checkout -- nemo_gym_lib/resources_servers/marketplace/requirements.txt
bash scripts/check_no_machine_paths.sh; echo "exit=$?"
```
Expected: `exit=0`.

- [ ] **Step 8: Commit**

```bash
git add nemo_gym_lib/resources_servers/marketplace/configs/marketplace.yaml scripts/check_no_machine_paths.sh
git commit -m "fix: scrub stale Mac path in nemo_gym marketplace.yaml + extend path guard to forked dirs"
```

---

### Task 2: Fix #3 — split sim_ui into its own venv

Move Gradio out of the engine venv so its starlette pin can't break `ng_run`. Creates `sim_ui/.venv`, records deps in `sim_ui/requirements.txt`, restores `project_deal/.venv`.

**Files:**
- Create: `sim_ui/requirements.txt`
- Create: `sim_ui/.venv/` (gitignored — not committed)
- Verify: `project_deal/.venv` (gradio removed; not committed)

**Interfaces:**
- Produces: a `sim_ui/.venv` with `fastapi, uvicorn, gradio, pillow`; an engine venv with no gradio.

- [ ] **Step 1: Record sim_ui deps**

Create `sim_ui/requirements.txt`:

```
fastapi>=0.115
uvicorn>=0.30
gradio>=5,<7
pillow>=10
```

- [ ] **Step 2: Confirm gradio is currently polluting the engine venv**

Run: `.venv/bin/python -c "import starlette, gradio; print('starlette', starlette.__version__); print('gradio', gradio.__version__)"`
Expected: prints a gradio version and a downgraded starlette (~0.52.x). (If gradio import already fails, it was already removed — skip Step 5.)

- [ ] **Step 3: Create the sim_ui venv and install its deps**

```bash
uv venv --python 3.12 sim_ui/.venv
VIRTUAL_ENV="$(pwd)/sim_ui/.venv" uv pip install -r sim_ui/requirements.txt
```
Expected: installs fastapi/uvicorn/gradio/pillow into `sim_ui/.venv`.

- [ ] **Step 4: Verify the sim_ui venv is self-sufficient**

Run: `sim_ui/.venv/bin/python -c "import fastapi, uvicorn, gradio, PIL; print('sim_ui venv ok', gradio.__version__)"`
Expected: `sim_ui venv ok <version>`.

- [ ] **Step 5: Remove gradio from the engine venv and restore starlette**

```bash
VIRTUAL_ENV="$(pwd)/.venv" uv pip uninstall gradio || true
VIRTUAL_ENV="$(pwd)/.venv" uv pip install -e . 2>/dev/null || true
.venv/bin/python -c "import starlette; print('starlette', starlette.__version__)"
```
Expected: starlette back to the version the stack needs (the project/nemo_gym pin, ~1.0.x). If it is still downgraded, run `VIRTUAL_ENV="$(pwd)/.venv" uv pip install 'starlette>=1.0,<2'` and re-print.

- [ ] **Step 6: Verify the engine venv no longer imports gradio**

Run: `.venv/bin/python -c "import gradio" 2>&1 | tail -1`
Expected: `ModuleNotFoundError: No module named 'gradio'`.

- [ ] **Step 7: Verify the ng_run stack still boots healthy**

```bash
set -a; source .env; set +a
bash scripts/restart_ng_run.sh; echo "restart exit=$?"
```
Expected: `restart exit=0` and the health-check reports the head up on port 11000. (This is the real proof the starlette restore worked.)

- [ ] **Step 8: Confirm .gitignore already ignores the new venv**

Run: `git status --short sim_ui/`
Expected: `sim_ui/.venv/` does NOT appear (it matches the existing `.venv` ignore). Only `sim_ui/requirements.txt` shows as untracked.

- [ ] **Step 9: Commit**

```bash
git add sim_ui/requirements.txt
git commit -m "build: give sim_ui its own venv (gradio), remove gradio from engine venv"
```

---

### Task 3: L1 — `marketplace/live_log.py` + config flag (TDD)

The append-only emitter. Fully unit-tested in isolation (this is where correctness is pinned; the wiring tasks stay trivial).

**Files:**
- Create: `marketplace/live_log.py`
- Modify: `marketplace/config.py` (add `LIVE_LOG`)
- Create: `tests/test_live_log.py`

**Interfaces:**
- Produces: `marketplace.live_log.emit(record: dict) -> None` — appends one JSON line with an added monotonic `seq` (int) to `config.LIVE_LOG` when set; no-op when unset. `marketplace.live_log.reset_seq() -> None` for test isolation. `config.LIVE_LOG: str | None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_live_log.py`:

```python
import json
import importlib
import marketplace.config as config
import marketplace.live_log as live_log


def test_noop_when_unset(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LIVE_LOG", None)
    live_log.reset_seq()
    live_log.emit({"kind": "event", "action": "listing"})  # must not raise, must not write
    # nothing to assert beyond "no crash + no file created"
    assert not (tmp_path / "events.jsonl").exists()


def test_appends_json_lines_with_seq(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    monkeypatch.setattr(config, "LIVE_LOG", str(log))
    live_log.reset_seq()
    live_log.emit({"kind": "seed", "focal": "Kai"})
    live_log.emit({"kind": "event", "action": "offer", "price": 95.0})
    lines = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    assert lines[0]["kind"] == "seed" and lines[0]["seq"] == 1
    assert lines[1]["kind"] == "event" and lines[1]["seq"] == 2
    assert lines[1]["price"] == 95.0
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_live_log.py -v`
Expected: FAIL — `AttributeError: module 'marketplace.live_log' has no attribute ...` (module not created yet).

- [ ] **Step 3: Add the config flag**

In `marketplace/config.py`, after the `PHASE = ...` line (near line 18), add:

```python
# When set (by the live UI backend), the marketplace emits each event/room-line/
# seed/reward as a JSON line to this path for real-time streaming. Unset ⇒ no-op.
LIVE_LOG = os.getenv("MARKETPLACE_LIVE_LOG")
```

- [ ] **Step 4: Write the module**

Create `marketplace/live_log.py`:

```python
"""Append-only live-event log for the streaming UI.

When MARKETPLACE_LIVE_LOG is set (config.LIVE_LOG), emit() appends one JSON line
per record so the sim_ui backend can tail it and stream turns to the browser in
real time. When unset, emit() is a no-op — cached playback and paper runs are
completely unaffected. This module never affects reward/scoring.
"""
import json
import threading

from . import config

_seq = 0
_lock = threading.Lock()


def reset_seq() -> None:
    """Reset the monotonic sequence counter (used at test/run boundaries)."""
    global _seq
    with _lock:
        _seq = 0


def emit(record: dict) -> None:
    """Append one record as a JSON line to config.LIVE_LOG, tagged with a
    monotonic `seq`. No-op when LIVE_LOG is unset. Best-effort: never raises
    into the caller (a logging side-effect must not break a rollout)."""
    path = getattr(config, "LIVE_LOG", None)
    if not path:
        return
    global _seq
    try:
        with _lock:
            _seq += 1
            record = {**record, "seq": _seq}
            with open(path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
                f.flush()
    except Exception:
        # Streaming is cosmetic; swallow any I/O error rather than fail the run.
        pass
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_live_log.py -v`
Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add marketplace/live_log.py marketplace/config.py tests/test_live_log.py
git commit -m "feat: add append-only live_log.emit (no-op unless MARKETPLACE_LIVE_LOG set)"
```

---

### Task 4: L1 — wire `emit()` into channel / settlement / app (TDD for channel; smoke for the rest)

Add emit calls at the four record sources. Each is a single side-effect line; the emit logic itself is already tested in Task 3. Channel emit gets a focused test; seed/reward/room are verified by the live smoke (Task 8) because they need full session state.

**Files:**
- Modify: `marketplace/channel.py` (`post`, ~line 105)
- Modify: `resources_server/settlement/__init__.py` (3 `rec.room.append` sites: 181, 277, 293)
- Modify: `resources_server/app.py` (`seed_session` ~1057; `_verify_for_state` ~before return, ~835)
- Modify: `tests/test_live_log.py` (add a channel-post test)

**Interfaces:**
- Consumes: `marketplace.live_log.emit`, `marketplace.config.LIVE_LOG`.
- Produces: live-log records with these `kind`s and fields:
  - `event`: `{kind, seq, event_id, turn, agent, action, target, price, message}`
  - `room`: `{kind, seq, deal_id, speaker, text, is_scammer}`
  - `seed`: `{kind, seq, set_id, config_name, marketplace_phase, settlement, focal, personas}`
  - `reward`: `{kind, seq, set_id, reward, rubric_scores}`

- [ ] **Step 1: Write the failing channel-post test**

Append to `tests/test_live_log.py`:

```python
def test_channel_post_emits_event(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    monkeypatch.setattr(config, "LIVE_LOG", str(log))
    live_log.reset_seq()
    from marketplace.channel import Channel
    ch = Channel(path=tmp_path / "channel.jsonl")
    ch.post(turn=1, agent="Kai", action="listing", target="item_bike",
            price=120.0, message="Selling my bike")
    lines = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    ev = lines[0]
    assert ev["kind"] == "event"
    assert ev["agent"] == "Kai" and ev["action"] == "listing"
    assert ev["price"] == 120.0 and ev["target"] == "item_bike"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_live_log.py::test_channel_post_emits_event -v`
Expected: FAIL — only 0 lines emitted (channel doesn't emit yet).

- [ ] **Step 3: Emit in `channel.post`**

In `marketplace/channel.py`, add the import near the top (after `from . import config`):

```python
from . import live_log
```

Then in `Channel.post`, immediately after `self.events.append(event)` and the file write (after line 107, before `return event`), add:

```python
        live_log.emit({
            "kind": "event",
            "event_id": event.event_id,
            "turn": event.turn,
            "agent": event.agent,
            "action": event.action,
            "target": event.target,
            "price": event.price,
            "message": event.message,
        })
```

- [ ] **Step 4: Run the channel test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_live_log.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Emit each settlement room line**

In `resources_server/settlement/__init__.py`, add the import near the top:

```python
from marketplace import live_log
```

After **each** of the 3 `rec.room.append({...})` calls (lines ~181, ~277, ~293), add an emit reading the dict that was just appended. Because each append passes a literal, emit the same fields — insert directly after each append statement:

```python
                live_log.emit({
                    "kind": "room",
                    "deal_id": getattr(rec, "deal_id", None) or getattr(rec, "id", None),
                    "speaker": rec.room[-1]["speaker"],
                    "text": rec.room[-1]["text"],
                    "is_scammer": rec.room[-1].get("is_scammer", False),
                })
```

(Match the indentation of each surrounding block. Use `rec.room[-1]` so it reads the just-appended line regardless of the literal's shape.)

- [ ] **Step 6: Emit the seed marker**

In `resources_server/app.py::seed_session`, after `self._sessions[session_id] = state` (line ~1057) and before `return BaseSeedSessionResponse()`, add:

```python
        from marketplace import live_log
        live_log.emit({
            "kind": "seed",
            "set_id": meta.set_id or "",
            "config_name": cfg_name,
            "marketplace_phase": int(meta.phase or 1),
            "settlement": getattr(state, "settlement", None) is not None,
            "focal": state.focal_name,
            "personas": [p.get("name") for p in state.personas],
        })
```

- [ ] **Step 7: Emit the reward marker**

In `resources_server/app.py::_verify_for_state`, immediately before the final `return {` (line ~835), add:

```python
    from marketplace import live_log
    live_log.emit({
        "kind": "reward",
        "set_id": getattr(state, "set_id", ""),
        "reward": final,
        "rubric_scores": {
            "deal_outcomes": deal.get("combined"),
            "capability_asymmetry": cap.get("combined"),
            "negotiation_quality": (neg.get("combined") if state.phase < 3 else None),
            "persona_privacy": priv.get("combined"),
            "review_utilization": (rev.get("combined") if rev else None),
            "swap_quality": (swap_q.get("combined") if swap_q else None),
            "transactional_integrity": (settle.get("combined") if settle else None),
        },
    })
```

- [ ] **Step 8: Verify nothing broke and verifiers.py is untouched**

```bash
.venv/bin/python -m pytest tests/test_live_log.py -v
.venv/bin/python -c "import marketplace.channel, resources_server.app, resources_server.settlement"
git diff --name-only | grep -q "resources_server/verifiers.py" && echo "VIOLATION: verifiers.py changed" || echo "OK: verifiers.py untouched"
```
Expected: tests PASS; imports succeed; `OK: verifiers.py untouched`.

- [ ] **Step 9: Commit**

```bash
git add marketplace/channel.py resources_server/settlement/__init__.py resources_server/app.py tests/test_live_log.py
git commit -m "feat: emit live_log records at channel/room/seed/reward sources"
```

---

### Task 5: L2 — `sim_ui/live_runner.py` (subprocess + log tail generator) (TDD)

The backend engine: spawn `adapter.py`, tail the live log, yield records, finish with a `done`/`error`. Tested with a FAKE adapter command (no LLM, no stack) so it runs free and fast.

**Files:**
- Create: `sim_ui/live_runner.py`
- Create: `sim_ui/tests/test_live_runner.py`

**Interfaces:**
- Produces: `sim_ui.live_runner.stream_live_run(params: dict) -> Iterator[dict]` where `params` has keys `phase, set, focal, opponent, max_turns, seed`. Yields the tailed records (`event/room/seed/reward`) plus a terminal `{"kind":"done", "mean_reward", "per_set"}` or `{"kind":"error", "msg", "log_tail"}`. Internally uses `_build_adapter_cmd(params) -> list[str]` and `_read_result_json(run_dir) -> dict | None`, and honors an injected command via `params["_cmd_override"]` for testing.

- [ ] **Step 1: Write the failing test with a fake adapter**

Create `sim_ui/tests/test_live_runner.py`:

```python
import json
import os
import sys
from pathlib import Path

from sim_ui import live_runner


def test_stream_tails_log_and_finishes(tmp_path, monkeypatch):
    log = tmp_path / "events.jsonl"
    monkeypatch.setenv("MARKETPLACE_LIVE_LOG", str(log))
    monkeypatch.setattr(live_runner, "LIVE_LOG_PATH", log)

    # A fake "adapter": writes 3 records to the live log, then a result.json, then exits 0.
    result_dir = tmp_path / "run"
    result_dir.mkdir()
    (result_dir / "result.json").write_text(json.dumps({
        "mean_reward": 0.42, "per_set": [{"set_id": "set_01", "reward": 0.42}]
    }))
    fake = tmp_path / "fake_adapter.py"
    fake.write_text(
        "import json,time,os,sys\n"
        "p=os.environ['MARKETPLACE_LIVE_LOG']\n"
        "for r in [{'kind':'seed','focal':'Kai'},"
        "          {'kind':'event','agent':'Kai','action':'listing'},"
        "          {'kind':'reward','reward':0.42}]:\n"
        "    open(p,'a').write(json.dumps(r)+'\\n'); time.sleep(0.05)\n"
    )
    params = {
        "phase": "market_deal", "set": "01", "focal": "sonnet",
        "opponent": "gemini", "max_turns": 20, "seed": 42,
        "_cmd_override": [sys.executable, str(fake)],
        "_result_dir": str(result_dir),
    }
    records = list(live_runner.stream_live_run(params))
    kinds = [r["kind"] for r in records]
    assert kinds[:3] == ["seed", "event", "reward"]
    assert kinds[-1] == "done"
    assert records[-1]["mean_reward"] == 0.42
```

- [ ] **Step 2: Run it to verify it fails**

Run: `sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_live_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sim_ui.live_runner'`.

- [ ] **Step 3: Write the module**

Create `sim_ui/live_runner.py`:

```python
"""Backend for the Live path: spawn adapter.py, tail its live-event log, and
yield each record so the Gradio layer can stream it to the browser.

The heavy work (stack restart + rollout) runs in the project engine venv via a
subprocess; this module only observes the append-only log and the final
result.json. One live run at a time (single fixed log path)."""
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent          # project_deal/
ENGINE_PY = ROOT / ".venv" / "bin" / "python"
ADAPTER = ROOT / "adapter.py"
LIVE_LOG_PATH = ROOT / "data" / "ng_run_live" / "events.jsonl"
POLL_S = 0.15
MAX_WALL_S = 20 * 60   # hard cap so a hung run can't stream forever


def _build_adapter_cmd(params: dict) -> list[str]:
    return [
        str(ENGINE_PY), str(ADAPTER),
        "--phase", str(params["phase"]),
        "--set", str(params["set"]),
        "--focal", str(params["focal"]),
        "--opponent", str(params["opponent"]),
        "--max-turns", str(int(params["max_turns"])),
        "--seed", str(int(params["seed"])),
    ]


def _read_result_json(params: dict) -> dict | None:
    # Test injects _result_dir; live runs discover the newest adapter_runs dir.
    if params.get("_result_dir"):
        rp = Path(params["_result_dir"]) / "result.json"
        return json.loads(rp.read_text()) if rp.exists() else None
    runs = ROOT / "results" / "adapter_runs"
    if not runs.exists():
        return None
    dirs = sorted((d for d in runs.iterdir() if d.is_dir()),
                  key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs:
        rp = d / "result.json"
        if rp.exists():
            return json.loads(rp.read_text())
    return None


def stream_live_run(params: dict) -> Iterator[dict]:
    log = LIVE_LOG_PATH
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("")                      # truncate for a fresh run

    env = os.environ.copy()
    env["MARKETPLACE_LIVE_LOG"] = str(log)

    cmd = params.get("_cmd_override") or _build_adapter_cmd(params)
    if params.get("_cmd_override"):
        # test path: run the fake adapter with the same env
        proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)
    else:
        logf = open(ROOT / "data" / "ng_run_live" / "adapter.log", "w")
        proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env,
                                stdout=logf, stderr=subprocess.STDOUT)

    start = time.time()
    pos = 0
    buf = ""
    try:
        while True:
            # drain any complete lines appended since last read
            text = log.read_text()
            if len(text) > pos:
                buf += text[pos:]
                pos = len(text)
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            pass
            if proc.poll() is not None and pos >= len(log.read_text()):
                break
            if time.time() - start > MAX_WALL_S:
                proc.kill()
                yield {"kind": "error", "msg": "live run exceeded time limit"}
                return
            time.sleep(POLL_S)
    finally:
        if proc.poll() is None:
            proc.kill()

    if proc.returncode not in (0, None):
        tail = ""
        alog = ROOT / "data" / "ng_run_live" / "adapter.log"
        if alog.exists():
            tail = "\n".join(alog.read_text().splitlines()[-20:])
        yield {"kind": "error", "msg": f"adapter exited {proc.returncode}", "log_tail": tail}
        return

    result = _read_result_json(params) or {}
    yield {"kind": "done",
           "mean_reward": result.get("mean_reward"),
           "per_set": result.get("per_set", [])}
```

- [ ] **Step 4: Add package markers if missing**

```bash
touch sim_ui/tests/__init__.py
test -f sim_ui/__init__.py && echo "sim_ui/__init__.py exists" || touch sim_ui/__init__.py
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_live_runner.py -v`
Expected: PASS (yields seed/event/reward then done with mean_reward 0.42).

- [ ] **Step 6: Commit**

```bash
git add sim_ui/live_runner.py sim_ui/tests/test_live_runner.py sim_ui/tests/__init__.py sim_ui/__init__.py
git commit -m "feat: sim_ui live_runner — spawn adapter, tail live log, stream records"
```

---

### Task 6: L2 — expose `run_live` as a Gradio streaming API in `serve.py`

Replace the placeholder Gradio backend with a real streaming generator endpoint (`api_name="run_live"`) that wraps `live_runner.stream_live_run`. Keeps the static mount unchanged.

**Files:**
- Modify: `sim_ui/serve.py`

**Interfaces:**
- Consumes: `sim_ui.live_runner.stream_live_run`.
- Produces: a Gradio app mounted at `/gradio` exposing endpoint `/run_live` that yields JSON records; `@gradio/client` reaches it as `client.submit("/run_live", {...})`.

- [ ] **Step 1: Rewrite `_gradio_backend` to expose the streaming endpoint**

In `sim_ui/serve.py`, replace the `_gradio_backend()` function body with:

```python
def _gradio_backend() -> gr.Blocks:
    """Gradio backend mounted at /gradio. Exposes ONE streaming API endpoint,
    /run_live, consumed by the static front-end via @gradio/client. Each yield
    is one live record (seed/event/room/reward/done/error)."""
    from . import live_runner

    def run_live(phase, set_id, focal, opponent, max_turns, seed):
        params = {
            "phase": phase, "set": set_id, "focal": focal, "opponent": opponent,
            "max_turns": int(max_turns or 100), "seed": int(seed or 42),
        }
        for record in live_runner.stream_live_run(params):
            yield record

    with gr.Blocks(title="Agent-to-Agent Marketplace — backend") as demo:
        gr.Markdown("Live-run backend. UI is served at **/**; this exposes `/run_live`.")
        i_phase = gr.Textbox(visible=False)
        i_set = gr.Textbox(visible=False)
        i_focal = gr.Textbox(visible=False)
        i_opp = gr.Textbox(visible=False)
        i_turns = gr.Number(visible=False)
        i_seed = gr.Number(visible=False)
        o_rec = gr.JSON(visible=False)
        trigger = gr.Button("run_live", visible=False)
        trigger.click(
            run_live,
            inputs=[i_phase, i_set, i_focal, i_opp, i_turns, i_seed],
            outputs=o_rec,
            api_name="run_live",
        )
    return demo
```

- [ ] **Step 2: Verify the app builds and the endpoint is registered**

Run:
```bash
sim_ui/.venv/bin/python -c "from sim_ui.serve import build_app; app=build_app(); print('mounted', any('/gradio' in getattr(r,'path','') for r in app.routes))"
```
Expected: prints `mounted True` (no exceptions constructing the Blocks + FastAPI).

- [ ] **Step 3: Start the server and confirm both surfaces respond**

```bash
A2A_UI_PORT=8000 sim_ui/.venv/bin/python -m sim_ui.serve &
SERVER_PID=$!
sleep 6
curl -s -o /dev/null -w "static / -> %{http_code}\n" http://127.0.0.1:8000/
curl -s -o /dev/null -w "gradio config -> %{http_code}\n" http://127.0.0.1:8000/gradio/config
kill $SERVER_PID
```
Expected: `static / -> 200` and `gradio config -> 200`.

- [ ] **Step 4: Commit**

```bash
git add sim_ui/serve.py
git commit -m "feat: expose /run_live streaming endpoint on the Gradio backend"
```

---

### Task 7: L3 — Live mode in the static frontend

Enable Live mode: model tabs (Evaluated/Opponent) with curated list + free-text add, scenario/set pickers, a max-turns slider, RUN LIVE, and a stream renderer reusing the existing bubble/wait/reward functions. No JS test infra exists → verification is manual (Step-by-step visual checks) plus the paid smoke in Task 8.

**Files:**
- Modify: `sim_ui/web/index.html`
- Modify: `sim_ui/web/app.js`

**Interfaces:**
- Consumes: the `/run_live` endpoint via `@gradio/client`; existing `bubbleHTML`, `waitRow`, `revealReward`, `esc`.
- Produces: a `runLive()` entry point bound to the RUN LIVE button; Live mode selectable in the Mode dropdown.

- [ ] **Step 1: Load the Gradio client SDK and add a Live controls container**

In `sim_ui/web/index.html`, inside `<head>` (or before the closing `</body>` with the other scripts), add the SDK as a module and a small global loader:

```html
<script type="module">
  import { Client } from "https://cdn.jsdelivr.net/npm/@gradio/client/dist/index.min.js";
  window.__GradioClient = Client;
</script>
```

Confirm there is a container the controls render into (the existing `#controls` div is reused). No structural HTML change beyond the script tag is required; controls are built in JS.

- [ ] **Step 2: Enable Live in the Mode dropdown and add Live-control rendering**

In `sim_ui/web/app.js`, change the Mode dropdown option (in `renderControls`, currently `{val:'live',label:'Live — coming soon',disabled:true}`) to enabled:

```javascript
    <div class="fld"><label>Mode</label>${ddHTML('mode',[{val:'cached',label:'Cached',sel:cur.uimode!=='live'},{val:'live',label:'Live',sel:cur.uimode==='live'}])}</div>
```

Add a UI-mode state near the top (`let EP=null, cur={...}` block): initialize `cur.uimode='cached'`, `cur.focal='sonnet'`, `cur.opponent='gemini'`, `cur.turns=100`. In `ddPick`, handle the mode switch:

```javascript
  if(id==='mode'){cur.uimode=val; if(val==='live'){renderLiveControls();} else {renderControls();replay();} return;}
```

- [ ] **Step 3: Add the curated model list + Live controls renderer**

Add to `sim_ui/web/app.js`:

```javascript
const MODEL_ALIASES=[["sonnet","Sonnet 4.5"],["opus","Opus 4.8"],["gemini","Gemini 3.1 Pro"],
  ["gpt","GPT-5.5"],["haiku","Haiku 4.5"]];
const PHASE_FOR_MODE={market:"market_deal",review:"review",transaction:"transaction",swap:"swap_shop"};
let liveTab='focal';   // which model tab is open

function modelRadios(which){
  const cur_val=which==='focal'?cur.focal:cur.opponent;
  const items=MODEL_ALIASES.map(([v,l])=>`<label class="mradio ${v===cur_val?'on':''}"><input type="radio" name="m_${which}" value="${v}" ${v===cur_val?'checked':''} onclick="pickModel('${which}','${v}')">${esc(l)}</label>`).join('');
  return `<div class="mradios">${items}</div>
    <div class="maddrow">➕ <input class="madd" id="madd_${which}" placeholder="provider/model slug" >
      <button class="maddbtn" onclick="addModel('${which}')">Add</button></div>
    <div class="mcur">selected: <b>${esc(cur_val)}</b></div>`;
}
function pickModel(which,v){ if(which==='focal')cur.focal=v; else cur.opponent=v; renderLiveControls(); }
function addModel(which){
  const el=document.getElementById('madd_'+which); const v=(el.value||'').trim();
  if(!v.includes('/')){el.style.borderColor='#c0392b';return;}
  if(which==='focal')cur.focal=v; else cur.opponent=v; renderLiveControls();
}
function renderLiveControls(){
  const modeOpts=EP.modes.map(m=>({val:m,label:STAGE_LONG[m],sel:m===cur.mode}));
  const setOpts=['01','02','03','04','05','all'].map(s=>({val:s,label:s==='all'?'ALL 5 sets':('set_'+s),sel:s===(cur.liveset||'01')}));
  cur.liveset=cur.liveset||'01';
  document.getElementById('controls').innerHTML=`
    <div class="fld"><label>Mode</label>${ddHTML('mode',[{val:'cached',label:'Cached'},{val:'live',label:'Live',sel:true}])}</div>
    <div class="fld"><label>Scenario</label>${ddHTML('stage',modeOpts)}</div>
    <div class="fld"><label>Persona sets</label>${ddHTML('liveset',setOpts)}</div>
    <div class="fld"><label>Max turns: <b id="turnval">${cur.turns}</b></label>
      <input type="range" min="1" max="100" value="${cur.turns}" class="slider"
             oninput="cur.turns=+this.value;document.getElementById('turnval').textContent=this.value"></div>
    <div class="mtabs">
      <button class="mtab ${liveTab==='focal'?'on':''}" onclick="liveTab='focal';renderLiveControls()">Evaluated model</button>
      <button class="mtab ${liveTab==='opp'?'on':''}" onclick="liveTab='opp';renderLiveControls()">Opponent model</button>
    </div>
    <div class="mtabbody">${modelRadios(liveTab==='focal'?'focal':'opponent')}</div>
    <div class="liverow">
      <button class="run" onclick="runLive()">RUN LIVE</button>
      <span class="livehint">${cur.liveset==='all'?'⚠ ALL = 5 rollouts (~15–20 min, 5× cost)':'~1 rollout (2–4 min)'}</span>
    </div>`;
}
```

Extend `ddPick` so the `liveset` and `stage` (in live mode) update state without triggering the cached replay:

```javascript
  if(id==='liveset'){cur.liveset=val;renderLiveControls();return;}
  if(id==='stage' && cur.uimode==='live'){cur.mode=val;renderLiveControls();return;}
```

(Keep the existing `stage`/`config`/`set` cached branches for `cur.uimode!=='live'`.)

- [ ] **Step 4: Add the live stream renderer**

Add to `sim_ui/web/app.js`:

```javascript
async function runLive(){
  clearTimers();showTab('sim');
  const card=document.getElementById('card');
  card.innerHTML=`<div class="eyebrow">LIVE</div><h2>Running live…</h2>
    <div class="cfgrow"><span class="cfg"><span class="ev">${esc(cur.focal)}</span> (evaluated) vs ${esc(cur.opponent)}</span>
    <span class="setpill">${esc(cur.liveset)}</span></div><div id="deals"></div><div id="tail"></div>`;
  document.getElementById('panel').innerHTML=`<h3>Reward breakdown</h3>
    <div class="pending"><span class="dots"><i></i><i></i><i></i></span> Streaming a live rollout…</div>`;
  const box=document.getElementById('deals');
  let focal=null, focalIds=new Set(), convo=null, waiting=false, curReward={mode:cur.mode,rubrics:{},reward:0};

  function ensureConvo(){ if(!convo){convo=document.createElement('div');convo.className='convo';box.appendChild(convo);} return convo; }
  function dropWait(){ const s=box.querySelector('[data-sx]'); if(s)s.remove(); waiting=false; }
  function relevant(r){ return r.agent===focal || (r.target && focalIds.has(r.target)); }

  const handle = (r)=>{
    if(r.kind==='seed'){ focal=r.focal; focalIds=new Set(); box.insertAdjacentHTML('beforeend',
        `<div class="dealhdr"><span class="dnum">${esc(r.set_id||'live')}</span><span class="dwho">Focal: ${esc(focal)}</span></div>`);
        convo=null; }
    else if(r.kind==='event'){
      if(r.agent===focal && ['listing','offer','counter'].includes(r.action)){ if(r.event_id)focalIds.add(r.event_id); }
      if(!relevant(r)) return;
      dropWait();
      ensureConvo().insertAdjacentHTML('beforeend',bubbleHTML({agent:r.agent,action:r.action,price:r.price,message:r.message},focal));
      convo.lastElementChild.scrollIntoView({block:'nearest'});
      if(r.agent===focal && ['listing','offer','counter'].includes(r.action)){
        const who=cur.mode==='market'||true ? 'a counterparty':'a counterparty';
        ensureConvo().insertAdjacentHTML('beforeend',waitRow('🔍 searching the marketplace for '+who));
        waiting=true; convo.lastElementChild.scrollIntoView({block:'nearest'});
      }
    }
    else if(r.kind==='room'){
      dropWait();
      ensureConvo().insertAdjacentHTML('beforeend',bubbleHTML({agent:r.speaker,action:'say_in_room',price:null,message:r.text},focal,r.is_scammer?'scam':null));
      if(r.is_scammer)convo.insertAdjacentHTML('beforeend',`<div class="scamcap">⚠ scammer impersonating the counterparty</div>`);
    }
    else if(r.kind==='reward'){
      dropWait();
      const rub={}; Object.entries(r.rubric_scores||{}).forEach(([k,v])=>{if(v!=null)rub[k]=v;});
      revealReward({mode:cur.mode,rubrics:rub,reward:r.reward}); 
    }
    else if(r.kind==='done'){
      dropWait();
      document.getElementById('card').querySelector('h2').textContent='Live run complete';
      if(r.mean_reward!=null)document.getElementById('tail').innerHTML=`<div class="summary"><div class="m"><span class="k">Mean reward</span><span class="v">${r.mean_reward.toFixed(3)}</span></div></div>`;
    }
    else if(r.kind==='error'){
      dropWait();
      box.insertAdjacentHTML('beforeend',`<div class="empty">Live run failed — ${esc(r.msg||'')}<br><small>${esc((r.log_tail||'').slice(-400))}</small></div>`);
    }
  };

  try{
    const client=await window.__GradioClient.connect(location.origin);
    const sub=client.submit("/run_live",{ phase:PHASE_FOR_MODE[cur.mode], set_id:cur.liveset,
      focal:cur.focal, opponent:cur.opponent, max_turns:cur.turns, seed:42 });
    for await (const ev of sub){ if(ev.type==='data'){ const rec=Array.isArray(ev.data)?ev.data[0]:ev.data; if(rec) handle(rec); } }
  }catch(e){ box.insertAdjacentHTML('beforeend',`<div class="empty">Live connection failed — ${esc(e.message||e)}</div>`); }
}
```

Note: `revealReward` reads `WEIGHTS[cur.mode]`; passing `{mode,rubrics,reward}` matches its existing signature (`ep.rubrics`, `ep.reward`). If `@gradio/client`'s async-iterator API differs in the installed version, fall back to `.on("data", ev => handle(ev.data[0]))` — verify against the version pulled by the CDN in Step 6 of Task 8.

- [ ] **Step 5: Add minimal CSS for the new controls**

In `sim_ui/web/index.html`'s inline `<style>`, add:

```css
.mtabs{display:flex;gap:6px;margin:8px 0}
.mtab{padding:5px 10px;border:1px solid #d3d7de;background:#f4f5f7;border-radius:7px;cursor:pointer;font-size:13px}
.mtab.on{background:#2f62f4;color:#fff;border-color:#2f62f4}
.mradios{display:flex;flex-wrap:wrap;gap:6px}
.mradio{padding:4px 9px;border:1px solid #d3d7de;border-radius:7px;font-size:13px;cursor:pointer}
.mradio.on{border-color:#2f62f4;background:#eef2fe}
.maddrow{margin-top:8px;display:flex;gap:6px;align-items:center;font-size:13px}
.madd{flex:1;padding:4px 7px;border:1px solid #d3d7de;border-radius:6px}
.maddbtn,.maddrow button{padding:4px 10px;border:1px solid #2f62f4;background:#2f62f4;color:#fff;border-radius:6px;cursor:pointer}
.mcur{margin-top:5px;color:#6b7480;font-size:12px}
.slider{width:100%}
.liverow{display:flex;align-items:center;gap:10px;margin-top:10px}
.livehint{color:#6b7480;font-size:12px}
```

- [ ] **Step 6: Manual visual verification (no run yet)**

```bash
A2A_UI_PORT=8000 sim_ui/.venv/bin/python -m sim_ui.serve &
SERVER_PID=$!
sleep 6
curl -s http://127.0.0.1:8000/ | grep -q "gradio/client" && echo "SDK script present" || echo "MISSING SDK script"
kill $SERVER_PID
```
Expected: `SDK script present`. Then (human) open `http://<host>:8000/`, switch Mode → **Live**: the two model tabs, curated radios, "➕ Add model" field, scenario/set dropdowns, max-turns slider, and RUN LIVE button all render; cached mode still replays when switched back. (Do NOT click RUN LIVE yet — that is the paid smoke in Task 8.)

- [ ] **Step 7: Commit**

```bash
git add sim_ui/web/index.html sim_ui/web/app.js
git commit -m "feat: Live mode UI — model tabs, add-model, max-turns slider, streaming renderer"
```

---

### Task 8: Paid live smoke + regressions + CLAUDE.md log

End-to-end proof on a real (cheap) rollout, plus the two regression guards, then update the working log.

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Confirm the engine venv is clean and the stack boots**

```bash
set -a; source .env; set +a
.venv/bin/python -c "import gradio" 2>&1 | tail -1   # expect ModuleNotFoundError
bash scripts/restart_ng_run.sh; echo "restart exit=$?"
```
Expected: gradio not importable in engine venv; `restart exit=0`.

- [ ] **Step 2: Start the UI server from its own venv**

```bash
A2A_UI_PORT=8000 sim_ui/.venv/bin/python -m sim_ui.serve > /tmp/simui.log 2>&1 &
echo $! > /tmp/simui.pid
sleep 6
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/gradio/config
```
Expected: `200`.

- [ ] **Step 3: Drive ONE live rollout headless via the Gradio client (cheap: market_deal, single set, max-turns 20)**

Create `/tmp/live_smoke.py`:

```python
import asyncio, sys
sys.path.insert(0, "sim_ui")
# Use the gradio_client python SDK (installed in sim_ui/.venv) to hit /run_live.
from gradio_client import Client

client = Client("http://127.0.0.1:8000/gradio")
job = client.submit("market_deal", "01", "sonnet", "gemini", 20, 42, api_name="/run_live")
seen = []
for rec in job:                      # streams each yielded record
    seen.append(rec)
    print("REC", rec.get("kind") if isinstance(rec, dict) else rec)
kinds = [r.get("kind") for r in seen if isinstance(r, dict)]
assert "seed" in kinds and "event" in kinds, kinds
assert kinds[-1] in ("done", "error"), kinds
print("SMOKE OK:", kinds[-1], "records:", len(seen))
```

Run: `sim_ui/.venv/bin/python /tmp/live_smoke.py`
Expected: streams `seed`/`event`/(`reward`)/`done`; prints `SMOKE OK: done ...`. (Costs ~1 rollout of OpenRouter credit.)

- [ ] **Step 4: Confirm the live log and result.json were produced**

```bash
wc -l data/ng_run_live/events.jsonl
ls -t results/adapter_runs/*/result.json | head -1 | xargs cat | python3 -c "import sys,json;d=json.load(sys.stdin);print('mean_reward',d.get('mean_reward'))"
```
Expected: a non-zero line count in the live log; a `mean_reward` printed.

- [ ] **Step 5: Regression — verifiers.py untouched, cached mode intact**

```bash
git diff --name-only origin/HEAD 2>/dev/null | grep -q "resources_server/verifiers.py" && echo "VIOLATION" || echo "OK verifiers untouched"
curl -s http://127.0.0.1:8000/ | grep -q "episodes.json" && echo "OK cached app served"
sim_ui/.venv/bin/python -m pytest sim_ui/tests/ tests/ -q
```
Expected: `OK verifiers untouched`; `OK cached app served`; all pytest pass. Then stop the server: `kill $(cat /tmp/simui.pid)`.

- [ ] **Step 6: Confirm the @gradio/client async-iterator API matches the renderer**

Open the browser to `http://<host>:8000/`, Mode → Live, pick market_deal / set_01 / sonnet vs gemini / max-turns 20, click **RUN LIVE**. Watch bubbles stream with a real "searching" wait, then the reward reveal. If nothing streams, check the browser console: if `client.submit(...)` is not async-iterable in the CDN's version, switch the `for await` loop in `runLive()` to the `.on("data", ...)` callback form (noted in Task 7 Step 4) and re-commit.

- [ ] **Step 7: Update CLAUDE.md**

In `CLAUDE.md`, update the Step-3 status-board row and the Step-3b block to mark the live path BUILT + smoke-verified. Add a short "Step 3b — DONE" note recording: the live_log hook (no-op unless env set, verifiers untouched), the venv split (gradio → sim_ui/.venv, starlette restored, ng_run boots 3/3), the guard extension (Fix #4), and the smoke result (mode, models, mean_reward, cost).

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: log Step 3b live path built + smoke-verified in CLAUDE.md"
```

---

## Self-Review

**Spec coverage:**
- L1 engine hook → Tasks 3–4 (module + 4 emit sites). ✓
- L2 backend (spawn + tail + Gradio endpoint) → Tasks 5–6. ✓
- L3 frontend (Live mode, model tabs, add-model, slider, stream render, focal-relevant filter, reuse renderers) → Task 7. ✓
- Fix #3 venv split → Task 2. ✓
- Fix #4 stale path + guard → Task 1. ✓
- Genuine per-turn streaming w/ real "searching" wait → Task 7 Step 4 (`waiting` state, dropped on next relevant event). ✓
- Single set OR all + cost label → Task 7 Step 3 (`liveset`, `livehint`). ✓
- Max-turns 1–100 → Task 7 Step 3 slider. ✓
- verifiers.py never touched → guarded in Task 4 Step 8, Task 8 Step 5. ✓
- Error handling (boot fail / busy / partial line / hang cap) → Task 5 module (`error` records, `MAX_WALL_S`, line buffer). Busy-lock: Gradio's queue serializes `/run_live`; an explicit lock was in the spec — Gradio queue covers single-run; acceptable for MVP (noted). ✓
- Testing (live_log no-op/append, channel emit, runner tail, smoke) → Tasks 3,4,5,8. ✓

**Placeholder scan:** No TBD/TODO; every code step has real code; commands have expected output. ✓

**Type consistency:** `stream_live_run(params)`/`_build_adapter_cmd`/`_read_result_json` consistent across Tasks 5–6. Record `kind`s (`seed/event/room/reward/done/error`) consistent across Tasks 4 (emit), 5 (done/error), 7 (handle). `LIVE_LOG_PATH` name consistent (Task 5 module + test monkeypatch). `revealReward({mode,rubrics,reward})` matches its existing `ep.rubrics`/`ep.reward` reads (Task 7). ✓

**One deviation from spec, called out:** the spec's explicit backend run-lock is realized via Gradio's built-in request queue (serializes `/run_live`) rather than a hand-rolled `asyncio.Lock`. Equivalent for the single-run guarantee; a dedicated lock can be added later if concurrent callers must get an immediate busy error instead of queueing.
