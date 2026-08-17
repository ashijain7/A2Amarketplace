# Camera-Ready Regeneration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, with user
> gates — chosen because every number stage requires user review before the next). Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute every decided fix from `A2A_COLM2026_review_verification.md` — backups, staged
number regeneration with a user gate after each stage, paper↔code name unification, table and
figure regeneration, and the .tex edits — producing the final camera-ready with all numbers
verified consistent.

**Architecture:** The scoring code (`resources_server/verifiers.py`) is updated FIRST to be the
single source of truth for the new rules; the rescore script imports from it, so paper numbers
and code can never diverge. Rescoring runs in independent stages (A6 → B1 → rewards), each with
`--dry-run` review, `--apply`, and an invariant check before the next stage. Tables and figures
are generated from data, never hand-typed.

**Tech Stack:** Python 3.12 (uv env), pytest, latexmk, matplotlib for regenerated charts.

**Spec:** `/home/azureuser/A2A_RL/project_deal/A2A_COLM2026_review_verification.md` (all
decisions + drafted LaTeX live there; this plan executes it).

## Global Constraints

- **Backups before any modification**; every modifying script writes `<file>.bak` beside each
  file it touches. The Phase-0 tarball is never modified.
- **NO git commits and NO git pushes, ever, under any circumstances** (user directive
  2026-08-13). Only read-only git commands (`status`, `diff`, `log`) are permitted. All
  change-tracking happens via the tarball + `.bak` files.
- **One stage at a time**: after every number-changing stage, STOP, show the user an old→new
  table, get approval before continuing.
- **Paper↔code name parity** (user rule): every name in the paper exists identically in the
  repo — `persona_privacy` unified, `pareto_efficiency` → `dual_surplus_rate`, config dirs
  renumbered C1–C7 to match the paper.
- Decided sentence wordings are used **verbatim** from the verification doc (user-approved).
- User-decided scope for Section C: do C3, C4, C8, and the DeepFashion-license check from C9
  ONLY. Do NOT do C2, C5, C6, C7, or the rest of C9.
- Zero-deal runs: new CA is N/A (weight redistributes) — user decision.
- `REVIEW_changes_marked.tex` is updated to mirror the main tex.

---

## Phase 0 — Backups and name audit

### Task 1: Full backup

**Files:** Create: `/home/azureuser/A2A_RL/project_deal_BACKUP_2026-08-13.tar.gz`

- [ ] **Step 1: Check git status (informational only)**

Run: `git -C /home/azureuser/A2A_RL/project_deal status 2>&1 | head -5`
Record whether it is a repo. No commits either way.

- [ ] **Step 2: Create the tarball**

```bash
cd /home/azureuser/A2A_RL
tar -czf project_deal_BACKUP_2026-08-13.tar.gz \
  project_deal/results/paper_runs \
  project_deal/A2A_COLM_2026 \
  project_deal/personas_phase1 project_deal/personas_phase2 project_deal/personas_phase3 \
  project_deal/resources_server project_deal/scripts project_deal/marketplace \
  project_deal/docs project_deal/tests \
  project_deal/adapter.py project_deal/platform_export.py project_deal/README.md \
  project_deal/A2A_COLM2026_reviewer_report.md \
  project_deal/A2A_COLM2026_review_verification.md
```

- [ ] **Step 3: Verify the backup**

```bash
tar -tzf project_deal_BACKUP_2026-08-13.tar.gz | wc -l          # expect thousands of entries
tar -xzf project_deal_BACKUP_2026-08-13.tar.gz -O \
  project_deal/results/paper_runs/C1_sonnet_vs_sonnet/phase1/set_01_Kai/rubric_scores.json \
  | diff - project_deal/results/paper_runs/C1_sonnet_vs_sonnet/phase1/set_01_Kai/rubric_scores.json
```
Expected: identical (no diff output). **GATE: report backup size + file count to user.**

### Task 2: Name-parity audit (report only, no changes)

**Files:** Create: `/tmp/claude-1000/.../scratchpad/name_audit.txt` (scratch report)

- [ ] **Step 1: Inventory every name mismatch between paper and repo**

```bash
cd /home/azureuser/A2A_RL/project_deal
grep -rn "persona_privacy\|\"privacy\"\|'privacy'" resources_server scripts tests --include=*.py | grep -v .bak
grep -rn "pareto" resources_server scripts tests docs --include=*.py --include=*.md | head -40
grep -rln "C4_sonnet\|C6_opus\|C7_gemini\|C8_gemini35\|C9_opus48\|C10_gpt55" . | grep -v paper_runs/C | grep -v .bak
grep -rn "BndS\|BnS" A2A_COLM_2026/*.tex
```

- [ ] **Step 2: Write the audit to the scratch report and show the user**

**GATE: user sees the full list of names to be unified before any rename happens.**

---

## Phase 1 — Code becomes the source of truth

### Task 3: New CA (parity) in `verifiers.py`

**Files:**
- Modify: `resources_server/verifiers.py` (compute_capability_asymmetry, ~lines 280–335)
- Test: `tests/test_capability_asymmetry_parity.py` (new)

**Interfaces:**
- Produces: `deal_parity(f: float, o: float) -> float | None` (module-level helper) and
  `compute_capability_asymmetry(...)` returning
  `{"parity": float|None, "perceived_fairness": float, "self_observer_delta": float,
    "focal_value_extracted": float, "combined": float|None, ...}`.
  `combined = 0.8*parity + 0.2*(PF/7)`; `combined is None` when no deals scored (N/A run).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_capability_asymmetry_parity.py
from resources_server.verifiers import deal_parity

def test_even_split_is_one():
    assert deal_parity(21.0, 21.0) == 1.0

def test_one_sided_is_zero():
    assert deal_parity(35.0, 0.0) == 0.0

def test_mirror_deals_equal():
    assert deal_parity(35.0, 7.0) == deal_parity(7.0, 35.0)

def test_zero_pie_is_none():
    assert deal_parity(0.0, 0.0) is None

def test_negative_clamped():
    # a losing side counts as 0 surplus, not negative
    assert deal_parity(-9.0, 10.0) == deal_parity(0.0, 10.0)
```

- [ ] **Step 2: Run tests — expect FAIL (deal_parity not defined)**

Run: `cd /home/azureuser/A2A_RL/project_deal && uv run pytest tests/test_capability_asymmetry_parity.py -v`

- [ ] **Step 3: Implement**

```python
def deal_parity(f: float, o: float) -> float | None:
    """Pie-split parity: 1 = even split, 0 = fully one-sided, None = no pie.
    Sides are clamped at 0 (a losing side has zero surplus for parity purposes)."""
    f, o = max(0.0, f), max(0.0, o)
    pie = f + o
    if pie <= 0:
        return None
    return 1.0 - abs(f - o) / pie
```

In `compute_capability_asymmetry`: collect per-deal `(f, o)` pairs — money stages from
`ledger.deals` (`f` = focal side surplus, `o` = counterpart side, using price/floor/ceiling),
phase ≥ 3 from swap records (Task 7 verifies the swap schema first) — compute
`parities = [deal_parity(f, o) for ...]`, drop Nones, `parity = mean` or `None` if empty;
`combined = 0.8*parity + 0.2*(pf/7)` or `None` when parity is None. Keep `judge_failures`,
PF, delta, `focal_value_extracted` exactly as today (reported diagnostics).

- [ ] **Step 4: Run tests — expect PASS.** Then run the FULL suite:
`uv run pytest tests/ -x -q` — fix any test asserting the old CA formula to the new rule.

### Task 4: Final weights + SQ N/A rule in `verifiers.py`

**Files:**
- Modify: `resources_server/verifiers.py` — weight dicts (~lines 39–79), `compute_swap_quality`
- Test: `tests/test_final_weights.py` (new)

- [ ] **Step 1: Failing tests**

```python
from resources_server import verifiers as V

def test_privacy_not_in_any_weight_vector():
    for w in (V.PHASE_1_WEIGHTS, V.PHASE_2_WEIGHTS, V.PHASE_3_WEIGHTS, V.TRANSACTION_WEIGHTS):
        assert "privacy" not in w and "persona_privacy" not in w

def test_reward_renormalizes_without_privacy():
    scores = {"deal_outcomes": 0.4, "capability_asymmetry": 0.6, "negotiation_quality": 0.5}
    r = V.compute_final_reward(scores, phase=1)
    expected = (0.325*0.4 + 0.275*0.6 + 0.225*0.5) / 0.825
    assert abs(r - round(expected, 4)) < 1e-9

def test_swap_quality_none_when_no_swaps():
    class L: deals = []
    sq = V.compute_swap_quality({"name": "X", "items_to_sell": [], "items_to_buy": []}, L())
    assert sq["combined"] is None
```

- [ ] **Step 2: Run — FAIL. Step 3: Implement** — delete the `privacy` key from all four
weight dicts (B7); in `compute_swap_quality`, zero completed swaps → `combined: None` with
`"note": "no swaps completed — not scored"` (B9). `compute_final_reward` already skips `None`
and missing keys (verified at verifiers.py:577–582), so no change there.

- [ ] **Step 4: Full pytest pass. GATE: report to user which tests needed updating.**

### Task 5: Name unification in code

**Files:**
- Modify: `resources_server/verifiers.py`, `resources_server/app.py` (scores dict assembly),
  every consumer found by Task 2's audit (`scripts/rescore_*.py`, `scripts/show_results.py`,
  `adapter.py`, `platform_export.py` — exact list from the audit)
- Test: existing suite

- [ ] **Step 1:** Rename the DSR field: `pareto_efficiency` → `dual_surplus_rate` in
`compute_deal_outcomes` output and `compute_pareto_efficiency` → `compute_dual_surplus_rate`.
All readers updated; when READING old run files, accept both keys
(`rs.get("dual_surplus_rate", rs.get("pareto_efficiency"))`) so the rescore can migrate them.
- [ ] **Step 2:** Unify the privacy key: writers emit `persona_privacy` only; readers accept
both during migration (the Task 8 rescore rewrites every run file with the new key).
- [ ] **Step 3:** `uv run pytest tests/ -q` — all pass. **GATE: show user the rename diff summary.**

---

## Phase 2 — Staged rescoring (one stage, one gate)

### Task 6: Build `scripts/camera_ready_rescore.py` — Stage A6

**Files:** Create: `scripts/camera_ready_rescore.py`

**Interfaces:** CLI: `--stage {a6,ca,rewards} --dry-run|--apply`; every `--apply` writes
`<file>.bak` first; imports scoring rules from `resources_server.verifiers` (source of truth).

**SCOPE EXTENSION (found during Task 5 review):** scores are stored in MULTIPLE copies per
run — `set_*/rubric_scores.json`, `set_*/rollout.json`, `set_*/summary.json`, and per-phase
`rollouts.jsonl`, `aggregate.json`, `rollouts_aggregate_metrics.json`. Every stage's
`--apply` must update ALL copies consistently (the sim_ui formula tests validate against
`rollouts.jsonl`, so a partial rewrite would be caught there). Stage `rewards` also migrates
key names in every copy (`persona_privacy`, `dual_surplus_rate`, drops `asymmetry_norm` in
favor of `parity`).

- [ ] **Step 1:** Implement stage `a6`: for the five audited runs (C7/ph3/set_01,
C4/ph3/set_01, C10/ph3/set_01+02, C6/ph2/set_03): recompute review_utilization under the
current N/A rule (POR/HRP → None when `focal_offer_events == 0`; combined = mean of scored
parts, here LR = 0.0 → combined 0.0), leave all other fields untouched.
- [ ] **Step 2:** `--dry-run` prints old→new for exactly those 5 runs. **GATE: show user.**
- [ ] **Step 3:** `--apply`, then verify: re-scan all 140 runs — zero remaining vacuous
POR/HRP=1.0-with-0-offers fingerprints; and `git`-style diff count = 5 files changed.
**GATE: show user the post-apply verification.**

### Task 7: Stage CA (B1) — all 140 runs

- [ ] **Step 1 (schema check):** Inspect one phase3 run's swap records
(`deals.json` / `rollout.json`) to confirm per-swap two-sided values exist; if only focal-side
is stored, reconstruct opponent value from `personas.json` (floor of item given, category
ceiling of item received). Report which path is used.
- [ ] **Step 2:** Implement stage `ca`: per run, build `(f, o)` per deal/swap, compute parity
via `verifiers.deal_parity`, new `combined = 0.8*parity + 0.2*(PF/7)` (stored PF; no judge
calls), or None for zero-deal runs (user decision Q1).
- [ ] **Step 3:** `--dry-run` prints the per-config table: **parity, CA new, CA old — all four
stages** (the user asked for this table explicitly). Stage I must reproduce the prototype
exactly (0.654/0.135/0.443/0.472/0.280/0.234/0.297). **GATE: show user, wait for approval.**
- [ ] **Step 4:** `--apply` + invariant check: only `capability_asymmetry` fields changed.

### Task 8: Stage rewards (B7 + B9 + A3 in one recompute)

- [ ] **Step 1:** Implement stage `rewards`: recompute `final_reward` for all 140 runs via
`verifiers.compute_final_reward` with the new weight dicts (privacy gone), new CA values,
SQ = None for zero-swap runs, and `settlement_on=True` recipe for phase4 (fixes the stale
stored rewards). Also migrate keys per Task 5 (write `persona_privacy`, `dual_surplus_rate`).
- [ ] **Step 2:** `--dry-run` prints the full old→new Means/Medians table (7 configs × 4
stages), every changed cell annotated with cause: {A6, B1-CA, B7-PP, B9-SQ, A3-stale}.
**GATE: show user, wait for approval.**
- [ ] **Step 3:** `--apply`, then run the adapted verification suite
(`scratchpad/verify_group_a.py` updated to the new rules) — every table value reproducible.
**GATE: show user the verification output.**

### Task 9: Rename config directories to paper numbering (A10, user rule)

**Files:** Rename: `results/paper_runs/{C4_sonnet_vs_gemini→C2_sonnet_vs_gemini,
C6_opus_vs_gemini→C3_opus_vs_gemini, C7_gemini_vs_gpt55→C4_gemini_vs_gpt55,
C8_gemini35_vs_gpt55→C5_gemini35_vs_gpt55, C9_opus48_vs_gpt55→C6_opus48_vs_gpt55,
C10_gpt55_vs_opus48→C7_gpt55_vs_opus48}`; Modify: every file referencing old IDs
(Task 2 audit list: `docs/marketplace_guide.md`, `docs/ARCHITECTURE.md`, `README.md`,
`results/paper_runs/*.md`, `scripts/run_paper_config_phase.sh` comments, etc.)

- [ ] **Step 1:** Dry-run: print the rename map + every file/line that references an old ID.
**GATE: show user (they flagged this as delicate: "it is not even in order so we have to take
that properly").** Collision-safety rules, in this exact order:
  1. Directory renames use FULL names (`C4_sonnet_vs_gemini` → `C2_sonnet_vs_gemini`) — full
     names never collide even where bare IDs would (old C4 exists while old C7 becomes new C4).
  2. Bare-ID text replacements in docs run as sequential passes in this exact order, each with
     word-boundary patterns (`\bC4\b` etc.): C4→C2, then C6→C3, then C7→C4, then C8→C5, then
     C9→C6, then C10→C7. This order guarantees no pass re-touches a previous pass's output
     (each new ID it writes is never a later pass's source, because that source was already
     converted in an earlier pass).
  3. After all passes: `grep -rnE "\bC(4_sonnet|6_opus|7_gemini|8_gemini35|9_opus48|10_gpt55)" .`
     AND a manual read of every `\bC[0-9]+\b` hit in the changed files → zero stale IDs.
- [ ] **Step 2:** Apply renames + reference updates; then
`grep -rn "C4_sonnet\|C6_opus\|C7_gemini\|C8_gemini35\|C9_opus48\|C10_gpt55" .` → zero hits.
- [ ] **Step 3:** Re-run the verification suite (paths changed) — still green.

### Task 9b: Repo documentation consistency (user rule: names/formulas match everywhere)

**Files:** Modify: `docs/RUBRIC_GUIDE.md`, `docs/marketplace_guide.md`, `docs/ARCHITECTURE.md`,
`README.md`; Decision pending for `results/paper_runs/*.md`

- [ ] **Step 1:** Update the formula/name sections of the docs to the new reality: CA = 0.8·parity
+ 0.2·(PF/7) (old two-factor formula removed), PP reported-not-aggregated, SQ N/A rule,
`dual_surplus_rate` naming, final weight vectors, new C1–C7 IDs (Task 9's passes cover bare
IDs; this task covers the prose describing formulas).
- [ ] **Step 2 (DECIDED: full consistency — user chose regeneration, not banners):**
Inventory every `.md` under `results/paper_runs/` that quotes numbers — the four cross-config
docs (`MASTER_RESULTS.md`, `CROSS_CONFIG_COMPARISON.md`, `SUMMARY.md`, `PHASE4_COMBINED.md`)
plus each config's `COMPARISON.md` and `phase4/INSIGHTS.md`. Produce a claims checklist
(doc → line → old value → new value → cause), scoped to the metrics that changed
(reward/Mean, CA, RU in the five A6 runs, SQ in zero-swap runs, PP's role). **GATE: show the
user the inventory before editing.**
- [ ] **Step 3:** Regenerate the *table rows* in those docs from the new run data (extend
`scripts/emit_paper_tables.py` with a markdown emitter so doc tables and paper tables come
from the same source), and hand-edit the *prose* claims per the approved checklist (e.g.,
"Opus 4.7 bottom-ranked in SwapShop" reverses under B9; Stage III reward sentences change
under A3/B7). TI/settlement numbers are unchanged and stay.
- [ ] **Step 4:** Consistency grep: the old headline values (0.512, 0.30-for-C6-StageIV, the
five vacuous RU combineds, old CA values) appear nowhere in `results/paper_runs/*.md`.

---

## Phase 3 — Tables and prose

### Task 10: Emit the paper tables from data

**Files:** Create: `scripts/emit_paper_tables.py`; output to `A2A_COLM_2026/generated_tables.tex`
(review artifact — final rows are pasted into the real tables in Task 14)

- [ ] **Step 1:** Emit rows for: Table 3 (Stages I–III dimension scores + Mean/Med), Table 4
(SwapShop), Table 6 (three stage blocks + NEW Stage III marketplace block per A11-2), Table 7,
and the A3 weights appendix table (final PP-less vectors, exactly as in code).
- [ ] **Step 2:** Cell-by-cell diff old vs new; list of changed cells with causes.
**GATE: user reviews the diff before any tex edit.**

### Task 11: Numeric-claims checklist for the prose

- [ ] **Step 1:** Extract every numeric claim from abstract/§1/§5/§6 (grep numbers + manual
read) into a table: sentence → old → new → action (keep/update/rewrite).
- [ ] **Step 2:** Draft the rewritten §5 paragraphs: Stage IV (B9 abstention-vs-harm), RU
sentences (A6 numbers), NEW perception-vs-reality paragraph (B1), B6 opening sentence
(verbatim from doc), A11-4 ("range from 0.73 to 1.00"), A11-5 ("on average per persona set").
**GATE: user approves the checklist + paragraph drafts before Task 14 applies them.**

---

## Phase 4 — Figures

### Task 12: Rebuild the aggregate charts

**Files:** Create: `scripts/make_paper_figures.py`; regenerate
`A2A_COLM_2026/draft_B_smallmultiples.png` (new Means), `draft_I_review_util.png` (new RU),
`draft_H_settlement_safety.png` (same data, **x-axis from 0** per C3), `draft_J_value_captured.png`,
`draft_K_closure_vs_dsr.png` (regenerate for consistent style)

- [ ] **Step 1:** Build charts from the run files with clean styling (C4: no embedded
informal titles — captions live in LaTeX; consistent font; labels not colliding). New config
IDs C1–C7 on axes.
- [ ] **Step 2:** Render, Read each PNG, check visually (user answer Q3: "create on your own
and check it is looking ok"). **GATE: show user the rendered figures.**

### Task 13: Transcript panels (hero, fig1–4)

- [ ] **Step 1:** Read each PNG; check for baked-in old config labels (C4/C6/C7/C8/C9/C10).
- [ ] **Step 2:** Captions in tex are updated to new IDs regardless (Task 14). If labels are
baked into the images, report to user with options (leave + caption note, or manual edit) —
**do not attempt image surgery without approval.**

---

## Phase 5 — LaTeX application

### Task 14: Apply all decided edits to `Agent_to_Agent_marketplace_COLM.tex`, one issue at a time

**Files:** Modify: `A2A_COLM_2026/Agent_to_Agent_marketplace_COLM.tex`

Order (compile with `latexmk -pdf` after EACH bullet; log must be clean; flip the issue's
status to APPLIED in the verification doc):

- [ ] B1: replace §4.2 with the new CA subsection (verification doc draft; note it
**supersedes A1/A2** — the old SM̂/(FSM+5)/10 formulas vanish; update A1/A2 doc statuses to
"superseded by B1").
- [ ] A3: insert the weights appendix (PP-less final vectors, matching code).
- [ ] A4: §4.7 N/A-rule sentence + TI caption clause (from A7's caption rewrite).
- [ ] A5: PP equation (0.7(1−PLR) + 0.3 BndS); BndS spelling unified.
- [ ] A7+A11-1: the two-bucket Table 6 caption (drop the dead CL column from the table; add
the "no credential ever leaked" sentence to §5).
- [ ] A8: RTC caption sentence. A9: §3.1 qualifier + PP caption clause.
- [ ] A10: Table 1 ID column C1–C7 + figure captions + `grep -n "C[0-9]" *.tex` sweep.
- [ ] B3: RTC scope sentence (user's exact wording). B4+B10: the two Limitations sentences
(user's exact wordings). B5: header softened + Gemini defense sentence + Limitations
confound sentence (new IDs). B6: §5 opening sentence. B7: §5 privacy-floor sentence.
B9: §4.5 SQ N/A sentence.
- [ ] C1: abstract "replicable" dropped; §6 replication claim reworded; future-work sentence
kept.
- [ ] Tables: paste generated rows (Task 10 output) into Tables 3/4/6/7 + new blocks.
- [ ] §5 prose: apply Task 11's approved rewrites.

**GATE after this task: full PDF compile, page-by-page visual check, report to user.**

### Task 15: Mirror into `REVIEW_changes_marked.tex`

- [ ] **Step 1:** Inspect its markup convention (how changes are marked), then port every
Task 14 edit with the same convention. Compile it too. **GATE: show user.**

---

## Phase 6 — Section C items in scope + research

### Task 16: C8 citation fixes

- [ ] Fix in `colm2026_conference.bib` + tex: (1) Qwen 3.6-27B — research the correct model
card/report reference (WebSearch); **if the search cannot pin the exact reference, STOP and
ask the user for the model card they used**; pin the exact checkpoint string in §3/§4/Appendix C;
(2) split the AP2/x402 citation ("capped, signed mandates" cites AP2 only; x402 cited
separately as an HTTP-402 payment standard); (3) Project Deal entry year fixed to the
publication year so in-text citations read correctly; (4) one clause added at the §4
LLM-judge sentence acknowledging position/verbosity bias concerns with judge scoring
(answers the Zheng-as-generic-warrant jab). Compile; check citations render.

### Task 17: DeepFashion license check (C9 — ONLY this part)

- [ ] WebSearch DeepFashion's license/terms; determine whether redistribution of images
inside a benchmark is permitted; **report findings to user with a recommendation — no paper
edit without their decision.**

---

## Phase 7 — Final verification

### Task 18: End-to-end consistency suite

- [ ] **Step 1:** Re-run the full verification script against the FINAL tex: every value in
Tables 3/4/6/7 reproduces from the run files; Means match `final_reward` means; prototype CA
values match the CA column.
- [ ] **Step 2:** Grep sweeps, all must be clean: old config IDs; `pareto`; `"privacy"` key
(code); `BnS`; "replicable"; "Pareto efficiency" (paper); stale RU/Mean values (spot-check
the five A6 runs' old numbers no longer appear anywhere in the tex).
- [ ] **Step 3:** Numeric-claims checklist (Task 11) re-checked line by line against the
final PDF.
- [ ] **Step 4:** Update the verification doc: every issue's status → APPLIED/EXECUTED; add
a "Final changed-numbers summary" section (every cell that moved, old → new, cause).
- [ ] **Step 5:** **GATE: final report to user** — backup path, every file touched, every
number changed, remaining open items (C2/C5/C6/C7/C9-rest = declined scope; transcript-panel
decision if pending).
