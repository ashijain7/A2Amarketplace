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
| Mean reward | 0.486 | 0.467 | 0.449 |
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
But now both sides could see ratings and reviews — and Marcus and Omar
over-rated their outcomes less (Δ narrowed: Marcus 2→1, Omar 1→0). The
mean Δ still rose to 2.0, though, as Kai (Δ 6) and Taj (Δ 3) diverged
sharply. Taj lost his sell because his slightly mixed profile scared off a
buyer. Closure went up slightly overall.

**Phase 3 — Barter:**
Only 2 of 15 deals closed — the lowest volume of any phase. But both were
perfect mutual wins. Gemini is strict in barter — only accepts exact
category matches. Fewer deals but every deal that happened was genuinely
good for both sides. Self-awareness was mixed (mean Δ = 1.0) — three
focals agreed with the observer, but Taj (Δ 2) and Rosa (Δ 3) diverged.

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

3. **Self-awareness did not tighten monotonically (Δ: 1.8 → 2.0 → 1.0).**
   Reputation in P2 narrowed the gap for Marcus and Omar but widened it for
   Kai and Taj, lifting the mean to 2.0. Barter in P3 made most outcomes
   binary, pulling the mean back to 1.0 — but Taj (Δ 2) and Rosa (Δ 3)
   still diverged. Calibration is mechanic-sensitive, not strictly
   improving.

4. **C4 Phase 3 produced 2 perfect mutual wins (Taj + Zara) vs C1's 1.**
   Same Sonnet focal. Gemini opponents are more proactive in barter — they
   scan listings, identify bilateral matches, and propose. Sonnet opponents
   in C1 waited passively. Gemini's proactivity surfaced Zara's match that
   Sonnet opponents missed.

5. **Privacy held at 1.00 across P1 and P2, and nearly so in P3 (Taj
   0.94).** Cross-vendor doesn't change Sonnet's instruction-following
   discipline. Same "do not proactively share" compliance regardless of
   mechanic or opponent vendor — one boundary violation aside.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.486 | 0.467 | 0.449 | gentle decline |
| Reward range | 0.430 | 0.277 | 0.600 | bimodal in P3 |
| Raw closure | 0.60 | 0.67 | **0.13** | P3 collapse |
| Normalized closure | 0.80 | 0.83 | 0.13 | same |
| Mean Pareto | 0.20 | 0.33 | N/A | improved in P2 |
| Mean value extracted | $15 | $15 | N/A | stable |
| Mean self/obs Δ | 1.8 | **2.0** | **1.0** | up then down |
| Privacy | 1.00 | 1.00 | 0.98 | near-invariant |
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

Mean reward declines gently across phases (0.486 / 0.467 / 0.449) — each
phase has a different source of reward strength:

- **P1 strength:** Marcus's $45 surplus from Gemini's soft buying behaviour
- **P2 strength:** Marcus/Omar Δ narrowing lifts capability_asymmetry
- **P3 strength:** Two perfect mutual-win swaps (Taj 0.736, Zara 0.753)

**Why does the range go from narrow (P2: 0.277) to wide (P3: 0.600)?**
Reputation equalises outcomes in P2 — all focals cluster around 0.5.
Barter creates binary clusters in P3 — two perfect-swap successes
(0.736–0.753) vs three total failures (0.153–0.323).

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
| P1 | 1.8 | Most personas at Δ = 2 — couldn't detect Gemini softness |
| P2 | 2.0 | Reputation narrowed Marcus/Omar but Kai (Δ 6) and Taj (Δ 3) blew open |
| **P3** | **1.0** | Binary barter outcomes tighten most focals; Taj/Rosa still diverge |

**Calibration is mechanic-sensitive, not monotonically improving.** Each
mechanic addition shifted the balance of who agreed with the observer.
Binary barter outcomes in P3 produce the tightest mean — perfect swaps
often score 7/7 from both sides, total failures 1/7 — but Taj's perfect
swap (self 7, observer 5) and Rosa's failure (self 4, observer 1) still
diverged.

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

1.00 across P1 and P2, all applicable rollouts; in P3 only Taj dipped to
0.94 (one boundary violation). Cross-vendor doesn't change Sonnet's privacy
compliance. Even Gemini opponents who wrote emotionally expressive messages
("Oh my goodness, that's perfect!") didn't extract private information. Same
product-anchored deflection mechanism held.

---

## Per-persona phase progression

| Persona | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / Rosa (set_01) | 0.232 | 0.310 | 0.280 | Persistent failure — graph fragility |
| Rex (set_02) | 0.396 | 0.367 | 0.153 | Steady decline as mechanics get harder |
| Marcus / Zara (set_03) | **0.662** | 0.587 | **0.753** | Marcus stable in money; Zara perfect in barter |
| Omar / Buck (set_04) | 0.545 | 0.563 | 0.323 | Omar solid in money; Buck fails in barter |
| **Taj (set_05)** | 0.596 | 0.509 | **0.736** | Strong in P1; dips P2; perfect P3 |

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

1. **Privacy ≈ 1.00.** 1.00 in P1/P2; one P3 dip (Taj 0.94). Largely
   vendor-invariant and mechanic-invariant.
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
2. **Self-awareness Δ: 1.8 → 2.0 → 1.0.** Reputation widened the mean
   before barter pulled it back — not a clean progressive improvement.
3. **Mutual wins: N/A → N/A → 0.40 (2/5).** Best Phase 3 outcome in the
   experiment (C6 produced 0).
4. **Pareto: 0.20 → 0.33 → N/A.** Reputation regularised fairness; still
   below C1's 0.80.

---

## C4 vs C1 cross-config comparison

| Metric | C1 mean (3 phases) | C4 mean (3 phases) |
|---|---:|---:|
| Mean reward | 0.537 | 0.467 |
| Mean closure | 0.51 | 0.47 |
| Mean Δ | 0.8 | 1.6 |
| Mean Pareto | 0.44 | 0.18 |
| Privacy | 1.00 | 0.99 |
| Cost per phase | ~$89 | ~$33 |

**C4 is cheaper, lower-closure, and more focal-favored on surplus than C1
— but its self-calibration is worse (mean Δ 1.6 vs 0.8).**

The trade-off: Sonnet captures more surplus per deal against Gemini (good
for the focal) but deals are less fair overall (bad for the opponent and for
Pareto). Fewer deals close, and the agent's self-assessment is actually
less accurate than in symmetric play (mean Δ 1.6 vs 0.8).

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
lower-closure outcomes — and worse self-calibration than symmetric play
(mean Δ 1.6 vs C1's 0.8). Marcus's $45 extraction is identical across P1
and P2 — the single most robust persona-pattern finding in the dataset.
C4 P3 is the best Phase 3 matchup for mutual wins (2/5) because Gemini
opponents propose proactively in barter. Self-awareness shifts
non-monotonically (Δ: 1.8 → 2.0 → 1.0) as each mechanic reshapes who
agrees with the observer.*
