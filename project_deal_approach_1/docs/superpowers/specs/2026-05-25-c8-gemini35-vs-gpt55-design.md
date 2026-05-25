# C8 — Gemini 3.5 Flash vs GPT-5.5: Design

**Date:** 2026-05-25
**Author:** Ashi (with Claude)
**Status:** Draft — pending user review

---

## 1. Background

The paper experiment in `results/paper_runs/` currently has four configs:

| Config | Focal | Opponents |
|---|---|---|
| C1 | Sonnet 4.5 | 9× Sonnet 4.5 |
| C4 | Sonnet 4.5 | 9× Gemini 3.1 Pro |
| C6 | Opus 4.7 | 9× Gemini 3.1 Pro |
| C7 | Gemini 3.1 Pro | 9× GPT-5.5 |

Paper claim #4 (`CROSS_CONFIG_COMPARISON.md`): **Gemini 3.1 Pro ignored the
Phase 2 lookup tool 0.0 times per rollout**, despite being told it was free.
This was the most behaviorally distinctive finding in C7. The question this
spec resolves: does a newer-generation Gemini still ignore the tool?

`google/gemini-3.5-pro` is not yet on OpenRouter (verified 2026-05-25). The
3.5-family slug available is `google/gemini-3.5-flash`. We will use Flash and
accept the tier confound in the methodology caveats.

## 2. Goals

1. Add a fifth config — **C8: Gemini 3.5 Flash focal vs 9× GPT-5.5 opponents** —
   to the paper experiment matrix.
2. Reuse the existing pipeline (`run_paper_config_phase.sh`,
   `extract_per_set_channels.py`, archive scripts) without re-implementing it.
3. Produce writeups (3 INSIGHTS + 1 COMPARISON + rewritten CROSS_CONFIG) that
   match the existing depth and voice.

## 3. Non-goals

- Re-running C1/C4/C6/C7. They stay frozen.
- Retrofitting any existing writeup to a different style.
- Adding `gemini-3.5-pro` when it ships — out of scope until the slug exists.
- Approach 2 (peer-LLM simulation). Out of scope.
- A Haiku 4.5 config (C2/C3 in the original plan) — separately discussed; not
  in this spec.

## 4. The C8 config — definition

| Field | Value |
|---|---|
| Config name (internal) | `focal_G35_vs_X` |
| Folder name | `C8_gemini35_vs_gpt55` |
| Focal model | `google/gemini-3.5-flash` |
| Opponents | 9× `openai/gpt-5.5` |
| Personas | 5 sets (same as all other configs), seed=42 |
| Phases | 1, 2, 3 |
| Rollouts | 15 (5 sets × 3 phases) |
| Expected spend | $15–25 (Flash is cheaper per-token than 3.1 Pro) |

## 5. Code changes — four small patches

The pipeline is already config-driven. Adding C8 follows the C7 recipe.

### 5.1 `marketplace/config.py`

After line 40 (`GPT5_5_MODEL = ...`), add:

```python
GEMINI_FLASH_MODEL = "google/gemini-3.5-flash"
```

### 5.2 `resources_server/model_config.py`

Add the new constant after line 9:

```python
GEMINI_FLASH = mp_config.GEMINI_FLASH_MODEL  # "google/gemini-3.5-flash"
```

Append `"focal_G35_vs_X"` to `CONFIG_NAMES` (line 11-22).

Add entry to `_CONFIGS` (line 24-35):

```python
"focal_G35_vs_X": {"focal_model": GEMINI_FLASH, "opponents_model": GPT5_5},
```

### 5.3 `scripts/run_paper_config_phase.sh`

In the `case "$CONFIG" in` block (lines 36-44), add a new branch before the
`*) echo "ERROR"` catch-all:

```bash
focal_G35_vs_X) FOCAL_MODEL="google/gemini-3.5-flash"; CONFIG_DIR="C8_gemini35_vs_gpt55" ;;
```

### 5.4 Task files

`tasks/generate_tasks.py` already iterates `CONFIG_NAMES` from
`resources_server.model_config` and supports `--config-filter`. Once 5.2 is
in place, generate the three C8 task files:

```bash
python tasks/generate_tasks.py --phase 1 --config-filter focal_G35_vs_X
python tasks/generate_tasks.py --phase 2 --config-filter focal_G35_vs_X
python tasks/generate_tasks.py --phase 3 --config-filter focal_G35_vs_X
```

Verified diff between configs: only the `metadata.task_id` and
`metadata.config_name` change. Personas, prompts, tools, seed are identical.

Output files:
- `tasks/paper_runs/focal_G35_vs_X_phase1.jsonl`
- `tasks/paper_runs/focal_G35_vs_X_phase2.jsonl`
- `tasks/paper_runs/focal_G35_vs_X_phase3.jsonl`

## 6. Pre-flight checks

Before paying for 15 rollouts:

1. **Slug verification.** A 1-token chat completion to `google/gemini-3.5-flash`
   through OpenRouter. If 4xx/5xx, stop — the slug name is wrong.
2. **Tool-calling sanity.** Verify the slug accepts the focal-agent tool
   schema (Gemini families have varied here historically — the `customtools`
   variant exists specifically because the default has issues).
3. **Smoke test.** One rollout via `ng_collect_rollouts +limit=1`, Phase 1,
   set_01 only. Cost ~$0.30. Confirms no `choices=None` regressions like C7
   P2 hit with GPT-5.5, and that `marketplace/llm.py`'s retry handles any new
   provider-side hiccups.

Smoke test passes iff:
- `rollouts.jsonl` has exactly 1 record with non-null `reward`
- The transcript shows at least 3 valid tool calls from the focal
- The rollout exited within `MAX_TURNS = 120`

## 7. Run sequence

Sequential, one phase at a time. The existing script restarts `ng_run`
between phases automatically.

```bash
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 1
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 2
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 3
```

Each phase writes to `results/paper_runs/C8_gemini35_vs_gpt55/phase{N}/` and
appends a row to `data/credit_log.jsonl`.

The script auto-generates an INSIGHTS.md stub. The narrative analysis is
written after the run completes — see Section 8.

## 8. Writeup deliverables

Five documents, matching existing C7 depth and voice. Layman-friendly
vocabulary, full metric tables, per-persona stories, methodology caveats.

| File | Target size | Mirrors |
|---|---:|---|
| `C8_gemini35_vs_gpt55/phase1/INSIGHTS.md` | ~250 lines | `C7_*/phase1/INSIGHTS.md` |
| `C8_*/phase2/INSIGHTS.md` | ~250 lines | C7 phase2 |
| `C8_*/phase3/INSIGHTS.md` | ~250 lines | C7 phase3 |
| `C8_*/COMPARISON.md` | ~250 lines | `C7_*/COMPARISON.md` |
| `CROSS_CONFIG_COMPARISON.md` (rewrite in place) | ~600 lines | adds 5th column |

### 8.1 INSIGHTS.md structure (per phase)

Same sections as C7 INSIGHTS:

1. Aggregate header (focal, opponents, rollouts, spend, wall time)
2. Per-rollout summary table (set / focal / reward / deals / events)
3. **The 5 things that matter most** — narrative bullets
4. Master metric table (reward, closure_rate, normalized_closure,
   pareto_efficiency, focal_value_extracted, self_observer_delta,
   boundary_score, deadlock_handling, review_utilization,
   swap_quality where applicable)
5. Per-persona breakdown (Kai/Rosa, Rex, Marcus/Zara, Omar/Buck, Taj)
6. Key narrative sections (tool usage in P2, mutual wins in P3, etc.)
7. Notable rollouts (quoted transcript moments)
8. What stayed constant / what changed
9. Methodology caveats

Author by reading `rollouts.jsonl` + `aggregate.json` + per-set channel
transcripts in `phase{N}/set_NN_<focal>/`.

### 8.2 COMPARISON.md structure

Same sections as `C7_gemini_vs_gpt55/COMPARISON.md`:

1. What this document does
2. The C8 story in three phases (one paragraph per phase)
3. The 5 things that matter most across phases
4. Master table (reward, closure, normalized closure, Pareto, value
   extracted, mean Δ, privacy, mutual wins, cost — per phase)
5. Why phase transitions happened (the measurement-vs-reality breakdown)
6. Closure trajectory analysis
7. Per-persona phase progression
8. What stayed constant in C8 / what changed dramatically
9. C8 vs the other configs (1-row contribution to the 5-config table)
10. Self-perception story across phases
11. Methodology caveats
12. Files manifest
13. Italic summary paragraph

### 8.3 CROSS_CONFIG_COMPARISON.md rewrite

Replace every 4-column table with a 5-column table (C1, C4, C6, C7, C8).
Sections to revise:

- "What are the four configurations?" → **five**
- "The 5 things the paper claims" → reconsider claim #4 in light of C8's
  lookup tool behavior. If C8 still ignores tools, claim hardens. If C8
  engages, claim becomes "Gemini 3.1 ignored / 3.5 fixed it."
- "The headline matrix — mean reward across all 12 cells" → **15 cells**
- "The key comparison — why Opus failed where Sonnet didn't" → unchanged,
  but the table gains C8 columns for completeness.
- Rubric-by-rubric analysis (all 9 sub-sections) → 5-column tables
- Per-persona heatmap → add 3 columns (C8 P1, C8 P2, C8 P3)
- Sell-rate trajectories → 5 rows
- Cost comparison → 5 rows
- The thesis paragraph → may need a sentence on tier/generation effect

### 8.4 New methodology caveat (must appear in COMPARISON.md and CROSS_CONFIG)

> **Gemini 3.5 Flash vs Gemini 3.1 Pro mixes generation with tier.** C7 used
> the Pro variant of Gemini 3.1; C8 uses the Flash variant of Gemini 3.5
> because Pro is not yet available on OpenRouter at 3.5. Any delta between
> C7 and C8 conflates two changes (generation + tier). Until `gemini-3.5-pro`
> ships, treat C7→C8 comparisons as directional, not isolated.

## 9. Output layout (final)

```
results/paper_runs/
├── C1_sonnet_vs_sonnet/                  (unchanged)
├── C4_sonnet_vs_gemini/                  (unchanged)
├── C6_opus_vs_gemini/                    (unchanged)
├── C7_gemini_vs_gpt55/                   (unchanged)
├── C8_gemini35_vs_gpt55/                 (NEW)
│   ├── phase1/
│   │   ├── INSIGHTS.md
│   │   ├── aggregate.json
│   │   ├── rollouts.jsonl
│   │   ├── rollouts_aggregate_metrics.json
│   │   ├── rollouts_materialized_inputs.jsonl
│   │   ├── rollout.log
│   │   ├── set_01_Kai/    (channel.jsonl, deals.json, summary.json)
│   │   ├── set_02_Rex/
│   │   ├── set_03_Marcus/
│   │   ├── set_04_Omar/
│   │   └── set_05_Taj/
│   ├── phase2/                            (same shape, P2 personas)
│   ├── phase3/                            (same shape, P3 personas)
│   └── COMPARISON.md
└── CROSS_CONFIG_COMPARISON.md            (REWRITTEN to 5 configs)
```

## 10. Error handling

Inherits everything `run_paper_config_phase.sh` already does (credit floor
check, ng_run restart, archive, aggregate, credit log). Three model-specific
guards:

- **Provider returns `choices=None`** — `marketplace/llm.py`'s retry +
  graceful fallback (patched mid-C7) should cover this. If it triggers
  frequently, log in `phase{N}/rollout.log` and surface in the INSIGHTS
  methodology caveats.
- **Tool-call schema rejection** — Gemini 3.5 Flash may not accept the same
  tool schema as Gemini 3.1 Pro. The smoke test in §6 catches this before
  spending on 15 rollouts.
- **Phase 3 vision payload** — Phase 3 personas use DeepFashion image inputs.
  Confirm Gemini 3.5 Flash supports the image-in-prompt format used by other
  configs. If not, document in caveats and accept the phase as text-only.

## 11. Testing & validation

Before declaring C8 done:

- All 15 rollouts have non-null `reward` in `rollouts.jsonl`
- `aggregate.json` exists in each phase folder with `mean_reward` populated
- 5 per-set folders exist per phase (Kai/Rex/Marcus/Omar/Taj for P1-2,
  Kai/Rex/Zara/Buck/Taj for P3)
- Existing test suite passes: `pytest tests/` (no changes to test files
  expected since C8 reuses code paths)
- The 5-config rewrite of `CROSS_CONFIG_COMPARISON.md` has internal
  consistency: per-cell numbers cited in narrative match the tables

## 12. Open questions / decisions made

| Question | Decision |
|---|---|
| Run all 3 phases or just P2? | All 3 phases — full replica |
| Cross-config doc handling | Rewrite in place to 5 configs × 3 phases |
| Layman-English depth | Match existing C1/C4/C6/C7 voice (already plain) |
| Pro vs Flash slug | Use Flash; accept tier confound in caveats |
| Config naming | `focal_G35_vs_X` / `C8_gemini35_vs_gpt55` |

## 13. Risks

- **Slug doesn't accept tool calls.** Mitigation: smoke test in §6.
- **Flash too weak to be informative.** Possible. If P1 closure is <0.30 or
  rewards cluster at the floor, the writeup reports that honestly — a negative
  result is still publishable, and reinforces the "more capability ≠ better
  marketplace skill" thesis from a different angle.
- **Provider intermittent failures (`choices=None`).** Same risk as C7 P2.
  `marketplace/llm.py` already has retry + fallback.
- **Phase 3 image inputs unsupported.** Documented as a possible degraded
  case; acceptable to run P3 text-only if forced.

## 14. Scope check (self-review)

- This spec is one config (C8) + writeup rewrite. Single implementation plan.
- All sections are concrete (specific files, specific lines, specific
  shell invocations).
- No "TBD" or placeholder content.
- The tier-confound caveat is explicit and recurs in every public-facing
  output (COMPARISON, CROSS_CONFIG).
