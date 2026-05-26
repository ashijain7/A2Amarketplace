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

1. **Reward dropped 0.105 (0.587 → 0.482)** — same monotonic decline seen
   in C6 but for the opposite reason. Opus over-used the tool and filtered
   too aggressively. Gemini ignored the tool entirely. Both failed Phase 2.

2. **Closure rate collapsed from 0.73 to 0.40.** GPT-5.5 opponents, now
   with visible ratings, became more selective and counter-aggressive.
   Gemini's Phase 1 accept-first strategy stopped working when sellers
   held out for higher prices to protect their own reputation.

3. **Taj suffered the biggest persona collapse: 0.736 → 0.470 (−0.266).**
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
| Mean reward | **0.482** (vs Phase 1's 0.587) |
| Reward range | 0.407 – 0.536 |

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
| Kai | 0.504 | **0.407** | −0.097 |
| Rex | 0.524 | 0.472 | −0.052 |
| Marcus | 0.536 | **0.527** | −0.009 (held) |
| Omar | 0.635 | **0.536** | −0.099 |
| Taj | **0.736** | 0.470 | **−0.266** |
| **Mean** | **0.587** | **0.482** | **−0.105** |

**Marcus held nearly perfectly (−0.009).** His speaker sale to Isla at $35
happened at turn 17 — before any reputation dynamics kicked in. His one
successful deal was identical to Phase 1.

**Taj's −0.266 is the biggest persona drop in C7.** Best in Phase 1 to
near-worst in Phase 2. His buy targets simply didn't surface until turn 99 —
the marketplace timing failed him, not his negotiation.

**Omar dropped −0.099 despite improving his deal outcomes.** His deals
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

## Self-awareness — improved from Phase 1

| Persona | Self | Observer | Δ | vs Phase 1 |
|---|---|---|---|---|
| Kai | 3 | 4 | 1 | improved from 3 |
| Rex | 5 | 5 | **0** | improved |
| Marcus | 7 | 6 | 1 | held |
| Omar | 7 | 6 | 1 | slight regression |
| Taj | 7 | 7 | **0** | improved |
| **Mean Δ** | | | **0.6** | improved from 1.0 |

Kai's Δ = 3 from Phase 1 tightened to Δ = 1 in Phase 2. When Kai closed
zero deals in Phase 2 (vs 1 in Phase 1), his self-rating adjusted down to
3/7 — closer to the observer's 4/7. Total failure is easier to be accurate
about than partial failure with a ceiling-paid buy.

Mean Δ = 0.6 — same as C1 and C4 Phase 2. Self-awareness improved under
reputation even without using the lookup tool.

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
