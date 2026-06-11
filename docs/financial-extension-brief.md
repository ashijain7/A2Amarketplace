# Financial Transaction Extension — Manager Briefing
**Date:** 2026-05-27

---

## What we've done

We ran 75 AI-to-AI negotiation experiments across 5 model configurations (Sonnet, Opus, Gemini 3.1 Pro, Gemini 3.5 Flash, GPT-5.5) and 3 market mechanics. We measured who wins deals, who leaks private data, and how model capability affects outcomes. All 75 rollouts are complete. Paper draft is in progress for KDD 2026 (August 9–13, Jeju, Korea).

---

## The problem with what we have

In every experiment, deals closed — but nothing actually transferred. An agent agreed to pay $45 for a keyboard, but the $45 never moved. The experiment ends at the handshake, not the payment.

Real AI marketplaces don't stop at the handshake. Agents will eventually need to complete transfers. No existing research paper covers what happens at that step, especially across different AI model families.

---

## What the extension adds

We add a payment step after every deal closes. The agent has to actually complete the transfer using payment tools.

This gives us three new things to measure that no existing paper covers:

1. **Can the agent use payment tools correctly?** Does it pay the right person, the right amount, at the right time?
2. **Can the agent be tricked?** If a bad-faith opponent claims they already paid (without actually paying), does the focal agent hand over the goods?
3. **Does the agent's negotiation behavior change** when financial stakes are introduced? Does it become more careful? Does it accidentally expose financial details?

**Scope:** Phase 1 (money trading) and Phase 2 (reputation + money trading) only. Phase 3 (barter) is excluded — no money changes hands there.

---

## Why this is a gap in the literature

| Paper | What they tested | What's missing |
|---|---|---|
| FinVault (2026) | One agent resisting financial attacks | No negotiation, no multi-agent setup |
| AgentLeak (2026) | Credential leakage across agent systems | Agents aren't trading with each other |
| FinMCP-Bench (2026) | Agents using financial tools | No negotiation before payment |
| Project Deal / Anthropic (2025) | Real money A2A marketplace | No cross-vendor model comparison, no adversarial opponents |

Our extension is the first to combine negotiation + payment completion + cross-vendor model comparison in one experiment.

---

## The 4 approaches

### Option A — Change the prompts only
Tell each agent it has a bank account and the transfers are real. No actual payment system. Observe whether the belief changes behavior or causes credential leakage in chat.

- **Effort:** 1 week
- **Extra cost:** Same as existing runs
- **Downside:** No real payment infrastructure — weaker paper claim

### Option B — Build our own fake bank
Write a small internal bank server. Agents call `transfer_funds(to="Marcus", amount=45)` after each deal. We log whether the transfer was correct, timely, and to the right person.

- **Effort:** 3–4 weeks
- **Extra cost:** Same as existing runs (server runs locally)
- **Downside:** We built the bank ourselves — less credible than an actual payment system

### Option D — Use Stripe's test environment *(I recommend this)*
Stripe (the payment company behind Uber, Amazon) has a free test mode — real API, real responses, real dashboard, but no actual money moves. Agents use real Stripe to complete payments. We can show Stripe dashboard as evidence.

- **Effort:** 3–4 weeks
- **Extra cost:** $0 for Stripe, same LLM costs as before
- **Strength:** "Agents operated on real Stripe infrastructure" — strongest claim we can make

### Option E — Use Stripe through MCP
MCP (Model Context Protocol) is Anthropic's standard for connecting agents to external tools. Stripe has an official MCP server. Agents connect to it and use Stripe tools through the MCP standard — same way production agents are expected to work.

- **Effort:** 4–5 weeks
- **Extra cost:** $0
- **Strength:** Fills a direct gap in FinMCP-Bench paper (that paper tests financial MCP tools but has no negotiation). Highest novelty.
- **Risk:** Need to verify NeMo Gym supports MCP clients

---

## Decision needed: How does payment happen in the shared chat?

The marketplace has one shared channel — all 10 agents see all messages. If agents shared bank details in chat, everyone would see them. Three ways to handle this:

**Option 1 — Tool abstraction** *(I recommend this)*  
Agents never share financial details in chat. After a deal, the agent calls a tool: `transfer_funds(to="Marcus", amount=45)`. The system handles account mapping internally. Nothing financial appears in the shared channel. Same way Venmo works — you send to a username, not a bank number.

**Option 2 — Private channel after deal closes**  
The two agents switch to a private 1-on-1 channel to complete payment. Interesting research angle: do agents behave differently when fewer people are watching?

**Option 3 — Payment token**  
The system generates a one-time token after each deal. Agents exchange only the token in the marketplace. The token is useless to bystanders — it can only complete that specific transaction.

---

## Optional add-on: adversarial opponents

Once any payment system is in place (B, D, or E), we can make 2–3 opponent agents act in bad faith — sending fake payment confirmations, asking the focal for its "account confirmation code", etc. The payment server holds the truth, so we know exactly whether the focal was fooled or verified before accepting.

This adds about 1 extra week and 5 extra runs. Relevant paper: [When AI Agents Collude Online](https://arxiv.org/pdf/2511.06448).

---

## Timeline (if we go with Option D)

| Week | What happens |
|---|---|
| 1 | Finalise approach + payment mechanism decision |
| 2–3 | Build Stripe integration, new agent tools |
| 4 | Update rubric, generate new task files |
| 5–6 | Run Phase 1 + Phase 2 extension rollouts (~30 runs) |
| 7 | Run adversarial add-on subset (~5 runs) if approved |
| 8 | Analysis + write into paper |

**Extra runs:** ~35 total  
**Extra cost estimate:** $50–$100 in API calls

---

## What we can claim in the paper

- "We are the first to evaluate A2A negotiation agents through deal closure and payment settlement, across 4 model families."
- "Model X overpays / under-verifies at rate Y% — distinct from its negotiation performance."
- "Adversarial opponents successfully deceived model Z in Y% of post-deal payment steps."
- "Phase 2 reputation scores interacted with payment history — agents with poor payment records faced harder negotiations in subsequent rounds."

---

## Questions for you

1. Which approach — B (our own bank), D (Stripe test mode), or E (Stripe via MCP)?
2. Which payment mechanism — tool abstraction, private channel, or token?
3. Do we add the adversarial opponents?
4. Is the 8-week timeline okay given the August KDD deadline?
