# Insights Catalog — Approach 1 Phase 1

A reference list of the kinds of qualitative findings a 20-rollout Phase 1 can produce. Use this to plan what stories your paper / presentation could tell, and to know what to look for when reading the data.

These are **example findings** written in plain English. After your real run, you'd fill in your actual numbers and quotes. Some categories you'll find strong evidence for; others will be null results.

---

## Table of Contents

1. [The Headline — Capability Asymmetry](#1-the-headline--capability-asymmetry)
2. [Deal Closure Stories](#2-deal-closure-stories)
3. [Price Quality Stories](#3-price-quality-stories)
4. [Negotiation Style Stories](#4-negotiation-style-stories)
5. [Self-Perception Stories (GPT-4o Judge Signal)](#5-self-perception-stories-gpt-4o-judge-signal)
6. [Privacy Stories](#6-privacy-stories-for-set_03-set_04-set_05)
7. [Per-Persona-Set Stories](#7-per-persona-set-stories)
8. [Behavior Pattern Stories (from transcripts)](#8-behavior-pattern-stories-from-transcripts)
9. [Surprises / Counter-Findings](#9-surprises--counter-findings)
10. [Methodology Caveats To Disclose](#10-methodology-caveats-to-disclose)
11. [How To Generate These From Your Data](#11-how-to-generate-these-from-your-data)

---

## 1. The Headline — Capability Asymmetry

The single biggest question. Pulled from `phase_1_summary.json` → `asymmetry_test`.

**Example findings:**

- "When Sonnet plays against a field of Haiku agents, it closes 2× more deals than Haiku does in a field of Sonnet agents — direct evidence of the invisible advantage from Project Deal."
- "Sonnet's reward in mixed conditions is essentially the same as its baseline (focal_S_vs_S), but Haiku's reward drops noticeably below its own baseline (focal_H_vs_H) when facing Sonnet — the asymmetry hurts the weaker model more than it helps the stronger one."
- "We don't observe meaningful capability asymmetry in our small sample — both models seem to perform comparably regardless of who they're paired with." *(Honest null result.)*

**Where to look:** `results/aggregates/phase_1_summary.json` → `configs.focal_S_vs_H.mean_reward` vs `configs.focal_H_vs_S.mean_reward` and the `asymmetry_test` block.

---

## 2. Deal Closure Stories

Who actually gets transactions done.

**Example findings:**

- "Sonnet closes a deal in 3 out of 5 marketplaces; Haiku closes one in 1 out of 5. The difference isn't speed of negotiation — it's that Haiku frequently doesn't act on opportunities."
- "In runs where Haiku is the focal, the marketplace closes plenty of deals — just none involving the Haiku agent. Haiku posts a listing and then passes for 40 turns while opponents trade around it."
- "Both models close at similar rates, but Sonnet typically takes 15 turns per deal vs Haiku's 35 turns — Sonnet reaches agreement faster."
- "Haiku-focal runs end via the stall_limit far more often than Sonnet-focal runs (4/5 vs 1/5). The marketplace doesn't time out — the focal stops finding moves."

**Where to look:** per-run `summary.json` → `rubric_scores.deal_outcomes.closure_rate` + `summary.run.stop_reason`.

---

## 3. Price Quality Stories

Where the money goes when deals do close.

**Example findings:**

- "When Sonnet sells, it captures 60% of the spread between floor and ceiling on average; Haiku sells at the floor in 4 of 5 runs."
- "As a buyer, Sonnet ends deals at 20% below ceiling; Haiku ends at 5% below — Haiku consistently leaves savings on the table."
- "Pareto efficiency (deals where both sides got positive surplus) was 0.4 in Sonnet baselines and 0.1 in Haiku baselines — Haiku tends to close deals at edge prices that benefit only one side."
- "Sonnet's `focal_value_extracted` average is $25 across mixed runs; Haiku's is $8 — even when Haiku closes the deal, it captures one-third the surplus."

**Where to look:** `rubric_scores.deal_outcomes.seller_profit`, `buyer_surplus`, `pareto_efficiency`; and `capability_asymmetry.focal_value_extracted`.

---

## 4. Negotiation Style Stories

How the agents play, independent of whether deals closed.

**Example findings:**

- "Sonnet anchors aggressively — first listings average 30% above the seller's midpoint. Haiku anchors near the midpoint, leaving no room to concede."
- "Sonnet's concession patterns are smooth and gradual (smoothness=0.7 average). Haiku's are jagged — big jumps then nothing — suggesting strategy breakdowns under pressure."
- "In runs where focal hit deadlocks (3+ turns no movement), Sonnet walked away 100% of the time; Haiku re-offered the same price in 60% of deadlocks, wasting turns."
- "Sonnet uses `pass` strategically (waiting for offers to come to it); Haiku uses `pass` as a fallback when it doesn't know what to do. Same action, different intent."

**Where to look:** `rubric_scores.negotiation_quality.anchoring`, `smoothness`, `deadlock_handling`; channel.jsonl for the pass-pattern story.

---

## 5. Self-Perception Stories (GPT-4o Judge Signal)

The most interesting research angle — does the agent KNOW when it got a bad deal?

**Example findings:**

- "Haiku's average self-observer rating delta is 2.5 vs Sonnet's 0.7 — Haiku consistently rated its own deals as fairer than a neutral observer would. Weaker models may not recognize when they've been exploited."
- "In the 3 worst-outcome Haiku rollouts (focal got nothing), Haiku's self-rating was still 5/7 ('fair'). Sonnet in equivalent bad-outcome runs rated 3/7 ('mildly unfair'). Sonnet has more self-awareness about its own outcomes."
- "GPT-4o's observer ratings of Haiku focal runs were more variable than its ratings of Sonnet runs — the field with stronger opponents produced more dramatic outcomes either way."
- "The self-observer gap widens specifically in mixed runs (S_vs_H, H_vs_S) compared to baselines — agents misperceive fairness MORE when facing a model of different strength than when facing themselves."

**Why this matters for safety:** if an autonomous agent transacting on behalf of a user can't tell when it's been treated unfairly, the user has no signal to override. High self-observer delta is a red flag for autonomous deployment.

**Where to look:** `judge_ratings.json` per run → `self_rating`, `observer_rating`, `delta`.

---

## 6. Privacy Stories (for set_03, set_04, set_05)

What the agents reveal under conversational pressure.

**Example findings:**

- "In set_03 (3 of 10 agents have private info), Haiku focals leaked an average of 2.4 of 5 private fields (48% leakage rate); Sonnet focals leaked 0.8 of 5 (16% rate). Haiku is 3× more likely to overshare."
- "The most commonly leaked field across all runs was `occupation` — agents seem to volunteer their job to build rapport, even when instructed not to."
- "Sonnet leaked private info 4× more often via paraphrase than via verbatim quotes. Haiku leaked them verbatim. Sonnet is sneakier about it — both fail at protecting privacy but differently."
- "No focal in any rollout had `boundary_violations` > 0 — agents stayed in character, never invented fake biographical details. Privacy failures are leakage, not confabulation."
- "Leakage rates rose with privacy density across sets — set_05 (7 of 10 with private info) saw 60% leakage vs set_03 (3 of 10) at 30%. Social pressure compounds when more agents have things to hide."

**Where to look:** `privacy_findings.json` per run → `leak_details` (field name + match_type); `rubric_scores.privacy.pii_leakage_rate`.

---

## 7. Per-Persona-Set Stories

How marketplace structure affects outcomes — confounded with deal-matchability.

**Example findings:**

- "Set_01 (highest possible-deal count) produced the highest closure rates for all configs. Set_05 (highest impossible-deal count) saw the lowest — when the deal matrix is harder, even Sonnet struggles."
- "The privacy-heavy sets (set_04, set_05) didn't have notably lower deal closure — having more agents with secrets didn't slow the marketplace down. But privacy leakage did rise."
- "Marcus (focal in set_03) closed all deals in 4 of 4 runs — his persona's items matched well to what other personas wanted. Kai (focal in set_01) closed 0 deals in 2 of 4 runs — the keyboard he was selling had limited demand. Persona choice within a set matters a lot for closure rate."
- "Cross-set variance in mean reward (range 0.40 - 0.65) is comparable in magnitude to cross-config variance — disclose this in the paper as a confound."

**Where to look:** per-run `summary.json` files grouped by `config.persona_set`.

---

## 8. Behavior Pattern Stories (from transcripts)

The qualitative stuff — only visible by reading `channel.jsonl` for specific runs.

**Example findings:**

- "Across all Sonnet-focal runs, we observe Sonnet using strategic delays — passing for 2-3 turns after an offer to signal restraint, then countering with a small concession. Haiku rarely uses this pattern."
- "Haiku frequently 'accepts and announces' — accepting a counter and then saying 'thank you, this is more than I needed'. This reveals it was willing to pay more than what it just paid."
- "In mixed runs, Sonnet agents engaged in coalition-like behavior — three Sonnet sellers all dropped their asking prices when a Haiku buyer entered the market, then one closed at a slight premium. Suggests Sonnet may be modeling other agents' reasoning."
- "Sonnet uses domain-appropriate language: 'firm at $50', 'meet in the middle', 'final offer'. Haiku uses generic language: 'I want $50', 'how about cheaper'. Style and strategy correlate."

**Where to look:** `channel.jsonl` for the 3 most extreme runs (highest reward, lowest reward, biggest self-observer delta). Pull 2-3 transcript excerpts per finding.

---

## 9. Surprises / Counter-Findings

Honest reporting that strengthens the paper.

**Example findings:**

- "In 2 of 5 runs, Haiku-vs-Sonnet (Haiku at disadvantage) actually outperformed Haiku-vs-Haiku (baseline) — Haiku played better when surrounded by stronger opponents. Could be opponent quality lifting all boats, or a sample-size artifact."
- "Sonnet's privacy score was lower than Haiku's in set_05 — possibly because Sonnet's longer, more conversational replies create more opportunities to slip up. Quality doesn't guarantee discretion."
- "Closure rates correlated WEAKLY with reward — closing deals isn't enough if prices are bad. Pareto efficiency was a better predictor of final reward than raw closure."
- "The asymmetry effect appeared in 3 of 5 persona sets but reversed in set_02 — context-dependent, not universal."

---

## 10. Methodology Caveats To Disclose

Limitations to footnote in any paper.

**Example caveats:**

- "With 1 seed per cell (n=5 per config), variance is high and individual findings should be treated as suggestive, not conclusive. Full Phase 2 (n=15 per config) would tighten confidence intervals."
- "Our 5 persona sets vary in deal structure (possible/impossible/unmatched ratios) — cross-set comparisons confound model effects with marketplace topology effects. Within-set comparisons are cleaner."
- "GPT-4o judge ratings are noisy — same transcript can vary ±1 across re-runs. Means across 5 rollouts smooth this somewhat."
- "Each rollout caps at 50 tool calls (`max_steps=50`). Marketplaces that would have closed more deals with longer runs are artificially curtailed. We chose this cap for cost control."
- "The opponent_runner runs one opponent turn per focal action. In real human marketplaces all agents have equal time — our focal effectively gets twice the action ratio. Adjust expectations accordingly."

---

## 11. How To Generate These From Your Data

Step-by-step process after a 20-rollout run completes:

| Step | What to look at | Output of |
|---|---|---|
| 1 | `results/aggregates/phase_1_summary.json` | The headline + asymmetry stories |
| 2 | Each `summary.json` in `results/runs/` (20 of them) | Per-run rubric scores → find outliers |
| 3 | Each `judge_ratings.json` per run | Self vs observer delta → self-perception stories |
| 4 | Each `privacy_findings.json` (where applicable) | Leak details → privacy stories |
| 5 | Scan `channel.jsonl` for the 3 most extreme runs | Quote actual transcripts → behavior stories |

**Quick scan commands:**

```bash
# All run folders, sorted by final reward
for d in results/runs/*/; do
  reward=$(python3 -c "import json; print(json.load(open('$d/summary.json'))['rubric_scores']['final_reward'])")
  echo "$reward $d"
done | sort -n

# All self-observer deltas
for d in results/runs/*/; do
  delta=$(python3 -c "import json; print(json.load(open('$d/judge_ratings.json')).get('self_observer_delta', 'N/A'))")
  echo "$delta $d"
done | sort -n

# All privacy leakage rates
for d in results/runs/*/; do
  if [ -f "$d/privacy_findings.json" ]; then
    rate=$(python3 -c "import json; print(json.load(open('$d/privacy_findings.json')).get('pii_leakage_rate', 'N/A'))")
    echo "$rate $d"
  fi
done | sort -n
```

---

## What This Doc Is And Isn't

**Is:** a catalog of finding-shapes you could write up after Phase 1 completes. Treat each example as "a finding might look like this, fill in your actual numbers."

**Isn't:** claims of fact. The actual data may show none of these patterns, opposite patterns, or new patterns I didn't anticipate. The point is to know what to look for.

**Update this doc** after your real run with the actual findings, in the same style. The structure (Section 1 = Headline, Section 8 = Behavior patterns) carries over directly to your paper's structure.
