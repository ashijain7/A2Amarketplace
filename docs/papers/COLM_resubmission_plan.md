# A2A Marketplace Paper — WAB @ COLM 2026 Resubmission Plan

**Status:** proposed plan for discussion.
**Paper:** *Beyond Task Completion: A Rubric for Evaluating Agent-to-Agent Marketplaces* (rejected at Agent4IR @ KDD 2026).
**Target venue:** Workshop on Agent Behavior (WAB) @ COLM 2026 — 4–9 pages, non-archival, double-blind. **Submission deadline 23 June 2026; all work to wrap by 19 June.**

This document covers: what the reviewers asked for, the experiment plan that answers it (built on the 75 rollouts already done), the new transactional-accuracy experiment, the remaining paper-side fixes, and a set of additional observations made while reviewing the work. Every item is mapped to the reviewer comment it addresses.

---

## 1. Target venue — why it fits

The work is being moved from an information-retrieval workshop to the **Workshop on Agent Behavior (WAB) @ COLM 2026**.

- The reject reviewer's deepest objection was that *"the connection to information retrieval is indirect."* That objection only existed because the paper aimed at an IR venue. WAB's own pitch — *understand how agents behave, beyond task success* — is exactly this paper's thesis (*Beyond Task Completion*). Re-pitching to the behavioural framing removes the single largest rejection reason.
- WAB is **non-archival** and **encourages concurrent submissions and preprints**, so the earlier rejection costs nothing.
- The paper fits three named WAB topics: **behavioural evaluations** (the rubric), **agentic interactions** (the marketplace), and **interventions** (the new transactional experiment).
- WAB also runs a separate **1–2 page benchmark track** (proposals only, with implementation support) — a low-cost second route for the MarketDeal / SwapShop scenarios.

---

## 2. Reviewer points — reference key

Used throughout this document so each fix is traceable.

**Review 1 (weak accept).** Strengths to protect: **R1-S1** Project Deal motivation (strongest opening); **R1-S2** Review Utilization (most novel); **R1-S3** precise, replicable sub-metrics; **R1-S4** dual-perspective fairness; **R1-S5** SwapShop; **R1-S6** honesty about limits.
Weaknesses: **R1-W1** underpowered, no error bars / significance; **R1-W2** personas critically underspecified; **R1-W3** novel metrics not grounded in theory; **R1-W4** results only aggregated, no per-persona breakdown; **R1-W5** the two SwapShop zero-scores are opposite failures but lumped together.
Minor: **R1-M1** inconsistent model naming; **R1-M2** "deadlock" undefined for barter; **R1-M3** cross-run delta needs both-direction (mirror) runs; **R1-M4** within-family comparison confounds generation and tier.

**Review 2 (reject).** **R2-W1** ~one run per setup, no confidence intervals / significance / multi-seed; **R2-W2** capability claim not validated — no complete mirror pairings, evaluated model confounded with opponent field; **R2-W3** many defined metrics never reported; **R2-W4** heuristic thresholds; "Pareto efficiency" mislabeled; **R2-W5** no external (human) validation; **R2-W6** IR connection indirect; **R2-W7** reproducibility incomplete; **R2-W8** minor inconsistencies; privacy and deadlock metrics barely vary.

---

## 3. What the paper already does well (protect these)

The real-world Project Deal motivation (R1-S1), the Review Utilization dimension (R1-S2), the precisely-specified sub-metrics with worked examples (R1-S3), the dual-perspective fairness measure (R1-S4), and the SwapShop barter scenario (R1-S5) are the paper's strengths and are kept intact. The plan adds rigor around them; it does not change them.

---

## 4. The two core problems the reviewers raised

### Problem 1 — "Did it really happen, or was it luck?" (R1-W1, R2-W1)

Each exact setup — one model matchup, in one market type, with one trader group — was run a **single time**, giving one score. One run cannot tell a real result from luck. The paper's "15 runs per configuration" was, once split across 3 market types × 5 trader groups, effectively **one run per setup**. The fix is to repeat each setup enough to report a number **with an error bar**.

### Problem 2 — The model comparisons were incomplete (R1-M3, R2-W2)

To prove "Model A beats Model B because A is stronger," both directions must be run — A against a field of B, and B against a field of A (a "mirror"). Only one direction was run, so the paper's own capability-gap measure cannot be computed. Separately, the paper is motivated by Anthropic's finding that **Opus earned more than Haiku**, yet **no experiment actually ran Opus against Haiku.**

---

## 5. The efficient fix — score 3 focal traders per group

Every market has **10 traders**. The shipped paper scored only **1** of them (the focal). The framework's built-in setting evaluates **3 traders per group** — and 3 was the original design; the paper used 1.

The key point for budgeting: **the 1 trader already scored is the 75 completed rollouts.** Moving to 3 means running only the **other 2 traders** — nothing already done is re-run.

| The 3 focal traders, per matchup | Status |
|---|---|
| Trader 1 | already done — this is the 75 rollouts |
| Trader 2 | to add |
| Trader 3 | to add |

Going from 1 → 3 takes each setup from 1 score to 3, and each matchup (across 5 groups) from **5 → 15 scores** — enough for an error bar and a basic significance test, without adding any trader groups and without re-running the 75. The trader-selection rule also forces at least one private-data trader into the three for groups 3–5, which increases privacy-dimension coverage as well.

For the 1–2 **headline** claims only, the same setup is also repeated a couple of times ("seeds") for the strictest proof — a cheap top-up, not applied everywhere.

---

## 6. The model matchups (full experiment list)

Models: **Opus** (Claude Opus 4.7), **Sonnet** (Claude Sonnet 4.5), **Haiku** (Claude Haiku 4.5), **Gemini** (Gemini 3.1 Pro Preview), **Flash** (Gemini 3.5 Flash), **GPT** (GPT-5.5).
One market = 10 traders: 1 **evaluated** model + 9 **opponent field** (all one model).
Market types: **Phase 1** money trading · **Phase 2** money + reputation/reviews · **Phase 3** barter (no money). Each cell = 5 groups × 3 focal = 15 rollouts.

| Evaluated | Opponent field (×9) | Group | Market types | Traders done | Traders to add | New rollouts |
|---|---|---|---|:--:|:--:|--:|
| Sonnet | Sonnet | existing | P1, P2, P3 | 1 | 2 | 30 |
| Sonnet | Gemini | existing | P1, P2, P3 | 1 | 2 | 30 |
| Opus | Gemini | existing | P1, P2, P3 | 1 | 2 | 30 |
| Gemini | GPT | existing | P1, P2, P3 | 1 | 2 | 30 |
| Flash | GPT | existing | P1, P2, P3 | 1 | 2 | 30 |
| **Opus** | **Haiku** | new — motivation | P1, P2, P3 | 0 | 3 | 45 |
| **Haiku** | **Opus** | new — motivation | P1, P2, P3 | 0 | 3 | 45 |
| **Gemini** | **Sonnet** | new — mirror | P1, P2 | 0 | 3 | 30 |
| **Gemini** | **Opus** | new — mirror | P1, P2 | 0 | 3 | 30 |
| **GPT** | **Gemini** | new — mirror | P1, P2 | 0 | 3 | 30 |
| **GPT** | **Flash** | new — mirror | P1, P2 | 0 | 3 | 30 |
| Opus | Sonnet | optional — ladder | P1, P2 | 0 | 3 | 30 |
| Sonnet | Opus | optional — ladder | P1, P2 | 0 | 3 | 30 |
| Sonnet | Haiku | optional — ladder | P1, P2 | 0 | 3 | 30 |
| Haiku | Sonnet | optional — ladder | P1, P2 | 0 | 3 | 30 |
| Opus | Opus | optional — ladder | P1, P2 | 0 | 3 | 30 |
| Haiku | Haiku | optional — ladder | P1, P2 | 0 | 3 | 30 |

**Why these matchups.** The *motivation* pair (Opus vs Haiku, both directions) reproduces Anthropic's finding inside the benchmark and gives the cleanest same-vendor capability gap. The *mirror* matchups complete the second direction of every cross-vendor pairing already run, so the capability-gap measure can finally be computed and the evaluated model is no longer confounded with its opponents (R1-M3, R2-W2). The *ladder* (Opus / Sonnet / Haiku, all pairings) shows the advantage grows with the size of the capability gap. New matchups skip Phase 3 barter on purpose — barter is only needed for the two-failure-mode story, which the existing matchups plus Opus vs Haiku already cover.

---

## 7. How many rollouts in total

| Plan | What it covers | Already done | New to run | Total data |
|---|---|--:|--:|--:|
| **A — fix statistics only** | the 5 existing matchups → add traders 2 & 3 | 75 | **150** | 225 |
| **B — floor** | A + Opus↔Haiku + all mirror matchups | 75 | **360** | 435 |
| **C — recommended** | B + the full Claude capability ladder | 75 | **540** | 615 |

**75 are done.** Adding the 2 remaining traders to the existing matchups = **150 more**; adding the mirror matchups too = **360**; adding the full ladder as well = **540**. The 75 are never re-run.

*To confirm on day 1:* that the trader already run is genuinely "trader 1 of 3" the selection picks, so the new runs pool cleanly with the 75. For one or two private-data groups this may need a small adjustment — flagged, not a blocker.

---

## 8. Proposed experiment structure — two separate, non-overlapping tracks

The experiments are organised into **two independent tracks that do not overlap**. Track 1 measures negotiation behaviour with **no payment step**; Track 2 measures payment safety with the **payment step on**. They are kept separate by design for three reasons:

1. **To protect the 75 completed rollouts.** The 75 contain no payment step. For the new runs to pool with them like-for-like, the new rubric runs must also be payment-free. Switching payment on changes the simulation — agents spend turns paying rather than trading, the turn order shifts, new private fields appear — which would move the rubric scores for reasons unrelated to the model and break comparability with the 75.
2. **The transactional result needs both payment modes.** The headline transactional finding is the *gap* between real-card paying and mandate paying, which requires both modes. The main rubric runs are a single setup; combining the two would mean running the entire matrix twice, for no benefit to the matchups outside the payment study.
3. **Payment applies only to money markets.** There is no payment in barter, so the transactional track is confined to Phase 1 (optionally Phase 2). Phase 3 stays in Track 1 only.

| | Track 1 — Rubric / capability | Track 2 — Transactional |
|---|---|---|
| Payment step | off | on |
| Question answered | reviewer fixes (error bars, mirror comparisons, Opus vs Haiku) | new finding (private-data leak gap) |
| Rollouts | 75 done + new 3-focal & mirror runs (§6–7) | separate focused batch (~60–120) |
| Conditions | Phase 1, 2, 3 | two payment modes (real-card vs mandate) |
| Models | all listed matchups | Opus + Haiku |
| Market type | money, reputation, barter | money only (Phase 1, optionally Phase 2) |

The 75 completed rollouts are reused in Track 1 only and never re-run. Track 2 reuses the same five persona groups and the same 3-focal machinery, so the only genuinely new work is building the payment step (needed regardless) plus the extra rollouts. Conceptually, Track 2 is "a payment condition layered on Phase 1," the same way Phase 2 layered reputation on Phase 1.

---

## 9. Transactional-accuracy experiment (Track 2)

**Idea.** Today the marketplace stops at "deal agreed" — no money moves. This experiment adds the paying step and measures whether the agent leaks its owner's private payment details while paying.

**The intervention — two ways to pay:**
- **Human-rail:** the agent holds the real card / UPI details and must use them to pay. Risk: it may reveal those details in conversation.
- **Agent-native (mandate):** the agent holds only a capped permission ("spend up to ₹15,000/month") and never sees the real details. Almost nothing can leak.

The **gap in leak rate** between the two is the headline result.

**Why it is worth adding:** it is a genuinely new contribution (the paper's own listed future work — executed transactions); it fits WAB's "interventions" theme directly; and it rescues the privacy dimension, which currently scores a flat 1.00 everywhere (R2-W8) — the real-details condition is exactly what makes privacy vary.

**Design.**

| Knob | Setting |
|---|---|
| Conditions | 2 — human-rail vs agent-native (mandate) |
| Models | Opus (strong) + Haiku (weak) — tests whether capability affects payment safety too |
| Market type | money trading (Phase 1; optionally Phase 2) |
| Trader groups | the same 5, with 3 focal traders each |
| Measured | credential leak rate across all channels (public chat, private buyer–seller room, payment-tool inputs, logs); optionally two cheap correctness checks — paid the right person, did not pay twice |

**Rollouts:** 2 models × 2 conditions × 5 groups × 3 focal = **60** (Phase 1 only); **120** with Phase 2.

**What must be built first, and the safety net.** The paying step does not exist yet — it requires building the settlement layer (the payment tools, the two payment modes, the leak capture). This is the riskiest part of the timeline. Hard checkpoint: **by day 3, if it is not producing leak numbers, the transactional experiment is dropped from the main paper** (the strengthened paper stands on its own) **and submitted instead as a 1–2 page WAB benchmark proposal.** Either way, a submission goes in.

**Out of scope (too large for the timeline):** the planted-cheater attacks and the full five-area transaction rubric, both left as future work / the released benchmark.

---

## 10. Remaining work beyond the runs (paper-side fixes)

E = execution, W = writing.

**Reporting & analysis (from existing run data, no new simulations):**
- Report every sub-metric already computed (buyer surplus, rounds-to-close, perceived fairness, anchoring, smoothness, pre-offer ratio). (W/E — R2-W3)
- Per-trader-group breakdown, not just averages. (W — R1-W4)
- Split the two barter failure modes (Opus too cautious vs Flash too careless): name, count, show a snippet. (E/W — R1-W5)

**Documentation & grounding (writing):**
- A persona table — price ranges, market structure, negotiating style per group. (W — R1-W2)
- Tie the novel metrics to established theory (search theory, reputation systems, mechanism design). (W — R1-W3)
- Rename "Pareto efficiency" and justify the threshold choices. (W — R2-W4)

**Validation & judge rigor (small new work):**
- The scoring judge (GPT-4o, 2024) is weaker than the agents it scores (Opus 4.7, GPT-5.5, Gemini 3.x). Move to a stronger judge, or run two judges and report agreement. Affects every score — decide before the large run batches. (E — see C4)
- Human spot-check: 2–3 people score ~15–20 transcripts; report agreement with the judge. (E/W — R2-W5)

**Presentation & framing (writing):**
- Re-pitch from information retrieval to agent behaviour. (W — R2-W6)
- Add figures: one "hero" chart (same closure rate, very different rubric scores) and one scenario schematic. (W)
- Polish: consistent model naming, define "deadlock" for barter, reduce double-hedging, proofread, use the full page budget. (W — R1-M1, R1-M2, R2-W8)

**Reproducibility & submission:**
- Release code, prompts, tool schemas, judge prompts, settings. (E — R2-W7)
- Reformat to the COLM template; anonymize for double-blind review. (W)
- Optional: arXiv preprint; benchmark-track proposal. (W)

---

## 11. Additional observations (beyond the reviewers)

Issues found while reviewing the work that the reviewers did not raise:

- **C1 — The motivation was never tested.** The paper's entire hook is Anthropic's Opus-vs-Haiku result, but no experiment ran Opus against Haiku. The matchups exist in the code unused. The motivation pair in §6 closes this — the highest-value, lowest-cost addition.
- **C2 — Turn-cap inconsistency.** The paper states a 100-turn cap and normalizes metrics against 100, but the code sets the cap at 120. Reconcile the number across text, scoring, and code before release.
- **C3 — Two dimensions never vary.** Privacy scored 1.00 in 44 of 45 runs; deadlock 1.00 everywhere. A metric that never moves invites "why is it here." The transactional experiment makes privacy vary (the rescue); deadlock should be redefined for barter or reported as a saturated baseline.
- **C4 — The judge is weaker than the judged.** Scoring with GPT-4o while agents are Opus 4.7 / GPT-5.5 / Gemini 3.x is an easy attack. Use a stronger judge or two-judge agreement. This sits under every number.
- **C5 — Small-n honesty, still.** Even with 3 focal traders, the sample stays modest. Report medians with bootstrap confidence intervals, use non-parametric tests for the headline contrasts, and claim significance only where it holds. Over-claiming would repeat the original mistake.
- **C6 — Double-blind readiness.** The current draft carries author names, affiliation, and ACM/IR formatting. It must be anonymized and moved to the COLM template, or risk a desk reject.
- **C7 — Trace every number to its source.** The authoritative scores are the per-run archive folders, not the partial combined file. State the exact sample size and ensure every printed number traces to an archive.
- **C8 — The opponent-field confound is structural.** Each evaluated model faces a single-model field. The mirror design is the fix — and the paper should state explicitly that the field is identical across a mirrored pair, so the measured difference is attributable to swapping the evaluated model.

---

## 12. Open decisions (pending)

1. **Run-plan size:** A (statistics only, +150), B (floor, +360), or C (recommended, +540)?
2. **Transactional scope:** Opus + Haiku only, or add Sonnet; Phase 1 only or Phase 1 + 2; leak rate only or leak rate + the two correctness checks.
3. **Judge model:** stronger single judge, two-judge agreement, or judge + human spot-check.
4. **Within-family confound (R1-M4):** check whether Gemini 3.5 Pro is now available; if so, add it to remove the generation/tier confound.
5. **Headline seed top-up:** how many repeat seeds on the 1–2 headline contrasts.
6. **Budget ceiling and day-by-day schedule** — to be built once the run-plan size is chosen.

---

## 13. Reviewer-point → fix traceability

| Reviewer point | Addressed by |
|---|---|
| R1-W1 / R2-W1 (underpowered, no error bars) | 3 focal traders (§5) + headline seeds + statistics (C5) |
| R1-M3 / R2-W2 (mirrors, ΔSM, confound) | mirror matchups (§6) + explicit field statement (C8) |
| R1-W2 (personas underspecified) | persona table (§10) |
| R1-W3 (no theory grounding) | theory grounding (§10) |
| R1-W4 (no per-persona breakdown) | per-group breakdown (§10) |
| R1-W5 (two barter modes lumped) | split failure modes (§10) |
| R2-W3 (metrics defined not reported) | report all sub-metrics (§10) |
| R2-W4 ("Pareto" mislabel, thresholds) | rename + justify (§10) |
| R2-W5 (no external validation) | human spot-check (§10) |
| R2-W6 (IR connection) | re-pitch to behaviour (§1, §10) |
| R2-W7 (reproducibility) | release package (§10) |
| R2-W8 (inconsistencies, flat metrics) | naming/polish (§10) + transactional rescues privacy (§9, C3) |
| R1-M1 / R1-M2 (naming, barter deadlock) | polish (§10) |
| R1-M4 (generation/tier confound) | Gemini 3.5 Pro check (§12) |
| (new) transactional accuracy | Track 2 (§8–9) |
| (observed) motivation untested | motivation pair (§6, C1) |
| (observed) weak judge | judge decision (§10, C4) |

---

## 14. Findings from the Accepted-Submission Review

*Digest of `docs/wab_redraft_findings.md`, which compared this paper against the two reviews and six accepted COLM 2025 papers. Items already covered elsewhere in this plan carry a cross-reference (↔ §x) so the duplicates can be trimmed later if we choose; items marked **new** are not yet in the plan above.*

### 14.1 The accepted papers we are benchmarking against (the evidence) — new

The findings were drawn from six accepted COLM 2025 papers, which set the bar this submission must clear. Concrete targets worth matching: AgentRewardBench reports about 89% agreement with human annotators and the sharp headline "30% of trajectories erroneously marked successful"; "Illusion of Progress" reports 86% judge-vs-human agreement; "Hell or High Water" stood out for reporting confidence intervals. Together these give us specific numbers to match on human validation, a model for one crisp headline statistic, and a precedent for error-bar reporting.

### 14.2 Strategy & rigor

- **Reframe from information retrieval to agent behaviour.** The reject reviewer's deepest objection was the indirect IR connection, which only existed because the paper targeted an IR venue. Rewriting the title, abstract, and intro in WAB's behavioural language removes that objection. *(↔ §1, §10)*
- **Build one "money table."** The central claim — closure rates hide large behavioural differences — should be proven with a single table showing two setups at near-identical closure rates but very different rubric scores. Accepted papers anchor their claim in one such number; this table becomes the spine of the paper. *(data is in §6–7; the single spine-table framing is new)*
- **Human validation.** Semantic scores currently come only from GPT-4o, and reviewers said the rubric lacks external validation. Have 2–3 people score a sample of transcripts per dimension and report how often they agree with the judge. *(↔ §10)*
- **Basic statistics / error bars.** Both reviewers' top complaint was one run per setup with no confidence intervals. Report variance across the repeated runs and soften any claim the numbers cannot support; the one accepted paper that reported CIs stood out for it. *(↔ §5, C5)*
- **Persona table.** Review 1 called the personas "critically underspecified," and they are the foundation the rubric rests on. Add a table giving each persona's price ranges, market structure, and negotiating style. *(↔ §10)*
- **Report every metric or cut it.** The reject reviewer listed several metrics defined but never reported; defined-but-unused metrics read as padding. Either show them in results or delete them. *(↔ §10)*
- **Failure taxonomy with counts.** A six-row score table reads thin, while every accepted paper has a failure/behaviour taxonomy with frequencies and examples. Beyond splitting the two opposite barter failures, name the behaviour types, count them, and show a transcript snippet. *(↔ §10; extends R1-W5)*
- **Theory teeth + rename Pareto.** The novel search/review metrics map onto search theory and reputation systems, and the surplus metrics onto mechanism design — a few grounding sentences make them look principled. Also rename "Pareto efficiency," which does not measure what the name claims. *(↔ §10)*
- **Release everything and link it in the abstract.** All six accepted papers release code, scenarios, prompts, and the scoring spec, and the reviewer flagged reproducibility. Release the full package and link it from the abstract. *(↔ §10)*
- **Fix the mirror claim.** The cross-run delta needs both A-vs-B and B-vs-A runs, which were not done, so either run the other direction or drop the claim. The same honesty applies to the Gemini-Flash-for-Pro substitution — state which findings it affects. *(↔ §6, §8)*
- **Consistency fixes.** Name each model the same way throughout, and either define "deadlock" for barter (which has no prices) or state the metric does not apply there. Small inconsistencies signal an unpolished paper. *(↔ §10)*

### 14.3 Presentation & craft

- **Hero figure.** The paper currently has zero figures while every accepted COLM paper is figure-rich. Add a chart where two models sit at the same closure rate but spread far apart on the rubric, so the reader sees the claim. *(new)*
- **Schematic.** A simple diagram of the two scenarios plus how scoring flows (message log → deterministic + judge scoring → dimensions) lets a reviewer grasp the setup in seconds. *(new)*
- **Use the full page budget.** Only 5 of the allowed 9 pages were used; spend the extra space on a figure, the persona table, the failure section, and validation — not more rubric prose. *(new)*
- **Cut the double-hedging.** Almost every finding sentence hedges twice ("appeared to," "may be," "suggesting"). State the observation crisply first, then qualify once. *(↔ §10 polish)*
- **Lead the abstract with the finding.** The first sentence is dense IR theory; open instead with the Project Deal hook and a concrete number, then the behavioural finding. *(new)*
- **Proofread.** There are visible slips (a verb-agreement error, a typo, inconsistent model names) that signal "unpolished." A careful pass fixes these. *(↔ §10)*
- **Rebalance rubric versus results.** The rubric section is long and detailed while the evidence is squeezed onto one page, reinforcing the "rubric strong, evidence weak" complaint. Move full metric definitions to an appendix and let the evidence breathe in the body. *(new)*
- **Move worked examples into a table.** The parenthetical worked examples the reviewer liked bloat the prose; pull them into one compact table to keep the clarity and free up space. *(new)*

### 14.4 Rigor holes the reviewers did not catch

- **The judge is weaker than the judged.** Scoring is done by GPT-4o (2024) while the agents are newer and stronger — an easy attack. Use a stronger judge, run two judges and report agreement, or validate against humans. *(↔ C4)*
- **Justify the thresholds.** Several thresholds (three lookups = full score, 4.0 stars = high rating, the turn cap, the deadlock window) were called heuristic; show the conclusions do not flip if they are nudged, or cite a basis. *(↔ §10)*
- **Two metrics never move.** Privacy scored 1.00 in 44 of 45 runs and deadlock 1.00 everywhere; a metric that never varies is not discriminating. Either create harder conditions so it varies, or shrink it to a one-line baseline. *(↔ C3)*
- **Make "achievable deals" transparent.** Closure rate divides by "achievable targets," so spell out exactly how achievability is computed, for reproducibility. *(new)*

### 14.5 WAB-specific moves and suggested order

- **Submit a benchmark-track proposal too.** WAB's separate 1–2 page benchmark track fits MarketDeal + SwapShop exactly, and accepted proposals get compute credits and implementation support — a second, low-cost shot at the same workshop. *(↔ §1, §9)*
- **Post an arXiv preprint.** WAB is non-archival and encourages preprints, so posting one timestamps the contribution at no cost. *(↔ §10)*
- **Know the audience.** The organizers come from social-simulation and computational-economics backgrounds; framing the work as social and economic agent behaviour will resonate more than a dry metrics list. *(new)*
- **Suggested order for a June 19 finish (from the findings).** Do the four highest-impact items first — reframe to behaviour, hero figure, money table, persona table — then validation, statistics, and the failure taxonomy, then the quick presentation polish. *(new)*
