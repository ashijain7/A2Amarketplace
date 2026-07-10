# Live-Run Streaming (Step 3b) — Design

**Date:** 2026-07-09
**Status:** approved (brainstorm), ready for implementation plan
**Scope:** wire `sim_ui`'s **Live** path to `adapter.py` — a real marketplace rollout streamed
turn-by-turn into the existing static UI. Steps 1–5 constraint holds: **`resources_server/verifiers.py`
is not touched** (no rubric/scoring change).

---

## 1. Goal & non-goals

**Goal.** A "Live" mode in the marketplace UI: user picks scenario, evaluated model, opponent model,
persona set (or ALL), and max-turns (1–100 slider), clicks **RUN LIVE**, and watches a genuine rollout
play out message-by-message — with a real "🔍 searching the marketplace for a buyer/seller" wait while the
focal agent's counterparty is still computing its reply. Reward reveals when the episode ends.

**Non-goals.**
- No rubric or reward-semantics change (`verifiers.py` untouched).
- No RLEaaS reward connector (that is Step 6).
- No registration of the fresh live run into the cached catalog (deferred).
- No OpenRouter live model list (curated + free-text paste now; live list deferred).

---

## 2. Locked decisions (from brainstorm 2026-07-09)

1. **Genuine per-turn streaming**, not run-then-replay. A minimal, append-only **engine hook** surfaces
   each event as it happens; the UI renders it live with real waits.
2. **Model picker = curated list + free-text add.** Radio list of known aliases
   (sonnet / opus / gemini / gpt / haiku) plus an "➕ Add model" field that accepts any full
   `provider/model` slug (the backend already accepts any slug via `resolve_model`).
3. **Scope = single set OR all 5 sets.** ALL = 5 paid rollouts (~15–20 min); the RUN control shows an
   estimated cost/time label. No confirm modal — RUN starts immediately.
4. **Transport = keep Gradio (Route-1).** The static UI is unchanged; the live JS talks to a Gradio
   backend via the `@gradio/client` SDK (`gradio.Server` "any custom frontend with Gradio's backend"
   pattern). Gradio's queue gives run-serialization for free. Gradio is **isolated in `sim_ui/.venv`**
   (removed from `project_deal/.venv`) so it cannot clash with the ng_run stack.

---

## 3. Architecture — three layers + two fixes

```
browser (web/, static)  ──@gradio/client──►  Gradio backend (sim_ui/.venv, /gradio)
   render turns live                            │  run_live() generator
   "searching" real waits                       ├─ truncate MARKETPLACE_LIVE_LOG
   reward reveal on done                         ├─ spawn adapter.py subprocess (project_deal/.venv)
                                                  │      └─ restart_ng_run.sh → ng_run stack
                                                  │             └─ marketplace server:
                                                  │                  channel.post / room / seed / verify
                                                  │                       └─ live_log.emit(record)  ◄── engine hook
                                                  └─ tail MARKETPLACE_LIVE_LOG → yield each record ──► SSE ──► browser
```

### Layer 1 — Engine live-event log (append-only; no scoring touch)

- **New module `marketplace/live_log.py`** with `emit(record: dict)`:
  - Reads target path from `config.LIVE_LOG` (env `MARKETPLACE_LIVE_LOG`).
  - **Unset → no-op** (cached and normal paper runs are completely unaffected).
  - When set: append one JSON line, with a process-local monotonic `seq`, `flush()`ed.
- **`config.py`:** `LIVE_LOG = os.environ.get("MARKETPLACE_LIVE_LOG")`.
- **Call sites (all append-only, no behavior/score change):**
  - `marketplace/channel.py::Channel.post` → emit each public event:
    `{kind:"event", seq, event_id, author, action, price, target, message, phase}`.
  - settlement room emit (`settlement/__init__.py` counterparty reply path) → emit each room line:
    `{kind:"room", seq, deal_id, speaker, text, is_scammer}`.
  - `resources_server/app.py::seed_session` → emit start marker:
    `{kind:"seed", set_id, config_name, marketplace_phase, settlement:bool, focal, personas:[names]}`.
  - `resources_server/app.py::_verify_for_state` → emit reward marker:
    `{kind:"reward", set_id, reward, rubric_scores:{name:combined}}`.
- **Guarantees:** `verifiers.py` untouched; every hook is a side-effect append. Same class of engine-adjacent
  change as the approved money-want fix — no rubric input moves.
- **Single-run assumption:** only one live run at a time (enforced in Layer 2), so one fixed log path
  (`data/ng_run_live/events.jsonl`) is safe; the backend truncates it at run start.

### Layer 2 — Backend (sim_ui, Gradio)

- **`sim_ui/serve.py`** (unchanged shape): FastAPI serves the static app at `/`, and
  `gr.mount_gradio_app(app, demo, "/gradio")` mounts the Gradio backend.
- **`demo`** exposes ONE streaming generator `run_live(phase, set, focal, opponent, max_turns, seed)`
  reached from the browser via `@gradio/client` `client.submit("/run_live", {...})`:
  1. **Acquire run lock** (explicit guard; Gradio's queue also serializes). If busy → yield
     `{kind:"error", msg:"a live run is already in progress"}` and return.
  2. **Truncate** the `MARKETPLACE_LIVE_LOG` file.
  3. **Spawn `adapter.py`** as a subprocess with the **`project_deal/.venv`** interpreter and env
     including `MARKETPLACE_LIVE_LOG`. Args map straight through:
     `--phase --set --focal --opponent --max-turns --seed`.
  4. **Tail** the log file (poll ~150 ms, parse only complete lines) and **`yield`** each new record
     (Gradio streams it over SSE to the client).
  5. On subprocess exit: read the run's `result.json`, **yield** `{kind:"done", mean_reward, per_set}`,
     drain any remaining log lines first, release the lock.
  6. On failure (nonzero exit / missing `result.json`): **yield** `{kind:"error", msg, log_tail}`.
- **Env propagation (assumption to verify in the plan):** `adapter._stack_env` copies `os.environ`, so
  `MARKETPLACE_LIVE_LOG` rides the exact same channel that already carries `MARKETPLACE_PHASE`,
  `ENABLE_SETTLEMENT`, and `MARKETPLACE_OPPONENTS_MODEL` down through `restart_ng_run.sh` → `ng_run` →
  the marketplace subserver (which inherits the launcher's env). Confirm the subserver reads it.
- **Run command:** `sim_ui/.venv/bin/python -m sim_ui.serve` (port from `A2A_UI_PORT`, default 8000).

### Layer 3 — Frontend (`web/`, static — exact look preserved)

- **Enable the "Live" mode** (currently a disabled "coming soon" item).
- **Live controls** (rendered only in Live mode; cached controls unchanged):
  - **Model area with two tabs — Evaluated | Opponent.** Each tab: a curated radio list
    (sonnet-4.5 / opus-4.8 / gemini-3.1 / gpt-5.5 / haiku-4.5) plus **"➕ Add model"** free-text input
    accepting a full `provider/model` slug. Selection → `cur.focal` / `cur.opponent`.
  - **Scenario** dropdown (mode → phase/settlement mapping via adapter's `--phase` names).
  - **Persona set** dropdown: `set_01…set_05` or **ALL**.
  - **Max-turns slider 1–100** → `--max-turns`.
  - **RUN LIVE** button, with a small cost/time estimate label (ALL = 5× warning).
- **`runLive()`** — connect `@gradio/client`, `client.submit("/run_live", {...}).on("data", handleRecord)`.
  `handleRecord` dispatches by `kind`:
  - `seed` → set `focal`, reset the card header, start a fresh feed (mark set boundary for ALL).
  - `event` → **focal-relevant filter**: keep if `author == focal`, OR `target` ∈ tracked focal
    listing/offer ids, OR it is a reply within a thread the focal is in. Track focal listing/offer ids as
    they appear. Render a bubble via `bubbleHTML`. Manage the **wait state**: after a focal
    listing/offer/counter, show `waitRow("🔍 searching the marketplace for a buyer/seller")`; drop it when
    the next relevant reply streams in (a genuine wait, not a timer).
  - `room` → render a settlement-room bubble (scam styling for `is_scammer`).
  - `reward` → `revealReward` for that set.
  - `done` → show mean + per-set summary; re-enable RUN.
  - `error` → error banner; re-enable RUN.
- **Reuse** `bubbleHTML` / `waitRow` / `revealReward` verbatim. **Cached mode is untouched.**
- **Fallback note:** the focal-relevant live filter is best-effort; the authoritative clean per-deal view
  remains the post-run `result.json` / rollout (and could later seed the cached catalog).

### Fix #3 — venv split (isolate Gradio from the engine)

- **Create `sim_ui/.venv`** (`uv venv`): install `fastapi`, `uvicorn`, `gradio`, `pillow`.
- **Remove `gradio` from `project_deal/.venv`** (`uv pip uninstall gradio …`) so its `starlette` restores
  to the version the ng_run stack needs (was downgraded 1.0.0 → 0.52.1 by gradio 5.50). If the uninstall
  does not restore it, explicitly reinstall the ng_run-required `starlette`.
- **Verify:** `restart_ng_run.sh` → 3/3 healthy after the change; `sim_ui` serves from its own venv.

### Fix #4 — stale Mac path + guard gap

- **`nemo_gym_lib/resources_servers/marketplace/configs/marketplace.yaml:6-7`** — replace the
  `/Users/ashi.jain/…` comment with anchor-relative wording (comment only; no functional change).
- **`scripts/check_no_machine_paths.sh`** — extend the scan to the **3 forked nemo_gym dirs**
  (`resources_servers/marketplace`, `responses_api_agents/simple_agent`, `responses_api_models/openai_model`)
  while still excluding the ~85 stock upstream servers (their tests legitimately contain `/Users`). Verify
  the guard both passes clean and catches a planted `/Users` line in a forked dir.

---

## 4. Data flow — one set, live

1. Browser **RUN LIVE** → `@gradio/client` submit `/run_live`.
2. Backend: lock → truncate log → spawn `adapter.py`.
3. `adapter` resets `env.yaml` (focal), clears scratch, builds task, exports stack env
   (incl. `MARKETPLACE_LIVE_LOG`), runs `restart_ng_run.sh` (stack up ~10 s), then `ng_collect_rollouts`.
4. Per focal tool call, the marketplace server posts to the channel → `live_log.emit` appends a line →
   backend tail reads it → `yield` → browser renders the bubble. Between a focal action and its reply,
   the browser holds "searching" until the reply line streams in (real wait).
5. `verify` → `reward` line → browser reward reveal.
6. Subprocess exits → `result.json` read → `done` → RUN re-enabled.

ALL sets: the log carries `seed`/`reward` markers per set; the UI marks set boundaries and reveals each
set's reward, then the mean at `done`.

---

## 5. Error handling

- **Stack boot failure** → `adapter` exits nonzero → backend yields `error` with the tail of `rollout.log`.
- **Run already in progress** → backend yields a busy `error` (belt-and-suspenders with Gradio's queue).
- **Partial log lines** → tail parses only newline-terminated lines; keeps a remainder buffer.
- **Hang guard** → cap total wall-clock (e.g. 20 min for ALL) → kill subprocess, yield `error`.
- **Cost** → the RUN control shows an estimate; ALL shows a 5× note. No accidental-double-run (lock).

---

## 6. Testing / verification

- `live_log.emit` is a no-op with env unset; appends a valid JSON line when set (free unit check).
- `check_no_machine_paths.sh` passes clean **and** fails on a planted `/Users` line in a forked dir.
- ng_run boots 3/3 healthy after gradio removal from `project_deal/.venv`; `sim_ui` serves from its own venv.
- **Cached mode regression:** unchanged behavior after all edits.
- **Live smoke (paid, ~1 rollout):** `market_deal`, single set, sonnet vs gemini, max-turns 20 → events
  stream in order, "searching" waits are real, reward reveals, `result.json` written; `verifiers.py`
  git-clean.

---

## 7. Deferred / open

- Seeding the fresh live run into the cached catalog for later clean replay.
- OpenRouter live model list (curated + free-text for now).
- RLEaaS reward connector (Step 6).
- Verify the `MARKETPLACE_LIVE_LOG` env reaches the marketplace subserver (well-founded; confirm in plan).
