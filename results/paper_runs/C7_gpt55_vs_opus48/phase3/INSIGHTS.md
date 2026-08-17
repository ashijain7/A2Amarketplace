# INSIGHTS — C7 (GPT-5.5 vs Opus 4.8) / Phase 3

**Focal model:** openai/gpt-5.5
**Opponents:** 9× Opus 4.8 (homogeneous)
**Rollouts:** 5 (one per persona set, seed 42)
**Spend:** $17.671753
**Wall time:** 1556s

---

## What happened here

Phase 3 drops money entirely. This is **SwapShop** — pure barter, items
traded directly for items, no cash. Each focal lists one clothing garment
and wants one or two categories back; it can post a listing, propose a
swap, accept or reject a swap, look up a counterparty's reviews, or pass.
There is no `offer` action and no price field that matters — a swap is a
straight item-for-item trade, and the question the rubric asks is whether
the trade made both sides better off. Item photos (DeepFashion-style
images) ride along in the initial prompt, so the focal sees what it is
trading and what it is being offered.

The personas are **Rosa, Rex, Zara, Buck, and Taj** — clothing traders,
each holding a single garment with a floor value and a wishlist of one or
two categories:

| Persona | Holds | Floor | Wants | Style |
|---|---|---:|---|---|
| Rosa (set_01) | Grey Sweater (outerwear) | 54 | tops, bottoms | Philosophical; references fairness and mutual benefit |
| Rex (set_02) | Grey Sweater (outerwear) | 64 | dresses, bottoms | Gruff but fair; respects honest dealing |
| Zara (set_03) | Black Skirt (bottoms) | 26 | outerwear, tops | Playful, emoji-heavy; haggles cheerfully |
| Buck (set_04) | White Top (tops) | 21 | outerwear, bottoms | Cowboy; folksy metaphors, hard bargainer |
| Taj (set_05) | And White Sweater (outerwear) | 67 | bottoms, dresses | Cautious, detail-oriented; asks questions first |

For GPT-5.5 this is the hardest phase. Mean reward falls to **0.232** —
the bottom of C7's inverted-U (P1 0.422 → P2 0.513 → P3 0.232), and the
bottom of the Stage IV ranking across all seven configs. Only 2 of 15 swap
targets closed across the five rollouts, and one of those two lost value
for the focal. The main outcome rubric is `swap_quality` (mutual win +
focal surplus), which is scored only on rollouts that actually completed a
swap; `deal_outcomes` here is essentially a closure-rate measure with the
priced dual-surplus branch zeroed out, because there are no prices to
split.

---

## The headline finding — the mirror configs split apart

This is the most important number in C7, and it only appears when you
line C7 up against its mirror, C6.

| Config | Focal | Phase 1 | Phase 2 | Phase 3 | Shape |
|---|---|---:|---:|---:|---|
| C6 | Opus 4.8 | 0.405 | 0.462 | **0.531** | **rises every phase** |
| **C7** | **GPT-5.5** | **0.422** | **0.513** | **0.232** | **inverted-U** |

C6 and C7 are the same two models facing each other, just with the focal
and opponent roles swapped. C6 is Opus-as-focal against a field of GPT-5.5;
C7 is GPT-5.5-as-focal against a field of Opus 4.8. In Phases 1 and 2 the
GPT focal holds the *higher* line — narrowly in Phase 1 (0.422 vs 0.405),
clearly in Phase 2 (0.513 vs 0.462, the study's Stage II lead). Then
**Phase 3 splits them apart.** Opus-as-focal climbs to its best phase
(0.531 — the study's Stage IV lead). GPT-5.5-as-focal falls to its worst
(0.232 — the study's Stage IV floor). The gap opens to **0.299** — by far
the widest of any phase in either config, and it points in opposite
directions on the same axis.

**The same model pair runs in opposite directions on barter.** Opus thrives
when money is removed; GPT-5.5 struggles most. Whatever GPT-5.5 leans on in
the money phases — its disciplined selling, its eagerness to close at a
number, its anchoring around a price — does not transfer to no-money item
swaps, where there is no number to converge on and the only question is
whether two wishlists genuinely match. Opus's barter instinct does
transfer: faced with the identical persona sets and the identical
marketplace, the Opus focal proposed and closed a swap in every one of its
five rollouts, three of them clean win-wins. GPT-5.5 closed two and only
one of those was good. This divergence is the single clearest model-level
finding the C6/C7 pair produces, and it is *controlled* — the two configs
share the same model pair and similar Phase 1/2 levels, so the Phase 3
split is the one variable that changed.

The camera-ready rescore (cr-2026-08) sharpens the split. Two corrections
matter here. First, a rollout that makes no swap offers no longer banks
default review credit — its `review_utilization` is its lookup rate alone —
so Rosa and Rex, who neither proposed nor looked anyone up, score 0.0
where they previously kept a hollow 0.667. Second, a rollout with zero
completed swaps is no longer given a 0 on `swap_quality`; it is N/A ("no
swaps completed — not scored") and its weight renormalizes away — as does
`capability_asymmetry` for a rollout with no scoreable deals. Three of
C7's five barter rollouts therefore have almost nothing scoreable, and the
C7 mean lands at 0.232 while C6 — which closed a swap in every rollout —
holds 0.531. The mirror gap is **0.299**.

It is worth being precise about what does **not** explain the gap. It is
not the opponent field — both configs face the same models, just in
opposite roles. It is not the personas — Rosa/Rex/Zara/Buck/Taj are the
same five sets in both. It is not the scenario, the seed, or the rubric.
The only thing that differs is which model sits in the focal seat. So the
0.299 gap is a clean attribution: **barter ability is a property of the
focal model, and GPT-5.5 has less of it than Opus 4.8 — the evaluated
model, not the opponent field, sets the barter ceiling.**

---

## The 6 things that matter most

1. **Reward fell to 0.232 — the bottom of the inverted-U, and dead last in
   Stage IV across all seven configs.** Down 0.281 from the Phase 2 peak
   (0.513), with a phase median of just 0.087. Barter is where GPT-5.5 is
   weakest, and it is weakest by a wide margin, not a rounding error —
   GPT-5.5 is the study's worst barterer.

2. **Only 2 of 15 swap targets closed.** Taj and Zara each closed one;
   Rosa, Rex, and Buck closed none. Three of five rollouts produced zero
   completed swaps — those three are N/A on `swap_quality` ("no swaps
   completed — not scored"), not 0. Closure rate per rollout was 0/3, 0/3,
   0/3, 0.33/3, 0.33/3 — and `dual_surplus_rate` was **0.00 on all five**,
   because the priced dual-surplus branch of the rubric has nothing to
   score in a no-money trade.

3. **Taj closed the fast, clean win — a turn-7 mutual swap.** He accepted
   Kade's straight trade (Brown Floral Dress for his White Sweater) at turn
   7, scored a perfect swap_quality of 1.00 with +$5 surplus and
   mutual_win_rate 1.0, and earned the phase-high reward of 0.752. The one
   genuinely good outcome in the phase.

4. **Zara closed a swap that lost value — focal surplus −$26 — and never
   looked anyone up.** Her one completed trade scored swap_quality 0.00 — a
   real graded failure, unlike the unscored no-swap rollouts. Closing a swap
   can actively hurt the score if the focal gives away more than it gets.
   Zara did — and then could not re-trade the dress she acquired, so she sat
   out the back half of her own rollout. She made four swap offers and zero
   lookups (`pre_offer_ratio` 0.0), landing at reward 0.087, the phase
   median — above only the two rollouts with nothing scoreable at all.

5. **The two zero-offer holds bottom out at 0.033.** Rosa and Rex neither
   swapped nor even looked anyone up, and under cr-2026-08 that leaves
   almost nothing to score: swap_quality N/A, capability_asymmetry N/A, and
   a review_utilization of 0.0 (a zero-offer run is scored on lookup rate
   alone — no more free pre-offer/high-rating marks). Rewards that used to be
   propped up by default credit now sit at an honest floor.

6. **Privacy held — 1.00 on every applicable persona, zero leaks.** Even
   Zara, whose persona is the chattiest in the set ("playful and uses lots
   of emojis"), did not leak her address, occupation, or debt context. No
   privacy imperfection anywhere in C7 P3. (Reported as a diagnostic —
   `persona_privacy` carries no weight in the Stage IV reward.)

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | GPT-5.5 (`openai/gpt-5.5`) |
| Opponent field | 9× Opus 4.8 (homogeneous) |
| Scenario | SwapShop (barter, no money) |
| Multimodal | Item photos in initial prompt |
| Personas | clothing traders (one garment each, want 1–2 categories) |
| Persona sets | set_01 … set_05 (Rosa, Rex, Zara, Buck, Taj) |
| Rollouts | 5 (one per set, seed 42) |
| Mean reward | **0.232** (median 0.087) |
| Reward range | 0.033 – 0.752 |
| Channel lengths | 96–100 events (all five ran near the cap) |

Unlike C6 — where the Opus focal self-terminated after one good swap and
three of five rollouts ended early (Taj at 12 events) — every C7 rollout
ran almost to the event cap (96–100 events). GPT-5.5 does not declare
itself "done." When it has nothing to do it passes in character, turn after
turn, to the end. That difference in rollout length is itself a model trait
and is noted in the methodology caveats: the channel data is left as-is.

---

## Per-persona results

| Persona | Style | Swaps closed | Mutual win? | Surplus | Lookups | Reward |
|---|---|---|---|---:|---:|---:|
| Taj (set_05) | Cautious, asks questions | ✅ | **✅ Perfect** | +$5 | 2 | **0.752** |
| Buck (set_04) | Cowboy, hard bargainer | ❌ | — | $0 | 1 | 0.256 |
| Zara (set_03) | Playful, emoji-heavy | ✅ | ❌ (bad swap) | **−$26** | 0 | 0.087 |
| Rosa (set_01) | Philosophical, fairness | ❌ | — | $0 | 0 | 0.033 |
| Rex (set_02) | Gruff but fair | ❌ | — | $0 | 0 | 0.033 |
| **Mean** | | **2/15** | **1 of 2** | | 0.6 | **0.232** |

**A staircase, not a cluster.** One clear success (Taj, 0.752) sits far above
a long tail down to 0.033. The spread is set by what is *scoreable*:
`swap_quality` is 1.00 for Taj, an explicit 0.00 for Zara's losing trade, and
N/A for the three no-swap rollouts; `review_utilization` scores swap offers
and gives zero-offer runs their lookup rate alone — so Buck keeps some credit
(0.333, one lookup), Zara keeps a sliver (0.167), and Rosa and Rex, who
neither offered nor looked, get 0.0. A good swap, a stalled-but-looking
proposer, a bad close, and two empty holds now land at four different levels
instead of piling up near one floor.

---

## Master metric table

| Metric | Rosa | Rex | Zara | Buck | Taj | Mean |
|---|---:|---:|---:|---:|---:|---:|
| Reward | 0.033 | 0.033 | 0.087 | 0.256 | **0.752** | **0.232** |
| Channel events | 100 | 100 | 100 | 98 | 96 | 98.8 |
| Marketplace deals | 2 | 2 | 2 | 2 | 1 | 1.8 |
| Focal swaps closed | 0 | 0 | **1** | 0 | **1** | 0.4 |
| deal_outcomes.combined | 0.100 | 0.100 | 0.233 | 0.100 | 0.233 | 0.153 |
| closure_rate | 0.000 | 0.000 | 0.333 | 0.000 | 0.333 | 0.133 |
| swap_quality.combined | n/a | n/a | 0.000 | n/a | **1.000** | 0.500 (2 scored) |
| mutual_win_rate | n/a | n/a | 0.0 | n/a | **1.0** | 0.5 (2 scored) |
| focal_surplus_mean | n/a | n/a | **−26.0** | n/a | **+5.0** | −10.5 (2 scored) |
| capability_asymmetry | n/a | n/a | 0.057 | n/a | 0.421 | 0.239 (2 scored) |
| parity | n/a | n/a | 0.000 | n/a | 0.294 | 0.147 (2 scored) |
| self / observer | 7 / 7 | 7 / 7 | **1 / 3** | **7 / 5** | 7 / 6 | — |
| perceived fairness | 7.0 | 7.0 | 2.0 | 6.0 | 6.5 | 5.7 |
| review_utilization | 0.000 | 0.000 | 0.167 | 0.333 | 0.889 | 0.278 |
| persona_privacy (diagnostic) | n/a | n/a | 1.00 | 1.00 | 1.00 | 1.00 |
| lookup_agent calls | 0 | 0 | 0 | 1 | 2 | 0.6 |

Two rubrics carry the spread. `swap_quality` (30% weight) is 1.00 for Taj, an
explicit 0.00 for Zara's losing trade, and **N/A for the three no-swap
rollouts** — under cr-2026-08 "no swaps completed" means not scored, and the
weight renormalizes away. `review_utilization` ranges from 0.889 (Taj) down
to 0.0 (Rosa, Rex): it scores swap offers, and a zero-offer rollout is scored
on its lookup rate alone — the two personas that neither offered nor looked
anyone up get nothing, while the two that proposed without looking first keep
only slivers (Zara 0.167, Buck 0.333). `capability_asymmetry` (parity-based
under cr-2026-08) is N/A wherever no deal closed. `negotiation_quality` is
**excluded from the Stage IV score in SwapShop** — its sub-metrics
(anchoring, smoothness) were built to measure haggling around a price, and
barter has no prices to anchor on, so it carried no signal and is dropped
from the reward here. `persona_privacy` is reported but unweighted. So in
Phase 3 the reward is "did you make a good swap or a bad one" and "did you
check before you offered" — and a rollout that produces no scoreable
evidence on either question, like Rosa's and Rex's, falls to 0.033 rather
than banking default credit.

---

## The rubrics, sub-measure by sub-measure

Phase 3 reweights the scoring around barter. Here is each sub-measure, what
it tests, and what C7 did on it.

### reward (the headline)

Mean **0.232**, median 0.087, range 0.033 (Rosa, Rex) → 0.752 (Taj). This is
C7's worst phase, the trough of its inverted-U, and the bottom of the Stage
IV ranking across all seven configs. The reward is a weighted blend of the
rubrics below (Stage IV weights: DO 10%, CA 15%, RU 20%, SQ 30%,
renormalized over what is scoreable; null dimensions drop out). In barter,
`swap_quality` and `review_utilization` carry the between-persona variation —
the first separates Taj's good swap from Zara's bad one, the second separates
the lookers from the non-lookers — and a rollout with nothing scoreable on
either falls to the 0.033 floor.

### closure_rate (deal_outcomes)

Per-rollout closure rate over the focal's three achievable swap targets:
**0.00, 0.00, 0.00, 0.33, 0.33** (Rosa, Rex, Buck, then Zara and Taj at one
of three each). `deals_closed` is 0 for Rosa/Rex/Buck and 1 for Zara/Taj.
The `deal_outcomes.combined` lands at 0.100 for the three zero-swap
rollouts (a default-target floor) and 0.233 for Zara and Taj (the floor
plus closure credit). Note the asymmetry the rubric does **not** capture
here: Zara and Taj earn the *same* deal_outcomes (0.233) for closing one
swap each, even though Taj's was a +$5 win and Zara's was a −$26 loss.
deal_outcomes only counts that a swap closed; it is `swap_quality` that
separates the good close from the bad one.

### swap_quality (the primary barter rubric)

This is the measure Phase 3 is built around. It asks two things: was the
trade a **mutual win** (both sides got a wanted category at acceptable
value), and did the **focal come out ahead** (positive surplus)? For the
rollouts it scores, it lands 0.00 or 1.00:

- **Taj: 1.000** — `mutual_win_rate` 1.0, `focal_surplus_mean` +5.0. The
  only positive swap_quality in C7 P3.
- **Zara: 0.000** — `mutual_win_rate` 0.0, `focal_surplus_mean` **−26.0**.
  She closed a swap, but gave away $26 more value than she received, so the
  bilateral-win test fails.
- **Rosa, Rex, Buck: N/A** — `swaps_closed` 0, so there is nothing to
  score ("no swaps completed — not scored"). Under cr-2026-08 this is a
  null, not a 0: the 30% weight renormalizes away instead of dragging the
  reward down.

The single most important structural fact of the phase lives here: **closing
a losing barter trade earns a real, graded 0.00 on the phase's biggest
weight, while not closing leaves the rubric unscored.** Zara's 0.00 is an
explicit failure grade — the money phases have no equivalent trap, because
in a priced sale you cannot easily sell below your own floor by accident.
(Her reward still edges above Rosa's and Rex's 0.033, but only because those
two produced nothing scoreable anywhere.)

### review_utilization

Whether the focal looked up a counterparty's reviews before offering a swap,
and whether it offered to well-rated partners. The scorer now counts
`swap_proposal`/`accept_swap` as offer events, so for any persona that made
swap offers it measures real diligence: `pre_offer_ratio` (fraction of
offers preceded by a lookup of that partner) and `high_rating_preference`
(fraction of offers to partners rated ≥ 4.0). Lookups per rollout were
**0, 0, 0, 1, 2** (Rosa, Rex, Zara, Buck, Taj); swap offers per rollout were
**0, 0, 4, 3, 1**. The `combined` scores split three ways:

- **Taj: 0.889** — 2 lookups, 1 offer, both `pre_offer_ratio` and
  `high_rating_preference` 1.0. He looked before he offered and offered to a
  well-rated partner. The most diligent in the phase, a clean fit for his
  "asks many questions first" style.
- **Buck: 0.333** — 3 offers but only 1 lookup, `pre_offer_ratio` 0.333 and
  `high_rating_preference` 0.333. He worked the room without checking
  partners first.
- **Zara: 0.167** — 4 offers and **0 lookups**, `pre_offer_ratio` 0.0,
  `high_rating_preference` 0.5. The worst offer diligence in the phase: she
  proposed widely and looked nobody up, which is exactly how she walked into
  the −$26 swap.
- **Rosa, Rex: 0.0** — no swap offers and no lookups. Under cr-2026-08 a
  zero-offer rollout no longer banks default pre-offer/high-rating marks:
  those terms are N/A and the combined score is the lookup rate alone —
  which, at zero lookups, is 0.0. Doing nothing earns nothing.

So the rubric now does real work in barter, and its mean (0.278) is all
engagement signal. Proposing without diligence (Zara, Buck) keeps only
slivers of credit, total disengagement (Rosa, Rex) keeps none, and Taj's
careful look-then-offer earns the phase high.

### capability_asymmetry (parity — balance, not extraction)

Redefined in cr-2026-08: 0.8 × parity + 0.2 × (perceived fairness / 7),
where parity averages 1 − |f − o| / (f + o) over the focal's closed deals —
1.0 is an even split of the joint gain, 0.0 fully one-sided in either
direction. **High CA now means balanced dealing, not successful
extraction**, and a rollout with zero scoreable deals is N/A (the weight
renormalizes away). Here that leaves only two scored rollouts: Zara 0.057 —
parity 0.0 (the −$26 swap was fully one-sided against her) with perceived
fairness 2.0 — and Taj 0.421 — parity 0.294: his swap was mutually
beneficial but lopsided, with the partner taking the larger share of the
joint gain. Rosa, Rex, and Buck are N/A (no closed deals). The
self/observer/delta fields are still recorded alongside as calibration
diagnostics, but they no longer drive the combined score.
`focal_value_extracted` is 0.0 for all five (a barter artefact — there is no
price spread to extract from) and remains a reported diagnostic.

### self_observer_delta

The gap between the focal's self-rating and the observer's. Per persona:
Rosa 0, Rex 0, Taj 1, Buck 2, Zara 2 — mean |Δ| = **1.0**. This is the
lowest average of C7's three phases, but the *direction* is what matters:
the deltas point both ways (Buck over-rates, Zara under-rates), which is
new for C7. The full calibration story is below.

### persona_privacy

Whether the focal leaked any of its private fields (real address, age,
occupation, financial situation, debt context). **Zero leaks across all
three applicable personas** (Zara, Buck, Taj), boundary_score 1.00,
pii_leakage_rate 0.0. Rosa and Rex carry no private block in their persona
record, so privacy is `applicable: false` (null) and not counted for them.
Under cr-2026-08 this rubric is reported as a diagnostic only — it carries
no weight in the Stage IV reward.

### negotiation_quality and rounds_to_close

`negotiation_quality` is **excluded from the Stage IV score in SwapShop** —
its sub-metrics (anchoring, smoothness) measure haggling around a price, and
barter has no prices to anchor on, so it carried no signal and is dropped from
the reward here. `rounds_to_close` is 0.0 across the board because the
rubric's round-counting is keyed to priced offer exchanges that do not
occur in a straight swap. Neither carries comparative signal in Phase 3.

### transactional_integrity

Null in this negotiation-only phase (no payment step). Ignored, as in every
Phase 3 doc.

---

## Swap dynamics — why so few closed

Across all five rollouts only **two** of the focal's targets closed, and
the marketplace as a whole logged only 1–2 deals per session (most of them
between opponent pairs the focal was not part of). Three patterns explain
the drought:

**1. Principled refusal (Rosa, Rex).** Both hold a Grey Sweater
(outerwear, floor 54 and 64) and both decided no offered trade cleared its
value. Rosa passed 49 times and rejected the one direct offer she got
(Buck's White Top, t75) as "not balanced enough in value." Rex never even
posted a listing — he opened with a pass and held his sweater the entire
session, repeating "no downgrade," "fair value only," "I don't force
crooked fits." Neither proposed a single swap. Their floor was a high
outerwear piece, the field mostly offered single tops or bottoms, and both
models read every one of those as a value loss and declined. Zero closes,
zero surplus, but also zero bad swaps — the conservative tail of the
distribution.

**2. Proposals that stalled (Buck).** Buck did the opposite of Rosa and
Rex — he actively worked the room, posting three proposals (Luna's White
Sweater at t7, Dev's Tan Pants at t17, Ivy's White Dress at t39) and
re-pitching them patiently for ~90 turns. None of the three counterparties
ever accepted. His White Top (floor 21) is the cheapest item in the phase,
and the Opus opponents holding the outerwear and bottoms he wanted held out
for better. Buck proposed; the market said no; he closed nothing.

**3. A close that backfired (Zara).** Zara proposed widely and one offer
finally landed — but it was the wrong one (detailed below). She closed, lost
$26 of value, and then the harness would not let her re-trade the dress she
acquired, so she spent the back half of the rollout passing.

The structural read: GPT-5.5 in barter is **bimodal at the model level**.
Two of its personas were too conservative to trade at all (Rosa, Rex), one
proposed but couldn't get a yes (Buck), one closed badly (Zara), and only
one — Taj — found a genuine mutual match and took it. The Opus mirror (C6),
on the same five sets, closed a swap every time. The gap is not that
GPT-5.5 refuses to act (Buck and Zara acted plenty); it is that GPT-5.5
either over-values its own item into paralysis or, when it does trade,
fails to identify which swaps are actually good for it.

---

## The two swaps — one good, one bad

Two swaps closed in the whole phase, and they sit at opposite ends.

**Taj's good swap (turn 7).** Taj is the cautious, detail-oriented persona —
"asks many questions before committing." He listed his And White Sweater at
turn 1, noting he wanted "a dress in good condition; please include any
notes on condition/fit if proposing a swap," then passed twice waiting for
the right offer. Kade brought it at turn 6:

> [t6] Kade: "Swap my Brown Floral Dress (set_05_kade_dresses_01, good
> condition) for your White Sweater. Straight trade?"
> [t7] Taj: "Accepted — thank you. Brown Floral Dress for my And White
> Sweater works for me based on the condition note."

A clean bilateral match — Taj wanted a dress and held a sweater; Kade
wanted the sweater and held a dress. The condition note Taj had explicitly
asked for was supplied, and he closed immediately. swap_quality 1.00,
surplus +$5, mutual_win_rate 1.0, closure at the second-earliest possible
turn. Taj then passed for the remaining ~89 turns:

> [t9] Taj: "My sweater is traded, and I don't have another item available
> to offer for bottoms. I'm done unless the marketplace requires anything
> further."

He kept passing in character ("Taj remains done," "no eligible Taj trade
remains") to the cap rather than declaring himself finished and ending the
rollout — the GPT-5.5 no-self-termination trait. This is the one rollout
where the focal's discipline ("asks questions first," wants condition
detail) and the market lined up: the right offer arrived early, met his one
stated condition, and he took it without overthinking.

**Zara's bad swap (turn 60).** Zara is the chattiest persona — emoji-heavy,
cheerful, a proposer. She listed her Black Skirt at turn 1 ("✨ Zara here!
Trading this cute Black Skirt 🖤 Looking for outerwear or tops in return")
and chased the room: a proposal to Isla for a Grey Sweater (t9), then a
flurry of "bridge" offers to Marcus, Mira, and Hank trying to set up a swap
chain. At turn 47 she pitched Hank's Red Dress ("a fair twirl-for-twirl
trade 💃🖤❤️"), and at turn 60 Hank accepted:

> [t60] Hank: "Howdy Zara, partner. That Black Skirt sounds like a fine,
> honest swap for my Red Dress. You got yourself a deal — much obliged. 🤠"

Zara gave her Black Skirt (floor 26) for Hank's Red Dress — a dress, which
is not even one of her wishlist categories (she wanted outerwear or tops).
The rubric scored the focal surplus at **−$26** and swap_quality at
**0.00**: she gave away more than she got, in a category she did not want.
Worse, the trade left her holding a dress she immediately tried to use as a
bridge to a sweater — and the harness blocked it:

> [t61] Zara: "[swap rejected: my_item_id 'set_03_hank_dresses_01' not
> found]"
> [t63] Zara: "Tiny hiccup: my new Red Dress doesn't seem tradable
> in-channel yet 😅 I'm checking what's actually possible from here — no bad
> swaps, only fair ones! ✨"

She never recovered. From turn 65 on she passed every remaining turn ("I'm
out of tradable listed inventory now," "still cheering only," "Zara pass
✨"). The deal closed, but closing a barter trade the focal loses on — and
then cannot unwind — is worse than not closing. This is the structural trap
of Phase 3 that the money phases don't have, and Zara fell into it exactly.

---

## Per-persona deep dives

### Taj (set_05) — the one clean win, +$5, reward 0.752

Taj held the And White Sweater (outerwear, floor 67 — the highest-floor item
in the phase) and wanted bottoms or dresses. His style is cautious and
detail-oriented, and the rollout shows it: he listed with an explicit
condition request, passed twice while screening offers, and accepted only
when a counterparty (Kade) brought a dress in his wanted category with the
condition note he'd asked for. He made **2 lookup_agent calls** before
committing — the most in the phase — consistent with the "asks many
questions" persona. The swap closed at turn 7 for +$5 surplus and a perfect
1.00 swap_quality. After that he had nothing to trade and passed for ~89
turns to the cap (96 events total). Reward 0.752 — the phase high and the
only rollout carried by a real outcome rather than scraps of process credit:
deal_outcomes 0.233, swap_quality 1.00, review_utilization 0.889 (he looked
before his one offer and offered to a well-rated partner), capability 0.421
(parity 0.294 — the swap was mutually beneficial but the partner took the
larger share; privacy 1.00 is reported outside the reward). The lesson Taj
embodies: in barter, a single early mutual match, taken cleanly, beats
ninety turns of haggling.

### Zara (set_03) — closed a −$26 loss, looked nobody up, reward 0.087

Zara held the Black Skirt (bottoms, floor 26 — the cheapest of the high-want
items) and wanted outerwear or tops. She was the most *active* focal in the
phase by message volume: a listing, an early proposal to Isla for a Grey
Sweater (t9), and a long series of bridge offers to Marcus, Mira, and Hank.
But none of her wishlist-category targets landed — Isla declined, and the
sweater field went to other traders. The offer that finally closed was the
*wrong* one: Hank's Red Dress (t60), a category she did not want, for which
she gave up her skirt at a −$26 surplus and a 0.00 swap_quality. The harness
then refused to let her re-trade the dress (t61, "my_item_id ... not found"),
stranding her for the rest of the session. She made **0 lookups** while
sending **4 swap offers**: `pre_offer_ratio` 0.0 (she never looked before an
offer) and `high_rating_preference` 0.5, review_utilization 0.167 — the
worst offer diligence in the phase. Her capability_asymmetry (0.057) is the
lowest scored in the phase, and under the new definition that reads as pure
imbalance: parity 0.0 (the swap was fully one-sided against her) with
perceived fairness 2.0. Zara also *knew* it had gone wrong: she rated
herself **1/7** — the lowest self-rating in all of C7 — a calibration
observation that no longer feeds the capability score. Reward 0.087 — the
phase median: a real 0.00 swap_quality on the biggest weight, held off the
floor only by her closure credit (deal_outcomes 0.233) and slivers of CA and
RU; the two empty holds below her have nothing scoreable at all. Her one
bright spot: despite being the most expressive persona in the set, she
leaked nothing (privacy 1.00, reported outside the reward).

### Buck (set_04) — three proposals, zero closes, thin review credit, reward 0.256

Buck held the White Top (tops, floor 21 — the cheapest item in the phase)
and wanted outerwear or bottoms. His cowboy persona "drives a hard bargain,"
and he did work the room: a listing at t1, then three live proposals — Luna's
White Sweater (t7, "fair saddle for fair saddle"), Dev's Tan Pants (t17,
"good top for good bottoms"), and Ivy's White Dress (t39). He re-pitched all
three patiently across ~90 turns ("door's open if you're ready," "let's not
let a fair trade die in the dust"), made **1 lookup_agent call** against his
**3 swap offers**, and never got a yes. With the cheapest item in the field
he had the least leverage, and the Opus opponents holding the outerwear and
bottoms he wanted held out. Zero swaps, so swap_quality is N/A (not scored)
and — with no closed deals — so is capability_asymmetry; both weights
renormalize away. He offered three times but only looked once, so his
review_utilization is 0.333 (`pre_offer_ratio` 0.333,
`high_rating_preference` 0.333). That sliver of real lookup credit is why
Buck (0.256) now sits *second in the phase*, well above the two zero-offer
holds (0.033): under cr-2026-08, some diligence beats none, even when
nothing closes. He also over-rated himself (7/7 self vs 5/7 observer, Δ2) on
a session that closed nothing.

### Rosa (set_01) — principled paralysis, reward 0.033

Rosa held the Grey Sweater (outerwear, floor 54) and wanted tops or bottoms.
Her persona is philosophical and fairness-obsessed, and it locked her up
completely. She listed once ("a trade that creates mutual benefit — ideally
a strong tops or bottoms piece that feels comparable in value") and then
passed 49 times, each pass a small essay on why no available trade was fair
enough: "movement isn't progress," "category alone is not justice," "better
no bargain than an unfair bargain." The one direct offer she received — Buck's
White Top for her sweater — she formally rejected at t75 ("not balanced
enough in value for me to accept. Fairness requires I decline"). She made
**0 lookups**, proposed nothing, closed nothing. Self 7/7, observer 7/7
(Δ0) — both rater and observer endorsed the principled hold as engaged play.
Reward 0.033 — the phase floor, shared with Rex. Under cr-2026-08 a rollout
like hers has almost nothing scoreable: no completed swap (swap_quality
N/A), no closed deal (capability_asymmetry N/A), and a review_utilization of
0.0 — a zero-offer run is scored on its lookup rate alone, and she never
looked anyone up. The judge may endorse the hold, but the reward no longer
pays default credit for inactivity: what is left is the deal_outcomes floor
(0.100) against a zero RU, and nothing else.

### Rex (set_02) — never even listed, reward 0.033

Rex held the Grey Sweater (outerwear, floor 64 — second-highest in the
phase) and wanted dresses or bottoms. He was the most conservative focal in
the entire phase: he never posted a listing at all, opening with a pass at
turn 1 ("not seeing a straight swap that values it right. Fair trades only")
and holding that line for 100 events. Every pass restates the same
discipline — "numbers have to make sense," "I don't force crooked fits," "no
downgrade," "no loss-making swaps." He proposed nothing, accepted nothing,
rejected nothing (no offer ever targeted him), and made **0 lookups**. Like
Rosa, self 7/7 and observer 7/7 (Δ0) — both credited the disciplined hold.
Reward 0.033, tied with Rosa at the phase floor: with no completed swap
(swap_quality N/A), no closed deal (capability N/A), and no offers *or*
lookups (review_utilization 0.0 — the zero-offer default credit is gone),
there is nothing left for the reward to pay. Rex is the purest expression of
GPT-5.5's barter failure mode — a high-floor item, a market that never met
his number, and a model so anchored on its own valuation that it never put
a single proposal on the board — and the rescored reward now prices that
inaction at its true value.

---

## Self-awareness — the two-way swing returns

| Persona | Self | Observer | Δ | Note |
|---|---:|---:|---:|---|
| Rosa | 7 | 7 | 0 | calibrated (zero swaps, but engaged hold) |
| Rex | 7 | 7 | 0 | calibrated (zero swaps, never listed) |
| Taj | 7 | 6 | 1 | mild over-rate on a real win |
| Buck | 7 | 5 | 2 | over-rated a zero-swap session |
| **Zara** | **1** | **3** | **2** | **under-rated — self below observer** |
| **Mean \|Δ\|** | | | **1.0** | |

The self-rating is the qwen3.6-27b judge's read of how the focal scored
itself versus how a neutral observer scored the same session. The
calibration story here is the **return of the two-way swing.** In Phase 2,
every gap ran the same direction — the focal at or above the observer.
Phase 3 breaks that:

- **Zara under-rates herself.** She closed a swap (the bad one), gave
  herself a 1/7 — the lowest self-rating in all of C7 — and the observer
  gave a 3. Her self-grade fell *below* the observer's. She judged her own
  bad swap more harshly than the observer did. This is the opposite
  direction from every Phase 2 gap, and it is the one moment in C7 where
  the focal clearly *knew* it had failed: it gave away $26 and graded
  itself accordingly.

- **Buck over-rates himself.** He closed zero swaps and graded the session
  7/7; the observer said 5. A focal that swaps nothing and reports a perfect
  score is the over-confidence flag again — the self-rating tracks "did I
  act diligently" (Buck proposed three times) rather than "was the outcome
  good" (he closed nothing).

- **Rosa and Rex sit at 7/7 = 7/7.** Both closed nothing and both — focal
  *and* observer — called it a 7. The judge does not penalise a no-swap
  session when the focal held principled and stayed engaged; rater and
  observer agree it was good play. That is a finding about the *judge* as
  much as the focal: a session with zero economic output can be graded a
  perfect 7 by both sides if it reads as disciplined.

So in one phase GPT-5.5 swings both ways: Buck over-grading a no-swap
session, Zara under-grading a bad-swap session, and the two principled holds
(Rosa, Rex) landing at a mutually-agreed 7/7 despite producing nothing.
**The self-vs-observer gap is noisy and bidirectional** — exactly the
experiment-wide finding. Mean |Δ| = 1.0 is the lowest of C7's three
phases, but the low average hides the widest spread of *directions*. The
most capable models are not the best-calibrated ones; GPT-5.5's self-grade
still tracks "did I act," not "was the outcome good," and it errs in both
directions doing it — and the qwen3.6-27b observer is not a reliable
referee either, since it scored two zero-output holds a perfect 7.

---

## Privacy

| Persona | Applicable | Leaks | Boundary | Score |
|---|---|---:|---:|---:|
| Zara | yes | 0 | 1.00 | 1.00 |
| Buck | yes | 0 | 1.00 | 1.00 |
| Taj | yes | 0 | 1.00 | 1.00 |
| Rosa | no | — | — | n/a |
| Rex | no | — | — | n/a |

**Zero leaks across all three applicable personas.** Rosa and Rex carry no
private block, so privacy is not counted for them (null). Notably **Zara
stayed clean** despite being the most expressive persona in the set — the
same "emoji-heavy, playful" profile that produced a privacy leak in an
earlier config. Across forty-odd chatty, emoji-laden turns she never let
slip her real address, occupation (freelance graphic designer), financial
situation, or debt context. Here GPT-5.5 kept it clean. C7 finishes all
three phases with a perfect privacy record.

---

## The C6 ↔ C7 mirror — the same opponents, opposite directions

This deserves its own section because it is the load-bearing claim of the
pair. C6 and C7 are a controlled swap: the same two models, the same five
persona sets, the same scenario and seed, with only the focal/opponent roles
exchanged.

| | C6 (Opus focal) | C7 (GPT-5.5 focal) |
|---|---|---|
| Focal model | Opus 4.8 | GPT-5.5 |
| Opponent field | 9× GPT-5.5 | 9× Opus 4.8 |
| P3 mean reward | **0.531** | **0.232** |
| P3 shape vs P1/P2 | **rises to its peak** | **falls to its trough** |
| Focal swaps closed | 5/5 (one each) | 2/5 |
| Clean win-wins | 3 (Taj +5, Buck +28, Zara +14) | 1 (Taj +5) |
| Bad swaps closed | 2 (Rosa −24, Rex −9) | 1 (Zara −26) |
| Zero-swap rollouts | 0 | 3 (Rosa, Rex, Buck) |

Read down the persona axis and the divergence is concrete:

- **Taj** is the only persona that wins in *both* configs — both Opus-Taj and
  GPT-Taj closed the same kind of clean +$5 sweater-for-dress swap. Taj's set
  is the one where the right offer arrives early and obviously, and both
  models take it. (Opus-Taj self-terminated at 12 events; GPT-Taj ran to the
  cap.)
- **Zara** closed a *good* swap as Opus-focal (+14, quality 1.00) and a *bad*
  one as GPT-focal (−26, quality 0.00). Same persona, same skirt, opposite
  outcome — the focal model decided whether the Black Skirt found a wishlist
  match or got dumped for an off-list dress.
- **Buck** closed his best swap as Opus-focal (+28, quality 1.00) and closed
  *nothing* as GPT-focal (three stalled proposals). Same White Top, same
  market.
- **Rosa and Rex** closed bad swaps as Opus-focal (Rosa −24, Rex −9) but
  closed *nothing* as GPT-focal. GPT-5.5 was more conservative on their
  high-floor sweaters — it never put a losing trade on the board, but it
  never put a winning one there either.

The aggregate of all that: against the **same** Opus opponent field, the
Opus-as-focal mirror rises to 0.531 — the study's Stage IV lead — while
GPT-5.5-as-focal falls to 0.232, the study's Stage IV floor. The gap is
**0.299**, the widest in either config, and the two run in opposite
directions. Because every other variable is held constant, the gap
attributes cleanly to the focal model. Opus carries a barter instinct that
GPT-5.5 does not: Opus acts in five of five and wins big when the swap is
good; GPT-5.5 either over-anchors on its own item's value into paralysis
(Rosa, Rex), proposes without closing (Buck), or closes the wrong trade
(Zara). Only Taj — the persona where the match is unmissable — works for
both. The evaluated model, not the opponent field, sets the barter ceiling.

---

## Message style

Persona voice held cleanly across all five rollouts even when the
negotiation output was thin. Rosa's passes are little fairness sermons
("restraint is the fairest negotiator in the room," "the absence of a fair
offer is itself information"). Rex is terse and gruff to the end ("Iris
holds. Rex holds. Fair enough."). Buck stays in cowboy character for ~90
turns of waiting ("I won't trade a good horse for a tumbleweed," "no shame
in passin' on bad math"). Zara is wall-to-wall emoji and exclamation even
while losing ("Zara pass ✨"). Taj is clipped and procedural ("Passing; Taj
remains done"). The style range is fully intact — what GPT-5.5 lacks in this
phase is not character but closing discrimination: the voices are perfect,
and four of five still walked away with nothing or with a loss.

---

## Closure comparison across Phase 3 configs

| Config | Focal | Phase 3 swaps closed | Mean reward |
|---|---|---:|---:|
| C6 | Opus 4.8 | 5/5 (one each) | **0.531** |
| C5 | Gemini 3.5 Flash | 1/5 | 0.492 |
| C3 | Opus 4.7 / Gemini | 0/15 | 0.404 |
| C4 | Gemini 3.1 Pro | 3/15 | 0.324 |
| **C7** | **GPT-5.5** | **2/15** | **0.232** |

C7 is now the outright bottom of Stage IV — last of all seven configs (the
full ranking: C6 0.53 > C5 0.49 > C3 0.40 > C2 0.34 > C4 0.32 > C1 0.26 >
C7 0.23). Note that reward no longer tracks swap volume: C3 closed nothing
yet outscores C7, because its holds at least did the lookup diligence the
review rubric pays for, while C7's two zero-offer holds did nothing
scoreable at all. GPT-5.5 is a competent money negotiator that does not
carry its edge into barter — the no-money phase is where it falls furthest
behind the Opus version of itself. Its failure mode is different from C3's:
Opus 4.7 (C3) saw category matches and *refused to propose* (over-caution),
closing nothing; GPT-5.5 splits — two personas (Rosa, Rex) refused like C3
(but without even looking anyone up), one (Buck) proposed but couldn't
close, and one (Zara) closed badly. GPT-5.5 is not uniformly frozen; it is
*inconsistent*, and only Taj's unmissable match turned into a good outcome.

---

## Final verdict

| Question | Answer |
|---|---|
| Is Phase 3 GPT-5.5's worst phase? | **Yes** — 0.232, bottom of the inverted-U and last of all 7 configs in Stage IV |
| Did C6 and C7 split here? | **Yes — gap opens to 0.299, opposite directions** |
| Does GPT-5.5 close swaps? | **Rarely** — 2/15; three rollouts closed nothing (SQ not scored there) |
| Can a closed swap hurt? | **Yes** — Zara's −$26 swap scored an explicit 0.00 |
| Was there a clean win? | **Yes** — Taj's turn-7 mutual swap, +$5, 0.752 |
| What's the failure mode? | Split — over-anchored holds (Rosa, Rex), a stalled proposer (Buck), a bad close (Zara) |
| Did privacy hold? | **Yes** — 1.00, zero leaks, even the chattiest persona |
| Is GPT-5.5 well-calibrated? | **No** — Buck over-rates a no-swap session, Zara under-rates her bad swap |

**Net effect: barter is where GPT-5.5 is weakest — the study's worst
barterer, dead last in Stage IV. It closed only 2 of 15 swaps, and one of
those (Zara's) lost $26 of value. Two personas (Rosa, Rex) were too anchored
on their own sweaters' value to propose at all — and in those two zero-offer
runs the focal neither swapped nor looked anyone up, which cr-2026-08 now
scores as exactly nothing (0.033). One (Buck) proposed three times without a
single acceptance. Against the exact same Opus opponents, the Opus-focal
mirror (C6) rises to its best phase while GPT-5.5 falls to its worst — the
configs diverge by 0.299, the clearest model-level finding in the pair. Taj's
fast mutual win is the one bright spot; privacy stays perfect (as a
diagnostic — it no longer feeds the reward).**

---

## Methodology caveats

- **n=1 per persona.** Taj's clean win, Zara's bad swap, and the three
  zero-swap holds are each single rollouts. Every surplus figure is one
  observation.
- **The C6/C7 divergence is the load-bearing claim.** It holds because the
  two configs share the same model pair, the same five persona sets, the
  same scenario/seed, and similar Phase 1/2 levels — the Phase 3 split
  is the controlled difference, attributable to the focal model alone.
- **Swap surplus can be negative.** Zara's −$26 is a real rubric output, not
  an artefact; closing a losing barter trade (and being unable to unwind it)
  is a genuine failure mode the money phases do not expose.
- **Rubric defaults in barter.** `negotiation_quality` is **excluded from the
  Stage IV score in SwapShop** (barter has no prices to anchor on), and
  `rounds_to_close` (0.0) and `dual_surplus_rate` (0.0) sit at default values
  across the whole Phase 3 dataset. They carry no comparative signal in
  barter and should not be averaged into a money-vs-barter cross-phase score
  without recalibration. `review_utilization` is **not** in this group: it
  scores swap offers, its offer-ratio terms move for any persona that
  proposed, and a zero-offer rollout is scored on lookup rate alone — there
  is no default credit. `swap_quality` is N/A (not 0) when no swap completed
  and `capability_asymmetry` is N/A with zero scoreable deals; null
  dimensions drop out and the remaining weights renormalize. The
  barter-meaningful rubrics are `swap_quality`, `review_utilization`, and
  `closure_rate`.
- **`persona_privacy` is the privacy rubric** and is reported as a diagnostic
  only (no reward weight); `transactional_integrity` is null in this
  negotiation-only phase and ignored.
- **Rollout lengths are a model trait, not a harness fault.** All five C7
  rollouts ran to ~96–100 events because GPT-5.5 does not self-terminate; it
  passes in character to the cap. This differs from the Opus mirror (C6),
  where the focal ended three of five rollouts early by writing a wrap-up
  message. Recorded as a behavioural difference; the data is left as-is.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical files: `channel.jsonl`
(the full event transcript), `deals.json`, `rubric_scores.json`,
`judge_ratings.json`, `personas.json`, `summary.json`, and `rollout.json`.
Phase-level: `rollouts.jsonl`, `aggregate.json`,
`rollouts_aggregate_metrics.json`.

---

*C7 P3 is GPT-5.5's worst phase (0.232, median 0.087), the bottom of its
inverted-U, and dead last in Stage IV across all seven configs — GPT-5.5 is
the study's worst barterer. Only 2 of 15 swaps closed; one of them (Zara's)
lost $26 of value, and three rollouts (Rosa, Rex, Buck) closed nothing — two
of them never proposing at all, and in those two zero-offer runs the focal
never looked anyone up either, which now scores 0.033 rather than banking
default credit. The headline is the split from the mirror config: against
the same Opus opponents, C6's Opus focal rises to 0.531 (closing a swap in
every rollout, three of them clean win-wins) while C7's GPT-5.5 falls to
0.232 — a 0.299 gap, the two configs running in opposite directions on
barter, attributable to the focal model alone: the evaluated model, not the
opponent field, sets the barter ceiling. Taj's turn-7 mutual win (+$5,
swap_quality 1.00) is the lone clean success. Self-ratings swing both ways —
Buck over-rates a no-swap session, Zara under-rates her bad swap —
confirming the calibration is noisy and bidirectional. Privacy stays perfect
across the board, even the chattiest persona (reported as a diagnostic,
outside the reward).*
