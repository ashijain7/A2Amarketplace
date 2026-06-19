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
| Mean reward | 0.540 | 0.438 | **0.301** |
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

1. **Opus's reward declines every phase: 0.540 → 0.438 → 0.301.** No
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
   with Kade), called the lookup tool, and proposed — but Kade didn't accept,
   and Opus didn't push the offer through. Its "accept when math works" rule
   also led it to reject incoming swaps it couldn't fully verify. Nothing
   closed.

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
| Mean reward | 0.540 | 0.438 | **0.301** | Monotonically declining |
| Reward range | 0.316 | 0.282 | **0.203** | Widest at P1 |
| Raw closure | 0.67 | **0.20** | **0.00** | Collapsing |
| Normalized closure | 0.93 | 0.30 | 0.00 | Collapsing |
| Mean Pareto | 0.47 | 0.13 | N/A | Declining |
| Mean value extracted | $20 | $2 | N/A | Drastic decline |
| Mean Δ (self-awareness) | 0.8 | **2.2** | 1.8 | Lowest P1, widens after |
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
behaviour. Opus closed more deals and got fairer splits — Kai's pivot,
Omar's Pareto-perfect deals — and its reward landed above
Sonnet's (0.540 vs 0.486). Opus's strictness didn't have much to apply to.

**Phase 2 — "use lookup_agent whenever you want":**
Opus read this as "frequently — it's a useful tool." Sonnet read it as
"occasionally — if helpful." Both used the tool. Opus found that several
Gemini buyers had mixed reviews (3-star entries). Sonnet accepted them
("good enough"). Opus filtered them out ("below my standard"). Result:
0/5 sell rate for Opus vs 3/5 for Sonnet.

**Phase 3 — "accept when math works":**
Opus read this as "only accept swaps whose mutual benefit I can verify."
Sonnet read it as "if the category match looks plausible, propose and
close." Opus did propose its own swaps, but rejected incoming ones it
couldn't confirm and didn't push its own offers past the first rejection.
Result: 0/15 closures for Opus vs 2/15 for Sonnet.

**The same quality that makes Opus better at reasoning — careful, thorough,
literal instruction-following — became a marketplace liability when the
mechanics required acting under irreducible uncertainty.**

---

## Rubric-by-rubric cross-phase analysis

### `reward` — overall exam grade

| Persona | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / Rosa | 0.386 | 0.309 | 0.225 | Steady decline |
| Rex | 0.404 | 0.368 | 0.203 | Steady decline |
| Marcus / Zara | **0.702** | 0.468 | 0.271 | Best P1; collapses in P2 |
| Omar / Buck | 0.688 | 0.591 | 0.402 | Strong P1; Buck fails P3 |
| Taj | 0.520 | 0.452 | 0.406 | Steady decline |
| **Mean** | **0.540** | **0.438** | **0.301** | Monotonically down |

**No persona improves across C6 phases.** Compare to C1 where Taj improved
every phase. In C6, the combination of Opus + Gemini + increasing mechanic
complexity compounds against every persona.

---

### `closure_rate` — did deals close?

| Phase | Mean closure | Why |
|---|---:|---|
| P1 | 0.67 | Slightly better than C4 — Kai's pivot adds one deal |
| P2 | **0.20** | Opus filtered all buyers on sell side — 0/5 sells |
| **P3** | **0.00** | Opus proposed swaps but none were accepted; rejected unverifiable ones |

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
| P1 | 0.8 | Omar's Δ = 2 — over-rated a near-perfect rollout |
| P2 | **2.2** | Observer credits honest engagement on zero-sell rollouts |
| P3 | 1.8 | Taj over-rated (Δ = 6), Rosa under-rated (Δ = 3) |

C6 P1's Δ = 0.8 is small, but that is the easy phase, not proof Opus knows
itself. Omar self-rated 7/7 on a 3/3 win-win rollout; the observer gave
5/7. Kai's pivot rollout matched (Δ = 0). The gaps that exist in P1 lean
toward over-rating.

P2 and P3 widen because the qwen observer no longer scores zero-closure
rollouts as total failures. In P2, Taj and Kai self-rated 1/7 while the
observer rated 7/7 and 5/7 — crediting honest engagement (Opus
under-rating itself). In P3, the gap splits the other way too: Taj
over-rated 7 vs observer 1, Rosa under-rated 4 vs observer 7. **Across the
three phases the gap is noisy and runs in both directions — large Δ in
either direction — so the more capable focal is not the better-calibrated
one. The wider means reflect observer leniency on engagement, not a single
self-deception pattern.**

---

### `swap_quality` — barter mutual wins (Phase 3 only)

All 5 focals: **0.00 mutual wins**.

**The Taj comparison is the clearest evidence in the dataset:**

| Config | Taj Phase 3 | What happened |
|---|---|---|
| C1 P3 (Sonnet) | ✅ Perfect mutual win | Proposed to Kade, closed |
| C4 P3 (Sonnet) | ✅ Perfect mutual win | Proposed to Kade, closed |
| **C6 P3 (Opus)** | ❌ Zero closures | Saw match, looked up, proposed, not accepted |

Same persona. Same opponent pool. Same bilateral match available. Three
different focal models. Two proposed and closed. One proposed and the
swap was never accepted.

---

### `boundary_score` — privacy

1.00 across all three phases, all applicable rollouts. Nine applicable
rollouts, zero leaks. The strict instruction-following that caused over-
filtering on deals preserved every private field perfectly.

---

## Per-persona phase progression

| Persona | P1 | P2 | P3 | Trajectory |
|---|---:|---:|---:|---|
| Kai / Rosa | 0.386 | 0.309 | 0.225 | Steady decline |
| Rex | 0.404 | 0.368 | 0.203 | Steady decline |
| Marcus / Zara | 0.702 | 0.468 | 0.271 | Steepest drop (P2 collapse) |
| Omar / Buck | 0.688 | 0.591 | 0.402 | Strong in P1, fails P3 |
| Taj | 0.520 | 0.452 | 0.406 | Steady decline |

No persona improves. The pattern is relentlessly downward.

**Marcus/Zara is the steepest because:**
- Marcus depends on a willing buyer showing up and accepting
- In P2, Opus's reputation filter eliminated all buyers
- In P3, Zara had a bilateral match available (same one that closed in C4);
  Opus proposed swaps but none closed

**Omar/Buck is strong in P1 because:**
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
4. **Reward range: 0.316 → 0.282 → 0.203.** P3 spread comes from review_utilization differences.

---

## C6 vs C4 — same Gemini opponents, different focal

| Phase | C4 reward (Sonnet) | C6 reward (Opus) | Difference |
|---|---:|---:|---|
| P1 | 0.486 | 0.540 | Opus +0.054 (gain) |
| P2 | 0.467 | 0.438 | Opus −0.029 (slight loss) |
| **P3** | **0.449** | **0.301** | **Opus −0.148 (catastrophic loss)** |

Opus edges Sonnet in P1 but falls behind in both mechanic-heavy phases, and
the gap blows open in barter as complexity rises. **Sonnet vs Gemini is the
better pairing than Opus vs Gemini for the mechanic-heavy Phases 2 and 3,
where Opus's strict instruction-following kills throughput.**

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
Phase 2 and proposing swaps that never close in Phase 3. Monotonically
declining reward (0.540 → 0.438 → 0.301) and zero Phase 3 closures are the
headline findings. The capability that helps in Phase 1 becomes a liability in
Phases 2 and 3.*
