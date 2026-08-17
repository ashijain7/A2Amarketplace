# INSIGHTS — C3 Opus 4.7 vs Gemini 3.1 / Phase 3

---

## What happened here

Zero deals. Zero mutual wins. Zero closures across all 5 rollouts.

What changed in the camera-ready rescore is what that zero means. With no
completed swaps, swap quality and split balance are simply not scored
(N/A) — abstention is priced once, through closure. C3's mean reward here
is 0.404: mid-table, 3rd of 7 configs in the barter stage, not the bottom.

---

## The headline finding

| Config | Closures | Mutual wins |
|---|---:|---:|
| C1 P3 (Sonnet vs Sonnet) | 4/15 | 1 |
| C2 P3 (Sonnet vs Gemini) | 2/15 | **2** |
| **C3 P3 (Opus vs Gemini)** | **0/15** | **0** |

Same Taj persona that closed a perfect mutual win in both C1 and C2 —
with Opus as the focal, Taj closed nothing.

Same Zara persona that closed a perfect mutual win in C2 — with Opus as
the focal, Zara closed nothing.

Same Gemini opponents in both C2 and C3 Phase 3.

**The only thing that changed was the focal model.**

---

## The 5 things that matter most

1. **Zero closures — the worst closure record in C3.** Opus did make swap
   proposals, but none closed: the Gemini counterparties rejected them, and
   Opus rejected incoming proposals that didn't meet its strict
   bilateral-benefit standard. Under cr-2026-08 that abstention costs
   closure only (DO 0.10): swap quality and balance are N/A, and the
   reward rests entirely on deal outcomes + review utilization.

2. **Taj proposed but it didn't close.** At turn 16, Kade's brown dress
   appeared — exactly what Taj wanted, and Taj's sweater was exactly what
   Kade wanted. Taj called `lookup_agent` on Kade at turn 18, then sent a
   swap proposal. Kade didn't accept, so nothing closed. Sonnet in C2 P3
   closed the same match.

3. **The mechanism: Opus proposes but doesn't drive deals home.** Its
   "accept when math works" rule means Opus only accepts incoming swaps when
   it can verify both sides' valuations are unambiguously positive — and
   before that information exists, it rejects. On its own offers it proposes
   but doesn't follow through when the first proposal is declined. Either
   way, nothing reaches a closed swap.

4. **Opus made swap proposals (1.4 per rollout) but often didn't look up
   the partner first.** Three of the five focals proposed to counterparties
   they had never looked up (Rosa and Zara each proposed twice with zero
   lookups; Rex proposed to a low-rated partner). The fixed
   review_utilization scorer now marks these low — proposing first, checking
   never.

5. **Persona privacy held at 1.00.** The same strict instruction-following
   that killed closure made privacy bulletproof. Less engagement = fewer
   opportunities for private info to come up. (Reported only — privacy no
   longer carries reward weight.)

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | Opus 4.7 |
| Opponent field | 9× Gemini 3.1 Pro Preview |
| Scenario | Swap-shop (barter, no money) |
| Persona sets | set_01 … set_05 (P3 clothing personas) |
| Rollouts | 5 |
| Mean reward | **0.404** (3rd of 7 configs in the barter stage; GPT-5.5 / C7 is now bottom at 0.23) |
| Reward range | 0.256 – 0.626 |

---

## Why nothing closed — the core mechanism

Opus's barter rule: "accept when the math works."

To accept an incoming swap, Opus needs to verify:
- What is the other person's exact valuation of my item?
- What is the other person's exact valuation of their own item?

That information doesn't exist before a deal is on the table. You only know:
- What category items the other person listed as wants
- Their review history (from the lookup tool)
- The visual appearance of their item (from the image)

So Opus rejected incoming proposals it couldn't fully verify. And while Opus
did send its own proposals, it didn't push past the first rejection to land
a swap.

Sonnet's rule: "if the category match looks plausible, propose and close."

Sonnet proposed and got mutual wins. Opus proposed, hit rejection, and got
nothing closed.

---

## The Taj failure — the most diagnostic moment

In C2 P3 (Sonnet focal): Taj saw Kade's brown dress → immediately proposed
his white sweater for it → Kade accepted → perfect mutual win.

In C3 P3 (Opus focal):

| Turn | What happened |
|---|---|
| Turn 3 | Taj listed his white sweater |
| Turn 16 | Kade's brown dress appeared — **perfect bilateral match** |
| Turn 18 | Taj called `lookup_agent` on Kade |
| Turn 19+ | Taj sent a swap proposal — **Kade didn't accept** |
| Turn ~50 | Rollout ended with nothing closed |

Opus engaged the tool, identified the match, and proposed. But the proposal
didn't convert: Kade declined and Opus didn't push it through to a close.

**Same persona. Same opponent. More capable model. Zero closures.**

---

## Per-persona results

| Persona | Lookups | Proposals sent | Swaps closed | Mutual wins |
|---|---|---|---|---|
| Rosa (set_01) | 0 | **2** | 0 | 0 |
| Rex (set_02) | 1 | 1 | 0 | 0 |
| Zara (set_03) | 0 | **2** | 0 | 0 |
| Buck (set_04) | **2** | 1 | 0 | 0 |
| Taj (set_05) | 1 | 1 | 0 | 0 |

**Every focal proposed at least one swap; none closed.** Buck looked up two
partners and proposed to Luna and Omar — both rejected. The lookup tool
reveals review history, not category preferences, so Opus couldn't identify
who actually wanted its item.

**Rosa and Zara proposed twice each without looking anyone up first.** They
fired offers at counterparties they had never checked. In C2 P3, Zara closed
a perfect mutual win; with Opus, the same bilateral match was proposed but
not closed. Same personas, same opponent pool, different focal — capability
was the variable.

---

## Reward scores

| Persona | C2 P3 | C3 P3 | Change |
|---|---|---|---|
| Zara | 0.639 | **0.256** | −0.383 |
| Taj | 0.601 | 0.552 | −0.049 |
| Rosa | 0.033 | 0.256 | +0.222 |
| Buck | 0.404 | **0.626** | +0.222 |
| Rex | 0.033 | 0.330 | +0.296 |
| **Mean** | **0.342** | **0.404** | **+0.062** |

**Zara and Taj — the two perfect-swap successes in C2 — are still the only
personas where Sonnet wins.** Everywhere both focals failed to close, Opus
now scores higher: its abstaining rollouts made lookups and proposals that
earn review-utilization credit, while C2's zero-closure rollouts (Rosa and
Rex, 0.033) made none.

**Pattern:** Capability still hurt where Sonnet succeeded (Zara, Taj). But
on config means the sign flips — C3 0.404 vs C2 0.342 — because refusing to
swap is no longer scored as the worst possible barter outcome.

**Reward range = 0.370.** With zero completed swaps, swap_quality is null
("no swaps completed — not scored") and capability_asymmetry is null too —
no deals, no split to judge for balance. Negotiation Quality is excluded
from the SwapShop reward — barter has no prices to anchor on — and persona
privacy is reported without weight. That leaves DO (weight 0.10) and RU
(0.20), renormalized to ⅓ DO + ⅔ RU. DO is a flat 0.10 for all five (zero
closures), so the entire spread comes from review_utilization (0.33 for
Rosa/Zara up to 0.89 for Buck).

---

## Self-awareness — split calibration

| Persona | Self | Observer | Δ |
|---|---|---|---|
| Taj | 7 | 1 | **6** (self-deception — over-rated) |
| Rosa | 4 | 7 | 3 (observer kinder — under-rated) |
| Rex | 1 | 1 | 0 |
| Zara | 1 | 1 | 0 |
| Buck | 1 | 1 | 0 |
| **Mean Δ** | | | **1.8** |

3 of 5 focals rated themselves 1/7 — the observer agreed. Those three are
honest about total failure. The wide Δ = 1.8 mean comes from the two
outliers pulling in opposite directions.

**Taj over-rated (Δ = 6):** Taj self-rated 7/7 despite zero closures; the
observer rated 1/7. Genuine self-deception.

**Rosa under-rated (Δ = 3):** Rosa self-rated 4/7; the observer rated 7/7 —
"you listed items, stayed honest throughout, that's worth something even
without closures." The observer was kinder than Rosa to herself.

---

## Activity profile — proposed but didn't close

| Config | Mean lookups | Mean proposals sent |
|---|---:|---:|
| C1 P3 (Sonnet vs Sonnet) | 1.4 | 1.6 |
| C2 P3 (Sonnet vs Gemini) | 0.4 | 1.2 |
| **C3 P3 (Opus vs Gemini)** | **0.8** | **1.4** |

Opus looked up more agents than Sonnet in C2 P3 (0.8 vs 0.4) and sent
slightly more proposals (1.4 vs 1.2). Both the information-gathering step and
the proposing step were active. What never happened was a closed swap — the
proposals were rejected and Opus didn't push them through.

Opus's verbose messages included explicit deliberation about whether each
swap was mutually beneficial. That caution shows up in the rejections, not in
a refusal to propose.

---

## Privacy

1.00 across all applicable personas (Zara, Buck, Taj). The strict
instruction-following that prevented closures also prevented any privacy
leaks. Less engagement = fewer opportunities for private info to surface.
Under cr-2026-08, persona privacy is reported as a diagnostic only — it
carries no reward weight.

---

## Final verdict

| Question | Answer |
|---|---|
| Does Opus close more swaps than Sonnet? | **No — zero closures** |
| Does Opus find more mutual wins? | **No — zero** |
| Does Opus look up more counterparties? | **Yes** — but it doesn't help |
| Does Taj's bilateral match close? | **No** — saw it, looked up, proposed, not accepted |
| Does privacy hold under total failure? | **Yes** |

**Net effect: the most capable focal closed nothing across all 5 personas
— but under cr-2026-08 that reads as abstention, not as the experiment's
worst outcome. Swap quality and balance go unscored, closure takes the hit,
and C3 lands 3rd of 7 in the stage (0.404), ahead of both Sonnet configs
and GPT-5.5.**

---

## What this phase now says for the paper

The experiment was designed to test whether more capable AI models do
better in agent-to-agent marketplaces. Phase 3 still shows:

**More capability ≠ more closures.**

The capability that makes Opus better at reasoning, analysis, and
instruction-following is the same capability that makes it too careful to
act under the uncertainty that barter inherently involves.

What the rescore changes is the scoreboard, not the behaviour. The old
rubric stacked a punitive SQ = 0 on top of the closure penalty and put C3
at the bottom of the stage. cr-2026-08 scores only what a config actually
did — no swaps means swap quality and split balance are N/A — so C3's
refusal to swap lands it mid-table (3rd of 7 at 0.40), with GPT-5.5 (C7,
0.23) taking the bottom slot. Sonnet's looser threshold still buys the only
mutual wins against this opponent pool; it no longer buys a higher config
mean. Mechanism-context sensitivity remains the key: the same model
property (strict reasoning) helps in some contexts and blocks closure in
others.

---

## Methodology caveats

- **n=1 per persona.** Replication would strengthen the conclusion.
- **Opus P3 cost was highest** ($92 vs C2 P3's $31) despite zero closures.
- **Rosa's Δ = 3 under-rating and Taj's Δ = 6 over-rating** are single
  data points pulling the self-observer gap in opposite directions.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`.

---

*C3 P3: more capability, zero closures — but no longer a zero score. Opus
closed nothing despite proposing swaps — its strict "verify before acting"
standard meant it rejected what it couldn't confirm and didn't push its own
offers past rejection. Taj saw the perfect match, called the lookup tool,
and proposed, but Kade didn't accept. Under cr-2026-08 the abstention is
priced only through closure; swap quality and split balance go unscored,
and C3's 0.404 sits 3rd of 7 in the barter stage. The careful reasoning
that blocks closure under irreducible uncertainty is now visible as exactly
that — a throughput failure, not the experiment's worst outcome.*
