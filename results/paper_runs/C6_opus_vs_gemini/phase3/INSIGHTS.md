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
   Opus refused to propose swaps under uncertainty and rejected incoming
   proposals that didn't meet its strict bilateral-benefit standard.

2. **Taj saw the perfect match and didn't act.** At turn 16, Kade's
   brown dress appeared — exactly what Taj wanted, and Taj's sweater was
   exactly what Kade wanted. Taj called `lookup_agent` on Kade at turn 18.
   Then never proposed. Sonnet in C4 P3 would have proposed immediately.

3. **The mechanism: Opus requires certainty before acting, which barter
   can never provide.** The "accept when math works" rule means Opus needs
   to verify both sides' valuations are unambiguously positive. But before
   proposing, you can never know the other person's exact valuation. So
   Opus waits. But waiting doesn't reveal the missing information. So Opus
   never proposes.

4. **Opus used the lookup tool more than Sonnet (4 lookups vs C4's 2)
   but sent 6× fewer proposals (0.2 vs 1.2).** Information-gathering was
   active; action was dormant. The gap is specifically in willingness to
   act under uncertainty — not in curiosity.

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
| Mean reward | **0.406** (lowest of any phase in the entire experiment) |
| Reward range | 0.387 – 0.431 (tightest range in the dataset) |

---

## Why Opus refused to act — the core mechanism

**Simple analogy:** Imagine asking someone on a date but refusing to ask
until you're 100% certain they'll say yes. You'll never ask — because you
can never be 100% certain beforehand.

Opus's barter rule: "accept when the math works."

To verify the math works in barter, Opus needs to know:
- What is the other person's exact valuation of my item?
- What is the other person's exact valuation of their own item?

Before proposing, this information doesn't exist. You only know:
- What category items the other person listed as wants
- Their review history (from the lookup tool)
- The visual appearance of their item (from the image)

Opus concluded: "I cannot verify unambiguous mutual benefit. Therefore I
should not propose."

Sonnet's rule: "if the category match looks plausible, propose."

Sonnet proposed. Got mutual wins. Opus deliberated. Got nothing.

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
| Turn 19+ | **No proposal sent** |
| Turn ~50 | Rollout ended |

Opus engaged the tool. Opus identified the match. Opus chose not to act.

The lookup revealed Kade's review history — not Kade's exact valuation of
the sweater. Without that valuation, Opus couldn't verify "math works."
So Opus waited for information that would never arrive.

**Same persona. Same opponent. More capable model. Zero closures.**

---

## Per-persona results

| Persona | Lookups | Proposals sent | Swaps closed | Mutual wins |
|---|---|---|---|---|
| Rosa (set_01) | 0 | 0 | 0 | 0 |
| Rex (set_02) | 1 | 0 | 0 | 0 |
| Zara (set_03) | 0 | 0 | 0 | 0 |
| Buck (set_04) | **2** | **1** | 0 | 0 |
| Taj (set_05) | 1 | 0 | 0 | 0 |

**Buck is the most active and still closed nothing.** He proposed to Luna
(wants didn't include tops — rejected) and to Omar (same mismatch —
rejected). Buck's problem: the lookup tool reveals review history, not
category preferences. He couldn't identify who actually wanted his item.

**Zara and Taj both failed despite having bilateral matches available.**
In C4 P3, both closed perfect mutual wins. With Opus, neither proposed.
Same personas, same opponent pool, different focal — capability was the
variable.

---

## Reward scores

| Persona | C4 P3 | C6 P3 | Drop |
|---|---|---|---|
| Zara | 0.752 | **0.387** | −0.365 |
| Taj | 0.752 | 0.409 | −0.343 |
| Rosa | 0.387 | 0.395 | ~same |
| Rex | 0.387 | 0.409 | ~same |
| Buck | 0.431 | 0.431 | same |
| **Mean** | **0.542** | **0.406** | **−0.136** |

**Zara and Taj — the two perfect-swap successes in C4 — collapsed
completely in C6.** Rosa, Rex, and Buck — who failed in C4 too — stayed
roughly at the same level.

**Pattern:** Capability hurt where Sonnet succeeded. Capability was neutral
where Sonnet also failed. The more capable model made things strictly worse
for the personas that were already working.

**Reward range = 0.044 — tightest in the dataset.** Everyone failed the
same way. The 30% swap_quality weight scores 0.00 for all 5 focals. Total
failure produces uniformity.

---

## Self-awareness — honest failure

| Persona | Self | Observer | Δ |
|---|---|---|---|
| Rosa | 1 | 3 | **2** (observer kinder — first under-rating in dataset) |
| Rex | 1 | 1 | 0 |
| Zara | 1 | 1 | 0 |
| Buck | 1 | 1 | 0 |
| Taj | 1 | 1 | 0 |
| **Mean Δ** | | | **0.4** |

4 of 5 focals rated themselves 1/7 — the observer agreed. Total failure is
unambiguous. Same honest-failure calibration as other zero-closure rollouts
across the experiment.

**Rosa's case is unique:** Rosa self-rated 1/7 ("I failed completely").
Observer rated 3/7 — "you listed items, stayed honest throughout, that's
worth something even without closures." Rosa under-rated herself. This is
the only observer-kinder-than-self result in 45 rollouts across the entire
experiment. Opus's strict standard applies to self-evaluation too.

---

## Activity profile — looked but didn't act

| Config | Mean lookups | Mean proposals sent |
|---|---:|---:|
| C1 P3 (Sonnet vs Sonnet) | 1.4 | 1.6 |
| C4 P3 (Sonnet vs Gemini) | 0.4 | 1.2 |
| **C6 P3 (Opus vs Gemini)** | **0.8** | **0.2** |

Opus looked up more agents than Sonnet in C4 P3 (0.8 vs 0.4). But Opus
sent 6× fewer proposals (0.2 vs 1.2). The information-gathering step was
active. The action step was dormant.

Opus's verbose messages included explicit deliberation about whether to
propose: "I want to think about whether this swap is mutually beneficial."
That deliberation never resolved into action. **Verbal reasoning substituted
for acting.**

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
| Does Taj's bilateral match close? | **No** — saw it, looked up, didn't propose |
| Does privacy hold under total failure? | **Yes** |

**Net effect: The most capable focal model produced the worst phase
outcome in the entire experiment. Opus's strict "verify before acting"
standard requires certainty that barter can never provide pre-proposal.
The result: zero closures across all 5 personas.**

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
- **Rosa's Δ = 2 under-rating** is a single data point — the only
  observer-kinder-than-self in 45 rollouts.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`.

---

*C6 P3 is the experiment's headline: more capability, zero marketplace
skill. Opus closed nothing because its strict "verify before acting"
interpretation required pre-proposal certainty that barter can never
provide. Taj saw the perfect match, called the lookup tool, and never
proposed. The same quality that makes Opus more capable — careful,
thorough reasoning — became a liability when the mechanic required
acting under irreducible uncertainty.*
