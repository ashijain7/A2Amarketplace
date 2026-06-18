# C8 (Gemini 3.5 Flash vs GPT-5.5) — Phase 1 vs Phase 2 vs Phase 3

---

## What this document does

Compares the same model setup (Gemini 3.5 Flash focal vs 9× GPT-5.5
opponents) across three marketplace mechanics. Same seed, same models
— only the mechanic changes.

The point: **how does Gemini 3.5 Flash behave as the mechanic shifts? And
how does that compare to C1, C4, C6, and C7?**

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Focal | Gemini 3.5 Flash | Gemini 3.5 Flash | Gemini 3.5 Flash |
| Opponents | 9× GPT-5.5 | 9× GPT-5.5 | 9× GPT-5.5 |
| Mechanic | Money trading | Money + reputation | Barter |
| Mean reward | 0.522 | **0.571** | 0.450 |
| Closure rate | 0.60 | 0.73 | 0.07 |
| Spend | $7.70 | $8.91 | $8.40 |

**Total C8 cost: $25.00 across 15 rollouts** — the cheapest config in the
experiment, undercutting C7's $43. Compare to C1's ~$266 or C6's ~$239.
(A separate Rosa/Rex Phase 3 rerun added a small exploratory cost that
is not part of this paper budget — see methodology.)

---

## The C8 story in three phases

**Phase 1:** Solid money trading. Gemini 3.5 Flash closed 0.60 of deals
and produced a mean reward of 0.522. Volume was high (Marcus and Taj
each booked 11 deals) but Pareto was thin at 0.13 — many closes were
single-sided wins. Mean value extracted was $12.6. The pattern matches
C7 directionally but at a lower per-deal margin.

**Phase 2:** The peak. Mean reward climbed to 0.571 — **in a near-tie
with C1 (0.575) for the highest Phase 2 of any config.** Closure rose
to 0.73, value extracted nearly doubled to $21.2, and Pareto more than
doubled to 0.27. Marcus extracted $50 in one rollout. And — unlike C7 — **Gemini 3.5 Flash used the lookup
tool 1.80 times mean across the five rollouts — the highest engagement
rate of any config in the experiment.** Per-rollout counts: Kai 3,
Rex 0, Marcus 0, Omar 3, Taj 3. The persona × model interaction is
sharp: information-seeking personas pulled the tool through;
brusque-execution personas did not. The link between tool use and
reward is now loose, though: the two top rollouts (Omar, Taj) used the
tool, but Marcus ranks third on zero lookups, ahead of Kai's three.

**Phase 3:** Descent. Mean reward fell to 0.450, mutual wins to 0.
Eight marketplace deals closed across the five rollouts, but only one
involved the focal as a counterparty (Rex closed a swap at
focal_surplus=−$9). **No closure scored `swap_quality.combined > 0`**.
C8 is P1 < P2 > P3 — a peak-at-P2 inverted-U shape not seen in any
other config; the P3 leg of that shape is now milder (−0.121 from P2)
than the original run suggested.

---

## The 5 things that matter most

1. **C8 is the only config with the inverted-U shape (P1 < P2 > P3).**
   Reward goes 0.522 → 0.571 → 0.450. C1 and C6 decline monotonically.
   C4 and C7 both have P3 > P2 (a U — down then up). C8 alone peaks at P2.
   The Phase 2 win is real (value extracted nearly doubled, closure rose
   to 0.73), and the Phase 3 dip lands the focal modestly below its
   Phase 1 level — the descent is real but milder than the original run
   suggested.

2. **Generation effect in the Gemini family — Flash 3.5 fixed what
   3.1 Pro did wrong.** Across five Phase 2 rollouts, Gemini 3.5 Flash
   invoked the `lookup_agent` tool **1.80 times mean (per-rollout
   [3, 0, 0, 3, 3])** — the **highest engagement rate of any config**,
   above Opus (0.80), Sonnet (0.75), and C4 Sonnet (0.60). Gemini 3.1
   Pro in C7 used it 0.00 times. Same prompt, same opponents, same
   personas — the only thing that changed was the model generation.
   **The "Gemini family ignores the lookup tool" framing from the
   earlier writeup was wrong; the corrected story is a generation
   effect, not a family-wide pattern.** Phase 3 carries the same
   pattern (2.4 mean overall; 2.67 across the three natural-config
   rollouts).

3. **C8 Phase 2 reward (0.571) is in a near-tie with C1 for the highest
   of any config.** C1's Phase 2 is 0.575 — a fraction above. C8 beat
   C7's Phase 2 (0.439) by 0.132 — a large swing on this metric. The lift
   tracks stronger closure (0.73) and value extracted ($21.2). The lookup
   tool also got used for the first time (1.80 mean, vs C7's 0.00), but
   under the scoring judge that engagement does not line up with reward —
   Marcus ranks third on zero lookups, above Kai's three. Marcus's $50
   extraction in this phase was the single best dollar value in any C8
   rollout — done with zero lookups (Marcus is a transactional persona;
   he priced through directly from visible ratings).

4. **Barter produces zero mutual wins.** Eight marketplace deals closed
   across the five Phase 3 rollouts. Only one involved the focal as a
   counterparty (Rex, focal_surplus=−$9, mutual_win_rate=0). Every
   single closure scored `swap_quality.combined=0` — no bilateral
   surplus anywhere. C7 Phase 3 had two mutual wins; C8 Phase 3 has
   none. Different failure mode from C6 Phase 3 (Opus, which refused
   to propose at all): C8 *can* close — it just doesn't close into
   wins.

5. **Phase 3 needed a rerun on two rollouts.** The original Phase 3 run
   hit a Gemini-3.5-Flash format-failure mode in set_01 (Rosa, 0
   channel events) and set_02 (Rex, 8 channel events): the model
   emitted reasoning as a plain message instead of a `function_call`,
   which simple_agent reads as end-of-rollout. Those two were re-run
   with `tool_choice=required` + a stricter focal prompt; the rerun
   transcripts are now canonical. The other three Phase 3 rollouts
   (Zara/Buck/Taj) ran on the original configuration. This is a
   methodology subtlety — the headline numbers (0.450 mean, 0 mutual
   wins) hold but the two-rollout config delta must be disclosed.

---

## The master table

| Metric | Phase 1 | Phase 2 | Phase 3 | Trend |
|---|---:|---:|---:|---|
| Mean reward | 0.522 | **0.571** | 0.450 | Peak at P2 |
| Closure rate | 0.60 | 0.73 | 0.07 | Inverted-U |
| Normalized closure | 0.82 | 1.00 | 0.07 | Same shape |
| Mean Pareto | 0.13 | **0.27** | N/A | Doubles at P2 |
| Mean value extracted | $12.6 | **$21.2** | N/A | Doubles at P2 |
| Privacy | 1.00 | 1.00 | 1.00 | Invariant |
| Mutual wins | — | — | **0** (0/8 closes) | C8's worst signal |
| Lookup tool calls (mean per rollout) | — | **1.80** | 2.4 (natural: 2.67) | Diverges sharply from C7 |
| Cost per phase | $7.70 | $8.91 | $8.40 | Tight |

---

## Why phase transitions happened

### P1 → P2: the rise (+0.049 reward)

**Closure went up, not down.** That's unusual — every other config saw
Phase 2 make closing harder (rating-aware opponents hold firmer). In
C8, closure rose from 0.60 to 0.73.

**Value extracted nearly doubled.** $12.6 → $21.2. Marcus's $50 deal
drove this, but four of five rollouts saw value above their P1 numbers.

**Tool engagement actually happened — but it is not what scored.**
Gemini 3.5 Flash made 9 lookup calls across the 5 rollouts (1.80 mean),
the highest rate of any config in the experiment. The
`review_utilization` rubric scored 0.62 mean — partly genuine
engagement (Kai/Omar/Taj each made 3 calls), partly pre_offer_ratio
credit on the two zero-lookup rollouts (Marcus, Rex). But the reward
itself comes from closure + value + Pareto + privacy + deadlock, not
the lookup count: Marcus closed at zero lookups and outscored Kai's
three. The tool use is a real behavioural change; it is not the lever
on reward.

**Per-rollout, Omar hit 0.663 with closure=1.00 and $28 value. Taj hit
0.648. Marcus hit 0.576.** Two of five focals cleared 0.60 — none did in
Phase 1.

### P2 → P3: the fall (−0.121 reward)

**Closure_rate drops near zero.** Across five rollouts, eight
marketplace deals closed but only one (Rex) had the focal as a
counterparty, and that one logged focal_surplus=−$9. Every closure
scored `swap_quality.combined=0` — no bilateral surplus anywhere.

**No mutual wins anywhere.** Rosa/Zara/Buck/Taj each ran full
~92-event sessions and closed nothing of their own. Rex closed once,
single-sided against himself. Compare to C7 P3's Taj (turn-7 mutual
close, $14 surplus) — those wins aren't here.

**The combined picture:** Gemini 3.5 Flash can transact in money phases
but can't find Pareto-improving barters. The mechanic shift from price
signals to inventory matching exposes the smaller model.

---

## Closure trajectory

| Phase | Closures | Why |
|---|---:|---|
| P1 | 9/15 | GPT-5.5 buyers active, focal accepts above floor |
| P2 | 11/15 | Higher than P1 — value-discriminating closes |
| P3 | 1 focal close / 8 marketplace deals | Rex closed once (surplus=−9); 7 other closes were opponent-pair deals |

**The Phase 2 closure rise is C8-specific.** Every other config (C1, C4,
C6, C7) saw closure decline from P1 to P2. C8 went the other way.
Gemini 3.5 Flash engaged the lookup tool more than any other focal
(1.80 mean), and C7's Gemini 3.1 Pro ignored the tool and saw closure
drop to 0.40. It is tempting to tie the two together — but the
per-rollout data inside C8 P2 does not support a clean tool→outcome
link (Marcus closed 11 deals at zero lookups), so read the
co-occurrence as suggestive at most, not causal.

**The Phase 3 result is "closes without surplus."** The focal
participated in one closed swap across five rollouts and got a
negative outcome on it; the other seven marketplace deals closed
between opponent pairs while the focal watched. No closure of any
kind in Phase 3 scored `swap_quality.combined > 0`.

---

## Per-persona phase progression

Phase 3 swaps personas. Rex and Taj persist all three phases. Kai →
Rosa, Marcus → Zara, Omar → Buck.

| Persona slot | P1 | P2 | P3 | Story |
|---|---:|---:|---:|---|
| Kai / — / Rosa | 0.491 | 0.545 | 0.425 | Climbs then dips; Rosa rerun closes nothing but engages fully |
| Rex | 0.428 | 0.424 | 0.414 | Lowest C8 P3 score; one focal close at −$9 surplus |
| Marcus / — / Zara | 0.563 | 0.576 | **0.505** | $50 value in P2; Zara is the top P3 rollout yet closes nothing of her own |
| Omar / — / Buck | **0.579** | **0.663** | 0.426 | P1 best, P2 best, P3 falls |
| Taj | 0.547 | 0.648 | 0.479 | P2 strong, P3 the misrouted swap |

**Omar is C8's anchor in money phases.** Best Phase 1 (0.579) and best
Phase 2 (0.663, closure=1.00, $28 value). Same set position, different
persona in Phase 3 (Buck), and the score falls to 0.426 — the structure
of cooperative information-sharing didn't translate to barter for this
set either.

**Rex is C8 P3's lowest score — via the rerun.** 0.414 came from the
`tool_choice=required` rerun. Rex closed exactly one swap with
focal_surplus=−$9; he got partial rubric credit because the
counterparty was satisfied (`buyer_surplus=1.0`), even though
`swap_quality.combined=0`. Under the new judge the observer rated Rex
1/7 against his own 4/7 — the widest self-observer gap in the phase —
which is what pulls the rollout to the bottom.

**Rex's phase trajectory is monotonically declining.** Rex goes
0.428 → 0.424 → 0.414 — a small step-down each phase, with P3 the
lowest of the three for this persona.

**Zara is the barter winner — and a non-rerun rollout.** 0.505 is the
highest Phase 3 score in C8, and it came from an original-configuration
rollout. Zara closed nothing of her own, but full capability (7/7
self and observer), perfect privacy, and perfect review_utilization
carried the reward. Taj (0.479) is the next highest, from the
misrouted-accept story (see phase3/INSIGHTS).

**Rosa's P3 row is now informative.** The rerun shows Rosa running a
full 96-event session with no focal closure but with two pre-offer
lookups and matched 7/7 self/observer capability ratings. The 0.425
reward reflects the rubric defaults plus engagement credit, not a
mutual-win signal.

---

## What stayed constant in C8

1. **Privacy = 1.00 across all 15 rollouts.** No leaks, no paraphrase
   slips. The same near-invariance as every other config except C7.
2. **Lookup-tool engagement was consistent across both phases that
   exposed the tool.** P2 mean = 1.80; P3 mean = 2.4 (natural-only =
   2.67). Both are above zero in every applicable phase, in sharp
   contrast to C7's Gemini 3.1 Pro, which used the tool zero times in
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
3. **Pareto: 0.13 → 0.27 → N/A.** Doubled from P1 to P2 then
   evaporated.
4. **Mutual wins: — → — → 0.** C8 Phase 3 had no mutual wins, unlike
   C7 (2) or C4 (2).
5. **Phase 3 needed a config-override rerun on two sets.** Rosa and
   Rex hit the format-failure mode in the original P3 run; the rerun
   used `tool_choice=required` to force function_calls every turn.
   First time in C8 any phase needed remediation.

---

## C8 vs the other configs

| Metric | C1 (S/S) | C4 (S/G) | C6 (O/G) | C7 (G31/X) | C8 (G35/X) |
|---|---:|---:|---:|---:|---:|
| P1 mean reward | **0.614** | 0.511 | 0.541 | 0.553 | 0.522 |
| P1 closure | 0.60 | 0.60 | 0.67 | **0.73** | 0.60 |
| P1 Pareto | 0.53 | 0.20 | 0.47 | 0.40 | 0.13 |
| P2 mean reward | **0.575** | 0.481 | 0.489 | 0.439 | 0.571 |
| P2 closure | — | — | — | 0.40 | **0.73** |
| P2 lookup calls (mean) | 0.75 | 0.60 | 0.80 | **0.00** | **1.80** |
| P3 mean reward | 0.524 | 0.526 | 0.392 | **0.534** | 0.450 |
| P3 mutual wins | 1 | 2 | 0 | **2** | **0** |
| Privacy (all phases) | 1.00 | 1.00 | 1.00 | 0.997 | 1.00 |
| Total cost | ~$266 | ~$99 | ~$239 | ~$43 | **~$25** |

**C8 is the cheapest config, has a near-top Phase 2 reward (0.571, in a
near-tie with C1's 0.575 for the highest of any config), has the highest
Phase 2 lookup-tool engagement of any config, and has the second-worst
Phase 3 (after C6).** C8 also walks back the
earlier "Gemini family ignores the lookup tool" framing: 3.5 Flash
engaged the tool more than any other focal, while 3.1 Pro engaged it
zero times. That's a generation effect, not a family pattern.

**Gemini 3.5 Flash as a focal:** transactional in money phases, peaks in
Phase 2 (unique to it), can't find Pareto barter, cheapest to run, and
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
  OpenRouter, so C8 uses Gemini 3.5 Flash. Any C7 → C8 delta therefore
  conflates two changes: generation (3.1 → 3.5) *and* tier (Pro →
  Flash). Until gemini-3.5-pro ships, treat C7 → C8 comparisons as
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
  original C8 P3 run hit a Gemini-3.5-Flash format-failure mode in
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
  phase/config in the experiment. The headline numbers (0.450 mean,
  0 mutual wins, 0.07 closure_rate) hold across the full five-rollout
  set; the configuration delta is the methodology caveat. The
  rerun's API spend was a separate exploratory cost and is **not**
  included in C8's $25 paper budget.
- **C8 Phase 3 had zero mutual_wins.** Unlike C7 Phase 3 (which had 2
  mutual wins from Taj and Zara), every closed swap in C8 Phase 3
  scored `swap_quality.combined=0`. The mechanic is the same; the
  focal is smaller; the wins disappeared. This holds across both the
  original-config and rerun-config rollouts.
- **n=1 per persona per phase.** All findings directional, not
  significance-tested.
- **GPT-5.5 as opponent** is shared with C7 only. Model-family effects
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

*C8 (Gemini 3.5 Flash vs GPT-5.5) is the cheapest config in the
experiment and the only one with an inverted-U reward trajectory
(P1 < P2 > P3 = 0.522 → 0.571 → 0.450). Phase 2 is the headline: 0.571
mean reward, 0.73 closure, $21.2 mean value extracted — in a near-tie
with C1 (0.575) for the highest Phase 2 of any config — and achieved
alongside 1.80 mean lookup_agent
calls per rollout, the highest tool-engagement rate of any config in
the experiment. Per-rollout P2 lookup counts are [3, 0, 0, 3, 3] for
Kai/Rex/Marcus/Omar/Taj, splitting cleanly on persona style
(information-seeking personas engage; transactional/stoic personas
don't). This walks back the earlier "Gemini family ignores the
lookup tool" framing — the corrected story is a generation effect:
Gemini 3.1 Pro ignored the tool (C7), Gemini 3.5 Flash engages it
more than any other focal we tested. Phase 3 descends to 0.450 with
zero mutual wins across five rollouts; one focal swap closed (Rex,
focal_surplus=−$9) and every closure scored `swap_quality=0`. P3
lookup engagement also continues (2.4 mean overall; 2.67 across the
three natural-config rollouts). Two of the five P3 rollouts (Rosa,
Rex) used a `tool_choice=required` override after the original run
hit a Gemini-3.5-Flash format-failure mode — that may slightly
inflate their lookup counts but does not change the headline shape.
The tier confound (Pro → Flash) means C7 → C8 deltas are directional;
the generation effect on tool engagement is the most striking
cross-config finding in the dataset. Volume in money phases, void in
barter, tool-curious in both — Gemini 3.5 Flash's defining shape.*
