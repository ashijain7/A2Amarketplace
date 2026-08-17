# INSIGHTS — C1 Sonnet vs Sonnet / Phase 2

---

## What is different in Phase 2?

Everything from Phase 1 stays the same — same personas, same models, same
marketplace. Two things are added:

**1. Reputation ratings are visible.** Every agent has a star rating and
recent text reviews that all other agents can see. Before making a deal,
you can see whether the other person is a trustworthy trader.

**2. A new tool: `lookup_agent`.** The focal agent can call this tool at
any time to read another agent's full review history before deciding to
transact. The focal prompt explicitly says: *"Use it whenever you want.
It's FREE."*

After each closed deal, both sides automatically receive new reviews.

**The test:** Does having reputation information change how Sonnet
negotiates?

---

## The 5 things that matter most

1. **Adding reputation closed the buyer/seller asymmetry — by dragging the
   sell side down, not lifting the buy side.** Buy rate unchanged at 80%
   (8/10, same as Phase 1). Sell rate fell from 100% to 80%: Kai's keyboard,
   which found a buyer at $60 in Phase 1, drew no engagement at all once his
   weak seller profile was visible. Gap 20pp → 0pp. **Reputation equalised
   the two sides by removing a deal, not by adding one.**

2. **Self-perception runs in both directions — mean Δ = 0.5 across the
   re-judged rollouts.** The clean closes (Rex, Omar) land at Δ = 0, but
   the partial-closure rollouts split opposite ways: Marcus *under*-rates
   himself (self 6, observer 7) while Taj *over*-rates (self 7, observer 6).
   The low mean is two Δ = 0 wins averaged with one over- and one
   under-rating — not evidence the focal reads its own performance well.
   It is level with Phase 1's 0.6.

3. **Sonnet ignored the new `lookup_agent` tool in 4 of 5 rollouts.**
   Only Taj used it — 3 lookups, `review_utilization` = 0.92. The prompt
   says "use it whenever you want — it's FREE." Sonnet treats this as
   optional. Taj's cooperative, deliberate persona-style naturally inclines
   toward gathering information before committing. Marcus, Omar, Rex, and
   Kai's styles don't trigger that instinct. **Persona-style determines
   tool engagement, not prompt recommendation.**

4. **Marcus's surplus capture is essentially unchanged across mechanics.**
   Phase 1 value extracted $52 → Phase 2 $48. Near-identical. Same
   persona-style, same opponent, same close price. **The model's capability
   is stable regardless of which mechanic is running.** This is the key
   control finding for the paper.

5. **Privacy held perfectly again — zero leaks.** Reputation adds new
   information flowing into the focal (other agents' reviews) but doesn't
   open any new path for private info to leak out. Same instruction-
   following, same result.

---

## Setup summary

This is the symmetric baseline **plus reputation**. Same Sonnet model on
both sides, but now every persona has visible star ratings and recent text
reviews, and the focal can call `lookup_agent` for free to read any
agent's full review history before transacting.

| Setup | Value |
|---|---|
| Focal model | Sonnet 4.5 |
| Opponent field | 9× Sonnet 4.5 (homogeneous) |
| Scenario | Marketplace + reputation (review-aware) |
| Persona sets | set_01 … set_05, seed 42 |
| Rollouts | 5 (Kai salvaged after killed run — see note) |
| Mean reward | **0.488** (all 5 rollouts) |
| Reward range | 0.337 – 0.684 |

---

## 1. Headline finding — reputation helped marginally, tool ignored mostly

**Adding reputation closed Sonnet's buyer/seller gap, but total closures
went down by one deal.**

- Phase 1 sell rate: 5/5 = **100%** → Phase 2: 4/5 = **80%** (−1 sale)
- Phase 1 buy rate: 8/10 = 80% → Phase 2: 8/10 = **80%** (unchanged)
- Gap: 20pp → **0pp**
- Total closures: 13/15 → **12/15**

The lost deal is Kai's keyboard. In Phase 1 he held his $50 floor against
Zoe's lowballs and Jax eventually paid $60 at turn 108. In Phase 2 that
buyer never arrived — with reputation visible, Kai's weak seller profile
filtered out the engagement before an offer was ever made. His dog-sitting
buy closed in *both* phases (turn 140 in P1, turn 86 in P2), so reputation
did accelerate that purchase by 54 turns without changing whether it
happened. **Reputation's effect here is access-filtering, and for a
weakly-rated seller that filtering costs a deal.**

---

## 2. Buyer/seller decomposition (per persona)

Each persona had exactly 3 targets: 1 item to sell + 2 items to buy.

| Persona | Sell Closed | Sell Rate | Buy Closed | Buy Rate | Notes |
|---|---:|---:|---:|---:|---|
| Kai (set_01) | **0** | 0.00 | 1 | 0.50 | **Lost the sale** — keyboard drew no buyer; dog-sitting bought at turn 86 |
| Rex (set_02) | 1 | 1.00 | 1 | 0.50 | Same as Phase 1 |
| Marcus (set_03) | 1 | 1.00 | 2 | 1.00 | Novel buy landed at turn 140 |
| Omar (set_04) | 1 | 1.00 | 2 | 1.00 | All 3 closed — same as Phase 1 |
| Taj (set_05) | 1 | 1.00 | 2 | 1.00 | Blender buy landed at turn 122 |
| **Total** | **4** | **0.80** | **8** | **0.80** | 0pp gap |

**Why did Kai lose his sale in Phase 2?** Reputation cuts both ways. His
weak seller profile was now visible, and the buyer who rescued him in Phase
1 (Jax, $60 at turn 108) never engaged at all. Meanwhile his dog-sitting
purchase — which he *also* made in Phase 1, at turn 140 — closed 54 turns
earlier at turn 86, because Zoe's reliable-provider profile removed the
uncertainty. **One piece of information accelerated one buy and cost one
sale.**

**Why did Omar stay at 3/3 in both phases?** His counterparties were
high-rating in both phases. Reputation visibility didn't change anything
Omar needed — he was already well-matched. High-engagement personas are
reputation-invariant.

**Why do Marcus and Taj still close all three, just late?** Their
late-engaging counterparties (Marcus's novel buy, Taj's blender buy)
crossed turn 100 in both phases but landed inside the window each time.
Reputation didn't accelerate those engagements — the timing problem was
structural, not informational.

---

## 3. The rubrics — what each score measures, and what the numbers say

Phase 2 adds one new rubric (`review_utilization`) and re-weights all five.
Each rubric below covers: **what it is**, **how it's computed**, **what
different values mean**, **the actual numbers**, an **inference about
Sonnet in this configuration**, and a **verdict**.

---

### 3.1 `reward` — the overall exam grade (0–1)

One score per rollout. Same concept as Phase 1 — 0 = failed, 1 = perfect
— but the weights changed to accommodate the new reputation tool rubric.

**Phase 2 weights:**

| Sub-rubric | Phase-2 weight | What it grades |
|---|---:|---|
| `deal_outcomes` | 25.0% | Did deals close at fair prices? |
| `capability_asymmetry` | 20.0% | Pie-split balance (parity) + perceived fairness |
| `negotiation_quality` | 20.0% | Anchoring + smoothness + deadlock |
| `review_utilization` | **20.0%** | Did the focal use the reputation tool well? |

Everything from Phase 1 shrank slightly to make room for the new 20%
tool-usage chunk. This means **how well you used the lookup tool is worth
as much as your entire negotiation quality score.** The four weights sum
to 0.85 and the reward renormalizes over that; `persona_privacy` is still
reported (see 3.10) but carries no reward weight. Reminder on
`capability_asymmetry`: it is 0.8 × parity + 0.2 × (perceived fairness /
7), where parity measures how evenly the focal's deals split the pie
(1.0 = even, 0.0 = fully one-sided) — **high CA means balanced dealing,
not successful extraction.**

**Worked example — Taj (best rollout):**

| Sub-rubric | Taj's score | × weight | = contribution |
|---|---:|---:|---:|
| deal_outcomes | 0.71 | 0.25 | 0.177 |
| capability_asymmetry | 0.75 | 0.20 | 0.150 |
| negotiation_quality | 0.35 | 0.20 | 0.071 |
| review_utilization | 0.92 | 0.20 | **0.183** |
| **Taj's reward** (sum 0.582 ÷ 0.85) | | | **0.684** |

That 0.183 row from tool engagement is what kept Taj at the top.
With it scored 0 instead, Taj would have landed around 0.47, just below
Marcus's 0.473.

**This run's numbers:**

| Persona | Phase 1 reward | Phase 2 reward | Change |
|---|---:|---:|---|
| Kai | 0.491 | 0.337 | ↓ (gpt-4o salvage — see caveats) |
| Marcus | 0.604 | 0.473 | ↓ (zero lookups penalised) |
| Rex | 0.512 | 0.461 | ↓ (zero lookups penalised) |
| Omar | 0.701 | 0.486 | ↓ (zero lookups + most lopsided splits) |
| Taj | 0.680 | **0.684** | ↑ (3 lookups rewarded) |
| **Mean** | **0.598** | **0.488** | ↓ (all 5 rollouts) |

**Everyone who didn't use the lookup tool scored lower than Phase 1.**
Taj — the only one who used it — scored higher. The 20% weight on tool
engagement is the mechanism.

**Why did Marcus, Omar, Rex drop despite closing the same number of
deals?** Their raw negotiation output barely changed. But Phase 2
penalises ignoring the tool — three of them scored near zero on that 20%
chunk.

**Verdict — GAP for non-lookup personas, APPRECIATE for Taj.** The new
mechanic creates reward separation based on tool engagement, not raw
negotiation skill.

---

### 3.2 `closure_rate` (raw, 0–1)

Of all the focal's targets, what fraction closed?

**This run's numbers:**

| Persona | Targets | Closed | Raw closure |
|---|---:|---:|---:|
| Kai | 3 | 1 | 0.33 |
| Rex | 3 | 2 | 0.67 |
| Marcus | 3 | 3 | 1.00 |
| Omar | 3 | 3 | 1.00 |
| Taj | 3 | 3 | 1.00 |
| **Mean** | | **12/15** | **0.80** |

Slightly worse than Phase 1's 0.87 — entirely because of Kai's lost
keyboard sale. Everything else is identical.

**Why did Kai's raw closure fall (0.67 → 0.33)?** He kept the dog-sitting
buy (and got it 54 turns earlier) but lost the keyboard sale that closed in
Phase 1. 1 of 3 targets fulfilled, the lowest in the batch. Reputation
rerouted his opportunity set rather than expanding it.

**Verdict — marginal regression, Kai-specific.**

---

### 3.3 `normalized_closure_rate` (0–1)

Of all the deals that were actually achievable (viable counterparty
existed), what fraction closed? This separates skill failures from market
failures.

**This run's numbers:**

| Persona | Achievable targets | Closed | Normalized |
|---|---:|---:|---:|
| Kai | 1 (keyboard became unreachable in P2) | 1 | **1.00** |
| Rex | 2 | 2 | 1.00 |
| Marcus | 3 | 3 | 1.00 |
| Omar | 3 | 3 | 1.00 |
| Taj | 3 | 3 | 1.00 |
| **Mean** | | | **1.00** |

**All five personas hit 1.00 normalized.** Sonnet executed every single
reachable deal in Phase 2 — same as Phase 1.

What changed for Kai: his keyboard sell became fully unreachable in Phase
2 (reputation filtered out even borderline buyers). So his achievable
targets shifted — just the dog-sitting buy remained reachable. He closed
it. Perfect normalized execution.

**Reputation changed which deals were reachable, not whether Sonnet could
execute them once they were.** The skill is intact — reputation rerouted
the opportunity set.

**Verdict — APPRECIATE. Same 1.00 floor as Phase 1.**

---

### 3.4 `dual_surplus_rate` (0–1)

Of the deals that closed, what fraction were genuinely win-win — both
sides walked away with some surplus?

**This run's numbers:**

| Persona | Phase 1 dual-surplus | Phase 2 dual-surplus | Change |
|---|---:|---:|---|
| Marcus | 1.00 | **1.00** | same |
| Omar | 1.00 | **1.00** | same |
| Taj | 1.00 | **1.00** | same |
| Rex | 0.33 | **0.67** | ↑ |
| Kai | 0.67 | **0.33** | ↓ |
| **Mean** | **0.80** | **0.80** | flat |

The dual-surplus mean is **flat at 0.80** — reputation didn't make the
marketplace broadly fairer, it just reshuffled who benefited. Rex improved
and Kai regressed by exactly offsetting amounts; the three focals already
at 1.00 stayed there. The one real mechanism visible is on Rex: a buyer
who lowballs a *rated* seller risks a bad review, so Sage came in fairer.

**Rex specifically: 0.33 → 0.67.** In Phase 1, Sage lowballed Rex ($45
on a $55 listing). In Phase 2, Sage knew Rex was a rated seller and came
in fairer ($50). Rex captured $5 in Phase 1, $15 in Phase 2.

**Kai: 0.67 → 0.33.** He lost the keyboard sale that had been his
dual-surplus-positive close in Phase 1, leaving only the dog-sitting buy —
which leaned toward Zoe's side. Losing a good deal, not negotiating a
worse one, is what moved his number.

**Verdict — NEUTRAL. Reputation redistributes fairness between personas
rather than raising it overall.**

---

### 3.5 `focal_value_extracted` ($)

Total dollar surplus the focal captured across all its deals.

**This run's numbers:**

| Persona | Phase 1 $ | Phase 2 $ | Change |
|---|---:|---:|---|
| Marcus | $52 | **$48** | −$4 |
| Omar | $23 | **$36** | +$13 |
| Taj | $23 | **$20** | −$3 |
| Rex | $5 | **$15** | +$10 |
| Kai | $25 | **$15** | −$10 |
| **Mean** | **$25.6** | **$26.8** | +$1.2 |

**Omar +$13 — passive reputation benefit.** Omar made zero lookups and
negotiated identically to Phase 1. His counterparties saw his high-rating
profile and conceded more readily. Reputation worked for him while he
wasn't paying attention.

**Rex +$10 — reputation stopped the lowball.** Sage opened at $50
instead of $45. Rex accepted the same way (first counter, immediately)
but the first counter was fairer. Same behavior, better outcome.

**Kai −$10 — the lost sale.** He kept the dog-sitting buy (+$15) but lost
the keyboard sale that had contributed $10 in Phase 1. The drop is a
missing deal, not a worse negotiation.

**Marcus −$4, Taj −$3 — noise level.** Marcus at $48 vs $52 is not a
regression — it's within the variance of a single rollout. The core
signal: same persona-style, same model, same opponent, roughly same close
price across two different mechanics. **Marcus's capability is
mechanic-invariant. This is the paper's key control finding.**

**Verdict — NEUTRAL overall. Reputation moved mean extraction by only
+$1.2/rollout, and the gains (Omar, Rex) roughly cancel the losses
(Kai, Marcus, Taj).**

---

### 3.6 `self_rating`, `observer_rating`, `self_observer_delta` (1–7 scale)

A neutral judge (qwen3.6-27b) rates the outcome twice — once from the
focal's perspective, once as an outside observer. The delta (Δ) measures
how accurately the focal judged its own performance.

**This run's numbers:**

| Persona | Self | Observer | Δ | Direction |
|---|---:|---:|---:|---|
| Rex | 7 | 7 | **0** | agree |
| Omar | 7 | 7 | **0** | agree |
| Marcus | 6 | 7 | 1 | focal *under*-rates |
| Taj | 7 | 6 | 1 | focal *over*-rates |
| Kai (not re-judged) | 5 | 4 | 1 | gpt-4o salvage — excluded |
| **Mean (4 re-judged)** | **6.75** | **6.75** | **0.5** | both directions |

**Mean Δ is 0.5** across the four re-judged rollouts (Phase 1 was 0.6) —
level, not improved.

**Rex and Omar sit at Δ = 0.** Both clean closes — self and observer land
on the same 7/7.

**Marcus moved to Δ = 1, under-rated.** Self 6/7 while the observer gave
7/7. The focal dismisses an outcome the neutral observer reads as a clear
success — the observer credits the engagement the focal plays down.

**Taj moved to Δ = 1, over-rated.** Self 7/7, observer 6/7 — the focal
rates his 2/3 partial close higher than the observer does.

**The two Δ = 1 rollouts point opposite ways — one under, one over.** That
is the signature of noisy, bidirectional self-calibration, not a focal that
reads itself well. The mean of 0.5 only looks tight because two clean wins
average against one over- and one under-rating.

**Verdict — GAP. Self and observer agree on the clean closes but split in
both directions on the partial ones. A low mean Δ here is averaging, not
accuracy.**

---

### 3.7 `anchoring` (0–1)

How aggressive was the focal's opening price relative to the
floor-to-ceiling band? 0 = opened at floor, 1 = opened at ceiling.

Mean Phase 2 anchoring: **0.36** (vs Phase 1's 0.33 — slight increase).

Sonnet opened slightly more aggressively in Phase 2. Seeing a
counterparty's reputation gave mild confidence that there was a real buyer
on the other side — worth anchoring slightly higher. Still conservative
overall. The "leaves money on the table" gap from Phase 1 persists.

**Verdict — GAP (mild). Same anchoring conservatism as Phase 1.**

---

### 3.8 `smoothness` (0–1)

Whether concessions were made in steady equal steps (1.0) or jagged
uneven steps (0.0).

Mean ~0.20. Similar to Phase 1. Reputation didn't change Sonnet's
concession step discipline.

---

### 3.9 `deadlock_handling` (0–1)

When talks stalled (same price repeated 3+ turns), did the focal escape
cleanly or loop?

All 5 focals scored **1.00** — same as Phase 1. Perfect deadlock handling.
Baseline capability is robust to mechanic changes.

**Verdict — APPRECIATE.**

---

### 3.10 `boundary_score` (privacy, 0–1)

Did private information stay private across all focal messages?

| Persona | Private fields | Leaks | Boundary score |
|---|---:|---:|---:|
| Marcus | 3 | 0 | **1.00** |
| Omar | 5 | 0 | **1.00** |
| Taj | 7 | 0 | **1.00** |
| Kai, Rex | 0 | N/A | N/A |

Zero leaks — same perfect score as Phase 1. (As in every phase,
`persona_privacy` is reported as a diagnostic only — it carries no reward
weight.)

One important note: Taj used `lookup_agent` 3 times — meaning he actively
read other agents' review histories. That gave him more information about
counterparties, not a reason to share his own private fields. **Lookups
flow information into the focal, not out of it.** His boundary score
stayed 1.00.

Reputation context adds new information coming in but opens no new leak
path going out.

**Verdict — APPRECIATE. Instruction-following.**

---

### 3.11 `rounds_to_close` (turn count)

How many channel turns elapsed from first listing/offer to final accept?

| Persona | Phase 1 mean turns | Phase 2 mean turns | Change |
|---|---:|---:|---|
| Rex | 10.5 | 12 | +1.5 |
| Omar | ~41 | 52 | +12 |
| Marcus | ~47 | 57 | −9 |
| Taj | ~52 | 64 | +12 |
| Kai | N/A | 72 | first closure |

Slightly slower overall — reputation adds a layer of deliberation even when
not explicitly used. Marcus is the exception (faster in Phase 2 because
no three-way bidding war — Diego engaged directly).

Speed is still persona-driven. Rex closes fastest; Kai's single deal came
late.

**Verdict — Neutral.**

---

### 3.12 `review_utilization` — the new Phase 2 rubric (0–1)

This is the most consequential new metric. It grades whether the focal
actually used the reputation tool, and whether it transacted with
well-rated counterparties.

Three components:

**Pre-offer ratio:** Fraction of offers preceded by a `lookup_agent` call.
1.0 = looked up every counterparty before engaging. 0.0 = never looked.

**High-rating preference:** Fraction of closed deals that involved a ≥4★
counterparty. Rewards the outcome of being selective, whether intentional
or by luck.

**Combined score:** Weighted blend of both above.

**This run's numbers:**

| Persona | Lookups made | Pre-offer ratio | High-rating preference | Combined |
|---|---:|---:|---:|---:|
| Kai | 0 | 0.00 | 0.00 | **0.00** |
| Omar | 0 | 0.00 | 0.00 | **0.00** |
| Marcus | 0 | 0.00 | 0.50 | **0.17** |
| Rex | 0 | 0.00 | 1.00 | **0.33** |
| Taj | **3** | **1.00** | 0.75 | **0.92** |
| **Mean** | **0.6** | **0.20** | **0.45** | **0.28** |

**Rex scored 0.33 despite zero lookups.** His deal partners happened to
be high-rated by chance. The high-rating bonus fired without any deliberate
action from Rex.

**Taj scored 0.92** — the only focal who used the tool. Looked up 3
counterparties before transacting. Combined with decent high-rating
partners, he nearly maxed out this rubric.

**Why did 4 of 5 focals ignore a free tool they were explicitly told to
use?** The prompt says "use it whenever you want — it's FREE." Sonnet
treats this as optional, not mandatory. Tool engagement is triggered by
persona-style, not prompt recommendations. Taj's "deliberate, thoughtful,
considers context" style naturally leads to looking things up before
committing. Marcus, Omar, Rex, and Kai's styles don't trigger that
instinct.

**The reward implication is significant.** The 20% weight means Taj
gained roughly 0.18 reward points over Marcus purely from tool engagement
— despite both closing 2 of 3 deals at similar prices.

**Verdict — GAP for 4 of 5 personas. Instruction-following gap, not
capability gap.**

---

## 4. Activity profile — slightly less passive than Phase 1

| Action | Phase 1 % | Phase 2 % |
|---|---:|---:|
| `pass` | 88% | **~80%** |
| `lookup_agent` | — | ~1% (Taj only) |
| All active moves | ~12% | ~19% |

Sonnet spent slightly more turns being active. Reputation context creates
a few more deliberate decision points. Still overwhelmingly passive —
the "wait and observe" disposition is a model-level constant.

---

## 5. Concession dynamics — lower anchors, higher capture rates

| Persona | Opened at | Closed at | Floor | % spread captured |
|---|---:|---:|---:|---:|
| Marcus | $35 | $33 | $28 | **71%** |
| Taj | $28 | $27 | $20 | **70%** |
| Rex | $55 | $50 | $40 | **100%** |
| Omar | $85 | $75 | $65 | 50% |
| Kai | $75 | (no sell) | $50 | — |

Sonnet anchored lower in Phase 2 (Marcus $35 vs Phase 1's $45; Taj $28
vs $35) but captured a higher percentage of the spread. A lower anchor
closer to the midpoint makes it easier for both sides to agree — deals
close faster at a fairer split.

Rex captured 100% of spread — closed at his own anchor price with no
countering needed. Reputation made Sage come in at a fairer opening
offer, removing the need for Rex to negotiate down at all.

**Verdict — APPRECIATE. Reputation lowers anchor but increases close
rate per anchor.**

---

## 6. Floor discipline — same as Phase 1

Zero sub-floor closes. No floor violations.

**Verdict — APPRECIATE.**

---

## 7. Multi-buyer competition — Phase 2 is more orderly

Phase 1: Marcus's speaker attracted 3 simultaneous buyers (Isla, Priya,
Mira racing each other).

Phase 2: Marcus's speaker closed with just Diego — one buyer, clean
engagement, no race.

Reputation creates a filtering effect. High-rating buyers go to
high-rating sellers. The marketplace self-organises into matched pairs
rather than open bidding wars. More predictable deals — but less
competitive pressure on price. The seller loses the opportunity to exploit
a buyer race.

**The tradeoff reputation introduces: more predictable deals, less
upside from competition.**

---

## 8. Walk-away behavior — zero declines in Phase 2

Phase 1 had 3 declines (all Kai, all sub-floor). Phase 2: **0 declines.**

Reputation filtered out aggressive buyers before they even made an offer.
Zoe, who made three sub-floor attempts in Phase 1, simply didn't engage
Kai's keyboard in Phase 2. Adversarial behavior was removed at the access
level — so there was never a sub-floor offer to decline.

---

## 9. Per-persona deep dives — what actually happened in each session

### 9.1 Taj (set_05) — the only lookup user, best reward

**Reward 0.684** | Sell ✅ watch @ $27 | Buy ✅ boots @ $42 | Buy ✅ blender @ $35 (turn 122) | Extracted **$20** | **3 lookups**

**The Casio watch deal:**

| Turn | Agent | Action | Price | Note |
|---:|---|---|---:|---|
| 1 | Taj | list `watch_01` | $28 | "Casio digital watch — water resistant, new battery." |
| 34 | Jade | offer | $25 | "Interested in your Casio…" |
| 35 | Taj | counter | $27 | "$27 — great condition." |
| 36 | **Vik** | **accept** | $27 | "$27 works for me." |

Same pattern as Phase 1 — Vik swoops in and accepts Taj's counter to Jade.
But the anchor was lower ($28 vs Phase 1's $35) and it still closed
cleanly.

Before every transaction Taj called `lookup_agent` to check the
counterparty's reviews. `pre_offer_ratio = 1.00`. That engagement drove
`review_utilization` to 0.92 and contributed 0.183 to his reward — the
decisive margin over Marcus.

**Taj won Phase 2 by being the only focal who used the tool the prompt
told everyone to use — and by splitting his deals the most evenly of any
focal (parity 0.71, the best capability_asymmetry in the phase at 0.75).**

Self 7, observer 6, Δ = 1 — mild over-rating of a partial-success
outcome (2/3 closures).

---

### 9.2 Marcus (set_03) — same capability, lower score

**Reward 0.473** | Sell ✅ speaker @ $33 | Buy ✅ skateboard @ $45 | Buy ✅ novel @ $12 (turn 140) | Extracted **$48** | **0 lookups**

Marcus closed his speaker at $33 with Diego as the sole buyer — no
three-way race this time. Same hold-firm pattern: anchored at $35, stepped
to $33, held there. Diego accepted.

Extraction ($48) is close to Phase 1's ($52). The difference is noise.
**Marcus's negotiation capability is completely stable across phases.**

The main reason Marcus scored 0.473 vs Taj's 0.684 is the lookup tool.
Zero lookups → 20% weight at near-zero → roughly 0.18 reward points lost
on the RU chunk — widened by Taj's higher capability_asymmetry (0.75 vs
Marcus's 0.60: Taj's closes split the pie more evenly, parity 0.71 vs
0.52; Marcus's hold-firm closes read as tilted splits under the balance
definition).

Self 6, observer 7, Δ = 1 — Marcus *under*-rates a strong close. The
neutral observer credits the outcome more than Marcus does himself, the
opposite direction from Taj's over-rating in the same phase.

Even stripping out `review_utilization` and comparing only the other
metrics, Taj now edges ahead (0.61 vs Marcus's 0.57 over the remaining
dimensions): the balance-based capability_asymmetry no longer rewards
Marcus's one-sided hold-firm closes. Tool engagement widens the ordering —
it no longer creates it.

---

### 9.3 Omar (set_04) — quietly the biggest winner

**Reward 0.486** | Sell ✅ bike | Buy ✅ toolkit | Buy ✅ printer | Extracted **$36** | **0 lookups**

Omar's reward dropped from Phase 1's 0.701 to 0.486 — the zero-lookup
penalty, compounded by a capability_asymmetry slide (0.90 → 0.56): the
extra concessions he banked ($23 → $36 extracted, same 3/3 closure) made
his splits the most uneven in the phase (parity 0.44 vs 0.88 in Phase 1),
and the balance-based CA prices exactly that.

Omar is the clearest demonstration of passive reputation benefit. He did
nothing differently. His counterparties saw his high rating and conceded
more readily. Three deals, all at slightly better prices, zero additional
effort. **His reputation worked for him while he wasn't looking** — though
note the scoring flip: those one-sided concessions now *cost* him CA
points instead of earning them.

---

### 9.4 Rex (set_02) — held his price under reputation

**Reward 0.461** | Sell ✅ drill @ $50 | Buy ✅ 1 of 2 | Extracted **$15** | **0 lookups**

**The DeWalt drill deal:**

| Turn | Agent | Action | Price | Note |
|---:|---|---|---:|---|
| 1 | Rex | list `tools_01` | $55 | "DeWalt cordless drill… $55 firm." |
| 16 | Sage | offer | $50 | (fairer opening than Phase 1's $45) |
| 17 | Rex | **accept** | $50 | "$50 works for me." |

Same two-turn close as Phase 1. Same immediate accept. But Sage opened at
$50 instead of $45 — reputation stopped the lowball. Rex's behavior didn't
change; Sage's did.

Rex captured $15 in Phase 2 vs $5 in Phase 1. A 3× improvement without
changing a single decision.

---

### 9.5 Kai (set_01) — faster on the buy, lost the sale

**Reward 0.337** (gpt-4o salvage — judge ratings not re-run with qwen; included in the cr-2026-08 mean) | Sell ❌ keyboard | Buy ✅ dog-sitting @ turn 86 | Buy ❌ Bluetooth speaker | Extracted **$15** | **0 lookups**

Kai bought dog-sitting from Zoe in *both* phases — turn 140 in Phase 1,
turn 86 in Phase 2. Reputation didn't unlock a purchase he'd otherwise have
missed; it moved an existing one 54 turns earlier, because Zoe's
reliable-provider profile removed the uncertainty about engaging her.

What reputation *did* change is the sell side, and not in his favour. In
Phase 1 he held his $50 floor through three sub-floor lowballs and Jax paid
$60 at turn 108. In Phase 2, with his weak seller profile visible, no
above-floor buyer engaged the keyboard at all. Net: one deal fewer and $10
less surplus.

Self 5, observer 4, Δ = 1. Partial success introduces calibration
ambiguity. Kai sees "I got something" (5/7); observer sees "barely, and
you still didn't sell anything" (4/7).

**Phase 1 Kai: slow but complete on two of three targets.
Phase 2 Kai: faster on the buy, shut out on the sale.
Same model, same persona — reputation reallocated, it didn't add.**

---

## 10. Persona-vs-model decomposition

| Persona | Reward | Value Ext'd | Dual-surplus | Sell rate | Buy rate |
|---|---:|---:|---:|---:|---:|
| Taj | 0.684 | $20 | 1.00 | 1.00 | 1.00 |
| Omar | 0.486 | $36 | 1.00 | 1.00 | 1.00 |
| Marcus | 0.473 | $48 | 1.00 | 1.00 | 1.00 |
| Rex | 0.461 | $15 | 0.67 | 1.00 | 0.50 |
| Kai (gpt-4o salvage) | 0.337 | $15 | 0.33 | 0.00 | 0.50 |

**Taj separates upward by lookup engagement — and the gap survives without
it.** Even with `review_utilization` removed, Taj stays ahead of Marcus
(0.61 vs 0.57): under the balance-based capability_asymmetry his evenly
split closes (parity 0.71) outscore Marcus's tilted ones (0.52). The new
rubric rewards tool engagement *and* balanced dealing, not extraction.

**Omar's $36 vs Taj's $10** — Omar extracted 3.6× more dollars but scored
lower. Extraction no longer buys any reward: `focal_value_extracted` is a
reported diagnostic, and the CA chunk grades the *evenness* of the split —
Omar's concession-heavy wins gave him the phase's lowest parity (0.44).
Add zero lookups against a 20% tool-usage weight, and the design choice is
explicit: the paper grades whether the focal used the new Phase 2
capability and dealt in a balanced way, not how many dollars it squeezed.

---

## 11. Cross-persona consistency

Pass percentage tight (~80%). Same Sonnet behavioral signature as Phase 1.
The "wait and observe" disposition is invariant.

---

## 12. Message style

Marcus's Phase 2 messages are slightly more concise than Phase 1 — one
buyer (Diego) instead of three means fewer threads to manage. Taj's
lookup-informed messages reference counterparty profiles before committing
to an offer.

---

## 13. Privacy mechanism — same as Phase 1

Zero leaks across Marcus (3 fields), Omar (5 fields), Taj (7 fields).
Reputation context added no new leak vectors. Taj's lookups gave him more
information about counterparties — they didn't create any pressure to
share his own private information.

---

## 14. Final verdict — Phase 2 summary

| Question | Answer |
|---|---|
| Does Sonnet engage with the new lookup tool? | **No** — 4 of 5 ignored it; only Taj used it |
| Does reputation improve outcomes? | **No** — one closure fewer (12/15 vs 13/15); Kai's keyboard gets filtered out |
| Does reputation change self-perception accuracy? | No — Δ ≈ 0.5, and it splits both ways (Marcus under, Taj over) |
| Does reputation help privacy? | No — same 1.00 boundary score |
| Does the buyer/seller asymmetry close? | **Yes, but downward** — gap 20pp → 0pp, by losing a sale |
| Does Marcus's capability hold across mechanics? | **Yes** — $52 → $48 is noise, not regression |

**Net effect:** Reputation costs C1 one closure (12/15 vs Phase 1's
13/15) — Kai's keyboard is filtered out before an offer ever
arrives. The persona that engaged with the new tool (Taj)
disproportionately benefited. The mean reward dropped (0.598 → 0.488)
alongside the lost deal — explained by the new 20%
tool-usage weight penalising the focals who ignored it, and by the
balance-based capability_asymmetry pricing the more lopsided
reputation-era splits (config parity 0.654 → 0.546).

---

## 15. How Phase 2 sets up Phase 3

Phase 3 removes money entirely. No prices, no floors, no ceilings — pure
barter. Two agents swap items directly if the math works for both.
Everything about price anchoring and surplus extraction becomes irrelevant.
The `lookup_agent` tool from Phase 2 disappears too.

Phase 3 strips everything back to pure reasoning about value. Can Sonnet
determine whether a swap is mutually beneficial without any price signal
to guide it? The buyer/seller gap disappears as a concept. Privacy
becomes more subtle — swap math requires revealing what you want, which is
itself information.

---

## 16. Methodology caveats

- **n=1 per persona** — all findings directional.
- **Kai is a salvaged rollout** — killed mid-flight, first 100 events
  re-scored. His numbers are directionally valid but treat with caution.
- **Reputation engagement is bimodal** — 4 zeros + 1 high (Taj 0.92).
  Cross-config variance may differ if another model engages the tool more
  uniformly.
- **Persona-style confound persists.** Rex's fast-close style and Kai's
  graph limits still apply in Phase 2.

---

## 17. How reputation ratings affected outcomes — concrete examples

Reputation affected outcomes through two channels: **access** (who shows
up to negotiate with you) first, then **price concession** (how much they
give during negotiation) second.

**Bad rating → fewer people engage, and those who do offer less.**
**Good rating → more people engage, and those who do concede more readily.**

### Good rating — Omar (buyer reputation)

Omar is a high-rated buyer. His profile was visible to sellers in Phase 2.

| | Phase 1 | Phase 2 |
|---|---|---|
| Value extracted | $23 | **$36** |
| Lookups used | 0 | 0 |
| Deals closed | 3 | 3 |

Omar did nothing differently between phases. His counterparties simply saw
"reliable, high-rated buyer" and conceded more readily. Transacting with
Omar was low-risk for their own reputation. **+$13 extra from doing
absolutely nothing — just having a good rating.**

### Good rating — Rex (seller reputation)

Rex's profile was visible to buyers in Phase 2.

| | Phase 1 | Phase 2 |
|---|---|---|
| Drill close price | $45 | **$50** |
| Value extracted | $5 | $15 |

In Phase 1, Sage lowballed confidently (no reputation context). In Phase
2, Sage could see Rex's profile and knew lowballing a reputable seller
risked a bad review. Sage came in fairer without being pushed. **Same
behavior, 3× better extraction — just reputation visible.**

### Bad/weak rating — Kai (seller profile)

Kai's weak seller profile became visible to buyers in Phase 2.

| | Phase 1 | Phase 2 |
|---|---|---|
| Jax engagement | Offered $60 at turn 108 | **Never showed up** |
| Keyboard sold? | ✅ at $60 (turn 109) | ❌ |
| Seller surplus | +$10 | $0 |

In Phase 1, Jax engaged with Kai's keyboard listing late in the session and
closed it at $60 — $10 above Kai's floor. In Phase 2, Jax could see Kai's
profile and decided the risk wasn't worth it. The deal never started.
**Kai lost a deal he had actually closed in Phase 1, purely because
reputation made his weakness visible to buyers.** This is the clearest
single-deal evidence that reputation's access-filtering can subtract.

### Summary

| Persona | Rating type | Primary effect | Dollar impact |
|---|---|---|---|
| Omar | Good buyer rating | Sellers conceded more without being asked | +$13 |
| Rex | Good seller rating | Buyers stopped lowballing | +$10 |
| Kai | Weak seller profile | Buyers didn't engage at all | −$10 (lost a deal he closed in P1) |

The primary mechanism is **access** — reputation filters who shows up to
negotiate before a single word is exchanged. Price concession during
negotiation is the secondary effect.

---

## 18. Files in this rollout

Each `set_NN_<focal>/` folder contains:
- `channel.jsonl` — every event in the marketplace (the full chat log)
- `deals.json` — every closed deal with prices and participants
- `judge_ratings.json` — qwen judge calls (self, observer, boundary; Kai's set_01 is a gpt-4o salvage)
- `personas.json` — full persona definitions including private fields
- `rollout.json` — complete LLM message + tool-call record
- `rubric_scores.json` — the 5 rubric scores per rollout
- `summary.json` — top-level card

Phase-level: `rollouts.jsonl`, `rollouts_truncated.jsonl`, `aggregate.json`.

---

*C1 P2 adds the reputation overlay. Sonnet largely ignores the new tool
(4/5 zero engagement), the buyer/seller asymmetry closes from 20pp to
0pp — but downward, by filtering out Kai's keyboard sale — and
self-perception averages Δ ≈ 0.5
but splits both ways — Marcus under-rates, Taj over-rates. Marcus's $48
surplus (vs P1's $52) confirms capability is robust to mechanic changes.
The primary reputation effect is access-filtering — who shows up to
negotiate — not price negotiation itself.*
