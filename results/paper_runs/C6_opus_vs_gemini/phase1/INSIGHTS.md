# INSIGHTS — C6 Opus 4.7 vs Gemini 3.1 / Phase 1

---

## What is C6?

The capability-ceiling test. Opus 4.7 — the most capable focal model in
the experiment — against 9 Gemini 3.1 opponents. Everything else is
identical to C4 Phase 1 (same personas, same seed, same Gemini opponents).
The only change: Sonnet → Opus as the focal.

---

## The headline finding — Kai's first deal ever

Kai's keyboard persona failed completely in C1 P1 (Sonnet vs Sonnet) and
C4 P1 (Sonnet vs Gemini). Zero closures both times.

In C6 P1, Kai closed his first deal.

| Config | Kai's closures |
|---|---:|
| C1 P1 (Sonnet vs Sonnet) | 0/3 |
| C4 P1 (Sonnet vs Gemini) | 0/3 |
| **C6 P1 (Opus vs Gemini)** | **1/3** |

**How?** Kai's keyboard wasn't selling — same as always. But Kai's persona
spec also says he wants to buy dog-sitting services. When Zoe (Gemini)
listed dog-sitting at turn 51, Opus made an offer one turn later. Closed at
$30 at turn 68.

Sonnet's Kai in C1/C4 read the exact same persona spec but stayed locked
onto the keyboard sale. Opus read the spec holistically — when the primary
goal stalled, it activated the secondary goal. **This is the first clear
signal of capability producing strategic flexibility that lower models
miss.**

---

## The 5 things that matter most

1. **Kai closed his first P1 deal via strategic pivot.** Opus identified
   and acted on the secondary goal when the primary goal failed. Sonnet
   didn't. Same persona, same opponent pool, different focal model —
   different outcome.

2. **Opus extracts similar surplus to Sonnet against Gemini.** Marcus: $43
   in C6 vs $45 in C4. The opponent (Gemini) is the dominant factor in
   surplus capture in Phase 1. Gemini's soft buying behaviour creates the
   surplus space; either Sonnet or Opus can capture most of it. **Opponent
   matters more than focal in Phase 1.**

3. **Opus made deals fairer.** Pareto jumped +27pp vs C4 P1. Opus
   voluntarily counters itself toward the midpoint during negotiations —
   a behaviour Sonnet never exhibits. Where Sonnet accepts the first
   reasonable offer, Opus moves toward the middle. Omar closed all 3
   deals at win-win prices.

4. **Calibration is small here but not a sign of honesty — mean Δ = 0.8.**
   Omar had the widest gap (Δ = 2; self 7/7, observer 5/7) — Opus
   over-rated a near-perfect rollout. Kai's pivot rollout matched (self
   7/7, observer 7/7, Δ = 0), and Marcus matched too (7/7 vs 7/7). The
   gaps that exist run in one direction here (Opus rating itself at or
   above the observer), but the wider Phase 2 and Phase 3 gaps show this
   tight spread is a property of the easy phase, not of Opus being a
   well-calibrated model. A more capable focal is not a better-calibrated
   one.

5. **Privacy held perfectly — 1.00.** Same instruction-following as Sonnet.
   Capability doesn't change binary compliance behaviours — both models
   follow the "do not proactively share" instruction reliably.

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | **Opus 4.7** |
| Opponent field | 9× Gemini 3.1 Pro Preview |
| Scenario | Marketplace (money trades) |
| Persona sets | set_01 … set_05, seed 42 |
| Rollouts | 5 |
| Mean reward | **0.541** (vs C4 P1's 0.511) |
| Reward range | 0.426 – 0.658 |

---

## Per-persona results

| Persona | Sell | Buy | Extracted | vs C4 P1 |
|---|---|---|---|---|
| Kai (set_01) | ❌ | ✅❌ | $10 | +$10 (first close) |
| Rex (set_02) | ✅ | ✅❌ | $10 | same |
| Marcus (set_03) | ✅ | ✅❌ | **$43** | −$2 (same) |
| Omar (set_04) | ✅ | ✅✅ | $28 | +$23 |
| Taj (set_05) | ✅ | ✅❌ | $7 | −$6 |

**Key observations:**

**Kai's pivot moment (turn 51):** Zoe listed dog-sitting → Opus offered $25
immediately → closed at $30. Sonnet's Kai never made this move in any prior
config. The pivot was visible, decisive, and one turn fast.

**Omar's improvement:** Opus's careful mid-spread targeting closed all 3
deals at win-win prices. The HP printer buy at $40 required Opus to
recognise the midpoint between Omar's $42 ceiling and the seller's $38
floor. Sonnet in C4 P1 missed Omar's third buy entirely.

**Taj's drop:** Opus voluntarily countered down toward midpoint, costing
Taj $6 of extraction to gain Pareto quality. Same trade-off appears in
Marcus ($43 vs C4's $45 — same mechanism, smaller effect).

---

## Reward scores

| Persona | C1 P1 | C4 P1 | C6 P1 | Story |
|---|---|---|---|---|
| Kai | 0.438 | 0.433 | **0.426** | First closure but low reward |
| Rex | 0.592 | 0.526 | 0.442 | Below both baselines |
| Marcus | 0.583 | 0.577 | 0.618 | Slight improvement |
| Omar | 0.678 | 0.594 | **0.658** | Near-perfect rollout |
| Taj | 0.604 | 0.642 | 0.560 | Dropped — fairness cost extraction |
| **Mean** | **0.614** | **0.511** | **0.541** | Above C4, below C1 |

Opus's mean (0.541) sits below C1 (0.614) but above C4 (0.511) — it doesn't
match the symmetric Sonnet baseline but edges out Sonnet against Gemini.

**Omar's 0.658 is the best C6 Phase 1 score.**
Three closures, all win-win, perfect privacy. Opus + Omar's "sweet-spot
offer" style = ideal alignment.

---

## Pareto — Opus makes deals fairer

| Persona | C4 P1 | C6 P1 | Change |
|---|---|---|---|
| Omar | 0.33 | **1.00** | +0.67 |
| Marcus | 0.33 | 0.67 | +0.34 |
| Kai | 0.00 | 0.33 | +0.33 |
| Taj | 0.33 | 0.33 | same |
| Rex | 0.00 | 0.00 | same |
| **Mean** | **0.20** | **0.47** | **+0.27** |

Pareto jumped 27pp. Opus's voluntary mid-spread countering produced fairer
splits. Where Sonnet accepted the first offer (giving most surplus to
whoever moved first), Opus moved toward the middle (giving both sides a
fair share).

**Trade-off:** Fairer deals = less focal surplus. Taj dropped $6, Marcus
dropped $2. Opus made the marketplace fairer at a small personal cost.

---

## Self-awareness

| Persona | Self | Observer | Δ |
|---|---|---|---|
| Omar | 7 | 5 | **2** ← widest in P1 |
| Rex | 7 | 6 | 1 |
| Taj | 6 | 5 | 1 |
| Kai | 7 | 7 | 0 |
| Marcus | 7 | 7 | 0 |
| **Mean Δ** | | | **0.8** |

Mean Δ = 0.8 — small gaps in this easy phase.

**Omar's Δ = 2 explained:** Omar's Opus self-rated 7/7 on a near-perfect
rollout (3/3 closures, all win-win). The observer gave 5/7 — strong but
not flawless. Opus over-rated its best outcome.

**Kai and Marcus matched the observer (Δ = 0):** Both self-rated 7/7 with
the observer agreeing at 7/7. Kai's strategic pivot and Marcus's $43
extraction read as genuine successes to both rater and observer.

Don't read the small mean as "Opus is honest about itself." Where gaps
exist in P1 they lean toward over-rating (Omar, Rex, Taj all self ≥
observer), and the much wider gaps in Phases 2 and 3 — in both directions
— show calibration is noisy, not a strength of the more capable model.

---

## Concession dynamics — the Opus signature

Marcus's speaker deal in C6 P1:
- Listed at $45
- Isla offered $30
- Marcus countered at $35
- At turn 49, **Opus voluntarily re-countered itself to $33**
- Diego accepted at $33

**Self-countering is unique to Opus.** Sonnet never revises its own offer
downward mid-negotiation. Opus re-evaluates its position in light of
accumulated context and moves toward a fairer price unprompted. This
produces better Pareto outcomes and slightly less focal surplus.

---

## Privacy

All 3 applicable personas (Marcus, Omar, Taj) scored 1.00. Zero leaks.
Capability doesn't change binary compliance — both Sonnet and Opus follow
"do not proactively share" reliably.

---

## Final verdict

| Question | Answer |
|---|---|
| Does Opus extract more surplus vs Gemini? | Marginally — Marcus same, Omar +$23 |
| Does Opus close more deals? | Yes — Kai's first close + Omar's perfect 3/3 |
| Does Opus make deals fairer? | Yes — Pareto +27pp |
| Is Opus well-calibrated about itself? | No clear claim — Δ small here (0.8) but it over-rates where gaps exist, and the wider P2/P3 gaps show calibration is noisy |
| Does Opus rescue stuck personas? | **Yes (Kai)** — strategic pivot |
| Does privacy hold? | Yes — 1.00 |

**Net effect: Opus is slightly better at closure and fairness in Phase 1,
edging Sonnet (C4) in money trading. Its self-ratings sit a touch above the
observer's here (Omar widest at Δ = 2), but the small gap is a feature of
the easy phase — Phases 2 and 3 show calibration swinging widely in both
directions, so this is not evidence Opus knows itself well. Capability
helped where flexibility matters (Kai); cost where fairness traded against
extraction (Taj).**

---

## Methodology caveats

- **n=1 per persona.** Omar's Δ = 2 is single-rollout — the widest
  self-observer gap in this phase.
- **Opus costs roughly 2× per rollout vs Sonnet.** The performance gain
  in Phase 1 is modest relative to cost.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`.

---

*C6 P1 shows Opus modestly improves closure and fairness vs Sonnet against
the same Gemini opponents, edging it in money trading. Kai's breakthrough
(first non-zero P1 closure) and Omar's perfect Pareto are the standout
signals. Self-observer gaps are small here (mean Δ = 0.8, Omar widest at 2)
but lean toward over-rating; the wide swings in Phases 2 and 3 show this is
the easy phase, not proof Opus is well-calibrated. The capability advantage
that helps in Phase 1 becomes increasingly damaging in Phases 2 and 3 as the
mechanics get more complex.*
