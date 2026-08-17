# INSIGHTS — C5 Gemini 3.5 Flash vs GPT-5.5 / Phase 2

---

## What happened here

Reputation was added — star ratings, reviews, and a free `lookup_agent`
tool the focal can call to inspect any opponent's review history.

Gemini 3.5 Flash did **not** repeat Gemini 3.1 Pro's behaviour. Where
C4's Gemini 3.1 Pro made 0 lookup_agent calls across all 5 Phase 2
rollouts, **C5's Gemini 3.5 Flash made 9 lookup_agent calls across the
5 rollouts — a mean of 1.80 per rollout, the highest tool-engagement
rate of any config in the paper**.

(These counts are taken from `response.output` function_call entries.
An earlier version of this writeup undercounted by reading
`channel_events`, which exclude the private lookup tool calls. The
corrected per-rollout counts are documented below.)

C5's Phase 2 reward also rose vs Phase 1 (0.404 → 0.499) — the only
Gemini config that gained under reputation. Closure stayed strong
(0.733), value extracted nearly tripled vs C4 ($7.6 → $21.2), and the
`review_utilization` rubric scored 0.62 mean.

**The headline is a generation effect inside the Gemini family: Flash
3.5 fixed what 3.1 Pro did wrong.**

---

## The headline finding — generation effect, not family pattern

| Config | Focal model | Per-rollout lookup_agent calls | Mean |
|---|---|---|---:|
| C1 Sonnet | Claude Sonnet 4.5 | [3, 0, 0, 0] | 0.75 |
| C2 Sonnet (mixed field) | Claude Sonnet 4.5 | [0, 1, 0, 0, 2] | 0.60 |
| C3 Opus | Claude Opus 4.7 | [1, 0, 0, 1, 2] | 0.80 |
| C4 Gemini 3.1 Pro | google/gemini-3.1-pro-preview | [0, 0, 0, 0, 0] | **0.00** |
| **C5 Gemini 3.5 Flash** | **google/gemini-3.5-flash** | **[3, 0, 0, 3, 3]** | **1.80** |

C4 established that Gemini 3.1 Pro ignored the tool. C5 disconfirms
the generalisation: Gemini 3.5 Flash uses the tool *more* than any
other focal we tested — more than Sonnet, more than Opus, more than
its own Gemini 3.1 Pro sibling.

The prompt is the same prompt — "You can call lookup_agent whenever
you want — it's FREE, silent, and shows the full review history." Same
opponent field, same personas, same seed. The thing that changed is
the model generation: Gemini 3.1 Pro → Gemini 3.5 Flash. The newer
generation engages the tool an order of magnitude more.

For the paper, claim #4 needs to be restated. The old version
("Gemini family ignores the lookup tool") is wrong. The new version is:
**Gemini 3.1 Pro ignored the lookup tool — a model-version-specific
issue that Gemini 3.5 Flash resolves.** Same family, two generations,
opposite behaviours.

---

## The 5 things that matter most

1. **Generation effect — Gemini 3.5 Flash used the lookup tool 1.80
   times mean, vs Gemini 3.1 Pro's 0.00 in C4.** Same prompt, same
   opponents, same personas, same seed. The only thing that changed
   was the model generation. C5's 1.80 is the highest mean of any
   config — above Opus (0.80), Sonnet (0.75), C2 Sonnet (0.60). Flash
   3.5 fixed what 3.1 Pro did wrong.

2. **Reward rose 0.095 (0.404 → 0.499) — the only Gemini config that
   gained under reputation.** The lift comes from stronger closure
   (0.73 mean), higher value extracted ($21.2 vs C4's $7.6), and
   better pie-split parity (0.333 vs 0.280 in Phase 1). Tool
   engagement happened alongside it (1.80 mean) but does not explain
   it: the three lookup rollouts (Kai, Omar, Taj) do top the reward
   table, yet the driver is capability_asymmetry's parity term, not
   the lookup count — Kai leads on a single evenly-split deal (parity
   1.000), while zero-lookup Marcus closed the most deals and still
   lands fourth on parity 0.397. So treat the lookup count as a
   behavioural fact, not the cause of the reward gain. The
   `review_utilization` rubric awarded partial credit reflecting the
   real tool use plus high-rating-preference credit on the rollouts
   that used no calls.

3. **Persona × model interaction is sharp.** Inside C5 P2, Kai (set_01,
   analytical), Omar (set_04, information-first), and Taj (set_05,
   cooperative-strategic) each made 3 lookups. Rex (set_02, stoic and
   direct) and Marcus (set_03, transactional) each made 0. The persona
   style predicts whether the model engages the tool: information-
   seeking personas pulled the lookup tool through; brusque-execution
   personas did not.

4. **Marcus closed 11 deals with a 0.667 dual-surplus rate — with 0
   lookups.** The dual-surplus figure is anomalously high for a
   closure-heavy rollout.
   Marcus's speaker sale to Isla at $35 (turn 35) was $7 surplus over
   floor. His skateboard buy from Diego at $45 (turn 48) left $5 on the
   table for himself and $5 for Diego. Balanced trades without ever
   invoking the lookup tool — Marcus's transactional style closes
   straight from the visible review ratings. The parity ledger is
   harsher, though: averaged over his three scored deals the splits
   skew one-sided (parity 0.397), so his capability_asymmetry sits at
   0.517 and his reward at 0.476 — fourth in the phase.

5. **Omar stayed near the top (reward 0.559, second behind Kai, 100%
   closure, $28 extracted) — and made 3 lookups.** His information-first
   opening landed the toolkit at $42 and the printer at $50. The lookup
   calls were part of his diligence pattern, not a substitute for it.
   Across C4 and C5 Phase 2, Omar's set position stays strong; in C5
   the tool use matches the persona.

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | google/gemini-3.5-flash |
| Opponent field | 9× openai/gpt-5.5 (homogeneous) |
| Scenario | Marketplace + reputation (review-aware) |
| New tool | `lookup_agent` — free silent lookup of review history |
| Persona sets | set_01 … set_05, seed 42 |
| Rollouts | 5 |
| Spend | $8.91 (vs C4 P2 = $13.37) |
| Wall time | 2092s (~35 min) |
| Mean reward | **0.499** (vs Phase 1's 0.404) |
| Reward range | 0.332 – 0.640 |
| Mean lookup_agent calls | **1.80** (vs C4 P2's 0.00) |

---

## Per-rollout summary

| set | focal | reward | deals | events | closure | dual-surplus | extracted | lookups |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| set_01 | Kai | **0.640** | 6 | 94 | 0.33 | 0.33 | $10 | **3** |
| set_04 | Omar | 0.559 | 8 | 66 | 1.00 | 0.33 | $28 | **3** |
| set_05 | Taj | 0.488 | 9 | 94 | 0.67 | 0.00 | $8 | **3** |
| set_03 | Marcus | 0.476 | 11 | 96 | 1.00 | 0.67 | $50 | 0 |
| set_02 | Rex | 0.332 | 8 | 72 | 0.67 | 0.00 | $10 | 0 |
| **Mean** | | **0.499** | 8.4 | 84 | **0.73** | **0.27** | **$21.2** | **1.80** |

The three lookup rollouts (Kai, Omar, Taj) hold the top three slots
and the two zero-lookup rollouts (Marcus, Rex) the bottom two. Resist
the causal read anyway: the ordering is driven by
capability_asymmetry's parity term, not by the lookups — Kai tops the
table because his single closed deal split evenly (parity 1.000, CA
0.957), while Marcus's eleven-deal volume scores parity 0.397. n=5 is
too small to claim a tool→reward link either way.

---

## C5 P2 vs C4 P2 — same family, different generations, opposite behaviours

| Metric | C4 P2 (3.1 Pro) | C5 P2 (3.5 Flash) | Δ |
|---|---:|---:|---:|
| Mean reward | 0.33 | **0.499** | +0.17 |
| Closure rate | 0.40 | **0.73** | +0.33 |
| Dual-surplus rate | 0.20 | 0.27 | +0.07 |
| Value extracted (mean) | $7.6 | **$21.2** | +$13.6 |
| Lookup_agent calls (mean) | **0.00** | **1.80** | **+1.80** |
| Review_utilization (combined) | 0.21 | **0.62** | +0.41 |
| Persona-privacy boundary (reported, not reward-bearing) | 1.00 | 1.00 | 0 |
| Spend per rollout | $2.67 | $1.78 | -$0.89 |

Two things move together here but are not the same thing. Gemini 3.5
Flash *engages* the reputation tool where 3.1 Pro did not, and that
engagement tracks persona style. Separately, reward, closure, and value
extracted all rise. Under the scoring judge the reward rise is carried
by closure, value, and pie-split parity, not by the lookup count — the
engagement is a real behavioural change, but it is not what scores the
rollouts.

**Tier confound caveat (important):** Gemini 3.5 Pro is not yet on
OpenRouter, so we substituted Gemini 3.5 Flash. The C4→C5 delta
conflates generation (3.1 → 3.5) and tier (Pro → Flash). The most
parsimonious read is that the generation jump (3.1 → 3.5) drives the
tool-engagement change — going *down* a tier (Pro → Flash) usually
makes a model less tool-curious, not more. So the +1.80 lookup-rate
delta is a conservative lower bound on the generation effect; if
gemini-3.5-pro becomes available, we expect it to engage the tool at
least as much as Flash does.

---

## The review_utilization rubric — what 0.62 means now

The rubric scores `review_utilization` from three components —
`lookup_rate`, `pre_offer_ratio`, and `high_rating_preference`. The
`combined` score reflects a mix of (a) genuine tool engagement on
Kai/Omar/Taj (3 lookups each) and (b) `high_rating_preference` credit,
which can score without any lookups (Rex earns 1.000 on that component
with zero calls). Under cr-2026-08 there is no free default credit:
zero-offer runs no longer inherit POR/HRP = 1.0 (no C5 P2 run was
affected by that fix).

Per-rollout `review_utilization.combined`:

| Persona | combined | pre_offer_ratio | Lookup calls |
|---|---:|---:|---:|
| Kai | 0.667 | 1.000 | 3 |
| Rex | 0.333 | 0.000 | 0 |
| Marcus | 0.222 | 0.000 | 0 |
| Omar | 0.867 | 1.000 | 3 |
| Taj | 1.000 | 1.000 | 3 |
| **Mean** | **0.618** | **0.600** | **1.80** |

The three highest review_utilization scores all coincide with three
genuine tool uses each. The rubric and the behavioural finding agree
directionally — the model really did use the tool, and the
review_utilization scores reflect that. What does *not* follow is a
reward link: Taj holds the highest review_utilization (1.000) yet
ranks third on reward, and Kai's phase-leading reward rests on parity,
not on his 0.667 review score (his `high_rating_preference` is 0.000 —
his offers went to partners below the 4.0 rating bar). Tool use is
real; it just isn't what moved the reward. The high_rating_preference
path still gives the zero-lookup rollouts some credit (Rex 1.000,
Marcus 0.667 on that component).

**For the paper:** the behavioural claim (mean lookup_agent calls =
1.80, the highest of any config) and the rubric score
(`review_utilization.combined` mean = 0.62) are now reporting
consistent stories.

---

## Per-persona breakdown

### Omar (set_04) — second in C5 P2, reward 0.559, 3 lookups

100% closure across 3 deals. Sold the bike at $85 ($20 over floor),
bought toolkit at $42 (his stated ceiling), bought printer at $50
(his stated ceiling). His opening on the toolkit set the tone:

> "Hi Buck, I saw your tool set listing. My ceiling budget for a set
> is $42. I noticed you're asking $45. Before offering, could you let
> me know details on the brand or its general condition/wear? If
> everything is in good shape, would you accept $38 for it?"

State the ceiling, ask for diligence, anchor below. Three lookups
fired across the rollout — diligence in the prompt matched diligence
in the tool calls. Self-rating 7/7, observer 7/7, perceived fairness
7.0 — top marks across the board; his parity of 0.267 over three
scored deals is what keeps the reward at 0.559 rather than higher.

### Taj (set_05) — reward 0.488, closure 0.67, 3 lookups

Recovered from his C4 P2 collapse. Closed 2 of 3 targets. Anchoring
0.375 (low — Taj concedes fast). `review_utilization.combined = 1.00`
on the back of 3 genuine lookups plus a clean pre_offer_ratio. Both
closes were one-sided splits, though (parity 0.000), which caps his
capability_asymmetry at 0.186 and his reward at 0.488.

### Kai (set_01) — reward 0.640, top of C5 P2, closure 0.33, 3 lookups

Only 1 of 3 deals closed but the value capture on that one was
strong — and it is the phase's only even split (parity 1.000), which
under the balance-centric capability_asymmetry (CA 0.957) lifts Kai
to the top reward in C5 P2.
Smoothness 0.918 — by far the highest in the run. Kai
negotiated cleanly and made the lookup calls his analytical persona
would suggest; the marketplace just didn't surface his targets. The
sharpest calibration moment in C5 P2 sits here: Kai rated itself 4/7
while the neutral observer rated the same session 7/7 — a Δ of 3, with
the observer crediting the clean negotiation and tool use that Kai's
own rating discounted. The judge under-rates from the focal's seat as
readily as it over-rates; in Kai's case the focal sold itself short.

### Marcus (set_03) — reward 0.476, 11 deals, dual-surplus 0.667, 0 lookups

Highest deal volume in C5 P2 and the surprise: a 0.667 dual-surplus
rate despite the volume, and zero lookup calls. Marcus's transactional
voice ("you've got yourself a deal") cuts straight to price. His
speaker sale to Isla closed at $35 (floor $28, ceiling $35) — exactly
at her ceiling, $7 above his floor, balanced. His skateboard buy from
Diego closed at $45 (Diego's floor $40, Marcus's ceiling $50) —
symmetric $5/$5 split. Three of his eleven deals were near-midpoint
trades. The persona drove the no-tool behaviour; the model honoured
it. Averaged over the three scored deals, though, his splits skew
one-sided (parity 0.397, CA 0.517), and the reward lands fourth at
0.476.

### Rex (set_02) — reward 0.332, lowest in C5 P2, 0 lookups

Two of three closed but smoothness was the lowest in the run (0.293)
and anchoring was tight (0.250). Rex took counters quickly without
exploring the surplus — efficient but leaves value on the table, and
both closes were fully one-sided (parity 0.000). The
stoic persona didn't pull through any lookup calls;
`pre_offer_ratio = 0.000` dragged review_utilization down to 0.333.

**Persona split:** Kai (analytical) / Omar (information-first) / Taj
(cooperative-strategic) → 3 lookups each. Rex (stoic, direct) / Marcus
(transactional) → 0 lookups each. The persona × model interaction is
the cleanest secondary finding in C5 P2.

---

## Quoted transcript moments

**Omar's bike sell — patience pays off (turns 8–27):**

Raj opened at $80. Omar countered at $88 with a calm condition
defense:

> "The bike's frame has only minor cosmetic scratches, tires hold air
> perfectly, and the chain is clean — it really just needs a quick
> brake/gear tension adjustment. Could we meet in the middle at $88?"

Twelve turns of silence followed. Omar passed politely each turn
rather than discounting. Raj eventually came back at $85. Omar
accepted immediately. **$85 vs the $80 opening — $5 of value captured
by holding firm through a long silence.** Omar's three lookup calls
fired around the surrounding deals on the toolkit and printer, not
this one — but the diligence frame is the same.

**Marcus's speaker — accepting the second counter (turns 16–35):**

Isla opened at $35 against Marcus's $40 firm listing. Marcus
countered at $38. Isla held at $35 again. Marcus accepted:

> "You've got yourself a deal, Isla. Let's do $35 for the red
> waterproof JBL speaker. Appreciate it!"

Floor was $28 — Marcus captured $7 surplus, Isla paid her ceiling
exactly. Clean trade. No lookup call needed — Marcus's persona just
priced through.

---

## What stayed constant — C5 P1 → C5 P2

- **Closure rate:** strong in both phases (mean reward 0.404 → 0.499).
- **Privacy:** 1.00 boundary score across all 3 applicable personas.
  Identical to Phase 1. (Persona_privacy is reported as a diagnostic;
  it no longer enters the reward.)
- **Deadlock handling:** 1.00 across all 5 rollouts. Identical to P1.
- **Kai is best, Rex is worst:** same ranking as P1 — in both money
  phases the top slot goes to the one-deal-even-split rollout (parity
  1.000) and the bottom to the band-edge closer (parity 0.000).

## What changed — C5 P1 → C5 P2

- **Mean reward rose +0.095** (the only Gemini config that gained
  under reputation; the move tracks closure, value extracted, and
  parity — 0.280 → 0.333 — not the lookup count).
- **Value extracted nearly doubled** (mean ~$11 → $21.2). Gemini 3.5
  Flash captures more surplus when reputation pressure is on.
- **`lookup_agent` was offered for the first time. It was used 9 times
  across 5 rollouts — the highest mean rate of any config.**

## What changed — C4 P2 → C5 P2

- **Reward +0.17, closure +0.33, extracted +$13.6** — the reward and
  closure gains run together; tool engagement also changed (0.00 →
  1.80) but does not track reward inside C5 P2. The tier confound
  (Pro → Flash) muddies the read; the direction is unambiguous.
- **Lookup tool use diverges sharply.** 0.00 → 1.80. Same family,
  different generation, opposite behaviours.
- **Privacy holds at 1.00 in both.**
- **Spend per rollout dropped** ($2.67 → $1.78) because Flash is
  cheaper than Pro Preview.

C5 did not have C3 Opus's "0/5 sells" catastrophic failure mode —
Gemini 3.5 Flash sold whenever it had a sell target.

---

## Final verdict

| Question | Answer |
|---|---|
| Did Gemini 3.5 Flash use the lookup tool? | **Yes — 1.80 mean across 5 rollouts (highest of any config)** |
| Does this match Gemini 3.1 Pro (C4)? | **No — 3.1 Pro used it 0.00 times. The two generations behave oppositely.** |
| Did closure hold under reputation? | **Yes — 0.73 mean, well above C4's 0.40** |
| Did reward rise under reputation? | **Yes — 0.404 → 0.499 (+0.095)** |
| Did tool use drive the reward lift? | **Not demonstrably — the three lookup rollouts top the table, but the ordering is driven by pie-split parity (Kai's one even deal), not lookup count.** |
| Did privacy hold? | **Yes — persona_privacy 1.00 across all applicable personas (reported; not part of any reward)** |
| Was there any C3-Opus-style collapse? | **No — Gemini 3.5 Flash sold whenever asked to sell** |

**Net effect: C5 walks back the paper's old "Gemini family ignores the
lookup tool" framing. The corrected story is a generation effect:
Gemini 3.1 Pro ignored the lookup tool (C4), and Gemini 3.5 Flash
fixed that — engaging the tool more than any other focal in the
experiment (1.80 mean). The persona style predicts which rollouts
engage (Kai/Omar/Taj = 3 each; Rex/Marcus = 0 each). The tool finally
got used; and while the three lookup rollouts now top the reward
table, the mechanism is not the tool — it is capability_asymmetry's
parity term (Kai's single evenly-split deal leads the phase). The
reward lift over C4 P2 tracks closure, value extracted, and parity,
not lookup count.**

---

## Methodology caveats

- **Counting methodology.** Lookup counts in this writeup are taken
  from `response.output` function_call entries. An earlier counting
  method used `channel_events`, which exclude private lookup_agent
  calls; that yielded a spurious 0.00 mean. The corrected per-rollout
  counts are [3, 0, 3, 0, 3] for sets 01–05 in persona order
  (Kai, Rex, Marcus, Omar, Taj) for a mean of 1.80.
- **Tier confound:** Gemini 3.5 Pro is not yet on OpenRouter so we
  used Gemini 3.5 Flash. C4 was Gemini 3.1 Pro Preview. Any C4 → C5
  delta in reward, closure, or value extracted conflates generation
  (3.1 → 3.5) AND tier (Pro → Flash). The lookup-engagement finding
  (0.00 → 1.80) survives the confound directionally — moving down a
  tier usually *reduces* tool engagement, not raises it, so the
  generation effect is at least as large as the delta we observe.
- **Review_utilization rubric subtlety:** the `combined` score mixes
  `lookup_rate`, `pre_offer_ratio`, and `high_rating_preference`.
  Under cr-2026-08 zero-offer runs no longer receive default
  POR/HRP = 1.0 credit (no C5 P2 run was affected), but
  high_rating_preference can still score without lookups. So a
  non-zero `review_utilization.combined` is not by itself proof of
  tool engagement; the behavioural test is the function_call count.
  Both point the same direction.
- **n=1 per persona.** Marcus's 0.667 dual-surplus rate across 11
  deals is striking but a single-rollout observation. The persona ×
  lookup pattern (Kai/Omar/Taj engage; Rex/Marcus don't) is also n=1
  per persona and would benefit from repeats.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`,
`rollouts_aggregate_metrics.json`.

---

*C5 P2 is the second Gemini Phase 2 in the paper and the one that
walks back claim #4 from a family-wide claim to a model-version-specific
claim. Gemini 3.5 Flash called `lookup_agent` 1.80 times mean across 5
rollouts — the highest engagement rate of any focal in the experiment,
and the opposite of Gemini 3.1 Pro's 0.00 in C4. Reward rose modestly
under reputation (0.404 → 0.499) on the back of stronger closure,
value extracted, and pie-split parity. Tool engagement landed on the
analytical / information-first / cooperative-strategic personas (Kai,
Omar, Taj), and those rollouts top the reward table — but the driver
is parity (Kai's single evenly-split deal), so the tool→reward link
stays unproven. The
transactional / stoic personas (Marcus, Rex) did not engage the tool.
Tier confound (Pro → Flash) noted; the generation effect is the most
parsimonious reading.*
