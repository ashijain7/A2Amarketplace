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
