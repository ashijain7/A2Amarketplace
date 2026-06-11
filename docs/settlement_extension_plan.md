# Settlement Extension — Master Plan & Progress Log

> **Purpose of this file:** a single, self-contained handoff. Any new chat or person
> should be able to open this cold and know the full context, which documents to read,
> what is already done, what we found, and what is left. **Keep it updated after every
> work session** (see the Progress Log at the bottom).

---

## ▶ CURRENT STATUS — START HERE

- **Where we are:** Stripe payment draft has been **removed and pushed**. Phase 2 has
  been broken into a 5-day plan, and **Day 1 is fully designed** (below) and ready to build.
- **Next action:** **Implement Day 1** (the skeleton — 5 tools, 5 stages, a pretend
  no-op payment), then run a real mini-simulation and eyeball it together. *Then*
  brainstorm Day 2.
- **How we work (important — full rules in §0):** build **interleaved** — brainstorm one day → implement it →
  run it and look at the output → brainstorm the next day. The owner is **non-technical**;
  explain in plain language, define every term, small chunks. **No test files** in this
  project — verify by running the simulation and reading the output.

---

## 0. How we brainstorm & build (ground rules)

**These are strict. They apply to every day and every step.**

1. **Discuss before building.** Each piece is talked through and approved *before* any code is written.
2. **Always show alternatives.** For every real design choice, lay out **2–3 approaches** with
   trade-offs and a clear recommendation — never present a single path as if it were the only one.
3. **Every step is reviewed.** Implementation is broken into small steps; each step is shown and
   approved before the next. No big-bang changes.
4. **Surface additions — don't sneak them in.** If something *could* be added or improved, raise it
   and discuss it. Never expand scope silently.
5. **Edge cases up front.** Think through edge cases and failure modes **deeply during brainstorming**,
   not after they bite us in a run. List each one and decide how it's handled.
6. **Plain language.** The owner is non-technical: define every term, use everyday analogies, keep
   chunks small, never quiz.
7. **No tests.** Verify by running the real simulation and reading the output.
8. **Keep this file current.** Append decisions and findings to the Progress Log every session.

---

## 1. The goal (plain language)

The marketplace today: ten AI agents haggle, agree a price, and we write **"deal done."**
No money ever moves. **This extension adds the missing half — the actual *paying*** — but
in a world we fully control (a *simulated* payment layer, not a real bank).

**The headline experiment** (the heart of the paper): let the buyer's agent pay in two ways
and compare how much private information leaks.

- **Way 1 — "human-rail":** the agent holds the **real card / account details** and must use
  them to pay. We watch whether it blurts them out.
- **Way 2 — "agent-native":** the agent holds only a **mandate** (a capped spending
  permission — "spend up to ₹15,000/month"), never the raw details. Almost nothing can leak.

The **gap between the two leak rates** is the result.

Two more switches we flip on/off: a **cheater** in the room, and a **smart vs simpler model**.

---

## 2. Source documents (read these for full detail)

| Document | What it is |
|---|---|
| `docs/transaction_rubric_detailed.md` | **The scoring design.** 5 areas (Privacy, Security, Transactional Integrity, Smart Method Choice, Integrity & Accountability), ~20 sub-measures, the cheater's 7-trick playbook, and how it all maps to prior research. This is Phase 3's spec. |
| `razorpay_mcp/payment_findings_detailed.md` | **Why we simulate.** Records that no free sandbox (Razorpay, Cashfree, NPCI) lets agents pay each other autonomously over Indian rails today — and that simulating is the field-standard method (FinVault, AgentDojo, τ-bench, etc.). |
| `razorpay_mcp/settlement_phased_plan.md` | **The manager's roadmap.** 5 phases; Phase 2 has the day-wise build plan we are following. |
| `docs/transaction_rubric.md` | Shorter version of the rubric. |
| `docs/financial-extension-detailed.md`, `docs/magentic-marketplace-explained.md` | Supporting background. |

---

## 3. Decisions already locked

1. **Simulate the payment layer** (a "truth-holding ledger" we control). Real rails
   (Razorpay S2S, x402) are an *optional* later phase (manager's Phase 5), not now.
2. **Stripe integration removed** — it "wasn't real" for this purpose (global cards,
   customer-pays-business, no Indian UPI, no agent-to-agent). Done & pushed (see §6).
3. **Kept the deal "notebook"** in `marketplace/ledger.py` — it is backend-neutral and the
   new payment stages grow directly out of its `payment_status` field.
4. **No test files** in this project. Verify by real runs + reading output. (This overrides
   default TDD behaviour — owner's instruction.)
5. **Build interleaved**, headline-first: smallest complete payment loop first, then layer on.
6. **The payment layer lives *inside* the existing resources server**, behind a clean,
   swappable interface — so a real Razorpay backend could drop in later without touching
   the agents.

---

## 4. The codebase a new chat needs to know

The simulation is one "referee computer" (a FastAPI server) the agents talk to.

| File | Role |
|---|---|
| `resources_server/app.py` | The **referee server**. Endpoints for every agent action (post_listing, make_offer, accept_offer, …); orchestrates the opponent agents; invokes the verifiers. The new payment tools/endpoints go here. |
| `resources_server/opponent_runner.py` | The **scheduler + opponents**: round-robin loop, one opponent turn per focal action. Records closed deals via `Ledger.record_deal`. |
| `marketplace/ledger.py` | **The deal notebook (KEPT).** `Deal` dataclass with `payment_status` (`n/a/pending/confirmed/cancelled`); `record_deal(pending=…)`, `confirm_deal`, `cancel_deal`, `pending_deals_for_buyer`. Saves to `data/deals.json`. |
| `marketplace/build_agents.py` | Renders each persona → its prompt. (The old Stripe `PAYMENT_BLOCK` was removed from here.) |
| `marketplace/channel.py` | Append-only event log of everything said (`data/channel.jsonl`). |
| `resources_server/verifiers.py` | **Scoring.** deal_outcomes, capability_asymmetry, negotiation_quality, privacy (exact-match + LLM-judge), review_utilization (P2), swap_quality (P3). (The thin `payment_compliance` scorer was removed; Phase 3's rubric replaces it.) |
| `tasks/generate_tasks.py` | Builds the NeMo Gym task file and the **agent tool catalog**. New tools are declared here. |
| `resources_server/model_config.py` | Config name → model pairing (e.g. `focal_S_vs_S`). The old `_pay` variants were removed. |
| `personas_phase{1,2,3}/*.json` | Personas. Each has a `private` block (real_address, age, occupation, financial_situation, debt_context) — the leak targets. Payment "wallet" fields get added here in Day 3. |
| `marketplace/config.py` | Phase select (`MARKETPLACE_PHASE`=1/2/3), `MAX_TURNS=120`, models, `JUDGE_MODEL=gpt-4o`, paths. |

**Scenarios:** Phase 1 = MarketDeal (money); Phase 2 = + reviews/reputation; Phase 3 =
SwapShop (barter, no money). **The payment step applies to MarketDeal (Phases 1–2) only.**

---

## 5. Phase 2 — the 5-day build plan

| Day | Plain words | Technical |
|---|---|---|
| **Day 1 — Skeleton** | Build the "payments desk", the 5 buttons, the 5 stages; one full pretend walk-through. | Settlement module + the 5 tools + per-deal state machine (AGREED → METHOD_CHOSEN → PAID → CONFIRMED/FAILED); no-op backend; behind an off-by-default switch. |
| **Day 2 — Pretend bank** | The 5 ways to pay behave realistically. | 5 methods (UPI/card/bank/wallet/mandate) with exposure + reversibility profiles; deterministic success/failure; double-pay block; spending-limit; capped mandate. Seed-controlled. |
| **Day 3 — Conditions + recording + cheater** | The real-details vs mandate switch; record everything; add the cheater. | `pay_mode` (human-way raw creds vs agent-way mandate token); capture tool-call inputs + logs (leak observability across channels); cheater trick library (fake receipt, OTP-phish, payee redirect) with on/off toggle. Persona payment "wallet" added. |
| **Day 4 — Run & check repeat** | Drive an agent through every combination; confirm runs repeat. | Walk choose→pay→confirm for {human,agent} × {cheater off,on}; confirm same seed → identical run. |
| **Day 5 — Example runs + tidy** | A few known-answer example runs; clean up. | Example rollouts: clean pay, double-pay, leak, redirect, decline+recover. |

**Note on Days 4–5:** the manager calls these "tests/fixtures." Because this project uses
**no test suite**, we do them as **real example runs we inspect by eye**, not unit tests.

---

## 6. What's done

- **Stripe / payment-draft removed and pushed** (branch `project_deal`):
  - `61022ea` — Remove Stripe payment draft and test files
  - `a9504a0` — Add payment-extension research docs and tooling
  - Deleted: `stripe_ledger.py`, `setup_stripe_agents.py`, `smoke_test_payment.py`, and the
    `tests/` folder. Surgically removed the payment endpoints, `stripe_accounts`, the
    `enable_payments` flag, the `PAYMENT_BLOCK` prompt, the `payment_compliance` scorer, the
    `_pay` config variants, and the payment tools — all behind the old off-by-default flag.
  - **Verified:** no `stripe`/`enable_payments` left in code; the deal notebook intact; the
    test suite passed (24) *before* the tests were deleted per the no-tests preference.
  - **To see the old payment wiring** (useful when rebuilding it cleanly), a future chat can
    run `git show 61022ea` — the removal diff shows exactly how the tools/flags threaded
    through `app.py`, `opponent_runner.py`, `build_agents.py`, `generate_tasks.py`.
- **Phase 2 structure agreed** and **Day 1 designed** (next section).

---

## 7. Day 1 — DESIGNED, ready to build

### The 5 buttons (agent tools)
Plain → manager's tool name:
1. *"What can I pay with?"* → `list_payment_methods`
2. *"I'll use UPI."* → `choose_payment_method(deal_id, method)`
3. *"Send the money."* → `pay(deal_id, …)`
4. *"Did it arrive?"* → `confirm_receipt(deal_id)`
5. *"Where's this deal at?"* → `get_payment_status(deal_id)`

*(A 6th, `request_human` / "ask a human" for over-limit purchases, comes with Day 2's
spending limits — not Day 1.)*

### The 5 stages (per-deal state machine)
`AGREED → METHOD_CHOSEN → PAID → CONFIRMED` (happy path), with `FAILED → retry` as the
off-ramp. **Forward-only:** reject `pay` before a method is chosen, reject double `pay`, etc.

| Stage | Set by | Notebook today |
|---|---|---|
| AGREED | deal closes (offer accepted) | `payment_status="pending"` |
| METHOD_CHOSEN | `choose_payment_method` | — |
| PAID | `pay` | — |
| CONFIRMED | `confirm_receipt` | `payment_status="confirmed"` |
| FAILED | `pay` declined | `payment_status="cancelled"` (then retry) |

### The pretend (no-op) run
Day 1 builds the **buttons and stamps only** — *not* the clever bank (that's Day 2). So
`pay` simply succeeds and stamps the deal PAID; `confirm_receipt` always confirms. No method
realism, no success/failure, no leak-catching yet. It's the **frame of the house before the
plumbing.**

### Definition of done (Day 1)
With the settlement switch ON, a **real mini-simulation** (one buyer, one seller) closes a
deal and the buyer's agent calls choose → pay → confirm, ending **CONFIRMED**, visible in
`data/deals.json` and the run output. We confirm by eye. Normal (switch-off) runs behave
exactly as before.

### Implementation notes (for the engineer/AI)
- Add a new module, e.g. `resources_server/settlement.py`, holding **(a)** the simulated
  backend behind a tiny interface (Day 1 = stub that always succeeds) and **(b)** the
  per-deal payment-state store + forward-only transitions. Keep `ledger.py` as-is for Day 1;
  reconcile the richer state set with `Deal.payment_status` later if useful.
- Add a **fresh on/off switch** — suggest `enable_settlement` (new name, to avoid confusion
  with the removed `enable_payments`) — **defaulting OFF**. Thread it like the old flag did
  (see `git show 61022ea` for the pattern) through `app.py` / `opponent_runner.py` /
  `build_agents.py` / `tasks/generate_tasks.py`, and add a config variant in `model_config.py`.
- Declare the 5 tools in `tasks/generate_tasks.py` and implement them as endpoints in
  `resources_server/app.py`.
- On deal close in `opponent_runner.py`, when settlement is on: `record_deal(pending=True)`
  and initialise settlement state = AGREED. (Mirror of the old payment flow.)
- A short prompt block telling the buyer's agent to settle pending deals (the clean
  replacement for the removed `PAYMENT_BLOCK`).

### Day 1 deep-dive — decisions to settle (thorough brainstorm)

Each is worked through with alternatives + edge cases before any Day 1 code. Tick as settled:

- [x] **D1. Who actually pays?** → **Option B**: role-symmetric, every agent participates, no auto-settle.
- [x] **D2. How does the agent know to pay — and what if it forgets?** → pending jumps the queue (one-shot) + a reminder of its jobs in its view + counterparty reminder + unpaid-at-120 = not done.
- [x] **D3. Buttons + rules + channels** → re-choose until paid; agent-typed amount/recipient (logged); three-place model with the private room built in Day 1.
- [x] **D4. Where the payment stage is stored** → **C (split)**: ledger keeps coarse done/not-done; a separate payment-tracker holds the play-by-play.
- [x] **D5. The pretend backend behind a swappable window** → **A**: define the thin interface now (execute / is-settled / list-methods); Day-1 dummy behind it.
- [x] **D6. The on/off switch + phase guard** → **named config**, OFF by default, MarketDeal-only (Phase 3 guarded off).

**Edge-case bank (Day 1):** pay before choosing → reject; choose method twice → allowed until paid;
pay twice → blocked (idempotent); confirm before pay → reject; confirm twice → idempotent; act on a
deal that isn't yours / doesn't exist → reject; focal is the seller → nothing to pay (confirm only,
deferred to Day 3); Phase 3 swap → settlement off; agent never pays → `MAX_TURNS` cap ends the run.

### Day 1 — settled decisions (D1 ✓, D2 mostly ✓)

- **D1 = Option B (role-symmetric, no shortcuts).** Every agent (focal + all 9 opponents) fully
  participates. **Buyer:** `list_payment_methods → choose_payment_method → pay` (AGREED →
  METHOD_CHOSEN → PAID). **Seller:** `confirm_receipt` (PAID → CONFIRMED, via `ledger.confirm_deal`).
  Focal uses tool-calls, opponents use JSON actions, but **both route into one settlement module**
  (single source of truth). On deal close, record `pending=True` (= AGREED).
- **D2 (mostly): scheduling + reminders + termination.**
  - *Pending payment jumps the queue:* the next turn goes to the agent who must act (buyer pays /
    seller confirms), overriding round-robin — **once per attempt**; if ignored, normal rotation
    resumes (anti-deadlock guard).
  - *Counterparty chases:* the waiting agent may remind the other on its own turn.
  - *Termination:* a deal still pending at `MAX_TURNS` (**120, unchanged**) = **not done** (stays
    pending, item not marked sold). The extra cost of B is accepted.
- **D3 = button rules + agent-typed details.** Re-choosing the method is allowed **until paid**;
  forward-only + ownership rules apply (pay only your own buyer-deals, in order, once; confirm only
  your own seller-deals, after the buyer paid). The **agent supplies amount + recipient** itself
  (Option 2); Day 1 **logs** what it typed — no correctness check yet (Day 2), no card details yet
  (wallet = Day 3).
- **Channels = three-place model (Approach 3), private room built in Day 1.** On deal close a
  **private buyer↔seller room** opens (two-party). The mechanical pay goes through the **pay tool**
  (Pipe 1); the room (Pipe 2) and public square (Pipe 3) are for talk. **Day 1 pay = no-op**
  (click → log → stamp PAID; real method logic = Day 2). **Record all three places** (tool inputs,
  private room, public square) — the foundation for Day 3 leak-scanning. **Build approach:** one
  underlying log + per-message visibility tags + a filtered per-agent view (extends the existing
  channel-view rendering); keep the room flexible enough for a third party (cheater) to enter on
  Day 3. Wallet/secrets, leak-scan, and cheater all come on **Day 3**.
- **D4 = split storage (Option C).** The kept `ledger` notebook keeps the **coarse** status
  (`pending`/`confirmed`/`cancelled`) and stays the source of truth for sold items. A separate
  **settlement-tracker** (in the new module, keyed by `deal_id`) holds the **play-by-play**: the
  detailed stage (AGREED→…→CONFIRMED/FAILED), chosen method, typed amount + recipient, attempt
  count. They sync at two points only: CONFIRMED → `ledger.confirm_deal`; FAILED → `ledger.cancel_deal`.
- **D5 = define the swappable backend interface now (Option A).** A thin "window" the settlement
  module calls: `execute_payment(...) -> {success, reference, failure_reason}`,
  `check_settled(...) -> bool`, `available_methods() -> list`. Day 1 = a **no-op backend** (always
  success/settled; the 5 method names). Day 2's realistic backend — and any later real-Razorpay
  backend — slot in **behind the same interface** (manager's Phase 5).
- **D6 = on/off switch (named config), default OFF, phase-guarded.** A fresh switch
  `enable_settlement`, exposed as a **named config variant** (like the existing model configs),
  **OFF by default** so the 75-run baseline is untouched. Valid only in **Phases 1–2** (money);
  **forced off in Phase 3** (swap). Threaded through `app.py` / `opponent_runner.py` /
  `build_agents.py` / `tasks/generate_tasks.py` / `model_config.py` (see `git show 61022ea` for the
  old wiring pattern). A quick env override may be added for ad-hoc tests.

---

## 8. Days 2–5 — outline (brainstorm when we reach them)

- **Day 2 — Pretend bank:** the 5 methods with exposure (what each reveals) and
  reversibility (card = chargeback-able; UPI/bank = final) profiles; deterministic
  success/failure (model Razorpay's `success@razorpay` / `failure@razorpay`); double-pay
  block; spending-limit + the `request_human` escalation; capped mandate.
- **Day 3 — Conditions + recording + cheater:** the `pay_mode` switch (raw creds vs mandate
  token); the persona payment **wallet** (card+CVV, UPI id, bank acct+IFSC, mandate cap, plus
  a public handle) added to persona `private` blocks; record tool-call **inputs + logs** so a
  leak is observable in every channel (not just the chat); the cheater playbook + toggle.
- **Day 4 — Run & repeat:** all four combinations; seed reproducibility.
- **Day 5 — Example runs + tidy:** the known-answer rollouts, inspected by eye.

Then **Phase 3** (lock the rubric + write the LLM-judge prompt), **Phase 4** (run the eval
matrix, score, validate the judge), **Phase 5** (optional real Razorpay rails).

---

## 9. Open questions (decide later)

- Scoring **weights** per measure/area, and **severity weights** (a leaked CVV ≫ a ₹5 overpay).
- Exactly **how the agent holds raw details** in human-way mode (Day 3 detail).
- The cheater: **how many** cheater agents, and **which tricks** to switch on first.
- **Escrow** — add a "trusted middle-man holds the money until goods arrive" option?
- Tool-name reconciliation: manager's names vs the rubric's (`check_settlement`,
  `request_human`). Currently following the manager's 5 + `request_human` later.

---

## 10. Progress Log (append every session — newest first)

- **2026-06-11**
  - Read the 3 source docs + mapped the codebase.
  - Removed the Stripe payment draft (commits `61022ea`, `a9504a0`), kept the ledger
    notebook, verified clean, pushed to `origin/project_deal`.
  - Recorded the **no-tests** preference; deleted the `tests/` folder.
  - Agreed the **interleaved, headline-first** build approach.
  - Broke Phase 2 into the manager's 5 days; brainstormed the Day 1 design (5 tools, 5 stages, no-op run).
  - Added strict §0 ground rules. Day 1 deep-dive: **D1 settled = Option B** (role-symmetric, no
    auto-settle); **D2 mostly settled** (pending payment jumps the queue once + counterparty reminder
    + unpaid-at-120-turns = not done; turn cap unchanged).
  - **D3 settled:** button rules (re-choose until paid; ownership/forward-only); agent-typed
    amount/recipient (logged). **Channels:** three-place model — public square + a private
    buyer↔seller room (built in Day 1, two-party) + the pay tool; record all three; Day 1 pay = no-op.
    Wallet/leak-scan/cheater deferred to Day 3.
  - **D4 settled:** split storage (C) — ledger keeps coarse status; a separate settlement-tracker
    holds stage/method/typed-amount/attempts; sync at confirm/cancel only.
  - **D5 settled (A):** thin backend interface defined now (execute / check-settled / list-methods); Day-1 no-op behind it.
  - **D6 settled:** on/off switch = named config, OFF by default, money-phases-only (Phase 3 guarded).
  - **All D1–D6 settled → Day 1 is fully designed.** **Next:** build Day 1 in small reviewed steps
    (no big-bang), then run a mini-simulation and eyeball it; then brainstorm Day 2.
