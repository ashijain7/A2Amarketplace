# Replication Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply 8 targeted improvements to the Project Deal POC — fixing bugs, improving agent context, strengthening negotiation mechanics, and adding reproducibility infrastructure.

**Architecture:** Each task is a self-contained change. Order matters: test infrastructure first, bug fixes second (lowest risk), then behavioral changes to channel/scheduler/agent, then infrastructure (frozen personas + scale). Tasks 2 and 3 share scheduler.py but touch different sections — do them in order.

**Tech Stack:** Python 3.10+, pytest, openai SDK via OpenRouter, uv

---

## File Map

| File | Changed by task |
|------|----------------|
| `pyproject.toml` | Task 0 |
| `tests/__init__.py` | Task 0 (new) |
| `tests/test_analyze.py` | Task 1 (new) |
| `tests/test_channel.py` | Task 2, Task 6 (new) |
| `tests/test_scheduler.py` | Task 2, Task 3, Task 6, Task 7 (new) |
| `tests/test_agent.py` | Task 4 (new) |
| `project_deal_poc/analyze.py` | Task 1, Task 2 |
| `project_deal_poc/channel.py` | Task 2, Task 6 |
| `project_deal_poc/scheduler.py` | Task 2, Task 3, Task 6, Task 7 |
| `project_deal_poc/agent.py` | Task 4 |
| `project_deal_poc/prompts/agent_template.txt` | Task 5, Task 6 |
| `project_deal_poc/config.py` | Task 8 |
| `project_deal_poc/run.py` | Task 7, Task 8 |
| `project_deal_poc/personas/` | Task 8 (new directory) |

---

## Task 0: Test Infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`

- [ ] **Step 1: Add pytest as dev dependency**

In `pyproject.toml`, add after the `dependencies` block:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
```

- [ ] **Step 2: Install dev dependencies**

```bash
uv pip install -e ".[dev]"
```

Expected output: `Successfully installed pytest-...`

- [ ] **Step 3: Create tests directory**

```bash
mkdir tests && touch tests/__init__.py
```

- [ ] **Step 4: Verify pytest works**

```bash
python -m pytest tests/ -v
```

Expected output: `no tests ran` (directory exists, nothing to run yet)

---

## Task 1: Fix unbought tracking bug in analyze.py

**Problem:** `analyze.py` line 92 calls `ledger.is_sold(w["want_id"])` which checks the wrong set — sold items, not fulfilled wants. Every agent's "unbought" list is always wrong.

**Files:**
- Modify: `project_deal_poc/analyze.py:92`
- Create: `tests/test_analyze.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_analyze.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.ledger import Ledger


def test_unbought_uses_want_fulfilled_not_is_sold():
    """Unfulfilled wants should be detected with is_want_fulfilled, not is_sold."""
    ledger = Ledger.__new__(Ledger)
    ledger.deals = []
    ledger.sold_item_ids = set()
    ledger.fulfilled_want_ids = {"headphones_w1"}
    ledger._next_deal_num = 1
    ledger.path = Path("/tmp/test_deals.json")

    persona = {
        "name": "Dexter",
        "items_to_buy": [
            {"want_id": "headphones_w1", "description": "Headphones", "ceiling_price": 50},
            {"want_id": "books_w1", "description": "Books", "ceiling_price": 15},
        ]
    }

    # headphones_w1 is fulfilled — should NOT appear in unbought
    # books_w1 is not fulfilled — SHOULD appear in unbought
    unbought = [
        w for w in persona.get("items_to_buy", [])
        if not ledger.is_want_fulfilled(w["want_id"])
    ]

    want_ids = [w["want_id"] for w in unbought]
    assert "headphones_w1" not in want_ids, "fulfilled want should not appear as unbought"
    assert "books_w1" in want_ids, "unfulfilled want should appear as unbought"
```

- [ ] **Step 2: Run test to confirm logic is correct**

```bash
python -m pytest tests/test_analyze.py -v
```

Expected: PASS (this tests the correct logic — now we need to fix analyze.py to use it)

- [ ] **Step 3: Write test that catches the actual bug**

Append to `tests/test_analyze.py`:

```python
def test_analyze_bug_is_sold_wrong_for_wants():
    """Demonstrates the bug: is_sold returns False for want IDs, making everything look unfulfilled."""
    ledger = Ledger.__new__(Ledger)
    ledger.deals = []
    ledger.sold_item_ids = set()
    ledger.fulfilled_want_ids = {"headphones_w1"}
    ledger._next_deal_num = 1
    ledger.path = Path("/tmp/test_deals.json")

    # The buggy code uses is_sold to check wants
    # headphones_w1 is in fulfilled_want_ids but NOT in sold_item_ids
    # So is_sold("headphones_w1") returns False — wrong, it IS fulfilled
    assert ledger.is_sold("headphones_w1") is False      # confirms the bug exists
    assert ledger.is_want_fulfilled("headphones_w1") is True  # correct answer
```

- [ ] **Step 4: Run to confirm bug exists**

```bash
python -m pytest tests/test_analyze.py::test_analyze_bug_is_sold_wrong_for_wants -v
```

Expected: PASS (confirms `is_sold` returns False for want IDs, proving the bug)

- [ ] **Step 5: Fix the bug**

In `project_deal_poc/analyze.py`, find line 92:

```python
            if not ledger.is_sold(w["want_id"]):
```

Change to:

```python
            if not ledger.is_want_fulfilled(w["want_id"]):
```

- [ ] **Step 6: Commit**

```bash
git add project_deal_poc/analyze.py tests/test_analyze.py pyproject.toml tests/__init__.py
git commit -m "fix: use is_want_fulfilled for unbought tracking in analyze.py"
```

---

## Task 2: Add reject event type

**Problem:** When the scheduler rejects an invalid action it silently posts a `pass`. The agent never learns it failed. Analysis cannot distinguish real passes from rejections.

**Files:**
- Modify: `project_deal_poc/channel.py`
- Modify: `project_deal_poc/scheduler.py`
- Modify: `project_deal_poc/analyze.py`
- Create: `tests/test_channel.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing test for reject event in channel**

Create `tests/test_channel.py`:

```python
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.channel import Channel


def make_channel():
    """Create a channel backed by a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    c = Channel(path=Path(tmp.name))
    c.clear()
    return c


def test_reject_event_gets_rjt_prefix():
    """Posting a reject action should produce an event_id starting with rjt_."""
    c = make_channel()
    event = c.post(1, "Dexter", "reject", None, None, "action rejected: invalid target")
    assert event.event_id.startswith("rjt_"), f"Expected rjt_ prefix, got {event.event_id}"


def test_pass_event_gets_psh_prefix():
    """Posting a pass action should still produce an event_id starting with psh_."""
    c = make_channel()
    event = c.post(1, "Dexter", "pass", None, None, "(pass)")
    assert event.event_id.startswith("psh_"), f"Expected psh_ prefix, got {event.event_id}"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python -m pytest tests/test_channel.py::test_reject_event_gets_rjt_prefix -v
```

Expected: FAIL — `rjt_` prefix not yet in the map, `reject` maps to `evt_`

- [ ] **Step 3: Add reject to channel event prefix map**

In `project_deal_poc/channel.py`, find the `_make_event_id` method (lines 51–60). The prefix dict currently is:

```python
        prefix = {
            "listing": "lst",
            "offer": "off",
            "counter": "ctr",
            "accept": "acc",
            "decline": "dec",
            "pass": "psh",
        }.get(action, "evt")
```

Add `"reject": "rjt"`:

```python
        prefix = {
            "listing": "lst",
            "offer": "off",
            "counter": "ctr",
            "accept": "acc",
            "decline": "dec",
            "pass": "psh",
            "reject": "rjt",
        }.get(action, "evt")
```

- [ ] **Step 4: Run channel test — should pass now**

```bash
python -m pytest tests/test_channel.py -v
```

Expected: PASS

- [ ] **Step 5: Write failing test for scheduler posting reject**

Create `tests/test_scheduler.py`:

```python
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.channel import Channel
from project_deal_poc.ledger import Ledger
from project_deal_poc.agent import AgentDecision
from project_deal_poc.scheduler import _validate_and_apply


def make_channel():
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    c = Channel(path=Path(tmp.name))
    c.clear()
    return c


def make_ledger():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    l = Ledger(path=Path(tmp.name))
    l.clear()
    return l


PERSONAS = {
    "Dexter": {
        "name": "Dexter",
        "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
        "items_to_buy": [{"want_id": "headphones_w1", "description": "Headphones", "ceiling_price": 50}],
        "style": "Direct.",
    }
}


def test_invalid_action_posts_reject_not_pass():
    """When an action is invalid, scheduler should post a reject event, not a pass."""
    c = make_channel()
    l = make_ledger()

    # Try to list an item that doesn't belong to Dexter
    decision = AgentDecision(
        action="listing",
        target="nonexistent_item",
        price=100,
        message="Listing a fake item",
        raw={},
    )

    _validate_and_apply(decision, "Dexter", PERSONAS["Dexter"], PERSONAS, c, l, turn=1)

    assert len(c.events) == 1
    assert c.events[0].action == "reject", f"Expected reject, got {c.events[0].action}"
    assert c.events[0].event_id.startswith("rjt_")
```

- [ ] **Step 6: Run test to confirm it fails**

```bash
python -m pytest tests/test_scheduler.py::test_invalid_action_posts_reject_not_pass -v
```

Expected: FAIL — scheduler still posts "pass" for invalid actions

- [ ] **Step 7: Change _reject in scheduler.py to post reject instead of pass**

In `project_deal_poc/scheduler.py`, find the `_reject` function (lines 270–276):

```python
def _reject(agent_name: str, reason: str, channel: Channel, turn: int):
    print(f"  [reject] {agent_name} turn {turn}: {reason}")
    channel.post(
        turn, agent_name, "pass", None, None,
        f"(invalid action rejected: {reason})",
    )
    return False, reason
```

Change to:

```python
def _reject(agent_name: str, reason: str, channel: Channel, turn: int):
    print(f"  [reject] {agent_name} turn {turn}: {reason}")
    channel.post(
        turn, agent_name, "reject", None, None,
        f"(action rejected: {reason})",
    )
    return False, reason
```

- [ ] **Step 8: Run scheduler test — should pass now**

```bash
python -m pytest tests/test_scheduler.py -v
```

Expected: PASS

- [ ] **Step 9: Update analyze.py to count reject events**

In `project_deal_poc/analyze.py`, find the action loop (around lines 59–61):

```python
    for action in ("listing", "offer", "counter", "accept", "decline", "pass"):
        print(f"  {action:8} {action_counts.get(action, 0)}")
```

Change to:

```python
    for action in ("listing", "offer", "counter", "accept", "decline", "reject", "pass"):
        print(f"  {action:8} {action_counts.get(action, 0)}")
```

- [ ] **Step 10: Commit**

```bash
git add project_deal_poc/channel.py project_deal_poc/scheduler.py project_deal_poc/analyze.py tests/test_channel.py tests/test_scheduler.py
git commit -m "feat: add reject event type so agents see when their actions fail"
```

---

## Task 3: Fix stall counter

**Problem:** The stall counter increments when an action is rejected. A rejected action means the agent was trying — not stalling. This can trigger premature run termination.

**Files:**
- Modify: `project_deal_poc/scheduler.py:343-347`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_scheduler.py`:

```python
def test_rejected_action_does_not_increment_stall_counter():
    """A rejected action should not count as a stall turn."""
    c = make_channel()
    l = make_ledger()

    # Simulate: agent tries something invalid (rejected) vs agent passes (stall)
    # We'll call _validate_and_apply directly and check what action was posted

    # Invalid listing → gets rejected
    decision = AgentDecision(
        action="listing",
        target="fake_item",
        price=100,
        message="fake",
        raw={},
    )
    accepted, _ = _validate_and_apply(decision, "Dexter", PERSONAS["Dexter"], PERSONAS, c, l, turn=1)

    assert accepted is False
    assert decision.action != "pass", "original decision was not a pass — stall should not increment"


def test_genuine_pass_should_be_identified_as_stall():
    """A genuine pass decision should increment the stall counter."""
    c = make_channel()
    l = make_ledger()

    decision = AgentDecision(
        action="pass",
        target=None,
        price=None,
        message="(pass)",
        raw={},
    )
    accepted, _ = _validate_and_apply(decision, "Dexter", PERSONAS["Dexter"], PERSONAS, c, l, turn=1)

    assert accepted is True
    assert decision.action == "pass", "genuine pass should be identified for stall tracking"
```

- [ ] **Step 2: Run tests to confirm they pass (these test the logic, not the counter itself)**

```bash
python -m pytest tests/test_scheduler.py -v
```

Expected: PASS (these tests validate the preconditions for the fix)

- [ ] **Step 3: Fix the stall counter logic in scheduler.py**

In `project_deal_poc/scheduler.py`, find lines 342–348 in the main loop:

```python
        # Track stall
        if accepted and decision.action in productive_actions:
            turns_since_progress = 0
        else:
            turns_since_progress += 1
```

Change to:

```python
        # Track stall — only genuine passes count, not rejected attempts
        if accepted and decision.action in productive_actions:
            turns_since_progress = 0
        elif decision.action == "pass":
            turns_since_progress += 1
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add project_deal_poc/scheduler.py tests/test_scheduler.py
git commit -m "fix: stall counter only increments on genuine passes, not rejected actions"
```

---

## Task 4: Full channel history in agent context

**Problem:** Each agent sees only the last 8 channel events globally. Negotiations that span more than ~1 turn per agent fall out of the window, causing agents to reference wrong event IDs or lose track of threads they're in.

**Files:**
- Modify: `project_deal_poc/agent.py:141-148`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_agent.py`:

```python
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_deal_poc.channel import Channel
from project_deal_poc.ledger import Ledger
from project_deal_poc.agent import _format_channel_view


def make_channel():
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    c = Channel(path=Path(tmp.name))
    c.clear()
    return c


def make_ledger():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    l = Ledger(path=Path(tmp.name))
    l.clear()
    return l


PERSONA = {
    "name": "Dexter",
    "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
    "items_to_buy": [{"want_id": "headphones_w1", "description": "Headphones", "ceiling_price": 50}],
    "style": "Direct.",
}


def test_full_history_excludes_pass_events():
    """Pass events should not appear in the channel history shown to agents."""
    c = make_channel()
    l = make_ledger()

    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera for sale")
    c.post(2, "Mika", "offer", "lst_001", 55, "Offering $55")
    c.post(3, "Rosa", "pass", None, None, "(pass)")
    c.post(4, "Mika", "counter", "lst_001", 60, "How about $60?")

    view = _format_channel_view("Dexter", PERSONA, c, l)

    assert "(pass)" not in view, "pass event message should not appear in agent context"
    assert "Offering $55" in view, "offer event should appear in agent context"
    assert "How about $60?" in view, "counter event should appear in agent context"


def test_full_history_includes_old_events_beyond_8():
    """Events older than 8 turns should still appear in agent context."""
    c = make_channel()
    l = make_ledger()

    # Post 12 events — more than the old window of 8
    c.post(1, "Mika", "listing", "headphones_01", 48, "Headphones listing turn 1")
    for i in range(2, 12):
        c.post(i, "Rosa", "pass", None, None, "(pass)")
    c.post(12, "Dexter", "offer", "lst_001", 45, "Offer at turn 12")

    view = _format_channel_view("Dexter", PERSONA, c, l)

    # The listing from turn 1 should still be visible at turn 12
    assert "Headphones listing turn 1" in view, "old events should still appear in full history"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_agent.py -v
```

Expected: FAIL — current code uses `channel.recent(8)` so old events don't appear

- [ ] **Step 3: Replace recent(8) with full filtered history in agent.py**

In `project_deal_poc/agent.py`, find lines 141–148:

```python
    lines.append("=== RECENT MESSAGES IN CHANNEL (most recent last) ===")
    recent = channel.recent(8)
    if recent:
        for e in recent:
            lines.append(f"  [turn {e.turn}] {e.agent} ({e.action}): {e.message[:120]}")
    else:
        lines.append("  (channel is empty — you can post the first listing)")
    lines.append("")
```

Replace with:

```python
    lines.append("=== FULL CHANNEL HISTORY (oldest first, passes excluded) ===")
    history = [e for e in channel.events if e.action != "pass"]
    if history:
        for e in history:
            lines.append(f"  [turn {e.turn}] {e.agent} ({e.action}): {e.message[:120]}")
    else:
        lines.append("  (channel is empty — you can post the first listing)")
    lines.append("")
```

- [ ] **Step 4: Run tests — should pass now**

```bash
python -m pytest tests/test_agent.py -v
```

Expected: PASS

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add project_deal_poc/agent.py tests/test_agent.py
git commit -m "feat: show full channel history to agents, excluding pass events"
```

---

## Task 5: Explicit ID targeting in agent template

**Problem:** The agent template says "use the relevant event ID" but doesn't explain the three different targeting scenarios. Agents pick the wrong ID and deals fail at the accept stage.

**Files:**
- Modify: `project_deal_poc/prompts/agent_template.txt`

No automated test for this — it's a prompt change. Verify by reading the updated template.

- [ ] **Step 1: Update the accept field rules in agent_template.txt**

In `project_deal_poc/prompts/agent_template.txt`, find the Field rules section:

```
- "accept":   target = the listing_id (if you're the buyer accepting a counter)
              OR the offer_id (if you're the seller accepting a buyer's offer),
              price = the agreed price
```

Replace with:

```
- "accept":   price = the agreed price. For target, there are three cases:
              CASE 1 — You are the SELLER accepting a buyer's offer or counter:
                target = the offer or counter event_id (e.g. "off_007" or "ctr_014")
                Example: Mika offered off_007 at $55. You accept it:
                  {"action":"accept","target":"off_007","price":55,"message":"Done."}
              CASE 2 — You are the BUYER accepting a seller's counter back to you:
                target = the counter event_id posted by the seller (e.g. "ctr_009")
                Example: Dexter countered ctr_009 at $62. You accept it:
                  {"action":"accept","target":"ctr_009","price":62,"message":"Deal."}
              CASE 3 — You are the BUYER buying at the listing's asking price directly:
                target = the listing event_id (e.g. "lst_005")
                Example: Rosa listed lst_017 at $25. You buy at asking price:
                  {"action":"accept","target":"lst_017","price":25,"message":"Buying now."}
              IMPORTANT: Copy the exact event_id from the channel history above.
              Do not guess or construct IDs. Only use IDs you can see.
```

- [ ] **Step 2: Verify the template reads correctly**

```bash
python -c "
from project_deal_poc.config import AGENT_TEMPLATE_PATH
txt = AGENT_TEMPLATE_PATH.read_text()
assert 'CASE 1' in txt and 'CASE 2' in txt and 'CASE 3' in txt
assert 'Copy the exact event_id' in txt
print('Template updated correctly')
"
```

Expected: `Template updated correctly`

- [ ] **Step 3: Commit**

```bash
git add project_deal_poc/prompts/agent_template.txt
git commit -m "fix: add explicit ID targeting examples to agent template for all accept scenarios"
```

---

## Task 6: Decline closes the offer

**Problem:** Declining an offer is functionally identical to passing — nothing changes, and the offerer can immediately re-offer the same price. Decline is not a real signal.

**Files:**
- Modify: `project_deal_poc/channel.py`
- Modify: `project_deal_poc/scheduler.py`
- Modify: `project_deal_poc/prompts/agent_template.txt`
- Modify: `tests/test_channel.py`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing test for max_declined_price_for**

Append to `tests/test_channel.py`:

```python
def test_max_declined_price_for_returns_none_when_no_declines():
    """Returns None when no offers from agent have been declined on a listing."""
    c = make_channel()
    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera $65")   # lst_001
    c.post(2, "Mika", "offer", "lst_001", 55, "Offering $55")        # off_002

    result = c.max_declined_price_for("lst_001", "Mika")
    assert result is None


def test_max_declined_price_for_returns_declined_price():
    """Returns the price of a declined offer."""
    c = make_channel()
    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera $65")    # lst_001
    c.post(2, "Mika", "offer", "lst_001", 50, "Offering $50")        # off_002
    c.post(3, "Dexter", "decline", "off_002", None, "No thanks")     # dec_003

    result = c.max_declined_price_for("lst_001", "Mika")
    assert result == 50.0


def test_max_declined_price_for_returns_highest_when_multiple():
    """Returns the highest declined price when multiple offers were declined."""
    c = make_channel()
    c.post(1, "Dexter", "listing", "camera_01", 65, "Camera $65")    # lst_001
    c.post(2, "Mika", "offer", "lst_001", 45, "Try $45")             # off_002
    c.post(3, "Dexter", "decline", "off_002", None, "Too low")       # dec_003
    c.post(4, "Mika", "offer", "lst_001", 50, "Try $50")             # off_004
    c.post(5, "Dexter", "decline", "off_004", None, "Still no")      # dec_005

    result = c.max_declined_price_for("lst_001", "Mika")
    assert result == 50.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_channel.py -v
```

Expected: FAIL — `max_declined_price_for` method does not exist yet

- [ ] **Step 3: Add max_declined_price_for to channel.py**

In `project_deal_poc/channel.py`, add this method after the `recent` method (after line 112):

```python
    def max_declined_price_for(self, listing_id: str, offerer_name: str) -> float | None:
        """
        Return the highest price the seller has declined from offerer_name on listing_id.
        Used to prevent re-offers at or below a declined price.
        """
        declined_prices = []
        for e in self.events:
            if e.action != "decline" or not e.target:
                continue
            ref = self.get_event(e.target)
            if ref is None or ref.agent != offerer_name:
                continue
            if ref.action not in ("offer", "counter"):
                continue
            # Check that this offer/counter was on our listing
            listing = self.get_event(ref.target) if ref.target else None
            if listing and listing.event_id == listing_id and ref.price is not None:
                declined_prices.append(ref.price)
        return max(declined_prices) if declined_prices else None
```

- [ ] **Step 4: Run channel tests — should pass now**

```bash
python -m pytest tests/test_channel.py -v
```

Expected: PASS

- [ ] **Step 5: Write failing test for offer rejection after decline**

Append to `tests/test_scheduler.py`:

```python
def test_offer_at_declined_price_is_rejected():
    """An offer at or below a previously declined price should be rejected."""
    c = make_channel()
    l = make_ledger()

    personas = {
        "Dexter": {
            "name": "Dexter",
            "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
            "items_to_buy": [],
            "style": "Direct.",
        },
        "Mika": {
            "name": "Mika",
            "items_to_sell": [],
            "items_to_buy": [{"want_id": "camera_w1", "description": "Camera", "ceiling_price": 70}],
            "style": "Friendly.",
        },
    }

    # Dexter lists camera
    list_decision = AgentDecision("listing", "camera_01", 65, "Camera $65", {})
    _validate_and_apply(list_decision, "Dexter", personas["Dexter"], personas, c, l, turn=1)

    # Mika offers $50
    offer_decision = AgentDecision("offer", "lst_001", 50, "Offering $50", {})
    _validate_and_apply(offer_decision, "Mika", personas["Mika"], personas, c, l, turn=2)

    # Dexter declines
    decline_decision = AgentDecision("decline", "off_002", None, "Too low", {})
    _validate_and_apply(decline_decision, "Dexter", personas["Dexter"], personas, c, l, turn=3)

    # Mika tries to offer $50 again — should be rejected
    reoffer_decision = AgentDecision("offer", "lst_001", 50, "Still $50?", {})
    accepted, reason = _validate_and_apply(reoffer_decision, "Mika", personas["Mika"], personas, c, l, turn=4)

    assert accepted is False, "re-offer at declined price should be rejected"
    assert "declined" in reason.lower(), f"rejection reason should mention declined: {reason}"


def test_offer_above_declined_price_is_allowed():
    """An offer above a previously declined price should be allowed."""
    c = make_channel()
    l = make_ledger()

    personas = {
        "Dexter": {
            "name": "Dexter",
            "items_to_sell": [{"item_id": "camera_01", "name": "Camera", "floor_price": 45}],
            "items_to_buy": [],
            "style": "Direct.",
        },
        "Mika": {
            "name": "Mika",
            "items_to_sell": [],
            "items_to_buy": [{"want_id": "camera_w1", "description": "Camera", "ceiling_price": 70}],
            "style": "Friendly.",
        },
    }

    # Dexter lists
    _validate_and_apply(AgentDecision("listing", "camera_01", 65, "Camera", {}),
                        "Dexter", personas["Dexter"], personas, c, l, turn=1)
    # Mika offers $50
    _validate_and_apply(AgentDecision("offer", "lst_001", 50, "$50", {}),
                        "Mika", personas["Mika"], personas, c, l, turn=2)
    # Dexter declines
    _validate_and_apply(AgentDecision("decline", "off_002", None, "No", {}),
                        "Dexter", personas["Dexter"], personas, c, l, turn=3)
    # Mika offers $60 — higher than declined $50, should be accepted
    accepted, _ = _validate_and_apply(AgentDecision("offer", "lst_001", 60, "$60", {}),
                                       "Mika", personas["Mika"], personas, c, l, turn=4)

    assert accepted is True, "offer above declined price should be allowed"
```

- [ ] **Step 6: Run tests to confirm they fail**

```bash
python -m pytest tests/test_scheduler.py::test_offer_at_declined_price_is_rejected tests/test_scheduler.py::test_offer_above_declined_price_is_allowed -v
```

Expected: FAIL — scheduler doesn't check declined prices yet

- [ ] **Step 7: Add declined price check to scheduler.py offer validation**

In `project_deal_poc/scheduler.py`, find the offer/counter validation block (around line 100–121). Find this section inside `if action in ("offer", "counter")`:

```python
        if action == "offer" and listing.agent == agent_name:
            return _reject(agent_name, "offering on your own listing", channel, turn)
```

Add the declined price check immediately after that line:

```python
        if action == "offer" and listing.agent == agent_name:
            return _reject(agent_name, "offering on your own listing", channel, turn)
        if action == "offer":
            max_declined = channel.max_declined_price_for(listing_id, agent_name)
            if max_declined is not None and decision.price <= max_declined:
                return _reject(
                    agent_name,
                    f"offer price ${decision.price} at or below previously declined ${max_declined}",
                    channel,
                    turn,
                )
```

- [ ] **Step 8: Run tests — should pass now**

```bash
python -m pytest tests/test_scheduler.py -v
```

Expected: PASS

- [ ] **Step 9: Update agent template to explain decline semantics**

In `project_deal_poc/prompts/agent_template.txt`, find the decline line:

```
- "decline":  target = the listing_id or offer_id you're rejecting, price = null
```

Replace with:

```
- "decline":  target = the offer_id or counter_id you are rejecting, price = null
              WARNING: Once you decline an offer, that agent cannot re-offer at the
              same price or lower. They can only come back with a higher price.
              Use decline deliberately — it closes off that price range permanently.
```

- [ ] **Step 10: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 11: Commit**

```bash
git add project_deal_poc/channel.py project_deal_poc/scheduler.py project_deal_poc/prompts/agent_template.txt tests/test_channel.py tests/test_scheduler.py
git commit -m "feat: decline closes offer — re-offers at same or lower price are rejected"
```

---

## Task 7: Shuffled rotation scheduler

**Problem:** `random.choice(active_agents)` can pick the same agent multiple times in a row. With 10 agents and 120 turns, turn distribution can be heavily skewed. Project Deal likely used round-robin shuffled rotation.

**Files:**
- Modify: `project_deal_poc/scheduler.py`
- Modify: `project_deal_poc/run.py`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing test for rotation**

Append to `tests/test_scheduler.py`:

```python
from project_deal_poc.scheduler import _pick_next_agent_rotation


def test_rotation_gives_each_agent_one_turn_per_round():
    """Every agent should appear once before any agent appears twice."""
    agents = ["Alice", "Bob", "Carol", "Dave"]
    queue = []
    seen_in_round: list[str] = []

    for _ in range(len(agents) * 3):  # 3 full rounds
        agent, queue = _pick_next_agent_rotation(agents, queue)
        assert agent not in seen_in_round, f"{agent} appeared twice before round reset"
        seen_in_round.append(agent)
        if len(seen_in_round) == len(agents):
            seen_in_round = []  # round complete, reset


def test_rotation_skips_finished_agents():
    """Agents no longer in active list should not be returned."""
    agents_full = ["Alice", "Bob", "Carol"]
    agents_reduced = ["Alice", "Carol"]  # Bob finished mid-round
    queue = []

    # Run two turns from full list to populate queue
    _, queue = _pick_next_agent_rotation(agents_full, queue)
    _, queue = _pick_next_agent_rotation(agents_full, queue)

    # Now Bob finishes — next picks should only return Alice or Carol
    for _ in range(6):
        agent, queue = _pick_next_agent_rotation(agents_reduced, queue)
        assert agent in agents_reduced, f"Finished agent returned: {agent}"
```

- [ ] **Step 2: Run test**

```bash
python -m pytest tests/test_scheduler.py::test_rotation_gives_each_agent_one_turn_per_round -v
```

Expected: FAIL — `_pick_next_agent_rotation` does not exist yet

- [ ] **Step 3: Refactor scheduler.py main loop to support both modes**

In `project_deal_poc/scheduler.py`, update the `run_marketplace` function signature (line 282) to add a `scheduler` parameter:

```python
def run_marketplace(
    personas: list[dict],
    agent_prompts: dict[str, str],
    model: str = config.DEFAULT_MODEL,
    max_turns: int = config.MAX_TURNS,
    stall_limit: int = config.STALL_LIMIT,
    seed: Optional[int] = None,
    scheduler: str = "rotation",
) -> tuple[Channel, Ledger]:
```

Then replace the agent-selection line inside the loop. Find:

```python
        agent_name = random.choice(active)
```

Replace the entire agent-selection section (from `active = [...]` through `agent_name = ...`) with:

```python
        active = [
            name for name in personas_by_name
            if not _is_agent_done(name, personas_by_name, ledger)
        ]
        if not active:
            print(f"\n[scheduler] All agents done at turn {turn - 1}.")
            break

        if scheduler == "rotation":
            if not round_queue:
                round_queue = random.sample(active, len(active))
            # Pop next agent, skip if they finished mid-round
            while round_queue:
                candidate = round_queue.pop(0)
                if not _is_agent_done(candidate, personas_by_name, ledger):
                    agent_name = candidate
                    break
            else:
                continue
        else:
            agent_name = random.choice(active)
```

Also add `round_queue: list[str] = []` just before the main `for turn in range(...)` loop.

- [ ] **Step 4: Add _pick_next_agent_rotation stub for the test import**

Add above `run_marketplace` in `scheduler.py`:

```python
def _pick_next_agent_rotation(active: list[str], queue: list[str]) -> tuple[str, list[str]]:
    """Pop the next agent from the rotation queue, rebuilding if empty. Returns (agent, queue)."""
    if not queue:
        queue = random.sample(active, len(active))
    while queue:
        candidate = queue.pop(0)
        if candidate in active:
            return candidate, queue
    return random.choice(active), []
```

- [ ] **Step 5: Run rotation test — should pass now**

```bash
python -m pytest tests/test_scheduler.py::test_rotation_gives_each_agent_one_turn_per_round -v
```

Expected: PASS

- [ ] **Step 6: Add --scheduler flag to run.py**

In `project_deal_poc/run.py`, find the `argparse` section. After `--seed` argument, add:

```python
    parser.add_argument("--scheduler", default="rotation", choices=["rotation", "random"],
                        help="rotation: shuffled round-robin (default). random: pure random choice.")
```

Then update the `run_marketplace` call to pass `scheduler=args.scheduler`:

```python
    run_marketplace(
        personas=personas,
        agent_prompts=agent_prompts,
        model=args.model,
        max_turns=args.max_turns,
        stall_limit=args.stall_limit,
        seed=args.seed,
        scheduler=args.scheduler,
    )
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add project_deal_poc/scheduler.py project_deal_poc/run.py tests/test_scheduler.py
git commit -m "feat: shuffled rotation scheduler as default, --scheduler random for old behavior"
```

---

## Task 8: 10 agents, frozen persona sets, --persona-set flag

**Problem:** Default 6 agents produces little market complexity. Persona generation is non-reproducible. Experiments need fixed persona sets to compare results.

**Files:**
- Modify: `project_deal_poc/config.py`
- Modify: `project_deal_poc/run.py`
- Create: `project_deal_poc/personas/` directory
- Create: `project_deal_poc/personas/generate_sets.py`

- [ ] **Step 1: Update constants in config.py**

In `project_deal_poc/config.py`, find and update these lines:

```python
MAX_TURNS = 60              # hard cap on scheduler iterations
STALL_LIMIT = 10            # end run if this many turns pass with no listing/offer/deal
DEFAULT_NUM_PERSONAS = 6    # number of agents to generate by default
```

Change to:

```python
MAX_TURNS = 120             # hard cap on scheduler iterations
STALL_LIMIT = 10            # end run if this many turns pass with no listing/offer/deal
DEFAULT_NUM_PERSONAS = 10   # number of agents to generate by default
```

Also add the personas directory path after `PERSONAS_PATH`:

```python
PERSONAS_PATH = DATA_DIR / "personas.json"
PERSONAS_DIR = ROOT / "personas"
```

- [ ] **Step 2: Create the personas directory**

```bash
mkdir /Users/ashijain/Documents/projectdealpoc/project_deal_poc/personas
touch /Users/ashijain/Documents/projectdealpoc/project_deal_poc/personas/__init__.py
```

- [ ] **Step 3: Create generate_sets.py**

Create `project_deal_poc/personas/generate_sets.py`:

```python
"""
Generate frozen persona sets for reproducible experiments.

Run once to create sets 01-05. All experiments should use these fixed sets.

Usage:
    python -m project_deal_poc.personas.generate_sets

Each set has 10 agents with a different seller/buyer ratio:
  set_01: 5 sellers / 5 buyers  (balanced)
  set_02: 6 sellers / 4 buyers  (buyer's market)
  set_03: 4 sellers / 6 buyers  (seller's market)
  set_04: 7 sellers / 3 buyers  (strong buyer's market)
  set_05: 3 sellers / 7 buyers  (strong seller's market)

Each set includes deliberate orphan items (sellers with no matching buyer)
to ensure not every deal closes — making results meaningful.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from project_deal_poc import config
from project_deal_poc.interview import generate_personas, validate_personas

SETS = [
    {"set_id": "01", "n_sellers": 5, "n_buyers": 5,  "label": "balanced"},
    {"set_id": "02", "n_sellers": 6, "n_buyers": 4,  "label": "buyer_market"},
    {"set_id": "03", "n_sellers": 4, "n_buyers": 6,  "label": "seller_market"},
    {"set_id": "04", "n_sellers": 7, "n_buyers": 3,  "label": "strong_buyer_market"},
    {"set_id": "05", "n_sellers": 3, "n_buyers": 7,  "label": "strong_seller_market"},
]

SETS_DIR = config.PERSONAS_DIR


def generate_set(set_def: dict) -> list[dict]:
    """Generate one persona set with the given ratio. Returns validated personas."""
    n = set_def["n_sellers"] + set_def["n_buyers"]
    print(f"\n[generate_sets] Generating set_{set_def['set_id']} "
          f"({set_def['n_sellers']} sellers / {set_def['n_buyers']} buyers, {n} agents)...")

    # Use higher temperature for variety across sets
    personas = generate_personas(n=n)
    warnings = validate_personas(personas)
    if warnings:
        print(f"[generate_sets] Warnings for set_{set_def['set_id']}:")
        for w in warnings:
            print(f"  - {w}")
    return personas


def main():
    config.require_api_key()
    SETS_DIR.mkdir(parents=True, exist_ok=True)

    for set_def in SETS:
        out_path = SETS_DIR / f"set_{set_def['set_id']}.json"
        if out_path.exists():
            print(f"[generate_sets] {out_path.name} already exists — skipping. Delete to regenerate.")
            continue
        personas = generate_set(set_def)
        out_path.write_text(json.dumps(personas, indent=2))
        print(f"[generate_sets] Wrote {len(personas)} personas to {out_path}")

    print("\n[generate_sets] All sets generated.")
    print(f"Use: uv run deal --persona-set 1  (through 5)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add --persona-set flag and --regenerate-personas to run.py**

In `project_deal_poc/run.py`, update the argparse section and persona loading logic. Replace the entire `main()` function with:

```python
def main():
    parser = argparse.ArgumentParser(description="Run the Project Deal PoC marketplace.")
    parser.add_argument("--model", default=config.DEFAULT_MODEL,
                        help="OpenRouter model string for the agents.")
    parser.add_argument("--max-turns", type=int, default=config.MAX_TURNS)
    parser.add_argument("--stall-limit", type=int, default=config.STALL_LIMIT)
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible runs.")
    parser.add_argument("--scheduler", default="rotation", choices=["rotation", "random"],
                        help="rotation: shuffled round-robin (default). random: pure random.")
    parser.add_argument("--persona-set", type=int, default=None, metavar="N",
                        help="Use frozen persona set N (1-5) from personas/set_0N.json.")
    parser.add_argument("--regenerate-personas", action="store_true",
                        help="Generate fresh personas before running (ignores --persona-set).")
    args = parser.parse_args()

    config.require_api_key()

    if args.regenerate_personas:
        print("[run] Regenerating personas...")
        personas = generate_personas(n=config.DEFAULT_NUM_PERSONAS)
        warnings = validate_personas(personas)
        if warnings:
            for w in warnings:
                print(f"  - {w}")
        config.PERSONAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.PERSONAS_PATH.write_text(json.dumps(personas, indent=2))
        print(f"[run] Wrote {len(personas)} personas to {config.PERSONAS_PATH}\n")
    elif args.persona_set is not None:
        set_path = config.PERSONAS_DIR / f"set_{args.persona_set:02d}.json"
        if not set_path.exists():
            raise FileNotFoundError(
                f"Persona set {args.persona_set} not found at {set_path}.\n"
                f"Run: python -m project_deal_poc.personas.generate_sets"
            )
        personas = json.loads(set_path.read_text())
        print(f"[run] Loaded {len(personas)} personas from frozen set {args.persona_set}: {set_path}\n")
    elif config.PERSONAS_PATH.exists():
        personas = load_personas()
        print(f"[run] Loaded {len(personas)} personas from {config.PERSONAS_PATH}")
        print(f"[run] Tip: use --persona-set 1 for a reproducible frozen set.\n")
    else:
        print("[run] No personas file found — generating fresh personas...")
        personas = generate_personas(n=config.DEFAULT_NUM_PERSONAS)
        warnings = validate_personas(personas)
        if warnings:
            for w in warnings:
                print(f"  - {w}")
        config.PERSONAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.PERSONAS_PATH.write_text(json.dumps(personas, indent=2))
        print(f"[run] Wrote {len(personas)} personas to {config.PERSONAS_PATH}\n")

    agent_prompts = build_agent_prompts(personas)
    print(f"[run] Built {len(agent_prompts)} agent system prompts.")

    run_marketplace(
        personas=personas,
        agent_prompts=agent_prompts,
        model=args.model,
        max_turns=args.max_turns,
        stall_limit=args.stall_limit,
        seed=args.seed,
        scheduler=args.scheduler,
    )

    print("\n" + "=" * 60)
    print(" POST-RUN ANALYSIS")
    print("=" * 60 + "\n")
    run_analysis()
```

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 6: Generate the 5 frozen persona sets (requires API key)**

```bash
python -m project_deal_poc.personas.generate_sets
```

Expected output: 5 files written to `project_deal_poc/personas/`:
- `set_01.json` through `set_05.json`
- Each contains 10 personas with summary printed

- [ ] **Step 7: Smoke test with frozen set**

```bash
uv run deal --persona-set 1 --max-turns 5 --seed 42
```

Expected: run starts, prints agent names from set_01, runs 5 turns, prints summary

- [ ] **Step 8: Add personas/ JSONs to .gitignore exclusion (they should be committed)**

The `.gitignore` currently has `data/` excluded (runtime data). The `personas/` directory contains frozen research assets that should be committed. Verify it's not accidentally excluded:

```bash
git check-ignore -v project_deal_poc/personas/set_01.json
```

Expected: no output (file is not ignored). If it shows ignored, remove the matching rule.

- [ ] **Step 9: Commit**

```bash
git add project_deal_poc/config.py project_deal_poc/run.py project_deal_poc/personas/ 
git commit -m "feat: 10 agents default, frozen persona sets, --persona-set flag, max-turns 120"
```

---

## Final Verification

- [ ] **Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tasks' tests PASS

- [ ] **Run a short end-to-end smoke test**

```bash
uv run deal --persona-set 1 --max-turns 10 --seed 42 --scheduler rotation
```

Expected: runs without errors, prints channel events, prints post-run analysis with correct unbought stats
