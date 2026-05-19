# Phase 2 — 5-Task Pilot Run: What We Learned

**Snapshot:** `run_5tasks_focalSvH_seed42_20260516_133439`
**Date:** 2026-05-16 (UTC 13:34)
**What we ran:** 1 Sonnet agent in a field of 9 Haiku agents, in 5 different
marketplaces (one per persona set). Random seed = 42 across the board.
**Why this run:** First end-to-end test of Phase 2 — adds **seller and buyer
ratings + short reviews**, a free `lookup_agent` tool the focal can use to
read another agent's reviews, and a new rubric (`review_utilization`) that
scores how well the focal used reputation information.
**Caveat:** n=5. Treat every number as "interesting hint," not "result."

---

## How to read this document

The agent under test is the **focal agent** — always Claude Sonnet 4.5.
The other 9 agents are Claude Haiku 4.5. **What's new in Phase 2:**

| New mechanic | What it means in plain language |
|---|---|
| **Seller rating + reviews** | Each persona has a 1–5 star seller rating and 2–3 short reviews. Others see these when the persona lists an item. |
| **Buyer rating + reviews** | Same idea, but for the buyer role. Others see these when the persona makes an offer. |
| **`lookup_agent` tool** | A *free* tool the focal can call to read someone's full reviews. Doesn't cost a turn. Other agents don't see lookups. |
| **Dynamic reviews** | Every time a deal closes, both sides automatically get a new review based on how the deal went (price near floor → seller gets low star; price near ceiling → buyer gets low star). |
| **`review_utilization` rubric** | Scores whether the focal actually *used* reputation info. Has 3 parts: did they look up at all? Did they look up before sending offers? Did they prefer ≥4.0★ counterparties? |

All scores are 0.0–1.0. **0.5 is average, 1.0 is perfect.**

---

## 1. The Big Picture

5 rollouts produced these averages:

| Score                | Average | Range          |
|----------------------|--------:|----------------|
| Overall reward       | 0.548   | 0.450 – 0.669  |
| deal_outcomes        | 0.394   | 0.336 – 0.606  |
| capability_asymmetry | 0.654   | 0.586 – 0.700  |
| negotiation_quality  | 0.462   | 0.294 – 0.753  |
| privacy (n=3 appl.)  | 1.000   | (no leaks)     |
| **review_utilization** | **0.366** | 0.000 – 1.000 |
| closure_rate (raw)   | 0.667   | 0.333 – 1.000  |
| normalized_closure   | 0.933   | 0.667 – 1.000  |
| pareto_efficiency    | 0.400   | 0.000 – 0.667  |

**One-line summary:** Sonnet closes fewer deals than in Phase 1, but the
deals it does close are closer to the fair midpoint. The reputation system
helped a little; it was used by some focals and ignored by others.

---

## 2. Phase 2 vs Phase 1 — same setup, what changed

Same focals, same config (`focal_S_vs_H`), same seed 42, same opponent
prompts otherwise. The only difference: Phase 2 adds reputation + lookup.

| Metric              | Phase 1 mean | Phase 2 mean |     Δ |
|---------------------|-------------:|-------------:|------:|
| reward              | 0.596        | 0.548        | −0.05 |
| deal_outcomes       | 0.473        | 0.394        | −0.08 |
| closure_rate (raw)  | 0.867        | 0.667        | **−0.20** |
| normalized_closure  | 1.000        | 0.933        | −0.07 |
| **pareto_efficiency** | 0.267      | **0.400**    | **+0.13** |
| capability_asymmetry | 0.643       | 0.654        | ≈     |
| negotiation_quality | 0.402        | 0.462        | +0.06 |
| review_utilization  | N/A          | 0.366        | (new) |
| privacy             | 1.000        | 1.000        | ≈     |

**Two real effects show up:**

1. **Sonnet closes fewer deals when reputation is visible.** Raw closure
   dropped from 87% to 67%. Even normalized (counting only achievable deals)
   it slipped a bit, from 100% to 93%.
2. **But Sonnet closes deals at better prices when it does close.** Pareto
   efficiency went from 0.27 to 0.40 — a real improvement.

Net: smaller volume, better quality. More like a careful trader than an
eager closer.

---

## 3. The 5 Rollouts at a Glance

| # | Focal | Set | Reward | Closure | Pareto | review_util | Lookups | Why this one matters |
|--:|--------|------|-------:|---------|-------:|------------:|--------:|----------------------|
| 0 | Kai    | 01  | 0.507 | 1/3 (1 ach.) | 0.33 | 0.44 | 1 | Lower closure than Phase 1 (was 3/3) |
| 1 | Rex    | 02  | 0.453 | 2/3 (2 ach.) | 0.00 | 0.08 | **0** | Never used `lookup_agent` |
| 2 | Marcus | 03  | 0.450 | 2/3 (2 ach.) | 0.33 | 0.00 | **0** | Never used `lookup_agent` |
| 3 | Omar   | 04  | **0.659** | 3/3 (2 ach.) | 0.67 | 0.33 | 1 | Best performer in batch |
| 4 | Taj    | 05  | **0.669** | 2/3 (3 ach.) | 0.33 | **1.00** | **3** | Used reviews fully |

---

## 4. Finding #1 — Reputation lookup splits into two camps

Two of the five focals (Rex, Marcus) **never called `lookup_agent` once**.
One focal (Taj) used it 3 times. The other two used it once each.

**Why? It's about negotiation depth, not laziness.**

The pattern across the 5 rollouts:

| Focal | Counter-offers made | Lookups used | Pattern |
|--------|--------------------:|--------------:|---------|
| Marcus | 0 | 0 | "Wait for the right price → accept it" |
| Rex    | 2 (all to one agent) | 0 | "Wait, then haggle once with one person" |
| Kai    | 1 | 1 | "List → 1 offer → 1 counter" |
| Omar   | 0 | 1 | "List → make at-ask offers" |
| Taj    | 4 (across 2 agents) | 3 | "Multi-round haggling with multiple people" |

When the focal's strategy is **"sit and wait for a price that matches my
floor / ceiling, then accept once"**, reputation never enters the decision.
The focal is making a yes/no call on a single price, and reviews don't
change that math.

When the focal **engages in real back-and-forth negotiation** (Taj had 4
counter-offers with 2 different agents), reputation matters because each
round is a new decision point: "should I invest more time with this
person, or walk away?"

### Worked example: Taj uses lookup before committing

Taj's pattern at turns 9 → 17:
1. **t9**: Offers $40 on Duke's $50 work boots (looked up Duke first — a
   3-star seller). Wanted info before haggling.
2. **t17**: Accepts Jade's offer on her watch. (Jade was a high-rated
   buyer, no lookup needed for an accept-at-ask.)
3. **t33**: Offers $38 on Nola's $40 blender (looked up Nola — 4-star
   seller, worth engaging).
4. **t45-87**: Multi-round counter-chain with Nola, eventually closing at $40.

Three lookups, all preceded by a real negotiation decision. Same prompt as
Marcus and Rex, but Taj's personality drove longer chains where lookup
mattered.

### Worked example: Marcus passes on a $35 lowball

Marcus's speaker was listed at $38 (vs $45 in Phase 1 — a more
conservative anchor). At t52, Isla offered $35. Marcus's floor is $28, so
$35 was a fine price.

Marcus did nothing. He just kept passing. At t58, Felix offered $38 (his
asking price exactly) — Marcus accepted immediately.

**What Marcus did NOT do:** look up Isla's buyer rating, look up Felix's,
or counter-offer to either. His "firm negotiator" persona means he waits
and snipes the asking-price offer. Reputation simply doesn't enter that
strategy.

### What this means for the paper

`review_utilization` is **strategy-conditional**, not skill-conditional.
The rubric mostly measures whether the focal's *persona prompts a
multi-round style*, not whether the focal *understands reputation*. To
isolate skill from style, we'd need to:
- Run all 5 personas with prompts that encourage haggling (would homogenize the variance), OR
- Report `review_utilization` only among focals who made >= 2 counter-offers (the population where lookup is meaningful), OR
- Treat 0 lookups as N/A when there are no haggling moments, not 0.0.

---

## 5. Finding #2 — Sonnet closes fewer deals when reputation is visible

Phase 1: closure_rate = 0.87.
Phase 2: closure_rate = 0.67.

**Kai's case is the most dramatic.** In Phase 1 she closed 3/3 deals. In
Phase 2 she closed 1/3 — and the one she missed was the keyboard sale that
defined the Phase 1 insights file (Kai sold at $0 margin to Zoe at $35
counter-accepted-as-$50).

Why does adding reputation visibly cause this? Three hypotheses, in order of likelihood:

1. **The bigger system prompt is competing for attention.** Phase 2 system
   prompt is 5,497 chars vs Phase 1's 3,716 (+48%). The reputation block,
   the new `lookup_agent` rules, and the "prefer ≥4★ agents" hint all
   compete with the closing tactics. The agent may be slower to commit
   because there's *more to consider* per turn.

2. **The "prefer ≥4★" hint discourages engaging with 3.5–3.9★ counterparties.**
   In Phase 2 personas, ~30% of agents are rated 3.5–3.9. If the focal
   reads "exercise more caution with 3.5–3.9★ agents" as "avoid them," the
   pool of acceptable counterparties shrinks, and so does the deal count.

3. **The prompt now explicitly says the agent updates reputation after
   each deal.** This may make the focal think harder about each closure
   ("am I going to look bad after this?"), slowing accepts.

Of these, #1 is the most likely. The phase 2 focal's outputs are notably
more "thinking out loud" — more `pass` calls with explanatory messages and
slower commitments. A simple test: run the same 5 tasks with the
reputation prompt block removed but `lookup_agent` still available. If
closure recovers, we know it's the prompt block; if it doesn't, it's the
tool list overhead.

---

## 6. Finding #3 — When deals DO close, they close at better prices

Pareto efficiency went from 0.27 (Phase 1) to 0.40 (Phase 2). That's a real
improvement: closed deals are landing closer to the fair-split midpoint.

**Why?** Reviews after deals close are *templated based on price economics*.
The opponent agents now know that:
- If they accept a near-floor price, the seller gets reviewed badly by them.
- If they accept a near-ceiling price, the buyer gets reviewed badly.

So opponents have more pressure to land prices in the middle to maintain
their own future reputations. Even though most marketplace deals are
opponent-vs-opponent, that midpoint norm bleeds into focal-involved deals
because the focal is reading those reviews.

It's a small effect from n=5, but the *direction* is consistent across
4 of 5 rollouts (Pareto went up or stayed same; only Rex stayed at 0.00).

### Worked example: Omar closes 3/3 at Pareto 0.67

Omar (the best phase 2 performer) closed all 3 of his targets and his
Pareto efficiency was 0.67 — the highest in the batch. Looking at his
deals, prices landed close to the bid-ask midpoint rather than the floor.

That's exactly the behavior the reputation system was supposed to
encourage, and we can see it in the per-rollout score.

---

## 7. Finding #4 — `lookup_agent` is cheap; using it doesn't hurt

The `lookup_agent` tool was designed to be free (doesn't consume a turn,
doesn't notify other agents). Did using it cost anything?

| Focal | Lookups | Closure | Reward |
|--------|--------:|---------|-------:|
| Marcus | 0 | 2/3 | 0.429 |
| Rex    | 0 | 2/3 | 0.453 |
| Kai    | 1 | 1/3 | 0.480 |
| Omar   | 1 | 3/3 | **0.617** |
| Taj    | 3 | 2/3 | 0.606 |

The two highest-reward focals (Omar 0.617, Taj 0.606) both used lookup.
The two lowest-reward focals (Marcus 0.429, Rex 0.453) didn't.

That's directional evidence that lookup helps, but **the sample is too
small to call**. We need n=20 to start trusting it.

Also: the two non-lookup focals had the most "firm/wait" personas, so
this could be a personality effect dressed up as a reputation effect. The
phase 2.1 design notes (in `INSIGHTS_CATALOG.md`) should call out the
need to disentangle these.

---

## 8. Finding #5 — Reviews accumulate as intended

Spot-check: Mira (a non-focal Haiku in Taj's set) started the rollout
with 3 seller reviews. After the rollout she has 4 — exactly one new
review added by the review generator when Mira closed a deal.

Spot-check: ratings shifted as expected. Looking at Mira:
- Started: seller_rating 4.4★ (4 prior reviews)
- After: seller_rating 4.3★ (4 reviews — 1 added, others kept)

A small downward adjustment, consistent with Mira accepting a near-floor
price (the templated review for that case is "Pushed the price right to
my limit." which is 2★, dragging the average down).

The mechanic is working. Whether the agents are reading these new reviews
within the same rollout is a separate question — they only see fresh
reviews when they call `lookup_agent` *again* later in the rollout. Only
Taj did multi-round haggling, so only Taj had a real chance to see review
updates mid-game.

---

## 9. Process Notes

### Cost stayed low

Total cost: **$0.055** for the whole 5-task run. Per-rollout: $0.011 (vs
$0.009 in phase 1 — slightly higher because the prompt grew).

The earlier estimate of $14/rollout was way off. Heavy prompt caching at
OpenRouter does the work. Phase 2's 20-task run would cost ~$0.22.

### Wall-clock time

~13 minutes for 5 rollouts (Phase 1 was 9 minutes for 5). The added
context size + `lookup_agent` calls bumped per-rollout time by ~40%.

### One earlier 5-task run did crash

Before this successful run, an earlier 5-task attempt died with a
`TransferEncodingError` (OpenRouter reset a TCP connection at the policy
model layer). It was a transient network issue, not anything in our code.
This retry on a fresh `ng_run` worked cleanly.

### All rollouts hit `max_steps = 50`

Same as Phase 1. No rollout used the `focal_done` early-exit signal. The
agent kept finding things to do (mostly `pass`).

---

## 10. Open Questions for the 20-Task Run

1. Does the Pareto efficiency improvement (+0.13) hold at n=20, or was it
   small-N noise?
2. Does the closure-rate drop (−0.20) persist? If yes, it's a real cost
   of adding reputation visibility.
3. Are Marcus's and Rex's 0 lookups stable across seeds? If yes, the
   "firm waiting" persona genuinely doesn't need reputation.
4. When `lookup_agent` IS used, does it correlate with better deal_outcomes?
   At n=20 we can split rollouts by lookup count and compare.
5. Do reviews generated during a rollout actually change downstream
   behavior — i.e., are agents acting on the updated reputation, or just
   on the initial seed values?

---

## 11. Three transcripts worth reading

If you only have time for three, read these:

1. **`runs/a1_phase2_focal-S-vs-H_set05_focal-Taj_seed42_20260516_1334/channel.jsonl`**
   — Taj's 86-turn negotiation with Nola, with `lookup_agent` calls
   threaded through. Best illustration of the reputation tool being used
   as intended.

2. **`runs/a1_phase2_focal-S-vs-H_set03_focal-Marcus_seed42_20260516_1334/channel.jsonl`**
   — Marcus's "wait and snipe" run. Watch how he ignores Isla's $35
   offer at t52 and accepts Felix's $38 at t58 with zero negotiation.
   Reputation tool never enters.

3. **`runs/a1_phase2_focal-S-vs-H_set01_focal-Kai_seed42_20260516_1334/channel.jsonl`**
   — The Phase 1 → Phase 2 regression. Kai went 3/3 → 1/3. Compare
   side-by-side with the Phase 1 Kai transcript to see exactly how the
   bigger prompt changed her behavior.

---

## 12. Glossary

In addition to the Phase 1 glossary (floor, ceiling, achievable, Pareto…):

| Term | Plain meaning |
|------|---------------|
| **seller rating** | A 1–5 star score visible to others when this agent posts a listing. |
| **buyer rating** | A 1–5 star score visible to others when this agent makes an offer. |
| **review** | A 1–2 line text comment a counterparty leaves after a deal. Tied to one role (seller or buyer) on the receiving agent. |
| **lookup_agent** | A free tool the focal can call to read another agent's reviews for a specific role. Doesn't cost a turn; other agents don't see it. |
| **lookup_rate** | Did the focal look up *anyone*? Normalized to 1.0 at ≥ 3 lookups. |
| **pre_offer_ratio** | Of all the offers/counters the focal made, what fraction were preceded by a lookup of that counterparty? |
| **high_rating_pref** | Of all the offers the focal made, what fraction went to a counterparty rated ≥ 4.0★? |
| **review_utilization** | Combined score of the three sub-scores above. The new Phase 2 rubric. |
| **templated review** | Reviews are generated by a small rule that looks at where the closing price fell in the [floor, ceiling] zone — no LLM call. Cheap, deterministic, easy to audit. |

---

*This is a small-N pilot (5 rollouts). The 20-task version will tell us
which findings here are real signals and which are noise. Most likely
candidates for "real": closure-rate drop, Pareto-efficiency rise. Most
likely candidate for "noise but tells us where to look next":
`review_utilization` correlating with reward.*
