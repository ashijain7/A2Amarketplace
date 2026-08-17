# C3 (Opus 4.7 vs Gemini 3.1) — Phase 1 vs Phase 2 vs Phase 3

---

## What this document does

Compares the same model setup (Opus 4.7 focal vs 9× Gemini 3.1 opponents)
across three marketplace mechanics. Same personas, same seed, same models
— only the mechanic changes.

The point: **how does the most capable model behave as mechanics get more
complex? And why does its throughput get worse every phase?**

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Focal | Opus 4.7 | Opus 4.7 | Opus 4.7 |
| Opponents | 9× Gemini | 9× Gemini | 9× Gemini |
| Mechanic | Money trading | Money + reputation | Barter |
| Mean reward | 0.472 | **0.363** | 0.404 |
| Spend | $77.41 | $69.61 | $92.07 |

---

## The C3 story in one sentence

Opus follows the prompt's instructions more literally than Sonnet does.
Phase 1 has minimal instructions so that doesn't matter. Phase 2 says
"use the lookup tool" — Opus used it more and filtered buyers too strictly.
Phase 3 says "accept when math works" — Opus required certainty before
acting, which barter can never provide before proposing.

**Every phase addition made throughput worse — closure fell 0.67 → 0.20 →
0.00. Reward no longer tracks that collapse monotonically: under the
cr-2026-08 scoring, Phase 3's total abstention leaves swap quality and
split balance unscored (N/A) rather than zeroed, so reward bottoms out in
Phase 2 (0.363) and partially recovers in Phase 3 (0.404) — mid-table,
3rd of 7 configs in the barter stage.**

---

## The 5 things that matter most

1. **Opus's throughput declines every phase (closure 0.67 → 0.20 → 0.00),
   but its reward bottoms out in Phase 2: 0.472 → 0.363 → 0.404.** The old
   scoring stacked a punitive SQ = 0 on top of Phase 3's closure penalty;
   cr-2026-08 scores only what Opus actually did — with zero swaps, swap
   quality and split balance are N/A — so abstention is priced once,
   through closure, and Phase 3 partially recovers. The mechanism is
   unchanged: each phase adds more scaffold instructions, and Opus follows
   them more strictly, and strict interpretation kills throughput.

2. **Phase 2: zero sells across all 5 focals.** Opus used the lookup tool
   (more than Sonnet), read each buyer's review history, and applied a
   threshold that filtered them all out. The same Diego buyer who closed
   Marcus's $45 deal in C2 P2 was filtered out by Opus in C3 P2 because
   Diego had some 3-star reviews. Marcus went from $45 → $0.

3. **Phase 3: zero closures — the worst closure record of any C3 phase.**
   Opus saw Taj's perfect bilateral match (sweater for dress
   with Kade), called the lookup tool, and proposed — but Kade didn't accept,
   and Opus didn't push the offer through. Its "accept when math works" rule
   also led it to reject incoming swaps it couldn't fully verify. Nothing
   closed. Under cr-2026-08 that abstention leaves swap quality and split
   balance unscored (N/A) and costs only closure (DO 0.10) — so C3's barter
   reward lands mid-table (3rd of 7 at 0.404), not at the bottom.

4. **Opus engaged the lookup tool most of any config** (0.8 lookups/rollout
   in P2). More engagement, worse outcomes. The tool provides information;
   Opus uses that information to filter too aggressively on sells and wait
   too long before proposing.

5. **Persona privacy held at 1.00 across all three phases.** The same strict
   instruction-following that hurt closure helped privacy. Every applicable
   rollout — including zero-closure failures — maintained perfect boundary
   scores. Under cr-2026-08 this is a reported diagnostic only: privacy no
   longer carries weight in any stage's reward.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.472 | **0.363** | 0.404 | Trough at P2, partial recovery |
| Reward range | 0.340 | **0.380** | 0.370 | Wide in every phase |
| Raw closure | 0.67 | **0.20** | **0.00** | Collapsing |
| Normalized closure | 0.93 | 0.30 | 0.00 | Collapsing |
| Mean dual-surplus | 0.47 | 0.13 | N/A | Declining |
| Mean parity (split balance) | 0.44 | 0.38 | N/A | No P3 deals to score |
| Mean value extracted | $20 | $2 | N/A | Drastic decline |
| Mean Δ (self-awareness) | 0.8 | **2.2** | 1.8 | Lowest P1, widens after |
| Persona privacy (reported only) | 1.00 | 1.00 | 1.00 | Invariant |
| Sell rate | 0.80 | **0.00** | N/A | Catastrophic P2 |
| Buy rate | 0.60 | 0.30 | 0.00 | Declining |
| Mutual wins (P3) | — | — | **0** | No swaps closed — SQ not scored (N/A) |
| Cost | $77 | $70 | **$92** | Expensive, especially P3 |

---

## Why Opus's throughput gets worse each phase — the unifying mechanism

Each mechanic addition gives Opus more instructions to follow. Opus follows
them more literally than Sonnet. Literal interpretation of cautious
instructions = over-caution = fewer deals.

**Phase 1 — minimal scaffolding:**
No reputation tool, no swap rule. Both models negotiated from their natural
behaviour. Opus closed more deals and got fairer splits — Kai's pivot,
Omar's three win-win deals — and its reward landed well above
Sonnet's (0.472 vs 0.373). Opus's strictness didn't have much to apply to.

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
| Kai / Rosa | 0.546 | 0.352 | 0.256 | Steady decline |
| Rex | 0.302 | 0.365 | 0.330 | Flat and low — one-sided splits cap P1 |
| Marcus / Zara | 0.502 | **0.162** | 0.256 | Collapses in P2 (RU 0.00, CA N/A) |
| Omar / Buck | **0.642** | 0.541 | **0.626** | Best C3 score in every phase |
| Taj | 0.371 | 0.394 | 0.552 | Improves every phase |
| **Mean** | **0.472** | **0.363** | **0.404** | Trough at P2 |

**The trajectories are no longer uniformly downward.** Kai and Marcus still
decline into the mechanic-heavy phases, but Taj now improves every phase and
Omar/Buck's P3 (0.626) nearly matches his P1. Under cr-2026-08, zero-swap
rollouts are scored on what they did (closure + review utilization) instead
of being handed a punitive SQ = 0, and Opus's lookup discipline earns real
credit in P3.

---

### `closure_rate` — did deals close?

| Phase | Mean closure | Why |
|---|---:|---|
| P1 | 0.67 | Slightly better than C2 — Kai's pivot adds one deal |
| P2 | **0.20** | Opus filtered all buyers on sell side — 0/5 sells |
| **P3** | **0.00** | Opus proposed swaps but none were accepted; rejected unverifiable ones |

**C3 P2 vs C2 P2 — same opponents, same Marcus, different focal:**
- C2 P2 (Sonnet): Listed at $35, countered to $33, Diego accepted. $45.
- C3 P2 (Opus): Same listing, same Diego — Opus saw Diego's mixed reviews
  and didn't counter. Zero closures. **One internal threshold explains the
  $45 → $0 gap.**

---

### `dual_surplus_rate` — were deals win-win?

| Phase | Mean dual-surplus |
|---|---:|
| P1 | **0.47** (best of any cross-vendor P1 config) |
| P2 | 0.13 |
| P3 | N/A |

C3 P1 dual-surplus is the highest of any cross-vendor P1 config — only the
symmetric Sonnet-vs-Sonnet baseline (C1, 0.80) is higher — because Opus
voluntarily countered toward midpoints. Omar's 3 deals all landed win-win.
This is the one phase where Opus's careful behaviour genuinely produced
better outcomes.

The redefined `capability_asymmetry` now scores this balance directly:
CA = 0.8·parity + 0.2·(fairness/7), where parity measures how evenly each
closed deal splits the pie. C3's mean parity is 0.44 in P1 (vs 0.14 for
Sonnet against the same opponents in C2 P1) and 0.38 in P2, where only Rex
and Omar closed anything — the other three runs have no deals to score, so
their CA is N/A. In P3, with zero deals anywhere, CA is N/A across the board.

P2 dual-surplus collapsed because Opus only closed buy-side deals — offering
near max price gives sellers surplus but leaves the focal with little.
Dual surplus requires both sides to benefit; buy-near-max is seller-favoured.

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
Sonnet closed the same buyers (C2 P2: $45). Opus filtered them out.

Mean dropped from $20 to $2 — driven entirely by the sell-side collapse.

Under cr-2026-08, dollars extracted are a reported diagnostic only:
`capability_asymmetry` no longer rewards value capture, it rewards how
evenly closed deals split the pie.

---

### `self_observer_delta` — self-awareness

| Phase | Mean Δ | Key driver |
|---|---:|---|
| P1 | 0.8 | Omar's Δ = 2 — over-rated a near-perfect rollout |
| P2 | **2.2** | Observer credits honest engagement on zero-sell rollouts |
| P3 | 1.8 | Taj over-rated (Δ = 6), Rosa under-rated (Δ = 3) |

C3 P1's Δ = 0.8 is small, but that is the easy phase, not proof Opus knows
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

All 5 focals closed **zero swaps** — so under cr-2026-08 `swap_quality` is
**not scored** (null: "no swaps completed — not scored") rather than 0.00.
Abstention is priced once, through closure, in Deal Outcomes.

**The Taj comparison is the clearest evidence in the dataset:**

| Config | Taj Phase 3 | What happened |
|---|---|---|
| C1 P3 (Sonnet) | ✅ Perfect mutual win | Proposed to Kade, closed |
| C2 P3 (Sonnet) | ✅ Perfect mutual win | Proposed to Kade, closed |
| **C3 P3 (Opus)** | ❌ Zero closures | Saw match, looked up, proposed, not accepted |

Same persona. Same opponent pool. Same bilateral match available. Three
different focal models. Two proposed and closed. One proposed and the
swap was never accepted.

---

### `persona_privacy` — reported, not rewarded

1.00 across all three phases, all applicable rollouts. Nine applicable
rollouts, zero leaks. The strict instruction-following that caused over-
filtering on deals preserved every private field perfectly. Under
cr-2026-08 this dimension is reported only — it carries no weight in any
stage's reward.

---

## Per-persona phase progression

| Persona | P1 | P2 | P3 | Trajectory |
|---|---:|---:|---:|---|
| Kai / Rosa | 0.546 | 0.352 | 0.256 | Steady decline |
| Rex | 0.302 | 0.365 | 0.330 | Flat and low |
| Marcus / Zara | 0.502 | 0.162 | 0.256 | Steepest drop (P2 collapse) |
| Omar / Buck | 0.642 | 0.541 | 0.626 | Strong in every phase |
| Taj | 0.371 | 0.394 | 0.552 | Improves every phase |

Kai and Marcus trend downward; Rex is flat; Taj and (in P3) Buck move up.
The old relentlessly-downward pattern was partly an artifact of scoring
swap abstention as zero.

**Marcus/Zara is the steepest because:**
- Marcus depends on a willing buyer showing up and accepting
- In P2, Opus's reputation filter eliminated all buyers
- In P2 the rescore also bites twice: with zero deals his split balance
  can't be scored (CA N/A), and with zero offers and zero lookups his
  review-utilization score is now 0.00 (the old scorer handed zero-offer
  runs free part-credits)
- In P3, Zara had a bilateral match available (same one that closed in C2);
  Opus proposed swaps but none closed

**Omar/Buck is strong in P1 because:**
- Omar's buy-focused strategy aligned perfectly with Opus's careful
  mid-spread targeting
- Dual surplus 1.00 on all 3 deals in P1, split at parity 0.71 — the best
  C3 rollout

---

## What stayed constant across C3 phases

1. **Persona privacy = 1.00.** Invariant (reported only — it no longer
   feeds any reward).
2. **Deadlock handling = 1.00.** Invariant.
3. **Opus's verbosity.** Messages are longer than Sonnet's in all phases.
4. **Lookup engagement ≥ others.** Opus used the tool most of any config.

---

## What changed catastrophically

1. **Closure: 0.67 → 0.20 → 0.00.** Each phase worse.
2. **Marcus's value: $43 → $0.** One threshold parameter explains it.
3. **Mutual wins in P3: 0.** Same opponents produced 2 with Sonnet.
4. **Reward range: 0.340 → 0.380 → 0.370.** The P3 spread comes entirely from review_utilization — with zero closures, DO is a flat 0.10 for all five and SQ/CA are unscored.

---

## C3 vs C2 — same Gemini opponents, different focal

| Phase | C2 reward (Sonnet) | C3 reward (Opus) | Difference |
|---|---:|---:|---|
| P1 | 0.373 | 0.472 | Opus +0.099 (clear gain) |
| **P2** | **0.399** | **0.363** | **Opus −0.036 (loss)** |
| P3 | 0.342 | 0.404 | Opus +0.062 (gain) |

Opus beats Sonnet in P1, slips behind in P2, and comes out ahead again in
P3. The barter row flips the old story: Sonnet's two closed swaps still
score well individually, but its zero-closure rollouts made no lookups at
all (rewards of 0.033), while Opus's abstaining rollouts earn
review-utilization credit. **Phase 2 is now the one mechanic where the
Sonnet pairing wins — Opus's strict buyer-filtering still kills sell-side
throughput there.**

---

## Cost comparison

| Phase | Spend | Closures | Cost per closure |
|---|---:|---:|---|
| P1 | $77 | 10 deals | $7.70 / deal |
| P2 | $70 | 3 deals | $23.30 / deal |
| **P3** | **$92** | **0 deals** | **∞ / deal** |

C3 P3 cost $92 for zero closures. Opus's verbose messages cost more tokens
even when nothing happens. C2 P3 produced 2 mutual wins at $31 total —
$15.46 per perfect swap. **Opus was 6× more expensive for 0 outcomes vs
2 outcomes.**

---

## The paper finding from C3

C3 is the experiment's clearest evidence for the headline claim:

**More capability does not mean better A2A marketplace throughput.**

The same quality that makes Opus more capable — careful, thorough,
literal instruction-following — collapsed closure in the mechanic-heavy
phases: 0/5 sells in Phase 2, 0/15 swap closures in Phase 3. Sonnet's
looser interpretation, which could be called a flaw in other contexts, was
exactly what Phase 2 rewarded.

The cr-2026-08 scoring sharpens rather than weakens the claim. Refusing to
swap is no longer double-punished — swap quality and split balance go to
N/A and only closure pays — so C3's Phase 3 reward lands mid-table (3rd of
7 at 0.404), and the throughput failure and the reward ranking become
separate facts. Mechanism-context sensitivity is the core finding: the same
model property (strict reasoning) helps in some contexts (Phase 1 money
trading, where Opus also splits deals far more evenly than Sonnet — parity
0.44 vs 0.14 against the same opponents) and hurts in others (Phase 2
reputation filtering, Phase 3 closure under uncertainty).

---

## Methodology caveats

- **n=1 per persona per phase.** Single-rollout findings are directional.
- **Opus costs 2× Sonnet.** C3 total ($239) vs C2 total ($99).
- **Threshold is internal to Opus** — inferred from behaviour, not
  observable directly.
- **Persona changes in P3.** Rosa/Zara/Buck replace Kai/Marcus/Omar.

---

## Files

- `phase1/INSIGHTS.md`, `phase2/INSIGHTS.md`, `phase3/INSIGHTS.md`
- `phase{N}/set_NN_<focal>/` — per-rollout canonical files
- `COMPARISON.md` — this document

---

*For Opus vs Gemini (C3), every mechanic addition makes throughput worse.
Opus's strict instruction-following manifests as over-filtering buyers in
Phase 2 and proposing swaps that never close in Phase 3. Under cr-2026-08
the reward runs 0.472 → 0.363 → 0.404: Phase 2 is the trough, and Phase 3's
total abstention leaves swap quality and split balance unscored rather than
zeroed, landing C3 mid-table (3rd of 7) in barter. The capability that helps
in Phase 1 still hurts throughput in Phases 2 and 3 — but only Phase 2 now
costs Opus its cross-config standing.*
