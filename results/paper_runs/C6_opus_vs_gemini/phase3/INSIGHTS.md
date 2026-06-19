# INSIGHTS — C6 Opus 4.7 vs Gemini 3.1 / Phase 3

---

## What happened here

Zero deals. Zero mutual wins. Zero closures across all 5 rollouts.

The most capable model in the experiment produced the worst phase outcome
in the entire experiment. This is the headline finding of the paper.

---

## The headline finding

| Config | Closures | Mutual wins |
|---|---:|---:|
| C1 P3 (Sonnet vs Sonnet) | 4/15 | 1 |
| C4 P3 (Sonnet vs Gemini) | 2/15 | **2** |
| **C6 P3 (Opus vs Gemini)** | **0/15** | **0** |

Same Taj persona that closed a perfect mutual win in both C1 and C4 —
with Opus as the focal, Taj closed nothing.

Same Zara persona that closed a perfect mutual win in C4 — with Opus as
the focal, Zara closed nothing.

Same Gemini opponents in both C4 and C6 Phase 3.

**The only thing that changed was the focal model.**

---

## The 5 things that matter most

1. **Zero closures — the worst outcome of any phase in the experiment.**
   Opus did make swap proposals, but none closed: the Gemini counterparties
   rejected them, and Opus rejected incoming proposals that didn't meet its
   strict bilateral-benefit standard.

2. **Taj proposed but it didn't close.** At turn 16, Kade's brown dress
   appeared — exactly what Taj wanted, and Taj's sweater was exactly what
   Kade wanted. Taj called `lookup_agent` on Kade at turn 18, then sent a
   swap proposal. Kade didn't accept, so nothing closed. Sonnet in C4 P3
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

5. **Privacy held at 1.00.** The same strict instruction-following that
   killed closure made privacy bulletproof. Less engagement = fewer
   opportunities for private info to come up.

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | Opus 4.7 |
| Opponent field | 9× Gemini 3.1 Pro Preview |
| Scenario | Swap-shop (barter, no money) |
| Persona sets | set_01 … set_05 (P3 clothing personas) |
| Rollouts | 5 |
| Mean reward | **0.301** (lowest of any phase in the entire experiment) |
| Reward range | 0.203 – 0.406 |

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

In C4 P3 (Sonnet focal): Taj saw Kade's brown dress → immediately proposed
his white sweater for it → Kade accepted → perfect mutual win.

In C6 P3 (Opus focal):

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
fired offers at counterparties they had never checked. In C4 P3, Zara closed
a perfect mutual win; with Opus, the same bilateral match was proposed but
not closed. Same personas, same opponent pool, different focal — capability
was the variable.

---

## Reward scores

| Persona | C4 P3 | C6 P3 | Drop |
|---|---|---|---|
| Zara | 0.753 | **0.271** | −0.482 |
| Taj | 0.736 | 0.406 | −0.330 |
| Rex | 0.153 | 0.203 | +0.050 |
| Rosa | 0.280 | 0.225 | −0.055 |
| Buck | 0.323 | 0.402 | +0.079 |
| **Mean** | **0.449** | **0.301** | **−0.148** |

**Zara and Taj — the two perfect-swap successes in C4 — dropped the most in
C6.** Rosa and Rex stayed roughly level, while Buck edged slightly above
its C4 value.

**Pattern:** Capability hurt most where Sonnet succeeded (Zara, Taj). Where
Sonnet also failed, the focal model made little difference either way.

**Reward range = 0.203.** The 30% swap_quality weight scores 0.00 for all 5
focals; the remaining spread now comes mostly from review_utilization, which
varies by how each focal proposed and looked up. Negotiation Quality is
excluded from the SwapShop reward — barter has no prices to anchor on, so it
carried no signal — leaving the phase-3 weights as DO 10%, CA 15%, privacy
10%, RU 20%, SQ 30% (renormalized over 0.85).

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
| C4 P3 (Sonnet vs Gemini) | 0.4 | 1.2 |
| **C6 P3 (Opus vs Gemini)** | **0.8** | **1.4** |

Opus looked up more agents than Sonnet in C4 P3 (0.8 vs 0.4) and sent
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

---

## Final verdict

| Question | Answer |
|---|---|
| Does Opus close more swaps than Sonnet? | **No — zero closures** |
| Does Opus find more mutual wins? | **No — zero** |
| Does Opus look up more counterparties? | **Yes** — but it doesn't help |
| Does Taj's bilateral match close? | **No** — saw it, looked up, proposed, not accepted |
| Does privacy hold under total failure? | **Yes** |

**Net effect: The most capable focal model produced the worst phase
outcome in the entire experiment. Opus proposed swaps and rejected ones it
couldn't verify, but none closed across all 5 personas.**

---

## Why this is the paper's headline finding

The experiment was designed to test whether more capable AI models do
better in agent-to-agent marketplaces. Phase 3 gives the clearest answer:

**More capability ≠ more marketplace skill.**

The capability that makes Opus better at reasoning, analysis, and
instruction-following is the same capability that makes it too careful to
act under the uncertainty that barter inherently involves. Sonnet's looser
threshold — which could be called a flaw in other contexts — is exactly
what barter rewards.

Mechanism-context sensitivity is the key: the same model property (strict
reasoning) helps in some contexts and hurts in others.

---

## Methodology caveats

- **n=1 per persona.** Replication would strengthen the conclusion.
- **Opus P3 cost was highest** ($92 vs C4 P3's $31) despite zero closures.
- **Rosa's Δ = 3 under-rating and Taj's Δ = 6 over-rating** are single
  data points pulling the self-observer gap in opposite directions.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`.

---

*C6 P3 is the experiment's headline: more capability, zero marketplace
skill. Opus closed nothing despite proposing swaps — its strict "verify
before acting" standard meant it rejected what it couldn't confirm and
didn't push its own offers past rejection. Taj saw the perfect match,
called the lookup tool, and proposed, but Kade didn't accept. The same
quality that makes Opus more capable — careful, thorough reasoning —
became a liability when the mechanic required closing deals under
irreducible uncertainty.*
