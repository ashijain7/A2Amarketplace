# Diagnostic prompt: gemini-focal run hangs indefinitely in NeMo Gym

> Self-contained problem report. Hand this to a colleague / maintainer / AI for diagnosis.
> Paths are absolute on the machine where this reproduces.

## TL;DR

We run a multi-agent marketplace simulation on **NeMo Gym** (`/Users/ashi.jain/Documents/nemo_gym_lib`),
driven by the project at `/Users/ashi.jain/Documents/project_deal`. The "focal" agent's model is served
by NeMo Gym's policy-model server and called over **OpenRouter**. When the focal model is
**`google/gemini-3.1-pro-preview`**, a run **freezes permanently** during the later (settlement) phase:
every process drops to **0% CPU**, nothing is written for 8–10+ minutes, no error is logged, and it
never recovers. The same gemini-pro model used as a *background opponent* is fine, and
**`google/gemini-3.5-flash`** as the focal is fine. We believe a focal model call to OpenRouter
**silently stalls** (connection stays open, no bytes ever return) and the NeMo Gym HTTP client has
**no timeout**, so it blocks forever. We want help confirming the root cause and the best fix.

## System / request flow

- Orchestrator: `ng_collect_rollouts` runs 5 rollouts concurrently.
- Each rollout: `marketplace_agent` (NeMo Gym `simple_agent`, responses-API style) drives a focal agent.
  Per focal turn it **synchronously** POSTs to the **policy-model server** (`openai_model`).
- The policy-model server calls the upstream model over OpenRouter using NeMo Gym's own async HTTP client:
  `simple_agent` → `openai_model` server → `NeMoGymAsyncOpenAI` → `request()` → a **global aiohttp
  `ClientSession`** → OpenRouter → `gemini-3.1-pro-preview`.
- Because the rollout waits on each focal turn and the 5 rollouts share the one collector, **one stuck
  focal call freezes the whole run**.

Key files (in `nemo_gym_lib`):
- `nemo_gym/server_utils.py:109-115` — the global aiohttp session is built with `timeout=ClientTimeout()`.
  **`ClientTimeout()` with no args = `total=None` = no timeout.** ← prime suspect.
- `nemo_gym/server_utils.py:163` — `async def request(...)`: a `while True` retry loop that catches
  `ServerDisconnectedError`, `ClientOSError`, and a catch-all `except Exception` (retries up to
  `MAX_NUM_TRIES = 3`, `server_utils.py:149`, then re-raises). **It retries on raised exceptions —
  but a no-timeout request never raises, it just blocks.**
- `nemo_gym/openai_utils.py:468` — `NeMoGymAsyncOpenAI` (aiohttp wrapper). Its `_request_with_retry`
  only retries on HTTP **status codes** `RETRY_ERROR_CODES = [429,500,502,503,504,520]`. A silent hang
  returns no status, so this layer can't retry it either.
- `responses_api_models/openai_model/app.py:57` — constructs `NeMoGymAsyncOpenAI(base_url, api_key,
  default_headers)` with **no timeout** argument.

Contrast — the path that does NOT hang: the 9 background *opponents* are called by our own code
(`project_deal/marketplace/llm.py::call_llm`) via the OpenAI SDK with **`timeout=90.0` + retry**, so a
hung opponent call self-heals. Only the focal/policy path lacks a timeout.

## Symptom (exact observations)

- Focal = `gemini-3.1-pro-preview`. Hang occurs in the **settlement phase** (focal making payment turns),
  ~25 min into the run, after the public marketplace phase completed.
- Signature: all run processes (`ng_run`, `openai_model`, `simple_agent`, `marketplace`,
  `ng_collect_rollouts`) at **0.0% CPU** (blocked on I/O, not computing). No new file writes anywhere
  in the working dir. **No error or traceback** in any log.
- Observed twice on the same config: frozen ~9 min and ~8.5 min before we killed it; **never recovered**.
- Distinct from normal slowness: gemini-pro-focal also has *recoverable* slow bursts (no writes for
  ~3–6 min, then resumes). The permanent hang is >8 min with zero recovery.

## What we tried / ruled out

1. **Direct OpenRouter test of gemini-pro** (chat-completions API, our own client, 90s cutoff,
   15 calls, 5 concurrent): **15/15 OK, latency 6s/7s/11s (min/median/max), 0 hangs.** → gemini-pro is
   normally fast and reliable; the hang is **rare/transient** and did **not** reproduce in this isolated test.
2. **Model-as-opponent vs model-as-focal:** gemini-pro as *opponent* (configs C4/C6) ran clean
   (opponent path has the 90s timeout). gemini-pro as *focal* (C7) hung twice. → the difference is the
   **focal/policy path's missing timeout**, not the model itself.
3. **gemini-flash focal** (config C8): ran to completion, 0 issues, including settlement. → a faster
   model doesn't trigger it (or triggers it far less).
4. **Confirmed the no-timeout** by reading `server_utils.py:114` (`ClientTimeout()` → `total=None`).

## Root-cause hypothesis

A focal call to OpenRouter for gemini-pro occasionally **half-opens**: the TCP connection stays up but
no response bytes ever arrive (gemini stuck mid-generation, a dropped path through OpenRouter's proxy,
or upstream timing out without sending an error). With **no request timeout** on the shared aiohttp
session, the `await` in `request()` blocks indefinitely — and since it never *raises*, the existing
3-try retry loop never fires. The synchronous rollout (and the whole 5-rollout collector) freezes behind it.

## Other things it could be (please consider)

1. **Responses-API path specifics** — our isolated test used chat-completions; the real focal uses the
   responses API through the policy server. The hang may be specific to that path or to streaming.
2. **Connection-pool / keep-alive** — the session uses one shared `TCPConnector` (`server_utils.py:109`)
   with `limit`/`limit_per_host`. Over a long run, a stale **half-open keep-alive connection** reused from
   the pool could hang on the next request. (Would explain why it only appears after ~25 min of load.)
3. **OpenRouter throttling/queueing** of gemini-pro under sustained concurrent load → multi-minute waits
   that, with no timeout, look like hangs.
4. **asyncio concurrency** — `openai_model/app.py` wraps calls in an `asyncio.Semaphore`
   (`max_concurrent_requests`). A hung request holding a permit shouldn't block *itself*, but is worth
   confirming it doesn't deadlock siblings.

## Candidate fix (untested in-run; declined for now pending review)

`nemo_gym/server_utils.py:114`: `timeout=ClientTimeout()` → `timeout=ClientTimeout(total=120)`.
A stalled call then raises `TimeoutError` after 120s, the existing `request()` catch-all retries it
(`MAX_NUM_TRIES=3`), and the rollout continues — no whole-run freeze, no lost progress. We measured
normal gemini calls at ~7–11s, so 120s never cuts off a legitimate response. (A `sock_read` timeout was
considered but risks killing long single-shot generations; `total` is safer for non-streaming.)

## Questions that would help most

1. Is the block in the request **send** or the response **read**? (Needs instrumentation around the
   `await client.request(...)` in `server_utils.py:163`.)
2. Is it the **responses-API** path specifically, or any request through the global session?
3. Is it a **stale-pooled-connection** issue? (Does forcing a fresh connection / disabling keep-alive,
   or a `sock_read` timeout, avoid it?)
4. Is `total=120` the right knob, or should NeMo Gym set a sane default `ClientTimeout` for *all* external
   model calls (the no-timeout default seems like a latent bug regardless)?
5. Why gemini-pro but not flash — purely latency/load, or a streaming/content difference upstream?

## Environment

- Project: `/Users/ashi.jain/Documents/project_deal` ; NeMo Gym: `/Users/ashi.jain/Documents/nemo_gym_lib`
  (editable install). macOS (darwin). Provider: OpenRouter.
- Focal that hangs: `google/gemini-3.1-pro-preview`. Fine: `google/gemini-3.5-flash` (focal),
  gemini-pro (opponent). Opponents in the hung config: `openai/gpt-5.5`.
