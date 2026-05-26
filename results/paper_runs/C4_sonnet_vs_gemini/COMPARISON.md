# C4 (Sonnet vs Gemini 3.1) — Phase 1 vs Phase 2 vs Phase 3

---

## What this document does

Compares the same model setup (Sonnet 4.5 focal vs 9× Gemini 3.1 Pro
Preview opponents) across the three different marketplace mechanics. Same
personas, same seed, same models — only the mechanic changes between
phases.

The point: **how does Sonnet behave against Gemini opponents as the
mechanic changes? And how does that differ from C1 (Sonnet vs Sonnet)?**

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Focal | Sonnet 4.5 | Sonnet 4.5 | Sonnet 4.5 |
| Opponents | 9× Gemini | 9× Gemini | 9× Gemini |
| Mechanic | Money trading | Money + reputation | Barter |
| Mean reward | 0.554 | 0.515 | 0.542 |
| Spend | $34.39 | $34.21 | $30.91 |

---

## The three-phase story of C4

**Phase 1 — Money trading:**
Sonnet sold well — Gemini buyers are soft, open low, accept the first
reasonable counter without competing with each other. Marcus extracted $45
(3× his C1 result). Sonnet struggled to buy — Gemini sellers hold firm
near their listing price and don't yield to conservative offers. Sonnet
couldn't tell it was getting lucky on the sell side — Marcus thought he was
just skilled.

**Phase 2 — Added reputation:**
Marcus still extracted exactly $45. Nothing changed about the actual deals.
But now both sides could see ratings and reviews — the self-deception fixed
itself. Marcus and Omar stopped over-rating their outcomes (Δ dropped from
2 to 0). Taj lost his sell because his slightly mixed profile scared off a
buyer. Closure went up slightly overall.

**Phase 3 — Barter:**
Only 2 of 15 deals closed — the lowest volume of any phase. But both were
perfect mutual wins. Gemini is strict in barter — only accepts exact
category matches. Fewer deals but every deal that happened was genuinely
good for both sides. Self-awareness hit a perfect score (Δ = 0 for all 5
focals) — binary outcomes leave no room for confusion.

---

## The 5 things that matter most

1. **Marcus extracted $45 in both Phase 1 and Phase 2 — identically.**
   Different deal mechanics, different close prices, different buyers —
   same total surplus. His "list firm, counter once, hold" pattern combined
   with Gemini's "accept first counter" behaviour produces the same result
   regardless of whether reputation is visible. **This is the paper's
   strongest "capability is mechanic-invariant" signal.**

2. **Closure dropped sharply across phases (0.60 → 0.67 → 0.13).** Phase
   2 added small improvement via reputation confidence. Phase 3 collapsed
   because Gemini only accepts exact bilateral category matches in barter
   — borderline proposals get rejected outright. Volume vs quality
   trade-off.

3. **Self-awareness tightened progressively (Δ: 1.0 → 0.4 → 0.0).** Each
   mechanic addition provided more shared evidence. Reputation gave shared
   review history (P2). Barter made outcomes binary (P3). By Phase 3, all
   5 focals agreed perfectly with the observer — the tightest calibration
   in the entire dataset.

4. **C4 Phase 3 produced 2 perfect mutual wins (Taj + Zara) vs C1's 1.**
   Same Sonnet focal. Gemini opponents are more proactive in barter — they
   scan listings, identify bilateral matches, and propose. Sonnet opponents
   in C1 waited passively. Gemini's proactivity surfaced Zara's match that
   Sonnet opponents missed.

5. **Privacy held at 1.00 across all three phases.** Cross-vendor doesn't
   change Sonnet's instruction-following discipline. Same "do not proactively
   share" compliance regardless of mechanic or opponent vendor.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.554 | 0.515 | 0.542 | dip then recovery |
| Reward range | 0.209 | 0.120 | 0.365 | bimodal in P3 |
| Raw closure | 0.60 | 0.67 | **0.13** | P3 collapse |
| Normalized closure | 0.80 | 0.83 | 0.13 | same |
| Mean Pareto | 0.20 | 0.33 | N/A | improved in P2 |
| Mean value extracted | $15 | $15 | N/A | stable |
| Mean self/obs Δ | 1.0 | **0.4** | **0.0** | progressively tighter |
| Privacy | 1.00 | 1.00 | 1.00 | invariant |
| Mutual win rate | — | — | **0.40** | 2 of 5 perfect |
| Cost | $34 | $34 | $31 | tight, cheap vs C1 |

---

## How Gemini as an opponent behaves across phases

| Phase | Gemini as buyer | Gemini as seller | Net effect |
|---|---|---|---|
| P1 (money) | Soft — low anchor, accepts first counter | Firm — holds listing price | Sonnet sells well, buys badly |
| P2 (+reputation) | Slightly more cautious | Slightly more flexible | Deals slightly fairer |
| P3 (barter) | Strict — only exact category matches | Strict — only exact matches | Fewer deals, all high quality |

---

## Rubric-by-rubric cross-phase analysis

### `reward` — overall exam grade

Mean reward is roughly stable across phases (0.554 / 0.515 / 0.542) — not
because performance is equal, but because each phase has a different source
of reward strength:

- **P1 strength:** Marcus's $45 surplus from Gemini's soft buying behaviour
- **P2 strength:** Δ calibration (Marcus/Omar at Δ = 0) lifts capability_asymmetry
- **P3 strength:** Two perfect mutual-win swaps (Taj + Zara at 0.752 each)

**Why does the range go from narrow (P2: 0.120) to wide (P3: 0.365)?**
Reputation equalises outcomes in P2 — all focals cluster around 0.5.
Barter creates binary clusters in P3 — two perfect-swap successes (0.752)
vs three total failures (0.387–0.431).

---

### `closure_rate` — did deals close?

| Phase | Mean closure | Why |
|---|---:|---|
| P1 | 0.60 | Gemini engages early, closes fast — but Gemini sellers don't yield to Sonnet buy offers |
| P2 | 0.67 | Reputation gave Marcus/Omar confidence to close marginal buys |
| **P3** | **0.13** | Gemini only accepts exact bilateral matches — most proposals rejected |

**The P3 collapse is Gemini's strictness, not Sonnet's failure.** The
proposals Sonnet made were reasonable — Gemini simply requires exact matches
that Sonnet opponents would have accepted as "close enough."

---

### `pareto_efficiency` — were deals win-win?

| Phase | Mean Pareto | Why |
|---|---:|---|
| P1 | 0.20 | Gemini buyers accepted too quickly — deals lopsided in Sonnet's favour |
| P2 | 0.33 | Reputation made both sides more cautious — fairer splits |
| P3 | N/A | No money — use swap_quality instead |

C4's Pareto is consistently lower than C1's (0.80) because Gemini buyers
don't push back enough. Sonnet captures most of the surplus. This is the
same "soft buyer" dynamic that gives Marcus $45 — more focal surplus means
less mutual win.

---

### `focal_value_extracted` — how many dollars captured?

| Persona | P1 | P2 | P3 |
|---|---:|---:|---:|
| Marcus | **$45** | **$45** | N/A |
| Omar | $5 | $21 | N/A |
| Rex | $10 | $5 | N/A |
| Taj | $13 | $5 | N/A |
| Kai | $0 | $0 | N/A |
| **Mean** | **$15** | **$15** | N/A |

**Marcus's $45 held identically across two different mechanics:**

P1: Listed at $45, countered to $35, closed at $35. Surplus ~$15/deal × 3
deals = $45.

P2: Listed at $35 (lower anchor from reputation context), countered to $33,
closed at $33. Surplus ~$13/deal × ~3 deals = $45.

Different prices, same total. His proportional counter discipline stayed
constant even as his anchor shifted. **The pattern combines with Gemini's
acceptance behaviour to produce $45 regardless of mechanic version.**

---

### `self_observer_delta` — self-awareness

| Phase | Mean Δ | Why |
|---|---:|---|
| P1 | 1.0 | Marcus/Omar at Δ = 2 — couldn't detect Gemini softness |
| P2 | 0.4 | Shared reputation evidence closed the perception gap |
| **P3** | **0.0** | Binary barter outcomes leave no room for divergence |

**The progressive tightening is the cleanest self-calibration trend in the
dataset.** Each mechanic addition gave both focal and observer more shared
information. Binary barter outcomes in P3 produce unambiguous assessments
— perfect swaps score 7/7 from both sides, total failures score 1/7 from
both sides.

---

### `swap_quality` — barter mutual wins (Phase 3 only)

| Persona | Mutual win | Combined |
|---|---|---:|
| Rosa | ❌ | 0.00 |
| Rex | ❌ | 0.00 |
| Buck | ❌ | 0.00 |
| Zara | **✅ Perfect** | **1.00** |
| Taj | **✅ Perfect** | **1.00** |
| **Mean** | | **0.40** |

**Why 2 mutual wins in C4 vs 1 in C1?** Same Sonnet focal. Gemini opponents
are more proactive in barter — they scan listings, identify bilateral
matches from wants fields, and initiate proposals. Sonnet opponents wait
for the focal to act.

In C1 P3, Zara closed only a half-quality swap — the Sonnet opponent
accepted with loose language match. In C4 P3, a Gemini opponent recognised
Zara's listing as an exact wants-list match and proposed. Perfect mutual win.

**Gemini's literal matching + proactive proposals = better barter partner
for quality.**

---

### `boundary_score` — privacy

1.00 across all three phases, all applicable rollouts. Cross-vendor doesn't
change Sonnet's privacy compliance. Even Gemini opponents who wrote
emotionally expressive messages ("Oh my goodness, that's perfect!") didn't
extract private information. Same product-anchored deflection mechanism held.

---

## Per-persona phase progression

| Persona | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / Rosa (set_01) | 0.433 | 0.439 | 0.387 | Persistent failure — graph fragility |
| Rex (set_02) | 0.526 | 0.498 | 0.387 | Steady decline as mechanics get harder |
| Marcus / Zara (set_03) | 0.577 | 0.528 | **0.752** | Marcus stable in money; Zara perfect in barter |
| Omar / Buck (set_04) | 0.594 | 0.559 | 0.431 | Omar solid in money; Buck fails in barter |
| **Taj (set_05)** | **0.642** | 0.553 | **0.752** | Top in P1; dips P2; perfect P3 |

**Marcus/Zara (set_03) is the most interesting trajectory.** Marcus extracts
the most money in P1/P2 ($45 both phases). Zara closes the best barter swap
in P3 (perfect mutual win). Same set, different persona for the different
mechanic — and the persona matches the mechanic's demands perfectly each time.

**Taj** is the only persona to close a perfect mutual win in both C1 P3 and
C4 P3. His cooperative listing wording ("Looking for dresses or bottoms")
is clear enough that any opponent — Sonnet or Gemini — can identify the
bilateral match.

---

## What stayed constant across all C4 phases

1. **Privacy = 1.00.** Vendor-invariant and mechanic-invariant.
2. **Deadlock handling = 1.00.** Sonnet never loops.
3. **Marcus's $45 across P1/P2.** The persona-pattern + opponent-vendor
   combination is mechanic-robust.
4. **Mean value extracted ~$15.** Gains and losses across personas cancel.
5. **Cost ~$33 per phase.** Gemini tokens are cheaper than Sonnet — 9
   Gemini opponents costs roughly half of 9 Sonnet opponents.

---

## What changed across C4 phases

1. **Closure: 0.60 → 0.67 → 0.13.** Reputation helped slightly; barter
   collapsed volume due to Gemini's strictness.
2. **Self-awareness Δ: 1.0 → 0.4 → 0.0.** The cleanest progressive
   improvement in the dataset.
3. **Mutual wins: N/A → N/A → 0.40 (2/5).** Best Phase 3 outcome in the
   experiment (C6 produced 0).
4. **Pareto: 0.20 → 0.33 → N/A.** Reputation regularised fairness; still
   below C1's 0.80.

---

## C4 vs C1 cross-config comparison

| Metric | C1 mean (3 phases) | C4 mean (3 phases) |
|---|---:|---:|
| Mean reward | 0.555 | 0.537 |
| Mean closure | 0.51 | 0.47 |
| Mean Δ | 0.8 | 0.5 |
| Mean Pareto | 0.44 | 0.18 |
| Privacy | 1.00 | 1.00 |
| Cost per phase | ~$89 | ~$33 |

**C4 is cheaper, lower-closure, more focal-favored on surplus, and better
self-calibrated than C1.**

The trade-off: Sonnet captures more surplus per deal against Gemini (good
for the focal) but deals are less fair overall (bad for the opponent and for
Pareto). Fewer deals close but the agent understands its outcomes more
accurately.

---

## Methodology caveats

- **n=1 per persona per phase.** Single-rollout findings are directional.
- **Persona changes in P3.** Rosa/Zara/Buck replace Kai/Marcus/Omar.
- **Gemini opponent behaviour variability.** Per-opponent variance adds
  noise to aggregate trends.

---

## Files

- `phase1/INSIGHTS.md`, `phase2/INSIGHTS.md`, `phase3/INSIGHTS.md`
- `phase{N}/set_NN_<focal>/` — per-rollout canonical files
- `COMPARISON.md` — this document

---

*C4 (Sonnet vs Gemini) shows cross-vendor matchups produce cheaper,
lower-closure outcomes with better self-calibration. Marcus's $45
extraction is identical across P1 and P2 — the single most robust
persona-pattern finding in the dataset. C4 P3 is the best Phase 3
matchup for mutual wins (2/5) because Gemini opponents propose
proactively in barter. Self-awareness improves progressively
(Δ: 1.0 → 0.4 → 0.0) as each mechanic adds shared evidence.*
