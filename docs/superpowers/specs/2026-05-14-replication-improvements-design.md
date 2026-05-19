# Replication Improvements — Design Spec
Date: 2026-05-14

## Overview

Eight improvements to the Project Deal POC replication. No new features (no rubrics, reputation layer, or multi-model experiments). Scope is strictly improving the quality and correctness of the existing simulation.

---

## Improvement 1 — Full channel history in agent context

**Problem:** Each agent sees only the last 8 channel events globally. With 10 agents, a negotiation that starts at turn 5 can fall out of the window by turn 16. Agents lose track of their own negotiations and reference wrong event IDs.

**Fix:** Replace `channel.recent(8)` in `agent.py/_format_channel_view` with all non-pass events from the channel. The "RECENT MESSAGES IN CHANNEL" section shows every listing, offer, counter, accept, and decline — in order, oldest to newest. Pass events (`psh_` prefix) are excluded as noise.

**Files affected:** `project_deal_poc/agent.py`

---

## Improvement 2 — Reject event type

**Problem:** When the scheduler rejects an agent's action, it silently posts a `pass` on the agent's behalf. The agent has no idea it failed. It retries the same invalid action next turn, wasting API calls. Analysis cannot distinguish "agent respected constraints" from "agent kept failing silently."

**Fix:**
- Add `"reject"` as a new action type in `channel.py` (prefix `rjt_`)
- In `scheduler.py/_reject`, post a `reject` event instead of a `pass`, including the rejection reason in the message
- In `agent.py/_format_channel_view`, show reject events in the full history so the agent sees its own failures
- In `analyze.py`, count and report rejection events per agent

**Files affected:** `project_deal_poc/channel.py`, `project_deal_poc/scheduler.py`, `project_deal_poc/agent.py`, `project_deal_poc/analyze.py`

---

## Improvement 3 — Fix unbought tracking bug in analyze.py

**Problem:** `analyze.py` line 92 calls `ledger.is_sold(w["want_id"])` to check if a want is unfulfilled. This looks in the wrong set — `sold_item_ids` tracks item IDs like `camera_01`, not want IDs like `camera_w1`. Every agent's "unbought" list is always wrong.

**Fix:** Change `ledger.is_sold(w["want_id"])` to `ledger.is_want_fulfilled(w["want_id"])` on that line.

**Files affected:** `project_deal_poc/analyze.py`

---

## Improvement 4 — Stall counter only increments on genuine passes

**Problem:** `scheduler.py` increments `turns_since_progress` when an agent's action is rejected. A rejection means the agent was trying to do something — it is not a stall. This can trigger premature run termination.

**Fix:** Only increment `turns_since_progress` when the agent's *original decision* was `pass` (i.e. `decision.action == "pass"`). Rejected actions do not count toward the stall limit.

**Files affected:** `project_deal_poc/scheduler.py`

---

## Improvement 5 — Explicit ID targeting examples in agent template

**Problem:** The agent template tells agents to "use the relevant event ID" but doesn't explain which ID to use in which scenario. There are three distinct cases that require different IDs. Agents pick the wrong one, causing deals to fail at the accept stage.

**Fix:** Add three explicit examples to `prompts/agent_template.txt` in the ACTIONS section:

- Buy at asking price → target the listing ID (`lst_005`)
- Accept a buyer's offer or counter → target the offer/counter ID (`off_007` or `ctr_014`)
- Accept a seller's counter back to you → target the counter ID (`ctr_014`)

Each example shows the exact JSON format with the ID copied from the context the agent would see.

**Files affected:** `project_deal_poc/prompts/agent_template.txt`

---

## Improvement 6 — 10 agents, frozen persona sets, varied ratios

**Problem:** 6 agents produces too little market complexity. Pure random persona generation makes runs non-reproducible and tends toward artificially easy markets with perfect overlap.

**Fix:**

- Change `DEFAULT_NUM_PERSONAS` in `config.py` from 6 to 10
- Generate 5 frozen persona sets manually, saved as `project_deal_poc/personas/set_01.json` through `set_05.json`
- Each set has a different seller/buyer ratio: 5/5, 6/4, 4/6, 7/3, 3/7
- Each set deliberately includes orphan items (sellers with no matching buyer) for realistic friction
- Add `--persona-set N` flag to `run.py` to select which frozen set to use (default: set_01)
- Bump `DEFAULT_MAX_TURNS` from 60 to 120 to give 10 agents enough room
- `--regenerate-personas` still works for generating new sets, but experiments use the frozen ones

**Files affected:** `project_deal_poc/config.py`, `project_deal_poc/run.py`, `project_deal_poc/interview.py`, new `project_deal_poc/personas/` directory

---

## Improvement 7 — Shuffled rotation scheduler

**Problem:** `random.choice(active_agents)` allows the same agent to be picked multiple times in a row while others wait many turns. This creates structural bias — high-activity agents get more turns and naturally close more deals.

**Fix:**
- Change default scheduler to shuffled rotation: shuffle the active agents list, iterate through it once, then reshuffle and repeat
- As agents finish (no items left to sell AND no wants unfulfilled), they drop out of the active list — rounds get shorter naturally
- Add `--scheduler random` flag to keep the current pure-random behavior available for comparison
- Add `--scheduler rotation` as the explicit default

**Files affected:** `project_deal_poc/scheduler.py`, `project_deal_poc/run.py`

---

## Improvement 8 — Decline closes the specific offer

**Problem:** Decline and pass are functionally identical. Nothing happens when an agent declines — the listing stays open, the offer is not blocked, the offerer can immediately re-offer the same amount. Agents have no reason to use decline.

**Fix:**
- Track declined offer IDs in the ledger or channel state
- When an agent tries to re-offer on a listing after their previous offer was declined, the scheduler rejects the new offer if the price is equal to or lower than the declined price
- The agent can still counter at a higher price — decline signals "not at that price or lower," not "never"
- Update the agent template to explain decline semantics explicitly

**Files affected:** `project_deal_poc/scheduler.py`, `project_deal_poc/channel.py`, `project_deal_poc/prompts/agent_template.txt`

---

## Implementation order

1. Improvement 3 (one-line bug fix — lowest risk)
2. Improvement 2 (reject event type — foundational, Improvements 4 depends on it)
3. Improvement 4 (stall counter fix — depends on reject events existing)
4. Improvement 1 (full channel history — agent context change)
5. Improvement 5 (agent template — prompt change)
6. Improvement 8 (decline semantics — channel + scheduler change)
7. Improvement 7 (shuffled rotation — scheduler change)
8. Improvement 6 (10 agents + frozen personas — largest change, last)
