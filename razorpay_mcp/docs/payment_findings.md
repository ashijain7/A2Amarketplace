# Payment Backend Feasibility — Summary

## 1. The question

Our marketplace has 10 agents that negotiate and agree on prices, but no money moves once a deal closes. We wanted to add a real **payment step** — after a deal, the buyer's agent pays the seller's agent — with one hard requirement: it must happen with **no human in the loop**. No person taps a phone, enters a PIN, or types a code. The experiment needs agents handling money entirely on their own, across many deals.

The natural first choice was **Razorpay test mode** — a free, fake-money practice version of the Indian payments company Razorpay — because it offers real Indian rails (UPI, cards) and ships an official adapter (an "MCP server") that lets an AI agent call its actions as tools. The question we set out to answer:

> Can free Razorpay test mode let one agent pay another, automatically, with no human?

The answer turned out to be **no** — and finding out exactly why told us what to build instead.

---

## 2. What we built and tested

In a self-contained folder (`razorpay_mcp/`) we set up a free Razorpay account with **test keys** (the secret a program uses to reach the account), launched Razorpay's official **MCP server** through Docker, and wrote three small probe scripts that connect to it and report what the account can actually do. The same server is also wired into Claude Code, reading the same keys. Nothing here touches real money — it is all test mode.

---

## 3. What we found

The MCP server exposed **41 tools** and the basics worked, but the one thing we needed did not:

| Check | Result | What it means |
|---|---|---|
| MCP server reachable | ✅ PASS | The "agent calls Razorpay as tools" idea works (41 tools). |
| Keys authenticate | ✅ PASS | The test keys are valid. |
| Create a bill (order) | ✅ PASS | A real ₹500 test order was created. The agent *can* start a payment. |
| Autonomous-pay tool present | ✅ PASS | The tool exists in the toolbox. |
| Complete a payment (UPI) | ❌ FAIL | Razorpay replied `URL not found` — the agent could not finish the payment. |
| Push money (payouts) | ❌ FAIL | Needs RazorpayX, a separate product we don't have. |

In one line: **the agent can *ask* for money automatically, but cannot *complete* a payment automatically.**

---

## 4. Why autonomous pay is blocked

Two separate walls, each explained simply.

**RazorpayX (the "push money" wall).** Regular Razorpay is built to *receive* money — like a shop's **card machine** (money in). Sending money *out* needs a different product, **RazorpayX** — the business's own **current account with a chequebook** (money out). The "push" model (the buyer's agent sending money straight to the seller) needs an account to send *from*, and that's RazorpayX. The error we got — `missing required parameter: account_number` — was literally Razorpay asking which account to pull from. We don't have one, and getting one means full business onboarding (a registered business, KYC). Too heavy for a sandbox, so we set push aside.

**S2S (the "complete a payment" wall).** Normally a Razorpay payment runs through a **checkout page** where a human taps "pay." Completing a payment with *no* page and *no* human needs a power called **S2S (server-to-server)** — letting a program create *and* finish a payment by itself. It is exactly what we need, and it is blocked two ways: Razorpay says S2S is "an on-demand feature — raise a request with Support to activate it" (no dashboard toggle), and separately that **UPI "should be tested in Live Mode"** and isn't really supported in test mode. So a real autonomous UPI payment would need both an S2S request *and* Live Mode — real KYC, a real business, and **real money** — which is far too much for a research sandbox.

This isn't a setup mistake. **Test mode is built for a shop developer rehearsing a checkout page for human customers, not for a headless robot paying by itself.**

---

## 5. The wider landscape

Razorpay isn't the only option, so we checked the alternatives — asking each: *can an agent pay another agent with no human, for free, today?*

| Option | No human? | Free? | Method | The catch |
|---|---|---|---|---|
| **x402** (Coinbase) | ✅ | ✅ test network + faucet | Crypto (USDC) | Crypto, not UPI/cards — but genuinely headless. |
| **Stripe** (already set up) | ✅ | ✅ test mode | Cards; stablecoin | No Indian UPI. |
| Nevermined / Skyfire / Payman | ✅ | partly | Fiat + crypto | Startups; more setup. |
| Cashfree (India) | ◑ simulated | ✅ | UPI / bank | Modes gated by Cashfree — same wall. |
| Razorpay (tested) | ❌ | ✅ | UPI / cards | Autonomous pay blocked. |

Two of these actually work: **x402**, where agents pay each other in crypto on a free test network with no human (150M+ real payments to date), and **Stripe**, which completes payments headlessly and which the project already has wired — but neither does Indian UPI. **For UPI specifically, no free, no-human option exists anywhere**: Razorpay and Cashfree both gate it, and the only systems that combine Indian rails with autonomous agent pay are the closed NPCI–OpenAI/Anthropic pilots. So the India-flavoured payment has to be simulated.

---

## 6. How other research handles payment

This is the reassuring part. We read how the relevant papers do the money step:

- **AgenticPay**, the closest work to our project (a buyer-seller negotiation benchmark, 110+ tasks), has **no payment step at all** — a "transaction" is just a recorded agreement, with no wallets or ledgers. It stops where we begin.
- The benchmarks that *do* involve payment — **FinVault, AgentDojo, τ-bench, AppWorld, TessPay** — **all simulate** it against a controlled database or ledger. None use real money. FinVault's "execution-grounded" version (the agent's actions really change a sandbox database) is the gold standard.

So a **simulated, truth-holding ledger is the accepted method in the field**, not a shortcut. A real payment rail is optional realism on top.

---

## 7. What this means, and the decision

None of our scoring needs a real payment to fire: leaks are caught by scanning the agent's messages, fraud and double-pay by checking the ledger, method choice by judging the decision. The science is about how agents *behave* around money — which a payment layer we control tests completely.

**Decision:** build a **simulated, truth-holding payment layer** that we own. It records who paid whom and who has what, runs fully autonomously, and lets us score privacy, fraud, method-choice, and honesty — working today, with no real money. Razorpay and Stripe stay only as optional realism. And the wall itself is a result worth reporting: **no public sandbox lets agents pay each other autonomously today.**

---
