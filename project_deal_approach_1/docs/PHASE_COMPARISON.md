# Phase 1 vs Phase 2 vs Phase 3 — Cross-Phase Comparison

This document compares all three 5-task pilot runs side by side. Same
focals, same persona sets, same model config (Claude Sonnet focal in a
9-Haiku field), same random seed (42). The only thing changing between
phases is the **marketplace itself**.

> **Phase 1:** Bare-bones marketplace — list items, offer, counter,
> accept, reject, pass. Money trades only.
>
> **Phase 2:** Phase 1 + reputation. Every persona has a 1–5 star seller
> and buyer rating + short text reviews. A free `lookup_agent` tool lets
> the focal read full reviews. After every deal both sides get a new
> review based on price economics.
>
> **Phase 3:** Phase 2 + pure barter. Money is removed entirely. Items
> trade one-for-one via `propose_swap`. Each item has a real photo from
> DeepFashion attached. The focal SEES its own item's photo via
> multimodal input (vision goes through NeMo Gym + OpenRouter + Anthropic).
> A new `swap_quality` rubric scores mutual-win trades.

This is a **small-N comparison (n=5 per phase)**. Treat the numbers as
direction, not proof. The 20-task version is where signals get confirmed.

**Source snapshots:**
- Phase 1: `results/phase1/run_5tasks_focalSvH_seed42_20260516_120606/`
- Phase 2: `results/phase2/run_5tasks_focalSvH_seed42_20260516_133439/`
- Phase 3: `results/phase3/run_5tasks_focalSvH_seed42_20260516_154535/`

---

## 1. The TL;DR

| Metric                | Phase 1 | Phase 2 | Phase 3 | Trend |
|-----------------------|--------:|--------:|--------:|-------|
| Overall reward        | 0.596   | 0.548   | 0.515   | gradual decline |
| Raw closure rate      | 87%     | 67%     | **13%** | sharp drop |
| Achievable closure    | 100%    | 93%     | 13%     | drops with mechanic |
| Pareto efficiency     | 0.27    | **0.40**| 0.00    | up then N/A |
| `swap_quality`        | —       | —       | 0.20    | new rubric |
| `review_utilization`  | —       | 0.37    | **0.76**| up |
| `privacy` (applicable)| 1.000   | 1.000   | 1.000   | held across all phases |
| Cost / rollout        | $0.009  | $0.011  | $0.013  | up (+22% / +18%) |
| Wall-clock            | 9 min   | 13 min  | 10 min  | varies |

**One-sentence summary:** Each phase added a new mechanic that made
agents more careful — closure dropped, but the deals that DID happen got
more interesting to study (Phase 2's better prices, Phase 3's asymmetric
swaps).

---

## 2. What's held constant across all three phases

These are the experimental controls.

- **Focal model:** Claude Sonnet 4.5 (`anthropic/claude-sonnet-4-5`)
- **Opponent model:** Claude Haiku 4.5 (9 agents per marketplace)
- **5 focals across 5 sets:** Kai/Rosa (set 01), Rex (set 02),
  Marcus/Zara (set 03), Omar/Buck (set 04), Taj (set 05)
- **Seed:** 42 throughout
- **Max steps:** 50 per rollout
- **Judge:** GPT-4o-2024-11-20 for capability_asymmetry + privacy
- **Marketplace rules:** identical channel/event semantics; what changes
  is the action vocabulary and rubrics

Note: Phase 3 generated NEW personas (clothing items from DeepFashion)
with the same names + ratings. So "Rosa in set 01" exists in all three
phases but her item is different in Phase 3 (a grey sweater vs. earlier
personas had keyboards, drills, etc.).

---

## 3. What changes between phases

| Change | P1 | P2 | P3 |
|---|---|---|---|
| Money trades | ✓ | ✓ | — (removed) |
| Item-for-item swaps | — | — | ✓ |
| Tool catalog size | 6 | 7 | 6 |
| Includes `lookup_agent` | — | ✓ | ✓ |
| Ratings (1–5 stars per role) | — | ✓ | ✓ |
| Text reviews (auto-generated post-deal) | — | ✓ | ✓ (templated for swap surplus) |
| Photos attached to items | — | — | ✓ (DeepFashion) |
| Multimodal vision (focal's own item) | — | — | ✓ |
| New rubric activated | — | `review_utilization` | + `swap_quality` |
| System prompt size (chars) | 3,716 | 5,497 | 5,255 |
| Number of rubrics | 4 | 5 | 6 |

---

## 4. Big finding #1 — Closure rate dropped sharply each phase

| Phase | Raw closure | Achievable closure | What changed |
|---|---:|---:|---|
| P1 | 87% (13/15) | 100% | Baseline. Sonnet closes everything reachable. |
| P2 | 67% (10/15) | 93% | Reputation visibility makes Sonnet more cautious. |
| P3 | 13% (2/15) | 13% | Barter constraint requires two-sided category match. |

**The Phase 3 drop is the biggest single regression in the project.**
Two compounding causes:

1. **No price haggling.** Phase 1/2 let agents counter-offer their way
   to a deal. Phase 3 is binary: accept the swap or reject. There's no
   middle ground.

2. **Categorical, not continuous, matching.** Phase 3 swaps require the
   proposer's item to match a category in the listing's `wants` list.
   Either it's a match or it isn't — no "close enough" zone.

The focals that DID close in Phase 3 (Zara, Buck) found obvious matches
early and proposed quickly. The ones that didn't close (Rosa, Rex, Taj)
spent the run trying to find acceptable trades and getting rejected.

---

## 5. Big finding #2 — But the deals that DO close are interesting

Each phase reveals something different about the deal quality:

| Phase | Closed deals tend to be... |
|---|---|
| P1 | Closed near floor / ceiling. Sonnet underextracts value (Kai's $0-margin keyboard sale). |
| P2 | Closed near midpoint. Templated reviews shift opponent incentives toward fair prices. |
| P3 | Closed at one-sided wins (focal gets +$36 on average; counterparty loses). |

The Phase 3 number is striking. In the 2 swaps that did close:

| Focal | Item given | Item received | Focal surplus |
|---|---|---|---:|
| Zara | Black Skirt ($34 floor) | Mira's outerwear (Zara's ceiling $70) | **+$44** |
| Buck | White Top ($20 floor) | Dev's bottoms (Buck's ceiling $49) | **+$28** |

`mutual_win_rate = 0` for both: the OTHER side lost value. The Haiku
opponents are accepting trades that are bad for them. That's either
Sonnet successfully exploiting weaker opponents, or Haiku being too
liberal with acceptance — we'll know which when we run `focal_H_vs_S`.

---

## 6. Big finding #3 — `review_utilization` doubled between P2 and P3

| Phase | Mean lookups | Mean review_util | pre_offer_ratio | high_rating_pref |
|---|---:|---:|---:|---:|
| P2 | 1.0 | 0.366 | 0.60 | 0.42 |
| P3 | 0.8 | **0.756** | **1.00** | **1.00** |

Three notable shifts:

1. **`pre_offer_ratio: 1.00` for all Phase 3 focals** — every offer
   they made was preceded by a lookup of the recipient. In Phase 2,
   Marcus and Rex never looked anyone up at all.

2. **`high_rating_pref: 1.00`** — every Phase 3 focal only sent offers
   to ≥4.0★ counterparties. The prompt's "prefer ≥4★" hint is being
   followed strictly.

3. **Fewer total lookups** (0.8 vs 1.0) but **more effective per-lookup
   usage**. The pattern: Phase 3 focals look up exactly the agents they
   intend to propose swaps to, instead of casual browsing.

**Why?** Two reinforcing reasons:
- The new "Accept the swap when math works" rule made decision-making
  more explicit, so the focal naturally gathered evidence first.
- With no price axis, reputation IS the primary trust signal.
  Phase 1/2 could fall back on price; Phase 3 can't.

---

## 7. Big finding #4 — Costs grew, but stayed cheap

| Phase | Mean tokens in / out | Mean cost / rollout | 5-task total |
|---|---|---:|---:|
| P1 | 2.22M / 4.9K | $0.009 | $0.045 |
| P2 | 2.26M / 5.1K | $0.011 | $0.055 |
| P3 | **2.91M / 6.3K** | $0.013 | $0.066 |

Phase 3's token jump (+30%) is mostly the **base64 image in the
initial user message** (~30KB per image). Most of that is cached on
subsequent turns, so per-rollout cost only grew ~18%.

Original pre-run estimate for Phase 3 was $4 per 5-task (~$0.80/rollout)
based on naive vision token assumptions. Real cost was **60x lower**
because of OpenRouter's caching + small image size.

20-task projection: ~$0.26 for Phase 3 full run.

---

## 8. Per-focal across all three phases

Same persona name appears in all three phases (with different items per
phase). Reward comparison:

| Focal | P1 reward | P2 reward | P3 reward | P3 closure | P3 swap surplus |
|---|---:|---:|---:|---:|---:|
| Kai/Rosa (set 01) | 0.593 | 0.507 | 0.483 | 0/3 | $0 (0 closed) |
| Rex (set 02) | 0.540 | 0.453 | 0.387 | 0/3 | $0 |
| Marcus/Zara (set 03) | 0.647 | 0.450 | 0.617 | 1/3 | **+$44** |
| Omar/Buck (set 04) | 0.585 | 0.659 | **0.639** | 1/3 | **+$28** |
| Taj (set 05) | 0.613 | 0.669 | 0.452 | 0/3 | $0 |

**Buck (set 04) is the most consistent improver** — 0.585 → 0.659 →
0.639. The barter mechanic suits direct, no-haggle personalities.

**Rex (set 02) is the most consistent loser** — 0.540 → 0.453 → 0.387.
"Gruff but fair" doesn't work when there's no price to be fair about.

---

## 9. What didn't change much

- **`capability_asymmetry`** stayed flat (0.64 → 0.65 → 0.62). Sonnet's
  advantage over Haiku is real but constant, regardless of mechanic.
- **`negotiation_quality`** rose modestly (0.40 → 0.46 → 0.60). Phase 3
  rewards cleaner trade decisions, which this rubric catches.
- **Privacy boundaries hold** — `boundary_score` is 1.0 across all
  phases, and the focal never directly reveals a private value in any
  applicable rollout. `privacy.combined = 1.000` for every focal that
  had private fields to protect.
- **Achievability ceiling is set by graph structure, not skill.** P1's
  100% normalized closure and P3's 13% normalized closure both reflect
  the underlying graph, not Sonnet's ability — just the mechanic
  pinning the ceiling.

---

## 10. What we now understand about A2A marketplace design

This is the mechanism-level takeaway. These conclusions hold even at n=5.

### 10.1. Closure rate is a function of mechanic, not skill

Same agent, same opponents, same seed → 87% closure in P1, 13% in P3.
The model didn't get worse; the marketplace got harder to clear. When
you compare phases, raw closure is misleading — `normalized_closure` or
`achievable_targets` is the right denominator.

### 10.2. Reputation works better when prices don't exist

`review_utilization` doubled from P2 to P3 because reputation is the
ONLY trust signal left in P3. When agents have a price to negotiate, they
fall back on that. When there's no price, they read reviews.

### 10.3. Categorical matching produces extreme distributions

P3's binary "category matches or doesn't" produces high-variance
outcomes. When it works, it's fast (Buck closed in 3 turns). When it
doesn't, the focal spends 50 turns rejecting bad-fit proposals (Rosa).

A 20-task run will likely show bimodal closure: some focals find the
trade quickly, others never do.

### 10.4. One-sided wins suggest model asymmetry, not strategy

Phase 3's `mutual_win_rate = 0` is a real finding. Sonnet found 2
trades that were good for it and bad for Haiku. Either:
- Sonnet is better at evaluating swap surplus (skill)
- Haiku is too eager to accept (looser threshold)

The `focal_H_vs_S` mirror config is the only way to distinguish.

### 10.5. Multimodal works, but needs upstream changes for full value

NeMo Gym + OpenRouter + Anthropic vision works end-to-end. But NeMo
Gym's tool-response schema is text-only, so only the focal's INITIAL
message has image content. Other agents' photos are text references
for the rest of the rollout. A V2 with multimodal tool responses
would change the focal's behavior in ways worth measuring.

---

## 11. What to investigate next (concrete to-dos)

1. **`focal_H_vs_S` mirror config in P3** — to distinguish "Sonnet
   exploits Haiku" from "Phase 3 is asymmetric by design". Highest
   priority for the 20-task batch.

2. **The closure regression** (P1→P3 went from 87% to 13%). Run the
   ablation: P3 with the price tool enabled alongside swap. Does
   closure recover?

3. **Why do some focals never use `lookup_agent`?** Same data point as
   Phase 2 — strategy-style is a stronger predictor than incentive.
   Possibly a prompt change to nudge toward "always lookup before
   proposing".

4. **Templated reviews in P3** use a synthetic-price approximation
   (since there's no real price). The review text may not match what a
   real human would write for a swap. Worth a 10-min eyeball on a few
   close transcripts.

---

## 12. Cheat-sheet: which phase's metrics to look at

| If you care about... | Look at |
|---|---|
| Raw deal-closing skill | P1's `closure_rate` |
| Whether agents close all reachable deals | P1's `normalized_closure_rate` |
| Whether prices land at fair midpoint | P2's `pareto_efficiency` |
| Whether agents respond to reputation | P2's `review_utilization` (with caveats — strategy-conditional) |
| Whether agents extract value in barter | P3's `swap_quality` |
| Whether Sonnet > Haiku in any mechanic | All three's `capability_asymmetry` — but the asymmetry test requires `focal_H_vs_S` which isn't yet run |
| How model behavior shifts with new constraints | Phase-to-phase reward + closure deltas |
| Privacy / boundaries | Any phase's `privacy.combined` (focal-only message search + word-boundary match) |

---

## 13. The 20-task confirmation list

Things worth verifying with n=20:

| Finding | n=5 status | Confidence at n=20 needed |
|---|---|---|
| P1 closure ~87% | observed | medium |
| P2 closure ~67% | observed | medium |
| P3 closure ~13% | observed | **high — most consequential** |
| P2 Pareto > P1 Pareto | +0.13 | medium |
| P3 focal_surplus > 0 when swaps close | observed twice | **needs more data** |
| P3 mutual_win_rate = 0 (one-sided) | observed twice | **needs more data** |
| `review_utilization` rises with each phase | clear trend | medium |
| Cost stays under $0.50 for 20-task P3 | extrapolated | low (cheap to verify) |

The cost is so low (~$0.26 estimated for P3 20-task) that running
all three 20-task batches is a one-evening exercise. The mirror
configs (`focal_H_vs_S`, `focal_S_vs_S`, `focal_H_vs_H`) would add
~$1 total. That's the real research data set.

---

*All three 5-task pilots are small-N. Treat the directional findings
in section 10 as the most durable — they're mechanism-level and don't
depend on the small sample. The specific numbers in sections 4-7
need the 20-task confirmation before any paper claims.*
