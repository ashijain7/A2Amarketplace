# Resumable Focal Driver — Design Spec

- **Date:** 2026-06-18
- **Status:** Draft — awaiting user review
- **Owner:** Project Deal

## 1. Problem

The gemini-focal configs (C5, C7) cannot complete on NeMo Gym. The focal model
(`gemini-3.1-pro-preview`) stalls under concurrent load, and — more fundamentally —
when a rollout is interrupted, **it cannot resume mid-rollout**: it restarts from turn 0.
The focal's conversation lives only in NeMo Gym's memory and is never written to disk
until a rollout fully completes, so an interrupted rollout's progress is lost.

Today's symptoms (observed this session): repeated multi-minute stalls, 0/5 rollouts
finishing after ~50 min, ~$442 burned on runs that produced no usable data.

## 2. Goal

A **custom driver** that runs the focal agent loop ourselves — calling the marketplace's
tool functions directly, in-process — and **checkpoints state after every turn**, so a
rollout that stalls or stops at turn N can **resume from turn N** and run to completion.

Primary goal: **mid-rollout (turn-level) resume.**
Secondary goals it also delivers: eliminates the focal hang at its source (direct
OpenRouter call with a timeout, like the opponents already use), and removes the
concurrency-stall problem.

**Constraint:** the driver must reproduce C7/C5 faithfully — same marketplace, prompts,
tools, opponents, settlement, scoring, models — so results stay comparable/poolable with
the configs already run through NeMo Gym (C1/C4/C6/C8). The focal is a stochastic model,
so "reproduce" means *same methodology / comparable distribution*, not identical numbers.

## 3. Why this is feasible (verified)

- **Tools are already pure functions.** Every marketplace action is `_apply_<tool>(state, body) -> dict`
  in `resources_server/app.py` (e.g. `_apply_post_listing`, `_apply_make_offer`, `_apply_pay`,
  `_apply_say_in_room`). The HTTP endpoints are thin wrappers. The driver calls these directly.
- **Opponents are stateless.** `OpponentRunner.run_one_turn` rebuilds context from the channel
  each turn (`_format_channel_view(channel=...)` → `call_llm`). They carry **no memory** — nothing
  to serialize; on resume they re-read the channel.
- **Most state already persists to disk continuously:** `channel.jsonl` (all events/messages),
  `deals.json` (ledger), `settlement.json` (settlement state). `prompts` rebuild from `personas`.
- **The opponent path is the proven template.** `marketplace/llm.py::call_llm` already calls
  OpenRouter directly with `timeout=90` + retry, and **opponents never hang.** We apply the same
  pattern to the focal.

What is **not** yet persisted, and is all the driver must add to checkpoint:
1. The **focal's conversation** (the driver owns it).
2. A few **scalar counters** on `MarketplaceState`: `_turn`, `public_steps`, `_focal_lookups`, `phase`.

## 4. Architecture

The driver replaces exactly two NeMo Gym pieces — the **policy-model server** and the
**`simple_agent` focal loop**. Everything else is existing project code, called in-process.

```
                 ┌─────────────────────── custom driver (new) ───────────────────────┐
  focal model    │  focal loop:                                                       │
  (OpenRouter) ◀─┼─  call_focal(messages, tools)   ← direct OpenRouter call + timeout │
                 │  parse tool calls                                                  │
  marketplace  ◀─┼─  _apply_<tool>(state, body)     ← in-process, existing functions  │
  mechanics      │  run opponents                   ← OpponentRunner, existing        │
  (existing)     │  checkpoint(focal_messages, counters)  ← new, tiny, every turn     │
                 │  settlement phase / review+scoring     ← existing, judge = qwen    │
                 └────────────────────────────────────────────────────────────────────┘
```

- **No NeMo Gym, no policy server, no `simple_agent`, no HTTP for the focal.**
- `MarketplaceState`, `OpponentRunner`, settlement, and scoring are imported and called directly.

## 5. The focal loop (behavior)

```
state = build_or_resume_state(config, set, data_dir)   # fresh or reloaded
messages = state's focal conversation (system prompt + history so far)
while not done and state.public/turn caps not exceeded:
    resp = call_focal(focal_model, messages, focal_tools)   # direct OpenRouter, timeout+retry
    for tool_call in resp.tool_calls:
        result = _apply_<tool_call.name>(state, parsed_body)
        messages += [assistant tool_call, tool result]
    run_opponents(state)                                    # rebuilds from channel
    checkpoint(state, messages)                             # save counters + focal conversation
    done = focal signalled done / hit max_steps
settlement_phase(state)        # focal payment turns (existing settlement code)
review_and_score(state)        # existing rubric scoring, judge = qwen
write rollout result to rollouts.jsonl
```

The focal system prompt and tool schemas are **reused verbatim** from the existing
task files (`tasks/settlement_<config>_p2.jsonl` → `responses_create_params`) and the
tool catalog (`resources_server/configs/marketplace.yaml`), so the focal sees exactly
what it saw under NeMo Gym.

## 6. Checkpoint & resume design

**Checkpoint (after every focal turn)** — write one small file per rollout,
`data/<run>/<rollout>/driver_checkpoint.json`:
```json
{ "focal_messages": [...], "turn": 45, "public_steps": 12,
  "focal_lookups": [...], "phase": 2, "settlement_started": false }
```
`channel.jsonl`, `deals.json`, `settlement.json` are already written continuously by the
existing code, so the checkpoint only holds what isn't already on disk. Writes are
atomic (write temp + rename) so a crash mid-write can't corrupt the checkpoint.

**Resume** — on start, if `driver_checkpoint.json` exists for a rollout:
1. Build `MarketplaceState` **without clearing** channel/ledger (`__post_init__` currently
   calls `channel.clear()` / `ledger.clear()` — add a `resume=True` path that skips the clears
   and instead reloads `channel.jsonl` + `deals.json`).
2. Restore settlement from `settlement.json`.
3. Restore counters (`_turn`, `public_steps`, `_focal_lookups`, `phase`) from the checkpoint.
4. Restore `messages` from the checkpoint.
5. Continue the loop from `turn`.

**Rollout-level resume too:** rollouts already written to `rollouts.jsonl` are skipped
(don't re-run). So a re-run resumes both *across* rollouts (skip finished ones) and
*within* the unfinished one (continue from its last turn).

## 7. Key decisions

- **Focal API / request shape:** reproduce NeMo Gym faithfully — same prompt, same tool
  schemas, same request params as the task file's `responses_create_params` — issued as a
  direct OpenRouter call wrapped with a timeout + retry (mirroring `call_llm`). Equivalence
  is verified in §8; if a format difference changes behavior, adjust to match.
- **Timeout:** per-focal-call timeout (start at 120s like the opponents' 90s, tunable),
  with retry. A stalled call raises and retries instead of freezing.
- **Concurrency:** driver runs one rollout per process; parallelism is achieved by running
  N driver processes (or an outer loop). Stable models (Opus/Sonnet) can run many in parallel;
  flaky preview endpoints (gemini-pro) can be throttled — independent of resume.
- **Scope of the artifact:** the spec covers the **full pipeline** (negotiation + settlement +
  review/scoring) because C7/C5 need all three. Implementation is **phased** (see §9).

## 8. Equivalence / validation plan

Before trusting the driver on the expensive C7/C5 runs, validate it against a config that
**already has NeMo Gym results**:

- **Validation target: C8 (`gemini-3.5-flash`)** — cheap, already completed on NeMo Gym
  (baseline exists), doesn't hang, and is gemini-focal like C7.
- Run C8 through the custom driver and compare to the existing NeMo Gym C8 results on:
  behavior (tool-call mix, deal/settlement outcomes) and rubric score distributions.
- Acceptance: distributions and behavior are consistent with the NeMo Gym baseline
  (not identical — stochastic — but comparable). Spot-check transcripts read sensibly.
- Separately, verify **resume correctness**: kill a rollout mid-way, resume it, and confirm
  it continues coherently from the saved turn and completes.

## 9. Phased implementation (for the plan, not extra scope)

1. **Negotiation loop + checkpoint/resume** — focal loop (phase-2 marketplace), opponents,
   per-turn checkpoint, resume-from-turn. Validate resume correctness on a cheap model.
2. **Settlement phase** — wire existing settlement (payment turns, scammer, rooms) into the loop.
3. **Review + scoring** — wire existing rubric scoring (judge = qwen), write `rollouts.jsonl`
   in the same shape the aggregation scripts expect.
4. **Equivalence run** — full C8-flash run through the driver, compare to NeMo Gym baseline (§8).
5. **C7 / C5** — run the real gemini-pro configs.

## 10. Risks & mitigations

- **Subtle divergence from NeMo Gym** (different prompt/tool formatting changes focal behavior)
  → reuse prompts/tools verbatim; gate on the C8 equivalence check before real runs.
- **`MarketplaceState` rebuild on resume** (the `__post_init__` clears) → add an explicit
  `resume` path; cover with a kill/resume test.
- **Settlement state round-trip** (verify `settlement.json` fully restores) → test resume
  across a settlement-phase boundary specifically.
- **Output shape mismatch** (aggregation scripts expect NeMo Gym's `rollouts.jsonl` shape)
  → emit the same schema; run the existing `settlement_aggregate.py` / `settlement_validate.py`
  against driver output as a check.

## 11. Out of scope (YAGNI)

- Phase-3 (swap) mechanics — C7/C5 are phase-2.
- A general-purpose NeMo Gym replacement — this drives *only* the marketplace focal loop.
- Re-running configs that already completed on NeMo Gym (C1/C4/C6/C8/C9) — only C7/C5 need this.
- Distributed/remote execution — local processes are sufficient.
