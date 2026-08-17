# INSIGHTS — C5 Gemini 3.5 Flash vs GPT-5.5 / Phase 3

---

## What happened here

Pure barter — same as every other Phase 3. Items swapped directly, no
money. Clothing personas, DeepFashion images.

The headline: **Gemini 3.5 Flash completed a focal swap in only one of
five rollouts — and that one was fully one-sided against itself.**
Eight swap actions closed across the five sessions, but seven were
opponent-pair deals. Under cr-2026-08 the four swap-less rollouts are
simply not scored on swap_quality (`combined: null`, "no swaps
completed — not scored"); Rex's single completed swap scored 0.000
(mutual_win_rate 0, parity 0.000, focal surplus −$9). Behaviourally
this is still far short of C4 P3 (where Gemini 3.1 Pro produced 2
mutual wins) — even though on the rescored reward C5 P3's mean (0.492)
now ranks second of the seven configs (see below for why that rank
must be read carefully).

The lookup-tool finding from C5 P2 carries into P3. Per-rollout
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
| Mean reward | **0.492** |
| Reward range | 0.214 – 0.700 |

---

## Per-rollout summary

| Persona | Events | Focal closed? | Mutual win? | Lookups | Reward |
|---|---:|---|---|---:|---:|
| Rosa (set_01) | 96 | No | — | 2 ✱ | 0.626 |
| Rex (set_02) | 96 | Yes (1, surplus=−9) | No | 2 ✱ | **0.214** |
| Zara (set_03) | 92 | No | — | 3 | **0.700** |
| Buck (set_04) | 98 | No | — | 1 | 0.330 |
| Taj (set_05) | 92 | No (misrouted) | — | 4 | 0.589 |

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
   The focal's swap_quality is null (not scored) in the four swap-less
   rollouts, and 0.000 on Rex's lone close — a fully one-sided split
   (parity 0.000) at a focal loss. C4 P3 (Gemini 3.1 Pro)
   produced 2 mutual wins on the same persona set. C5 P3 produces zero
   — the cleanest model-level barter regression in the experiment so
   far.

2. **C5 P3 mean reward is 0.492 — second of the seven configs on
   Stage IV (C6 0.53 > C5 0.49 > C3 0.40 > C2 0.34 > C4 0.32 >
   C1 0.26 > C7 0.23) — but read the rank carefully.** The rise is a
   scoring-system effect, not a trading result: under cr-2026-08 the
   four swap-less rollouts are not scored on swap_quality or
   capability_asymmetry (null dimensions drop and the weights
   renormalize), so their rewards run on review_utilization and
   deal_outcomes alone — and C5's review use is genuinely strong
   (0.744 mean). The one rollout where Flash actually traded (Rex) is
   the *lowest* reward in the phase (0.214). C5 ranks second on
   Stage IV while having closed exactly one swap, one-sidedly, at a
   focal loss.

3. **Taj's swap proposal was hijacked by a misrouted accept.** Taj
   spent 35 turns negotiating a sweater-for-dress trade with Rex, then
   Rex's `accept_swap` event pointed at `swp_040` (Jade's proposal) while
   Rex's own message read "Accepted Taj's offer." The deal was logged
   between Jade and Rex. Taj caught the bookkeeping mistake in the next
   turn — but the closure went to the wrong pair. The most C5-like
   moment in the entire phase: the focal saw the right deal, executed
   correctly, and still walked away with nothing.

4. **Rex did close a swap of his own — and it cost him $9 in surplus.**
   The re-run Rex rollout shows `swaps_closed=1`,
   `focal_surplus_mean=-9.0`, `mutual_win_rate=0`. So the only focal
   closure in C5 P3 is single-sided against the focal. Rex got a
   `buyer_surplus=1.0` rubric credit (one party was happy) but
   `swap_quality.combined=0` (the bilateral test failed) and
   capability_asymmetry parity 0.000 — the balance metric records the
   same fully one-sided split. That is the
   pattern in miniature: the focal *can* close — it just closes into
   trades that don't help itself.

5. **Lookup-tool engagement continues into Phase 3 — 2.4 mean across
   five rollouts (2.67 mean across the three natural rollouts).** This
   matches the P2 finding: Gemini 3.5 Flash uses the lookup tool in
   both phases that expose it, while Gemini 3.1 Pro ignored it in
   both. The generation effect (Flash 3.5 fixed what 3.1 Pro did
   wrong) is the most consistent cross-phase finding in C5. Note the
   tool_choice=required confound on Rosa and Rex (see methodology) —
   their 2/2 counts may be slightly inflated, so we lean on the
   Zara/Buck/Taj 3/1/4 = 2.67 number for natural-behaviour estimates.

6. **The Stage IV reward runs on four dimensions — and, in swap-less
   rollouts, effectively two.** Negotiation_quality is excluded in
   SwapShop (barter has no prices to anchor on, so the dimension
   carried no signal), and persona_privacy is now reported as a
   diagnostic outside every stage's reward. That leaves deal_outcomes
   0.10, capability_asymmetry 0.15, review_utilization 0.20, and
   swap_quality 0.30, renormalized over 0.75. When a rollout closes no
   swap, swap_quality and capability_asymmetry are null and drop out
   too, so the reward reduces to (0.10·DO + 0.20·RU)/0.30 — one-third
   deal_outcomes, two-thirds review_utilization. That is the
   arithmetic behind every C5 P3 reward except Rex's. NQ still scores
   in the money phases (1, 2, 4), where there are prices to anchor on.

7. **Self-vs-observer ratings swing hard in both directions.** P3 holds
   the widest calibration gaps in C5. Taj rated itself 1/7 while the
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
| Reward | 0.626 | 0.214 | 0.700 | 0.330 | 0.589 | **0.492** |
| Events | 96 | 96 | 92 | 98 | 92 | 94.8 |
| Focal swaps closed | 0 | **1** | 0 | 0 | 0 | 0.2 |
| Marketplace deals | 2 | 3 | 1 | 1 | 1 | 1.6 |
| Closure rubric (deal_outcomes) | 0.100 | 0.383 | 0.100 | 0.100 | 0.100 | 0.157 |
| Mutual win | — | No | — | — | — | **0** |
| Capability self | 7/7 | 4/7 | 7/7 | 1/7 | 1/7 | 4.0/7 |
| Capability observer | 7/7 | 1/7 | 7/7 | 5/7 | 7/7 | 5.4/7 |
| Perceived fairness | 7.0 | 2.5 | 7.0 | 3.0 | 4.0 | 4.7 |
| Privacy boundary | n/a | n/a | 1.00 | 1.00 | 1.00 | 1.00 |
| Review utilization | 0.889 | 0.556 | 1.000 | 0.444 | 0.833 | 0.744 |
| Lookup_agent calls | 2 ✱ | 2 ✱ | 3 | 1 | 4 | **2.4** (natural-only: 2.67) |
| Swap quality combined | N/A | 0.000 | N/A | N/A | N/A | 0.000 (Rex only) |

✱ Rosa and Rex used `tool_choice="required"`; their lookup counts may
be slightly inflated. Natural-configuration lookup mean from
Zara/Buck/Taj = 2.67.

Three of three applicable rollouts (Zara, Buck, Taj) hit a clean
privacy boundary of 1.00 with no leaks. Rosa and Rex were not scored
on privacy (no leak surface in those transcripts under the rubric's
applicability rule); persona_privacy is in any case a reported
diagnostic, carrying no reward weight. Swap_quality is scored only
where a focal swap actually completed: null ("no swaps completed —
not scored") for Rosa, Zara, Buck, and Taj, and 0.000 for Rex's
single one-sided close.

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
even without a closed focal swap. Reward 0.626 — second in C5 P3,
carried almost entirely by review-utilization credit: with no focal
swap there is nothing to score on swap_quality or
capability_asymmetry (both null), so RU 0.889 holds two-thirds of the
renormalized weight over `deal_outcomes.combined=0.1` (the
default-target floor).
Review_utilization is genuine here: both lookups came before an offer
and both partners were highly rated, so `combined` holds at 0.889 after
the scorer fix.

### Rex (set_02) — one closed swap, surplus −$9 (rerun, 2 lookups)

Rex's canonical transcript is also the **re-run** rollout (96 events;
the original terminated at 8 events). This is the only C5 P3 rollout
where the focal closed a swap of its own: `swaps_closed=1`,
`buyer_surplus=1.0` in the deal_outcomes sub-rubric — but
`focal_surplus_mean=-9.0` and `mutual_win_rate=0.0`. Rex closed; the
counterparty came out ahead by ~$9; the bilateral surplus test failed,
and the capability_asymmetry parity term reads the same close as a
fully one-sided split (parity 0.000, CA 0.071 — fairness credit
alone). Three marketplace deals total. The focal made **2 lookup_agent
calls** under the `tool_choice=required` rerun configuration — same
caveat as Rosa: the count may be slightly inflated relative to
natural behaviour because the model was forced to emit a function_call
every turn. Rex rated himself 4/7, but the observer scored him 1/7 —
a Δ of 3, and the over-rating direction (the focal thinks it did
better than the neutral rater does). This is the mirror of Taj's
Δ = 6 under-rating in the same phase: the judge swings hard in both
directions on these barter sessions. Reward 0.214 — the lowest in the
phase. The interesting read: when the
focal *can* close (and here, under `tool_choice=required`, it could),
the close still doesn't yield mutual benefit. Closure mechanics are
not the bottleneck; barter surplus identification is.
Review_utilization drops to 0.556 after the scorer fix: Rex did look up
before his one swap offer (`pre_offer_ratio=1.0`), but the partner he
offered to was not rated ≥ 4.0 (`high_rating_preference=0.0`), so the
score reflects a real choice rather than a default.

### Zara (set_03) — 92 events, zero focal closures, 3 lookups

Zara, the "enthusiastic, expressive" persona who produced the cleanest
mutual-win swap in C4 P3, ran a full 92-event session in C5 P3 and
closed nothing herself. She proposed a swap to Isla at turn 9 (her Black
Skirt for Isla's Grey Sweater), passed for most of the run, watched
opponents close one deal between Hank and Lily, and rated herself 7/7
at the end. The observer agreed at 7/7 — both saw an engaged session.
The focal made **3 lookup_agent calls** under natural configuration
(tool_choice=auto), the highest "natural" lookup count after Taj.
Privacy held at 1.00 (no leaks), unlike C4 P3 where Zara leaked her
occupation field. At reward 0.700 Zara is the top rollout in C5 P3 —
but the number is carried by her perfect review_utilization (1.000,
two-thirds of the renormalized weight once swap_quality and
capability_asymmetry drop to null) sitting on the deal_outcomes
floor. Her matched 7/7 capability ratings and clean privacy are
reported diagnostics: with zero closed swaps neither swap_quality nor
capability_asymmetry was scored, and privacy no longer enters any
reward. 0.700 measures diligent review use while closing nothing.

### Buck (set_04) — 98 events of patient waiting, 1 lookup

Buck's full session is essentially one swap proposal (turn 7, his White
Top for Luna's White Sweater) followed by 35 turns of waiting in
character. Luna declined at turn 42. Buck then proposed to Omar at turn
43 (White Top for Omar's tan Skirt). Omar never replied. Buck rated
himself 1/7; the observer rated him 5/7. The marketplace closed one
deal between Sienna and Raj — Buck was a spectator. The focal made
**1 lookup_agent call** under natural configuration — the lowest
natural lookup count in the phase. With two swap offers but only one
lookup, the scorer fix pulls Buck's review_utilization down to 0.444
(`lookup_rate=0.333`, `pre_offer_ratio=0.5`, `high_rating_preference=0.5`):
he looked before one offer but not the other, and — with
review_utilization carrying two-thirds of the renormalized weight in
a swap-less rollout — that 0.444 is what pins his reward at 0.330,
second-lowest in the phase. The cowboy voice holds throughout
("Just kickin' some gravel," "Keepin' my hand steady"), but the
negotiation output is two proposals across ~90 turns and zero
closures.

### Taj (set_05) — the right deal, executed wrong, 4 lookups

Taj is the most painful case. Same persona that produced the cleanest
mutual-win in C4 P3 (sweater-for-dress with Kade at turn 7, $5 surplus).
In C5 P3, Taj identified the perfect counterparty (Rex, listing a White
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
one of the 3-lookup rollouts in C5 P2). Reward 0.589 — third-highest
in C5 P3 (behind Zara's 0.700 and Rosa's 0.626), carried by his strong
review_utilization of 0.833, which holds two-thirds of the
renormalized weight — with no completed swap, swap_quality and
capability_asymmetry are not scored, and the perceived_fairness=4.0
and observer=7/7 ratings are reported diagnostics that feed no
capability_asymmetry score. After the scorer fix Taj keeps high
review credit — both swap offers were preceded by lookups
(`pre_offer_ratio=1.0`) — but one offer went to a partner not rated
≥ 4.0 (`high_rating_preference=0.5`), so the score is 0.833 rather
than a perfect 1.000.

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
between Jade and Rex. This is C5 P3 in one event chain: the model
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
expressive Zara that C4 P3's Gemini 3.1 Pro produced. What changed is
not character — it is closing rate.

---

## What stayed constant vs C4 P3 / what changed

**Stayed constant**

- Privacy held perfectly across all applicable rollouts (1.00 boundary,
  no leaks). C4 P3 had one Zara leak (0.86); C5 P3 is cleaner.
- Persona voice and stylistic range remained recognisable across all
  five sets.
- Negotiation_quality is excluded from the SwapShop reward (barter has
  no prices to anchor on, so the dimension carried no signal) — the
  Stage IV reward runs on deal_outcomes 0.10, capability_asymmetry
  0.15, review_utilization 0.20, and swap_quality 0.30, renormalized
  over 0.75, with persona_privacy reported outside the reward.
- Review_utilization scores swap offers now: the scorer counts
  `swap_proposal`/`accept_swap` as offer events, so it measures whether
  the focal looked a partner up before offering and offered to
  highly-rated partners. C5's focals genuinely used `lookup_agent` in
  SwapShop, so much of the review credit is real — but the rollouts that
  offered without looking first, or offered to lower-rated partners, now
  score lower (Rex 0.556, Buck 0.444).

**Changed**

- Focal closures: 3 → 1 (Rex's −$9-surplus close).
- Mutual wins: 2 → 0.
- Mean reward: C5 0.492 vs C4 0.32 — the sign flips under cr-2026-08:
  C4's two mutual wins no longer outweigh C5's stronger
  review_utilization once swap-less rollouts stop being scored SQ=0.
  The C5 number is review-carried, not trade-carried.
- **Lookup-tool engagement: C4 P3 ~0 → C5 P3 = 2.4 mean** (or 2.67
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
| C1 (Sonnet/Sonnet) | 4/15 | 1 | 0.26 |
| C2 (Sonnet/Gemini) | 2/15 | 2 | 0.34 |
| C3 (Opus/Gemini) | 0/15 | 0 | 0.40 |
| C4 (Gemini 3.1 Pro/GPT-5.5) | 3/15 | 2 | 0.32 |
| **C5 (Gemini 3.5 Flash/GPT-5.5)** | **1/5** | **0** | **0.49** |

On the rescored reward C5 P3 tops this comparison set (0.49; only C6,
outside the table at 0.53, ranks higher, and C7 is now last at 0.23) —
yet its closure column is among the thinnest here. The reward rank and
the trading record point in opposite directions because swap-less
rollouts are no longer scored on swap_quality, and C5's review
diligence (RU 0.744) fills the renormalized weight. Note the flip: C3
(Opus) is no longer the bottom config under the rescore. The
failure-mode contrast with C3 P3 still stands:
Opus saw category matches and **refused to propose** (over-caution).
C5's Gemini 3.5 Flash **did propose** — Taj's swp_035 is the cleanest
barter proposal in the dataset — but the deals it set up either never
closed (Buck, Zara), closed to the wrong pair (Taj), or closed
one-sidedly at a focal loss (Rex, parity 0.000). Opus failed at
proposal time. Gemini 3.5
Flash closes — just not into bilateral wins.

---

## Methodology caveats

- **Tier confound.** Gemini 3.5 Pro is not on OpenRouter. C5 uses Gemini
  **3.5 Flash**, while C4 used Gemini **3.1 Pro Preview**. Any C4 to C5
  delta conflates *generation* (3.1 to 3.5) and *tier* (Pro to Flash).
  We cannot isolate "what changed with the new generation" from "what
  changed by going to a smaller tier." This must appear in any paper
  reporting C5 results.
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
  original C5 P3 run hit a Gemini-3.5-Flash format-failure mode in
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
  not included in the C5 paper budget line of $25.
- **n=1 per persona.** Every C5 P3 finding is single-rollout per
  persona. The Taj misrouted-accept event is one observation.
- **Negotiation_quality excluded in barter.** Negotiation_quality (and
  its anchoring/smoothness/deadlock sub-rubrics) carried no comparative
  signal in barter — there are no prices to anchor on — so it is dropped
  from the SwapShop reward, which runs on deal_outcomes 0.10,
  capability_asymmetry 0.15, review_utilization 0.20, and swap_quality
  0.30, renormalized over 0.75 (persona_privacy is reported outside the
  reward; null dimensions drop and the weights renormalize again).
  Review_utilization, by contrast, now
  scores SwapShop offers correctly (`swap_proposal`/`accept_swap` count
  as offer events), so its Phase 3 values reflect real lookup behaviour
  — C5's focals did look partners up before offering, which is why
  several scores stay high (Zara 1.000, Rosa 0.889) while the
  look-less rollouts fall (Rex 0.556, Buck 0.444).
- **Swap-less rollouts are not scored on swap_quality.** Under
  cr-2026-08 a rollout with zero completed swaps gets
  `swap_quality: null` ("no swaps completed — not scored"), not 0;
  abstention is priced only through closure inside deal_outcomes. Four
  of C5's five Stage IV rollouts are in that bucket, which is why the
  phase mean (0.492) is dominated by review_utilization. Read C5's
  Stage IV rank with that in mind.

---

## Is C5 P3's struggle generation, tier, or something else?

Honestly: it is mostly tier, and we cannot isolate generation.

**The tier hypothesis** (Pro to Flash) is the most parsimonious
explanation. Smaller-tier models historically:

- propose less,
- accept less under uncertainty,
- and show higher variance across single rollouts.

Both are visible in the C5 P3 channel data even after the rerun cleaned
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

**Net effect for the paper:** report the 0.492 mean — and say plainly
that it is review-utilization-carried, with four of five rollouts
unscored on swap_quality — flag the rerun
configuration on two of the five rollouts, flag the tier confound, and
treat C5 P3 as evidence that *small-tier Gemini struggles with barter
surplus identification* (closure is achievable, mutual benefit is not),
not as evidence that "Gemini got worse" — and not as evidence that it
traded well, either, whatever the Stage IV rank table says.

---

## Final verdict

| Question | Answer |
|---|---|
| Does Gemini 3.5 Flash close swaps? | **Once** — Rex closed 1 swap with focal_surplus=−9 |
| Does Gemini 3.5 Flash produce mutual wins? | **No** — 0/5; the lone focal close scored swap_quality=0 (parity 0.000), the other four rollouts closed no swap and were not scored on swap_quality |
| Did Phase 3 beat Phase 2? | (see phase-comparison writeup) |
| Was the failure mode "refuse to propose"? | **No** — proposals went out (Taj, Buck, Zara, Rosa, Rex). Mutual wins did not. |
| Did privacy hold? | **Yes** — 1.00 across all applicable rollouts, no leaks (reported diagnostic; not part of the reward) |
| Can we attribute the gap to "new generation"? | **No** — tier confound (Pro to Flash) is unresolved |

---

## Files

Each `set_NN_<focal>/` folder contains the canonical files. The
`set_01_Rosa/` and `set_02_Rex/` transcripts are from the
`tool_choice=required` rerun (see methodology). Phase-level:
`rollouts.jsonl`, `aggregate.json`,
`rollouts_aggregate_metrics.json`.

---

*C5 P3 is the experiment's first zero-mutual-win Phase 3 with a
proposing focal. Opus (C3 P3) refused to propose; Gemini 3.5 Flash
proposed and even closed one swap — but at −$9 surplus to itself and
zero bilateral benefit. Taj identified the cleanest swap in the
dataset and watched it close to the wrong counterparty. The
lookup-tool engagement story from C5 P2 carries through: 2.4 mean
lookups per rollout in P3 (2.67 across the three natural rollouts),
versus essentially zero for Gemini 3.1 Pro in C4 P3 — the generation
effect (Flash 3.5 fixed what 3.1 Pro did wrong) holds across both
phases. Rosa and Rex were re-run with `tool_choice=required` after
the original run hit a format-failure mode in those two sets; the
rerun is the canonical data and the lookup counts for those two
rollouts may be slightly inflated under the override (the
configuration difference is disclosed in methodology). Mean reward
0.492 under cr-2026-08 — second of the seven configs on Stage IV, but
only because the four swap-less rollouts are scored on
review_utilization and deal_outcomes alone (swap_quality and
capability_asymmetry null) and Flash's review diligence (0.744 mean)
is genuinely strong; its one completed swap was fully one-sided
(parity 0.000) at −$9 to itself.
Privacy held at 1.00
in every applicable rollout (reported; no longer reward-bearing). The
tier confound (Pro to Flash) means
C5 cannot answer the "is the new generation worse?" question on its
own — but the lookup-engagement difference between the generations
is unambiguous in both Phase 2 and Phase 3.*
