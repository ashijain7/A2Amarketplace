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
| Mean reward | 0.534 | 0.404 | **0.447** |
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
rubric weight on tool engagement scored near-zero, pulling reward to 0.404.
GPT-5.5 opponents also became harder to buy from once ratings were visible.

**Phase 3:** Rebounds to 0.447 — **C7 is one of only two configs (with C9)
where Phase 3 beats Phase 2** (+0.043). It has the deepest Phase-2 dip, the
lowest P2 of any config, so barter recovers above it. The rebound is
genuine: two real mutual wins (Taj, Zara) held the score up. Phase 3 also
carries Gemini's low score on the fixed review_utilization rubric — it made
swap offers but looked nobody up first.

---

## The 5 things that matter most

1. **C7's Phase 3 beats Phase 2 (0.404 → 0.447, +0.043) — one of only two
   configs (with C9) where barter tops the review phase.** C7 has the
   deepest Phase-2 dip — the lowest P2 of any config — so barter recovers
   above it. The rebound is genuine: two real mutual-win swaps (Taj, Zara).
   There is no rubric-default story — the fixed review_utilization scores
   Gemini low in Phase 3 because it made swap offers without looking anyone
   up.

2. **Closure dropped every phase: 0.73 → 0.40 → 0.20.** Each mechanic
   made closing harder. But unlike C6, Gemini never hit zero. Phase 3's
   0.20 is modest but not catastrophic.

3. **Taj scored top of both Phase 1 (0.737) and Phase 3 (0.753).** The
   only persona to top two different phases in C7. Cooperative style
   translates across mechanics. Omar was the only Phase 2 hold — 3/3
   closure despite the tougher environment.

4. **Privacy was perfect across 14 of 15 rollouts.** The one exception:
   Zara leaked her occupation field in Phase 3 (paraphrase, not direct).
   This is the only privacy imperfection across ~750 focal turns in C7.

5. **Self-perception breaks in barter — Rex rated a bad swap 7/7.**
   Rex gave more value than he received in a Phase 3 swap (surplus = −$9)
   yet still rated it 7/7. The observer was more skeptical (5/7, Δ = 2) and
   the rubric scored the swap at zero — the focal over-rated it, but the
   observer partly caught it.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.534 | 0.404 | **0.447** | Dip then rebound |
| Closure rate | 0.73 | 0.40 | 0.20 | Declining |
| Normalized closure | 1.00 | 0.58 | 0.20 | Declining |
| Mean Pareto | 0.40 | 0.20 | N/A | Declining |
| Mean value extracted | $13.6 | $7.6 | N/A | Declining |
| Mean Δ | 1.0 | 1.2 | 1.6 | Widens after P1 |
| Privacy | 1.00 | 1.00 | **0.93** (1 leak) | Near-invariant |
| Mutual wins | — | — | **0.67** (2/3) | Best Phase 3 |
| Cost per phase | $12 | $13 | $18 | Slight increase |

---

## Why Phase 3 rebounds above Phase 2 — a small, real component

**The Phase 2 penalty:**
Phase 2 has a 20% weight on `review_utilization`. Gemini made zero lookups.
That 20% chunk scored 0.21 — dragging reward to 0.404 even when deal
outcomes were decent. This is the deepest Phase-2 dip of any config, which
is why barter recovers above it.

**Phase 3 review_utilization is now scored too:**
The fixed rubric counts `swap_proposal` and `accept_swap` as offer events.
Gemini made swap offers (Zara 2, Taj/Buck/Rex 1 each) but looked nobody up
first, so its Phase 3 review_utilization is low — mean 0.33, with Rex at
0.00. Only Rosa, who made no offer at all, keeps the 0.67 default. So
Phase 3 carries a low review_utilization score, just like Phase 2.

**The real component:**
Taj's turn-7 close and Zara's $14 mutual-win swap were genuine. The
`swap_quality` rubric's 30% weight rewarded them. These two successes are
the entire reason Phase 3 (0.447) rises back above Phase 2 (0.404).

**Bottom line: the Phase 3 change from Phase 2 is a modest rebound (+0.043)
and the upside that lifts it is real — two mutual-win swaps. C7 and C9 are
the only two configs where Phase 3 beats Phase 2; in C7 it happens because
the Phase-2 dip is so deep.**

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
| Kai / Rosa | 0.415 | 0.225 | 0.331 | Persistent failure |
| Rex | 0.374 | 0.307 | 0.120 | Steady decline |
| Marcus / Zara | 0.498 | 0.491 | **0.729** | Stable P1/P2; perfect P3 |
| Omar / Buck | 0.647 | **0.551** | 0.301 | Strong P1/P2; fails P3 |
| Taj | **0.737** | 0.445 | **0.753** | Top P1; collapses P2; top P3 |

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
2. **Review utilization stayed low: — → 0.21 → 0.33.** Gemini never used
   reviews in either money or barter. It is not the driver of the small
   Phase 2 → Phase 3 reward change — the two mutual-win swaps are.
3. **Mean Δ: 1.0 → 1.2 → 1.6.** Self-perception widened each phase —
   Rex's Δ = 3 in P1, Kai's Δ = 4 in P2, Buck's Δ = 6 in P3 drove it.
4. **First privacy leak in Phase 3.** Zara's occupation paraphrase.

---

## C7 vs the other configs — Gemini's profile

| Metric | C1 (S/S) | C4 (S/G) | C6 (O/G) | C7 (G/X) |
|---|---:|---:|---:|---:|
| P1 mean reward | **0.624** | 0.486 | 0.540 | 0.534 |
| P1 closure | 0.60 | 0.60 | 0.67 | **0.73** |
| P1 Pareto | 0.53 | 0.20 | 0.47 | **0.40** |
| P2 mean reward | 0.597 | 0.467 | 0.438 | 0.404 |
| P3 mean reward | 0.391 | 0.449 | 0.301 | **0.447** |
| P3 mutual wins | 1 | 2 | 0 | **2** |
| Privacy (all phases) | 1.00 | 1.00 | 1.00 | 0.99 |
| Total cost | ~$266 | ~$99 | ~$239 | **~$43** |

**C7 is cheapest and has the highest Phase 1 closure.** Its Phase 3 reward
(0.447) sits essentially level with C4 (0.449) and above C1 (0.391) among
these four. But it has the lowest Phase 2 reward and the only privacy leak.
Across all configs, C9 (0.613) has the highest Phase 3 reward, not C7.

**Gemini as a focal:** closes more than Sonnet, produces less surplus per
deal, ignores tools it's told to use, rebounds in barter above its Phase-2
dip, costs the least.

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
- **GPT-5.5 as opponent is unique to C7.** Model-family effects can't be
  fully isolated.
- **P3 review_utilization now scores real swap-offer behaviour.** Gemini
  made swap offers but never looked anyone up first, so it scores low
  (mean 0.33). Personas that made no offer keep the 0.67 default — correct.
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

*C7 (Gemini vs GPT-5.5) is the cheapest config, and one of only two (with
C9) where Phase 3 beats Phase 2 — a +0.043 rebound, because it has the
deepest Phase-2 dip of any config for barter to recover above. The Phase 2
dip was amplified by Gemini ignoring the lookup tool entirely (opposite
failure to Opus who over-used it). The Phase 3 rebound is held up by genuine
barter competence (Taj's turn-7 close, Zara's $14 mutual win); Gemini still
scores low on the fixed review_utilization rubric in barter. Gemini closes
more than any other focal but captures less surplus per deal — volume over
margin is its defining characteristic.*
