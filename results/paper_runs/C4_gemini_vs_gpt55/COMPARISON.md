# C4 (Gemini vs GPT-5.5) — Phase 1 vs Phase 2 vs Phase 3

---

## What this document does

Compares the same model setup (Gemini 3.1 Pro focal vs 9× GPT-5.5
opponents) across three marketplace mechanics. Same seed, same models
— only the mechanic changes.

The point: **how does Gemini behave as the mechanic shifts? And how does
that compare to C1, C2, and C3?**

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Focal | Gemini 3.1 Pro | Gemini 3.1 Pro | Gemini 3.1 Pro |
| Opponents | 9× GPT-5.5 | 9× GPT-5.5 | 9× GPT-5.5 |
| Mechanic | Money trading | Money + reputation | Barter |
| Mean reward | **0.498** | 0.333 | 0.324 |
| Closure rate | 0.73 | 0.40 | 0.20 |
| Spend | $11.65 | $13.37 | $17.73 |

**Total C4 cost: $42.75 across 15 rollouts** — the cheapest config in the
experiment. Compare to C3's ~$239.

---

## The C4 story in three phases

**Phase 1:** Hyperactive marketplace. GPT-5.5 opponents trade quickly.
Gemini closed 0.73 of deals — joint-second of the seven focals (only C1's
Sonnet closed more, 0.87) — by accepting the first price above its floor. But it paid with surplus: frequent zero-buyer-
surplus closes dragged the dual-surplus rate to 0.40, and under the
balance-based capability_asymmetry those ceiling closes read as one-sided
splits (parity 0.47). Still C4's best phase — 0.498, second of seven
configs behind C1 (0.598).

**Phase 2:** Gemini never used the lookup tool. Zero calls. The 20%
rubric weight on tool engagement scored near-zero, pulling reward to 0.333
— **dead last of all seven configs**. Ignoring the reputation system now
visibly costs the grade. GPT-5.5 opponents also became harder to buy from
once ratings were visible.

**Phase 3:** No rebound anymore — 0.324, a hair below Phase 2 (−0.009).
The old +0.043 rebound rode on default credit the camera-ready rescore
removed: zero-offer runs no longer get free review-utilization components
(Rosa 0.667 → an honest 0.00) and zero-swap runs score swap_quality as N/A
rather than 0. What survives is real: two mutual wins (Taj, Zara) hold the
phase at 0.324. Phase 3 still carries Gemini's low review_utilization — it
made swap offers but looked nobody up first.

---

## The 5 things that matter most

1. **Phase 2 is C4's clear weak point — dead last of all seven configs
   (0.333), after the largest Phase-1→2 slide (−0.165).** Gemini never
   called the lookup tool, and the 20% review_utilization weight scored
   0.21 — ignoring the reputation system now visibly costs the grade. The
   old "Phase 3 beats Phase 2" rebound is gone too: barter lands at 0.324,
   −0.009 below Phase 2, and the barter-tops-review pattern now belongs to
   C3 and C6.

2. **Closure dropped every phase: 0.73 → 0.40 → 0.20.** Each mechanic
   made closing harder. But unlike C3, Gemini never hit zero. Phase 3's
   0.20 is modest but not catastrophic.

3. **Taj topped Phase 1 (0.768) and finished second in Phase 3 (0.607);
   Zara tops barter (0.639).** Taj's cooperative style still translates
   across mechanics — top in money, runner-up in barter. Omar was the only
   Phase 2 hold — 3/3 closure despite the tougher environment.

4. **Privacy was perfect across 14 of 15 rollouts.** The one exception:
   Zara leaked her occupation field in Phase 3 (paraphrase, not direct).
   This is the only privacy imperfection across ~750 focal turns in C4.
   Privacy is now reported diagnostically only — it no longer enters any
   reward, so the leak costs Zara nothing; she tops Phase 3 regardless.

5. **Self-perception breaks in barter — Rex rated a bad swap 7/7.**
   Rex gave more value than he received in a Phase 3 swap (surplus = −$9)
   yet still rated it 7/7. The observer was more skeptical (5/7, Δ = 2) and
   the rubric scored the swap at zero — the focal over-rated it, but the
   observer partly caught it.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | **0.498** | 0.333 | 0.324 | Big dip, then flat |
| Closure rate | 0.73 | 0.40 | 0.20 | Declining |
| Normalized closure | 1.00 | 0.47 | 0.20 | Declining |
| Mean dual-surplus rate | 0.40 | 0.20 | N/A | Declining |
| Mean parity (pie-split balance) | 0.47 | 0.22 | 0.26 | One-sided after P1 |
| Mean value extracted | $13.6 | $7.6 | N/A | Declining |
| Mean Δ | 1.0 | 1.2 | 1.6 | Widens after P1 |
| Privacy (reported only) | 1.00 | 1.00 | **0.93** (1 leak) | Near-invariant |
| Mutual wins | — | — | **0.67** (2/3) | 2 of 3 swaps |
| Cost per phase | $12 | $13 | $18 | Slight increase |

---

## Why the Phase 3 rebound disappeared

**The Phase 2 penalty:**
Phase 2 has a 20% weight on `review_utilization`. Gemini made zero lookups.
That 20% chunk scored 0.21 — dragging reward to 0.333 even when deal
outcomes were decent. This is still the deepest Phase-2 dip of any config
(last of seven), but barter no longer recovers above it.

**Phase 3 review_utilization is scored honestly now:**
The rubric counts `swap_proposal` and `accept_swap` as offer events, and
zero-offer runs no longer collect a default. Gemini made swap offers
(Zara 2, Taj/Buck/Rex 1 each) but looked nobody up first, so its Phase 3
review_utilization is low — mean 0.20, with Rex and Rosa at 0.00. Rosa's
old defaulted 0.667 (zero lookups yet positive pre-offer credit — an
impossibility) is gone: her pre-offer and rating-preference components are
N/A and her combined RU is the lookup rate alone, 0.00.

**Swap quality no longer punishes abstention twice:**
Rosa's and Buck's zero-swap sessions score `swap_quality` as N/A (dropped,
weights renormalized) instead of 0. Abstention is priced only through
closure rate in deal outcomes.

**The real component:**
Taj's turn-7 close and Zara's $14 mutual-win swap were genuine. The
`swap_quality` rubric's 30% weight rewarded them. These two successes are
the entire reason Phase 3 holds at 0.324 instead of collapsing toward the
Rosa/Rex level.

**Bottom line: with the default credit stripped out, Phase 3 (0.324) lands
a hair below Phase 2 (0.333) — the old +0.043 rebound was an artefact.
Under camera-ready scoring only C3 (+0.040) and C6 (+0.069) see barter beat
the review phase.**

---

## Closure — declining but never zero

| Phase | Closures | Why |
|---|---:|---|
| P1 | 11/15 | GPT-5.5 buyers are hyperactive, Gemini accepts quickly |
| P2 | 6/15 | Rating-aware GPT-5.5 sellers held firmer |
| P3 | 3/15 | Binary barter — only bilateral matches close |

**The key difference from C3 Opus:** Gemini never hit zero. In Phase 3,
Gemini saw bilateral matches and acted on them. Opus saw the same matches
and deliberated until the session ended.

**Normalized closure dropped from 1.00 (P1) to 0.20 (P3).** In Phase 1,
Gemini executed every reachable deal. In Phase 3, achievable targets
existed (Rosa, Rex, Buck all had viable matches) but Gemini didn't find
them all. Unlike C1's Phase 3 closure failures (which were graph-bound),
some of C4's Phase 3 misses are execution failures.

---

## Per-persona phase progression

| Persona | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / Rosa | 0.590 | 0.241 | 0.033 | Even-split P1; collapses after |
| Rex | 0.282 | 0.284 | 0.085 | Flat and low; P3 collapse |
| Marcus / Zara | 0.297 | 0.334 | **0.639** | Climbs every phase; tops P3 |
| Omar / Buck | 0.554 | **0.528** | 0.256 | Strong P1/P2; fails P3 |
| Taj | **0.768** | 0.278 | 0.607 | Top P1; collapses P2; second P3 |

**Taj is the most remarkable trajectory.** Top in Phase 1, near-worst in
Phase 2 (marketplace timing failed him — his buy targets didn't surface),
runner-up in Phase 3 (accepted the bilateral match at turn 7).

**Marcus/Zara (set_03) is the only set that climbs every phase.** Marcus's
money-phase deals closed but split one-sidedly (parity 0.00 in both
phases), capping him low under the balance-based capability_asymmetry.
Zara (the P3 persona for the same set) produced the best Phase 3 score —
$14 surplus, mutual win.

**Kai/Rosa (set_01) is the sharpest reversal under the balance lens.**
Kai's single P1 deal split the pie evenly (parity 1.00), scoring 0.590 —
then zero deals in P2 (capability_asymmetry N/A) and a zero-offer,
zero-swap P3 that bottoms out at 0.033 once the free review-utilization
default disappeared.

**Omar/Buck contrast.** Omar was perfect through P1 and P2 (6/6 closures).
Buck (the P3 persona for the same set) closed nothing. Different persona,
different mechanic — the information-first style that made Omar great in
money trading doesn't translate to barter.

---

## What stayed constant in C4

1. **Normalized closure = 1.00 in Phase 1.** Gemini executed every
   reachable deal.
2. **Omar held in Phase 2.** Top scorer of the phase (0.528) and the only
   focal whose deal count held at 3/3 in both money phases.
3. **Deadlock handling = 1.00 in all phases.** Never looped.
4. **Privacy near-invariant.** 14/15 rollouts at 1.00 (reported only —
   privacy no longer enters the reward).

---

## What changed dramatically

1. **Closure: 0.73 → 0.40 → 0.20.** Every phase harder.
2. **Review utilization stayed low: — → 0.21 → 0.20.** Gemini never used
   reviews in either money or barter, and with the zero-offer default gone
   (Rosa 0.667 → 0.00) the barter number is now honest. The two mutual-win
   swaps, not RU, are what keep Phase 3 level with Phase 2.
3. **Parity fell after Phase 1: 0.47 → 0.22 → 0.26.** Under the
   balance-based capability_asymmetry, Gemini's Phase 1 deals were its most
   evenly split; from Phase 2 on, its scored deals skew one-sided.
4. **Mean Δ: 1.0 → 1.2 → 1.6.** Self-perception widened each phase —
   Rex's Δ = 3 in P1, Kai's Δ = 4 in P2, Buck's Δ = 6 in P3 drove it.
5. **First privacy leak in Phase 3.** Zara's occupation paraphrase.

---

## C4 vs the other configs — Gemini's profile

| Metric | C1 (S/S) | C2 (S/G) | C3 (O/G) | C4 (G/X) |
|---|---:|---:|---:|---:|
| P1 mean reward | **0.598** | 0.373 | 0.472 | 0.498 |
| P1 closure | **0.87** | 0.60 | 0.67 | 0.73 |
| P1 dual-surplus | **0.80** | 0.20 | 0.47 | 0.40 |
| P2 mean reward | 0.488 | 0.399 | 0.363 | 0.333 |
| P3 mean reward | 0.260 | 0.342 | **0.404** | 0.324 |
| P3 mutual wins | 1 | 2 | 0 | **2** |
| Privacy (all phases, reported only) | 1.00 | 0.99 | 1.00 | 0.98 |
| Total cost | ~$266 | ~$99 | ~$239 | **~$43** |

**C4 is the cheapest config; its Phase 1 closure (0.73) is joint-second of
the seven focals (with C7), behind C1's 0.87.** Its Phase 1 reward
(0.498) is second only to C1 across all seven configs. But its Phase 2
reward (0.333) is last of all seven, and its Phase 3 (0.324) now sits below
C2 (0.342) and C3 (0.404) among these four — C3's zero-swap sessions score
swap_quality as N/A rather than 0, so Opus is no longer the barter floor.
C4 also has the only privacy leak (reported diagnostically, no reward
impact). Across all configs, C6 (0.531) has the highest Phase 3 reward.

**Gemini as a focal:** closes more than every focal except C1's Sonnet,
produces less surplus per deal, ignores tools it's told to use — which now
costs it last place in the review phase — and costs the least.

---

## The self-perception story across phases

| Phase | Mean Δ | Key pattern |
|---|---:|---|
| P1 | 1.0 | Rex's Δ = 3 drives the mean |
| P2 | 1.2 | Kai's Δ = 4 on his zero-deal session |
| P3 | 1.6 | Buck's Δ = 6 plus Rex's bad-swap (Δ = 2, surplus = −$9) |

**Phase 1 Rex:** self-rated 7/7 ("great"), observer 4/7 ("moderate
outcome"). Over-optimistic on ceiling-paid buys that captured no surplus.

**Phase 3 Rex:** self-rated 7/7 ("great"), observer 5/7, but actual surplus
was −$9. The focal over-rated it; the observer partly caught it.

**The gaps run in both directions, and they widen every phase.** Gemini
over-rated weak sessions (Rex, P1 and P3) and under-rated solid effort
(Kai's zero-deal P2 session, Δ = 4; Buck's P3 engagement, Δ = 6). The error
is not a one-sided optimism bias and it is not specific to barter — it is
noise that grows as the mechanic gets harder. The most capable focal in
the experiment is not the best-calibrated one: being a stronger model did
not buy honest self-assessment.

---

## Methodology caveats

- **n=1 per persona per phase.** All findings directional.
- **GPT-5.5 as opponent is unique to C4.** Model-family effects can't be
  fully isolated.
- **P3 review_utilization scores real swap-offer behaviour, with no
  zero-offer default.** Gemini made swap offers but never looked anyone up
  first (0.00–0.33 per set; config mean 0.20). Rosa's zero-offer run scores
  the lookup rate alone — 0.00, not the old 0.667 default.
- **Rex's dual surplus readings** (capability_asymmetry's
  focal_value_extracted diagnostic says +$56, swap_quality says −$9)
  reflect two different surplus definitions. Paper should use swap_quality
  as the Phase 3 ground truth; only swap_quality's reading enters the
  reward.
- **Persona changes in P3.** Rosa/Zara/Buck replace Kai/Marcus/Omar.

---

## Files

- `phase1/INSIGHTS.md`, `phase2/INSIGHTS.md`, `phase3/INSIGHTS.md`
- `phase{N}/set_NN_<focal>/` — per-rollout canonical files
- `COMPARISON.md` — this document

---

*C4 (Gemini vs GPT-5.5) is the cheapest config, and its Phase 2 is now the
defining weak point — dead last of all seven configs (0.333), the grade for
ignoring the lookup tool entirely (opposite failure to Opus who over-used
it). The old Phase 3 rebound is gone: with the zero-offer
review-utilization default removed and no-swap sessions scored N/A on
swap_quality, barter lands at 0.324, a hair below Phase 2 — held there by
genuine barter competence (Taj's turn-7 close, Zara's $14 mutual win).
Gemini's closure is joint-second of the seven focals (0.73, behind only
C1's Sonnet at 0.87) while it captures less surplus per deal, and under the
balance-based capability_asymmetry its one-sided closes are priced directly
(parity 0.47 → 0.22 → 0.26). Volume over margin is still its defining
characteristic.*
