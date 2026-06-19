# Reviewer Notes — *Beyond Task Completion: A Rubric for Evaluating Agent-to-Agent Marketplaces*

Target venue: **Workshop on Agent Behavior (WAB) @ COLM 2026** — double-blind, non-archival, 4–9 pages, COLM template, OpenReview. Deadline **June 23, 2026 (AoE)**.
Paper file: `A2A_COLM_2026/agent2agentmarketplace_COLM.tex`
Review started: 2026-06-19. This is a living document — we add one section at a time.

---

## Severity legend
- 🔴 **Blocking** — factual/consistency error that breaks reviewer trust; must fix before submission.
- 🟠 **Major** — meaningfully weakens the paper; a reviewer is likely to raise it.
- 🟡 **Minor** — worth fixing; small credibility or clarity cost.
- ⚪ **Nit** — cosmetic (wording, typo, formatting).

---

## How WAB / COLM reviews papers (the lens used here)
- **WAB has no published rubric of its own** (first-edition workshop). Reviewers will default to **COLM's general review philosophy** + normal ML/NLP habits.
- **COLM scores five qualitative dimensions**, not one number: (1) Empiricism / data / evaluation; (2) Technological impact; (3) Ambition / vision; (4) Depth of understanding / principled approach; (5) Clarity / honesty / trust. Excellence in *one* is already a real contribution; weakness in some is *not by itself* grounds for rejection.
- **"No state-of-the-art" is explicitly OK.** The bar is *new, relevant, useful knowledge*. Position papers are an accepted COLM contribution type.
- **Highest-risk axes for this paper:** *Empiricism* (are the numbers real/sufficient?) and *Clarity/Honesty/Trust* (do claims match evidence; is the paper internally consistent?).
- **Don't count on a rebuttal.** Author responses barely move scores except on borderline papers, and it's unknown whether WAB even has a rebuttal round. **The submitted draft must stand on its own.**

Sources: aiagentbehavior.com; colmweb.org ReviewGuide / AC-guidelines / CFP; ICLR 2026 Reviewer Guide; review-mining studies (Chakraborty 2020, Gao 2019).

---

## Ground-truth check (results folder, verified 2026-06-19)
Counted directly from `results/paper_runs/`:
- **7 configs**: C1, C4, C6, C7, C8, C9, C10.
- **4 phases** each (Stages I–IV), **5 persona sets** each.
- **140 archived runs** (7 × 4 × 5) — every cell present in the per-run archive folders.
- `rollouts.jsonl` totals 139 (C1/phase2 has 4 lines; the salvaged Kai run is in the archive folder but not the jsonl). **Authoritative count = 140 from archives.**

**Locked facts for the whole paper:**
- Run count = **140** (not 75).
- Configurations = **7** (not 5). The two missing from Table 1 are **C9 Opus 4.8 (vs GPT-5.5)** and **C10 GPT-5.5 (vs Opus 4.8)** — the *mirrored pairing*.

---

## GLOBAL INCONSISTENCY TRACKER (the "5-vs-7 / 75-vs-140" cluster)
The paper was scaled up from an earlier design (5 configs × 3 stages = 75 runs) to the current one (7 configs × 4 stages = 140 runs), but several front-matter spots were never updated. Fix all of these together:

| Location | Line | Says | Should say | Status |
|---|---|---|---|---|
| Abstract | 64 | "75 runs" | "140 runs" | ✅ fixed |
| Contributions | 83 | "140 runs" | (correct) | ok |
| Intro prose | 85 | "five model configurations" + 3 categories | "seven" + add *mirrored pairing* | ✅ fixed |
| Table 1 body | 108–109 | 5 rows | added C9 + C10 rows; created `anthropic2026opus48` bib entry | ✅ fixed |
| Table 1 caption | 116 | "Five model configurations evaluated." | "Seven…" (enriched, defines 9×) | ✅ fixed |
| Methodology | 125 | "seven configurations" / "140 runs" | (correct) | ok |
| Results | 256 | "seven model configurations" | (correct) | ok |

---

## Section 1 — Abstract (line 64)
Overall: well-written, correctly framed as a position paper. The "what vs how" contrast and "rule change as a behavioral *intervention*" framing land squarely on WAB's theme — keep that spine.

### 🔴 BLOCKING — "75 runs" contradicts the rest of the paper
- **Problem:** Abstract says "75 runs"; Contributions (l.83) and Methodology (l.125) say 140; archive folders confirm **140**.
- **Why it matters:** Clarity/Honesty/Trust — the first number disagreeing with the body makes a reviewer distrust every later number, and a rebuttal can't fully repair that.
- **Fix:** Use **140** everywhere. (Verified against results folder.) → applied.

### 🟠 MAJOR — abstract hides the strongest result (settlement under a scammer)
- **Problem:** Abstract lists exploitation, reputation-ignoring, and privacy leakage, but never mentions the **payment/settlement stage under an adversary**, which the paper itself calls the sharpest separator between model generations (l.264–265) and leads the conclusion with.
- **Why it matters:** Technological impact / ambition. This is the most novel, most reviewer-grabbing contribution ("no marketplace benchmark scores payment safety"); burying it undersells the paper.
- **Fix:** Add a clause to the results sentence naming the settlement-safety separation. → applied.

### 🟠 MAJOR — abstract over-promises privacy leakage
- **Problem:** Headlines "leaking its principal's private information under pressure," but results (l.270) show Persona Privacy departed from a perfect score in **only three runs**, each a soft paraphrase — almost no leakage occurred.
- **Why it matters:** Empiricism/Honesty — a reviewer reading near-perfect 1.00s in the privacy table sees a phenomenon promised but not delivered.
- **Fix:** Reframe privacy as a behavior the rubric *checks for* (motivation), and keep the *results* sentence to what actually separated. → applied (privacy moved to the motivation list; removed from the results claim).

### 🟡 MINOR — "fail entirely once peer reviews are introduced" is loosely supported
- **Problem:** The model that collapses in the reviews stage (Opus 4.7, closure 0.20) was not "excelling" at basic trading either (Stage I score 0.42). The "fall to zero" half *is* clean for the swap stage (mutual-win rate → 0.00).
- **Why it matters:** A careful reviewer maps the punchline onto your own table and finds the "reviews" half doesn't hold.
- **Fix:** Lead the punchline with the clean swap-collapse fact instead. → applied.

### ⚪ NIT — "becoming a real setting" (l.64)
"a live setting" / "an emerging setting" reads stronger. → applied ("live").

---

## Section 2 — Introduction (lines 70–107)
Four motivation paragraphs (73, 75, 77, 79) + contributions (82–87) + Table 1 (89–107).

**Project Deal numbers — verified against the live Anthropic page (anthropic.com/features/project-deal) on 2026-06-19:**
- ✅ Correct: 69 employees; 186 deals; "over $4,000"; one week; Opus seller +$2.68; Opus buyer −$2.45; fairness 4.05 vs 4.06; "essentially identical."
- ❌ Not in source: see issues below.

### 🔴 BLOCKING — Table 1 lists 5 configs; paper uses 7 (l.79, l.89–107)
- **Problem:** Table 1 has 5 rows and caption "Five model configurations evaluated" (l.105); intro prose (l.79) says "five model configurations" + only 3 pairing categories. But Methodology (l.~128) and Results (l.~259) say "seven," and every results table has 7 rows. The table contradicts the two sentences that cite it. Missing: **C9 Opus 4.8 (vs GPT-5.5)** and **C10 GPT-5.5 (vs Opus 4.8)** — the *mirrored pairing*.
- **Why it matters:** Clarity/Honesty/Trust; a table that disagrees with the body is an instant credibility hit.
- **Fix:** Add the two rows; caption → "Seven…"; intro → "seven … spanning symmetric self-play, cross-vendor pairing, a within-family generation comparison, and a mirrored pairing."

### 🟠 MAJOR — "Opus 4.8" is uncited; no bib entry exists
- **Problem:** Opus 4.8 anchors the settlement headline (C9/C10, "resists every scam") but has **no bibliography entry** (only `anthropic2026opus47` exists) and is never `\citep`'d.
- **Why it matters:** A central model with no reference looks careless; the new Table 1 row needs a citation.
- **Fix:** Create `anthropic2026opus48` (model id `claude-opus-4-8`), cite on first use (new C9 row). **URL needs confirmation** before commit.

### 🟠 MAJOR — "Project Deal's most important finding went unmeasured" is factually wrong (l.75)
- **Problem:** Anthropic *did* measure and report the $2.68/$2.45 and fairness numbers (they are on the page). "Went unmeasured" is false and self-contradictory with the precise numbers that immediately follow.
- **Why it matters:** A reviewer who opens the cited page sees the finding *was* measured — directly undercuts the Honesty axis.
- **Fix:** Reframe to "reported but not foregrounded as an evaluation gap," e.g. "Project Deal reported — almost in passing — a finding that outcome-only metrics would miss."

### 🟠 MAJOR — "a swing of 15–25% per deal" is not in the source (l.75)
- **Problem:** The page gives no overall percentage; its only comparable figure is one illustrative example (a bike: $38→$65, a 70% increase). "15–25%" appears unsourced.
- **Fix:** Drop it (keep the sourced $2.68/$2.45), or replace with the clearly-attributed bike example as illustrative.

### 🟠 MAJOR — "median of $2.68" should be "on average" (l.75)
- **Problem:** Page says "+$2.68 more on average"; paper says "a median of $2.68." Median ≠ mean.
- **Fix:** "earned $2.68 more per item on average … and paid $2.45 less."

### 🟡 MINOR — fairness scale is glossed and clashes with the paper's own (l.75)
- **Problem:** Project Deal's scale is bipolar — "1 (unfair to one party) to 7 (unfair to the other)," 4 = balanced midpoint. Writing "4.05 vs 4.06 out of 7" reads like a higher=fairer scale and clashes with the paper's OWN fairness rubric (1=exploited, 7=fair, l.~177/456). The "nearly identical" claim itself is correct.
- **Fix:** Say "perceived fairness was essentially identical (4.05 vs. 4.06)" and drop "out of 7," or add one clause explaining the balanced-midpoint scale.

### 🟡 MINOR — "no marketplace benchmark scores it" is an absolute (l.77)
- **Problem:** A reviewer could counter with AgenticPay / TessPay.
- **Fix:** Scope it: "no marketplace benchmark scores settlement *as a behavioral dimension* — whether an agent pays safely and honestly."

### ⚪ NIT — "summarised" (l.79)
British spelling; rest of paper is American ("behavior," "operationalize"). → "summarized." (Also "recognises" ~l.177 — track for the spelling pass.)

### ⚪ NIT — Table 1 caption is bare and "9×" is undefined
Reviewers like self-contained tables. Optional richer caption: "Seven model configurations. Each run pits one evaluated agent against a field of nine opponent agents drawn from a single model (9×), spanning symmetric self-play, cross-vendor, within-family, and mirrored pairings."

### ⚪ NIT — three .bib files; only `colm2026_conference.bib` is active (l.390)
`agent2agentmarketplace_COLM.bib` shares the paper's name but is **not** used — a trap if edited by mistake. (Citation pass.)

---

**Section 2 fixes applied 2026-06-19** (paper recompiled clean, no undefined citations): Table 1 +2 rows & enriched caption; `anthropic2026opus48` bib entry created; "went unmeasured" reframed; median→average; 15–25% dropped; fairness scale explained; "no benchmark scores it" scoped; intro five→seven + mirrored pairing; "summarised"→"summarized". Originals preserved as commented blocks. (Note: the "as a behavioral dimension" addition at l.80 was an in-line add — nothing removed — so it was not comment-wrapped.)

---

## Section 3 — Related Work (lines 120–136)
Five paragraphs. External numbers verified against source papers on 2026-06-19.

### 🟠 MAJOR — TITLE COLLISION with a paper you cite (title l.32 vs `cao2026`)
- **Problem:** This paper's title is "**Beyond Task Completion**: A Rubric for Evaluating Agent-to-Agent Marketplaces." The cited `cao2026` paper (arXiv 2603.03116) is titled "**Beyond Task Completion**: Revealing Corrupt Success in LLM Agents…" — same lead phrase, same year, same area.
- **Why it matters:** The title is the first thing a reviewer reads. Sharing the exact lead with a contemporaneous paper you cite reads as derivative and is easy to mistake for sloppiness. Originality/Clarity axis.
- **Fix:** Rename the lead phrase. Options: "Beyond the Deal," "How Agents Trade, Not Just Whether," "Trading Behavior, Not Just Outcomes," etc. (decision pending).

### 🟠 MAJOR — "3.2× the wealth" is not in Diagon's abstract (l.129)
- **Problem:** Diagon = "When Agent Markets Arrive" (arXiv 2604.06688). The system name "Diagon" and the market cycle ✅ check out. But the abstract reports only "market exchange generates more **productivity gains** over self-sufficient agents… depend strongly on institutional structure" — **no "3.2×" multiple**, and "productivity gains," not "wealth."
- **Why it matters:** Same risk as the dropped 15–25% — a specific number a reviewer can't find in the source. (Could be in the full PDF body; abstract-only check.)
- **Fix:** Confirm 3.2× is in the paper body (then keep, ideally cite the section); else soften to the abstract's actual claim. Decision pending.

### 🟡 MINOR — "68.9%" attribution is slightly off (l.136)
- **Problem:** AgentLeak (arXiv 2602.11510): 68.9% is **total system exposure aggregated across channels**; the inter-agent channel (C2) alone is **68.8%**, vs **27.2%** for final outputs (C1). The .tex attributes 68.9% to "internal inter-agent channels."
- **Why it matters:** Numbers are essentially right (68.8 ≈ 68.9) and "far above output-only audits" is well-supported (output-only misses ~41.7%), but a precise reviewer notes 68.9% is the aggregate.
- **Fix:** "…push total privacy leakage to 68.9% (inter-agent messages alone leak at 68.8%, vs 27.2% for final outputs)," or just "to 68.9% overall."

### ✅ VERIFIED — "27–78% corrupt successes" (`cao2026`, l.126)
Exact match to source ("27-78% of benchmark reported successes are corrupt successes concealing violations across interaction and integrity"). Leave as is.

### 🟡 MINOR — repeated four-item list
"reputation use, privacy exposure, negotiation process, and transactional …" appears 3× in Related Work alone (l.123, 126, 129) and again elsewhere. Reads repetitive. Vary or trim.

### ⚪ NIT — "open source toolkit" (l.123) → "open-source toolkit" (hyphenate compound adjective; Magentic's own title uses "Open-Source").
### ⚪ NIT — double blank line after l.129 (l.130–131). Formatting pass.
### Optional — consider citing "Task Success is not Enough" (COLM 2024) — directly on-theme (behavior critics for undesirable agent behavior), strengthens the behavioral-evaluation lineage.

---

## External reviewer reports — triage (received 2026-06-20)
Two reviews of the **earlier submission** (they describe it as "six-dimension, 75 runs, five configs" — i.e., pre-settlement/Transactional-Integrity, pre-expansion). Triaged to small/doable fixes only; major asks (more seeds/CIs/significance, full persona docs + validation, persona-wise breakdowns, human validation, deep theory grounding, IR-framing) flagged as **not doable now**. Reviewers' core reject reason = underpowered study (1 run/cell) — unchanged by minor edits.

**Applied 2026-06-20 (no manual compile — IDE builds; verified by citation key-matching):**
- ✅ Gemini naming standardized to **"Gemini 3.1 Pro Preview"** (25 spots; perl negative-lookahead so no "Preview Preview"; verified 0 stragglers).
- ✅ Citations added (R1 weakness #3, "citation" half): Stigler 1961 + Diamond 1971 (search) and Resnick 2000 (reputation) in Review Utilization intro; Myerson–Satterthwaite 1983 (bilateral-trade efficiency) in the new Pareto footnote. 4 bib entries; all resolve.
- ✅ "Pareto efficiency" Option A: footnote clarifying informal usage (no rename, `PE` column untouched).

**Resolved independently by user's own edits (so dropped from my list):**
- DO now states weighted formula (l.193); CA rewritten to `0.6·SM-hat + 0.4·PF/7` with ΔSM dropped (was never computed) — fixes the "mean→weighted" issue AND the ΔSM-mirror reviewer point.

**Still optional / on user:** point-to-appendix sentence for "unreported" sub-metrics (PF/POR/anchoring/etc. are in App tables); within-family confound specificity; reproducibility pointer; title rename (cao2026 collision).

## Sections still to review
- [x] Section 2 — Introduction (reviewed + fixed)
- [~] Section 3 — Related Work (reviewed + mostly fixed)
  - **Applied 2026-06-19** (recompiled clean): 3.2× softened to abstract's claim (confirmed absent from the full Diagon PDF); 68.9% made precise (aggregate vs 68.8% inter-agent vs 27.2% output); "open source"→"open-source". Originals comment-wrapped.
  - **Still on you:** rename title ("Beyond Task Completion" collides with cao2026) — *you'll change later*; optionally trim the 3×-repeated four-item list; optionally cite "Task Success is not Enough" (COLM 2024).
- [x] Section 4 — Methodology (reviewed; per user, all flagged points withdrawn except one nit)
  - **Design clarification (user-confirmed):** a single focal agent may act as **both** buyer and seller — there is no fixed per-agent role. So Table 1's "9×" (1 focal + 9 opponents) is correct and consistent with the rubric summing the focal's sell-side and buy-side deals. *(My earlier consistency concern was based on a wrong assumption — withdrawn.)*
  - SwapShop persona-swap concern: withdrawn per user.
  - **Applied:** `buyer-seller` → `buyer--seller` (l.145) for consistency with the rest of the paper. Inline (punctuation only).
- [~] Section 5 — Evaluation Rubric (reviewed against code; user editing)
  - ✅ User changes clean & consistent: NQ excluded from SwapShop everywhere (rubric table, sentence l.233, main table+caption, appendix); RU added everywhere.
  - ✅ **Fixed 2026-06-19:** `qwen3` bib key → `qwen3_6` (3 `\citep{qwen3_6}` were undefined; recompiled clean).
  - 🔴 **OPEN — `max_rounds` 20→100 (code) makes DO table numbers stale.** Code & paper now say ÷100, but every DO value was computed under ÷20 (RTC≈0). Under ÷100, RTC=0.44–0.72 → DO rises ~0.04–0.07 per cell (verified: Stage I Sonnet self-play 0.59 → ≈0.62). DECISION NEEDED: (A) keep ÷100 + re-score all 140 runs (deterministic, no LLM cost) and update DO in both tables + appendix; or (B) revert code to ÷20 + reword "100-turn cap" → "20-round span".
  - 🟠 **OPEN — "mean" vs weighted (l.170).** Says "mean of sub-metrics"; code is weighted (DO 0.40/0.20/0.15/0.15/0.10; CA 0.6/0.4; NQ 0.40/0.40/0.20; PP 0.7/0.3). Need to state real weights.
  - ✅ **Fixed 2026-06-19:** grammar "measures"→"measure" (l.220, inline); PE example reworded (closing at the seller's floor → seller gets no surplus → not Pareto-positive); anchoring example reworded ($32 "barely above its $30 floor" vs opening high at $72). Examples comment-wrapped; recompiled clean.
- [ ] Section 6 — Results & Discussion (incl. main results tables)
- [ ] Section 7 — Conclusion & Limitations
- [ ] Appendices (personas, judge prompts, full sub-metric tables)
- [ ] LaTeX / formatting / citation pass
