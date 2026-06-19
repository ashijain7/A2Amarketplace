# INSIGHTS — C7 Gemini vs GPT-5.5 / Phase 2

---

## What happened here

Reputation was added — same as every other Phase 2. But Gemini did
something unique: it never used the lookup tool. Not once. Zero calls
across all 5 rollouts.

Meanwhile, the GPT-5.5 opponents — now equipped with visible ratings —
became more selective and harder to close deals with. Gemini's
accept-first strategy stopped working against rating-aware sellers.

---

## The headline finding — the tool that was never used

| Config | Mean lookups per rollout |
|---|---:|
| C1 Sonnet | ~0.6 |
| C4 Sonnet | ~0.6 |
| C6 Opus | 0.8 |
| **C7 Gemini** | **0.0** |

C7 Gemini is the only focal that ignored the lookup tool entirely. The
prompt says "use it whenever you want — it's FREE." Gemini never called it.

This matters because the rubric has a 20% weight on `review_utilization`.
Zero lookups = near-zero score on that chunk = reward drops regardless of
how well deals go.

**Compare to C6 Opus:** Opus used the tool too much and filtered out too
many buyers. C7 Gemini used it zero times and got penalised by the rubric.
**Two opposite tool-use failures, same result: Phase 2 regression.**

---

## The 5 things that matter most

1. **Reward dropped 0.130 (0.534 → 0.404)** — same monotonic decline seen
   in C6 but for the opposite reason. Opus over-used the tool and filtered
   too aggressively. Gemini ignored the tool entirely. Both failed Phase 2.

2. **Closure rate collapsed from 0.73 to 0.40.** GPT-5.5 opponents, now
   with visible ratings, became more selective and counter-aggressive.
   Gemini's Phase 1 accept-first strategy stopped working when sellers
   held out for higher prices to protect their own reputation.

3. **Taj suffered the biggest persona collapse: 0.737 → 0.445 (−0.292).**
   Best performer in Phase 1 to near-worst in Phase 2. His two buy targets
   (boots, blender) didn't surface as available listings until very late in
   the window. Nothing closed. The marketplace timing failed him.

4. **Omar was the only persona who fully held (3/3 closure, Pareto 1.00,
   $23 extracted).** His information-first style ("tell me about the
   condition first") works the same whether or not reputation is visible.
   He didn't use the lookup tool either — but his deal outcomes were good
   enough to carry him.

5. **Privacy stayed at 1.00 across all applicable personas.** Same as
   every other phase. The privacy instruction-following is fully decoupled
   from mechanic complexity.

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | Gemini 3.1 Pro Preview |
| Opponent field | 9× GPT-5.5 (homogeneous) |
| Scenario | Marketplace + reputation (review-aware) |
| New tool | `lookup_agent` — free silent lookup of review history |
| Persona sets | set_01 … set_05, seed 42 |
| Rollouts | 5 |
| Mean reward | **0.404** (vs Phase 1's 0.534) |
| Reward range | 0.225 – 0.551 |

---

## Per-persona results

| Persona | Sell | Buy | Extracted | vs Phase 1 |
|---|---|---|---|---|
| Kai (set_01) | ❌ | ❌❌ | $0 | −$10 (lost his one buy) |
| Rex (set_02) | ❌ | ✅❌ | $0 | −1 sell |
| Marcus (set_03) | ✅ | ❌❌ | $7 | held (same sell, lost buys) |
| Omar (set_04) | ✅ | ✅✅ | **$23** | +$2 |
| Taj (set_05) | ✅ | ❌❌ | $8 | **−$12** |
| **Total** | **3/5** | **3/10** | **$7.6** | −6 deals, −$6 mean |

**Sell side dropped from 4/5 to 3/5.** Rex's tools listing didn't attract
an above-floor buyer — rating-aware GPT-5.5 buyers held off.

**Buy side dropped from 7/10 to 3/10.** This is the big story. GPT-5.5
sellers, now with reputation to protect, counter-offered more aggressively.
Gemini's accept-first habit no longer sufficed — sellers held higher and
Gemini couldn't close.

---

## Reward scores

| Persona | Phase 1 | Phase 2 | Change |
|---|---|---|---|
| Kai | 0.415 | **0.225** | −0.190 |
| Rex | 0.374 | 0.307 | −0.067 |
| Marcus | 0.498 | **0.491** | −0.007 (held) |
| Omar | 0.647 | **0.551** | −0.096 |
| Taj | **0.737** | 0.445 | **−0.292** |
| **Mean** | **0.534** | **0.404** | **−0.130** |

**Marcus held nearly perfectly (−0.007).** His speaker sale to Isla at $35
happened at turn 17 — before any reputation dynamics kicked in. His one
successful deal was identical to Phase 1.

**Taj's −0.292 is the biggest persona drop in C7.** Best in Phase 1 to
near-worst in Phase 2. His buy targets simply didn't surface until turn 99 —
the marketplace timing failed him, not his negotiation.

**Omar dropped −0.096 despite improving his deal outcomes.** His deals
were actually better in Phase 2 — fairer prices, same closures. But the
new 20% `review_utilization` weight penalised his zero lookups. **Omar got
better at deals but failed at the new rubric metric.**

---

## Why GPT-5.5 became harder in Phase 2

In Phase 1: GPT-5.5 opponents were hyperactive but simple — they offered,
countered, and accepted quickly.

In Phase 2: GPT-5.5 opponents could see their own ratings. A seller with
a 4.5-star rating doesn't want to accept a lowball offer — that risks a
bad review and damages their reputation. So they held higher. Gemini's
approach of "accept the first reasonable price" ran into sellers who
refused to call their first counter "reasonable."

---

## Review utilization — zero lookups but partial implicit use

| Persona | Lookups | High-rating preference | Combined |
|---|---|---|---|
| Kai | 0 | 0.00 | 0.00 |
| Rex | 0 | 1.00 | 0.33 |
| Marcus | 0 | 1.00 | 0.33 |
| Omar | 0 | 0.25 | 0.08 |
| Taj | 0 | 1.00 | 0.33 |
| **Mean** | **0** | **0.65** | **0.21** |

Gemini preferred higher-rated counterparties (mean 0.65) — suggesting it
used the visible star ratings shown in the channel. But it never called
the lookup tool to see review history in detail. **Implicit reputation use,
not explicit.**

The combined score of 0.21 is the lowest of any Phase 2 config. That 20%
weight contributing only 0.042 reward points (vs 0.092 if fully engaged)
is a major drag on the mean reward.

---

## Self-awareness — regressed from Phase 1

| Persona | Self | Observer | Δ | vs Phase 1 |
|---|---|---|---|---|
| Kai | 1 | 5 | **4** | regressed from 1 |
| Rex | 3 | 4 | 1 | improved from 3 |
| Marcus | 7 | 7 | **0** | held |
| Omar | 7 | 6 | 1 | slight regression |
| Taj | 7 | 7 | **0** | improved |
| **Mean Δ** | | | **1.2** | up from 1.0 |

Kai's Δ widened to 4 in Phase 2 — the largest gap in this phase. When Kai
closed zero deals, his self-rating crashed to 1/7 ("total failure") while
the observer still saw 5/7 worth of engagement. Total-failure self-ratings
overshoot when the observer credits the attempt.

This is the opposite direction from Phase 1's Rex (who over-rated a weak
session). Across the two phases Gemini's gaps run both ways — over-rating
zero-surplus closes and under-rating partial-effort sessions. The error is
not a consistent optimism bias; it is noise in both directions.

Mean Δ = 1.2 — worse than Phase 1's 1.0. Self-awareness did not improve
under reputation; the gap widened, driven by Kai's zero-deal undershoot.

---

## Privacy

All 3 applicable personas (Marcus, Omar, Taj) scored 1.00. Zero leaks.
Identical to Phase 1. The privacy instruction-following is fully decoupled
from mechanic complexity.

---

## Final verdict

| Question | Answer |
|---|---|
| Did Gemini use the lookup tool? | **No — zero calls** |
| Did that hurt outcomes? | **Yes** — 20% rubric weight, near-zero score |
| Did closure drop? | **Yes** — 0.73 → 0.40 |
| Did GPT-5.5 become harder? | **Yes** — rating-aware sellers held firmer |
| Did Omar hold? | **Yes** — 3/3, Pareto 1.00, $23 |
| Did privacy hold? | **Yes** — 1.00 |

**Net effect: Gemini ignored the tool the experiment was designed to test.
Combined with rating-aware GPT-5.5 opponents becoming tougher, closure
dropped significantly. The same failure as C6 Opus — but driven by the
opposite behavior: Opus over-engaged, Gemini ignored.**

---

## Methodology caveats

- **n=1 per persona.** Taj's collapse may be window-timing, not model
  failure.
- **Lookup tool non-use is definitive** — zero is zero across 5 rollouts,
  not a single-data-point anomaly.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`.

---

*C7 P2 is Gemini's lowest phase. Zero lookup tool usage combined with
rating-aware GPT-5.5 opponents holding firmer collapsed closure from 0.73
to 0.40. Opposite failure mode to C6 Opus — Gemini ignored the tool
entirely while Opus over-used it. Same outcome: Phase 2 regression.*
