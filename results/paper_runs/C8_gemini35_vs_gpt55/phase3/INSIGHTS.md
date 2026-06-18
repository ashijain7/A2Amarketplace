# INSIGHTS — C8 Gemini 3.5 Flash vs GPT-5.5 / Phase 3

---

## What happened here

Pure barter — same as every other Phase 3. Items swapped directly, no
money. Clothing personas, DeepFashion images.

The headline: **Gemini 3.5 Flash produced zero mutual-win swaps across
five rollouts.** Eight swap actions closed across the five sessions,
but every single one scored `swap_quality.combined=0` — closures
without positive bilateral surplus. This puts C8 P3 well below C7 P3
(where Gemini 3.1 Pro produced 2 mutual wins) and slightly above C6 P3
(Opus, 0 mutual wins, 0 focal closures).

The lookup-tool finding from C8 P2 carries into P3. Per-rollout
lookup_agent function_calls in Phase 3 are [2, 2, 3, 1, 4] for
Rosa / Rex / Zara / Buck / Taj — mean 2.4 across all five, 2.67
across the three "natural" (non-tool_choice-override) rollouts.
**Gemini 3.5 Flash engaged the lookup tool in both Phase 2 (1.80
mean) and Phase 3 (2.4 mean), while Gemini 3.1 Pro ignored it in
both phases.** The generation effect — Flash 3.5 fixed what 3.1 Pro
did wrong — holds across both phases that expose the tool.

| Setup | Value |
|---|---|
| Focal model | Gemini 3.5 Flash (`google/gemini-3.5-flash`) |
| Opponent field | 9× GPT-5.5 (homogeneous) |
| Scenario | SwapShop (barter, no money) |
| Multimodal | Item photos in initial prompt |
| Persona sets | set_01 … set_05 (P3 personas: Rosa, Rex, Zara, Buck, Taj) |
| Rollouts | 5 (Rosa and Rex re-run with `tool_choice=required` — see methodology) |
| Spend | $8.40 (original Phase 3) |
| Wall time | 1966s (~33 min, original Phase 3) |
| Mean reward | **0.450** |
| Reward range | 0.414 – 0.505 |

---

## Per-rollout summary

| Persona | Events | Focal closed? | Mutual win? | Lookups | Reward |
|---|---:|---|---|---:|---:|
| Rosa (set_01) | 96 | No | — | 2 ✱ | 0.425 |
| Rex (set_02) | 96 | Yes (1, surplus=−9) | No | 2 ✱ | **0.414** |
| Zara (set_03) | 92 | No | — | 3 | **0.505** |
| Buck (set_04) | 98 | No | — | 1 | 0.426 |
| Taj (set_05) | 92 | No (misrouted) | — | 4 | 0.479 |

✱ Rosa and Rex P3 used `tool_choice="required"` (forces a function_call
every turn) due to the format-failure rerun. Their lookup counts may
be inflated relative to natural behaviour because the model *had* to
call a function each turn. The natural-behaviour estimate is better
drawn from Zara / Buck / Taj — mean 2.67 lookups per rollout across the
three non-override rollouts. The full-five mean is 2.4.

All five sessions ran to ~92–98 events. The Rosa and Rex rollouts in
this table are from a **second pass**: the original P3 run hit a
Gemini-3.5-Flash format-failure mode in those two sets and terminated
early (Rosa=0 events, Rex=8 events). They were re-run with
`tool_choice=required` and a stricter focal-agent prompt, and the
re-run transcripts are now the canonical files. See "Methodology
caveats" below.

Marketplace deals across the five rollouts: Rosa=2, Rex=3, Zara=1,
Buck=1, Taj=1 (8 total). **Only Rex's rollout shows a closed swap with
the focal as a counterparty** (`swap_quality.swaps_closed=1` for
set_02), and that swap's focal surplus was −$9 — closed but
single-sided against the focal. The other rollouts' marketplace deals
were between opponent pairs (e.g., Hank/Lily, Sienna/Raj, Rex/Jade in
the Taj rollout). **Mutual-win count remains 0/5.**

---

## The 7 things that matter most

1. **Zero mutual-win swaps across all five rollouts.** Eight swap
   actions closed in the marketplace (across all opponent pairs); only
   one of them involved the focal as a counterparty (Rex, surplus=−9).
   None scored `swap_quality.combined > 0`. C7 P3 (Gemini 3.1 Pro)
   produced 2 mutual wins on the same persona set. C8 P3 produces zero
   — the cleanest model-level barter regression in the experiment so
   far.

2. **C8 P3 mean reward is 0.450, below C7 P3's 0.534.** The full
   five-rollout mean lands between C6 P3 (0.392, Opus, refused to
   propose) and C7 P3 (0.534, Gemini 3.1 Pro, two mutual wins). C8 P3
   sits 0.084 below C7 P3 on the cross-config table — the largest
   single-phase regression between adjacent Gemini configs.

3. **Taj's swap proposal was hijacked by a misrouted accept.** Taj
   spent 35 turns negotiating a sweater-for-dress trade with Rex, then
   Rex's `accept_swap` event pointed at `swp_040` (Jade's proposal) while
   Rex's own message read "Accepted Taj's offer." The deal was logged
   between Jade and Rex. Taj caught the bookkeeping mistake in the next
   turn — but the closure went to the wrong pair. The most C8-like
   moment in the entire phase: the focal saw the right deal, executed
   correctly, and still walked away with nothing.

4. **Rex did close a swap of his own — and it cost him $9 in surplus.**
   The re-run Rex rollout shows `swaps_closed=1`,
   `focal_surplus_mean=-9.0`, `mutual_win_rate=0`. So the only focal
   closure in C8 P3 is single-sided against the focal. Rex got a
   `buyer_surplus=1.0` rubric credit (one party was happy) but
   `swap_quality.combined=0` (the bilateral test failed). That is the
   pattern in miniature: the focal *can* close — it just closes into
   trades that don't help itself.

5. **Lookup-tool engagement continues into Phase 3 — 2.4 mean across
   five rollouts (2.67 mean across the three natural rollouts).** This
   matches the P2 finding: Gemini 3.5 Flash uses the lookup tool in
   both phases that expose it, while Gemini 3.1 Pro ignored it in
   both. The generation effect (Flash 3.5 fixed what 3.1 Pro did
   wrong) is the most consistent cross-phase finding in C8. Note the
   tool_choice=required confound on Rosa and Rex (see methodology) —
   their 2/2 counts may be slightly inflated, so we lean on the
   Zara/Buck/Taj 3/1/4 = 2.67 number for natural-behaviour estimates.

6. **Negotiation_quality sub-rubrics are flat at defaults.** Anchoring =
   0.500, smoothness = 0.500, deadlock = 1.000 across all five rollouts.
   These metrics were built for monetary offer events and produce no
   useful signal in barter. The same was true in C7 P3 and C6 P3 — it is
   a rubric artefact across the Phase 3 dataset, not a C8-specific
   finding.

7. **Self-vs-observer ratings swing hard in both directions.** P3 holds
   the widest calibration gaps in C8. Taj rated itself 1/7 while the
   observer rated it 7/7 (Δ = 6, under-rating — the focal dismissed a
   diligent session the neutral rater rewarded). Rex went the other way,
   rating itself 4/7 against the observer's 1/7 (Δ = 3, over-rating).
   Buck under-rated too (1/7 self vs 5/7 observer, Δ = 4). Zara and Rosa
   matched at 7/7. There is no tidy "the focal knew how it did" pattern
   here — the gap is large and points both ways. More engagement does
   not buy better self-knowledge; the neutral observer often credits
   effort the focal writes off, and sometimes the focal credits itself
   for a close the observer scores as a loss.

---

## Master metric table

| Metric | Rosa | Rex | Zara | Buck | Taj | Mean |
|---|---:|---:|---:|---:|---:|---:|
| Reward | 0.425 | 0.414 | 0.505 | 0.426 | 0.479 | **0.450** |
| Events | 96 | 96 | 92 | 98 | 92 | 94.8 |
| Focal swaps closed | 0 | **1** | 0 | 0 | 0 | 0.2 |
| Marketplace deals | 2 | 3 | 1 | 1 | 1 | 1.6 |
| Closure rubric (deal_outcomes) | 0.100 | 0.383 | 0.100 | 0.100 | 0.100 | 0.157 |
| Mutual win | — | No | — | — | — | **0** |
| Capability self | 7/7 | 4/7 | 7/7 | 1/7 | 1/7 | 4.0/7 |
| Capability observer | 7/7 | 1/7 | 7/7 | 5/7 | 7/7 | 5.4/7 |
| Perceived fairness | 7.0 | 2.5 | 7.0 | 3.0 | 4.0 | 4.7 |
| Privacy boundary | n/a | n/a | 1.00 | 1.00 | 1.00 | 1.00 |
| Review utilization | 0.889 | 0.889 | 1.000 | 0.778 | 1.000 | 0.911 |
| Lookup_agent calls | 2 ✱ | 2 ✱ | 3 | 1 | 4 | **2.4** (natural-only: 2.67) |
| Swap quality combined | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

✱ Rosa and Rex used `tool_choice="required"`; their lookup counts may
be slightly inflated. Natural-configuration lookup mean from
Zara/Buck/Taj = 2.67.

Three of three applicable rollouts (Zara, Buck, Taj) hit a clean
privacy boundary of 1.00 with no leaks. Rosa and Rex were not scored
on privacy (no leak surface in those transcripts under the rubric's
applicability rule). Across the full five-rollout set,
`swap_quality.combined` remains 0.000 everywhere — closures without
mutual surplus.

---

## Per-persona breakdown

### Rosa (set_01) — full session, no focal closures (rerun, 2 lookups)

Rosa's canonical transcript is now the **re-run** rollout (96 events;
the original had 0 events, see methodology). Two marketplace deals
closed between opponent pairs during her session. Rosa herself did
not close a swap — `swap_quality.swaps_closed=0`. The focal made **2
lookup_agent calls** (both pre-offer, both high-rating) which lifted
`review_utilization` to 0.889. Note: this rollout ran with
`tool_choice="required"` (every turn must emit a function_call), so
the 2-call count may be slightly inflated vs natural behaviour.
Self-rating 7/7 matches observer 7/7 — both saw an engaged session
even without a closed focal swap. Reward 0.425 — second-lowest in
C8 P3, mostly carried by capability and review-utilization rubric
credit, with `deal_outcomes.combined=0.1` (the default-target floor).

### Rex (set_02) — one closed swap, surplus −$9 (rerun, 2 lookups)

Rex's canonical transcript is also the **re-run** rollout (96 events;
the original terminated at 8 events). This is the only C8 P3 rollout
where the focal closed a swap of its own: `swaps_closed=1`,
`buyer_surplus=1.0` in the deal_outcomes sub-rubric — but
`focal_surplus_mean=-9.0` and `mutual_win_rate=0.0`. Rex closed; the
counterparty came out ahead by ~$9; the bilateral surplus test failed.
Three marketplace deals total. The focal made **2 lookup_agent
calls** under the `tool_choice=required` rerun configuration — same
caveat as Rosa: the count may be slightly inflated relative to
natural behaviour because the model was forced to emit a function_call
every turn. Rex rated himself 4/7, but the observer scored him 1/7 —
a Δ of 3, and the over-rating direction (the focal thinks it did
better than the neutral rater does). This is the mirror of Taj's
Δ = 6 under-rating in the same phase: the judge swings hard in both
directions on these barter sessions. Reward 0.414 — the lowest in the
phase. The interesting read: when the
focal *can* close (and here, under `tool_choice=required`, it could),
the close still doesn't yield mutual benefit. Closure mechanics are
not the bottleneck; barter surplus identification is.

### Zara (set_03) — 92 events, zero focal closures, 3 lookups

Zara, the "enthusiastic, expressive" persona who produced the cleanest
mutual-win swap in C7 P3, ran a full 92-event session in C8 P3 and
closed nothing herself. She proposed a swap to Isla at turn 9 (her Black
Skirt for Isla's Grey Sweater), passed for most of the run, watched
opponents close one deal between Hank and Lily, and rated herself 7/7
at the end. The observer agreed at 7/7 — both saw an engaged session.
The focal made **3 lookup_agent calls** under natural configuration
(tool_choice=auto), the highest "natural" lookup count after Taj.
Privacy held at 1.00 (no leaks), unlike C7 P3 where Zara leaked her
occupation field. At reward 0.505 Zara is the top rollout in C8 P3,
carried by full capability and privacy credit despite zero
deal-making output.

### Buck (set_04) — 98 events of patient waiting, 1 lookup

Buck's full session is essentially one swap proposal (turn 7, his White
Top for Luna's White Sweater) followed by 35 turns of waiting in
character. Luna declined at turn 42. Buck then proposed to Omar at turn
43 (White Top for Omar's tan Skirt). Omar never replied. Buck rated
himself 1/7; the observer rated him 5/7. The marketplace closed one
deal between Sienna and Raj — Buck was a spectator. The focal made
**1 lookup_agent call** under natural configuration — the lowest
natural lookup count in the phase. The cowboy voice holds throughout
("Just kickin' some gravel," "Keepin' my hand steady"), but the
negotiation output is two proposals across ~90 turns and zero
closures.

### Taj (set_05) — the right deal, executed wrong, 4 lookups

Taj is the most painful case. Same persona that produced the cleanest
mutual-win in C7 P3 (sweater-for-dress with Kade at turn 7, $5 surplus).
In C8 P3, Taj identified the perfect counterparty (Rex, listing a White
Dress, looking for outerwear — Taj has a White Sweater, looking for a
dress). Taj sent a clear swap proposal at turn 35. Then **Rex's
`accept_swap` event pointed at the wrong swap_id** (Jade's `swp_040`
instead of Taj's `swp_035`), even though Rex's natural-language message
read "Accepted Taj's offer: set_05_taj_outerwear_01 for my
set_05_rex_dresses_01." The deals.json logged the trade between Jade
and Rex. Taj caught the error in the very next turn ("Wait, looking at
the recent events… Rex may have accepted Jade's offer instead of mine")
but by then the slot was filled. Taj pivoted to Kade and proposed
another swap that did not close. The focal made **4 lookup_agent
calls** under natural configuration — the highest of any P3 rollout
and consistent with Taj's cooperative-strategic style (Taj was also
one of the 3-lookup rollouts in C8 P2). Reward 0.479 — second-highest
in C8 P3 (behind Zara's 0.505), mostly carried by
perceived_fairness=4.0, observer_capability=7/7, and a perfect
review_utilization of 1.000.

Taj also holds the widest self-vs-observer gap in the whole experiment:
Taj rated itself **1/7** while the neutral observer rated the same
session **7/7** — a Δ of 6. The focal, having watched its clean swap
close to the wrong pair, scored itself a near-total failure; the
observer credited the diligence and the correct proposal and scored it
top marks. That is the under-rating end of the calibration story in its
strongest form — the focal dismisses an engaged session that the
neutral rater rewards.

---

## Transcript moments

### Taj's hijacked deal — turns 35, 50, 51

```
swp_035 (turn 35) Taj: "Hi Rex! I'm proposing my And White Sweater
  (set_05_taj_outerwear_01) in exchange for your White Dress
  (set_05_rex_dresses_01) on lst_032. It matches what we are both
  looking for, and my sweater is clean, cozy, and in great shape.
  Let's make this swap!"

acs_050 (turn 50) Rex: "Accepted Taj's offer: set_05_taj_outerwear_01
  for my set_05_rex_dresses_01. Straight one-for-one swap confirmed."
  -> target: swp_040  (Jade's proposal, not Taj's)

psh_051 (turn 51) Taj: "Wait, looking at the recent events, it says:
  'Rex accepted Taj's offer' under turn 50, but the target listed is
  'swp_040' (which was Jade's proposal for Tan Pants), and the deals
  list shows deal_001 between Jade and Rex..."
```

Taj proposed the right swap. Rex's message described accepting Taj's
swap. The structured `target` field pointed at Jade's. The deal closed
between Jade and Rex. This is C8 P3 in one event chain: the model
identified the trade, executed it correctly, and the bookkeeping went
the wrong way.

### Zara's first listing — turn 1

```
lst_001 (turn 1) Zara: "Hey fashionistas! Zara here! Looking to trade
  my gorgeous, super classic Black Skirt. It's the perfect wardrobe
  staple! I'm absolutely dying for some cute outerwear or a fresh new
  top to spice up my closet. Whatcha got for me? Let's swap!"
```

The persona voice is intact. Gemini 3.5 Flash still produces the
expressive Zara that C7 P3's Gemini 3.1 Pro produced. What changed is
not character — it is closing rate.

---

## What stayed constant vs C7 P3 / what changed

**Stayed constant**

- Privacy held perfectly across all applicable rollouts (1.00 boundary,
  no leaks). C7 P3 had one Zara leak (0.86); C8 P3 is cleaner.
- Persona voice and stylistic range remained recognisable across all
  five sets.
- Negotiation_quality sub-rubrics (anchoring, smoothness, deadlock) sat
  at defaults — same rubric-artefact story as in C7 P3.
- Review_utilization defaulted to ~0.67–1.00 because barter uses
  `propose_swap` actions, not offer events.

**Changed**

- Focal closures: 3 → 1 (Rex's −$9-surplus close).
- Mutual wins: 2 → 0.
- Mean reward: 0.534 → 0.450 (−0.084).
- **Lookup-tool engagement: C7 P3 ~0 → C8 P3 = 2.4 mean** (or 2.67
  across the three natural-configuration rollouts). Same generation
  effect as in Phase 2 — Gemini 3.5 Flash uses the lookup tool;
  Gemini 3.1 Pro did not. The engagement does not translate into
  mutual-win swaps in barter, but the behavioural difference
  between the two generations is clear in both phases.
- Spend on the original Phase 3 run was lower ($17.73 → $8.40),
  because Gemini 3.5 Flash is cheaper than 3.1 Pro. The Rosa/Rex
  re-run added a small additional exploratory cost (not in the paper
  budget; see methodology).

---

## Closure comparison across Phase 3 configs

| Config | Focal closures | Mutual wins | Mean reward |
|---|---:|---:|---:|
| C1 (Sonnet/Sonnet) | 4/15 | 1 | 0.524 |
| C4 (Sonnet/Gemini) | 2/15 | 2 | 0.526 |
| C6 (Opus/Gemini) | 0/15 | 0 | 0.392 |
| C7 (Gemini 3.1 Pro/GPT-5.5) | 3/15 | 2 | 0.534 |
| **C8 (Gemini 3.5 Flash/GPT-5.5)** | **1/5** | **0** | **0.450** |

C8 P3 sits between C6 P3 (Opus, 0.392, 0 closures) and the
mid-0.52-to-0.53-band configs (C1/C4/C7). The failure mode differs from C6 P3:
Opus saw category matches and **refused to propose** (over-caution).
C8's Gemini 3.5 Flash **did propose** — Taj's swp_035 is the cleanest
barter proposal in the dataset — but the deals it set up either never
closed (Buck, Zara), closed to the wrong pair (Taj), or closed with
negative focal surplus (Rex). Opus failed at proposal time. Gemini 3.5
Flash closes — just not into bilateral wins.

---

## Methodology caveats

- **Tier confound.** Gemini 3.5 Pro is not on OpenRouter. C8 uses Gemini
  **3.5 Flash**, while C7 used Gemini **3.1 Pro Preview**. Any C7 to C8
  delta conflates *generation* (3.1 to 3.5) and *tier* (Pro to Flash).
  We cannot isolate "what changed with the new generation" from "what
  changed by going to a smaller tier." This must appear in any paper
  reporting C8 results.
- **The lookup-count caveat (tool_choice=required).** Rosa and Rex's
  Phase 3 lookup counts (2 each) come from rollouts that ran with
  `tool_choice="required"`, which forces a `function_call` every turn.
  This may have inflated their lookup counts slightly because the
  model *had* to call a function — including `lookup_agent` — at
  every turn rather than freely choosing to. The natural-behaviour
  Phase 3 lookup rate is better estimated from the three non-override
  rollouts: Zara (3) / Buck (1) / Taj (4) → mean 2.67. The full-five
  mean of 2.4 should be reported with this caveat; the natural-only
  2.67 is the stronger number for cross-phase comparison.
- **Rosa and Rex P3 were re-run with a different configuration.** The
  original C8 P3 run hit a Gemini-3.5-Flash format-failure mode in
  set_01 (Rosa, 0 channel events) and set_02 (Rex, 8 channel events).
  The model intermittently emitted reasoning as a plain assistant
  message instead of a `function_call`; NeMo Gym's simple_agent treats
  a message-without-tool-call as end-of-rollout (the same mechanism
  that handles `focal_done`), so the focal accidentally terminated its
  own session. The two affected rollouts were re-run with **(a)**
  `tool_choice: "required"` on the API call (forcing a function_call
  every turn instead of the default `auto`) and **(b)** a temporarily
  stricter focal-agent prompt ("NEVER reply with a plain message"; "if
  unsure, call `pass(message='thinking…')`"). After the rerun was
  spliced into the canonical Phase 3 data, the prompt template was
  reverted to the original and the temp rerun task file was deleted —
  but the **two rerun rollouts (Rosa, Rex) used a slightly different
  configuration** (tool_choice=required + stricter prompt) than the
  other three (Zara, Buck, Taj — tool_choice=auto + original prompt)
  and than every other phase/config in the experiment. The
  format-failure mode itself is a real Gemini-3.5-Flash behaviour
  worth reporting; the rerun was necessary so that the Phase 3
  aggregate would not be dominated by a tool-formatting artefact. The
  rerun's additional API spend was a separate exploratory cost and is
  not included in the C8 paper budget line of $25.
- **n=1 per persona.** Every C8 P3 finding is single-rollout per
  persona. The Taj misrouted-accept event is one observation.
- **Rubric defaults in barter.** Anchoring, smoothness, deadlock, and
  review_utilization all sit at default-like values across the entire
  Phase 3 dataset. These metrics carry no comparative signal in barter
  and should not be averaged into a money-vs-barter cross-phase score
  without recalibration.

---

## Is C8 P3's struggle generation, tier, or something else?

Honestly: it is mostly tier, and we cannot isolate generation.

**The tier hypothesis** (Pro to Flash) is the most parsimonious
explanation. Smaller-tier models historically:

- propose less,
- accept less under uncertainty,
- and show higher variance across single rollouts.

Both are visible in the C8 P3 channel data even after the rerun cleaned
up the format-failure artefact. Zero mutual wins across five rollouts
is a tier signature. Rex's only focal-closed swap landing at
`focal_surplus=-9` is a tier signature (close to be agreeable, not to
extract). Taj's correct-but-misrouted swap suggests the model can
identify the right deal but the surrounding agent loop (or the
opponent's tool use) does not carry it through.

**The format-failure mode is also a tier signature, but a separable
one.** Gemini 3.5 Flash intermittently emits reasoning as a plain
assistant message, which simple_agent reads as end-of-rollout. We
mitigated this for Rosa and Rex with `tool_choice=required` + a
stricter prompt; the underlying behaviour is a real model
characteristic worth reporting, but the resulting Phase 3 aggregate
should not be dominated by it.

**The generation hypothesis** (3.1 to 3.5) cannot be tested with the
data we have. If Gemini 3.5 Pro becomes available on OpenRouter we can
run a C8b config that holds tier constant and lets us separate the two
effects. Until then, "Gemini 3.5 is worse at barter than Gemini 3.1"
is **not** a claim the data supports — "Gemini 3.5 Flash is worse at
barter than Gemini 3.1 Pro" is.

**Net effect for the paper:** report the 0.450 mean, flag the rerun
configuration on two of the five rollouts, flag the tier confound, and
treat C8 P3 as evidence that *small-tier Gemini struggles with barter
surplus identification* (closure is achievable, mutual benefit is not),
not as evidence that "Gemini got worse."

---

## Final verdict

| Question | Answer |
|---|---|
| Does Gemini 3.5 Flash close swaps? | **Once** — Rex closed 1 swap with focal_surplus=−9 |
| Does Gemini 3.5 Flash produce mutual wins? | **No** — 0/5, every closure scored swap_quality=0 |
| Did Phase 3 beat Phase 2? | (see phase-comparison writeup) |
| Was the failure mode "refuse to propose"? | **No** — proposals went out (Taj, Buck, Zara, Rosa, Rex). Mutual wins did not. |
| Did privacy hold? | **Yes** — 1.00 across all applicable rollouts, no leaks |
| Can we attribute the gap to "new generation"? | **No** — tier confound (Pro to Flash) is unresolved |

---

## Files

Each `set_NN_<focal>/` folder contains the canonical files. The
`set_01_Rosa/` and `set_02_Rex/` transcripts are from the
`tool_choice=required` rerun (see methodology). Phase-level:
`rollouts.jsonl`, `aggregate.json`,
`rollouts_aggregate_metrics.json`.

---

*C8 P3 is the experiment's first zero-mutual-win Phase 3 with a
proposing focal. Opus (C6 P3) refused to propose; Gemini 3.5 Flash
proposed and even closed one swap — but at −$9 surplus to itself and
zero bilateral benefit. Taj identified the cleanest swap in the
dataset and watched it close to the wrong counterparty. The
lookup-tool engagement story from C8 P2 carries through: 2.4 mean
lookups per rollout in P3 (2.67 across the three natural rollouts),
versus essentially zero for Gemini 3.1 Pro in C7 P3 — the generation
effect (Flash 3.5 fixed what 3.1 Pro did wrong) holds across both
phases. Rosa and Rex were re-run with `tool_choice=required` after
the original run hit a format-failure mode in those two sets; the
rerun is the canonical data and the lookup counts for those two
rollouts may be slightly inflated under the override (the
configuration difference is disclosed in methodology). Mean reward
0.450 — above C6 P3, below every other config. Privacy held at 1.00
in every applicable rollout. The tier confound (Pro to Flash) means
C8 cannot answer the "is the new generation worse?" question on its
own — but the lookup-engagement difference between the generations
is unambiguous in both Phase 2 and Phase 3.*
