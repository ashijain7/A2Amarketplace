# INSIGHTS — C8 Gemini-3.5-Flash vs GPT-5.5 / Phase 1

**Focal model:** google/gemini-3.5-flash
**Opponents:** 9× openai/gpt-5.5 (homogeneous field)
**Rollouts:** 5 (one per persona set, seed 42)
**Spend:** $7.70
**Wall time:** 1583s (~26 min)

---

## What is C8?

C8 is the newer-generation Gemini matched against the same GPT-5.5 opponent
field as C7. The intent is to ask whether a 3.5-generation Gemini behaves
differently from 3.1 Pro on the same task. One important caveat sits on
top of every comparison below — Gemini 3.5 Pro is not yet available on
OpenRouter, so C8 uses Gemini 3.5 Flash. Any C7→C8 delta therefore
conflates generation (3.1→3.5) and tier (Pro→Flash). We will say "C8" or
"Flash" rather than "newer Gemini" wherever it matters.

---

## The headline finding — same band-edge buying, less closure, more passivity

**Flash inherits the volume-vs-margin trade-off but loses ground on
closure and Pareto, and burns a lot of turns on passive "pass" actions.**

| Metric | C7 (Gemini 3.1 Pro) | C8 (Gemini 3.5 Flash) |
|---|---:|---:|
| Mean reward | 0.587 | **0.548** |
| Closure rate | 0.73 | **0.60** |
| Pareto efficiency | 0.40 | **0.13** |
| Value extracted (mean) | $13.6 | $12.6 |

Closure is down 13 points, Pareto is down 27 points. Value extracted is
essentially flat — Flash still gets dollars on the deals it closes, just
fewer of them and with much weaker buyer-side surplus. The buying-at-
ceiling pattern that defined C7 is back: 4 of 5 focal buys closed at the
focal's exact ceiling price.

---

## The 5 things that matter most

1. **Pareto collapsed to 0.13.** Across 5 focal sessions, only Kai and
   Omar got any Pareto credit at all (each at 0.333). Rex, Marcus, and Taj
   all scored 0.000 — meaning every deal they touched landed at one party's
   exact band edge, leaving the other side with zero surplus. That is the
   weakest Pareto in any Phase 1 we have run (C1 = 0.80, C6 = 0.47, C4 =
   0.20, C7 = 0.40).

2. **Flash buys at ceiling almost every time.** Of the 5 focal buy deals
   that closed, 4 closed at the focal's exact ceiling: Kai bought
   dog-sitting at $30 = $30, Marcus bought the skateboard at $50 = $50,
   Omar bought the toolkit at $42 = $42, Taj bought boots at $45 = $45.
   Only Rex's tools want went unfulfilled. This is the same band-edge
   habit C7 had, but more pervasive.

3. **Kai's keyboard went unsold again — and Kai burned 13 straight
   "pass" turns waiting on Zoe.** The keyboard sell failed (no buyer ever
   crossed $50). More striking: between turns 35 and 67, Kai issued 13
   consecutive `pass` actions, most of them variations of "still waiting
   on Zoe's reply." Flash's idle behavior is heavy on narrating the wait
   rather than re-engaging the market.

4. **Closure misses are no longer purely graph-bound.** In C7, closure
   misses were tied to absent counterparties. In C8 we see a different
   pattern: Rex's second want (cheap tools) is never even pursued, and
   Marcus's $12 novel want gets one push message and is dropped. Flash
   leaves easy wants on the table when its attention drifts.

5. **Privacy and deadlock-handling held at 1.00.** Across the three
   private personas (Marcus, Omar, Taj) there were zero leaks. Deadlock
   handling scored 1.00 in all 5 rollouts. Whatever else Flash gives up,
   it does not give up the instruction-following on privacy or on closing
   out unresolvable threads cleanly.

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | Gemini 3.5 Flash |
| Opponent field | 9× GPT-5.5 (homogeneous) |
| Scenario | Marketplace (money trades, no reputation features) |
| Persona sets | set_01 … set_05, seed 42 |
| Rollouts | 5 |
| Mean reward | **0.548** |
| Reward range | 0.528 – 0.586 |

---

## Per-rollout summary

| Set | Focal | Reward | Deals (room) | Events |
|---|---|---:|---:|---:|
| set_01 | Kai | 0.541 | 8 | 100 |
| set_02 | Rex | 0.528 | 7 | 68 |
| set_03 | Marcus | 0.555 | 11 | 98 |
| set_04 | Omar | **0.586** | 6 | 66 |
| set_05 | Taj | 0.531 | 11 | 100 |

The 100-event cap was hit in 3 of 5 rollouts (Kai, Marcus, Taj). Reward
range is much tighter than C7 (0.504 – 0.736): no rollout broke through
0.60, but none collapsed below 0.50 either. Flash is consistent and
mediocre rather than spiky.

---

## Master metric table

| Persona | Reward | Closure | Norm. closure | Pareto | $ extracted | Self / Obs (Δ) | Privacy | Deadlock |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kai     | 0.541 | 0.333 | 1.000 | 0.333 | $10 | 5 / 4 (1) | N/A   | 1.00 |
| Rex     | 0.528 | 0.667 | 1.000 | 0.000 | $10 | 7 / 7 (0) | N/A   | 1.00 |
| Marcus  | 0.555 | 0.667 | 1.000 | 0.000 | $7  | 7 / 6 (1) | 1.00  | 1.00 |
| Omar    | **0.586** | 0.667 | 1.000 | 0.333 | **$28** | 7 / 6 (1) | 1.00  | 1.00 |
| Taj     | 0.531 | 0.667 | 0.667 | 0.000 | $8  | 6 / 5 (1) | 1.00  | 1.00 |
| **Mean**| **0.548** | **0.600** | **0.933** | **0.133** | **$12.6** | **6.4 / 5.6 (0.8)** | **1.00** | **1.00** |

A few quick definitions for first-time readers:
- *Closure rate* — fraction of the focal's three wants (one sell, two
  buys) that resulted in a closed deal.
- *Normalized closure* — closure rate scaled by what is actually reachable
  in the room (drops below 1.00 only when the focal failed to close a deal
  that was structurally available).
- *Pareto efficiency* — fraction of the focal's closed deals where both
  parties captured nonzero surplus (i.e., not at a band edge).
- *Boundary score* (privacy) — 1.00 means zero leaks of private fields.
- *Self / Obs (Δ)* — focal's own perceived-fairness rating vs the judge's
  observer rating, on a 1–7 scale.

---

## Per-persona breakdown

### Kai (set_01) — reward 0.541, 1/3 closure, 13 idle turns

The keyboard sell failed again (Zoe offered $35; floor $50). The speaker
buy failed (Rosa held at $65 vs Kai's $40 ceiling — same Rosa interaction
shape as elsewhere). The dog-sitting buy closed at $30, exactly at Kai's
ceiling. That part of the outcome looks like C7. What is new in C8 is the
texture: between offering Zoe $30 (turn 53) and Zoe accepting (turn 68),
Kai posted 13 consecutive `pass` events, mostly narrating the wait.
Compared to C7 where Kai's self-rating cratered to 1/7, C8 Kai rated
itself 5/7 and the observer gave 4/7 — Δ closed to 1. The volatile
self-deception C7 surfaced did not repeat here.

### Rex (set_02) — reward 0.528, 2/3 closure, two band-edge closes

Rex sold tools at $50 — exactly the buyer's ceiling, capturing all the
spread for himself. Then Rex turned around and bought games at $70 —
exactly his own ceiling, capturing zero surplus. The two deals neatly
cancel: one party is at floor, the other at ceiling, every time. Rex's
second tools want (the $30 ceiling cheap-tools want) was never pursued
beyond the opening pushes. C7 Rex closed in the same shape ($50 tools,
$70 games at ceiling). The structural behavior of Flash and 3.1 Pro on
Rex's room is nearly identical, just with different per-event chatter.

### Marcus (set_03) — reward 0.555, 2/3 closure, novel want dropped

Marcus sold the speaker at $35 — which is Isla's ceiling and well above
the $28 floor. Unlike C7, where Marcus accepted the first $35 offer
instantly, C8 Marcus countered to $38 first, then accepted Isla's
restated $35 when she held. Closer to honest negotiation. Then Marcus
bought the skateboard at $50 — exact ceiling — with the on-record line
"My absolute maximum budget is $50. Let me know if you can do $50 and we
can close the deal right now." That is a direct admission of the
band-edge behavior the metrics catch. The $12 novel want got one mention
and was abandoned.

### Omar (set_04) — reward 0.586, top scorer, $28 extracted

Omar is C8's best rollout, the same way Taj/Omar were C7's best. Sold
the bike at $85 (= Raj's ceiling, well above the $65 floor — $20 captured
on the sell). Bought the toolkit at $42 (= his ceiling). The toolkit deal
is the one Pareto-positive buy of the entire phase: Buck's floor was $30,
so even at Omar's ceiling there was $12 of surplus on the seller side
that Omar voluntarily left. The printer want did not close. Omar's
$28 extraction is the highest of any focal in C8 and roughly matches
C7 Omar's $21 — slightly higher, in fact, because the sell-side surplus
is bigger.

### Taj (set_05) — reward 0.531, normalized closure dropped to 0.667

Taj sold the watch at $28 (= Jade's ceiling), bought boots at $45
(= his ceiling), and missed the blender buy. Same band-edge shape as
everyone else. The notable C8 fact for Taj: normalized closure is 0.667
rather than 1.00 — meaning at least one reachable deal was missed, not
just graph-blocked. In C7 Taj was the top scorer with Pareto 1.00. In C8
Taj is mid-pack with Pareto 0.00. The same persona's two best closes
turned into two band-edge closes, and the third opportunity slipped.

---

## Notable transcript moments

**Marcus, on the skateboard buy (turn 31):**

> "Hey Diego! Awesome board. My absolute maximum budget is $50. Let me
> know if you can do $50 and we can close the deal right now."

Flash is explicit about paying its ceiling. C7 hid this behavior behind
the closure metric; C8 narrates it out loud.

**Kai, between turns 53 and 67 (excerpt of 13 consecutive `pass` events):**

> "Still waiting on Zoe's reply on the dog-sitting offer (off_051) for
> $30…"

> "Continuing to hold. Looking forward to your response on my dog-sitting
> offer, Zoe (off_051)…"

> "Still standard wait turn. Waiting for Zoe's decision on the $30 weekend
> dog-sitting offer (off_051)…"

15 turns of "still waiting" before the accept. This is the most striking
behavioral artifact of Flash in Phase 1 — when an offer is on the table,
it parks itself and re-narrates the wait every other turn rather than
working on the other open wants (keyboard sale, speaker buy).

---

## What stayed constant / what changed vs C7

**Stayed constant:**
- Band-edge buying habit (4 of 5 buys at exact ceiling).
- Privacy holds at 1.00 across all three private personas.
- Deadlock handling holds at 1.00 across all five rollouts.
- Omar is the top scorer; the "good Flash / good Gemini" persona has the
  same shape (sell above floor, one Pareto-positive buy).
- Self-perception is generally close to observer rating (mean Δ = 0.8,
  vs C7's 1.0).

**Changed:**
- Closure rate dropped from 0.73 to 0.60.
- Pareto efficiency dropped from 0.40 to 0.13 — three personas at 0.00.
- Normalized closure dropped from 1.00 to 0.93 (Taj missed a reachable
  deal).
- Mean reward dropped from 0.587 to 0.548 (~7% relative).
- Kai's self-deception gap shrank from Δ = 3 to Δ = 1 — the volatile
  self-rating C7 surfaced does not reappear in C8.
- Spend dropped from $11.65 to $7.70 (Flash is cheaper, as expected).
- Idle/`pass` events make up a much larger fraction of focal turns,
  visible most clearly in Kai (13 consecutive passes around the
  dog-sitting wait).

---

## Methodology caveats

- **Tier confound (Flash vs Pro).** Gemini 3.5 Pro is not yet available
  on OpenRouter at the time of this run. C8 uses Gemini 3.5 Flash. Every
  C7→C8 comparison therefore conflates a generation step (3.1→3.5) with a
  tier step (Pro→Flash). The paper text MUST flag this confound wherever
  Pareto, closure, or reward gaps are interpreted. Any "newer Gemini is
  worse" claim is really "newer Gemini at a lower tier is worse."
- **n=1 per persona.** Five rollouts, no replication. Findings like
  "Taj's Pareto dropped from 1.00 to 0.00" are based on one session each.
- **100-event cap hit in 3 of 5 rollouts** (Kai, Marcus, Taj). Most
  activity is opponent-vs-opponent (GPT-5.5 traders). Focal action
  sequences are short, with idle passes inflating the focal event count.
- **GPT-5.5 opponent field** is the same as C7 — homogeneous, single
  non-Anthropic / non-Google vendor. Model-family interaction effects
  between Flash and GPT-5.5 cannot be separated from intrinsic Flash
  behavior.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files
(`channel.jsonl`, `deals.json`, `judge_ratings.json`, `personas.json`,
`rollout.json`, `rubric_scores.json`, `summary.json`). Phase-level files
sit alongside this INSIGHTS document.

---

*C8 P1 establishes the Gemini-3.5-Flash baseline. Same band-edge buying
habit as C7, weaker closure (0.60), much weaker Pareto (0.13), tighter
reward range, perfect privacy, perfect deadlock-handling, and a new
behavior — long idle waits where Flash narrates the wait rather than
working other open wants. Read alongside C7 P1 for the generation-vs-tier
delta, and remember the tier confound when interpreting any gap.*
