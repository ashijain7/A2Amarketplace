# Payment Backend Feasibility — Detailed Findings

## 1. Objective

Our marketplace runs **10 agents** — 1 focal agent and 9 others. They talk to each other, haggle, and agree on prices. But the story stops at the handshake: once a deal closes, the ledger records it and nothing else happens. **No money actually moves.**

The work here was to add the missing half — a real **payment step**. After a deal closes (say Maya's agent buys Raj's keyboard for ₹500), the buyer's agent should choose a method, pay the seller's agent, and confirm the money arrived.

There is one hard requirement that shapes everything: it must happen with **no human in the loop**. No person taps a phone, enters a PIN, or types a one-time code. The whole point of the experiment is to watch agents handle money *by themselves*, across many deals, unattended.

This is not a toy concern. In the last year Google, Stripe, Visa, Mastercard, and India's own NPCI have all launched ways for AI agents to make real payments — including closed pilots where ChatGPT and Claude pay over UPI. So "can an agent pay safely and correctly, on its own?" is becoming a real question. To study it, we first need a payment step our agents can actually use.

The question this document answers:

> Can free **Razorpay test mode** — a fake-money practice version of the Indian payments company Razorpay — let one agent pay another, automatically, with no human?

The short answer is **no**, and the rest of this document explains exactly why, what else we checked, how the research field handles the same problem, and what we will build instead.

---

## 2. How the payment step should work

A real payment is not one action. It runs through four steps, and our agents would need to do all four on their own:

1. **Choose a method** — how to pay. The realistic options are UPI (India's instant phone-to-phone payment, where you send to a handle like `name@bank`), a card, a bank transfer, a wallet, or a mandate (a capped spending permission).
2. **Hand over what that method requires** — each method demands different details (a card needs its number and code; UPI needs a handle and a PIN).
3. **Pay** — send the money, often within a spending limit.
4. **Confirm** — check the money actually arrived, rather than assuming it did.

So the intended flow, end to end, looks like this:

> Maya's agent and Raj's agent close a deal at ₹500. Maya's agent picks a method, sends ₹500 to Raj, and then checks that it landed. Raj's agent, before "shipping," also checks the money truly arrived. All of it happens with no human watching.

That "no human" requirement is the entire test. Plenty of payment systems can do steps 1–4 *with* a human tapping a screen; very few can do them with a program alone.

---

## 3. What we built to test it

Everything lives in one self-contained folder, `razorpay_mcp/`, so nothing leaked into the rest of the project.

**The account and keys.** We created a free Razorpay account and generated **test keys**. A test key is a secret password that lets a program use the account — a Key ID (which looks like `rzp_test_…`) and a Key Secret. They are stored in `razorpay_mcp/.env`, which is **gitignored**, so the keys are never committed to the repository.

**The MCP server.** Razorpay ships an official **MCP server**. "MCP" is a standard adapter that turns a service's actions into **"tools" an AI agent can call directly** — instead of a developer hand-writing code for each Razorpay action, the agent simply calls `create_order`, `initiate_payment`, and so on. We run that server locally through Docker; it needs only the two keys.

**The probe scripts.** Three small scripts drive the testing:

- `test_razorpay_mcp.py` — connects to the MCP server and prints a PASS/FAIL report of what the account can do.
- `inspect_tools.py` — asks the MCP server exactly what fields each payment tool needs, so we don't have to guess.
- `test_pay_upi.py` — attempts one full autonomous UPI payment (this is where we hit the wall, §9).

**The Claude Code wiring.** We also connected the same MCP server into Claude Code, so the assistant can call Razorpay's tools directly too. Both the scripts and Claude Code read the *same* keys from the *same* `.env` — one source of truth. (Wiring it into Claude Code is convenience for testing; in the real experiment, the marketplace's own agents would be the ones calling the payment layer, not Claude Code.)

The Mac already had Docker, Node, Python, and `uv`, so setup was just the account and the keys. The scripts are described in the folder's `README.md`.

---

## 4. How an agent talks to Razorpay (the MCP tools)

When the probe connected, the Razorpay MCP server offered **41 tools**. They fall into a few groups, and the grouping itself tells the story of what's possible:

- **Make a bill / request money** — `create_order`, `create_payment_link`, `payment_link_upi_create`, `create_qr_code`. (These all worked.)
- **Complete a payment** — `initiate_payment`, `submit_otp`, `resend_otp`, `capture_payment`. (This is the autonomous-pay path — the one that turned out to be blocked.)
- **Look things up** — many `fetch_*` tools (payments, orders, refunds, settlements, payouts).
- **Other** — refunds, settlements, QR management, saved-card tokens.

The key split: the server is rich on the "**ask for money**" side and the "**look things up**" side, but the "**actually complete a payment**" side depends on a power your account does not have by default (§9–10).

---

## 5. Two ways money moves: push vs collect

This distinction turned out to drive the findings, so here it is in everyday terms — using GPay / PhonePe.

**Push — you SEND.**
You open GPay, type Raj's number, type ₹500, and hit send. Money leaves your account and lands on Raj. *You* made the first move.

**Collect — they ASK, you APPROVE.**
Raj's shop shows a QR code, or a "please pay ₹500" request pops up on your phone. You tap *Pay*. The same ₹500 reaches Raj — but this time *he* asked first, and you only approved.

Both end with ₹500 in Raj's pocket. The **only** difference is **who starts it.** For our marketplace:

- The **push** model would be: the buyer's agent sends money straight to the seller's account or UPI handle.
- The **collect** model would be: the seller's agent puts up a bill, and the buyer's agent pays it.

As we'll see, Razorpay's free account blocks the push model (§8) and limits the collect model (§9), which is why neither worked autonomously.

---

## 6. One account, ten agents: the cash box and the notebook

A natural assumption is that each of the 10 agents needs its own Razorpay account. **It does not**, and understanding why matters for the design.

Picture the 10 agents in one room with just two things:

- **One cash box** — that's Razorpay (your single account). There is only one. The agents do not each get their own.
- **One notebook** — that's our **own ledger**: a private record with 10 pages, one per agent, showing how much money each one has.

Nobody owns a box; they all share the single one. The **notebook** is what keeps each agent's money separate *on paper*. When Maya pays Raj ₹500:

1. The **cash box (Razorpay)** makes the payment *really happen* — a genuine (test) payment.
2. The **notebook (our ledger)** records it: Maya −₹500, Raj +₹500.

> **Razorpay** makes a payment *real*. **Our ledger** keeps *score*. We need both — one to *act*, one to *remember*.

So "creating an agent's payment identity" is not opening a new bank account; it's **adding a page to the notebook** with a name and a starting balance. This is exactly the pattern the project's existing Stripe setup already uses: it creates 10 Stripe "customers" under one Stripe account, not 10 separate accounts.

---

## 7. What the probe found

Running `test_razorpay_mcp.py` produced this:

| Check | Result | What it means |
|---|---|---|
| MCP server reachable | ✅ PASS | The server runs and answers — 41 tools available. The "agent calls Razorpay as tools" idea works. |
| Keys authenticate | ✅ PASS | The test keys are valid: the agent read the (empty) payments list. |
| Create a bill (order) | ✅ PASS | A real ₹500 test order was created — `order_SzsmuoUdpZwfrT`. The agent *can* start a payment. |
| Autonomous-pay tool present | ✅ PASS | The tool `initiate_payment` exists in the toolbox. |
| Push money (payouts) | ❌ FAIL | The tool returned `missing required parameter: account_number`. |

So the "**ask for money**" side worked completely — the agent could make orders, links, and QR codes. The first thing that failed was **payouts** — the "push" side from §5 — and the reason has a name: RazorpayX.

---

## 8. RazorpayX, and why payouts failed

**What is RazorpayX?** Regular Razorpay — the thing your test keys unlock — is built for a business to **receive** money from customers. Think of it as a shop's **card machine**: great at taking money *in*. **RazorpayX** is a *separate* product: the business's own **current account with a chequebook** — money goes *out*. It is business banking. It lets a company send money out by program: payouts to any bank account or UPI ID, vendor payments, salaries, and so on.

> Regular Razorpay (you have it) = a card machine, money **in**.
> RazorpayX (you don't) = a business account + chequebook, money **out**.

**Why we'd want it.** The "push" style of payment — the buyer's agent *sending* money straight to the seller — needs an account for the money to leave *from*. That source account is exactly what RazorpayX provides. So RazorpayX is the natural technical fit for "one agent pushes money to another."

**What the error actually meant.** `missing required parameter: account_number` was literally Razorpay asking *"which RazorpayX account should this money leave from?"* — and we have none. It is not that payouts are forbidden; it is that there is no source account to push from.

**Why we didn't go there.** Getting a RazorpayX account is not a toggle. It needs its **own business onboarding**: a registered business, KYC documents, and an approved current account. That is heavy, slow, real-world setup — far more than a research sandbox needs. So we set the push model aside, and the **collect** model became the path to test next.

---

## 9. The wall: the agent can't complete a payment

The decisive test was `test_pay_upi.py`, which tries the collect model end to end: create an order, then pay it over UPI, then confirm.

- **Making the bill worked** — order `order_SztHtUJ3krTRJ3` was created.
- **Paying it failed**, with this reply from Razorpay:

> `initiating payment failed: The requested URL was not found on the server.`

In plain words:

> The agent can **ask** for money automatically. It **cannot complete** the payment automatically.

There was a second limit, found by `inspect_tools.py` (which prints exactly what each tool accepts). The autonomous-pay tool, `initiate_payment`, takes only **UPI** details — its fields are `vpa` (a UPI handle), `upi_intent`, and `token` (a saved method). There is **no field for a fresh card, netbanking, or wallet.** So even if the tool had worked, the autonomous path would be **UPI-only** — card, wallet, and netbanking can only be completed on the human checkout page.

---

## 10. S2S, and why it's blocked

The power the failed step needs has a name: **S2S — server-to-server.**

Normally a Razorpay payment runs through a **checkout page**: a human sees the page, picks a method, and taps "pay" (entering a one-time code or UPI PIN). **S2S removes that page.** It lets *your program* talk straight to Razorpay's servers and both *create* and *complete* a payment — supplying the details, and even the test OTP, through code. No page, no human.

That is **exactly** the power we need, because it's the only way an agent can finish a payment with nobody clicking. So we checked whether it can be switched on. Two findings, both pointing the same way:

**S2S cannot be self-enabled.** Razorpay states it is "an on-demand feature" and you must "**raise a request with our Support team to get this feature activated**" on your account. There is no dashboard toggle. ([S2S JSON v2 docs](https://razorpay.com/docs/payments/payment-gateway/s2s-integration/json/v2/))

**UPI is restricted in test mode anyway.** Razorpay says "**UPI payments should be tested in Live Mode**," and "**UPI Payment Links is not supported in Test Mode.**" ([Web integration FAQ](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/troubleshooting-faqs/)) The `success@razorpay` test handle only works on the checkout *page*, not for a headless program. This is the likely reason the address itself came back "not found."

Putting it together: a *real* autonomous UPI payment would require **both** an S2S support request **and** a switch to **Live Mode** — real KYC, a real registered business, and **real money moving**. That is far too heavy for what is meant to be a research sandbox, and getting there isn't even guaranteed.

---

## 11. Why test mode exists at all

It's a fair question, since Razorpay test mode couldn't do the one thing we wanted. The answer: **test mode is built for a different person than us.**

It is for a **shop or app developer** whose customers will pay them through a **checkout page**. Test mode lets that developer rehearse the entire checkout — test cards, netbanking, refunds, receipts, the webhooks that confirm a payment — with **fake money**, before flipping to live. It is genuinely excellent at that.

But it assumes **a human is sitting at a checkout page tapping "pay."** It fakes that human's tap *inside the checkout screen only* — never for a headless program with no screen.

> Test mode = "rehearse your checkout page safely." It was never "let a robot pay by itself."

The honest landscape:

| Sandbox | Headless (no human)? | Indian rails / UPI? |
|---|---|---|
| **Stripe test** (the project already has this) | ✅ yes — fires by itself | ❌ no UPI |
| **Razorpay test** | ❌ no — needs a human / checkout page | ✅ real UPI, cards, etc. |

**No free sandbox gives both at once.** The only systems with "Indian rails *and* autonomous agent pay" are the **closed NPCI–OpenAI/Anthropic pilots** — not open to the public. That gap is not our mistake; it is the actual state of the world, and it is itself worth reporting.

---

## 12. Other payment rails we could test with

Razorpay isn't the only option. We checked the main alternatives, asking each the same question: **can an agent pay another agent with no human, for free, today?** Each is written up in full below, then summarised in a table.

### x402 (Coinbase)
- **How it works:** built on the web's `HTTP 402 "Payment Required"` signal. A server replies "402, pay first," the agent **signs** a small stablecoin (USDC) payment and retries the request with the signed payment attached. No card details handed over, no human.
- **Autonomous?** ✅ Fully — agents pay each other with no keys shared and no human input.
- **Free to test?** ✅ Runs on the **Base Sepolia test network**; agents top up play-money USDC from a free faucet.
- **Method:** crypto (USDC) — not UPI or cards.
- **The catch:** it's crypto, so it's a different rail from Indian payments. But it genuinely works end to end. It's real at scale, too: 150M+ payments / ~$50M in nine months.
- **For us:** the rubric doc already calls x402 "the agent-native contrast." It turns out to be the *one* rail you can actually run autonomously and free. ([Coinbase x402](https://www.coinbase.com/developer-platform/discover/launches/x402), [Cloudflare](https://blog.cloudflare.com/x402/))

### Stripe
- **How it works:** Stripe's test mode completes payments server-side, with no checkout page. Its Agent Toolkit exposes Stripe actions as agent tools, and it recently launched a **Machine Payments Protocol** specifically for agents paying agents (cards + stablecoins + credential-less "shared payment tokens").
- **Autonomous?** ✅ Yes — headless test payments work.
- **Free to test?** ✅ Test mode is free.
- **Method:** cards (global), and stablecoin via the new protocol. **No Indian UPI.**
- **The catch:** not Indian rails. But the project **already has a Stripe layer built**, so it's the lowest-effort real rail.
- **For us:** the easiest "real payment that fires headlessly" option we have today. ([Stripe agents](https://docs.stripe.com/agents), [Machine Payments Protocol](https://stripe.com/blog/machine-payments-protocol))

### Nevermined / Skyfire / Payman
- **How they work:** startups building payment infrastructure *for* AI agents. Nevermined adds a settlement and identity layer (agent wallets, DIDs, prepaid "credits") on top of x402, supporting both fiat and crypto. Skyfire (raised $8.5M) gives agents wallets you fund and control in real time. Payman is in the same space.
- **Autonomous?** ✅ Built exactly for it.
- **Free to test?** Partly — developer tiers exist.
- **Method:** fiat *and* crypto.
- **The catch:** third-party startups; more to learn and some sign-up; you depend on their platform.
- **For us:** higher-level toolkits worth a look if we want a turnkey agent-payment layer. ([Nevermined](https://nevermined.ai/blog/best-platforms-agent-payments))

### Cashfree (Indian)
- **How it works:** an Indian aggregator with a payouts sandbox; you add a beneficiary (with a test UPI handle) and send a test payout.
- **Autonomous?** ◑ Simulated payouts in test mode.
- **Free to test?** ✅ Test mode.
- **Method:** UPI / bank.
- **The catch:** "all modes must be enabled by Cashfree before the attempt" — the **same gating wall** as Razorpay.
- **For us:** the closest Indian-UPI alternative, but gated the same way, so no better for autonomous testing. ([Cashfree test data](https://www.cashfree.com/docs/payouts/payouts/integrations/data-to-test))

### Also looked at, and set aside
- **NPCI official UPI sandbox** — the real government UPI test system, but locked to licensed banks; we can't get in.
- **Google AP2 sample** — reference code for the agent-payment standard, but mock only (no real UPI).

### Summary

| Option | No human? | Free? | Method | The catch |
|---|---|---|---|---|
| **x402** (Coinbase) | ✅ | ✅ testnet + faucet | Crypto (USDC) | Crypto, not UPI/cards — but truly headless. |
| **Stripe** (already set up) | ✅ | ✅ test mode | Cards; stablecoin | No Indian UPI. |
| Nevermined / Skyfire / Payman | ✅ | partly | Fiat + crypto | Startups; more setup. |
| Cashfree (India) | ◑ simulated | ✅ | UPI / bank | Modes gated by Cashfree. |
| Razorpay (tested) | ❌ | ✅ | UPI / cards | Autonomous pay blocked. |

**The takeaway:** for autonomous, free, real payment today, **x402** (crypto) and **Stripe** (cards, already wired) are the two that work. For **Indian UPI specifically, there is no free, no-human option** — Razorpay and Cashfree both gate it. That confirms, from a second angle, that the India-flavoured payment must be simulated.

---

## 13. How the research papers handle the payment step

The most useful question to ask the field is: **when a paper has agents "pay," what actually happens?** We read how each one does it. The answer is consistent — and it settles whether simulating payment is acceptable.

### AgenticPay — the closest paper, and it has no payment at all
A multi-agent **negotiation** benchmark: 110+ tasks across e-commerce, food delivery, ride-hailing, and apartment rental, in markets from 1-to-1 to many-to-many. Agents offer, counter-offer, and accept in plain language. But a "transaction" is just a **recorded agreement** on terms (price, delivery, return policy). In its own words: *"transactions are complete when agents agree on terms; the environment doesn't simulate payment infrastructure, wallets, or ledgers."* So it stops exactly where our project begins — the payment step is the gap. ([arXiv:2602.06008](https://arxiv.org/abs/2602.06008), [code](https://github.com/SafeRL-Lab/AgenticPay))

### The payment-involving benchmarks all simulate
None use real money on a real rail. The agent's actions change a **sandbox database / ledger the experiment controls**, and that record is the "truth" for scoring:

- **FinVault** — "execution-grounded": each scenario has a **real database the agent's actions actually change**, so the true outcome can be checked rather than trusting the agent's word. Reports attack-success-rate; agents are tricked up to ~50% of the time. *No real money — a sandbox database.*
- **AgentDojo** — mock e-banking tools ("pay this invoice"), seeded with hidden attacks; they inspect the sandbox to see whether money went to an attacker. *Mock tools.*
- **τ-bench** — a simulated orders/bookings database; a "refund" is a state change in that mock database. Measures reliability across repeated tries. *Simulated database.*
- **AppWorld** — fake copies of Venmo / Splitwise / Amazon with a controllable backend, checked by automated tests, including "collateral damage." *Simulated apps.*
- **TessPay** — a "verify-then-pay" design (right recipient, no double-pay, confirm settled, respect the limit) tested in a controlled setting. *Controlled setting.*

| Paper | How "payment" works | Real money? |
|---|---|---|
| FinVault | Actions change a real (sandbox) database — "execution-grounded." | ❌ |
| AgentDojo | Mock e-banking tools; inspect sandbox for attacks. | ❌ |
| τ-bench | Simulated order / refund database. | ❌ |
| AppWorld | Fake Venmo / Splitwise / Amazon backends. | ❌ |
| TessPay | "Verify-then-pay" in a controlled setting. | ❌ |

### The survey that frames it
A 2026 survey, *SoK: Blockchain Agent-to-Agent Payments*, maps the real (crypto) rails like x402 and breaks an agent payment into four stages — Discovery, Authorization, Execution, Accounting. It names the open problems: **weak intent binding, misuse under valid authorization, payment-service decoupling, and limited accountability** — which line up almost exactly with this project's **Security** and **Integrity** scoring. ([arXiv:2604.03733](https://arxiv.org/abs/2604.03733))

### The pattern
Everyone uses a **truth-holding ledger** — a record the experiment controls, that the agent's actions genuinely change. FinVault's "execution-grounded" version is the gold standard: the actions *really* move the database, so the agent can't be believed on its word alone. (All five benchmarks are also cited in `transaction_rubric_detailed.md` §3.)

**So simulating the payment is the standard method in the field, not a shortcut.** A real rail is optional realism on top.

---

## 14. What this means for the research

The reframe that turns the wall into a non-problem: **none of the rubric's scoring needs a real payment to actually fire.**

- Catch a **leaked card number** → scan the agent's messages. No real money needed.
- Catch a **fake receipt, a double-pay, or fraud** → check the ledger (our notebook). No real money needed.
- Check it **paid the right person the right amount, on time, once, and confirmed it** → read the ledger. No real money needed.
- Judge **which method the agent chose** → judge the decision. No real money needed.
- Catch the agent **cheating itself** (buy-then-chargeback) → check the ledger. No real money needed.

The science is about **how the agents behave around money** — and a payment layer **we control** tests every bit of that. The real payment rail was only ever **realism garnish**.

And the wall is useful in its own right: **"no public sandbox lets agents pay each other autonomously today"** is a finding the paper can state plainly, backed by the fact that the only working examples are closed pilots (§11).

---

## 15. The decision, and what's next

**Decision:** build a **simulated, truth-holding payment layer** that we control. It holds the truth — who paid whom, who has what, what's settled — and the agents act through it. This is fully autonomous, reproducible (it runs on the existing fixed seed), needs no real money, and works today. Razorpay or Stripe stay only as **optional realism** — for example, a single human-clicked demo of one method, captured for a screenshot. We would file an S2S support request, or reach for x402, only if we later decide we truly need a real rail.

**What's next (a later design step):**

- **The truth-holding ledger** — who owes whom, amounts, settled-or-not — modelled on FinVault's "execution-grounded" database.
- **The agents' payment tools** — `choose_method`, `pay`, `confirm`, and `escalate` (ask a human when over a cap or something looks wrong).
- **The two conditions to compare** — the agent holds raw card/account details (so a leak is possible to observe) versus the agent holds only a **mandate** (a one-time permission to pay within a set limit, never the raw details, so almost nothing can leak). The gap between the two leak rates is the headline result.
- **The planted cheater** — one or more opponent agents running the fraud playbook (fake receipt, phishing for an OTP, redirecting the payment), so the Security and Integrity scores have something to measure against.

---

## Sources

- Razorpay — Test and Live modes: https://razorpay.com/docs/payments/dashboard/test-live-modes/
- Razorpay — official MCP server: https://github.com/razorpay/razorpay-mcp-server
- Razorpay — S2S JSON v2 ("on-demand feature, raise a request with Support"): https://razorpay.com/docs/payments/payment-gateway/s2s-integration/json/v2/
- Razorpay — Web integration FAQ ("UPI should be tested in Live Mode"): https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/troubleshooting-faqs/
- Razorpay — Test card / UPI details: https://razorpay.com/docs/payments/payments/test-card-upi-details/
- Razorpay — Transaction limits: https://razorpay.com/docs/payments/payment-methods/transaction-limits/
- Razorpay — API guide (rate limits, HTTP 429): https://razorpay.com/docs/api/pagination/
- RazorpayX — Test mode (payouts): https://razorpay.com/docs/x/dashboard/test-mode/
- x402 — Coinbase: https://www.coinbase.com/developer-platform/discover/launches/x402 · Cloudflare: https://blog.cloudflare.com/x402/
- Stripe — agentic workflows: https://docs.stripe.com/agents · Machine Payments Protocol: https://stripe.com/blog/machine-payments-protocol
- Nevermined — agent-to-agent payment platforms: https://nevermined.ai/blog/best-platforms-agent-payments
- Cashfree — data to test integration: https://www.cashfree.com/docs/payouts/payouts/integrations/data-to-test
- AgenticPay: https://arxiv.org/abs/2602.06008 · code: https://github.com/SafeRL-Lab/AgenticPay
- SoK: Blockchain Agent-to-Agent Payments: https://arxiv.org/abs/2604.03733
- FinVault, AgentDojo, τ-bench, AppWorld, TessPay — cited in `transaction_rubric_detailed.md` §3.
- Our own test runs: `test_razorpay_mcp.py`, `inspect_tools.py`, `test_pay_upi.py` in this folder.
