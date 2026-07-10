"""Blocking run + read helpers behind the /api/* reward doors. Reuses
live_runner's subprocess/teardown machinery. One run at a time (the engine is a
single stack); a second call while busy raises RunInProgress."""
import json
import subprocess
import threading
import time

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


def _read_tail(n: int = 20) -> str:
    alog = live_runner.ROOT / "data" / "ng_run_live" / "adapter.log"
    if not alog.exists():
        return ""
    return "\n".join(alog.read_text().splitlines()[-n:])


def run_blocking(params: dict) -> dict:
    if not _LOCK.acquire(blocking=False):
        raise RunInProgress("run in progress")
    override = params.get("_cmd_override")
    started = False
    logf = None
    try:
        # A live human run (/run_live) also boots the stack — refuse to overlap it.
        # (This raise happens BEFORE a proc is started, so teardown below must not fire.)
        # NOTE: this guard is one-directional — /api/run refuses to start during a live run, but a live /run_live is NOT blocked by this lock (full mutual exclusion is deferred to Step-6 when the platform controls both triggers).
        if not override and _stack_running():
            raise RunInProgress("run in progress")

        cmd = override or live_runner._build_adapter_cmd(params)
        if override:
            proc = subprocess.Popen(cmd, cwd=str(live_runner.ROOT))
        else:
            alog_dir = live_runner.ROOT / "data" / "ng_run_live"
            alog_dir.mkdir(parents=True, exist_ok=True)
            logf = open(alog_dir / "adapter.log", "w")
            proc = subprocess.Popen(cmd, cwd=str(live_runner.ROOT),
                                    stdout=logf, stderr=subprocess.STDOUT)
        started = True

        cap = _cap_seconds(params)
        start = time.time()
        timed_out = False
        while proc.poll() is None:
            if time.time() - start > cap:
                proc.kill()
                timed_out = True
                break
            time.sleep(0.2)

        if logf is not None:
            logf.flush()

        if timed_out:
            raise RunFailed("run exceeded time limit",
                            _read_tail() if not override else "")
        if proc.returncode not in (0, None):
            raise RunFailed(f"adapter exited {proc.returncode}",
                            _read_tail() if not override else "")

        result = live_runner._read_result_json(params) or {}
        run_dir = live_runner._run_dir(params)
        result["run_id"] = run_dir.name if run_dir else None
        return result
    finally:
        if logf is not None:
            logf.close()
        # Teardown ONLY if we actually started a stack (so the busy-overlap raise,
        # which never started one, does not kill the OTHER run's stack) and not in tests.
        if started and not override:
            live_runner._teardown_stack()
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


def register_routes(app) -> None:
    from fastapi import Body
    from fastapi.responses import JSONResponse

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
