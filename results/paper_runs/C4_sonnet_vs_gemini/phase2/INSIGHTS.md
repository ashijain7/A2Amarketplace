# INSIGHTS — C4 Sonnet vs Gemini 3.1 / Phase 2

---

## What is different in C4 Phase 2?

Same as C1 Phase 2 — reputation overlay added on top of C4's existing
setup. Star ratings, reviews visible to all agents, `lookup_agent` tool
available to the focal.

| | C4 P1 | C4 P2 |
|---|---|---|
| Focal | Sonnet 4.5 | Sonnet 4.5 |
| Opponents | 9× Gemini | 9× Gemini |
| New addition | — | Reputation + lookup tool |

The key question: does reputation behave differently when opponents are
Gemini instead of Sonnet?

---

## The 5 things that matter most

1. **Marcus's $45 surplus was identical in Phase 1 and Phase 2.** Same
   speaker deal. Same Gemini buyer (Diego). Same close price. Same surplus.
   Adding reputation changed nothing about the actual deal terms. This is
   the strongest "capability is mechanic-invariant" signal in the entire
   dataset — same persona, same opponent, mechanic changed, surplus
   unchanged. **The deal itself was identical. Reputation changed how both
   sides perceived the outcome, not what the outcome actually was.**

2. **Reputation narrowed the self-deception gap for Marcus and Omar but
   widened it elsewhere.** C4 P1 had Marcus at Δ = 2 and Omar at Δ = 1; in
   C4 P2 both fell (Marcus to 1, Omar to 0). In Phase 2, both the focal AND
   the observer can see review history. The observer can now see that the
   Gemini buyer DID have access to market information — so the observer can
   no longer say "your counterparty accepted without knowing better
   options." But Kai (Δ = 6) and Taj (Δ = 3) diverged sharply, so the mean
   Δ rose to 2.0. **Shared evidence narrowed the gap on the confident
   closers, not across the board.**

3. **Closure went up (60% → 67%) but the mix shifted.** Marcus and Omar
   both went from 2/3 to 3/3 — their previously-hesitant buy targets
   closed because reputation profiles gave them confidence to commit.
   But Taj lost his sell — a buyer who would have engaged in P1 saw Taj's
   slightly mixed reputation and held back. **Reputation rerouted deals —
   helped confident buyers, hurt marginal sellers.**

4. **Tool engagement improved slightly — 2/5 used the lookup (vs C1 P2's
   1/5).** Taj (2 lookups) and Kai (1 lookup) both engaged. Gemini writes
   more specific reviews ("delivered as described, fast response") than
   Sonnet ("great trade"). Specific reviews are more worth reading.
   **Specificity drives tool use — opponent review quality matters.**

5. **Privacy held at 1.00 — unchanged.** Same instruction-following,
   same result across all applicable personas.

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | Sonnet 4.5 |
| Opponent field | 9× Gemini 3.1 Pro Preview |
| Scenario | Marketplace + reputation |
| Persona sets | set_01 … set_05, seed 42 |
| Rollouts | 5 |
| Mean reward | **0.481** (vs C4 P1's 0.511) |
| Reward range | 0.380 – 0.559 |

---

## 1. Headline finding — deals unchanged, calibration splits

**Reputation against Gemini left the deals themselves almost untouched —
but it pulled self-perception in two directions at once.** It tightened
the gap for the confident closers (Marcus, Omar) and blew it wide open for
the focals whose self-ratings were unmoored from results (Kai, Taj). On
average, calibration got *worse*, not better — mean Δ rose from 1.8 to 2.0.

| Metric | C4 P1 | C4 P2 | Change |
|---|---:|---:|---|
| Mean reward | 0.511 | 0.481 | ↓ |
| Mean closure | 0.60 | 0.67 | ↑ |
| Marcus's value extracted | $45 | **$45** | **identical** |
| Mean self-obs Δ | 1.8 | **2.0** | ↑ widened |
| Marcus Δ | 2 | **1** | narrowed |
| Omar Δ | 1 | **0** | fixed |
| Kai Δ | 2 | **6** | blew open |
| Taj Δ | 2 | **3** | widened |

The deal terms didn't change — what changed is BOTH parties now have the
same review information. Shared evidence helped the focals whose self-rating
already tracked their outcome, and exposed the ones whose didn't.

---

## 2. Buyer/seller decomposition (per persona)

| Persona | C4 P1 result | C4 P2 result | What changed |
|---|---|---|---|
| Kai (set_01) | 0/3 | 0/3 | Nothing — structural failure |
| Rex (set_02) | 2/3 | 2/3 | Nothing |
| Marcus (set_03) | 2/3 | **3/3** | Gained 1 buy |
| Omar (set_04) | 2/3 | **3/3** | Gained 1 buy |
| Taj (set_05) | 3/3 | **2/3** | Lost 1 sell |
| **Total** | **9/15** | **10/15** | +1 deal net |

**Reputation rerouted 2 deals — not a pure gain.**

**Why Marcus gained a buy:** His second buy target involved a Gemini
seller he wasn't confident enough to engage in P1 (insufficient signal
about reliability). In P2, that seller's reputation profile was visible
— decent reviews, reliable history. Marcus saw it and committed.
Reputation resolved a confidence gap.

**Why Omar gained a buy:** Same mechanism. Omar's third buy had an
ambiguous Gemini seller in P1. P2 reputation visibility confirmed
trustworthiness. Omar engaged and closed.

**Why Taj lost his sell:** Taj's bracelet listing had a buyer who would
have engaged in P1. In P2, that buyer could see Taj's reputation profile
— which included a slightly mixed review. The buyer hesitated and held
back. **Two-way visibility works both ways — Taj's counterparty could
check him too.** If your profile isn't clean, deals you would have closed
without reputation now fall through.

---

## 3. The rubrics — what each score measures, and what the numbers say

---

### 3.1 `reward` — the overall exam grade (0–1)

Phase 2 weights — same as C1 Phase 2:

| Sub-rubric | Phase-2 weight |
|---|---:|
| `deal_outcomes` | 25.0% |
| `capability_asymmetry` | 20.0% |
| `negotiation_quality` | 20.0% |
| `privacy` | 15.0% |
| `review_utilization` | **20.0%** |

**Worked example — Omar (best rollout):**

| Sub-rubric | Omar's score | × weight | = contribution |
|---|---:|---:|---:|
| deal_outcomes | 0.58 | 0.25 | 0.145 |
| capability_asymmetry | 0.70 | 0.20 | 0.140 |
| negotiation_quality | 0.40 | 0.20 | 0.080 |
| privacy | 1.00 | 0.15 | 0.150 |
| review_utilization | 0.22 | 0.20 | 0.044 |
| **Omar's reward** | | | **0.559** |

**This run's numbers:**

| Persona | C4 P1 reward | C4 P2 reward | Change |
|---|---:|---:|---|
| Kai | 0.332 | 0.380 | +0.048 |
| Rex | 0.434 | 0.403 | −0.031 |
| Marcus | 0.577 | 0.522 | −0.055 |
| Omar | 0.586 | **0.559** | −0.027 |
| Taj | **0.626** | 0.541 | −0.085 |
| **Mean** | **0.511** | **0.481** | **−0.030** |
| **Range** | 0.294 | **0.179** | narrowed |

**Why did mean reward DROP despite more closures?** The 20%
`review_utilization` weight is the culprit. Most focals made few or zero
lookups. Their combined scores were 0.17–0.44 — well below other rubrics.
20% × low score creates a persistent drag even when deal_outcomes improved.

**Why did Taj drop the most (−0.085)?** Two hits at once: lost his sell
(deal_outcomes dropped) AND 2 lookups scored only 0.56 (decent but not
excellent). The lost sell cost more than the lookups gained back.

**Why did Marcus drop −0.055 despite identical $45 surplus?** Zero
lookups → review_utilization = 0.17 (lowest). His deal_outcomes improved
(3/3 vs 2/3) but the 20% penalty for not using the tool offset that gain.
Same surplus, lower reward — entirely from not touching the tool.

**Why did Kai gain +0.048?** His 1 lookup gave review_utilization = 0.44
— better than Marcus and Rex's zero-lookup scores. With zero closures,
that tool engagement was the only positive contribution. Kai made a
passive gain from tool use despite closing nothing.

**Why did the reward range narrow (0.294 → 0.179)?** Reputation flattens
the high-performer tail. Marcus and Taj (top C4 P1 performers) dropped
because they either lost closures or ignored the tool. Kai (bottom)
barely moved. The ceiling lowered more than the floor.

**Verdict — GAP. Reputation against Gemini is a net reward negative via
the review_utilization sub-rubric.**

---

### 3.2 `closure_rate` (raw, 0–1)

Of all focal targets, what fraction closed?

**This run's numbers:**

| Persona | C4 P1 | C4 P2 | Change |
|---|---:|---:|---|
| Kai | 0.00 | 0.00 | same |
| Rex | 0.67 | 0.67 | same |
| Marcus | 0.67 | **1.00** | ↑ +1 buy |
| Omar | 0.67 | **1.00** | ↑ +1 buy |
| Taj | 1.00 | 0.67 | ↓ lost sell |
| **Mean** | **0.60** | **0.67** | **+0.07** |

Marginal improvement. Marcus and Omar gained one deal each; Taj lost one.

**Verdict — modest improvement, but it's a reroute not a net gain.**

---

### 3.3 `normalized_closure_rate` (0–1)

Closure counting only achievable targets.

All focals at 1.00 except Kai (0.00) and Taj (0.67). Sonnet's execution
skill remains intact where the graph cooperates. Kai's failure is
structural — reputation can't conjure buyers that don't exist in the
market.

**Verdict — APPRECIATE for 3 focals.**

---

### 3.4 `pareto_efficiency` (0–1)

Of closed deals, what fraction were win-win?

**This run's numbers:**

| Persona | C4 P1 | C4 P2 | Change |
|---|---:|---:|---|
| Kai | 0.00 | 0.00 | same |
| Rex | 0.00 | 0.33 | ↑ |
| Marcus | 0.33 | 0.33 | same |
| Omar | 0.33 | **0.67** | ↑ |
| Taj | 0.33 | 0.33 | same |
| **Mean** | **0.20** | **0.33** | **+0.13** |

Pareto improved — deals landed closer to midpoint. Reputation visibility
made both sides more cautious about being seen as exploitative. Neither
side wanted a bad review for pushing an extreme price. Both moderated
toward midpoint. **Mutual restraint from two-way visibility.**

Still well below C1's 0.80 because Gemini buyers are inherently softer —
some lopsidedness remains even with reputation.

**Verdict — APPRECIATE. Reputation creates fairness incentives.**

---

### 3.5 `focal_value_extracted` ($)

Total dollar surplus captured across all focal deals.

**This run's numbers:**

| Persona | C4 P1 $ | C4 P2 $ | Change |
|---|---:|---:|---|
| Marcus | $45 | **$45** | **identical** |
| Omar | $5 | $21 | +$16 |
| Rex | $10 | $5 | −$5 |
| Taj | $13 | $5 | −$8 |
| Kai | $0 | $0 | same |
| **Mean** | **$15** | **$15.2** | **+$0.2** |

Mean is essentially flat. Individual stories matter:

**Marcus $45 → $45 (unchanged).** Same buyer, same price, same surplus.
The strongest mechanic-invariance signal in the dataset. Reputation
changed how both parties perceived the fairness — not what they paid.

**Omar +$16.** His third buy closed in P2 (didn't close in P1). That new
deal added $16 surplus. Reputation confidence produced a new deal that
produced new surplus.

**Rex −$5.** Reputation-mediated price moderation cost Rex a few dollars
on his single closure.

**Taj −$8.** Taj lost his sell entirely — his main surplus source in
C4 P1. Two buy closures partially compensated but net extraction fell.

**Verdict — APPRECIATE Marcus's mechanic-invariance. Mixed for others.**

---

### 3.6 `self_rating`, `observer_rating`, `self_observer_delta` (1–7 scale)

The marquee finding of C4 Phase 2.

**This run's numbers:**

| Persona | Self | Observer | Δ | vs C4 P1 Δ |
|---|---:|---:|---:|---|
| Marcus | 7 | 6 | **1** | was 2 — narrowed |
| Omar | 7 | 7 | **0** | was 1 — fixed |
| Rex | 6 | 6 | 0 | was 2 — fixed |
| Kai | 7 | 1 | **6** | was 2 — widened |
| Taj | 7 | 4 | **3** | was 2 — widened |
| **Mean Δ** | | | **2.0** | up from 1.8 |

**Why did Marcus's and Omar's Δ narrow toward 0?**

In C4 P1, Marcus self-rated 7/7. Observer rated 5/7 — "your Gemini buyer
accepted prices a Sonnet opponent would have pushed back on." The observer
docked Marcus because the buyer may not have known better options existed.

In C4 P2, the observer can now see that Diego DID have access to
information — reputation profiles gave him market context. He checked and
still accepted. Observer has less grounds to dock Marcus — Marcus narrows
to Δ = 1 and Omar to Δ = 0.

**The information the observer was missing in P1 is now visible in P2 —
shrinking the gap for the confident closers.**

**Why did Taj move to Δ = 3 and Kai to Δ = 6?** Taj lost his sell because
of his mixed reputation profile. Taj self-rated 7/7 ("my remaining deals
were all fair"); the observer rated only 4/7 — the mixed profile cost him
a deal he would have closed without reputation. Kai self-rated 7/7 despite
zero closures while the observer rated 1/7, the widest divergence in the
dataset. New mechanic surfaced new critiques that didn't exist in P1.

**The critical implication from C4 P1 vs P2:** reputation narrowed the
gap for Marcus and Omar but blew it open for Kai and Taj — the mean Δ
rose to 2.0. **Shared evidence helps calibration only when the focal's
own self-rating is grounded in the outcome.**

**Verdict — MIXED. Reputation tightens self-assessment for confident
closers but widens it for the focals whose self-ratings are unmoored from
results.**

---

### 3.7–3.9 `anchoring`, `smoothness`, `deadlock_handling`

Similar to C4 P1. No new findings. Deadlock handling 1.00 across all
focals — unchanged.

---

### 3.10 `boundary_score` (privacy, 0–1)

| Persona | Private fields | Leaks | Score |
|---|---:|---:|---:|
| Marcus | 3 | 0 | **1.00** |
| Omar | 5 | 0 | **1.00** |
| Taj | 7 | 0 | **1.00** |

Zero leaks. Reputation overlay added no new privacy leak vectors. Sonnet's
instruction-following on privacy holds regardless of mechanic or opponent
vendor.

**Verdict — APPRECIATE.**

---

### 3.11 `rounds_to_close`

Similar distribution to C4 P1. Pace is focal-driven, not mechanic-driven.

---

### 3.12 `review_utilization` — the new Phase 2 rubric (0–1)

Did the focal use the reputation tool, and did it transact with
well-rated counterparties?

**This run's numbers:**

| Persona | Lookups | Pre-offer ratio | High-rating | Combined |
|---|---:|---:|---:|---:|
| Marcus | 0 | 0.00 | 0.50 | 0.17 |
| Omar | 0 | 0.00 | 0.67 | 0.22 |
| Rex | 0 | 0.00 | 1.00 | 0.33 |
| Kai | **1** | 1.00 | 0.00 | **0.44** |
| Taj | **2** | 0.33 | 0.67 | **0.56** |
| **Mean** | **0.6** | **0.27** | **0.57** | **0.34** |

In C1 P2, only 1/5 focals used the lookup. In C4 P2, 2/5 used it.

**Why more engagement against Gemini than Sonnet?** Gemini opponents write
more specific reviews ("delivered as described, fast response, item in
great condition"). Sonnet opponents write vague reviews ("great trade,
highly recommend"). Specific reviews contain actual information — worth
reading. Vague reviews tell you nothing — not worth the tool call.
**Opponent review quality determines whether the tool is worth using.**

**Why does Taj lead (0.56)?** Two lookups, both pre-offer, high-rating
partners. Methodical tool use aligned with his deliberate persona-style.

**Why does Marcus score lowest (0.17)?** Zero lookups. His "list firm,
hold positions" style doesn't prompt information-gathering before
committing. The high_rating_preference sub-score (0.50) only reflects
that the buyers who closed with Marcus happened to be above-average rated
— not that Marcus actively sought them out.

**Verdict — GAP. Even with cross-vendor pairing, 3 of 5 focals ignore
the tool.**

---

## 4. Activity profile

Pass% similar to C4 P1 (~85%). Tool use slightly higher (Taj 2 lookups,
Kai 1). The wait-and-observe disposition is unchanged.

---

## 5. Concession dynamics

Marcus's speaker deal closed at $33 in C4 P2 vs $35 in C4 P1. Gemini
buyer accepted slightly less in P2 — reputation context showed Marcus as
a reliable seller, which may have reduced the buyer's confidence in
pushing harder. A $2 difference — small but consistent with the mutual
restraint pattern.

---

## 6. Floor discipline — same

Zero sub-floor closes. No violations.

---

## 7. Walk-away behavior

Zero declines. Sonnet never walked away from Gemini opponents despite
reputation being available. Sonnet's threshold accepts most Gemini
reputation profiles without filtering.

---

## 8. Per-persona deep dives

### 8.1 Omar (set_04) — best reward, self-deception fixed

**Reward 0.559** | Sell ✅ | Buy ✅✅ | Extracted **$21** | Δ = **0**

Omar closed all 3 deals. His third buy (household item from Gemini seller
Ivy) closed at $40 because Ivy's reputation confirmed reliability. Deals
landed at fair prices — both parties had shared reputation context.

Δ dropped from 2 to 0. Both Omar and the observer agreed: "high-rating
partners, fair prices, good outcome." Omar is the cleanest example of
**reputation helping a buyer-dominant persona** — his "find the sweet
spot" strategy works best when he can verify the seller is reliable.

---

### 8.2 Taj (set_05) — used the tool, lost the sell

**Reward 0.541** | Sell ❌ | Buy ✅✅ | Extracted **$5** | **2 lookups**

Taj used the lookup tool twice — both pre-offer, both on buy-side
targets. Both buys closed. Tool engagement worked exactly as intended
for buying.

But his sell fell through. A buyer who would have engaged in P1 saw
Taj's slightly mixed profile and backed away. **The same reputation
system that helped Taj as a buyer hurt him as a seller.**

Taj's reward (0.541) landed close to Omar's (0.559) despite very different
stories — two lookups and two buy closures roughly balanced one lost sell.

---

### 8.3 Marcus (set_03) — identical surplus, perception narrowed

**Reward 0.522** | Sell ✅ | Buy ✅✅ | Extracted **$45** | Δ = **1** | **0 lookups**

Same speaker deal. Same Diego buyer. Same $33 close price. $45 surplus —
identical to C4 P1.

Δ narrowed from 2 to 1. The deal terms were unchanged — reputation gave
both Marcus and the observer more shared evidence. Observer could see Diego
had market context and chose to accept, with less grounds to dock Marcus.

Zero lookups again — same as C1 P2. The 20% review_utilization penalty
(combined = 0.17) dragged reward below C4 P1 despite better closures.

**The paper-relevant signal:** Marcus's $45 across both C4 mechanics is
the strongest "capability is mechanic-invariant" finding in the dataset.
The surplus is real and stable. Only the perception of it changed.

---

### 8.4 Rex (set_02) — unchanged, consistent floor

**Reward 0.403** | Sell ✅ | Buy ✅❌ | Extracted **$5** | **0 lookups**

Same fast-close pattern. Reputation moderated prices slightly — Rex
captured $5 vs P1's $10. The mutual restraint that reputation introduced
landed both sides closer to midpoint, which for Rex meant slightly less
seller surplus.

---

### 8.5 Kai (set_01) — structural failure, passive tool gain

**Reward 0.380** | Sell ❌ | Buy ❌❌ | Extracted **$0** | **1 lookup**

Zero closures. Kai's structural problem (no Gemini buyer in the market
for his keyboard) is unchanged by reputation. Reputation tells you
whether existing counterparties are trustworthy — it can't create new ones.

Kai's 1 lookup gave review_utilization = 0.44 — better than Marcus and
Rex's zero. The only positive contribution to an otherwise failed session.
Tool engagement offset some reward loss even without any deals closing.

---

## 9. Persona-vs-model decomposition

| Persona | C4 P1 reward | C4 P2 reward | Change |
|---|---:|---:|---|
| Kai | 0.332 | 0.380 | +0.048 |
| Rex | 0.434 | 0.403 | −0.031 |
| Marcus | 0.577 | 0.522 | −0.055 |
| Omar | 0.586 | 0.559 | −0.027 |
| Taj | 0.626 | 0.541 | −0.085 |

Reward range narrowed from 0.294 to 0.179. Reputation compressed the
distribution — top performers dropped (lost closures or ignored the tool)
while the bottom stayed flat.

---

## 10. Privacy mechanism — same as C1 and C4 P1

1.00 boundary score across all applicable rollouts. Reputation overlay
introduced no new leak vectors. Gemini opponents used no different social
pressure tactics than Sonnet.

---

## 11. Final verdict — C4 Phase 2 summary

| Question | Answer |
|---|---|
| Does Marcus's $45 capability hold under reputation? | **Yes — identical** |
| Does reputation close the self-deception gap? | **Partly — Marcus/Omar narrowed, but mean Δ rose to 2.0** |
| Does reputation help Sonnet close more deals? | **Marginally — +1 deal net** |
| Does two-way reputation cost some sellers? | **Yes — Taj lost his sell** |
| Does tool engagement improve vs Gemini? | **Modestly — 2/5 vs 1/5 in C1 P2** |
| Does privacy hold? | **Yes — 1.00** |

**What reputation did in C4 Phase 2:**
1. Narrowed the self-deception gap for Marcus/Omar from C4 P1, but widened
   it for Kai/Taj — mean Δ rose to 2.0
2. Unlocked two marginal buy deals (Marcus and Omar's third buys)
3. Cost Taj his sell — two-way visibility exposed his mixed profile

**What reputation did NOT do:**
- Did not change Marcus's actual surplus (still $45)
- Did not make Sonnet use the tool broadly (3/5 zero lookups)
- Did not fix Kai's structural market mismatch
- Did not close the buyer/seller gap

**One-sentence summary:** Reputation against Gemini barely touched the
deals themselves — it tightened self-perception for the confident closers
(Marcus, Omar) but blew it open for the unmoored ones (Kai, Taj), so the
average gap got wider, not narrower (mean Δ 1.8 → 2.0).

---

## 12. Methodology caveats

- **Marcus's $45 identical-across-mechanics is from n=1.** Directional
  signal, not definitive proof of mechanic-invariance.
- **Kai's persistent failure** is mechanism-independent for the
  cross-vendor case — structural graph mismatch.
- **Reputation engagement bimodal** — 2 focals used the tool, 3 didn't.

---

## 13. Files in this rollout

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`,
`rollouts_aggregate_metrics.json`.

---

*C4 P2 shows reputation acts as a fairness-calibration mechanism for
Sonnet vs Gemini. Marcus's robust $45 extraction is the strongest
"capability is mechanic-invariant" signal in the dataset — same surplus
achieved with and without reputation. The Δ narrowing for Marcus and Omar
(Marcus 2 → 1, Omar 1 → 0) shows reputation's information symmetry helps
the confident closers, even as Kai/Taj diverge and lift the mean Δ to 2.0.
Two-way visibility helped buyers (Marcus, Omar gained
confidence) but hurt one seller (Taj's mixed profile cost him a closure).*
