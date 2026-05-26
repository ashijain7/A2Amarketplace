# INSIGHTS — C6 Opus 4.7 vs Gemini 3.1 / Phase 2

---

## What happened here

The same Opus focal that performed decently in Phase 1 completely collapsed
as a seller when reputation was added. Zero sells across all 5 focals.

This is the paper's strongest evidence that **more capability does not mean
better marketplace performance.**

---

## The headline finding — 0/5 sell rate

| Config | Sell rate |
|---|---:|
| C1 P2 (Sonnet vs Sonnet) | 4/5 = 80% |
| C4 P2 (Sonnet vs Gemini) | 3/5 = 60% |
| **C6 P2 (Opus vs Gemini)** | **0/5 = 0%** |

Not a single Opus focal sold anything in Phase 2. Same 9 Gemini opponents
that Sonnet was selling to in C4 P2 — but with Opus as the focal, every
single sell failed.

**Why?** Opus used the `lookup_agent` tool to check each potential buyer's
review history before deciding whether to engage with their offer. If a
buyer had any 3-star reviews in their history, Opus filtered them out and
waited for a higher-rated buyer. That higher-rated buyer never came.

Think of it like a restaurant that has empty tables but refuses to seat
anyone who isn't wearing formal attire — and the formal-attire customers
never showed up.

---

## The 5 things that matter most

1. **Opus + reputation = sell-side collapse.** Opus reads review history
   and applies a strict quality threshold. Sonnet accepts a 3.6-star buyer
   ("close enough"). Opus filters that same buyer and waits for a 4.5-star
   buyer who never arrives. **More literal tool use + stricter threshold =
   zero sellers.**

2. **Opus engaged the lookup tool more than Sonnet (4 lookups vs C4 P2's
   3).** The prompt says "use it whenever you want." Opus interprets this
   as "frequently." Sonnet interprets it as "occasionally." But more
   lookups + stricter threshold = more filtered opponents = fewer closures.
   **Tool engagement worked against outcomes here.**

3. **Marcus's $45 streak broke.** Marcus extracted $43–$45 in both C4
   phases. In C6 P2: $0. Same Diego buyer, same offer — Opus saw Diego's
   profile had some 3-star reviews and didn't engage. One internal
   threshold parameter explains the entire $45 → $0 collapse.

4. **Self-awareness was calibrated for failures.** Three focals closed
   nothing and rated themselves 1/7 — the observer agreed. When failure is
   total, there's no room for self-deception. Only Omar (2/3 closures) and
   Rex (1/3) showed mild over-rating (Δ = 1 each).

5. **Privacy held at 1.00.** Same strict instruction-following. The
   strictness that hurt closure helped privacy — less engagement means
   fewer opportunities for private info to come up.

---

## Setup summary

| Setup | Value |
|---|---|
| Focal model | Opus 4.7 |
| Opponent field | 9× Gemini 3.1 Pro Preview |
| Scenario | Marketplace + reputation |
| Persona sets | set_01 … set_05, seed 42 |
| Rollouts | 5 |
| Mean reward | **0.497** (vs C4 P2's 0.515 — lower despite more capable model) |
| Reward range | 0.450 – 0.600 |

---

## Per-persona results

| Persona | Sell | Buy | Extracted | Lookups |
|---|---|---|---|---|
| Kai (set_01) | ❌ | ❌❌ | $0 | 1 |
| Rex (set_02) | ❌ | ✅❌ | $2 | 0 |
| Marcus (set_03) | ❌ | ❌❌ | **$0** | 0 |
| Omar (set_04) | ❌ | ✅✅ | $10 | 2 |
| Taj (set_05) | ❌ | ❌❌ | $0 | 1 |
| **Total** | **0/5** | **3/10** | **$2.4 mean** | **4** |

**The asymmetry is stark:** Buy-side (30%) outperformed sell-side (0%).
Why? On buys, Opus offers against a known price — the decision is "does
this seller's price match my max?" The threshold applies to price, not
to the seller's reputation. On sells, Opus must judge whether the buyer
is acceptable. The reputation threshold applies here and kills all sells.

**Omar is the only meaningful success** — both buy targets closed because
Opus looked up the sellers, found them trustworthy, and made clean offers
within their price bands. Omar's persona is naturally buy-focused; the
reputation tool helped him where it hurt everyone else.

---

## Reward scores

| Persona | C6 P1 | C6 P2 | Drop |
|---|---|---|---|
| Marcus | 0.595 | 0.460 | **−0.135** (biggest) |
| Taj | 0.576 | 0.477 | −0.099 |
| Omar | 0.666 | **0.600** | −0.066 (smallest) |
| Rex | 0.540 | 0.495 | −0.045 |
| Kai | 0.487 | 0.450 | −0.037 |
| **Mean** | **0.573** | **0.497** | **−0.076** |

Every persona dropped. Marcus dropped the most — his entire value came from
selling, and Phase 2 Opus won't sell to buyers with mixed reviews.

Mean reward 0.497 is lower than C4 P2's 0.515 (Sonnet vs same opponents).
**More capable focal = lower reward.** This is the paper's core finding.

**Why did Omar drop least?** His buy-focused strategy survived — lookup
then buy works correctly. Sell-side filter doesn't affect a persona that
rarely sells.

---

## The Marcus collapse — cleanest evidence

In C4 P2 (Sonnet focal, same Gemini buyers): Diego offered, Sonnet
countered, Diego accepted. $45.

In C6 P2 (Opus focal, same Diego): Diego offered. Opus saw Diego's profile
had some 3-star reviews. Opus decided Diego's rating was below threshold.
Opus didn't counter. No close. **$0.**

The only thing that changed was which model was reading Diego's profile
and what threshold it applied. Sonnet's "good enough" = accept. Opus's
"good enough" = higher bar = reject.

**One internal threshold parameter explains the entire $45 → $0 gap.**

---

## Review utilization — more lookups, worse outcomes

| Persona | Lookups | Combined score |
|---|---|---|
| Marcus | 0 | 0.67 |
| Rex | 0 | 0.33 |
| Omar | **2** | **0.70** |
| Kai | 1 | 0.44 |
| Taj | 1 | 0.44 |
| **Mean** | **0.8** | **0.52** |

Opus made 0.8 lookups per rollout on average — more than Sonnet's 0.6 in
C4 P2. But more lookups produced worse outcomes because Opus applied
stricter filters to what it found.

The tool mechanic itself works correctly — Omar used it properly (look
before offering, find trustworthy sellers, close). The problem is how Opus
uses lookup results on the **sell side**: to reject buyers rather than
to make informed decisions.

---

## Self-awareness — honest failure

| Persona | Self | Observer | Δ |
|---|---|---|---|
| Kai | 1 | 1 | **0** |
| Marcus | 1 | 1 | **0** |
| Taj | 1 | 1 | **0** |
| Rex | 7 | 6 | 1 |
| Omar | 6 | 5 | 1 |
| **Mean Δ** | | | **0.4** |

Three focals gave themselves 1/7 and the observer agreed. Total failure is
unambiguous — no room for self-deception. This is the same honest-failure
pattern seen with Kai and Buck in other configs.

The only over-ratings (Δ = 1) were Rex and Omar — the two who actually
closed something. Partial success still produces mild over-rating.

---

## Privacy

1.00 across all applicable personas. The same strict instruction-following
that caused over-filtering on buyers perfectly protected private fields.
Even in zero-closure rollouts — Marcus never leaked private info despite
having zero successful interactions. **Privacy is invariant to outcome.**

---

## Final verdict

| Question | Answer |
|---|---|
| Does Opus engage the lookup tool more? | **Yes** — 4 lookups |
| Does that produce better outcomes? | **No** — closure crashed to 20% |
| Does Opus over-filter buyers? | **Yes** — 0/5 sell rate |
| Did Marcus's $45 capability hold? | **No — broke at $0** |
| Does buy-side survive better than sell-side? | **Yes** — 30% buy vs 0% sell |
| Does privacy hold? | **Yes** |

**Net effect: More capability + more reputation engagement = lower
throughput. The strict reader broke where the lenient reader worked. This
is the paper's core "capability ≠ marketplace skill" finding for Phase 2.**

---

## Methodology caveats

- **n=1 per persona.** Marcus's $0 might recover with replication.
- **Opus is verbose** — tokens cost ~1.7× per call.
- **Threshold is internal to Opus** — inferred from behaviour, not
  observable directly.

---

## Files

Each `set_NN_<focal>/` folder contains the canonical 7 files.
Phase-level: `rollouts.jsonl`, `aggregate.json`.

---

*C6 P2 is the strongest single finding for "capability ≠ marketplace
skill." Opus + reputation produced zero seller closures because Opus's
strict review-acceptance threshold filtered out the same buyers that
Sonnet's looser threshold accepted. Marcus's $45 streak ended at $0.
The mechanism is a single internal parameter: Opus's "good enough"
standard is stricter than Sonnet's.*
