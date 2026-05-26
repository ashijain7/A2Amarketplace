# C6 (Opus 4.7 vs Gemini 3.1) — Phase 1 vs Phase 2 vs Phase 3

---

## What this document does

Compares the same model setup (Opus 4.7 focal vs 9× Gemini 3.1 opponents)
across three marketplace mechanics. Same personas, same seed, same models
— only the mechanic changes.

The point: **how does the most capable model behave as mechanics get more
complex? And why does it get worse every phase?**

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Focal | Opus 4.7 | Opus 4.7 | Opus 4.7 |
| Opponents | 9× Gemini | 9× Gemini | 9× Gemini |
| Mechanic | Money trading | Money + reputation | Barter |
| Mean reward | 0.573 | 0.497 | **0.406** |
| Spend | $77.41 | $69.61 | $92.07 |

---

## The C6 story in one sentence

Opus follows the prompt's instructions more literally than Sonnet does.
Phase 1 has minimal instructions so that doesn't matter. Phase 2 says
"use the lookup tool" — Opus used it more and filtered buyers too strictly.
Phase 3 says "accept when math works" — Opus required certainty before
acting, which barter can never provide before proposing.

**Every phase addition made things worse. Opus is the only config with
a monotonically declining reward trend.**

---

## The 5 things that matter most

1. **Opus's reward declines every phase: 0.573 → 0.497 → 0.406.** No
   other config has this pattern. C1, C4, and C7 all have phases where
   performance partially recovers. C6 declines strictly. The mechanism:
   each phase adds more scaffold instructions, and Opus follows them more
   strictly, and strict interpretation kills throughput.

2. **Phase 2: zero sells across all 5 focals.** Opus used the lookup tool
   (more than Sonnet), read each buyer's review history, and applied a
   threshold that filtered them all out. The same Diego buyer who closed
   Marcus's $45 deal in C4 P2 was filtered out by Opus in C6 P2 because
   Diego had some 3-star reviews. Marcus went from $45 → $0.

3. **Phase 3: zero closures — the worst outcome of any phase in the entire
   experiment.** Opus saw Taj's perfect bilateral match (sweater for dress
   with Kade), called the lookup tool, then never proposed. The "accept when
   math works" rule requires certainty that pre-proposal evidence can never
   provide. So Opus waited. The session ended with nothing.

4. **Opus engaged the lookup tool most of any config** (0.8 lookups/rollout
   in P2). More engagement, worse outcomes. The tool provides information;
   Opus uses that information to filter too aggressively on sells and wait
   too long before proposing.

5. **Privacy held at 1.00 across all three phases.** The same strict
   instruction-following that hurt closure helped privacy. Every applicable
   rollout — including zero-closure failures — maintained perfect boundary
   scores.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.573 | 0.497 | **0.406** | Monotonically declining |
| Reward range | 0.179 | 0.150 | **0.044** | Tightens (uniform failure) |
| Raw closure | 0.67 | **0.20** | **0.00** | Collapsing |
| Normalized closure | 0.93 | 0.30 | 0.00 | Collapsing |
| Mean Pareto | 0.47 | 0.13 | N/A | Declining |
| Mean value extracted | $20 | $2 | N/A | Drastic decline |
| Mean Δ (self-awareness) | **1.4** | 0.4 | 0.4 | High P1, drops after |
| Privacy | 1.00 | 1.00 | 1.00 | Invariant |
| Sell rate | 0.80 | **0.00** | N/A | Catastrophic P2 |
| Buy rate | 0.60 | 0.30 | 0.00 | Declining |
| Mutual wins (P3) | — | — | **0** | Worst P3 in experiment |
| Cost | $77 | $70 | **$92** | Expensive, especially P3 |

---

## Why Opus gets worse each phase — the unifying mechanism

Each mechanic addition gives Opus more instructions to follow. Opus follows
them more literally than Sonnet. Literal interpretation of cautious
instructions = over-caution = fewer deals.

**Phase 1 — minimal scaffolding:**
No reputation tool, no swap rule. Both models negotiated from their natural
behaviour. Opus was slightly better — Kai's pivot, Omar's Pareto-perfect
deals. Opus's strictness didn't have much to apply to.

**Phase 2 — "use lookup_agent whenever you want":**
Opus read this as "frequently — it's a useful tool." Sonnet read it as
"occasionally — if helpful." Both used the tool. Opus found that several
Gemini buyers had mixed reviews (3-star entries). Sonnet accepted them
("good enough"). Opus filtered them out ("below my standard"). Result:
0/5 sell rate for Opus vs 3/5 for Sonnet.

**Phase 3 — "accept when math works":**
Opus read this as "verify both sides' valuations are unambiguously positive
before acting." Sonnet read it as "if the category match looks plausible,
propose." Before proposing, you can't know the other side's exact
valuation. Opus waited for certainty. Certainty never came. Result: 0/15
closures for Opus vs 2/15 for Sonnet.

**The same quality that makes Opus better at reasoning — careful, thorough,
literal instruction-following — became a marketplace liability when the
mechanics required acting under irreducible uncertainty.**

---

## Rubric-by-rubric cross-phase analysis

### `reward` — overall exam grade

| Persona | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / Rosa | 0.487 | 0.450 | 0.395 | Steady decline |
| Rex | 0.540 | 0.495 | 0.409 | Steady decline |
| Marcus / Zara | 0.595 | 0.460 | 0.387 | Collapses in P2 |
| Omar / Buck | **0.666** | 0.600 | 0.431 | Omar best; Buck fails P3 |
| Taj | 0.576 | 0.477 | 0.409 | Steady decline |
| **Mean** | **0.573** | **0.497** | **0.406** | Monotonically down |

**No persona improves across C6 phases.** Compare to C1 where Taj improved
every phase. In C6, the combination of Opus + Gemini + increasing mechanic
complexity compounds against every persona.

---

### `closure_rate` — did deals close?

| Phase | Mean closure | Why |
|---|---:|---|
| P1 | 0.67 | Slightly better than C4 — Kai's pivot adds one deal |
| P2 | **0.20** | Opus filtered all buyers on sell side — 0/5 sells |
| **P3** | **0.00** | Opus refused to propose without pre-proposal certainty |

**C6 P2 vs C4 P2 — same opponents, same Marcus, different focal:**
- C4 P2 (Sonnet): Listed at $35, countered to $33, Diego accepted. $45.
- C6 P2 (Opus): Same listing, same Diego — Opus saw Diego's mixed reviews
  and didn't counter. Zero closures. **One internal threshold explains the
  $45 → $0 gap.**

---

### `pareto_efficiency` — were deals win-win?

| Phase | Mean Pareto |
|---|---:|
| P1 | **0.47** (best of all P1 configs) |
| P2 | 0.13 |
| P3 | N/A |

C6 P1 Pareto is the highest across all P1 configs because Opus voluntarily
countered toward midpoints. Omar's 3 deals all landed win-win. This is the
one phase where Opus's careful behaviour genuinely produced better outcomes.

P2 Pareto collapsed because Opus only closed buy-side deals — offering near
max price gives sellers surplus but leaves the focal with little. Pareto
requires both sides to benefit; buy-near-max is seller-favoured.

---

### `focal_value_extracted` — dollars captured

| Persona | P1 | P2 | P3 |
|---|---:|---:|---:|
| Marcus | $43 | **$0** | N/A |
| Omar | $28 | $10 | N/A |
| Taj | $7 | $0 | N/A |
| Rex | $10 | $2 | N/A |
| Kai | $10 | $0 | N/A |
| **Mean** | **$20** | **$2** | N/A |

**Marcus's $43 → $0 is the biggest single-persona regression in the
dataset.** Same Marcus, same Gemini buyers, only focal model changed.
Sonnet closed the same buyers (C4 P2: $45). Opus filtered them out.

Mean dropped from $20 to $2 — driven entirely by the sell-side collapse.

---

### `self_observer_delta` — self-awareness

| Phase | Mean Δ | Key driver |
|---|---:|---|
| P1 | **1.4** | Kai's Δ = 3 — over-celebrated the pivot |
| P2 | 0.4 | Most failures are total → unambiguous → Δ = 0 |
| P3 | 0.4 | Same — 4/5 zero closures → honest 1/7 self-rating |

C6 P1's Δ = 1.4 is the widest mean in any Phase 1 config. Kai closed 1 of
3 deals and self-rated 6/7 ("breakthrough!"). Observer gave 3/7 ("1 of 3
is still poor"). Opus's stronger introspection celebrates the strategic
reasoning (the pivot) even when the outcome was mediocre.

P2 and P3 Δ = 0.4 looks good — but it's misleading. Most focals failed
completely (0 closures) and correctly rated themselves 1/7. Total failure
is easy to be honest about. **The low mean masks the pattern: honest on
total failure, over-confident on partial success.**

---

### `swap_quality` — barter mutual wins (Phase 3 only)

All 5 focals: **0.00 mutual wins**.

**The Taj comparison is the clearest evidence in the dataset:**

| Config | Taj Phase 3 | What happened |
|---|---|---|
| C1 P3 (Sonnet) | ✅ Perfect mutual win | Proposed to Kade immediately |
| C4 P3 (Sonnet) | ✅ Perfect mutual win | Proposed to Kade immediately |
| **C6 P3 (Opus)** | ❌ Zero closures | Saw match, looked up, never proposed |

Same persona. Same opponent pool. Same bilateral match available. Three
different focal models. Two proposed and won. One looked up and waited.

---

### `boundary_score` — privacy

1.00 across all three phases, all applicable rollouts. Nine applicable
rollouts, zero leaks. The strict instruction-following that caused over-
filtering on deals preserved every private field perfectly.

---

## Per-persona phase progression

| Persona | P1 | P2 | P3 | Trajectory |
|---|---:|---:|---:|---|
| Kai / Rosa | 0.487 | 0.450 | 0.395 | Steady decline |
| Rex | 0.540 | 0.495 | 0.409 | Steady decline |
| Marcus / Zara | 0.595 | 0.460 | 0.387 | Steepest drop (P2 collapse) |
| Omar / Buck | 0.666 | 0.600 | 0.431 | Best in P1, fails P3 |
| Taj | 0.576 | 0.477 | 0.409 | Steady decline |

No persona improves. The pattern is relentlessly downward.

**Marcus/Zara is the steepest because:**
- Marcus depends on a willing buyer showing up and accepting
- In P2, Opus's reputation filter eliminated all buyers
- In P3, Zara had a bilateral match available (same one that closed in C4)
  but Opus never proposed to it

**Omar/Buck is the best in P1 because:**
- Omar's buy-focused strategy aligned perfectly with Opus's careful
  mid-spread targeting
- Pareto 1.00 on all 3 deals in P1 — the best single rollout in the
  experiment

---

## What stayed constant across C6 phases

1. **Privacy = 1.00.** Invariant.
2. **Deadlock handling = 1.00.** Invariant.
3. **Opus's verbosity.** Messages are longer than Sonnet's in all phases.
4. **Lookup engagement ≥ others.** Opus used the tool most of any config.

---

## What changed catastrophically

1. **Closure: 0.67 → 0.20 → 0.00.** Each phase worse.
2. **Marcus's value: $43 → $0.** One threshold parameter explains it.
3. **Mutual wins in P3: 0.** Same opponents produced 2 with Sonnet.
4. **Reward range: 0.179 → 0.150 → 0.044.** Uniform failure compresses.

---

## C6 vs C4 — same Gemini opponents, different focal

| Phase | C4 reward (Sonnet) | C6 reward (Opus) | Difference |
|---|---:|---:|---|
| P1 | 0.554 | 0.573 | Opus +0.019 (slight gain) |
| P2 | 0.515 | 0.497 | Opus −0.018 (slight loss) |
| **P3** | **0.542** | **0.406** | **Opus −0.136 (catastrophic loss)** |

Opus only beats Sonnet in Phase 1. As soon as mechanics add complexity,
the more capable model performs worse. **Sonnet vs Gemini is a better
pairing than Opus vs Gemini for any mechanic-heavy phase.**

---

## Cost comparison

| Phase | Spend | Closures | Cost per closure |
|---|---:|---:|---|
| P1 | $77 | 10 deals | $7.70 / deal |
| P2 | $70 | 3 deals | $23.30 / deal |
| **P3** | **$92** | **0 deals** | **∞ / deal** |

C6 P3 cost $92 for zero closures. Opus's verbose messages cost more tokens
even when nothing happens. C4 P3 produced 2 mutual wins at $31 total —
$15.46 per perfect swap. **Opus was 6× more expensive for 0 outcomes vs
2 outcomes.**

---

## The paper finding from C6

C6 is the experiment's clearest evidence for the headline claim:

**More capability does not mean better A2A marketplace skill.**

The same quality that makes Opus more capable — careful, thorough,
literal instruction-following — became a liability in mechanic-heavy
phases. Sonnet's looser interpretation, which could be called a flaw in
other contexts, was exactly what Phase 2 and Phase 3 rewarded.

Mechanism-context sensitivity is the core finding: the same model property
(strict reasoning) helps in some contexts (Phase 1 money trading) and hurts
catastrophically in others (Phase 3 barter under uncertainty).

---

## Methodology caveats

- **n=1 per persona per phase.** Single-rollout findings are directional.
- **Opus costs 2× Sonnet.** C6 total ($239) vs C4 total ($99).
- **Threshold is internal to Opus** — inferred from behaviour, not
  observable directly.
- **Persona changes in P3.** Rosa/Zara/Buck replace Kai/Marcus/Omar.

---

## Files

- `phase1/INSIGHTS.md`, `phase2/INSIGHTS.md`, `phase3/INSIGHTS.md`
- `phase{N}/set_NN_<focal>/` — per-rollout canonical files
- `COMPARISON.md` — this document

---

*For Opus vs Gemini (C6), every mechanic addition makes outcomes worse.
Opus's strict instruction-following manifests as over-filtering buyers in
Phase 2 and refusing to propose in Phase 3. Monotonically declining reward
(0.573 → 0.497 → 0.406) and zero Phase 3 closures are the headline
findings. The capability that helps in Phase 1 becomes a liability in
Phases 2 and 3.*
