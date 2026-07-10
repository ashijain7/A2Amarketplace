# Reward Doors (Step 2/6 bridge, "B1") — Design

**Date:** 2026-07-10
**Status:** approved (brainstorm), ready for implementation plan
**Scope:** add a plain REST control surface + a push hook so the RLEaaS platform can obtain a
marketplace run's **reward as data** (not just a picture on screen). Steps 1–5 constraint holds:
**`resources_server/verifiers.py` is not touched** (no rubric/scoring change). The engine
(`resources_server/`, `marketplace/`) is not touched except the one push hook, which is
engine-*adjacent* control flow (same class as prior approved money-want / live_log hooks) —
it changes no reward math.

---

## 1. Goal & non-goals

**Goal.** A finished marketplace run's reward reaches the RLEaaS platform's store as data, without
re-running and without the platform having to guess which run produced it. Two triggers are supported:
a **human** clicking Live inside the embedded UI, and an **optional platform-initiated** headless run.

**Non-goals.**
- No rubric or reward-semantics change (`verifiers.py` untouched).
- No mall-side code here (the callback ingest, token/URL injection, env registration = Step 6).
- No change to the human streaming experience (`/run_live` stays as-is; we only add a completion hook).
- Cached-mode batch seeding of the platform (C1) is separate work; it reuses this design's converter.

---

## 2. The problem this solves

The platform ("mall") can talk to our container **only over HTTP** through its reverse proxy. It cannot
reach inside to run our engine or read our files. All reward-making machinery (boot ng_run → run adapter →
`verify()` → `result.json`) lives inside our container. So the reward can only leave through a door we expose.

Two dangers we explicitly avoid:
- **Double-running.** A run must not be executed twice just to both *watch* it and *save* it.
- **"Which score?"** When a human triggers a run inside our iframe, the platform has no run_id and no
  existing channel to learn one (its only `postMessage` listener handles UI nav, not scores; nothing reads a
  reward from an external container today — verified in the platform code).

**Resolution.** Every run — whichever door triggered it — writes `result.json`. Runs are **serialized**
(one engine stack, one run at a time), so "the most recent finished run" is unambiguous. The finished run
**announces itself** (push) to the platform's existing ingest endpoint, tagged with its own `run_id` and
models — so the platform never guesses. Pull endpoints exist as a fallback/debug surface.

---

## 3. Locked decisions (from brainstorm 2026-07-10)

1. **Blocking** (`POST /api/run` waits until the run is done, returns the reward in the response).
2. **One call covers single set OR all-5** (`set=01..05` or `set=all`) — mirrors `adapter.py` exactly.
3. **Primary path = human-triggered `/run_live` + push-on-completion.** The platform has no run controls of
   its own (no phase/set/focal/opponent knobs anywhere in its UI — those live only in our iframe), so runs
   realistically start from a human clicking Live.
4. **`POST /api/run` is built but optional** — a headless trigger for future platform-initiated runs
   (automated eval / training sweeps). Kept as-is; used only if the platform chooses to.
5. **Push over pull as the reward channel**, because the run that just finished knows its own id/models and
   the platform has no reliable way to learn them otherwise. **Pull (`/api/result`) is the fallback.**
6. **Push needs a token.** The platform injects `RLEAAS_CALLBACK_URL` + `RLEAAS_TOKEN` into the container
   (same channel it injects `$PORT`). Push authenticates with the token. Both mall-side, Step 6.
7. **Push lives in `adapter.py`** (after it writes `result.json`) so it fires for *any* door and is a
   **no-op when the callback env is unset** (cached/local/CLI runs unaffected).
8. **One shared converter** `result.json → platform rollout format`, reused by the live push AND by C1's
   cached batch seeding. Built once.

---

## 4. Endpoints (added to `sim_ui/serve.py`)

Registered on the FastAPI `app` **before** the `StaticFiles("/")` mount, or the catch-all swallows them.

| Route | Method | Body / params | Returns |
|---|---|---|---|
| `/api/run` | POST | `{phase, set, focal, opponent, max_turns?}` | `200` full `result.json` + `run_id`; `409` if a run is in progress; `400` bad params; `500` `{error, log_tail}` |
| `/api/result/latest` | GET | — | `200` the most recent finished run's `result.json`; `404` if none yet |
| `/api/result/{run_id}` | GET | — | `200` that run's `result.json`; `404` if unknown |
| `/api/health` | GET | — | `200` `{status:"ok"}` |

`POST /api/run` is **blocking**: it spawns `adapter.py`, waits for exit, reads the newest
`results/adapter_runs/<run_id>/result.json`, tears the stack down, and returns it. `set=all` runs 5
rollouts and returns `mean_reward` + `per_set` (already produced by `extract_results`).

---

## 5. The push hook (in `adapter.py`)

After `run_live()` writes `result.json`:

```
if RLEAAS_CALLBACK_URL and RLEAAS_TOKEN are set in env:
    payload = to_platform_rollout(result_json, run_id, phase, set, focal, opponent)
    POST payload  →  RLEAAS_CALLBACK_URL   with  Authorization: Bearer <RLEAAS_TOKEN>
    (best-effort: log + swallow on failure; never fail the run because the push failed)
else:
    no-op
```

- Fires for **every** completed adapter run (human `/run_live`, headless `/api/run`, or CLI), because it
  sits in the one place all of them converge.
- **De-dup:** the payload carries `run_id` inside `final_outcome` for traceability. The current platform
  ingest (`store_rollout`, `main.py:8443`) assigns its **own** uuid `id` — so it does NOT upsert by our
  `run_id` today. Platform-side de-dup (e.g. skipping a record whose `final_outcome.run_id` already exists)
  is a **Step-6** concern, not handled here.
- Requires an HTTP client available in the **engine** `.venv` (adapter's venv). Use the stdlib
  (`urllib.request`) to avoid adding a dependency.

---

## 6. The shared converter

`result.json → platform rollout record`. One function, two callers:
- **live push** (§5) — converts a single finished run.
- **C1 cached seeding** (separate work) — converts each of the 139 recorded runs in a batch.

Exact target shape is read from the platform's own converter (`_convert_hitl_rollout_to_store_format`) and a
real sample (`sre_rollouts.json`) at build time — not guessed. Lives in a small shared module
(e.g. `sim_ui/ui/logic.py` alongside the existing exporters, or a new `platform_export.py`) importable by
both the push (engine side) and the C1 batch (sim_ui side). **Note the venv split:** if the push imports the
converter it must be importable from the engine venv; keep it dependency-free (pure dict/JSON transform).

---

## 7. Concurrency & lifecycle

- **One run at a time.** The engine is a single stack on port 11000; two concurrent runs collide. A
  module-level lock guards `POST /api/run` against a second `/api/run` → `409 {error:"run in progress"}`.
  Cross-door protection is **one-directional**: `POST /api/run` also checks `pgrep -f bin/ng_run` and refuses
  (`409`) if a live `/run_live` run is already booting the stack. The **reverse is NOT guarded** — a human
  clicking Live during an in-flight `/api/run` would `restart_ng_run.sh` and kill that headless run's stack
  (it errors out as `RunFailed`). This is an accepted v1 limitation: `/api/run` is optional/unused until the
  platform opts in (Step 6), and in the human-triggered primary path only `/run_live` runs. Full mutual
  exclusion (making `/run_live` respect the same lock) is deferred to Step-6, when the platform controls both
  triggers. (`/run_live` itself serializes via Gradio's queue.)
- **Teardown.** After a `/api/run` completes, tear the stack down (reuse `live_runner._teardown_stack`,
  `pkill -f "bin/ng_run"`) to free RAM — same policy as the live path.
- **Wall cap.** Reuse a generous cap (single ≈ 20 min; `all` ≈ 60 min) → `500` on exceed.

---

## 8. What is reused vs added

**Reused, unchanged:** `adapter.py` run pipeline (add only the push hook), `live_runner` constants +
`_build_adapter_cmd` / `_run_dir` / `_read_result_json` / `_teardown_stack`, the engine, `verifiers.py`,
`/run_live`, the static UI.

**Added:** the 4 endpoints in `serve.py`, a small run helper (`live_runner.run_blocking` or `run_api.py`),
the push hook in `adapter.py`, the shared converter, a single-flight lock.

---

## 9. Error handling

| Case | Response |
|---|---|
| Bad phase/set/model | `400 {error}` |
| Run already in progress | `409 {error:"run in progress"}` |
| adapter non-zero exit | `500 {error, log_tail}` (last ~20 lines of the adapter log) |
| Wall-cap exceeded | `500 {error:"run exceeded time limit"}`, stack killed |
| `/api/result` unknown/none | `404` |
| Push failure | run still succeeds; push error logged, swallowed |

---

## 10. Testing

Fake-adapter unit tests (mirror `tests/test_live_runner.py`, no LLM):
- `POST /api/run` with a fake adapter writing a `result.json` → asserts the reward is returned.
- `409` when the lock is held.
- `500` on a non-zero fake-adapter exit (with `log_tail`).
- Push hook: **fires** (captured by a fake callback server) when `RLEAAS_CALLBACK_URL`+`TOKEN` set;
  **no-op** when unset.
- Converter: `result.json` → platform record shape matches the sampled format.
- `GET /api/result/latest` and `/{run_id}` return the right file; `404` when absent.

---

## 11. Integrate-time (mall side, Step 6 — NOT in this build)

- Inject `RLEAAS_CALLBACK_URL` + `RLEAAS_TOKEN` (and `OPENROUTER_API_KEY`, `$PORT`) into the container.
- Accept the authed push at the existing ingest endpoint (`store_rollout` / `POST /api/rollouts`), upsert by
  `run_id`; confirm container→mall reachability + auth.
- Register the env tile + point `local_url` at the container.
- C1b: register the converted cached rollouts file so cached runs also list in the Rollouts tab.

---

## 12. Open items (tracked, not blocking this build)

- Exact platform rollout record shape — pin against `_convert_hitl_rollout_to_store_format` + `sre_rollouts.json`.
- Container→mall networking mode for the push (docker bridge / injected URL) — verify at integrate-time;
  fall back to pull (`/api/result/latest`) if push proves hard.
- Whether `POST /api/rollouts` requires auth beyond the token — confirm at integrate-time.
- **Full two-door mutual exclusion** — today only `/api/run`→(live) is guarded (§7); making `/run_live` respect
  the same lock is deferred to Step-6.
- **Failed-rollout status semantics** — the converter emits `status="completed"` with `total_reward=0.0` even for
  a `None`-reward (failed/empty) rollout. Step-6 may map a missing reward to `status="failed"` instead.
- **Verified 2026-07-10 (final review):** `reward_breakdown` now drops `None`-valued rubrics (platform types it
  `Dict[str,float]`, rejects `None`→422). Real runs routinely have `None` rubrics (swap_quality in non-swap,
  transactional_integrity in non-transaction, persona_privacy in 0%-privacy sets) — without the filter the push
  would 422 for ~every real run. Fixed + covered by `test_none_rubric_values_dropped`.
