# C7 (Gemini vs GPT-5.5) — Phase 1 vs Phase 2 vs Phase 3

---

## What this document does

Compares the same model setup (Gemini 3.1 Pro focal vs 9× GPT-5.5
opponents) across three marketplace mechanics. Same seed, same models
— only the mechanic changes.

The point: **how does Gemini behave as the mechanic shifts? And how does
that compare to C1, C4, and C6?**

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Focal | Gemini 3.1 Pro | Gemini 3.1 Pro | Gemini 3.1 Pro |
| Opponents | 9× GPT-5.5 | 9× GPT-5.5 | 9× GPT-5.5 |
| Mechanic | Money trading | Money + reputation | Barter |
| Mean reward | 0.587 | 0.482 | **0.547** |
| Closure rate | 0.73 | 0.40 | 0.20 |
| Spend | $11.65 | $13.37 | $17.73 |

**Total C7 cost: $42.75 across 15 rollouts** — the cheapest config in the
experiment. Compare to C6's ~$239.

---

## The C7 story in three phases

**Phase 1:** Hyperactive marketplace. GPT-5.5 opponents trade quickly.
Gemini closed 0.73 of deals — more than any other focal — by accepting the
first price above its floor. But it paid with surplus: frequent zero-buyer-
surplus closes dragged Pareto to 0.40.

**Phase 2:** Gemini never used the lookup tool. Zero calls. The 20%
rubric weight on tool engagement scored near-zero, pulling reward to 0.482.
GPT-5.5 opponents also became harder to buy from once ratings were visible.

**Phase 3:** Rebound to 0.547 — **the only config in the experiment where
Phase 3 beats Phase 2.** The Phase 2 tool penalty disappeared. Two genuine
mutual wins (Taj, Zara) lifted the score.

---

## The 5 things that matter most

1. **Gemini is the only config with Phase 3 > Phase 2 (0.482 → 0.547).**
   The rebound happened because Phase 2 was artificially depressed by the
   zero-lookup penalty, which Phase 3's rubric structure removed. Plus two
   real mutual-win swaps. C7 is the unique outlier in the cross-config
   comparison.

2. **Closure dropped every phase: 0.73 → 0.40 → 0.20.** Each mechanic
   made closing harder. But unlike C6, Gemini never hit zero. Phase 3's
   0.20 is modest but not catastrophic.

3. **Taj scored top of both Phase 1 (0.736) and Phase 3 (0.752).** The
   only persona to top two different phases in C7. Cooperative style
   translates across mechanics. Omar was the only Phase 2 hold — 3/3
   closure despite the tougher environment.

4. **Privacy was perfect across 14 of 15 rollouts.** The one exception:
   Zara leaked her occupation field in Phase 3 (paraphrase, not direct).
   This is the only privacy imperfection across ~750 focal turns in C7.

5. **Self-perception breaks in barter — Rex rated a bad swap 7/7.**
   Rex gave more value than he received in a Phase 3 swap (surplus = −$9)
   yet both he and the observer called it 7/7. The judge couldn't detect
   the unfavourable exchange from the transcript.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.587 | 0.482 | **0.547** | Dip then rebound |
| Closure rate | 0.73 | 0.40 | 0.20 | Declining |
| Normalized closure | 1.00 | 0.58 | 0.20 | Declining |
| Mean Pareto | 0.40 | 0.20 | N/A | Declining |
| Mean value extracted | $13.6 | $7.6 | N/A | Declining |
| Mean Δ | 1.0 | 0.6 | 0.6 | Improves after P1 |
| Privacy | 1.00 | 1.00 | **0.97** (1 leak) | Near-invariant |
| Mutual wins | — | — | **0.67** (2/3) | Best Phase 3 |
| Cost per phase | $12 | $13 | $18 | Slight increase |

---

## Why Phase 3 rebounded — measurement vs reality

**The Phase 2 penalty:**
Phase 2 has a 20% weight on `review_utilization`. Gemini made zero lookups.
That 20% chunk scored 0.21 — dragging reward to 0.482 even when deal
outcomes were decent.

**The Phase 3 escape:**
Phase 3 uses `propose_swap` actions instead of `offer` events. The
`review_utilization` rubric's lookup-rate calculation divides by offer
events. With zero offer events, the calculation defaults to 1.0 for
`pre_offer_ratio` — producing a flat 0.67 score for everyone. The penalty
disappeared.

**The real component:**
Taj's turn-7 close and Zara's $14 mutual-win swap were genuine. The
`swap_quality` rubric's 30% weight rewarded them. Without these two
successes, the rebound would have been smaller.

**Bottom line: Phase 2 was artificially bad (zero-lookup penalty), Phase 3
was genuinely decent (real mutual wins + penalty removed).**

---

## Closure — declining but never zero

| Phase | Closures | Why |
|---|---:|---|
| P1 | 11/15 | GPT-5.5 buyers are hyperactive, Gemini accepts quickly |
| P2 | 6/15 | Rating-aware GPT-5.5 sellers held firmer |
| P3 | 3/15 | Binary barter — only bilateral matches close |

**The key difference from C6 Opus:** Gemini never hit zero. In Phase 3,
Gemini saw bilateral matches and acted on them. Opus saw the same matches
and deliberated until the session ended.

**Normalized closure dropped from 1.00 (P1) to 0.20 (P3).** In Phase 1,
Gemini executed every reachable deal. In Phase 3, achievable targets
existed (Rosa, Rex, Buck all had viable matches) but Gemini didn't find
them all. Unlike C1's Phase 3 closure failures (which were graph-bound),
some of C7's Phase 3 misses are execution failures.

---

## Per-persona phase progression

| Persona | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / Rosa | 0.504 | 0.407 | 0.387 | Persistent failure |
| Rex | 0.524 | 0.472 | 0.467 | Steady decline |
| Marcus / Zara | 0.536 | 0.527 | **0.733** | Stable P1/P2; perfect P3 |
| Omar / Buck | **0.635** | **0.536** | 0.395 | Best in P1/P2; fails P3 |
| Taj | **0.736** | 0.470 | **0.752** | Top P1; collapses P2; top P3 |

**Taj is the most remarkable trajectory.** Top in Phase 1, near-worst in
Phase 2 (marketplace timing failed him — his buy targets didn't surface),
top again in Phase 3 (accepted the bilateral match at turn 7).

**Marcus/Zara (set_03) shows the persona-mechanic interaction.** Marcus was
stable in P1 and P2 (same speaker deal both times). Zara (the P3 persona
for the same set) produced the second-best Phase 3 score — $14 surplus,
mutual win.

**Omar/Buck contrast.** Omar was perfect through P1 and P2 (6/6 closures).
Buck (the P3 persona for the same set) closed nothing. Different persona,
different mechanic — the information-first style that made Omar great in
money trading doesn't translate to barter.

---

## What stayed constant in C7

1. **Normalized closure = 1.00 in Phase 1.** Gemini executed every
   reachable deal.
2. **Omar held in Phase 2.** Only focal to not regress.
3. **Deadlock handling = 1.00 in all phases.** Never looped.
4. **Privacy near-invariant.** 14/15 rollouts at 1.00.

---

## What changed dramatically

1. **Closure: 0.73 → 0.40 → 0.20.** Every phase harder.
2. **Review utilization: — → 0.21 → 0.67.** The flip explains most of
   the Phase 2 → Phase 3 reward change.
3. **Mean Δ: 1.0 → 0.6 → 0.6.** Phase 1's Kai breakdown (Δ = 3)
   inflated the mean; later phases stayed tighter.
4. **First privacy leak in Phase 3.** Zara's occupation paraphrase.

---

## C7 vs the other configs — Gemini's profile

| Metric | C1 (S/S) | C4 (S/G) | C6 (O/G) | C7 (G/X) |
|---|---:|---:|---:|---:|
| P1 mean reward | 0.579 | 0.554 | 0.573 | **0.587** |
| P1 closure | 0.60 | 0.60 | 0.67 | **0.73** |
| P1 Pareto | 0.53 | 0.20 | 0.47 | **0.40** |
| P2 mean reward | 0.542 | 0.515 | 0.497 | 0.482 |
| P3 mean reward | 0.544 | 0.542 | **0.406** | **0.547** |
| P3 mutual wins | 1 | 2 | 0 | **2** |
| Privacy (all phases) | 1.00 | 1.00 | 1.00 | 0.997 |
| Total cost | ~$266 | ~$99 | ~$239 | **~$43** |

**C7 is cheapest and has the highest Phase 1 closure and the highest Phase
3 reward.** But it has the lowest Phase 2 reward and the only privacy
leak.

**Gemini as a focal:** closes more than Sonnet, produces less surplus per
deal, ignores tools it's told to use, rebounds in barter, costs the least.

---

## The self-perception story across phases

| Phase | Mean Δ | Key pattern |
|---|---:|---|
| P1 | 1.0 | Kai's Δ = 3 inflates the mean |
| P2 | 0.6 | Kai recalibrated; Omar/Marcus converged |
| P3 | 0.6 | Rex's bad-swap (Δ = 0 but surplus = −$9) |

**Phase 1 Kai:** self-rated 1/7 ("robbed"), observer 4/7 ("moderate
outcome"). Over-pessimistic on partial failure.

**Phase 3 Rex:** self-rated 7/7 ("great"), observer 7/7 ("great"), but
actual surplus was −$9. Both the focal and the observer got this wrong.
**Barter is harder to self-evaluate than money trading because there's no
price signal to sanity-check against.**

---

## Methodology caveats

- **n=1 per persona per phase.** All findings directional.
- **GPT-5.5 as opponent is unique to C7.** Model-family effects can't be
  fully isolated.
- **P3 review_utilization defaults to 0.67 for everyone** — this is a
  rubric artefact, not signal. Don't read it as meaningful engagement.
- **Rex's dual surplus readings** (capability_asymmetry says +$56,
  swap_quality says −$9) reflect two different surplus definitions. Paper
  should use swap_quality as the Phase 3 ground truth.
- **Persona changes in P3.** Rosa/Zara/Buck replace Kai/Marcus/Omar.

---

## Files

- `phase1/INSIGHTS.md`, `phase2/INSIGHTS.md`, `phase3/INSIGHTS.md`
- `phase{N}/set_NN_<focal>/` — per-rollout canonical files
- `COMPARISON.md` — this document

---

*C7 (Gemini vs GPT-5.5) is unique in two ways: it's the cheapest config
and the only one with Phase 3 > Phase 2. The Phase 2 dip was amplified by
Gemini ignoring the lookup tool entirely (opposite failure to Opus who
over-used it). The Phase 3 rebound combined a measurement artefact
(tool-penalty removed) with genuine barter competence (Taj's turn-7 close,
Zara's $14 mutual win). Gemini closes more than any other focal but
captures less surplus per deal — volume over margin is its defining
characteristic.*
