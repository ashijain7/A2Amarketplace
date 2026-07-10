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
    d = _run_dir(params)
    if d is None:
        return None
    rp = d / "result.json"
    return json.loads(rp.read_text()) if rp.exists() else None


def _run_dir(params: dict):
    """The run's output dir (test injects _result_dir; live picks newest adapter_runs)."""
    if params.get("_result_dir"):
        return Path(params["_result_dir"])
    runs = ROOT / "results" / "adapter_runs"
    if not runs.exists():
        return None
    dirs = sorted((d for d in runs.iterdir() if d.is_dir()),
                  key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs:
        if (d / "result.json").exists():
            return d
    return None


def _photo_map(phase, set_id) -> dict:
    """Resolve item_id -> photo data-URI for a set's sellable items, so the live
    stream can show listing photos (the text-only event log carries no images).
    Keyed by item_id, so it works regardless of which persona holds the item."""
    if not phase or not set_id:
        return {}
    f = ROOT / f"personas_phase{phase}" / f"{set_id}.json"
    if not f.exists():
        return {}
    try:
        from .ui import logic
        m = {}
        for person in json.loads(f.read_text()):
            for it in person.get("items_to_sell", []):
                iid, ip = it.get("item_id"), it.get("image_path")
                if iid and ip:
                    uri = logic._image_data_uri(ip)
                    if uri:
                        m[iid] = uri
        return m
    except Exception:
        return {}


def _teardown_stack() -> None:
    """Kill the ng_run stack after a run finishes. Frees RAM between runs; the
    next run's adapter reboots it fresh anyway, so this never affects correctness.
    Fires once per RUN (after the adapter subprocess exits), so a --set all run
    keeps the stack up across all its rollouts and only tears down at the end."""
    try:
        subprocess.run(["pkill", "-f", "bin/ng_run"], timeout=15)
    except Exception:
        pass


def _build_episodes(run_dir, result: dict) -> list:
    """Reconstruct each fresh rollout into the frontend episode shape (same
    reconstruction cached uses) so the UI renders the polished end-of-run view —
    deal cards, no-deal attempts, 'passed / watched the market', summary."""
    if run_dir is None:
        return []
    rp = Path(run_dir) / "rollouts.jsonl"
    if not rp.exists():
        return []
    try:
        from .ui import logic
    except Exception:
        return []
    fm, om = result.get("focal_model"), result.get("opponents_model")
    out = []
    for line in rp.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(logic.rollout_line_to_frontend(json.loads(line), focal_model=fm, opponent_model=om))
        except Exception:
            continue
    return out


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
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield rec
                    # right after a seed, stream the set's item photos so listings
                    # can show their picture live (event log itself carries no images).
                    if rec.get("kind") == "seed":
                        pm = _photo_map(rec.get("marketplace_phase"), rec.get("set_id"))
                        if pm:
                            yield {"kind": "photos", "set_id": rec.get("set_id"), "map": pm}
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

    # run finished (1 set or all 5 shared one adapter boot) — free the stack.
    # Skipped in tests (fake adapter, no real stack).
    if not params.get("_cmd_override"):
        _teardown_stack()

    if proc.returncode not in (0, None):
        tail = ""
        alog = ROOT / "data" / "ng_run_live" / "adapter.log"
        if alog.exists():
            tail = "\n".join(alog.read_text().splitlines()[-20:])
        yield {"kind": "error", "msg": f"adapter exited {proc.returncode}", "log_tail": tail}
        return

    result = _read_result_json(params) or {}
    episodes = _build_episodes(_run_dir(params), result)
    yield {"kind": "done",
           "mean_reward": result.get("mean_reward"),
           "per_set": result.get("per_set", []),
           "episodes": episodes}
