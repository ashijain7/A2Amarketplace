# Run stalls, marketplace re-launch, and rollout.log — diagnosis + fixes

Date: 2026-06-18. Investigated after C9 (Opus-4.8 vs GPT-5.5) phase-4 banked 0 rollouts,
gemini-pro (C7) phase-4 hung, a single rollout spawned many concurrent marketplace
sessions, and rollout.log never updated live.

## What we proved (so we don't re-litigate)

- **OpenRouter + the opus-4.8 slug are fine.** Direct calls to `anthropic/claude-opus-4.8`
  return HTTP 200 in ~4–8s on `/responses` + tools. The dot is the correct OpenRouter slug
  (OpenRouter uses dots: 4.8/4.7/4.6; the hyphen form normalizes to the same model). Not the cause.
- **C9 wiring + the Opus `service_tier` runtime patch are correct.** Only the focal slug differs
  from the working C6 (Opus-4.7). The patch (`scripts/nemo_gym_runtime_patch.py`) just lets
  Anthropic's `service_tier: "standard"` pass validation; it is model-agnostic.
- **The failures live in the NeMo Gym harness + an added timeout — not the model or our code.**

## Root causes

1. **Focal→OpenRouter read-stall (the original hang).** A focal LLM call occasionally half-opens
   (connection up, no response bytes). The committed NeMo Gym client uses `ClientTimeout()` = no
   timeout (`nemo_gym/server_utils.py:114`), so it blocks forever.

2. **Marketplace re-launch / many sessions per rollout (the big one).** NeMo Gym uses ONE global
   aiohttp timeout for ALL calls, but the `/run` call (collector→agent) runs the ENTIRE marketplace
   in a single request — minutes long, silent on the wire. Any read/total timeout makes `/run` time
   out; `server_utils.request()` retries it (`:163-219`, `MAX_NUM_TRIES=3`); each retry re-enters the
   agent's `run()`, which POSTs `/seed_session` with no marketplace cookie (cookies discarded by
   `DummyCookieJar`, `:115`) → a fresh session UUID → a brand-new marketplace dir each time
   (`resources_server/app.py:998,1023`). Slow focals (gemini-pro, opus) trip the timeout → many
   sessions; fast focals (sonnet, flash) finish in time → one session. The original no-timeout code
   did NOT have this (no timeout → no `/run` retry → no re-launch), which is why all phase 1–3 paper
   data ran clean for every model.

3. **Total turns exceed 100.** `_market_closed()` (`resources_server/app.py:192-203`) caps only the
   FOCAL's public calls at 50 (`FOCAL_PUBLIC_MAX`); background traders are uncapped, so channel turns
   reach ~108. `state._turn == len(channel.events)` counts every agent.

4. **rollout.log frozen.** It is fed only by `ng_collect_rollouts` stdout via `tee`; the collector
   emits just a tqdm bar that redraws every 60s (`rollout_collection.py:497`) — no per-turn output.
   The real per-turn activity is in `data/ng_run/<uuid>/channel.jsonl` (a separate process). Python
   block-buffering compounds it; `PYTHONUNBUFFERED=1` flushes the startup block but there is nothing
   new mid-run to flush.

## The 3 fixes (apply when running settlement / phase 4–5)

### Fix 1 — split the timeouts (kills the re-launch, keeps stall protection)
- `nemo_gym/server_utils.py:114` → permissive global so long internal calls never spuriously time out:
  `timeout=ClientTimeout(total=3600, sock_connect=15)` (drop `sock_read`).
- `nemo_gym/openai_utils.py` `create_response` (~:543) → tight timeout ONLY on the single OpenRouter
  call: add `timeout=ClientTimeout(total=300, sock_read=120)` to its request kwargs. A focal stall
  then raises `ServerTimeoutError` → `request()` catch-all retries 3× → self-heals, without touching `/run`.

### Fix 2 — hard 100-turn total cap (focal + opponents)
- `marketplace/config.py` (after `FOCAL_PUBLIC_MAX`): `MARKETPLACE_MAX_TURNS = int(os.getenv("MARKETPLACE_MAX_TURNS","100"))`.
- `resources_server/app.py:192` `_market_closed()`: check `state._turn >= mp_config.MARKETPLACE_MAX_TURNS`
  FIRST (before the `settlement is None` early return) — counts every agent's turn.
- Add the same guard `if _market_closed(state): return _state_snapshot(state)` to the 4 phase-3 swap
  handlers (`app.py:437,452,501,602`) so nothing leaks past 100.

### Fix 3 — rollout.log updates live
- In `run_transactional.sh` (and `run_paper_config_phase.sh`), just before the collector call,
  background a `tail -F` of the newest `data/ng_run/*/channel.jsonl` into rollout.log; kill it after.
  Clean once Fix 1 leaves one session per rollout.

### Optional — cap the infinite ClientOSError retry
- `nemo_gym/server_utils.py:191-202`: the `ClientOSError`/`ServerDisconnectedError` branches loop
  forever (never check `MAX_NUM_TRIES`). Add the cap.

## Experimental change reverted
During debugging, `server_utils.py:114` was set to `ClientTimeout(total=600, sock_connect=15, sock_read=120)`.
The `sock_read=120` fixed the focal stall but made the long `/run` call time out every 120s → it made
the re-launch much worse. Reverted to the committed baseline `ClientTimeout()` for the phase-1 run.

## Decision (2026-06-18)
Run **C9 Opus-4.8 phase 1** on the no-timeout baseline — the proven config that produced all phase 1–3
data for every model, including the slow ones. Apply the 3 fixes above only when running phase 4/5
(settlement), where the stall and re-launch actually bite.
