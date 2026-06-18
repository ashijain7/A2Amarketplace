# Resumable Focal Driver — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an in-process driver that runs the marketplace focal loop directly against OpenRouter (with a timeout) and checkpoints every turn, so a rollout that stalls/stops at turn N resumes from turn N — reproducing C7/C5 faithfully without NeMo Gym.

**Architecture:** A new `driver/` package replaces NeMo Gym's `simple_agent` + policy server only. It calls the focal model directly (OpenRouter Responses API + timeout + retry), runs the existing marketplace tool functions in-process (`_apply_*(state, body)`), lets the existing stateless `OpponentRunner` respond, and checkpoints the focal conversation + counters each turn. Settlement and scoring reuse existing code. Everything except the focal call/loop is unchanged project code.

**Tech Stack:** Python 3.12, the OpenAI SDK pointed at OpenRouter (same as `marketplace/llm.py`), existing `resources_server` modules imported in-process.

## Global Constraints

- **No test files.** Verify via smoke checks + real runs (project rule). Do NOT create `tests/` or pytest files; each task's verification is a one-off command whose output you inspect, then delete any scratch file.
- **No new dependencies** beyond what `marketplace/llm.py` already uses (openai SDK, orjson/json).
- **Reproduce, don't reinvent:** reuse the focal system prompt + tool schemas verbatim from the task file `responses_create_params`; reuse `_apply_*`, `OpponentRunner`, `Settlement`, and `_verify_for_state` unchanged.
- **Focal model call:** direct to OpenRouter `/responses`, `timeout≈120s` + retry (mirrors the opponents' `call_llm` timeout=90 pattern in `marketplace/llm.py`).
- **Output shape:** emit `rollouts.jsonl` records in the exact existing shape (see Task 8) so `scripts/settlement_aggregate.py` / `settlement_validate.py` work unchanged.
- **Commit after every task.** Branch: `project_deal` (already on it).

## File Structure

```
driver/
  __init__.py            # package marker
  focal_client.py        # Task 1 — direct OpenRouter Responses-API call (timeout+retry)
  state_build.py         # Task 2 (fresh) + Task 5 (resume) — build/reload MarketplaceState in-process
  checkpoint.py          # Task 4 — atomic save/load of {focal_messages, counters}
  focal_loop.py          # Task 3 (negotiation) + Task 6 (settlement) — the turn loop
  score_and_emit.py      # Task 7 — _verify_for_state + build rollouts.jsonl record
  run_rollout.py         # Task 8 — one rollout end-to-end with resume
  run_driver.py          # Task 8 — CLI over a task file, rollout-level resume, aggregation
```
Modified: `resources_server/app.py` (Task 5 — add a `resume` path to `MarketplaceState`).

---

### Task 1: Focal client — direct OpenRouter Responses call with timeout

**Files:**
- Create: `driver/__init__.py` (empty)
- Create: `driver/focal_client.py`

**Interfaces:**
- Produces: `call_focal(model: str, input_items: list[dict], tools: list[dict], *, timeout: float = 120.0, max_retries: int = 3) -> dict` — returns the parsed Responses-API response dict (has key `"output"`: list of items, and `"usage"`). Raises after retries exhausted.

- [ ] **Step 1: Implement the focal client**

```python
# driver/focal_client.py
"""Direct OpenRouter Responses-API call for the focal — the driver's replacement
for NeMo Gym's policy server. Mirrors marketplace/llm.py: OpenAI SDK pointed at
OpenRouter, with a real timeout + retry (the missing timeout was the hang)."""
import os, time
from openai import OpenAI, APITimeoutError, APIConnectionError, APIStatusError

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

RETRY_STATUS = {429, 500, 502, 503, 504, 520}

def call_focal(model, input_items, tools, *, timeout=120.0, max_retries=3):
    last = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = _client.responses.create(
                model=model, input=input_items, tools=tools, timeout=timeout,
            )
            return resp.model_dump()
        except (APITimeoutError, APIConnectionError) as e:
            last = e
            print(f"[focal_client] {type(e).__name__} try {attempt}/{max_retries}; retrying", flush=True)
            time.sleep(1.0)
        except APIStatusError as e:
            if e.status_code in RETRY_STATUS and attempt < max_retries:
                last = e
                print(f"[focal_client] HTTP {e.status_code} try {attempt}/{max_retries}; retrying", flush=True)
                time.sleep(1.0)
            else:
                raise
    raise last
```

- [ ] **Step 2: Smoke-verify it calls OpenRouter and returns tool-callable output**

Run (uses a cheap model + a trivial tool; confirms the Responses API path works through OpenRouter):
```bash
cd /Users/ashi.jain/Documents/project_deal
set -a; source .env; set +a
.venv/bin/python -c "
from driver.focal_client import call_focal
tools=[{'type':'function','name':'ping','description':'say pong','parameters':{'type':'object','properties':{},'required':[]},'strict':True}]
r=call_focal('google/gemini-3.5-flash',[{'role':'user','content':'Call the ping tool.'}],tools,timeout=60)
print('output types:',[o.get('type') for o in r['output']])
"
```
Expected: prints `output types: [...]` including `function_call` (or a message) — i.e. a valid Responses-API response came back. If OpenRouter's `/responses` rejects the request, fall back to chat-completions tool-calling here and adjust Task 3's parsing accordingly (note it in the file docstring).

- [ ] **Step 3: Commit**
```bash
git add driver/__init__.py driver/focal_client.py
git commit -m "driver: focal client (direct OpenRouter responses + timeout)"
```

---

### Task 2: Build a fresh MarketplaceState in-process

**Files:**
- Create: `driver/state_build.py`
- Reference: `resources_server/app.py:995-1036` (seed_session) and `:40-95` (MarketplaceState + __post_init__)

**Interfaces:**
- Produces: `build_state(task: dict, data_dir: Path) -> MarketplaceState` — `task` is one parsed line from a `tasks/settlement_*_p2.jsonl` file (has `metadata` with focal_persona, config_name, set_id, seed, phase, personas_path). Builds a fresh state (channel/ledger cleared by `__post_init__`).
- Consumes: `get_model_config` (`resources_server/model_config.py`), `MarketplaceState` (`resources_server/app.py`).

- [ ] **Step 1: Read the seed_session bootstrap to copy its exact construction**

Run: `sed -n '995,1040p' resources_server/app.py` — confirm the arg sources (personas loaded from `metadata.personas_path`; models from `get_model_config(config_name)`; `judge_model` from `MarketplaceState`/env; `phase`, `seed`, `set_id`, `focal_name`). Note the exact `MarketplaceState(...)` call (mapped: `focal_name, personas, opponents_model, focal_model, judge_model, seed, set_id, config_name, data_dir, phase`).

- [ ] **Step 2: Implement build_state**

```python
# driver/state_build.py
"""Build (or, in Task 5, resume) a MarketplaceState in-process — the driver's
replacement for seed_session. Mirrors resources_server/app.py seed_session."""
import json
from pathlib import Path
from resources_server.app import MarketplaceState
from resources_server.model_config import get_model_config

def build_state(task: dict, data_dir: Path) -> MarketplaceState:
    meta = task["metadata"]
    with open(meta["personas_path"]) as f:
        personas = json.load(f)
    cfg = get_model_config(meta["config_name"])
    return MarketplaceState(
        focal_name=meta["focal_persona"],
        personas=personas,
        opponents_model=cfg["opponents_model"],
        focal_model=cfg["focal_model"],
        judge_model=MarketplaceState.JUDGE_MODEL,   # confirm attr name in Step 1
        seed=meta.get("seed", 0),
        set_id=meta.get("set_id", ""),
        config_name=meta["config_name"],
        data_dir=Path(data_dir),
        phase=int(meta.get("phase", 2)),
    )
```
(If `judge_model` is sourced from env/`env.yaml` rather than a class attr, use that source — confirmed in Step 1.)

- [ ] **Step 3: Smoke-verify a state builds with channel/ledger/runner/settlement**

```bash
cd /Users/ashi.jain/Documents/project_deal; set -a; source .env; set +a
export ENABLE_SETTLEMENT=yes MARKETPLACE_PHASE=2
.venv/bin/python -c "
import json,tempfile
from pathlib import Path
from driver.state_build import build_state
task=json.loads(open('tasks/settlement_focal_G35_vs_X_p2.jsonl').readline())  # generate first if missing
s=build_state(task, Path(tempfile.mkdtemp()))
print('focal:',s.focal_name,'| has channel:',s.channel is not None,'| runner:',s.runner is not None,'| settlement:',getattr(s,'settlement',None) is not None)
"
```
Expected: prints focal name and `True` for channel/runner/settlement. (Generate the task file first if needed: `.venv/bin/python tasks/generate_tasks.py --phase 2 --config focal_G35_vs_X --focal-count 1 --seeds 42 --out tasks/settlement_focal_G35_vs_X_p2.jsonl`.)

- [ ] **Step 4: Commit**
```bash
git add driver/state_build.py
git commit -m "driver: build MarketplaceState in-process"
```

---

### Task 3: Negotiation focal loop (tools in-process + opponents)

**Files:**
- Create: `driver/focal_loop.py`
- Reference: `nemo_gym_lib/responses_api_agents/simple_agent/app.py:83-166` (loop to replicate), `resources_server/app.py:330-674` (`_apply_*` functions), `resources_server/opponent_runner.py` (`run_n_turns`).

**Interfaces:**
- Produces: `run_focal_loop(state, messages: list[dict], tools: list[dict], *, max_steps: int, on_turn=None) -> list[dict]` — runs the focal↔opponent loop until done/max_steps; returns the final `messages`. `on_turn(state, messages, turn)` is called after each focal turn (used for checkpointing in Task 4/5).
- Consumes: `call_focal` (Task 1), `build_state` (Task 2).

- [ ] **Step 1: Map tool name → `_apply_*` function**

Run: `grep -nE "^def _apply_" resources_server/app.py` and the endpoint wrappers (`do_pass` etc., ~line 710+). Build a dispatch dict matching the tool names in `marketplace.yaml` to the `_apply_*` functions and their Body pydantic models (`PostListingBody`, `MakeOfferBody`, … and the settlement `_apply_*` which take `(state, payload_dict)`).

- [ ] **Step 2: Implement the loop (negotiation tools)**

```python
# driver/focal_loop.py
"""The focal turn loop — replaces simple_agent. Calls the focal directly, runs its
tool calls in-process via _apply_*, then lets opponents respond (stateless, rebuilt
from the channel)."""
import json
from driver.focal_client import call_focal
from resources_server import app as M  # _apply_* live here

# tool name -> (apply_fn, body_model_or_None). Settlement entries (body_model None)
# pass the raw dict. Confirm the exact set in Step 1.
DISPATCH = {
    "post_listing":  (M._apply_post_listing,  M.PostListingBody),
    "make_offer":    (M._apply_make_offer,    M.MakeOfferBody),
    "counter_offer": (M._apply_counter_offer, M.CounterOfferBody),
    "accept_offer":  (M._apply_accept_offer,  M.AcceptOfferBody),
    "reject_offer":  (M._apply_reject_offer,  M.RejectOfferBody),
    "pass":          (M._apply_pass,          M.PassBody),
    "lookup_agent":  (M._apply_lookup_agent,  M.LookupAgentBody),
    # settlement tools added in Task 6
}

def _run_tool(state, name, args: dict) -> dict:
    fn, body_model = DISPATCH[name]
    return fn(state, body_model(**args)) if body_model else fn(state, args)

def run_focal_loop(state, messages, tools, *, max_steps, on_turn=None):
    step = state._turn  # resume-aware: continue from saved turn
    while True:
        step += 1
        resp = call_focal(state.focal_model, messages, tools)
        output = resp["output"]
        fn_calls = [o for o in output if o.get("type") == "function_call"]
        out_msgs = [o for o in output if o.get("type") == "message" and o.get("role") == "assistant"]
        messages = messages + output
        for fc in fn_calls:
            args = json.loads(fc["arguments"])
            result = _run_tool(state, fc["name"], args)
            messages.append({"type": "function_call_output",
                             "call_id": fc["call_id"], "output": json.dumps(result)})
        state.runner.run_n_turns(n=<opponents_per_round>, starting_turn=state._turn)  # confirm signature in Step 1
        state._turn = step
        if on_turn:
            on_turn(state, messages, step)
        if (not fn_calls and out_msgs) or step >= max_steps:
            break
    return messages
```
(`<opponents_per_round>` and `run_n_turns`' exact signature/args come from `opponent_runner.py` — confirm in Step 1; in NeMo Gym the resources server called the runner once per focal action. Match that cadence.)

- [ ] **Step 3: Smoke-verify a few negotiation turns run and the channel grows**

```bash
cd /Users/ashi.jain/Documents/project_deal; set -a; source .env; set +a
export ENABLE_SETTLEMENT=yes MARKETPLACE_PHASE=2
.venv/bin/python -c "
import json,tempfile; from pathlib import Path
from driver.state_build import build_state; from driver.focal_loop import run_focal_loop
task=json.loads(open('tasks/settlement_focal_G35_vs_X_p2.jsonl').readline())
d=Path(tempfile.mkdtemp()); s=build_state(task,d)
rcp=task['responses_create_params']
msgs=run_focal_loop(s, list(rcp['input']), rcp['tools'], max_steps=6)
print('focal turns:',s._turn,'| channel events:',len(s.channel.events))
"
```
Expected: `focal turns: 6` (or fewer if done early) and `channel events: > 0`. Use `gemini-3.5-flash` focal (cheap) — it's already in the G35 config.

- [ ] **Step 4: Commit**
```bash
git add driver/focal_loop.py
git commit -m "driver: negotiation focal loop (in-process tools + opponents)"
```

---

### Task 4: Checkpoint — atomic save/load of focal conversation + counters

**Files:**
- Create: `driver/checkpoint.py`

**Interfaces:**
- Produces: `save_checkpoint(data_dir: Path, messages: list[dict], state) -> None` and `load_checkpoint(data_dir: Path) -> dict | None` (returns `{"messages":..., "turn":..., "public_steps":..., "focal_lookups":..., "phase":...}` or None).

- [ ] **Step 1: Implement atomic checkpoint**

```python
# driver/checkpoint.py
"""Per-turn checkpoint: the only state not already on disk (channel/deals/settlement
write themselves). Atomic via temp+rename so a crash mid-write can't corrupt it."""
import json, os
from pathlib import Path

def save_checkpoint(data_dir: Path, messages, state) -> None:
    data_dir = Path(data_dir)
    payload = {"messages": messages, "turn": state._turn,
               "public_steps": state.public_steps,
               "focal_lookups": state._focal_lookups, "phase": state.phase}
    tmp = data_dir / "driver_checkpoint.json.tmp"
    tmp.write_text(json.dumps(payload))
    os.replace(tmp, data_dir / "driver_checkpoint.json")

def load_checkpoint(data_dir: Path):
    p = Path(data_dir) / "driver_checkpoint.json"
    return json.loads(p.read_text()) if p.exists() else None
```

- [ ] **Step 2: Smoke-verify round-trip**
```bash
cd /Users/ashi.jain/Documents/project_deal
.venv/bin/python -c "
import tempfile; from pathlib import Path
from driver.checkpoint import save_checkpoint, load_checkpoint
class S: _turn=45; public_steps=12; _focal_lookups=['a']; phase=2
d=Path(tempfile.mkdtemp()); save_checkpoint(d,[{'role':'user','content':'hi'}],S())
c=load_checkpoint(d); print('turn:',c['turn'],'msgs:',len(c['messages']),'lookups:',c['focal_lookups'])
"
```
Expected: `turn: 45 msgs: 1 lookups: ['a']`.

- [ ] **Step 3: Commit**
```bash
git add driver/checkpoint.py
git commit -m "driver: atomic per-turn checkpoint"
```

---

### Task 5: Resume — reload state from disk + checkpoint, continue from turn N

**Files:**
- Modify: `resources_server/app.py` (`MarketplaceState.__post_init__`, ~line 69-95) — add resume support
- Modify: `driver/state_build.py` — add `resume_state(task, data_dir)`
- Reference: `resources_server/channel.py` + ledger for their load methods

**Interfaces:**
- Produces: `resume_state(task: dict, data_dir: Path) -> tuple[MarketplaceState, list[dict]]` — rebuilds state WITHOUT clearing, reloads channel/ledger/settlement + counters from disk, returns `(state, messages)`.

- [ ] **Step 1: Inspect how Channel/Ledger load existing data**

Run: `grep -nE "class Channel|def clear|def load|def read|self.events|append" resources_server/channel.py` and the ledger module. Determine how to repopulate `channel.events` and the ledger from the existing `channel.jsonl`/`deals.json` (there is likely a read on init, or add a `load()` that reads the jsonl). Note the exact method.

- [ ] **Step 2: Add a `resume` flag to MarketplaceState**

In `resources_server/app.py`, add field `resume: bool = False` to the dataclass and guard the clears in `__post_init__`:
```python
# in __post_init__, replace the unconditional clears:
self.channel = Channel(path=self.data_dir / "channel.jsonl")
if self.resume:
    self.channel.load()      # exact method from Step 1 (reads existing jsonl)
else:
    self.channel.clear()
self.ledger = Ledger(path=self.data_dir / "deals.json")
if self.resume:
    self.ledger.load()       # exact method from Step 1
else:
    self.ledger.clear()
```
(Settlement: if `settlement.json` exists and resume, load it via the Settlement store's existing read — confirm in Step 1; the `save()` at `settlement/state.py:73` implies a paired read.)

- [ ] **Step 3: Add resume_state to driver/state_build.py**

```python
from driver.checkpoint import load_checkpoint

def resume_state(task, data_dir):
    cp = load_checkpoint(data_dir)
    if cp is None:
        return build_state(task, data_dir), list(task["responses_create_params"]["input"])
    meta = task["metadata"]; import json
    with open(meta["personas_path"]) as f: personas = json.load(f)
    cfg = get_model_config(meta["config_name"])
    s = MarketplaceState(focal_name=meta["focal_persona"], personas=personas,
        opponents_model=cfg["opponents_model"], focal_model=cfg["focal_model"],
        judge_model=MarketplaceState.JUDGE_MODEL, seed=meta.get("seed",0),
        set_id=meta.get("set_id",""), config_name=meta["config_name"],
        data_dir=Path(data_dir), phase=int(meta.get("phase",2)), resume=True)
    s._turn = cp["turn"]; s.public_steps = cp["public_steps"]; s._focal_lookups = cp["focal_lookups"]
    return s, cp["messages"]
```

- [ ] **Step 4: Smoke-verify kill + resume continues from the saved turn**

```bash
cd /Users/ashi.jain/Documents/project_deal; set -a; source .env; set +a
export ENABLE_SETTLEMENT=yes MARKETPLACE_PHASE=2
.venv/bin/python -c "
import json,tempfile; from pathlib import Path
from driver.state_build import build_state, resume_state
from driver.focal_loop import run_focal_loop; from driver.checkpoint import save_checkpoint
task=json.loads(open('tasks/settlement_focal_G35_vs_X_p2.jsonl').readline())
d=Path(tempfile.mkdtemp()); s=build_state(task,d); rcp=task['responses_create_params']
m=run_focal_loop(s,list(rcp['input']),rcp['tools'],max_steps=4,on_turn=lambda st,ms,t: save_checkpoint(d,ms,st))
print('stopped at turn',s._turn,'events',len(s.channel.events))
s2,m2=resume_state(task,d)
print('resumed at turn',s2._turn,'reloaded events',len(s2.channel.events))
assert s2._turn==s._turn and len(s2.channel.events)==len(s.channel.events)
print('RESUME OK')
"
```
Expected: `stopped at turn 4 …`, `resumed at turn 4 reloaded events <same>`, `RESUME OK`.

- [ ] **Step 5: Commit**
```bash
git add resources_server/app.py driver/state_build.py
git commit -m "driver: resume MarketplaceState from disk + checkpoint"
```

---

### Task 6: Wire settlement into the loop

**Files:**
- Modify: `driver/focal_loop.py` (extend DISPATCH with settlement tools)
- Reference: `resources_server/app.py:650-675` (settlement `_apply_*`), `resources_server/settlement/__init__.py:61-177`

**Interfaces:**
- Consumes: `_apply_list_payment_methods/_apply_choose_payment_method/_apply_pay/_apply_submit_otp/_apply_confirm_receipt/_apply_get_payment_status/_apply_say_in_room` (all `(state, payload_dict)`).

- [ ] **Step 1: Extend DISPATCH with settlement tools**
```python
DISPATCH.update({
    "list_payment_methods":  (M._apply_list_payment_methods,  None),
    "choose_payment_method": (M._apply_choose_payment_method, None),
    "pay":                   (M._apply_pay,                   None),
    "submit_otp":            (M._apply_submit_otp,            None),
    "confirm_receipt":       (M._apply_confirm_receipt,       None),
    "get_payment_status":    (M._apply_get_payment_status,    None),
    "say_in_room":           (M._apply_say_in_room,           None),
})
```
(Confirm `Settlement` is created on deal-close: per the map, `Settlement.on_deal_closed(deal)` is called by the opponent runner / accept path. Verify `state.settlement` is wired so these `_apply_*` see an initialized settlement — read `app.py:650-675` + `_market_closed` at `:192-203`.)

- [ ] **Step 2: Smoke-verify a deal settles end-to-end (cheap focal)**

Run a longer cheap-model loop (G35 flash, `max_steps=40`, settlement on) and check `settlement.json` is written and has a record advancing past `CHOSE_METHOD`:
```bash
cd /Users/ashi.jain/Documents/project_deal; set -a; source .env; set +a
export ENABLE_SETTLEMENT=yes SETTLEMENT_SCAM=yes MARKETPLACE_PHASE=2
.venv/bin/python -c "
import json,tempfile; from pathlib import Path
from driver.state_build import build_state; from driver.focal_loop import run_focal_loop
task=json.loads(open('tasks/settlement_focal_G35_vs_X_p2.jsonl').readline())
d=Path(tempfile.mkdtemp()); s=build_state(task,d); rcp=task['responses_create_params']
run_focal_loop(s,list(rcp['input']),rcp['tools'],max_steps=40)
recs=s.settlement.store.for_party(s.focal_name)
print('settlement records:',len(recs),'| stages:',[getattr(r,'stage',None) for r in recs])
"
```
Expected: ≥1 settlement record with a non-initial stage. (Behavior is stochastic; re-run if the focal didn't reach a deal.)

- [ ] **Step 3: Commit**
```bash
git add driver/focal_loop.py
git commit -m "driver: settlement tools in the focal loop"
```

---

### Task 7: Score the rollout + build the rollouts.jsonl record

**Files:**
- Create: `driver/score_and_emit.py`
- Reference: `resources_server/app.py:741-848` (`_verify_for_state`), the `rollouts.jsonl` shape (Task 8 header / interface map item 6)

**Interfaces:**
- Produces: `score_and_build_record(state, task: dict, response_output, usage, rollout_id: int) -> dict` — returns one rollouts.jsonl record (exact shape below).

- [ ] **Step 1: Implement scoring + record assembly**

```python
# driver/score_and_emit.py
"""After the loop: run the existing verifier stack and assemble the rollouts.jsonl
record in the exact shape the aggregation scripts expect."""
from resources_server.app import _verify_for_state

def score_and_build_record(state, task, response_output, usage, rollout_id):
    verify = _verify_for_state(state)          # {deal_outcomes, capability_asymmetry, ...}
    settle_records, balances = [], {}
    if getattr(state, "settlement", None) is not None:
        settle_records = [r.__dict__ if hasattr(r, "__dict__") else r
                          for r in state.settlement.store.records.values()]   # confirm accessor
        balances = state.settlement.bank.balances                            # confirm accessor
    return {
        "id": rollout_id,
        "metadata": task["metadata"],
        "responses_create_params": task["responses_create_params"],
        "response": {"output": response_output, "usage": usage},
        "reward": verify.get("final_reward", verify.get("reward")),
        "rubric_scores": verify,
        "channel_events": [e.__dict__ if hasattr(e, "__dict__") else e for e in state.channel.events],
        "deals": [d.__dict__ if hasattr(d, "__dict__") else d for d in state.ledger.deals],
        "settlement_records": settle_records,
        "settlement_balances": balances,
        "personas": state.personas,
    }
```
(Confirm the exact accessors `state.channel.events`, `state.ledger.deals`, `state.settlement.store.records`, `state.settlement.bank.balances`, and `_verify_for_state`'s return keys by reading `app.py:741-848` — match item 6 of the interface map. Serialize dataclasses/pydantic to plain dicts.)

- [ ] **Step 2: Smoke-verify a record scores and the aggregator parses it**

```bash
cd /Users/ashi.jain/Documents/project_deal; set -a; source .env; set +a
export ENABLE_SETTLEMENT=yes MARKETPLACE_PHASE=2
.venv/bin/python -c "
import json,tempfile; from pathlib import Path
from driver.state_build import build_state; from driver.focal_loop import run_focal_loop
from driver.score_and_emit import score_and_build_record
task=json.loads(open('tasks/settlement_focal_G35_vs_X_p2.jsonl').readline())
d=Path(tempfile.mkdtemp()); s=build_state(task,d); rcp=task['responses_create_params']
m=run_focal_loop(s,list(rcp['input']),rcp['tools'],max_steps=30)
rec=score_and_build_record(s,task,m,{},0)
out=d/'rollouts.jsonl'; out.write_text(json.dumps(rec)+'\n')
print('reward:',rec['reward'],'| keys ok:',set(['id','metadata','rubric_scores','channel_events'])<=set(rec))
" && echo "now parse with the aggregator:" && .venv/bin/python scripts/settlement_aggregate.py "$(ls -dt /var/folders/* 2>/dev/null | head -1)/rollouts.jsonl" /tmp/agg_test C9_test 4 on 1 2>&1 | tail -3 || true
```
Expected: prints a `reward:` float and `keys ok: True`. (The aggregator path is illustrative — point it at the temp `rollouts.jsonl` actually written.)

- [ ] **Step 3: Commit**
```bash
git add driver/score_and_emit.py
git commit -m "driver: score rollout + emit rollouts.jsonl record"
```

---

### Task 8: Orchestration — one rollout end-to-end + multi-set driver with resume

**Files:**
- Create: `driver/run_rollout.py`, `driver/run_driver.py`

**Interfaces:**
- Produces: `run_one_rollout(task, out_dir, rollout_id) -> dict` (full lifecycle, resume-aware) and a CLI `python -m driver.run_driver <config> <phase> <scam> <nsets> [parallel]`.

- [ ] **Step 1: Implement run_rollout (build-or-resume → loop → score → emit)**
```python
# driver/run_rollout.py
from pathlib import Path
from driver.state_build import resume_state
from driver.focal_loop import run_focal_loop
from driver.checkpoint import save_checkpoint
from driver.score_and_emit import score_and_build_record

def run_one_rollout(task, data_dir, rollout_id, max_steps=80):
    data_dir = Path(data_dir); data_dir.mkdir(parents=True, exist_ok=True)
    state, messages = resume_state(task, data_dir)   # fresh if no checkpoint
    rcp = task["responses_create_params"]
    messages = run_focal_loop(state, messages, rcp["tools"], max_steps=max_steps,
                              on_turn=lambda st, ms, t: save_checkpoint(data_dir, ms, st))
    return score_and_build_record(state, task, messages, {}, rollout_id)
```

- [ ] **Step 2: Implement run_driver (task file, rollout-level resume, parallelism, aggregation)**

```python
# driver/run_driver.py  — CLI over a task file. Skips rollouts already in rollouts.jsonl
# (rollout-level resume); each rollout checkpoints per-turn (turn-level resume).
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from driver.run_rollout import run_one_rollout

def already_done(out_jsonl: Path) -> set:
    if not out_jsonl.exists(): return set()
    return {json.loads(l)["id"] for l in out_jsonl.read_text().splitlines() if l.strip()}

def main():
    config, phase, scam, nsets = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    parallel = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    cfg_dir = {"focal_G_vs_X":"C7_gemini_vs_gpt55","focal_G_vs_S":"C5_gemini_vs_sonnet",
               "focal_G35_vs_X":"C8_gemini35_vs_gpt55","focal_O_vs_X":"C9_opus48_vs_gpt55"}.get(config, config)
    out_dir = Path(f"results/paper_runs/{cfg_dir}/phase{phase}"); out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = out_dir / "rollouts.jsonl"
    tasks = [json.loads(l) for l in open(f"tasks/settlement_{config}_p2.jsonl")][:nsets]
    done = already_done(out_jsonl)
    todo = [(i, t) for i, t in enumerate(tasks) if i not in done]
    print(f"{len(done)} banked, running {len(todo)} (parallel={parallel})", flush=True)
    def work(item):
        i, t = item
        return run_one_rollout(t, Path("data") / f"driver_{cfg_dir}_{i}", i)
    with ProcessPoolExecutor(max_workers=parallel) as ex:
        for rec in ex.map(work, todo):
            with open(out_jsonl, "a") as f: f.write(json.dumps(rec) + "\n")
            print(f"banked rollout {rec['id']}", flush=True)

if __name__ == "__main__": main()
```
(`ENABLE_SETTLEMENT`/`MARKETPLACE_PHASE`/`SETTLEMENT_SCAM` env are set by a thin wrapper script as today; `max_steps` default 80 matches the existing cap.)

- [ ] **Step 3: Smoke-verify ONE cheap rollout end-to-end + resume across rollouts**
```bash
cd /Users/ashi.jain/Documents/project_deal; set -a; source .env; set +a
export ENABLE_SETTLEMENT=yes SETTLEMENT_SCAM=yes MARKETPLACE_PHASE=2
.venv/bin/python -m driver.run_driver focal_G35_vs_X 4 on 1 1
echo "--- banked? ---"; wc -l results/paper_runs/C8_gemini35_vs_gpt55/phase4/rollouts.jsonl
.venv/bin/python scripts/settlement_validate.py results/paper_runs/C8_gemini35_vs_gpt55/phase4/rollouts.jsonl | tail -5
# re-run: should skip the banked rollout (rollout-level resume)
.venv/bin/python -m driver.run_driver focal_G35_vs_X 4 on 1 1
```
Expected: first run banks `1` rollout, validator passes; the re-run prints `1 banked, running 0`.

- [ ] **Step 4: Commit**
```bash
git add driver/run_rollout.py driver/run_driver.py
git commit -m "driver: rollout orchestration + multi-set driver with resume"
```

---

### Task 9: Equivalence validation against C8 (gemini-flash)

**Files:** none (validation only). Compares driver output to the existing NeMo Gym C8 baseline.

- [ ] **Step 1: Run a full C8-flash set through the driver**
```bash
cd /Users/ashi.jain/Documents/project_deal; set -a; source .env; set +a
export ENABLE_SETTLEMENT=yes SETTLEMENT_SCAM=yes MARKETPLACE_PHASE=2
.venv/bin/python -m driver.run_driver focal_G35_vs_X 4 on 5 5 2>&1 | tee output_driver_c8.log
```

- [ ] **Step 2: Compare to the NeMo Gym C8 baseline**
Compare reward + rubric distributions and tool-call behavior between the driver run and the archived NeMo Gym C8 results (the previously-saved per-set folders / aggregate). Acceptance: comparable distributions and sane transcripts (stochastic, not identical). Record the comparison in `docs/superpowers/` notes.

- [ ] **Step 3: Resume-correctness check** — kill a driver rollout mid-settlement, re-run, confirm it continues from the checkpoint turn and completes; the final record is well-formed.

- [ ] **Step 4: Commit the validation note**
```bash
git add docs/superpowers/driver_c8_validation.md
git commit -m "driver: C8 equivalence + resume validation notes"
```

---

### Task 10: Run C7 and C5 (the real targets)

- [ ] **Step 1:** `python -m driver.run_driver focal_G_vs_X 4 on 5 1` (gemini-pro focal — parallel=1 to be gentle on the preview endpoint; resume covers any stall). Then `focal_G_vs_S` (C5).
- [ ] **Step 2:** Run `settlement_aggregate.py` + `settlement_validate.py` on the outputs; confirm 5/5 banked each.
- [ ] **Step 3:** Report cost (OpenRouter balance delta) and commit results pointers.

---

## Self-Review

**Spec coverage:** §2 goal (turn resume) → Tasks 4,5,8. §3 feasibility (in-process tools, stateless opponents, on-disk channel) → Tasks 2,3,5. §4 architecture → Tasks 1,3. §5 loop → Task 3. §6 checkpoint/resume → Tasks 4,5. §7 decisions (Responses API, timeout, concurrency) → Tasks 1,8. §8 validation (C8 + resume test) → Task 9. §9 phasing → Task order. §10 risks → covered by Step-1 inspections in Tasks 3,5,6,7 and the Task 9 gate. §11 out-of-scope respected (phase-2 only, local processes). No gaps.

**Placeholder scan:** No "TBD/TODO". The few `<...>`/"confirm in Step 1" notes are explicit *inspect-the-named-file* steps (Channel/Ledger load method, `run_n_turns` signature, settlement accessors) — real instructions with the exact file:line to read, not vague hand-waves, because those internals weren't read during planning.

**Type consistency:** `build_state`/`resume_state` return the same `MarketplaceState`; `run_focal_loop(state, messages, tools, *, max_steps, on_turn)` signature is consistent across Tasks 3,5,8; `save_checkpoint(data_dir, messages, state)` / `load_checkpoint(data_dir)` consistent in Tasks 4,5,8; `score_and_build_record(state, task, output, usage, id)` consistent in Tasks 7,8.
