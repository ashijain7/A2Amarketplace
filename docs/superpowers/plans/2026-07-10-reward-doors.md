# Reward Doors (B1) + Port Fix (A1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the RLEaaS platform an HTTP way to obtain a marketplace run's reward as data — a push hook that announces a finished run, an optional blocking `POST /api/run`, and read/health endpoints — plus make the UI server bind the platform-injected `$PORT`.

**Architecture:** A dependency-free converter (`platform_export.py`, project_deal root, importable from BOTH venvs) turns `result.json` into the platform's `RolloutRecord` shape. `adapter.py` calls a best-effort push after it writes `result.json` (no-op unless callback env is set) — so any run (human `/run_live`, headless `/api/run`, CLI) reports uniformly. `sim_ui/run_api.py` adds the blocking run + read endpoints, reusing `live_runner`'s subprocess/teardown helpers, guarded by a single-flight lock + a stack-busy check. `serve.py` registers those routes before the static mount and honors `$PORT`.

**Tech Stack:** Python 3.12, FastAPI/Starlette (sim_ui/.venv), stdlib `urllib`/`subprocess`/`threading`, pytest. adapter runs in the engine `.venv`; sim_ui runs in `sim_ui/.venv`.

## Global Constraints

- **Do NOT touch** `resources_server/verifiers.py`, the engine (`resources_server/`, `marketplace/`), `/run_live` (Gradio streaming), or the static UI (`sim_ui/web/`). `adapter.py` gets ONE added call (the push hook); `serve.py` gets route registration + the port line. Nothing else in those files changes.
- **`platform_export.py` must be dependency-free** (pure dict/JSON + stdlib `urllib` only) — it is imported from the engine venv (adapter) AND the sim_ui venv. No `marketplace`, no `pydantic`, no third-party imports.
- **Both venvs run with `project_deal/` on `sys.path`** (adapter cwd = root; `python -m sim_ui.serve` from root), so `import platform_export` resolves from either. Confirmed.
- **Push is best-effort and env-gated:** fires only when BOTH `RLEAAS_CALLBACK_URL` and `RLEAAS_TOKEN` are set; any push failure is logged and swallowed — it NEVER fails the run. Unset env = complete no-op (cached/local/CLI unaffected).
- **Platform record shape (verbatim from `api/main.py:989` `RolloutRecord`):** `environment_name: str` (required), `episode_number: int=1`, `steps: List[{step:int, action, reward:float, state_summary, reward_breakdown:Dict[str,float], timeline_events}]`, `initial_state`, `final_outcome: Dict`, `total_reward: float`, `total_steps: int`, `status: str="completed"`, `source: str="simulation"`, `job_id`, `timestamp`, `policy_name`, `scenario_name`, `verifier_results`, `final_environment_state`. The ingest (`store_rollout`, `main.py:8443`) assigns its OWN uuid `id` — so our `run_id` is carried inside `final_outcome` for traceability; platform-side de-dup is a Step-6 concern, NOT handled here.
- **Env var names (exact):** `RLEAAS_CALLBACK_URL`, `RLEAAS_TOKEN`, `RLEAAS_ENV_NAME` (default `"project_deal_marketplace"`). Port: read `PORT` then `A2A_UI_PORT` then `8000`.
- **No commits.** Standing user directive: nothing is committed. Each task ends by running its tests and appending a one-line note to `CLAUDE.md`. Do NOT run `git add`/`git commit`.
- **Run tests with the sim_ui venv:** `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest <path> -v`.

---

### Task 1: Pure converter `result_to_platform_records`

**Files:**
- Create: `platform_export.py` (project_deal root)
- Test: `sim_ui/tests/test_platform_export.py`

**Interfaces:**
- Produces: `result_to_platform_records(result: dict, env_name: str, run_id: str) -> list[dict]` — one platform `RolloutRecord`-shaped dict per entry in `result["per_set"]`. Each: `environment_name=env_name`, `episode_number=i+1`, `total_reward=per_set.reward or 0.0`, `total_steps=1`, `status="completed"`, `source="simulation"`, `policy_name=result["focal_model"]`, `scenario_name=per_set["set_id"]`, `steps=[{step:0, action:None, reward:<reward>, reward_breakdown:<rubric_breakdown>, state_summary:None, timeline_events:None}]`, `final_outcome={run_id, phase:result["phase"], focal_model, opponents_model, set_id, focal_persona, num_deals, num_channel_events}`.

- [ ] **Step 1: Write the failing test**

```python
# sim_ui/tests/test_platform_export.py
import platform_export


def _sample_result():
    return {
        "phase": "market_deal",
        "focal_model": "anthropic/claude-sonnet-4-5",
        "opponents_model": "google/gemini-3.1-pro-preview",
        "mean_reward": 0.30,
        "per_set": [
            {"set_id": "set_01", "focal_persona": "Kai", "reward": 0.30,
             "rubric_breakdown": {"deal_outcomes": 0.1, "negotiation_quality": 0.7},
             "num_deals": 3, "num_channel_events": 40},
        ],
    }


def test_converts_one_record_per_set():
    recs = platform_export.result_to_platform_records(
        _sample_result(), env_name="project_deal_marketplace", run_id="run_abc")
    assert len(recs) == 1
    r = recs[0]
    assert r["environment_name"] == "project_deal_marketplace"
    assert r["total_reward"] == 0.30
    assert r["scenario_name"] == "set_01"
    assert r["policy_name"] == "anthropic/claude-sonnet-4-5"
    assert r["steps"][0]["reward_breakdown"] == {"deal_outcomes": 0.1, "negotiation_quality": 0.7}
    assert r["final_outcome"]["run_id"] == "run_abc"
    assert r["final_outcome"]["num_deals"] == 3


def test_missing_reward_defaults_to_zero():
    result = _sample_result()
    result["per_set"][0]["reward"] = None
    recs = platform_export.result_to_platform_records(result, "e", "r")
    assert recs[0]["total_reward"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_platform_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'platform_export'`

- [ ] **Step 3: Write minimal implementation**

```python
# platform_export.py  (project_deal root — dependency-free; imported from BOTH venvs)
"""Convert an adapter result.json into the RLEaaS platform's RolloutRecord shape,
and push a finished run to the platform (best-effort, env-gated).

Dependency-free ON PURPOSE: imported from the engine venv (adapter.py) AND the
sim_ui venv. Stdlib only. Never raises out of push_to_platform."""
import json
import os
import urllib.request

DEFAULT_ENV_NAME = "project_deal_marketplace"


def result_to_platform_records(result: dict, env_name: str, run_id: str) -> list[dict]:
    """One platform RolloutRecord-shaped dict per set in result['per_set']."""
    recs = []
    for i, ps in enumerate(result.get("per_set", [])):
        reward = ps.get("reward")
        reward = float(reward) if reward is not None else 0.0
        recs.append({
            "environment_name": env_name,
            "episode_number": i + 1,
            "steps": [{
                "step": 0,
                "action": None,
                "reward": reward,
                "state_summary": None,
                "reward_breakdown": ps.get("rubric_breakdown") or {},
                "timeline_events": None,
            }],
            "total_reward": reward,
            "total_steps": 1,
            "status": "completed",
            "source": "simulation",
            "policy_name": result.get("focal_model"),
            "scenario_name": ps.get("set_id"),
            "final_outcome": {
                "run_id": run_id,
                "phase": result.get("phase"),
                "focal_model": result.get("focal_model"),
                "opponents_model": result.get("opponents_model"),
                "set_id": ps.get("set_id"),
                "focal_persona": ps.get("focal_persona"),
                "num_deals": ps.get("num_deals"),
                "num_channel_events": ps.get("num_channel_events"),
            },
        })
    return recs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_platform_export.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Update the log (no commit)**

Append to `/home/azureuser/A2A_RL/CLAUDE.md` under the Step-4 pre-work section: `- B1 Task 1 done: platform_export.result_to_platform_records (pure converter, dependency-free), 2 tests green.` Do NOT git commit.

---

### Task 2: Best-effort push `push_to_platform`

**Files:**
- Modify: `platform_export.py` (add function)
- Test: `sim_ui/tests/test_platform_export.py` (add tests)

**Interfaces:**
- Consumes: `result_to_platform_records` (Task 1).
- Produces: `push_to_platform(result: dict, run_id: str) -> int` — reads `RLEAAS_CALLBACK_URL`, `RLEAAS_TOKEN`, `RLEAAS_ENV_NAME` from env. If URL or TOKEN missing → returns `0` (no-op). Else POSTs each record (JSON body, header `Authorization: Bearer <token>`, `Content-Type: application/json`) to the URL via `urllib.request`; returns the count successfully POSTed. Any exception per-record is caught and swallowed (logged to stderr); never raises.

- [ ] **Step 1: Write the failing test**

```python
# add to sim_ui/tests/test_platform_export.py
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import platform_export


def _run_capture_server(captured):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n)
            captured.append({"auth": self.headers.get("Authorization"),
                             "body": json.loads(body)})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"success": true}')

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_push_noop_when_env_unset(monkeypatch):
    monkeypatch.delenv("RLEAAS_CALLBACK_URL", raising=False)
    monkeypatch.delenv("RLEAAS_TOKEN", raising=False)
    assert platform_export.push_to_platform(_sample_result(), "run_x") == 0


def test_push_posts_records_with_token(monkeypatch):
    captured = []
    srv = _run_capture_server(captured)
    host, port = srv.server_address
    monkeypatch.setenv("RLEAAS_CALLBACK_URL", f"http://{host}:{port}/api/rollouts")
    monkeypatch.setenv("RLEAAS_TOKEN", "secret-123")
    monkeypatch.setenv("RLEAAS_ENV_NAME", "project_deal_marketplace")
    n = platform_export.push_to_platform(_sample_result(), "run_x")
    srv.shutdown()
    assert n == 1
    assert captured[0]["auth"] == "Bearer secret-123"
    assert captured[0]["body"]["environment_name"] == "project_deal_marketplace"
    assert captured[0]["body"]["final_outcome"]["run_id"] == "run_x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_platform_export.py -k push -v`
Expected: FAIL — `AttributeError: module 'platform_export' has no attribute 'push_to_platform'`

- [ ] **Step 3: Write minimal implementation**

```python
# add to platform_export.py
import sys


def push_to_platform(result: dict, run_id: str) -> int:
    """Best-effort: POST each record to the platform. Returns count POSTed.
    No-op (returns 0) unless BOTH RLEAAS_CALLBACK_URL and RLEAAS_TOKEN are set.
    Never raises — a push failure must not fail the run."""
    url = os.environ.get("RLEAAS_CALLBACK_URL")
    token = os.environ.get("RLEAAS_TOKEN")
    if not url or not token:
        return 0
    env_name = os.environ.get("RLEAAS_ENV_NAME", DEFAULT_ENV_NAME)
    recs = result_to_platform_records(result, env_name, run_id)
    sent = 0
    for rec in recs:
        try:
            data = json.dumps(rec).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
            sent += 1
        except Exception as e:  # noqa: BLE001 — best-effort, never fail the run
            print(f"[platform_export] push failed for run {run_id}: {e}", file=sys.stderr)
    return sent
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_platform_export.py -v`
Expected: PASS (all, incl. the 2 push tests)

- [ ] **Step 5: Confirm it imports from the ENGINE venv too**

Run: `cd /home/azureuser/A2A_RL/project_deal && .venv/bin/python -c "import platform_export; print(platform_export.push_to_platform({'per_set':[]}, 'x'))"`
Expected: prints `0` (no env set → no-op), no ImportError. Proves the dependency-free module loads under the engine venv.

- [ ] **Step 6: Update the log (no commit)**

Append to `/home/azureuser/A2A_RL/CLAUDE.md`: `- B1 Task 2 done: platform_export.push_to_platform (env-gated best-effort urllib POST), tests green, imports clean from engine venv.` Do NOT git commit.

---

### Task 3: Wire the push hook into `adapter.py`

**Files:**
- Modify: `adapter.py` (add import + one call at the end of `run_live`)
- Test: `tests/test_adapter_push_hook.py`  ← ENGINE-venv test dir (imports `adapter`→`marketplace`→`dotenv`, which live only in `.venv`; run with `.venv`, NOT `sim_ui/.venv`)

**Interfaces:**
- Consumes: `platform_export.push_to_platform` (Task 2), `adapter.run_live` (existing).
- Produces: after `run_live` writes `result.json`, it calls `platform_export.push_to_platform(result, run_id)` exactly once. The call is wrapped so a push error can never break the run.

- [ ] **Step 1: Write the failing test** (monkeypatches all the heavy engine calls so no stack/LLM is needed — asserts run_live invokes the push with the extracted result + run_id)

```python
# sim_ui/tests/test_adapter_push_hook.py
import json
import types
from pathlib import Path

import adapter
import platform_export


def test_run_live_calls_push(monkeypatch, tmp_path):
    calls = {}

    # Stub every heavy side-effect of run_live: no env.yaml, no stack, no rollout.
    monkeypatch.setattr(adapter, "reset_env_yaml", lambda *a, **k: None)
    monkeypatch.setattr(adapter, "clear_session_scratch", lambda *a, **k: None)

    out_dir = tmp_path / "run"
    out_dir.mkdir()
    monkeypatch.setattr(adapter, "prepare_output_dir", lambda run_id: out_dir)
    monkeypatch.setattr(adapter, "make_run_id", lambda plan, now=None: "run_test")
    monkeypatch.setattr(adapter, "build_task_file",
                        lambda *a, **k: (out_dir / "task.jsonl", ["Kai"]))

    # subprocess.run: pretend both the restart AND ng_collect succeeded, and
    # write a rollouts.jsonl so run_live proceeds to extract_results.
    def fake_subprocess_run(cmd, **k):
        (out_dir / "rollouts.jsonl").write_text(
            json.dumps({"metadata": {"set_id": "set_01", "focal_persona": "Kai"},
                        "reward": 0.3, "rubric_scores": {}, "deals": [], "channel_events": []}) + "\n")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(adapter.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(adapter, "split_rollouts_by_set", lambda *a, **k: ["rollouts_set_01.jsonl"])

    def fake_push(result, run_id):
        calls["result"] = result
        calls["run_id"] = run_id
        return 1

    monkeypatch.setattr(platform_export, "push_to_platform", fake_push)

    plan = adapter.build_plan(types.SimpleNamespace(
        phase="market_deal", set="01", focal="sonnet", opponent="gemini",
        max_turns=20, seed=42))
    adapter.run_live(plan)

    assert calls["run_id"] == "run_test"
    assert calls["result"]["mean_reward"] == 0.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/azureuser/A2A_RL/project_deal && .venv/bin/python -m pytest tests/test_adapter_push_hook.py -v`  (ENGINE venv)
Expected: FAIL — `KeyError: 'run_id'` (run_live does not call push yet).

- [ ] **Step 3: Write minimal implementation** — add the import near the top of `adapter.py` (after the `marketplace` import, ~line 29):

```python
import platform_export
```

Then, in `run_live`, immediately after the existing `print(f"[adapter] mean_reward=...")` line (~line 361) and before `return result_path`, add:

```python
    # Announce this finished run to the RLEaaS platform (best-effort, env-gated:
    # no-op unless RLEAAS_CALLBACK_URL + RLEAAS_TOKEN are set). Never fails the run.
    try:
        pushed = platform_export.push_to_platform(result, run_id)
        if pushed:
            print(f"[adapter] pushed {pushed} rollout record(s) to the platform")
    except Exception as e:  # noqa: BLE001
        print(f"[adapter] platform push skipped: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/azureuser/A2A_RL/project_deal && .venv/bin/python -m pytest tests/test_adapter_push_hook.py -v`  (ENGINE venv)
Expected: PASS

- [ ] **Step 5: Sanity — adapter still imports + dry-run works (engine venv)**

Run: `cd /home/azureuser/A2A_RL/project_deal && .venv/bin/python adapter.py --phase market_deal --set 01 --focal sonnet --opponent gemini --dry-run`
Expected: prints the PLAN block, exits 0 (no push, dry-run runs nothing).

- [ ] **Step 6: Update the log (no commit)**

Append to `/home/azureuser/A2A_RL/CLAUDE.md`: `- B1 Task 3 done: adapter.run_live calls push_to_platform after writing result.json (best-effort, wrapped); dry-run + import clean.` Do NOT git commit.

---

### Task 4: Blocking runner + read helpers in `run_api.py`

**Files:**
- Create: `sim_ui/run_api.py`
- Test: `sim_ui/tests/test_run_api.py`

**Interfaces:**
- Consumes: `live_runner` helpers — `ENGINE_PY`, `ADAPTER`, `_build_adapter_cmd`, `_run_dir`, `_read_result_json`, `_teardown_stack` (existing).
- Produces:
  - `class RunInProgress(Exception)` — raised when a run is already active.
  - `class RunFailed(Exception)` — `.log_tail` attribute; raised on non-zero adapter exit / timeout.
  - `run_blocking(params: dict) -> dict` — single-flight (raises `RunInProgress` if busy). Spawns adapter (or `params["_cmd_override"]`), waits (cap: `all` → 3600s else 1200s), tears down stack (unless `_cmd_override`), returns `result.json` dict augmented with `run_id` (the newest adapter_runs dir name, or `params["_result_dir"]` name in tests). Raises `RunFailed` on non-zero exit (with `log_tail`) or timeout.
  - `latest_result() -> dict | None` — the newest finished run's result.json (reuse `_run_dir` with empty params).
  - `result_for(run_id: str) -> dict | None` — `results/adapter_runs/<run_id>/result.json` or None.

- [ ] **Step 1: Write the failing test** (fake adapter writes a result.json, mirrors test_live_runner)

```python
# sim_ui/tests/test_run_api.py
import json
import sys
from pathlib import Path

import pytest

from sim_ui import run_api


def _fake_adapter(tmp_path, result_dir):
    result_dir.mkdir(exist_ok=True)
    (result_dir / "result.json").write_text(json.dumps(
        {"mean_reward": 0.42, "focal_model": "m", "opponents_model": "o",
         "per_set": [{"set_id": "set_01", "reward": 0.42}]}))
    fake = tmp_path / "fake_adapter.py"
    fake.write_text("import sys; sys.exit(0)\n")
    return [sys.executable, str(fake)]


def test_run_blocking_returns_reward(tmp_path):
    result_dir = tmp_path / "run_id_dir"
    cmd = _fake_adapter(tmp_path, result_dir)
    params = {"phase": "market_deal", "set": "01", "focal": "sonnet",
              "opponent": "gemini", "max_turns": 20, "seed": 42,
              "_cmd_override": cmd, "_result_dir": str(result_dir)}
    out = run_api.run_blocking(params)
    assert out["mean_reward"] == 0.42
    assert out["run_id"] == "run_id_dir"


def test_run_blocking_raises_on_failure(tmp_path):
    result_dir = tmp_path / "run_fail"
    result_dir.mkdir()
    fake = tmp_path / "boom.py"
    fake.write_text("import sys; sys.exit(2)\n")
    params = {"phase": "market_deal", "set": "01", "focal": "sonnet",
              "opponent": "gemini", "max_turns": 20, "seed": 42,
              "_cmd_override": [sys.executable, str(fake)],
              "_result_dir": str(result_dir)}
    with pytest.raises(run_api.RunFailed):
        run_api.run_blocking(params)


def test_run_blocking_busy_raises(tmp_path, monkeypatch):
    # Pretend the single-flight lock is already held.
    monkeypatch.setattr(run_api._LOCK, "acquire", lambda blocking=False: False)
    with pytest.raises(run_api.RunInProgress):
        run_api.run_blocking({"phase": "market_deal", "set": "01",
                              "focal": "s", "opponent": "g",
                              "max_turns": 20, "seed": 42})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_run_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sim_ui.run_api'`

- [ ] **Step 3: Write minimal implementation**

```python
# sim_ui/run_api.py
"""Blocking run + read helpers behind the /api/* reward doors. Reuses
live_runner's subprocess/teardown machinery. One run at a time (the engine is a
single stack); a second call while busy raises RunInProgress."""
import json
import subprocess
import threading
import time
from pathlib import Path

from . import live_runner

_LOCK = threading.Lock()


class RunInProgress(Exception):
    """A run is already active (single engine stack)."""


class RunFailed(Exception):
    def __init__(self, msg, log_tail=""):
        super().__init__(msg)
        self.log_tail = log_tail


def _stack_running() -> bool:
    try:
        r = subprocess.run(["pgrep", "-f", "bin/ng_run"],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def _cap_seconds(params: dict) -> int:
    return 3600 if str(params.get("set")).lower() == "all" else 1200


def run_blocking(params: dict) -> dict:
    if not _LOCK.acquire(blocking=False):
        raise RunInProgress("run in progress")
    try:
        # A live human run (/run_live) also boots the stack — refuse to overlap it.
        if not params.get("_cmd_override") and _stack_running():
            raise RunInProgress("run in progress")

        cmd = params.get("_cmd_override") or live_runner._build_adapter_cmd(params)
        proc = subprocess.Popen(cmd, cwd=str(live_runner.ROOT))
        cap = _cap_seconds(params)
        start = time.time()
        while proc.poll() is None:
            if time.time() - start > cap:
                proc.kill()
                raise RunFailed("run exceeded time limit")
            time.sleep(0.2)

        if not params.get("_cmd_override"):
            live_runner._teardown_stack()

        if proc.returncode not in (0, None):
            tail = ""
            alog = live_runner.ROOT / "data" / "ng_run_live" / "adapter.log"
            if alog.exists():
                tail = "\n".join(alog.read_text().splitlines()[-20:])
            raise RunFailed(f"adapter exited {proc.returncode}", tail)

        result = live_runner._read_result_json(params) or {}
        run_dir = live_runner._run_dir(params)
        result["run_id"] = run_dir.name if run_dir else None
        return result
    finally:
        _LOCK.release()


def latest_result() -> dict | None:
    d = live_runner._run_dir({})
    if d is None:
        return None
    rp = d / "result.json"
    out = json.loads(rp.read_text()) if rp.exists() else None
    if out is not None:
        out["run_id"] = d.name
    return out


def result_for(run_id: str) -> dict | None:
    rp = live_runner.ROOT / "results" / "adapter_runs" / run_id / "result.json"
    if not rp.exists():
        return None
    out = json.loads(rp.read_text())
    out["run_id"] = run_id
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_run_api.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Update the log (no commit)**

Append to `/home/azureuser/A2A_RL/CLAUDE.md`: `- B1 Task 4 done: sim_ui/run_api.run_blocking (single-flight lock + stack-busy guard + teardown reuse) + latest_result/result_for, 3 tests green.` Do NOT git commit.

---

### Task 5: REST endpoints + `serve.py` wiring + `$PORT` (A1)

**Files:**
- Modify: `sim_ui/run_api.py` (add `register_routes`)
- Modify: `sim_ui/serve.py` (call `register_routes` before the static mount; add `_port()`)
- Test: `sim_ui/tests/test_serve_api.py`

**Interfaces:**
- Consumes: `run_blocking`, `latest_result`, `result_for`, `RunInProgress`, `RunFailed` (Task 4).
- Produces:
  - `register_routes(app)` — adds `POST /api/run`, `GET /api/result/latest`, `GET /api/result/{run_id}`, `GET /api/health`.
  - `serve._port() -> int` — `PORT` then `A2A_UI_PORT` then `8000`.
  - `POST /api/run` body: `{phase, set, focal, opponent, max_turns?}` → `200` result dict; `409 {error}` on `RunInProgress`; `400 {error}` on bad params; `500 {error, log_tail}` on `RunFailed`.

- [ ] **Step 1: Write the failing test** (FastAPI TestClient; a fake adapter cmd is injected via a monkeypatched `run_blocking` for the endpoint tests, and the port function is unit-tested directly)

```python
# sim_ui/tests/test_serve_api.py
import pytest
from fastapi.testclient import TestClient

from sim_ui import serve, run_api


@pytest.fixture
def client():
    return TestClient(serve.build_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_run_ok(client, monkeypatch):
    monkeypatch.setattr(run_api, "run_blocking",
                        lambda params: {"mean_reward": 0.5, "run_id": "r1"})
    r = client.post("/api/run", json={"phase": "market_deal", "set": "01",
                                      "focal": "sonnet", "opponent": "gemini"})
    assert r.status_code == 200
    assert r.json()["mean_reward"] == 0.5


def test_run_busy_returns_409(client, monkeypatch):
    def _busy(params):
        raise run_api.RunInProgress("run in progress")
    monkeypatch.setattr(run_api, "run_blocking", _busy)
    r = client.post("/api/run", json={"phase": "market_deal", "set": "01",
                                      "focal": "s", "opponent": "g"})
    assert r.status_code == 409


def test_run_failed_returns_500_with_tail(client, monkeypatch):
    def _fail(params):
        raise run_api.RunFailed("adapter exited 2", "boom-tail")
    monkeypatch.setattr(run_api, "run_blocking", _fail)
    r = client.post("/api/run", json={"phase": "market_deal", "set": "01",
                                      "focal": "s", "opponent": "g"})
    assert r.status_code == 500
    assert r.json()["log_tail"] == "boom-tail"


def test_static_still_served(client):
    # The "/" static mount must still work after /api/* routes are registered.
    r = client.get("/")
    assert r.status_code == 200


def test_port_precedence(monkeypatch):
    monkeypatch.setenv("PORT", "7001")
    monkeypatch.setenv("A2A_UI_PORT", "8001")
    assert serve._port() == 7001
    monkeypatch.delenv("PORT", raising=False)
    assert serve._port() == 8001
    monkeypatch.delenv("A2A_UI_PORT", raising=False)
    assert serve._port() == 8000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_serve_api.py -v`
Expected: FAIL — `AttributeError: module 'sim_ui.serve' has no attribute '_port'` / 404 on `/api/health`.

- [ ] **Step 3a: Add `register_routes` to `sim_ui/run_api.py`**

```python
# append to sim_ui/run_api.py
from fastapi import Body
from fastapi.responses import JSONResponse


def register_routes(app) -> None:
    @app.get("/api/health")
    def _health():
        return {"status": "ok"}

    @app.post("/api/run")
    def _run(payload: dict = Body(...)):
        required = ("phase", "set", "focal", "opponent")
        missing = [k for k in required if not payload.get(k)]
        if missing:
            return JSONResponse({"error": f"missing: {missing}"}, status_code=400)
        params = {
            "phase": payload["phase"], "set": payload["set"],
            "focal": payload["focal"], "opponent": payload["opponent"],
            "max_turns": int(payload.get("max_turns") or 100),
            "seed": int(payload.get("seed") or 42),
        }
        try:
            return run_blocking(params)
        except RunInProgress as e:
            return JSONResponse({"error": str(e)}, status_code=409)
        except RunFailed as e:
            return JSONResponse({"error": str(e), "log_tail": e.log_tail}, status_code=500)

    @app.get("/api/result/latest")
    def _latest():
        r = latest_result()
        return r if r is not None else JSONResponse({"error": "no runs yet"}, status_code=404)

    @app.get("/api/result/{run_id}")
    def _result(run_id: str):
        r = result_for(run_id)
        return r if r is not None else JSONResponse({"error": "unknown run_id"}, status_code=404)
```

- [ ] **Step 3b: Wire into `sim_ui/serve.py`** — in `build_app()`, register the API routes AFTER mounting Gradio and BEFORE the StaticFiles mount (the `/` mount is a catch-all — API routes must be registered first):

```python
def build_app() -> FastAPI:
    app = FastAPI(title="Agent-to-Agent Marketplace")
    # mount Gradio FIRST so /gradio wins over the "/" static catch-all
    app = gr.mount_gradio_app(app, _gradio_backend(), path="/gradio")
    # reward doors (POST /api/run, GET /api/result/*, /api/health) — BEFORE "/"
    from . import run_api
    run_api.register_routes(app)
    # serve the exact static UI at the root (html=True -> index.html for /)
    app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
    return app
```

And replace the `__main__` port line:

```python
def _port() -> int:
    import os
    return int(os.environ.get("PORT") or os.environ.get("A2A_UI_PORT") or 8000)


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=_port())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/test_serve_api.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Full suite green + server boots**

Run BOTH suites (each in its own venv):
`cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/ -v && .venv/bin/python -m pytest tests/ -v`
Expected: sim_ui suite green (test_live_runner + test_platform_export + test_run_api + test_serve_api); engine suite green (test_live_log + test_adapter_push_hook).
Then: `cd /home/azureuser/A2A_RL/project_deal && PORT=8123 sim_ui/.venv/bin/python -c "from sim_ui import serve; import uvicorn, threading, time, urllib.request; app=serve.build_app(); t=threading.Thread(target=lambda: uvicorn.run(app, host='127.0.0.1', port=8123, log_level='warning'), daemon=True); t.start(); time.sleep(3); print(urllib.request.urlopen('http://127.0.0.1:8123/api/health').read())"`
Expected: prints `b'{"status":"ok"}'` — confirms routes live on the real app and `$PORT`-style binding works.

- [ ] **Step 6: Update the log (no commit)**

Append to `/home/azureuser/A2A_RL/CLAUDE.md`: `- B1 Task 5 done (B1 COMPLETE + A1): /api/run (blocking, 409/400/500), /api/result/latest+/{run_id}, /api/health registered before static mount; serve._port() honors $PORT; full sim_ui suite green; /api/health verified on a live boot. Next: Step 4 Docker.` Do NOT git commit.

---

## Post-plan verification (whole feature)

- [ ] All tests pass (both venvs): `cd /home/azureuser/A2A_RL/project_deal && sim_ui/.venv/bin/python -m pytest sim_ui/tests/ -v && .venv/bin/python -m pytest tests/ -v`
- [ ] adapter dry-run unaffected: `.venv/bin/python adapter.py --phase review --set 02 --focal opus --opponent gpt --dry-run`
- [ ] Push is a no-op with no callback env (engine venv): `.venv/bin/python -c "import platform_export; print(platform_export.push_to_platform({'per_set':[{'set_id':'set_01','reward':0.3}]},'x'))"` → `0`
- [ ] `verifiers.py`, engine, `/run_live`, static UI unchanged (only `adapter.py` +import/+push call, `serve.py` +routes/+port).
- [ ] A **paid** end-to-end live check (`POST /api/run` actually booting the stack + a real rollout, and a real push to a local capture server) is deferred to the user — it costs OpenRouter credit. Note this in CLAUDE.md; do not run it automatically.

## Open items carried to integrate-time (Step 6, NOT this plan)

- Exact platform de-dup: `store_rollout` assigns its own uuid; our `run_id` rides in `final_outcome`. Platform-side de-dup / upsert-by-run_id is Step-6 work.
- Container→mall reachability + whether `POST /api/rollouts` needs auth beyond the bearer token — verify at integrate; pull (`/api/result/latest`) is the fallback.
- `RLEAAS_ENV_NAME` must match the name the env is registered under in the platform.
