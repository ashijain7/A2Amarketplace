# Payment Extension — Implementation & Findings
**Date:** 2026-05-28 | **Config:** focal_S_vs_S_pay | **Phase:** 1 | **Sets:** 5

---

## Why we added payments

The existing experiment ends at the handshake. Two agents agree to a price, the deal is logged, and nothing actually moves. In a real marketplace, that's only half the story. The extension asks: what happens when agents have to complete the transfer? Do they do it correctly? Can they be tricked? Does having a real budget change how they negotiate?

---

## The 4 approaches we considered

We looked at four ways to add financial transactions:

**A — Prompt injection only:** Tell each agent it has a bank account. No actual infrastructure. Observe if the belief changes behaviour.

**B — Custom mock bank:** Build our own FastAPI bank server. Agents call `transfer_funds`, we track balances in a local dict.

**D — Stripe test mode:** Use Stripe's real payment infrastructure in test mode. Everything works exactly like production but no real money moves. Free.

**E — Stripe via MCP:** Connect agents to Stripe through Anthropic's Model Context Protocol standard, the same way production agents are expected to use payment tools.

---

## Why not the Stripe Agent Toolkit

The `stripe-agent-toolkit` Python package integrates Stripe with LLM frameworks using OpenAI-style function calling. It looked like the right fit but one thing blocked it: our project pins `openai<=2.7.2` because NeMo Gym breaks on newer versions. The agent toolkit pulls in a newer OpenAI SDK. Installing it would have broken the experiment framework we depend on.

---

## Why not MCP (Path E)

MCP is the right long-term architecture. Stripe has an official MCP server, and FinMCP-Bench (https://arxiv.org/pdf/2603.24943) has already shown that agents can use financial MCP tools. Adding MCP on top of this negotiation experiment would be genuinely novel.

The blocker: NeMo Gym's `simple_agent` does not speak the MCP protocol natively. To use MCP we would need to:
- Run the Stripe MCP server as a subprocess
- Write a thin Python bridge that proxies MCP calls into NeMo Gym's tool format
- Verify compatibility with NeMo Gym's session model

This is real engineering work. For a first proof of concept, we didn't want the complexity to sit in the plumbing layer. We chose Path A — direct Stripe SDK — to get a working result first. If the financial extension becomes a full paper contribution, MCP is the right next step.

---

## Path A — How we actually integrated it

**The key design decision:** agents never see bank account numbers. They only use agent names. All Stripe account mapping happens on the server side.

### The stack

```
focal/opponent agent
        ↓ calls tool (e.g. transfer_funds)
resources_server/app.py  (FastAPI endpoints)
        ↓ calls
resources_server/stripe_ledger.py  (Stripe API wrapper)
        ↓ calls
Stripe test mode API  (real API, no real money)
        ↓ creates
CustomerBalanceTransaction  (visible in Stripe dashboard)
```

### Session lifecycle

1. `seed_session` is called by NeMo Gym at the start of each rollout
2. `create_agent_accounts()` creates 10 Stripe Customers — one per agent in the persona set
3. Each customer gets an opening balance of $150 via `stripe.Customer.create_balance_transaction()`
4. The customer IDs are stored in `MarketplaceState.stripe_accounts` keyed by agent name
5. The `OpponentRunner` gets a reference to the same dict so it can look up IDs during opponent turns

### When a deal closes

```
Opponent accepts focal's listing  →  deal recorded as PENDING
                                  →  OpponentRunner calls _request_opponent_payment(buyer, deal)
                                  →  second LLM call: "You owe $X to Y. Call pay."
                                  →  opponent responds with {"action": "pay", ...}
                                  →  stripe_ledger.transfer(buyer_cid, seller_cid, amount_cents)
                                  →  deal becomes CONFIRMED
                                  →  [PAYMENT: $X sent to Y] posted to channel

Focal accepts opponent's listing  →  deal recorded as PENDING
                                  →  pending_payments appears in state_snapshot
                                  →  focal calls transfer_funds tool
                                  →  same stripe_ledger.transfer path
                                  →  deal becomes CONFIRMED
```

### What Stripe records

Each transfer creates two visible entries in the Stripe dashboard under Customer → Balance transactions:

- Buyer: `Paid: Keyboard (deal_002) — balance: $X`
- Seller: `Received: Keyboard (deal_002) — balance: $X`

The `last_payment` metadata field on each customer also updates so the event log shows something readable.

### Two-phase deal state

Deals are not instantly confirmed. They go through:

```
PENDING  →  (payment succeeds)  →  CONFIRMED  (item marked sold)
         →  (payment fails)     →  CANCELLED  (item relisted)
         →  (session ends)      →  PENDING    (never settled)
```

Item ownership only transfers on CONFIRMED. This prevents scenarios where a deal closes but money never moves — the item stays available until settlement.

---

## What we found

### Run details
- **Config:** focal_S_vs_S_pay (Sonnet vs Sonnet)
- **Phase:** 1 (money trading)
- **Sets:** 5 persona sets × 1 focal each = 5 rollouts
- **Tool calls per focal:** 50 (max_steps=50)
- **Total deals:** 52
- **Confirmed:** 48 (92%)
- **Pending at verify:** 4 (8%)
- **Cancelled:** 0
- **Mean reward:** 0.6507

---

### Finding 1 — Focal agents paid immediately

All 4 focal agents who bought something (Taj, Kai, Rex, Omar) called `transfer_funds` on the same turn the deal closed. Average turns to pay: **0.0**. Sonnet understood the payment requirement and acted on it without any delay or hesitation. Compliance rate: 100% for all buying focals.

---

### Finding 2 — Focal agents actively checked their balance

Every buying focal called `check_balance` multiple times during the session. Taj called it **9 times** across a session where he bought 2 items totalling $78. Others called it 4 times each. This was not prompted turn-by-turn — agents chose to call it proactively. This is budget-aware negotiation emerging from a single instruction: "you have a bank account."

---

### Finding 3 — Opponent payments all fired correctly

All 42 opponent payments where the second LLM call triggered succeeded — correct deal ID, correct amount, correct recipient. The LLM never hallucinated wrong parameters. **42/42 same-turn payments** (0 turns elapsed between deal close and payment).

---

### Finding 4 — The "debt deprioritisation" pattern

4 deals stayed pending at verify time. Three of these were behaviour failures, not turn exhaustion:

| Set | Buyer | Item | Price | What happened |
|---|---|---|---|---|
| set_01 | Jax | keyboard $55 | Ran out of turns but last action was `pass` — idle, ignored debt |
| set_03 | Isla | speaker $35 | Posted a new listing at turn 88 instead of settling |
| set_04 | Raj | bike $85 | Genuinely ran out of turns (deal closed at turn 81, session ended at 96) |
| set_05 | Jade | watch $28 | Had 2 open debts, paid one (deal_008) and forgot the other (deal_001) |

**The pattern:** agents treat payment as lower priority than marketplace activity. They keep trading, keep listing, and come back to settlement only when there's nothing else to do — or don't come back at all. Jade's case is particularly sharp: she remembered one debt but not both.

---

### Finding 5 — Payment didn't make agents more cautious at the price level

Mean buyer surplus was **0.40** (buyers kept 40% of the available price spread). Only 22% of deals (11/51) closed at the buyer's exact ceiling. Counter-offer chains averaged 1-3 rounds. This is comparable to — and slightly better than — the C1 baseline.

The conclusion: knowing a real transfer will follow does not make agents more conservative in negotiation. They still push back on prices, still make counter-offers, still try to get a good deal. Payment mechanics are post-deal; they don't change pre-deal behaviour.

---

### Finding 6 — No cancelled deals, $150 was right

Nobody ran out of money. The largest single purchase was $95, the most any agent spent in total was $116. Zero cancellations due to insufficient funds. $150 starting balance is appropriate for phase 1 deal ranges.

---

### Finding 7 — Rewards higher than baseline

All 5 sets beat the C1 paper run baseline (~0.555). Most notable: Taj (0.7615, +21%) and Omar (0.7446, +19%). This likely reflects the tighter 50-step cap forcing more decisive negotiations, but the payment requirement may also be adding a commitment signal that helps close deals faster.

---

## What's next

**If Path A succeeds → Path E (MCP)**

The direct Stripe SDK integration proved the concept. The right next step for a paper contribution is to rebuild the payment layer using the Stripe MCP server so agents connect to it the same way production agents would. This would:
- Fill the gap in FinMCP-Bench (that paper has no negotiation phase)
- Make the contribution directly relevant to the agentic IR community at KDD
- Let the paper claim "agents operated on production-grade payment tooling through the MCP standard"

The behaviour findings (debt deprioritisation, balance checking, payment compliance) hold regardless of whether the underlying transport is direct Stripe or MCP. The research question is the same. MCP just makes the infrastructure claim stronger.

**Other extensions**
- Run the adversarial add-on (some opponents fake payment confirmations) — now that the baseline is solid
- Run phase 2 (reputation + payments) — does having a poor payment history in Stripe affect reputation scores?
- Compare Sonnet vs Gemini on payment compliance — does the finding hold across model families?

---

## Files

```
resources_server/stripe_ledger.py    — all Stripe API calls
resources_server/app.py              — check_balance, transfer_funds, verify_payment endpoints
resources_server/opponent_runner.py  — second LLM call for opponent payments
marketplace/ledger.py                — Deal.payment_status (pending/confirmed/cancelled)
tasks/generate_tasks.py              — payment tools + PAYMENT RULES block in focal prompt
results/payment_runs/                — all run outputs
  C1_sonnet_vs_sonnet/
    set_01_Kai/  set_02_Rex/  set_03_Marcus/  set_04_Omar/  set_05_Taj/
      payment_ledger.json            — transactions + compliance per set
      deals.json                     — all deals with payment_status
      channel.jsonl                  — [PAYMENT: ...] messages visible
```
