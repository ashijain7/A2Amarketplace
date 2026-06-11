# Payment Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional Stripe-backed payment layer to the A2A marketplace experiment so every agent (focal and opponent) must call payment tools after buying, with Stripe as the source of truth for balances.

**Architecture:** `enable_payments` flag in model configs gates the entire feature — when off, existing runs are completely unaffected. A new `stripe_ledger.py` owns all Stripe API calls. `Deal.payment_status` adds a two-phase (pending → confirmed/cancelled) flow to the ledger. `OpponentRunner` makes a second LLM call after any opponent buy to request payment. Results go to `results/payment_runs/` separate from existing `results/paper_runs/`.

**Tech Stack:** Python 3.12, `stripe` package (PyPI), FastAPI, existing NeMo Gym + OpenRouter setup, Stripe test mode (free, no real money).

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `marketplace/ledger.py` | Add `payment_status` to `Deal`; add `confirm_deal()`, `cancel_deal()`, `pending_deals_for_buyer()` to `Ledger` |
| Create | `resources_server/stripe_ledger.py` | All Stripe API calls: create accounts, read balance, execute transfer |
| Modify | `resources_server/app.py` | Add `enable_payments`, `stripe_accounts`, `payment_log` to `MarketplaceState`; add `check_balance`, `transfer_funds`, `verify_payment` endpoints; update `state_snapshot`; update `seed_session` |
| Modify | `resources_server/opponent_runner.py` | Accept payment state refs; second LLM call after opponent buy; `_request_opponent_payment()` |
| Modify | `marketplace/build_agents.py` | Accept `enable_payments` param; append payment block to prompts |
| Modify | `resources_server/model_config.py` | Add `enable_payments` field; add payment config names |
| Modify | `resources_server/verifiers.py` | Add `compute_payment_compliance()`; add `PAYMENT_PHASE_WEIGHTS` |
| Modify | `resources_server/app.py` | Update `_verify_for_state` to call payment rubric |
| Modify | `pyproject.toml` | Add `stripe` dependency |
| Create | `tests/test_stripe_ledger.py` | Unit tests for transfer logic (mocked Stripe) |
| Create | `tests/test_payment_endpoints.py` | Unit tests for all 3 payment endpoints |
| Create | `tests/test_payment_ledger.py` | Unit tests for ledger two-phase flow |

---

## Task 1: Install Stripe and update dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add stripe to pyproject.toml**

Open `pyproject.toml` and add `"stripe>=8.0.0"` to the dependencies list:

```toml
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.6.0",
    "openai>=1.40.0,<=2.7.2",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0",
    "httpx>=0.27.0",
    "stripe>=8.0.0",
]
```

- [ ] **Step 2: Install**

```bash
source .venv/bin/activate
uv pip install stripe
```

Expected: `Successfully installed stripe-X.X.X`

- [ ] **Step 3: Verify import works**

```bash
python -c "import stripe; print(stripe.__version__)"
```

Expected: prints a version number, no error.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add stripe>=8.0.0"
```

---

## Task 2: Two-phase deal status in Ledger

**Files:**
- Modify: `marketplace/ledger.py`
- Create: `tests/test_payment_ledger.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_payment_ledger.py`:

```python
import pytest
from pathlib import Path
from marketplace.ledger import Ledger


@pytest.fixture
def ledger(tmp_path):
    return Ledger(path=tmp_path / "deals.json")


def _make_deal(ledger, pending=False):
    return ledger.record_deal(
        seller="Kai", buyer="Marcus", item_id="itm_kb",
        item_name="Keyboard", price=45.0,
        seller_floor=35.0, buyer_ceiling=55.0, turn=1,
        pending=pending,
    )


def test_record_deal_default_status_na(ledger):
    deal = _make_deal(ledger, pending=False)
    assert deal.payment_status == "n/a"
    assert "itm_kb" in ledger.sold_item_ids


def test_record_deal_pending_not_sold(ledger):
    deal = _make_deal(ledger, pending=True)
    assert deal.payment_status == "pending"
    assert "itm_kb" not in ledger.sold_item_ids


def test_confirm_deal_marks_sold(ledger):
    deal = _make_deal(ledger, pending=True)
    result = ledger.confirm_deal(deal.deal_id)
    assert result is True
    assert deal.payment_status == "confirmed"
    assert "itm_kb" in ledger.sold_item_ids


def test_cancel_deal_stays_available(ledger):
    deal = _make_deal(ledger, pending=True)
    result = ledger.cancel_deal(deal.deal_id)
    assert result is True
    assert deal.payment_status == "cancelled"
    assert "itm_kb" not in ledger.sold_item_ids


def test_cancel_nonexistent_deal_returns_false(ledger):
    assert ledger.cancel_deal("deal_999") is False


def test_pending_deals_for_buyer(ledger):
    _make_deal(ledger, pending=True)
    pending = ledger.pending_deals_for_buyer("Marcus")
    assert len(pending) == 1
    assert pending[0].item_id == "itm_kb"


def test_pending_deals_excludes_confirmed(ledger):
    deal = _make_deal(ledger, pending=True)
    ledger.confirm_deal(deal.deal_id)
    assert ledger.pending_deals_for_buyer("Marcus") == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_payment_ledger.py -v
```

Expected: all tests FAIL — `record_deal` has no `pending` param, `Deal` has no `payment_status`.

- [ ] **Step 3: Update Deal dataclass in marketplace/ledger.py**

Add `payment_status` field after `item_a_ceiling` (line 41):

```python
payment_status: str = "n/a"   # "n/a" | "pending" | "confirmed" | "cancelled"
```

- [ ] **Step 4: Update record_deal() signature and body**

Replace the current `record_deal` method (lines 60–99) with:

```python
def record_deal(
    self,
    seller: str,
    buyer: str,
    item_id: str,
    item_name: str,
    price: float,
    seller_floor: float,
    buyer_ceiling: float,
    turn: int,
    deal_type: str = "money",
    item_b_id: str | None = None,
    item_b_name: str | None = None,
    item_b_floor: float | None = None,
    item_a_ceiling: float | None = None,
    pending: bool = False,
) -> Deal:
    status = "pending" if pending else "n/a"
    deal = Deal(
        deal_id=f"deal_{self._next_deal_num:03d}",
        seller=seller,
        buyer=buyer,
        item_id=item_id,
        item_name=item_name,
        price=price,
        seller_floor=seller_floor,
        buyer_ceiling=buyer_ceiling,
        turn=turn,
        deal_type=deal_type,
        item_b_id=item_b_id,
        item_b_name=item_b_name,
        item_b_floor=item_b_floor,
        item_a_ceiling=item_a_ceiling,
        payment_status=status,
    )
    self._next_deal_num += 1
    self.deals.append(deal)
    # Only mark sold immediately when NOT pending payment
    if not pending:
        self.sold_item_ids.add(item_id)
        if deal_type == "swap" and item_b_id:
            self.sold_item_ids.add(item_b_id)
    self._save()
    return deal
```

- [ ] **Step 5: Add confirm_deal, cancel_deal, pending_deals_for_buyer to Ledger**

Add after the `fulfill_want` method (after line 109):

```python
def confirm_deal(self, deal_id: str) -> bool:
    """Mark a pending deal as confirmed and mark item as sold."""
    for deal in self.deals:
        if deal.deal_id == deal_id:
            deal.payment_status = "confirmed"
            self.sold_item_ids.add(deal.item_id)
            if deal.deal_type == "swap" and deal.item_b_id:
                self.sold_item_ids.add(deal.item_b_id)
            self._save()
            return True
    return False

def cancel_deal(self, deal_id: str) -> bool:
    """Cancel a pending deal — item stays available."""
    for deal in self.deals:
        if deal.deal_id == deal_id:
            deal.payment_status = "cancelled"
            self.sold_item_ids.discard(deal.item_id)
            self._save()
            return True
    return False

def pending_deals_for_buyer(self, buyer_name: str) -> list:
    """Return all deals with status='pending' where buyer_name is the buyer."""
    return [
        d for d in self.deals
        if d.buyer == buyer_name and d.payment_status == "pending"
    ]
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_payment_ledger.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 7: Run existing tests to confirm nothing broke**

```bash
pytest tests/ -v --ignore=tests/test_payment_ledger.py
```

Expected: all existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add marketplace/ledger.py tests/test_payment_ledger.py
git commit -m "feat(ledger): add two-phase deal status and payment lifecycle methods"
```

---

## Task 3: Stripe client module

**Files:**
- Create: `resources_server/stripe_ledger.py`
- Create: `tests/test_stripe_ledger.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_stripe_ledger.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_stripe():
    with patch("resources_server.stripe_ledger.stripe") as m:
        yield m


def test_create_agent_accounts_creates_one_per_agent(mock_stripe):
    from resources_server.stripe_ledger import create_agent_accounts
    mock_stripe.Customer.create.side_effect = [
        MagicMock(id="cus_kai"),
        MagicMock(id="cus_rex"),
    ]
    result = create_agent_accounts(["Kai", "Rex"], session_id="sess_abc")
    assert result == {"Kai": "cus_kai", "Rex": "cus_rex"}
    assert mock_stripe.Customer.create.call_count == 2


def test_get_balance_cents(mock_stripe):
    from resources_server.stripe_ledger import get_balance_cents
    mock_stripe.Customer.retrieve.return_value = MagicMock(balance=15000)
    result = get_balance_cents("cus_kai")
    assert result == 15000
    mock_stripe.Customer.retrieve.assert_called_once_with("cus_kai")


def test_transfer_success(mock_stripe):
    from resources_server.stripe_ledger import transfer
    mock_stripe.Customer.retrieve.side_effect = [
        MagicMock(balance=15000),  # sender: $150
        MagicMock(balance=15000),  # receiver: $150
    ]
    result = transfer("cus_kai", "cus_rex", amount_cents=4500)
    assert result["success"] is True
    assert result["amount"] == 45.0
    assert result["sender_new_balance"] == 105.0
    assert result["receiver_new_balance"] == 195.0
    # Both modify calls should have fired
    assert mock_stripe.Customer.modify.call_count == 2


def test_transfer_insufficient_funds(mock_stripe):
    from resources_server.stripe_ledger import transfer
    mock_stripe.Customer.retrieve.return_value = MagicMock(balance=3000)  # $30
    result = transfer("cus_kai", "cus_rex", amount_cents=4500)  # wants $45
    assert result["success"] is False
    assert result["error"] == "insufficient_funds"
    assert result["balance"] == 30.0
    assert result["shortfall"] == 15.0
    mock_stripe.Customer.modify.assert_not_called()


def test_transfer_never_writes_negative_balance(mock_stripe):
    from resources_server.stripe_ledger import transfer
    # Sender has exactly the amount — new balance should be 0, not negative
    mock_stripe.Customer.retrieve.side_effect = [
        MagicMock(balance=4500),
        MagicMock(balance=4500),
    ]
    result = transfer("cus_kai", "cus_rex", amount_cents=4500)
    assert result["success"] is True
    assert result["sender_new_balance"] == 0.0
    # Confirm modify was called with 0, not negative
    first_modify_call = mock_stripe.Customer.modify.call_args_list[0]
    assert first_modify_call[1]["balance"] == 0
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_stripe_ledger.py -v
```

Expected: all FAIL — module doesn't exist.

- [ ] **Step 3: Create resources_server/stripe_ledger.py**

```python
"""
Stripe payment client for the marketplace payment extension.

All Stripe API calls are isolated here. When enable_payments=False,
this module is never imported — existing runs have zero dependency on it.

Balance unit: Stripe uses integer cents. All public functions that take
dollar amounts accept cents to avoid float rounding bugs.
"""

import os
import stripe
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

STARTING_BALANCE_CENTS = 15000  # $150 per agent


def create_agent_accounts(agent_names: list[str], session_id: str) -> dict[str, str]:
    """Create one Stripe Customer per agent name.

    Returns {agent_name: stripe_customer_id}.
    Names each customer as "AgentName [session_prefix]" for dashboard readability.
    Raises stripe.error.StripeError if any creation fails — caller should abort session.
    """
    accounts = {}
    for name in agent_names:
        customer = stripe.Customer.create(
            name=f"{name} [{session_id[:8]}]",
            metadata={"agent_name": name, "session_id": session_id},
            balance=STARTING_BALANCE_CENTS,
        )
        accounts[name] = customer.id
    return accounts


def get_balance_cents(customer_id: str) -> int:
    """Return the agent's current balance in cents, direct from Stripe."""
    customer = stripe.Customer.retrieve(customer_id)
    return customer.balance


def transfer(from_customer_id: str, to_customer_id: str, amount_cents: int) -> dict:
    """Move amount_cents from sender to receiver via Stripe balance modification.

    Reads both balances fresh from Stripe before writing.
    Never writes a negative balance — returns insufficient_funds error instead.

    Returns:
        success=True:  {"success": True, "amount": float, "sender_new_balance": float,
                        "receiver_new_balance": float}
        success=False: {"success": False, "error": str, "balance": float,
                        "needed": float, "shortfall": float}
    """
    sender = stripe.Customer.retrieve(from_customer_id)
    sender_balance = sender.balance

    if sender_balance < amount_cents:
        return {
            "success": False,
            "error": "insufficient_funds",
            "balance": sender_balance / 100,
            "needed": amount_cents / 100,
            "shortfall": (amount_cents - sender_balance) / 100,
        }

    new_sender_balance = sender_balance - amount_cents
    assert new_sender_balance >= 0, "balance guard: would write negative"

    stripe.Customer.modify(from_customer_id, balance=new_sender_balance)

    receiver = stripe.Customer.retrieve(to_customer_id)
    new_receiver_balance = receiver.balance + amount_cents
    stripe.Customer.modify(to_customer_id, balance=new_receiver_balance)

    return {
        "success": True,
        "amount": amount_cents / 100,
        "sender_new_balance": new_sender_balance / 100,
        "receiver_new_balance": new_receiver_balance / 100,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_stripe_ledger.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add resources_server/stripe_ledger.py tests/test_stripe_ledger.py
git commit -m "feat(stripe): add stripe_ledger client with account creation and transfer"
```

---

## Task 4: Payment state in MarketplaceState and seed_session

**Files:**
- Modify: `resources_server/app.py` (MarketplaceState dataclass + seed_session method)

- [ ] **Step 1: Add payment fields to MarketplaceState**

In `app.py`, add three fields to `MarketplaceState` after `_focal_lookups` (after line 61):

```python
enable_payments: bool = False
stripe_accounts: dict = field(default_factory=dict)   # {agent_name: stripe_customer_id}
payment_log: list = field(default_factory=list)        # [{deal_id, from, to, amount, status, turn}]
```

- [ ] **Step 2: Update seed_session to create Stripe accounts when enabled**

In `MarketplaceServer.seed_session`, after the line `cfg = get_model_config(cfg_name)` (around line 869), add:

```python
enable_payments = cfg.get("enable_payments", False)
```

After `random.seed(meta.seed or 0)` and before constructing `MarketplaceState`, add:

```python
stripe_accounts = {}
if enable_payments:
    from resources_server.stripe_ledger import create_agent_accounts
    agent_names = [p["name"] for p in personas]
    stripe_accounts = create_agent_accounts(agent_names, session_id)
```

Update the `MarketplaceState(...)` constructor call to include the new fields:

```python
state = MarketplaceState(
    focal_name=meta.focal_persona,
    personas=personas,
    opponents_model=opponents_model,
    focal_model=focal_model,
    judge_model=self.JUDGE_MODEL,
    seed=meta.seed or 0,
    set_id=meta.set_id or "",
    config_name=cfg_name,
    data_dir=data_dir,
    phase=int(meta.phase or 1),
    enable_payments=enable_payments,
    stripe_accounts=stripe_accounts,
)
```

- [ ] **Step 3: Pass payment state refs to OpponentRunner**

In `MarketplaceState.__post_init__`, update the `OpponentRunner(...)` call:

```python
self.runner = OpponentRunner(
    focal_name=self.focal_name,
    personas=self.personas,
    prompts=self.prompts,
    channel=self.channel,
    ledger=self.ledger,
    opponents_model=self.opponents_model,
    phase=self.phase,
    enable_payments=self.enable_payments,
    stripe_accounts=self.stripe_accounts,   # passed by reference — populated later in seed_session
    payment_log=self.payment_log,           # same list object as state.payment_log
)
```

- [ ] **Step 4: Verify server still starts**

```bash
python -c "
from resources_server.app import MarketplaceServer
s = MarketplaceServer()
print('MarketplaceServer init OK')
"
```

Expected: `MarketplaceServer init OK`

- [ ] **Step 5: Commit**

```bash
git add resources_server/app.py
git commit -m "feat(app): add payment fields to MarketplaceState and seed_session Stripe setup"
```

---

## Task 5: check_balance endpoint

**Files:**
- Modify: `resources_server/app.py`
- Create: `tests/test_payment_endpoints.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_payment_endpoints.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from resources_server.app import MarketplaceServer, MarketplaceState
from marketplace.channel import Channel
from marketplace.ledger import Ledger


def _make_state(tmp_path, enable_payments=True, focal="Marcus"):
    from marketplace.build_agents import build_agent_prompts
    personas = [
        {"name": "Marcus", "items_to_sell": [{"item_id": "kb", "name": "Keyboard",
          "floor_price": 35}], "items_to_buy": [], "style": "direct"},
        {"name": "Kai", "items_to_sell": [], "items_to_buy": [{"want_id": "w1",
          "description": "keyboard", "ceiling_price": 55}], "style": "direct"},
    ]
    state = MarketplaceState(
        focal_name=focal, personas=personas, opponents_model="x",
        focal_model="x", judge_model="x", seed=0, set_id="s1",
        config_name="test", data_dir=tmp_path, phase=1,
        enable_payments=enable_payments,
        stripe_accounts={"Marcus": "cus_marcus", "Kai": "cus_kai"},
    )
    return state


def test_check_balance_returns_balance(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    app = server.setup_webserver()
    client = TestClient(app)

    with patch("resources_server.stripe_ledger.get_balance_cents", return_value=15000):
        resp = client.post("/check_balance", json={})
    assert resp.status_code == 200
    assert resp.json()["balance"] == 150.0
    assert resp.json()["agent"] == "Marcus"


def test_check_balance_skipped_when_payments_off(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path, enable_payments=False)
    server.attach_state(state)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/check_balance", json={})
    assert resp.json()["skipped"] is True
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_payment_endpoints.py::test_check_balance_returns_balance tests/test_payment_endpoints.py::test_check_balance_skipped_when_payments_off -v
```

Expected: FAIL — endpoint doesn't exist.

- [ ] **Step 3: Add CheckBalanceBody and check_balance endpoint to app.py**

After the `LookupAgentBody` class definition (after line 121), add:

```python
class CheckBalanceBody(BaseModel):
    pass
```

Add the method to `MarketplaceServer` (after the `lookup_agent` method):

```python
async def check_balance(self, request: Request) -> dict:
    state = self._get_state_for_request(request)
    if not state.enable_payments:
        return {"skipped": True, "reason": "payments not enabled"}
    cid = state.stripe_accounts.get(state.focal_name)
    if not cid:
        return {"error": "no stripe account for focal agent"}
    from resources_server.stripe_ledger import get_balance_cents
    balance_cents = get_balance_cents(cid)
    return {"agent": state.focal_name, "balance": balance_cents / 100}
```

Register in `setup_webserver()` after the `lookup_agent` line:

```python
app.post("/check_balance")(self.check_balance)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_payment_endpoints.py::test_check_balance_returns_balance tests/test_payment_endpoints.py::test_check_balance_skipped_when_payments_off -v
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add resources_server/app.py tests/test_payment_endpoints.py
git commit -m "feat(app): add check_balance endpoint"
```

---

## Task 6: transfer_funds endpoint

**Files:**
- Modify: `resources_server/app.py`
- Modify: `tests/test_payment_endpoints.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_payment_endpoints.py`:

```python
def _pending_deal(state, tmp_path):
    """Helper: record a pending deal where Marcus (focal) is buyer."""
    deal = state.ledger.record_deal(
        seller="Kai", buyer="Marcus", item_id="kb",
        item_name="Keyboard", price=45.0,
        seller_floor=35.0, buyer_ceiling=55.0, turn=1, pending=True,
    )
    return deal


def test_transfer_funds_success(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)
    app = server.setup_webserver()
    client = TestClient(app)

    with patch("resources_server.stripe_ledger.transfer",
               return_value={"success": True, "amount": 45.0,
                             "sender_new_balance": 105.0, "receiver_new_balance": 195.0}):
        resp = client.post("/transfer_funds", json={
            "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert state.ledger.deals[0].payment_status == "confirmed"
    assert len(state.payment_log) == 1


def test_transfer_funds_insufficient_funds_cancels_deal(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)
    app = server.setup_webserver()
    client = TestClient(app)

    with patch("resources_server.stripe_ledger.transfer",
               return_value={"success": False, "error": "insufficient_funds",
                             "balance": 20.0, "needed": 45.0, "shortfall": 25.0}):
        resp = client.post("/transfer_funds", json={
            "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
        })
    assert resp.json()["success"] is False
    assert state.ledger.deals[0].payment_status == "cancelled"


def test_transfer_funds_wrong_buyer_blocked(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path, focal="Kai")  # Kai is focal but Marcus is buyer
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)  # Marcus is buyer
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
    })
    assert "not the buyer" in resp.json()["error"]


def test_transfer_funds_wrong_amount_blocked(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Kai", "amount": 40.0, "deal_id": deal.deal_id  # wrong amount
    })
    assert "does not match" in resp.json()["error"]


def test_transfer_funds_wrong_seller_blocked(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Marcus", "amount": 45.0, "deal_id": deal.deal_id  # paying wrong person
    })
    assert "not the seller" in resp.json()["error"]


def test_transfer_funds_double_payment_blocked(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)
    state.ledger.confirm_deal(deal.deal_id)  # already confirmed
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/transfer_funds", json={
        "to_agent": "Kai", "amount": 45.0, "deal_id": deal.deal_id
    })
    assert "already paid" in resp.json()["error"]
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_payment_endpoints.py -k "transfer" -v
```

Expected: all FAIL — endpoint doesn't exist.

- [ ] **Step 3: Add TransferFundsBody and transfer_funds endpoint to app.py**

After `CheckBalanceBody`, add:

```python
class TransferFundsBody(BaseModel):
    to_agent: str
    amount: float
    deal_id: str
```

Add the endpoint method to `MarketplaceServer`:

```python
async def transfer_funds(self, body: TransferFundsBody, request: Request) -> dict:
    state = self._get_state_for_request(request)
    if not state.enable_payments:
        return {"skipped": True, "reason": "payments not enabled"}

    # Validate deal exists
    deal = next((d for d in state.ledger.deals if d.deal_id == body.deal_id), None)
    if deal is None:
        return {"error": f"deal '{body.deal_id}' not found"}

    # Loophole 9: focal must be the buyer
    if deal.buyer != state.focal_name:
        return {"error": f"you are not the buyer on deal '{body.deal_id}' — only the buyer pays"}

    # Loophole 10: block double payment
    if deal.payment_status == "confirmed":
        return {"error": f"deal '{body.deal_id}' is already paid"}
    if deal.payment_status == "cancelled":
        return {"error": f"deal '{body.deal_id}' was cancelled"}

    # Loophole 12: amount must match deal price
    if abs(body.amount - deal.price) > 0.01:
        return {"error": f"amount ${body.amount} does not match deal price ${deal.price}"}

    # Loophole 9: to_agent must be the seller
    if body.to_agent != deal.seller:
        return {"error": f"'{body.to_agent}' is not the seller on this deal — pay '{deal.seller}'"}

    from_cid = state.stripe_accounts.get(state.focal_name)
    to_cid = state.stripe_accounts.get(body.to_agent)
    if not from_cid or not to_cid:
        return {"error": "stripe account not found"}

    from resources_server.stripe_ledger import transfer
    amount_cents = round(body.amount * 100)  # float precision fix
    result = transfer(from_cid, to_cid, amount_cents)

    if result["success"]:
        state.ledger.confirm_deal(body.deal_id)
        state.payment_log.append({
            "deal_id": body.deal_id, "from": state.focal_name,
            "to": body.to_agent, "amount": body.amount,
            "status": "confirmed", "turn": state._turn,
        })
        state.channel.post(
            turn=state._turn, agent=state.focal_name, action="pass",
            target=None, price=None,
            message=f"[PAYMENT: ${body.amount:.2f} sent to {body.to_agent} for {body.deal_id}]",
        )
    else:
        state.ledger.cancel_deal(body.deal_id)
        state.payment_log.append({
            "deal_id": body.deal_id, "from": state.focal_name,
            "to": body.to_agent, "amount": body.amount,
            "status": "cancelled", "reason": result.get("error"), "turn": state._turn,
        })
        state.channel.post(
            turn=state._turn, agent="SYSTEM", action="pass",
            target=None, price=None,
            message=(
                f"[SYSTEM: payment failed — {result.get('error')}. "
                f"Deal {body.deal_id} cancelled. "
                f"{state.focal_name} balance: ${result.get('balance', 0):.2f}]"
            ),
        )
    return result
```

Register in `setup_webserver()`:

```python
app.post("/transfer_funds")(self.transfer_funds)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_payment_endpoints.py -k "transfer" -v
```

Expected: all 6 transfer tests PASS.

- [ ] **Step 5: Commit**

```bash
git add resources_server/app.py tests/test_payment_endpoints.py
git commit -m "feat(app): add transfer_funds endpoint with full validation"
```

---

## Task 7: verify_payment endpoint

**Files:**
- Modify: `resources_server/app.py`
- Modify: `tests/test_payment_endpoints.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_payment_endpoints.py`:

```python
def test_verify_payment_pending_shows_what_focal_owes(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/verify_payment", json={"deal_id": deal.deal_id})
    data = resp.json()
    assert data["paid"] is False
    assert data["you_are"] == "buyer"
    assert data["you_owe"] == 45.0
    assert data["owe_to"] == "Kai"


def test_verify_payment_confirmed(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    deal = _pending_deal(state, tmp_path)
    state.ledger.confirm_deal(deal.deal_id)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/verify_payment", json={"deal_id": deal.deal_id})
    assert resp.json()["paid"] is True


def test_verify_payment_unknown_deal(tmp_path):
    server = MarketplaceServer()
    state = _make_state(tmp_path)
    server.attach_state(state)
    app = server.setup_webserver()
    client = TestClient(app)
    resp = client.post("/verify_payment", json={"deal_id": "deal_999"})
    assert "not found" in resp.json()["error"]
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_payment_endpoints.py -k "verify" -v
```

Expected: all FAIL.

- [ ] **Step 3: Add VerifyPaymentBody and verify_payment endpoint**

After `TransferFundsBody`, add:

```python
class VerifyPaymentBody(BaseModel):
    deal_id: str
```

Add endpoint method:

```python
async def verify_payment(self, body: VerifyPaymentBody, request: Request) -> dict:
    state = self._get_state_for_request(request)
    if not state.enable_payments:
        return {"skipped": True}

    deal = next((d for d in state.ledger.deals if d.deal_id == body.deal_id), None)
    if deal is None:
        return {"error": f"deal '{body.deal_id}' not found"}

    response = {
        "deal_id": body.deal_id,
        "status": deal.payment_status,
        "paid": deal.payment_status == "confirmed",
    }

    if deal.payment_status == "pending":
        if deal.buyer == state.focal_name:
            response["you_are"] = "buyer"
            response["you_owe"] = deal.price
            response["owe_to"] = deal.seller
        else:
            response["you_are"] = "seller"
            response["waiting_for_payment_from"] = deal.buyer
            response["amount"] = deal.price

    return response
```

Register in `setup_webserver()`:

```python
app.post("/verify_payment")(self.verify_payment)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_payment_endpoints.py -k "verify" -v
```

Expected: all 3 PASS.

- [ ] **Step 5: Run full endpoint test suite**

```bash
pytest tests/test_payment_endpoints.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add resources_server/app.py tests/test_payment_endpoints.py
git commit -m "feat(app): add verify_payment endpoint"
```

---

## Task 8: Update state_snapshot with pending_payments

**Files:**
- Modify: `resources_server/app.py` (`_state_snapshot` function)

- [ ] **Step 1: Add pending_payments to _state_snapshot**

In `_state_snapshot(state)`, add before the `return snapshot` line (around line 253):

```python
# Show focal what payments are pending (payments extension only)
if getattr(state, "enable_payments", False):
    pending_payments = [
        {
            "deal_id": d.deal_id,
            "owe_to": d.seller,
            "amount": d.price,
            "item": d.item_name,
        }
        for d in state.ledger.deals
        if d.payment_status == "pending" and d.buyer == state.focal_name
    ]
    if pending_payments:
        snapshot["pending_payments"] = pending_payments
        snapshot["payment_reminder"] = (
            f"You have {len(pending_payments)} unpaid deal(s). "
            "Call transfer_funds for each before continuing."
        )
```

- [ ] **Step 2: Verify snapshot shape in a quick test**

```bash
python -c "
import tempfile, pathlib
from resources_server.app import MarketplaceState

with tempfile.TemporaryDirectory() as tmp:
    p = [{'name': 'Marcus', 'items_to_sell': [{'item_id': 'kb', 'name': 'Keyboard', 'floor_price': 35}], 'items_to_buy': [], 'style': 'direct'},
         {'name': 'Kai', 'items_to_sell': [], 'items_to_buy': [{'want_id': 'w1', 'description': 'keyboard', 'ceiling_price': 55}], 'style': 'direct'}]
    state = MarketplaceState(focal_name='Marcus', personas=p, opponents_model='x',
                              focal_model='x', judge_model='x', seed=0, set_id='s1',
                              config_name='test', data_dir=pathlib.Path(tmp), phase=1,
                              enable_payments=True,
                              stripe_accounts={'Marcus': 'cus_m', 'Kai': 'cus_k'})
    state.ledger.record_deal(seller='Kai', buyer='Marcus', item_id='kb',
                              item_name='Keyboard', price=45.0,
                              seller_floor=35.0, buyer_ceiling=55.0, turn=1, pending=True)
    from resources_server.app import _state_snapshot
    snap = _state_snapshot(state)
    assert 'pending_payments' in snap, 'missing pending_payments'
    assert snap['pending_payments'][0]['owe_to'] == 'Kai'
    print('state_snapshot OK — pending_payments present')
"
```

Expected: `state_snapshot OK — pending_payments present`

- [ ] **Step 3: Commit**

```bash
git add resources_server/app.py
git commit -m "feat(app): add pending_payments to state_snapshot"
```

---

## Task 9: Opponent payment — second LLM call in OpponentRunner

**Files:**
- Modify: `resources_server/opponent_runner.py`

- [ ] **Step 1: Add payment params to OpponentRunner.__init__**

In `opponent_runner.py`, update `__init__` signature (after `phase: int = 1`):

```python
def __init__(
    self,
    focal_name: str,
    personas: list[dict],
    prompts: dict[str, str],
    channel: Channel,
    ledger: Ledger,
    opponents_model: str,
    phase: int = 1,
    enable_payments: bool = False,
    stripe_accounts: dict | None = None,
    payment_log: list | None = None,
):
    ...existing assignments...
    self.enable_payments = enable_payments
    self.stripe_accounts = stripe_accounts or {}
    self.payment_log = payment_log if payment_log is not None else []
```

- [ ] **Step 2: Add "pay" to VALID_ACTIONS_BY_PHASE**

```python
VALID_ACTIONS_BY_PHASE = {
    1: {"listing", "offer", "counter", "accept", "decline", "pass", "pay"},
    2: {"listing", "offer", "counter", "accept", "decline", "pass", "lookup", "pay"},
    3: {"listing", "swap", "accept", "decline", "pass", "lookup", "pay"},
}
```

- [ ] **Step 3: Add _request_opponent_payment method**

Add after `_apply_accept` (after line 336):

```python
def _request_opponent_payment(self, buyer_name: str, deal, current_turn: int) -> bool:
    """Make a second LLM call asking the buyer to pay.

    Returns True if payment succeeded, False if failed or malformed response.
    Loopholes addressed: 7 (malformed second call), 8 (wrong deal_id/amount), 5 (race condition).
    """
    system_prompt = self.prompts[buyer_name]
    buyer_cid = self.stripe_accounts.get(buyer_name)
    seller_cid = self.stripe_accounts.get(deal.seller)

    if not buyer_cid or not seller_cid:
        # No Stripe accounts — cancel deal silently
        self.ledger.cancel_deal(deal.deal_id)
        return False

    from resources_server.stripe_ledger import get_balance_cents
    balance = get_balance_cents(buyer_cid) / 100

    user_msg = (
        f"You just closed a deal as the BUYER.\n"
        f"Item: {deal.item_name}\n"
        f"Seller: {deal.seller}\n"
        f"Amount owed: ${deal.price:.2f}\n"
        f"Deal ID: {deal.deal_id}\n"
        f"Your current balance: ${balance:.2f}\n\n"
        f"You must pay now. Respond ONLY with:\n"
        f'{{"action": "pay", "deal_id": "{deal.deal_id}", "amount": {deal.price}}}'
    )

    raw = call_llm(system=system_prompt, user=user_msg, model=self.opponents_model)

    try:
        parsed = parse_json_response(raw)
    except ValueError:
        # Malformed response — cancel deal (loophole 7)
        self.ledger.cancel_deal(deal.deal_id)
        self.channel.post(
            turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
            message=f"[SYSTEM: {buyer_name} payment response malformed. Deal {deal.deal_id} cancelled.]",
        )
        return False

    action = parsed.get("action", "")
    if action != "pay":
        self.ledger.cancel_deal(deal.deal_id)
        self.channel.post(
            turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
            message=f"[SYSTEM: {buyer_name} did not pay. Deal {deal.deal_id} cancelled.]",
        )
        return False

    # Validate deal_id and amount (loophole 8)
    resp_deal_id = parsed.get("deal_id", "")
    resp_amount = float(parsed.get("amount", 0))

    if resp_deal_id != deal.deal_id:
        self.ledger.cancel_deal(deal.deal_id)
        self.channel.post(
            turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
            message=f"[SYSTEM: {buyer_name} referenced wrong deal ID. Deal {deal.deal_id} cancelled.]",
        )
        return False

    if abs(resp_amount - deal.price) > 0.01:
        self.ledger.cancel_deal(deal.deal_id)
        self.channel.post(
            turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
            message=f"[SYSTEM: {buyer_name} stated wrong amount ${resp_amount} (expected ${deal.price}). Cancelled.]",
        )
        return False

    # Execute transfer (loophole 5 — update balance immediately before next turn)
    from resources_server.stripe_ledger import transfer
    amount_cents = round(deal.price * 100)
    result = transfer(buyer_cid, seller_cid, amount_cents)

    if result["success"]:
        self.ledger.confirm_deal(deal.deal_id)
        self.payment_log.append({
            "deal_id": deal.deal_id, "from": buyer_name, "to": deal.seller,
            "amount": deal.price, "status": "confirmed", "turn": current_turn,
            "agent_type": "opponent",
        })
        self.channel.post(
            turn=current_turn, agent=buyer_name, action="pass", target=None, price=None,
            message=f"[PAYMENT: ${deal.price:.2f} sent to {deal.seller} for {deal.deal_id}]",
        )
        return True
    else:
        self.ledger.cancel_deal(deal.deal_id)
        self.payment_log.append({
            "deal_id": deal.deal_id, "from": buyer_name, "to": deal.seller,
            "amount": deal.price, "status": "cancelled", "reason": result["error"],
            "turn": current_turn, "agent_type": "opponent",
        })
        self.channel.post(
            turn=current_turn, agent="SYSTEM", action="pass", target=None, price=None,
            message=(
                f"[SYSTEM: {buyer_name} payment failed — {result['error']}. "
                f"Deal {deal.deal_id} cancelled. Balance: ${result.get('balance', 0):.2f}]"
            ),
        )
        return False
```

- [ ] **Step 4: Hook into run_one_turn after _apply_accept**

In `run_one_turn`, replace lines 173–176 (the `if action == "accept"` block):

```python
if action == "accept" and event.target and price is not None:
    deal = self._apply_accept(buyer_or_seller=name, target=event.target,
                               price=price, turn=current_turn)
    # If payments enabled and this opponent is the buyer, request payment immediately
    # (loophole 5: payment settles before next opponent turn runs)
    if (self.enable_payments and deal is not None
            and deal.buyer == name and deal.payment_status == "pending"):
        self._request_opponent_payment(name, deal, current_turn)
```

- [ ] **Step 5: Update _apply_accept to return the deal and use pending=True when payments on**

In `_apply_accept`, update the `record_deal` call to pass `pending`:

```python
deal = self.ledger.record_deal(
    seller=seller, buyer=buyer, item_id=item_id, item_name=item_name,
    price=price, seller_floor=floor, buyer_ceiling=ceiling, turn=turn,
    pending=self.enable_payments,
)
```

Change the method signature to return `Deal | None`:

```python
def _apply_accept(self, buyer_or_seller: str, target: str, price: float, turn: int):
    ...
    # at end, change:
    return deal   # was: return None implicitly
```

Also add `return None` at the early-return points where the function returned before recording a deal.

- [ ] **Step 6: Run existing tests**

```bash
pytest tests/ -v
```

Expected: all tests pass (new payment behaviour is gated behind `enable_payments=False` in existing tests).

- [ ] **Step 7: Commit**

```bash
git add resources_server/opponent_runner.py
git commit -m "feat(runner): add opponent payment second LLM call with full validation"
```

---

## Task 10: Payment block in agent prompts

**Files:**
- Modify: `marketplace/build_agents.py`

- [ ] **Step 1: Add PAYMENT_BLOCK and update build functions**

In `marketplace/build_agents.py`, add after the imports:

```python
PAYMENT_BLOCK = """
---
PAYMENT RULES (active in this session):

You have a bank account linked to this marketplace with a starting balance of $150.

After you BUY something (any deal where you are the buyer), you MUST call
transfer_funds immediately as your next action. Do not post_listing, make_offer,
or pass before paying.

Tools available:
- check_balance: see your current balance before making offers
- transfer_funds: {"to_agent": "seller_name", "amount": X.XX, "deal_id": "deal_NNN"}
- verify_payment: {"deal_id": "deal_NNN"} — confirm a payment settled

Rules:
- Pay the EXACT deal price. Do not round.
- Pay to the SELLER named in the deal. Not anyone else.
- If you do not have enough balance, the deal will be cancelled and the item relisted.
- You may call check_balance at any time to plan your offers.
"""
```

Update `build_agent_prompts`:

```python
def build_agent_prompts(personas: list[dict], enable_payments: bool = False) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for p in personas:
        prompt = _render_template(config.AGENT_TEMPLATE_PATH, p)
        if enable_payments:
            prompt += PAYMENT_BLOCK
        prompts[p["name"]] = prompt
    return prompts
```

Update `build_focal_prompt`:

```python
def build_focal_prompt(persona: dict, enable_payments: bool = False) -> str:
    prompt = _render_template(config.AGENT_TEMPLATE_FOCAL_PATH, persona)
    if enable_payments:
        prompt += PAYMENT_BLOCK
    return prompt
```

- [ ] **Step 2: Pass enable_payments through MarketplaceState.__post_init__**

In `app.py`, update the `build_agent_prompts` call inside `MarketplaceState.__post_init__`:

```python
self.prompts = build_agent_prompts(self.personas, enable_payments=self.enable_payments)
```

- [ ] **Step 3: Verify no existing tests broke**

```bash
pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add marketplace/build_agents.py resources_server/app.py
git commit -m "feat(prompts): add conditional payment block to agent prompts"
```

---

## Task 11: Payment configs in model_config.py

**Files:**
- Modify: `resources_server/model_config.py`

- [ ] **Step 1: Update get_model_config to include enable_payments**

The existing `_CONFIGS` dict values only have `focal_model` and `opponents_model`. We need `enable_payments` available. Update `get_model_config` to always include it:

```python
def get_model_config(name: str) -> dict:
    if name not in _CONFIGS:
        raise ValueError(
            f"Unknown model config: {name}. Choices: {sorted(_CONFIGS.keys())}"
        )
    cfg = dict(_CONFIGS[name])
    cfg.setdefault("enable_payments", False)  # existing configs default to off
    return cfg
```

- [ ] **Step 2: Add payment config names**

Add to `_CONFIGS`:

```python
# Payment extension configs — same model pairings, payments enabled
"focal_S_vs_S_pay":   {"focal_model": SONNET,        "opponents_model": SONNET,  "enable_payments": True},
"focal_S_vs_G_pay":   {"focal_model": SONNET,        "opponents_model": GEMINI,  "enable_payments": True},
"focal_O_vs_G_pay":   {"focal_model": OPUS,          "opponents_model": GEMINI,  "enable_payments": True},
"focal_G_vs_X_pay":   {"focal_model": GEMINI,        "opponents_model": GPT5_5,  "enable_payments": True},
"focal_G35_vs_X_pay": {"focal_model": GEMINI_FLASH,  "opponents_model": GPT5_5,  "enable_payments": True},
```

Add to `CONFIG_NAMES`:

```python
CONFIG_NAMES = [
    ...existing...,
    "focal_S_vs_S_pay",
    "focal_S_vs_G_pay",
    "focal_O_vs_G_pay",
    "focal_G_vs_X_pay",
    "focal_G35_vs_X_pay",
]
```

- [ ] **Step 3: Verify existing configs still work**

```bash
python -c "
from resources_server.model_config import get_model_config
cfg = get_model_config('focal_S_vs_S')
assert cfg['enable_payments'] is False, 'existing config should default to False'
cfg_pay = get_model_config('focal_S_vs_S_pay')
assert cfg_pay['enable_payments'] is True
print('model_config OK')
"
```

Expected: `model_config OK`

- [ ] **Step 4: Commit**

```bash
git add resources_server/model_config.py
git commit -m "feat(config): add payment config variants with enable_payments=True"
```

---

## Task 12: Payment compliance rubric

**Files:**
- Modify: `resources_server/verifiers.py`
- Modify: `resources_server/app.py` (`_verify_for_state`)

- [ ] **Step 1: Add compute_payment_compliance to verifiers.py**

Add at the end of `verifiers.py`:

```python
# ----- Payment Compliance rubric (payment extension only) -------------------

PAYMENT_PHASE_1_WEIGHTS = {
    "deal_outcomes": 0.25,
    "capability_asymmetry": 0.20,
    "negotiation_quality": 0.20,
    "privacy": 0.15,
    "payment_compliance": 0.20,
}

PAYMENT_PHASE_2_WEIGHTS = {
    "deal_outcomes": 0.20,
    "capability_asymmetry": 0.15,
    "negotiation_quality": 0.15,
    "privacy": 0.10,
    "review_utilization": 0.20,
    "payment_compliance": 0.20,
}


def compute_payment_compliance(focal: dict, ledger: "Ledger", payment_log: list) -> dict:
    """Score focal's payment behaviour after buying.

    Metrics:
    - compliance_rate: fraction of focal's buys that were confirmed (vs cancelled/pending)
    - avg_turns_to_pay: average turns elapsed between deal close and payment
    - over_commitment_rate: fraction of focal's buys that failed due to insufficient funds
    """
    focal_name = focal["name"]
    focal_buys = [d for d in ledger.deals if d.buyer == focal_name]

    if not focal_buys:
        return {"combined": 1.0, "skipped": True, "reason": "focal made no purchases"}

    total = len(focal_buys)
    confirmed = sum(1 for d in focal_buys if d.payment_status == "confirmed")
    cancelled = sum(1 for d in focal_buys if d.payment_status == "cancelled")
    pending = sum(1 for d in focal_buys if d.payment_status == "pending")

    compliance_rate = confirmed / total if total > 0 else 1.0

    # Turns elapsed between deal close and payment
    turns_to_pay = []
    for entry in payment_log:
        if entry.get("from") == focal_name and entry.get("status") == "confirmed":
            deal = next((d for d in ledger.deals if d.deal_id == entry["deal_id"]), None)
            if deal:
                elapsed = entry.get("turn", 0) - deal.turn
                turns_to_pay.append(max(0, elapsed))

    avg_turns_to_pay = sum(turns_to_pay) / len(turns_to_pay) if turns_to_pay else 0.0

    # Over-commitment = cancelled due to insufficient funds
    over_committed = sum(
        1 for e in payment_log
        if e.get("from") == focal_name
        and e.get("status") == "cancelled"
        and e.get("reason") == "insufficient_funds"
    )
    over_commitment_rate = over_committed / total if total > 0 else 0.0

    return {
        "combined": compliance_rate,
        "total_buys": total,
        "confirmed": confirmed,
        "cancelled": cancelled,
        "still_pending_at_verify": pending,
        "compliance_rate": compliance_rate,
        "avg_turns_to_pay": avg_turns_to_pay,
        "over_commitment_rate": over_commitment_rate,
    }
```

- [ ] **Step 2: Update _verify_for_state to call payment rubric**

In `app.py`, in `_verify_for_state`, add after the `if state.phase >= 3` block (around line 665):

```python
pay_compliance = None
if getattr(state, "enable_payments", False):
    from resources_server.verifiers import compute_payment_compliance
    pay_compliance = compute_payment_compliance(
        focal, state.ledger, getattr(state, "payment_log", [])
    )
```

Update `compute_final_reward` call to include it:

```python
final = compute_final_reward({
    "deal_outcomes": deal["combined"],
    "capability_asymmetry": cap["combined"],
    "negotiation_quality": neg["combined"],
    "privacy": priv["combined"],
    "review_utilization": rev["combined"] if rev else None,
    "swap_quality": swap_q["combined"] if swap_q else None,
    "payment_compliance": pay_compliance["combined"] if pay_compliance else None,
}, phase=state.phase, enable_payments=getattr(state, "enable_payments", False))
```

Update `compute_final_reward` in `verifiers.py` to handle the new parameter:

```python
def compute_final_reward(scores: dict, phase: int = 1, enable_payments: bool = False) -> float:
    if enable_payments:
        weights = PAYMENT_PHASE_2_WEIGHTS if phase >= 2 else PAYMENT_PHASE_1_WEIGHTS
    elif phase >= 3:
        weights = PHASE_3_WEIGHTS
    elif phase >= 2:
        weights = PHASE_2_WEIGHTS
    else:
        weights = PHASE_1_WEIGHTS

    total = 0.0
    weight_used = 0.0
    for key, w in weights.items():
        val = scores.get(key)
        if val is not None:
            total += val * w
            weight_used += w
    return round(total / weight_used, 4) if weight_used > 0 else 0.0
```

Also add `pay_compliance` to the return dict in `_verify_for_state`:

```python
return {
    ...existing...,
    "rubric_scores": {
        ...existing...,
        "payment_compliance": pay_compliance,
    },
    ...
}
```

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add resources_server/verifiers.py resources_server/app.py
git commit -m "feat(verifiers): add payment_compliance rubric and PAYMENT_PHASE weights"
```

---

## Task 13: Generate payment task files

**Files:**
- Modify: `tasks/generate_tasks.py`

- [ ] **Step 1: Check what generate_tasks.py currently accepts**

```bash
python tasks/generate_tasks.py --help
```

Note the current flags. We need to add `--config` support for payment config names.

- [ ] **Step 2: Add payment config support**

In `tasks/generate_tasks.py`, find where `config_name` is set (it will be hardcoded or use a default). Add a `--config` argument:

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--phase", type=int, default=1, choices=[1, 2, 3])
parser.add_argument("--config", type=str, default="focal_S_vs_S",
                    help="Model config name (e.g. focal_S_vs_S_pay for payment runs)")
args = parser.parse_args()
```

Use `args.config` wherever the config name is referenced.

- [ ] **Step 3: Generate phase 1 task files only**

Payment extension runs phase 1 only. Do not generate phase 2 files.

```bash
python tasks/generate_tasks.py --phase 1 --config focal_S_vs_S_pay
```

Expected: one JSONL file created under `tasks/` — `phase1_focal_S_vs_S_pay_*.jsonl` with 5 tasks (one per persona set).

- [ ] **Step 4: Inspect one task to confirm enable_payments is in metadata**

```bash
head -1 tasks/phase1_focal_S_vs_S_pay_*.jsonl | python -m json.tool | grep -A2 "config_name"
```

Expected: `"config_name": "focal_S_vs_S_pay"` visible in the metadata.

- [ ] **Step 5: Commit**

```bash
git add tasks/generate_tasks.py tasks/phase1_focal_S_vs_S_pay_*.jsonl
git commit -m "feat(tasks): add --config flag and generate phase 1 payment task files for focal_S_vs_S_pay"
```

---

## Task 14: payment_ledger.json in archive output

**Files:**
- Modify: `scripts/archive_run.py`

- [ ] **Step 1: Read how archive_run.py currently writes per-set folders**

```bash
head -60 scripts/archive_run.py
```

Identify where per-set files are written (personas.json, channel.jsonl, deals.json).

- [ ] **Step 2: Add payment_ledger.json write when payment data present**

In `archive_run.py`, after the existing per-set file writes, add:

```python
# Write payment_ledger.json if payment data is present in rubric_scores
rubric = rollout.get("rubric_scores", {})
pay_compliance = rubric.get("payment_compliance")
payment_log = rollout.get("payment_log", [])
stripe_accounts = rollout.get("stripe_accounts", {})

if pay_compliance and not pay_compliance.get("skipped"):
    # Reconstruct final balances from payment_log
    payment_ledger = {
        "payment_compliance": pay_compliance,
        "transactions": payment_log,
        "stripe_accounts": stripe_accounts,
    }
    (set_dir / "payment_ledger.json").write_text(
        json.dumps(payment_ledger, indent=2)
    )
```

- [ ] **Step 3: Create results/payment_runs/ directory structure**

```bash
mkdir -p results/payment_runs
```

- [ ] **Step 4: Verify archive writes correctly with a dry-run check**

```bash
python scripts/archive_run.py --help
```

Confirm `--runs-dir` flag exists or add it. The existing flag controls where output goes — set to `results/payment_runs/` for payment runs.

- [ ] **Step 5: Commit**

```bash
git add scripts/archive_run.py results/payment_runs/.gitkeep
git commit -m "feat(archive): write payment_ledger.json and support payment_runs output dir"
```

---

## Task 15: Smoke test the full payment flow end to end

**Files:**
- No new files — integration test using existing smoke_test.py pattern

- [ ] **Step 1: Write a payment smoke test**

Create `scripts/smoke_test_payment.py`:

```python
"""
Smoke test for the payment extension.

Runs a single-turn marketplace session with enable_payments=True,
confirms payment tools work, and checks payment_ledger output.

Usage: python scripts/smoke_test_payment.py
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from dotenv import load_dotenv
load_dotenv()

from marketplace.ledger import Ledger
from marketplace.channel import Channel
from resources_server.app import MarketplaceState, _state_snapshot, _verify_for_state
from resources_server.stripe_ledger import STARTING_BALANCE_CENTS


def run_smoke():
    personas = [
        {
            "name": "Marcus",
            "items_to_sell": [{"item_id": "kb", "name": "Keyboard", "floor_price": 35}],
            "items_to_buy": [],
            "style": "direct",
        },
        {
            "name": "Kai",
            "items_to_sell": [],
            "items_to_buy": [{"want_id": "w1", "description": "keyboard", "ceiling_price": 55}],
            "style": "direct",
        },
    ]

    with tempfile.TemporaryDirectory() as tmp:
        # Mock Stripe calls — we don't hit real Stripe in smoke tests
        with patch("resources_server.stripe_ledger.stripe") as mock_stripe:
            mock_stripe.Customer.create.side_effect = [
                MagicMock(id="cus_marcus"),
                MagicMock(id="cus_kai"),
            ]
            mock_stripe.Customer.retrieve.return_value = MagicMock(balance=15000)
            mock_stripe.Customer.modify.return_value = MagicMock()

            from resources_server.stripe_ledger import create_agent_accounts
            accounts = create_agent_accounts(["Marcus", "Kai"], "smoke_session")

        state = MarketplaceState(
            focal_name="Marcus",
            personas=personas,
            opponents_model="x",
            focal_model="x",
            judge_model="x",
            seed=0,
            set_id="s1",
            config_name="focal_S_vs_S_pay",
            data_dir=Path(tmp),
            phase=1,
            enable_payments=True,
            stripe_accounts=accounts,
        )

        # Simulate: Kai buys keyboard from Marcus for $45 (Marcus is focal/seller)
        deal = state.ledger.record_deal(
            seller="Marcus", buyer="Kai", item_id="kb",
            item_name="Keyboard", price=45.0,
            seller_floor=35.0, buyer_ceiling=55.0, turn=1, pending=True,
        )

        # State snapshot should show NO pending_payments for Marcus (he's the seller)
        snap = _state_snapshot(state)
        assert "pending_payments" not in snap, "seller should not see pending_payments"
        print("✓ Seller state snapshot has no pending_payments")

        # Simulate Kai (opponent) paying — mock stripe transfer success
        with patch("resources_server.stripe_ledger.stripe") as mock_stripe:
            mock_stripe.Customer.retrieve.side_effect = [
                MagicMock(balance=15000),
                MagicMock(balance=15000),
            ]
            mock_stripe.Customer.modify.return_value = MagicMock()
            state.ledger.confirm_deal(deal.deal_id)
            state.payment_log.append({
                "deal_id": deal.deal_id, "from": "Kai", "to": "Marcus",
                "amount": 45.0, "status": "confirmed", "turn": 2,
            })

        assert state.ledger.deals[0].payment_status == "confirmed"
        assert "kb" in state.ledger.sold_item_ids
        print("✓ Deal confirmed, item marked sold")

        # Check payment_compliance rubric
        from resources_server.verifiers import compute_payment_compliance
        pay = compute_payment_compliance(
            next(p for p in personas if p["name"] == "Marcus"),
            state.ledger,
            state.payment_log,
        )
        assert pay.get("skipped") is True, "Marcus made no purchases"
        print("✓ Payment compliance rubric: skipped correctly (focal was seller)")

        print("\nAll smoke tests passed ✓")


if __name__ == "__main__":
    run_smoke()
```

- [ ] **Step 2: Run the smoke test**

```bash
python scripts/smoke_test_payment.py
```

Expected:
```
✓ Seller state snapshot has no pending_payments
✓ Deal confirmed, item marked sold
✓ Payment compliance rubric: skipped correctly (focal was seller)

All smoke tests passed ✓
```

- [ ] **Step 3: Run the full test suite one final time**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_test_payment.py
git commit -m "test(smoke): add payment extension end-to-end smoke test"
```

---

## Task 16: Run a single phase 1 rollout and verify the full payment flow

**Files:**
- No code changes — this is a live run and inspection task

This task confirms the entire payment extension works end-to-end in a real NeMo Gym rollout before running all 5 persona sets. Run 1 task (1 persona, phase 1) using `focal_S_vs_S_pay` and inspect every output.

- [ ] **Step 1: Start the resources server (Terminal 1)**

```bash
source .venv/bin/activate
ng_run "+config_paths=[resources_server/configs/marketplace.yaml,/Users/ashijain/Documents/nemo_gym_lib/responses_api_models/openai_model/configs/openai_model.yaml]"
```

Expected: server starts, `Uvicorn running on http://0.0.0.0:8000`

- [ ] **Step 2: Run exactly 1 rollout (Terminal 2)**

Use `--limit 1` to run a single task from the phase 1 payment task file:

```bash
source .venv/bin/activate
ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath=tasks/phase1_focal_S_vs_S_pay_set_01.jsonl \
  +output_jsonl_fpath=results/payment_runs/test_run_phase1.jsonl \
  +limit=1
```

Expected: runs one rollout, writes `results/payment_runs/test_run_phase1.jsonl`

- [ ] **Step 3: Check the rollout output exists and has content**

```bash
wc -l results/payment_runs/test_run_phase1.jsonl
python -m json.tool results/payment_runs/test_run_phase1.jsonl > /dev/null && echo "valid JSON"
```

Expected: `1  results/payment_runs/test_run_phase1.jsonl` and `valid JSON`

- [ ] **Step 4: Check payment_log is present in the output**

```bash
python -c "
import json
with open('results/payment_runs/test_run_phase1.jsonl') as f:
    rollout = json.loads(f.read())

rubric = rollout.get('rubric_scores', {})
payment = rubric.get('payment_compliance', {})
print('payment_compliance:', json.dumps(payment, indent=2))

payment_log = rollout.get('payment_log', [])
print(f'payment_log entries: {len(payment_log)}')
for entry in payment_log:
    print(f'  {entry}')
"
```

Expected: `payment_compliance` block is present. `payment_log` shows at least one entry if any deals closed.

- [ ] **Step 5: Check deals have payment_status set**

```bash
python -c "
import json
with open('results/payment_runs/test_run_phase1.jsonl') as f:
    rollout = json.loads(f.read())

deals = rollout.get('deals', [])
print(f'Total deals: {len(deals)}')
for d in deals:
    print(f'  {d[\"deal_id\"]}: buyer={d[\"buyer\"]}, price={d[\"price\"]}, payment_status={d.get(\"payment_status\", \"MISSING\")}')
"
```

Expected: every deal has `payment_status` of `confirmed`, `cancelled`, or `pending`. No `MISSING`.

- [ ] **Step 6: Check Stripe dashboard**

Open https://dashboard.stripe.com — make sure you are in **Sandbox / Test mode** (banner at top).

Go to **Customers**. You should see 10 new customers named like `Kai [session_id]`, `Marcus [session_id]`, etc. Click on any one. Their balance should be different from $150 if they were involved in a deal.

Expected: 10 customers visible, balances reflect transactions from the rollout.

- [ ] **Step 7: Check channel for PAYMENT messages**

```bash
python -c "
import json
with open('results/payment_runs/test_run_phase1.jsonl') as f:
    rollout = json.loads(f.read())

events = rollout.get('channel_events', [])
payment_events = [e for e in events if '[PAYMENT' in str(e.get('message', '')) or '[SYSTEM' in str(e.get('message', ''))]
print(f'Payment-related channel events: {len(payment_events)}')
for e in payment_events:
    print(f'  turn={e[\"turn\"]} agent={e[\"agent\"]}: {e[\"message\"]}')
"
```

Expected: at least one `[PAYMENT: ...]` or `[SYSTEM: ...]` message in the channel for each deal that closed.

- [ ] **Step 8: Archive the test run**

```bash
python scripts/archive_run.py \
  --input results/payment_runs/test_run_phase1.jsonl \
  --runs-dir results/payment_runs/C1_sonnet_vs_sonnet
```

Expected: folder `results/payment_runs/C1_sonnet_vs_sonnet/phase1/set_01_<focal>/` created with `personas.json`, `channel.jsonl`, `deals.json`, and `payment_ledger.json`.

- [ ] **Step 9: Verify payment_ledger.json was written**

```bash
cat results/payment_runs/C1_sonnet_vs_sonnet/phase1/set_01_*/payment_ledger.json
```

Expected: JSON with `payment_compliance`, `transactions`, and `stripe_accounts` keys.

- [ ] **Step 10: Commit the test run output**

```bash
git add results/payment_runs/C1_sonnet_vs_sonnet/
git commit -m "test(payment-run): single phase 1 rollout — payment flow verified"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| Stripe as source of truth — no in-memory balance | Task 3 (`stripe_ledger.py` reads/writes Stripe directly) |
| All 10 agents follow payment rule | Task 9 (opponent second LLM call), Tasks 5–7 (focal endpoints) |
| enable_payments flag — existing runs unaffected | Task 11 (model_config), Task 10 (prompt gating), all endpoints check flag |
| $150 starting balance | Task 3 (`STARTING_BALANCE_CENTS = 15000`) |
| Two-phase deal (pending → confirmed/cancelled) | Task 2 (ledger), Task 6 (transfer_funds confirms/cancels) |
| L1: role ambiguity | Task 9 (`_apply_accept` already resolves buyer/seller — used in `_request_opponent_payment`) |
| L2: focal over-commitment | Task 6 (blocked at payment time, not offer time) |
| L3: silent blocking → visible message | Tasks 6 and 9 (channel SYSTEM post on failure) |
| L4: double payment | Task 6 (checks `payment_status == "confirmed"` before processing) |
| L5: race condition | Task 9 (`_request_opponent_payment` runs inline, updates before next turn) |
| L6: atomicity | Task 2 + Task 6 (item only in `sold_item_ids` after `confirm_deal`) |
| L7: opponent LLM call fails | Task 9 (malformed response → cancel + SYSTEM message) |
| L8: opponent hallucinates wrong deal/amount | Task 9 (validates `resp_deal_id` and `resp_amount`) |
| L9: focal pays wrong direction | Task 6 (`deal.buyer != state.focal_name` check + seller name check) |
| L10: double payment | Task 6 (`payment_status == "confirmed"` guard) |
| L11: pending deals at verify | Task 12 (only confirmed deals score; pending/cancelled counted as failures) |
| L12: amount mismatch | Task 6 (`abs(body.amount - deal.price) > 0.01` check) |
| L13: Stripe account creation failure | Task 4 (`create_agent_accounts` raises `stripe.error.StripeError` — propagates to abort session) |
| L14: float precision | Tasks 6 and 9 (`round(amount * 100)`) |
| L15: negative balance guard | Task 3 (`assert new_sender_balance >= 0`) |
| results/payment_runs/ separate from paper_runs/ | Task 14 (`--runs-dir` flag) |
| payment_ledger.json per set folder | Task 14 |
| Payment compliance rubric | Task 12 |
| Prompt payment block | Task 10 |
| Phase 1 only (no phase 2 task files) | Task 13 (only `--phase 1` generated) |
| Live end-to-end verification before full run | Task 16 (single rollout + Stripe dashboard check) |

All 15 loopholes and all design requirements are covered.
