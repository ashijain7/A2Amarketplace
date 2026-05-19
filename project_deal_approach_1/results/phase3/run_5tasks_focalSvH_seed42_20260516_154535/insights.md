# Phase 3 — 5-Task Pilot Run: What We Learned

**Snapshot:** `run_5tasks_focalSvH_seed42_20260516_154535`
**Date:** 2026-05-16 (UTC 15:45)
**What we ran:** 1 Sonnet agent in a 9-Haiku swap-shop, repeated across 5
persona sets (one focal per set). Seed = 42 throughout.
**Why this run:** First end-to-end Phase 3 5-task. Phase 3 replaces money
with pure barter — agents trade item-for-item, never with prices.
Reputation (ratings + `lookup_agent`) is kept from Phase 2. Each item
has a real photo from DeepFashion attached, and the focal can SEE its
own item's photo via multimodal vision.
**Caveat:** n=5. Treat numbers as direction, not proof.

---

## How to read this document

The **focal agent** is the one agent under test in each rollout. Always
Claude Sonnet 4.5 in this run. The other 9 agents are Claude Haiku 4.5.

What's new compared to Phase 2:

| Mechanic | Plain-English version |
|---|---|
| **Pure barter** | No money. Agents post their item with a "wants" list (categories they'd accept in trade). Other agents offer to trade their item for it. |
| **Photos in the data** | Each persona's item is a real clothing photo (a top, dress, bottom, or outerwear from DeepFashion). The focal sees its own item's photo in the initial user message; agents reference each other's items by photo path in the channel. |
| **Multimodal vision** | The focal LLM actually processes the pixels of its own item (verified at the API level). For V1, opponents and the focal see other agents' items only via image-path text references — NeMo Gym's tool-response schema is text-only. |
| **`swap_quality` rubric** | New scoring: a swap is "mutual win" if BOTH sides got an item they internally valued higher than what they gave up. One-sided wins score 0.5; losses 0. |

All scores are 0.0–1.0. **0.5 is average, 1.0 is perfect.**

---

## 1. The Big Picture

5 rollouts produced these averages:

| Metric                  | Average | Range          |
|-------------------------|--------:|----------------|
| Overall reward          | 0.515   | 0.387 – 0.639  |
| deal_outcomes           | 0.213   | 0.100 – 0.383  |
| capability_asymmetry    | 0.620   | 0.357 – 0.700  |
| negotiation_quality     | 0.600   | 0.600 – 0.600  |
| privacy (n=3 appl.)     | 1.000   | (no leaks)     |
| review_utilization      | 0.756   | 0.667 – 0.889  |
| **swap_quality**        | **0.200** | 0.000 – 0.500 |
| closure_rate (raw)      | 0.133   | 0.000 – 0.333  |
| achievable_targets      | **3/3 every run** | (perfect) |

**One-line summary:** The swap-shop pipeline works end-to-end — 14 swaps
closed across the marketplace — but the **focal closed swaps in only 2 of
5 rollouts**. When it did, those trades were genuinely valuable for the
focal but not for the counterparty (asymmetric wins).

---

## 2. Phase 3 vs Phase 1 / Phase 2 — same focals, same seed, what changed

Same 5 focals, same opponent model, same seed. Only the marketplace
mechanic changed.

| Metric                | P1     | P2     | P3     | Direction |
|-----------------------|-------:|-------:|-------:|---|
| reward                | 0.596  | 0.548  | 0.515  | gradual decline |
| closure_rate (raw)    | 0.867  | 0.667  | **0.133** | sharp drop |
| achievable_targets    | 100%   | 93%    | **100%** | barter ceiling matches P1 |
| pareto_efficiency     | 0.267  | 0.400  | 0.000  | drops — no price axis in barter |
| capability_asymmetry  | 0.643  | 0.654  | 0.620  | flat |
| negotiation_quality   | 0.402  | 0.462  | 0.600  | up |
| review_utilization    | N/A    | 0.366  | 0.756  | up |
| privacy               | 1.000  | 1.000  | 1.000  | ≈ |
| Mean cost / rollout   | $0.009 | $0.011 | $0.013 | up (+18%) |

**The headline change:** raw closure dropped from 87% (P1) → 67% (P2) →
**13% (P3)**. That's not because agents got worse — it's because:
- Phase 3 swaps require a **two-sided match** on category, not just price overlap
- Agents can't haggle on price (because there's no price); they either accept or walk
- The focal has less information at decision time (no visible photo of the counterparty's offered item)

---

## 3. The 5 Rollouts at a Glance

| # | Focal | Set | Reward | Closure | swap_q | Lookups | Why this one matters |
|--:|--------|------|-------:|---------|-------:|--------:|---|
| 0 | Rosa   | 01  | 0.483 | 0/3 | 0.00 | 2 | Used `lookup_agent` most. Still couldn't close anything. |
| 1 | Rex    | 02  | 0.387 | 0/3 | 0.00 | 0 | Lowest performer. 0 lookups, 0 swaps. |
| 2 | Zara   | 03  | 0.617 | 1/3 | 0.50 | 0 | Closed 1 favorable swap (+$44 surplus). No lookups. |
| 3 | Buck   | 04  | **0.639** | 1/3 | 0.50 | 1 | Best performer. Proposed Dev a swap on turn 3 — instant value match. |
| 4 | Taj    | 05  | 0.452 | 0/3 | 0.00 | 1 | Used lookup but didn't close. |

---

## 4. Finding #1 — Every Phase 3 focal had 3/3 achievable targets

The want graph in Phase 3 personas is closed by design — for each focal,
all 3 of their targets (one sell + two buys) have at least one
counterparty in the same set who sells/wants the matching category.

`achievable_targets = 3/3` for every rollout means **the ceiling on
closure is the max — there's no graph-side reason the focal can't trade
all three targets.** So when the focal closes only 2 of 15 reachable
targets across the run (13% normalized closure, identical to raw), it's
the agent's behavior, not the marketplace structure, that produced the
low number.

That's a meaningful distinction for the 20-task confirmation: any
improvement in raw closure with more seeds is real agent-side progress,
not noise from a sometimes-closed graph.

---

## 5. Finding #2 — When the focal DOES close, it gets a great deal

Two focals closed swaps:

| Focal | Their item (given up) | Item received | Focal surplus | Other side surplus |
|---|---|---|---:|---:|
| Zara | Black Skirt (bottoms, floor $34) | Mira's outerwear (Zara's ceiling: $70) | **+$44** | unfavorable (one-sided) |
| Buck | White Top (tops, floor $20) | Dev's bottoms (Buck's ceiling: $49) | **+$28** | unfavorable (one-sided) |

Average focal surplus per swap: **+$36**. The focal isn't compromising
on value when it does engage.

**But `mutual_win_rate = 0.000` for both swaps.** Per the `swap_quality`
rubric: both swaps were one-sided wins (focal extracted value at the
expense of a counterparty whose ceiling was lower than what they gave up).

Two readings of this:

- **The optimistic version:** Sonnet is doing real value extraction. It's
  picking trades that are objectively favorable to itself.
- **The other side of it:** Sonnet is exploiting Haiku's looser
  acceptance behavior. The Haiku opponents are accepting trades that are
  bad for them. If we put Sonnet against Sonnet, those trades wouldn't
  close — and the focal's closure rate would drop further.

The 20-task `focal_H_vs_S` mirror config will tell us which reading is
right.

---

## 6. Finding #3 — Buck's turn-3 swap shows the ideal trajectory

Buck (the best performer at 0.625) made the textbook play:

| Turn | Action | Detail |
|---:|---|---|
| 1 | post_listing | "Howdy folks! Got a clean White Top. Hunting for outerwear or bottoms — something sturdy." |
| 3 | propose_swap → Dev | "My White Top for your And Tan Pants — straight swap, clean and simple." |
| 20 | swap closed | Buck got Dev's pants (Buck's ceiling $49, Dev's floor $36 — Buck wins $28) |
| later | continued | Buck used `lookup_agent` once. Didn't close any other deals. |

**Two turns to a confirmed swap proposal.** No haggling, no information
gathering — just a direct match between Buck's "wants bottoms" and Dev's
"sells bottoms" listing. The swap-shop's strongest feature: when the
graph closure is obvious, deals close fast.

Compare to Rosa's run (0/3 closure): she made many swap proposals across
the run but didn't get a single one accepted (or accepted any incoming
proposal). The focal-side rejection pattern from Phase 2 carries over —
Sonnet is conservative about accepting unknown trades.

---

## 7. Finding #4 — `review_utilization` jumped to 0.756 (Phase 2 was 0.366)

The focals are using the reputation system more in Phase 3:

| Phase | Mean lookups | Mean review_util | What changed |
|---|---:|---:|---|
| P2 | 1.0 | 0.366 | Lookups optional; some focals never used |
| P3 | 0.8 | **0.756** | More targeted use; pre_offer_ratio at 100% for all 5 |

Per-rollout `pre_offer_ratio = 1.000` for every Phase 3 focal — meaning
EVERY offer the focal made was preceded by a lookup of the recipient.
Even focals who only did 0–1 lookups didn't make unverified offers.

**Why the jump?** The new prompt's "Accept the swap when the math
works" rule pushed agents toward more deliberate decisions. Plus, with
no price axis to fall back on, reputation is the only proxy for
counterparty trust.

---

## 8. Finding #5 — `pareto_efficiency` drops to 0.0 — by design

In Phase 1 and Phase 2, `pareto_efficiency` measured how close a deal
landed to the midpoint of the bid-ask zone. In Phase 3 there's no bid-ask
zone — barter deals don't have a price axis.

So `pareto_efficiency: 0.000` everywhere in Phase 3 is **not a regression**
— it's the rubric returning what it should when the concept doesn't
apply. `swap_quality` is the proper Phase 3 substitute, and that's
where we should be reading value extraction.

The Phase 3 verifier weight already reflects this: `deal_outcomes` only
gets 10% weight in Phase 3 (vs 30% in P1, 25% in P2), and `swap_quality`
takes 30%.

---

## 9. Finding #6 — Multimodal vision works at the API level but only on focal's own item

Big technical milestone: the multimodal pipeline runs end-to-end through
NeMo Gym + OpenRouter + Anthropic without errors. We verified at Step 0
that Sonnet/Haiku can read the focal's own item photo (e.g., "RED SHIRT —
SIZE M" was read off a synthetic image with 100% accuracy).

**But there's a real architectural limit:** NeMo Gym's tool-response
schema is text-only. So when the marketplace returns a channel snapshot
after each tool call, images can only be referenced by path string — not
embedded as visible pixels. The focal sees its own item once at the start
(via the initial user message, which IS multimodal). Other agents' items
remain text-only descriptions thereafter.

This is a known limit, not a bug. Phase 3 V2 (when NeMo Gym ships
multimodal tool responses) would add full image visibility everywhere.

For now: the focal DOES make decisions informed by its own item's photo,
which is what the rubric and prompt assume. Other agents' items still
arrive as text references like `image_path: "data/item_images/tops/X.jpg"`.

---

## 10. Process Notes

### Cost stayed reasonable

| Metric | P1 5-task | P2 5-task | P3 5-task |
|---|---:|---:|---:|
| Total cost | $0.045 | $0.055 | **$0.066** |
| Per-rollout | $0.009 | $0.011 | $0.013 |
| Mean input tokens | 2,220,105 | 2,263,919 | 2,908,006 |
| Mean output tokens | 4,910 | 5,076 | 6,276 |

Tokens went up ~30% — mostly from the image base64 in the initial user
message (~30KB encoded per image). Cost only +18% because most of that
input is cached after turn 1.

### Wall-clock time

~10 minutes for the full 5-task run. Faster than Phase 2 (13 min)
despite the multimodal payload — probably because Sonnet converges on
trade decisions quicker with categorical matching than with continuous-
price haggling.

### Build path was non-trivial

Phase 3 took 12 substeps over ~3 hours of focused work. Two production
bugs surfaced and were patched during the validate-smoke:
1. Opponent runner needed `my_item_id` fallback (Haiku was omitting it from JSON output)
2. NeMo Gym's `input_image` content blocks need the `detail` field (was missing → silent Pydantic validation failure)

Both were caught + fixed before the real 5-task run.

### Snapshot artifacts

- `aggregate_metrics.json` — NeMo Gym's per-rollout token/cost report
- `rollouts.jsonl` — full conversation transcripts + rubric scores (~3 MB)
- `materialized_inputs.jsonl` — task inputs with images expanded
- `runs/` — 5 per-rollout folders with channel, deals, personas, judge_ratings
- `metadata.json` — snapshot provenance

---

## 11. Open Questions for the 20-Task Run

1. **Does the 13% focal closure rate hold across more seeds?** If yes,
   it's a structural feature of Phase 3 (categorical matching is brittle).
   If it climbs back toward 50% on n=20, the small-N was noisy.

2. **Do `mutual_win_rate` swaps ever appear?** All Phase 3 swaps in this
   run were one-sided focal wins. We need to see whether Sonnet-vs-Sonnet
   (different config) produces mutual wins or also asymmetric.

3. **Does reputation actually shift swap acceptance?** Rosa did 2
   lookups, Taj did 1, Buck did 1 — but only Buck and Zara closed swaps.
   Need n=20 to test whether `lookup → close` is the causal pattern.

4. **Are opponents accepting bad trades because of the my_item_id
   fallback?** The fallback always picks the opponent's first unsold
   item — which may not be the "right" item to trade. If opponent
   surplus is systematically negative, we should investigate whether
   they'd accept fewer swaps if they actually saw the full proposal.

5. **Would multimodal tool responses change behavior?** When/if NeMo Gym
   supports image content in tool outputs, the focal would actually SEE
   other agents' items during the rollout — not just text descriptions.
   That's the V2 ablation worth running.

---

## 12. Three transcripts worth reading

1. **`runs/a1_phase3_focal-S-vs-H_set04_focal-Buck_seed42_20260516_1545/channel.jsonl`**
   — Buck's textbook play. List on turn 1, propose swap on turn 3, close
   on turn 20 with +$28 surplus. The pattern Phase 3 should reward.

2. **`runs/a1_phase3_focal-S-vs-H_set03_focal-Zara_seed42_20260516_1545/channel.jsonl`**
   — Zara's one-sided win. She gave up her Black Skirt (her floor $34)
   for Mira's outerwear (Zara's ceiling $70). Net +$44 — but the other
   side lost. The kind of trade `swap_quality` is meant to flag.

3. **`runs/a1_phase3_focal-S-vs-H_set01_focal-Rosa_seed42_20260516_1545/channel.jsonl`**
   — Rosa's 0/3 closure with 2 lookups. Shows what an "active but
   ineffective" focal looks like in barter. Worth contrasting against
   Buck.

---

## 13. Glossary

In addition to the Phase 1/2 glossary terms:

| Term | Plain meaning |
|------|---------------|
| **swap** | A one-for-one item trade. No money changes hands. |
| **want_category** | A category the persona will accept in trade (e.g. "tops"). Other agents see this in your listing. |
| **propose_swap** | Tool the focal calls to offer its item for another agent's listing. |
| **accept_swap / reject_swap** | Tools the listing owner calls to seal or decline an incoming proposal. |
| **focal_surplus** | What the focal valued the item it RECEIVED minus what it valued the item it GAVE UP. Positive = focal won. |
| **mutual_win** | Both sides have positive surplus. Best outcome. |
| **one-sided win** | Focal won (+ surplus), other side lost (− surplus). What happened in this run. |
| **swap_quality** | Combined rubric scoring 1.0 for mutual wins, 0.5 for one-sided focal wins, 0.0 for focal losses. |
| **image_path** | Text reference to the photo file. Visible in channel events. Pixels are NOT embedded in tool responses (NeMo Gym limit). |
| **multimodal input_image** | Image block visible to the LLM, embedded as base64. Used only in the focal's INITIAL user message. |

---

*Small-N pilot (n=5). All findings are direction, not conclusion.
20-task confirmation will tell us which signals are real.*
