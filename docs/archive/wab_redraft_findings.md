# WAB Redraft Findings

Target venue: **Workshop on Agent Behavior (WAB) @ COLM 2026**.
Paper: 4–9 pages, non-archival, double-blind. Deadline **June 23, 2026** (you have until June 19).
Source of these findings: your two Agent4IR reviews + the WAB call-for-papers + six accepted COLM 2025 papers studied for comparison.

Effort tags: `Quick` (mostly writing), `Medium` (some new work/runs), `Heavy` (significant work).

---

# Part 1 — What to prove (strategy and rigor)

## Tier 1 — the moves that change acceptance the most

**1. Re-pitch from "information retrieval" to "agent behavior." `Quick`**
Your reject reviewer's deepest objection was *"the connection to information retrieval is somewhat indirect."* That only existed because you aimed at an IR workshop. WAB's own pitch is *"move beyond capability-centric evaluation to understand how do agents achieve what they achieve?"* — which is your title, *Beyond Task Completion*. Rewrite the abstract, intro, and title to speak their language. The paper ticks three WAB topics: **behavioral evaluations** (your rubric), **agentic interactions / multi-agent dynamics** (the marketplace), and **social & ethical implications** (privacy, fairness). Dropping the IR framing removes the #1 rejection reason.

**2. Build one "money table" that proves your headline. `Medium`**
Your claim is "deal-closure rates hide big behavioral differences." Right now you assert it. Accepted papers prove their version with one number (AgentRewardBench: "30% of trajectories erroneously marked successful"). Make a single table: two model setups with **nearly identical closure rates** but **very different rubric scores**, side by side. That table becomes the spine of the paper.

**3. Have humans check your rubric. `Medium–Heavy`**
Your semantic dimensions are scored only by GPT-4o. Five of the six accepted papers report how well their main metric agrees with humans (AgentRewardBench: 89% annotator agreement; "Illusion of Progress": 86% judge-vs-human). Your reject reviewer said it directly: *"the rubric lacks external validation."* Fix: have 2–3 people score a sample of transcripts on each dimension, then report how often they agree with the GPT-4o judge.

**4. Add basic statistics. `Medium`**
Both reviewers' #1 complaint: 15 runs per setup, no confidence intervals or significance tests (a confidence interval = the error bar showing how much a number might wobble by chance). You may not need hundreds more runs, but you do need **error bars / variance across seeds**, and to soften any claim the numbers can't support. The one accepted paper that reported confidence intervals ("Hell or High Water") stood out for it.

## Tier 2 — credibility fixes

**5. Show your personas in a table. `Quick`**
Review 1 called the persona design *"critically underspecified"* — and personas are the foundation the rubric rests on. Add a table: each persona's price ranges, market structure, negotiating style.

**6. Report every metric you define — or cut it. `Quick`**
Your reject reviewer listed metrics you defined but never reported (perceived fairness, pre-offer ratio, anchoring, smoothness, buyer surplus, rounds-to-close). Either show them in results or delete them. Defined-but-unused metrics read as padding.

**7. Add a "how the agents failed" section with categories and counts. `Medium`**
A six-row score table reads thin. Every accepted paper has a failure/behavior taxonomy with frequencies and examples. You already have the material: your two SwapShop zero-scores came from **opposite** failures — Opus too cautious, Flash too careless — and Review 1 said *don't lump them together.* Name the behavior types, count them, show a transcript snippet.

**8. Give your novel metrics theoretical "teeth," and fix one name. `Quick–Medium`**
Review 1 noted your review/search metrics map onto established theory (search theory, reputation systems) and your surplus metrics onto mechanism design. A few grounding sentences make them look principled. Also rename **"Pareto efficiency"** — your reviewer said what you measure isn't actually that.

## Tier 3 — cleanups (all `Quick`)

**9. Release everything and link it in the abstract** — code, both scenarios, all agent + judge prompts, the scoring spec. All six accepted papers do this; your reviewer flagged reproducibility.

**10. Fix the mirror-comparison claim.** Your cross-run delta metric needs both A-vs-B and B-vs-A runs, which you didn't run — so either run the other direction or drop the claim. Same honesty fix for the Gemini-Flash-substituted-for-Pro confound: say which findings it affects.

**11. Small consistency fixes** — name each model the same way throughout, and either define what a "deadlock" means in SwapShop (which has no prices) or state that the metric doesn't apply there.

---

# Part 2 — How it looks, reads, and lands (presentation and craft)

## Presentation & visuals — the biggest untapped win

**12. Add a "hero figure." `Medium`**
Your paper has **zero figures** — only four numeric tables. Every accepted COLM paper is figure-rich. Add a chart where two models sit at nearly the same closure rate but spread far apart on the rubric, so the reader *sees* your claim. A radar chart or heatmap of all six dimensions across your five models would do it.

**13. Add a simple schematic. `Quick`**
A diagram of the two scenarios plus how scoring flows (message log → deterministic + GPT-4o scoring → six dimensions) helps a reviewer grasp the setup in seconds.

**14. Use your full page budget. `—`**
You used only 5 of the allowed 9 pages. Spend the extra four on a figure, a persona table, a failure-mode section, and validation — not more rubric prose.

## The writing itself

**15. Cut the double-hedging in your results. `Quick`**
Almost every finding sentence hedges twice (*"appeared to collapse," "may be a model-version property," "suggesting that... appears to introduce"*). Keep one honest qualifier, but state the observation crisply first, then qualify once. Right now the prose sounds unsure of its own findings.

**16. Lead the abstract with the finding, not the jargon. `Quick`**
Your first sentence is dense IR theory ("the corpus negotiates back"). Open instead with the Project Deal hook and a concrete number, then the behavioral finding.

**17. Proofread — there are visible slips. `Quick`**
Examples: *"The following sub-metrics measures"* (should be "measure"), *"a seller opening at $32 one a $30–$60 range"* ("one" → "on"), and the model named "Gemini 3.1 Pro Preview / 3.1 Pro / Gemini Pro" in different places. Small errors signal "unpolished."

## Structure & balance

**18. Rebalance rubric vs. results. `Medium`**
Section 4 defines six dimensions in detail; Section 5 (the evidence) is squeezed onto one page and reports only a few metrics. That imbalance reinforces the "rubric strong, evidence weak" complaint. Move full metric definitions to an appendix and let the evidence breathe in the body.

**19. Move worked examples into a table. `Quick`**
The parenthetical worked examples (which the reviewer liked) bloat the prose. Pull them into one compact "worked example" table — keep the clarity, free up space.

## Rigor holes the reviewers didn't catch

**20. Your judge is weaker than the agents it judges. `Medium`**
You score transcripts with GPT-4o (a 2024 model), but your agents are Opus 4.7, GPT-5.5, Gemini 3.x — all newer and stronger. "Judge weaker than judged" is an easy attack. Use a stronger judge, or run two judges and report agreement, or validate against humans (see #3).

**21. Justify or stress-test your thresholds. `Quick`**
Three lookups = full score, 4.0 stars = "high rating," 100-turn cap, 4-turn deadlock. Reviewer 2 called these "heuristic thresholds." Show your conclusions don't flip if you nudge them, or cite a basis.

**22. Two metrics never move — demote or stress them. `Quick`**
Privacy scored 1.00 in 44 of 45 runs; deadlock-handling 1.00 everywhere. A metric that never varies isn't discriminating. Either create harder conditions that make it vary (e.g. stronger privacy pressure), or shrink it to a one-line "baseline confirmed" and reclaim the space.

**23. Make "achievable deals" transparent. `Quick`**
Your closure rate divides by "achievable targets." Spell out exactly how achievability is computed, so it's reproducible.

## WAB-specific strategy — free moves

**24. Also submit a 1–2 page "benchmark proposal." `Quick`**
WAB has a separate benchmark track, and your MarketDeal + SwapShop scenarios are exactly that. Accepted proposals get compute credits and implementation support — which could fund the extra seeds your reviewers want. A second, low-cost shot at the same workshop.

**25. Put it on arXiv now. `Quick`**
WAB is non-archival and encourages preprints and concurrent submissions, so posting a preprint timestamps your contribution and costs you nothing.

**26. Know who's in the room. `—`**
The organizers come from social-simulation and computational-economics backgrounds (MIT Media Lab, Stanford social-agent work, MIT LLM-economics). Framing the work as *social and economic agent behavior* — not a dry metrics list — will resonate with the people reviewing it, and lines up with WAB's "agentic interactions" and "social & ethical implications" topics.

---

## Suggested order for a June 19 finish

Do these four first (highest impact for the effort): **#1** reframe to behavior, **#12** hero figure, **#2** money table, **#5** persona table. Then as much of the rest of Part 1 as time allows (validation #3, stats #4, failure taxonomy #7), then the Part 2 quick polish.
