# Settlement Extension — Phased Plan

A short, sequenced plan to add a payment step to the existing A2A marketplace experiments and score Transactional Integrity with an LLM judge.

---

## Phase 1 — Baseline (already done in NeMo Gym)

Nothing to build here; this is what we extend. From the paper:

- Three stages run in NeMo Gym: **MarketDeal Basic**, **MarketDeal Review-Assisted**, and **SwapShop**.
- Six-dimension rubric, scored deterministically + GPT-4o LLM-judge for semantic dimensions.
- **75 runs** across 5 model configurations, with **fixed persona sets and seeds**.

We reuse all of it — personas, seeds, model pairings, the LLM-judge harness, and the metrics roll-up.

---

## Phase 2 — Add a payment simulation layer (Razorpay Test Mode)

Build a self-contained settlement layer in NeMo Gym, modeled on **Razorpay Test Mode** semantics (deterministic test instruments: UPI `success@razorpay` / `failure@razorpay`, test card, capped mandate). No real network calls yet — that's Phase 5.

**Day-wise (engineer using Claude Code):**

- **Day 1 — Scaffold.** Create the settlement Resources Server; add the tools (`list_payment_methods`, `choose_payment_method`, `pay`, `confirm_receipt`, `get_payment_status`) and the per-deal state machine (AGREED → METHOD_CHOSEN → PAID → CONFIRMED / FAILED). Get a no-op end-to-end run working.
- **Day 2 — Payment backend.** Implement the simulated backend with Razorpay-Test-Mode behavior: the five methods (UPI/card/bank/wallet/mandate) with their exposure/reversibility profiles, deterministic success/failure instruments, decline handling, spending-limit enforcement, double-pay block, and capped mandates. Seed-controlled.
- **Day 3 — Conditions + capture.** Wire `pay_mode`: **human-way** (raw credentials passed into `pay`) vs **agent-way** (mandate token only). Extend logging to capture tool-call inputs + logs (so credential leakage is observable). Add the cheater trick library (fake receipt, OTP request, payee redirect) with an on/off toggle.
- **Day 4 — Integration test.** Run a scripted agent through choose → pay → confirm for human-way and agent-way, cheater on and off. Confirm seed-reproducibility (same seed → identical run).
- **Day 5 — Fixtures + polish.** Hand-crafted test rollouts with known answers (clean pay, double-pay, credential leak, successful redirect, decline + recover); generate example rollouts; clean up.

**Output:** a runnable payment step inside NeMo Gym, with `pay_mode` and cheater as switches, producing a settlement ledger per run.

---

## Phase 3 — Finalize the Transactional Integrity rubric + LLMJ scoring

Reviewer-led; lock this before grading any run.

- Finalize the 7A–7E definitions and edge cases (e.g., what counts as a credential leak vs. over-share; when an attack counts as "successful"; credit for exceeding the limit but escalating).
- Write the **LLM-judge prompt + output schema** (per-sub-metric score + rationale + evidence span).
- Keep the settlement ledger as **ground truth** to validate the judge on objective items (right amount, no double-pay, within limit).

**Output:** a locked rubric and a judge prompt ready to grade.

---

## Phase 4 — Run the evaluation and record scores

- Re-run the **same runs as the previous experiments, with the same seeds**, now including the payment step. Matrix = `pay_mode {human, agent} × cheater {off, on}` across the existing model pairings.
- Grade each run with the LLMJ against the locked rubric; record **Transactional Integrity** scores alongside the six existing dimensions.
- Validate the judge: agreement vs. ledger ground truth (objective items) and vs. a small human-rated sample (soft items, esp. method choice).

**Output:** Transactional Integrity scores across the matrix, comparable to the original runs, with results tables for the paper.

---

## Phase 5 — Add the S2S layer (real Razorpay test rails)

Optional, for external validity.

- Request **Razorpay S2S activation** (on-demand feature — needed to drive payments via API with no browser; file the request early).
- Implement the real Razorpay test backend behind the same interface (Orders → S2S create payment → poll; mandate via UPI AutoPay).
- Run the realism condition and compare against the simulated layer.

**Output:** the same evaluation, validated on real Razorpay test rails.

---

### Quick start

1. **Engineer:** begin Phase 2, Day 1.
2. **Reviewer:** start Phase 3 (rubric + judge prompt) in parallel, and file the Phase 5 S2S request now.
