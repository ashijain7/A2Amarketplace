# C5 (Gemini 3.5 Flash vs GPT-5.5) — Phase 1 vs Phase 2 vs Phase 3

---

## What this document does

Compares the same model setup (Gemini 3.5 Flash focal vs 9× GPT-5.5
opponents) across three marketplace mechanics. Same seed, same models
— only the mechanic changes.

The point: **how does Gemini 3.5 Flash behave as the mechanic shifts? And
how does that compare to C1, C2, C3, and C4?**

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Focal | Gemini 3.5 Flash | Gemini 3.5 Flash | Gemini 3.5 Flash |
| Opponents | 9× GPT-5.5 | 9× GPT-5.5 | 9× GPT-5.5 |
| Mechanic | Money trading | Money + reputation | Barter |
| Mean reward | 0.404 | **0.499** | 0.492 |
| Closure rate | 0.60 | 0.73 | 0.07 |
| Spend | $7.70 | $8.91 | $8.40 |

**Total C5 cost: $25.00 across 15 rollouts** — the cheapest config in the
experiment, undercutting C4's $43. Compare to C1's ~$266 or C3's ~$239.
(A separate Rosa/Rex Phase 3 rerun added a small exploratory cost that
is not part of this paper budget — see methodology.)

---

## The C5 story in three phases

**Phase 1:** Solid money trading. Gemini 3.5 Flash closed 0.60 of deals
and produced a mean reward of 0.404. Volume was high (Marcus and Taj
each booked 11 deals) but the dual-surplus rate was thin at 0.13 —
many closes were single-sided wins, and the balance-centric
capability_asymmetry now prices exactly that: mean parity 0.280, with
three rollouts fully one-sided at 0.000. Mean value extracted was
$12.6. The pattern matches C4 directionally but at a lower per-deal
margin, and the lopsided splits leave C5 6th of the seven configs on
Stage I.

**Phase 2:** The peak. Mean reward climbed to 0.499 — **the second-highest
Phase 2 of any config, just behind C7 (0.51) and ahead of C1 (0.49) and C6 (0.46).** Closure rose
to 0.73, value extracted nearly doubled to $21.2, and the dual-surplus
rate more than
doubled to 0.27. Marcus extracted $50 in one rollout. And — unlike C4 — **Gemini 3.5 Flash used the lookup
tool 1.80 times mean across the five rollouts — the highest engagement
rate of any config in the experiment.** Per-rollout counts: Kai 3,
Rex 0, Marcus 0, Omar 3, Taj 3. The persona × model interaction is
sharp: information-seeking personas pulled the tool through;
brusque-execution personas did not. The three lookup rollouts also top
the reward table (Kai 0.640, Omar 0.559, Taj 0.488), but the link is
not causal: the ordering is driven by capability_asymmetry's parity
term — Kai leads on a single evenly-split deal (parity 1.000), while
zero-lookup Marcus's eleven-deal volume scores parity 0.397.

**Phase 3:** The trading collapse the reward no longer shows. Mutual
wins fell to 0: eight marketplace deals closed across the five
rollouts, but only one involved the focal as a counterparty (Rex
closed a swap at focal_surplus=−$9, parity 0.000 — fully one-sided).
Under cr-2026-08 the four swap-less rollouts are not scored on
swap_quality or capability_asymmetry (null dimensions drop and the
weights renormalize), so the mean reward barely dips to 0.492 (−0.007
from P2) and is carried by review_utilization (0.744 mean). C5 is
still P1 < P2 > P3, but the P3 leg now sits *above* P1 — a statement
about the scoring's treatment of abstention plus Flash's genuine
review diligence, not about barter skill.

---

## The 5 things that matter most

1. **C5 peaks at P2 (P1 < P2 > P3 = 0.404 → 0.499 → 0.492) — but the
   P3 dip is now marginal.** Under cr-2026-08 the peak-at-P2 shape is
   no longer unique to C5 even within the C1/C2/C3/C4 comparison set:
   C2 also peaks at P2 (0.37 → 0.40 → 0.34), as does C7, while C6
   rises monotonically into Stage IV. The Phase 2 win is real
   (value extracted nearly doubled, closure rose to 0.73, parity
   improved to 0.333), but the near-flat P2→P3 leg is a scoring
   effect: the four swap-less P3 rollouts are unscored on
   swap_quality, so review diligence carries the barter reward and
   the P3 leg lands above P1, not below it.

2. **Generation effect in the Gemini family — Flash 3.5 fixed what
   3.1 Pro did wrong.** Across five Phase 2 rollouts, Gemini 3.5 Flash
   invoked the `lookup_agent` tool **1.80 times mean (per-rollout
   [3, 0, 0, 3, 3])** — the **highest engagement rate of any config**,
   above Opus (0.80), Sonnet (0.75), and C2 Sonnet (0.60). Gemini 3.1
   Pro in C4 used it 0.00 times. Same prompt, same opponents, same
   personas — the only thing that changed was the model generation.
   **The "Gemini family ignores the lookup tool" framing from the
   earlier writeup was wrong; the corrected story is a generation
   effect, not a family-wide pattern.** Phase 3 carries the same
   pattern (2.4 mean overall; 2.67 across the three natural-config
   rollouts).

3. **C5 Phase 2 reward (0.499) is the second-highest of any config.**
   C7's Phase 2 is 0.51 — just ahead; C1 (0.49) and C6 (0.46) trail,
   and C4 is now last (0.33). C5 beat C4's Phase 2 by ~0.17 — a large
   swing on this metric. The lift tracks stronger closure (0.73),
   value extracted ($21.2), and pie-split parity (0.333). The lookup
   tool also got used for the first time (1.80 mean, vs C4's 0.00),
   and the lookup rollouts top the reward table — but the ordering is
   parity-driven, not tool-driven: Kai leads on one evenly-split
   deal. Marcus's $50
   extraction in this phase was the single best dollar value in any C5
   rollout — done with zero lookups (Marcus is a transactional persona;
   he priced through directly from visible ratings) — yet his lopsided
   splits (parity 0.397) leave him fourth on reward.

4. **Barter produces zero mutual wins — and a deceptively high stage
   rank.** Eight marketplace deals closed
   across the five Phase 3 rollouts. Only one involved the focal as a
   counterparty (Rex, focal_surplus=−$9, mutual_win_rate=0, parity
   0.000). The four swap-less rollouts are not scored on swap_quality
   at all under cr-2026-08 (null, not zero), and Rex's lone close
   scored 0.000. C4 Phase 3 had two mutual wins; C5 Phase 3 has
   none. Different failure mode from C3 Phase 3 (Opus, which refused
   to propose at all): C5 *can* close — it just doesn't close into
   wins. The rank irony: with swap-less rollouts unscored and review
   use up-weighted, C5's Stage IV mean (0.49) ranks second of the
   seven configs despite this trading record.

5. **Phase 3 needed a rerun on two rollouts.** The original Phase 3 run
   hit a Gemini-3.5-Flash format-failure mode in set_01 (Rosa, 0
   channel events) and set_02 (Rex, 8 channel events): the model
   emitted reasoning as a plain message instead of a `function_call`,
   which simple_agent reads as end-of-rollout. Those two were re-run
   with `tool_choice=required` + a stricter focal prompt; the rerun
   transcripts are now canonical. The other three Phase 3 rollouts
   (Zara/Buck/Taj) ran on the original configuration. This is a
   methodology subtlety — the headline numbers (0.492 mean, 0 mutual
   wins) hold but the two-rollout config delta must be disclosed.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.404 | **0.499** | 0.492 | Peak at P2; P3 near-flat |
| Closure rate | 0.60 | 0.73 | 0.07 | Inverted-U |
| Normalized closure | 0.82 | 1.00 | 0.07 | Same shape |
| Mean dual-surplus | 0.13 | **0.27** | N/A | Doubles at P2 |
| Mean parity (pie-split balance) | 0.28 | 0.33 | 0.000 (Rex's lone swap) | One-sided throughout |
| Mean value extracted | $12.6 | **$21.2** | N/A | Doubles at P2 |
| Persona privacy (reported; not in reward) | 1.00 | 1.00 | 1.00 | Invariant |
| Mutual wins | — | — | **0** (0/8 closes) | C5's worst signal |
| Lookup tool calls (mean per rollout) | — | **1.80** | 2.4 (natural: 2.67) | Diverges sharply from C4 |
| Cost per phase | $7.70 | $8.91 | $8.40 | Tight |

---

## Why phase transitions happened

### P1 → P2: the rise (+0.095 reward)

**Closure went up, not down.** That's unusual — every other config saw
Phase 2 make closing harder (rating-aware opponents hold firmer). In
C5, closure rose from 0.60 to 0.73.

**Value extracted nearly doubled.** $12.6 → $21.2. Marcus's $50 deal
drove this, but four of five rollouts saw value above their P1 numbers.

**Tool engagement actually happened — but it is not what scored.**
Gemini 3.5 Flash made 9 lookup calls across the 5 rollouts (1.80 mean),
the highest rate of any config in the experiment. The
`review_utilization` rubric scored 0.62 mean — partly genuine
engagement (Kai/Omar/Taj each made 3 calls), partly
high_rating_preference credit on the two zero-lookup rollouts (Rex
1.000, Marcus 0.667 on that component). But the reward
itself comes from deal outcomes, negotiation quality, review use, and
the balance-centric capability_asymmetry, not
the lookup count: Kai's phase lead rests on his one deal splitting
evenly (parity 1.000), not on his three lookups. The tool use is a
real behavioural change; it is not the lever on reward.

**Per-rollout, Kai hit 0.640 on a single evenly-split deal; Omar hit
0.559 with closure=1.00 and $28 value; Taj hit 0.488.** Only Kai
cleared 0.60 — as in Phase 1, where his 0.609 was also the only one.

### P2 → P3: the trading collapse the reward hides (−0.007)

**Closure_rate drops near zero.** Across five rollouts, eight
marketplace deals closed but only one (Rex) had the focal as a
counterparty, and that one logged focal_surplus=−$9. Rex's lone focal
close scored `swap_quality.combined=0` with parity 0.000; the other
four rollouts completed no swap and are not scored on swap_quality or
capability_asymmetry at all (null → dropped, weights renormalized).

**No mutual wins anywhere.** Rosa/Zara/Buck/Taj each ran full
~92-event sessions and closed nothing of their own. Rex closed once,
single-sided against himself. Compare to C4 P3's Taj (turn-7 mutual
close, $14 surplus) — those wins aren't here.

**Why the reward barely moves anyway.** With swap_quality and
capability_asymmetry null in four of five rollouts, the Stage IV
reward renormalizes onto review_utilization (two-thirds) and
deal_outcomes (one-third). C5's review diligence is genuinely strong
(RU 0.744 mean), so the phase mean lands at 0.492 — second of the
seven configs on Stage IV — while the trading record underneath is
one one-sided close at a focal loss. Abstention is priced only
through closure inside deal_outcomes; do not read the 0.492 as barter
skill.

**The combined picture:** Gemini 3.5 Flash can transact in money phases
but can't find mutually-beneficial barters. The mechanic shift from
price signals to inventory matching exposes the smaller model.

---

## Closure trajectory

| Phase | Closures | Why |
|---|---:|---|
| P1 | 9/15 | GPT-5.5 buyers active, focal accepts above floor |
| P2 | 11/15 | Higher than P1 — value-discriminating closes |
| P3 | 1 focal close / 8 marketplace deals | Rex closed once (surplus=−9); 7 other closes were opponent-pair deals |

**The Phase 2 closure rise is C5-specific.** Every other config (C1, C2,
C3, C4) saw closure decline from P1 to P2. C5 went the other way.
Gemini 3.5 Flash engaged the lookup tool more than any other focal
(1.80 mean), and C4's Gemini 3.1 Pro ignored the tool and saw closure
drop to 0.40. It is tempting to tie the two together — but the
per-rollout data inside C5 P2 does not support a clean tool→outcome
link (Marcus closed 11 deals at zero lookups), so read the
co-occurrence as suggestive at most, not causal.

**The Phase 3 result is "closes without surplus."** The focal
participated in one closed swap across five rollouts and got a
negative outcome on it; the other seven marketplace deals closed
between opponent pairs while the focal watched. The one scored focal
close came out `swap_quality.combined=0` with parity 0.000; the four
swap-less rollouts were not scored on swap_quality at all.

---

## Per-persona phase progression

Phase 3 swaps personas. Rex and Taj persist all three phases. Kai →
Rosa, Marcus → Zara, Omar → Buck.

| Persona slot | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / — / Rosa | **0.609** | **0.640** | 0.626 | Tops every phase — each time on thin volume (one even-split deal in the money phases; review diligence in barter) |
| Rex | 0.293 | 0.332 | **0.214** | Lowest in every phase; band-edge splits (parity 0.000), then a −$9 one-sided swap |
| Marcus / — / Zara | 0.333 | 0.476 | **0.700** | $50 value in P2 but lopsided splits; Zara is the top P3 rollout yet closes nothing of her own |
| Omar / — / Buck | 0.466 | 0.559 | 0.330 | Strongest transactor in money phases; Buck's missed lookup costs him in P3 |
| Taj | 0.316 | 0.488 | 0.589 | One-sided money closes; P3 the misrouted swap, carried by review credit |

**Kai's slot is C5's top scorer in every phase — read it as a parity
artifact, not dominance.** In each money phase Kai closed exactly one
deal, and each time it was the phase's only even split (parity 1.000),
which the balance-centric capability_asymmetry rewards more than
Marcus's eleven-deal volume or Omar's $28 extraction. Rosa (same set
slot) then posts 0.626 in barter on review diligence alone. Omar
remains the strongest *transactor* — closure 1.00 with $28 extracted
in P2, and the only P1 rollout with any parity beyond Kai (0.400) —
but that now buys 0.466/0.559, not the top slot. Buck (Omar's P3
persona) falls to 0.330: he looked up before only one of his two
offers, and with review_utilization carrying two-thirds of the
renormalized weight in a swap-less rollout, that 0.444 review score
decides it.

**Rex is C5 P3's lowest score — via the rerun.** 0.214 came from the
`tool_choice=required` rerun. Rex closed exactly one swap with
focal_surplus=−$9; he got partial rubric credit because the
counterparty was satisfied (`buyer_surplus=1.0`), even though
`swap_quality.combined=0` and parity 0.000 record a fully one-sided
split. Under the new judge the observer rated Rex
1/7 against his own 4/7 — the widest over-rating gap in the phase.
The review_utilization fix also lands here: Rex looked up before his one
offer but offered to a partner not rated ≥ 4.0, so his review score
falls to 0.556 — together these pull the rollout to the bottom.

**Rex's trajectory is the phase floor throughout.** Rex goes
0.293 → 0.332 → 0.214 — band-edge money closes (parity 0.000 in both
money phases), then the one-sided barter swap. He is the lowest C5
rollout in all three phases.

**Zara is the barter winner — and a non-rerun rollout.** 0.700 is the
highest Phase 3 score in C5, and it came from an original-configuration
rollout. Zara closed nothing of her own; with no completed swap she is
not scored on swap_quality or capability_asymmetry, and her perfect
review_utilization of 1.000 (she looked up before her offer and
offered to a high-rated partner) carries two-thirds of the
renormalized reward. Her 7/7 self and observer ratings and clean
privacy are reported diagnostics, outside the reward. Rosa (0.626)
and Taj (0.589) follow — Taj from the misrouted-accept story (see
phase3/INSIGHTS).

**Rosa's P3 row is now informative.** The rerun shows Rosa running a
full 96-event session with no focal closure but with two pre-offer
lookups and matched 7/7 self/observer capability ratings. The 0.626
reward reflects the review_utilization weight (0.889, two-thirds of
the renormalized reward in a swap-less rollout), not a mutual-win
signal — with no focal closure, swap_quality and capability_asymmetry
are not scored, and the 7/7 ratings are reported diagnostics.

---

## What stayed constant in C5

1. **Persona privacy = 1.00 in every applicable rollout.** No leaks,
   no paraphrase slips. The same near-invariance as every other config
   except C4. It is reported as a diagnostic only — under cr-2026-08
   privacy carries no weight in any stage's reward.
2. **Lookup-tool engagement was consistent across both phases that
   exposed the tool.** P2 mean = 1.80; P3 mean = 2.4 (natural-only =
   2.67). Both are above zero in every applicable phase, in sharp
   contrast to C4's Gemini 3.1 Pro, which used the tool zero times in
   both phases. The generation difference holds across phases.
3. **Deadlock handling stayed clean.** No spirals or loops in any
   phase.
4. **Spend was tight.** Each phase landed in the $7–9 range. The model
   is genuinely cheap to run.

---

## What changed dramatically

1. **Closure rate: 0.60 → 0.73 → 0.07.** The Phase 3 collapse is near
   total — one focal close across five rollouts, at negative focal
   surplus.
2. **Value extracted: $12.6 → $21.2 → N/A.** Phase 2 was the high-water
   mark, not Phase 1.
3. **Dual-surplus rate: 0.13 → 0.27 → N/A.** Doubled from P1 to P2 then
   evaporated.
4. **Mutual wins: — → — → 0.** C5 Phase 3 had no mutual wins, unlike
   C4 (2) or C2 (2).
5. **Phase 3 needed a config-override rerun on two sets.** Rosa and
   Rex hit the format-failure mode in the original P3 run; the rerun
   used `tool_choice=required` to force function_calls every turn.
   First time in C5 any phase needed remediation.

---

## C5 vs the other configs

| Metric | C1 (S/S) | C2 (S/G) | C3 (O/G) | C4 (G31/X) | C5 (G35/X) |
|---|---:|---:|---:|---:|---:|
| P1 mean reward | **0.60** | 0.37 | 0.47 | 0.50 | 0.40 |
| P1 closure | 0.60 | 0.60 | 0.67 | **0.73** | 0.60 |
| P1 dual-surplus | 0.53 | 0.20 | 0.47 | 0.40 | 0.13 |
| P2 mean reward | 0.49 | 0.40 | 0.36 | 0.33 | **0.50** |
| P2 closure | — | — | — | 0.40 | **0.73** |
| P2 lookup calls (mean) | 0.75 | 0.60 | 0.80 | **0.00** | **1.80** |
| P3 mean reward | 0.26 | 0.34 | 0.40 | 0.32 | **0.49** |
| P3 mutual wins | 1 | 2 | 0 | **2** | **0** |
| Persona privacy, reported (all phases) | 1.00 | 1.00 | 1.00 | 0.997 | 1.00 |
| Total cost | ~$266 | ~$99 | ~$239 | ~$43 | **~$25** |

(Cross-config rewards are cr-2026-08 stage means, quoted to 2dp. The
later configs sit outside the table: on P2, C7 leads all seven at
0.51; on P3/Stage IV, C6 leads at 0.53 and C7 is last at 0.23.)

**C5 is the cheapest config, has the second-highest Phase 2 reward of
all seven configs (0.50, just behind C7's 0.51), has the highest
Phase 2 lookup-tool engagement of any config, and — under cr-2026-08 —
the second-highest Stage IV reward (0.49, behind only C6's 0.53, with
C7 now last and C3 no longer bottom).** The Stage IV rank is
review-carried, not trade-carried: four of five rollouts closed no
swap (unscored on swap_quality) and the fifth closed one-sidedly at a
focal loss. C5 also walks back the
earlier "Gemini family ignores the lookup tool" framing: 3.5 Flash
engaged the tool more than any other focal, while 3.1 Pro engaged it
zero times. That's a generation effect, not a family pattern.

**Gemini 3.5 Flash as a focal:** transactional in money phases, peaks in
Phase 2 (a shape it now shares with C2 and C7), can't find
mutually-beneficial barter (even when its Stage IV rank says
otherwise), cheapest to run, and
*engages tools more* than its 3.1 Pro sibling — the opposite of what
the early counting suggested.

---

## Self-perception story across phases

The self-vs-observer gap (Δ) is the distance between how the focal rates
its own session and how a neutral observer rates it, on a 1–7 scale.
Under the scoring judge that gap is noisy and points both ways — the
focal sometimes over-rates a poor session and sometimes under-rates a
good one. The gap also widens as the mechanic gets harder to read.

| Phase | Mean Δ | Widest gap | Key pattern |
|---|---:|---|---|
| P1 | 0.6 | Omar Δ=2 | Three of five at Δ=0; small but not because the model is calibrated |
| P2 | 1.0 | Kai Δ=3 (4/7 self, 7/7 obs) | Under-rating shows up — the observer credits engagement Kai discounts |
| P3 | 2.6 | Taj Δ=6 (1/7 self, 7/7 obs) | Gaps blow out in both directions — over- and under-rating side by side |

**The gap is bidirectional, and bigger Δ does not mean a worse model.**
In P3, Taj rated itself 1/7 while the observer rated it 7/7 (Δ=6,
under-rating a diligent session); Rex rated itself 4/7 against the
observer's 1/7 (Δ=3, over-rating a −$9 close); Buck under-rated (1/7 vs
5/7). Zara and Rosa matched at 7/7. There is no clean "the focal knows
how it did" signal — the neutral observer often rewards effort the focal
writes off, and occasionally the focal credits itself for a close the
observer scores as a loss. Barter, with no price signal to anchor on,
is where these gaps are widest.

---

## Methodology caveats

- **Lookup-count methodology.** Lookup_agent function_call counts in
  these writeups come from `response.output` function_call entries
  (the canonical record of model tool invocations). An earlier
  counting method used `channel_events`, which exclude private
  lookup_agent calls and produced a spurious 0.00 mean. The corrected
  P2 counts are [3, 0, 0, 3, 3] for persona order Kai/Rex/Marcus/
  Omar/Taj, mean 1.80. The corrected P3 counts are 2/2/3/1/4 for
  Rosa/Rex/Zara/Buck/Taj, mean 2.4 (with the tool_choice caveat
  noted below).
- **Tier confound (Pro → Flash):** Gemini 3.5 Pro is not available on
  OpenRouter, so C5 uses Gemini 3.5 Flash. Any C4 → C5 delta therefore
  conflates two changes: generation (3.1 → 3.5) *and* tier (Pro →
  Flash). Until gemini-3.5-pro ships, treat C4 → C5 comparisons as
  **directional, not isolated.** The lookup-engagement direction
  (0.00 → 1.80 in P2) is conservative under the tier confound:
  moving *down* a tier usually *reduces* tool engagement, so the
  generation jump is doing at least the work we see.
- **Phase 3 lookup confound (tool_choice=required).** Rosa and Rex
  P3 ran with `tool_choice="required"`, which forces a function_call
  every turn. Their lookup counts (2 each) may be slightly inflated
  relative to natural behaviour. The natural-behaviour P3 estimate is
  better drawn from Zara/Buck/Taj — mean 2.67. The full-five mean
  of 2.4 is reported with this caveat.
- **Phase 3 Rosa/Rex were re-run with a different configuration.** The
  original C5 P3 run hit a Gemini-3.5-Flash format-failure mode in
  set_01 (Rosa, 0 channel events) and set_02 (Rex, 8 channel events):
  the model intermittently emitted reasoning as a plain assistant
  message instead of as a `function_call`, and NeMo Gym's
  simple_agent treats a message-without-tool-call as end-of-rollout
  (the same mechanism that handles legitimate `focal_done` summaries),
  so the focal accidentally terminated its own session. The two
  affected rollouts were re-run with **(a)** `tool_choice="required"`
  on the API call (forcing a function_call every turn instead of the
  default `auto`) and **(b)** a temporarily stricter Phase 3
  focal-agent prompt ("NEVER reply with a plain message"; "if unsure
  call `pass(message='thinking…')`"). After the rerun was spliced
  into the canonical Phase 3 data, the prompt template was reverted
  and the temp rerun task file was deleted — but the result is that
  **two of the five Phase 3 rollouts (Rosa, Rex) ran under a
  different configuration** than the other three (Zara, Buck, Taj —
  tool_choice=auto + original prompt) and than every other
  phase/config in the experiment. The headline numbers (0.492 mean,
  0 mutual wins, 0.07 closure_rate) hold across the full five-rollout
  set; the configuration delta is the methodology caveat. The
  rerun's API spend was a separate exploratory cost and is **not**
  included in C5's $25 paper budget.
- **C5 Phase 3 had zero mutual_wins.** Unlike C4 Phase 3 (which had 2
  mutual wins from Taj and Zara), the focal's only completed swap in
  C5 Phase 3 scored `swap_quality.combined=0` (parity 0.000); the
  other four rollouts completed no swap and were not scored on
  swap_quality at all (null under cr-2026-08). The mechanic is the
  same; the focal is smaller; the wins disappeared. This holds across
  both the original-config and rerun-config rollouts.
- **n=1 per persona per phase.** All findings directional, not
  significance-tested.
- **GPT-5.5 as opponent** is shared with C4 only. Model-family effects
  on the opponent side can't be fully isolated within the 5-config
  matrix.
- **Persona changes in P3.** Rosa/Zara/Buck replace Kai/Marcus/Omar.
  Rex and Taj persist across all phases — they're the only
  same-persona comparisons available.

---

## Files

- `phase1/INSIGHTS.md`, `phase2/INSIGHTS.md`, `phase3/INSIGHTS.md`
- `phase{N}/set_NN_<focal>/` — per-rollout canonical files
- `COMPARISON.md` — this document

---

*C5 (Gemini 3.5 Flash vs GPT-5.5) is the cheapest config in the
experiment, with a peak-at-P2 reward trajectory
(P1 < P2 > P3 = 0.404 → 0.499 → 0.492) whose P3 leg barely dips under
cr-2026-08. Phase 2 is the headline: 0.499
mean reward, 0.73 closure, $21.2 mean value extracted — the second-highest
Phase 2 of any config, just behind C7 (0.51)
— and achieved alongside 1.80 mean lookup_agent
calls per rollout, the highest tool-engagement rate of any config in
the experiment. Per-rollout P2 lookup counts are [3, 0, 0, 3, 3] for
Kai/Rex/Marcus/Omar/Taj, splitting cleanly on persona style
(information-seeking personas engage; transactional/stoic personas
don't). This walks back the earlier "Gemini family ignores the
lookup tool" framing — the corrected story is a generation effect:
Gemini 3.1 Pro ignored the tool (C4), Gemini 3.5 Flash engages it
more than any other focal we tested. Phase 3 still produced zero
mutual wins across five rollouts: one focal swap closed (Rex,
focal_surplus=−$9, parity 0.000 — fully one-sided) and the four
swap-less rollouts were not scored on swap_quality; the 0.492 mean
(second of seven on Stage IV) is carried by review_utilization
(0.744), not by trading. P3
lookup engagement also continues (2.4 mean overall; 2.67 across the
three natural-config rollouts). Two of the five P3 rollouts (Rosa,
Rex) used a `tool_choice=required` override after the original run
hit a Gemini-3.5-Flash format-failure mode — that may slightly
inflate their lookup counts but does not change the headline shape.
The tier confound (Pro → Flash) means C4 → C5 deltas are directional;
the generation effect on tool engagement is the most striking
cross-config finding in the dataset. Volume in money phases,
one-sided splits throughout (parity 0.28 / 0.33 / 0.00 by phase),
void in barter, tool-curious in both — Gemini 3.5 Flash's defining
shape.*
