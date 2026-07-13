# sim_ui redesign — design spec (2026-07-13)

Status: **DESIGN LOCKED**, build not started.
Scope: `project_deal/sim_ui/` (+ `logic.py` exporter, `adapter.py` scammer flag). The RLEaaS platform
repo is NOT touched.

---

## 0. Context

The cached + live marketplace UI (`sim_ui/web/`) is embedded in RLEaaS via the container's runtime
proxy. It works. This spec covers a round of UI feedback plus **two data bugs found while analysing
that feedback**, both of which must be fixed before any of the display work is meaningful.

### The frozen surface (RLEaaS glue — DO NOT TOUCH)

| loc | what | why |
|---|---|---|
| `web/app.js` `new URL("gradio", document.baseURI)` | Gradio connect URL | inside the iframe `location.origin` is the PLATFORM, not us |
| `web/index.html` `<script src="app.js">`, `app.js` `fetch('episodes.json')` | **relative** paths | the platform injects `<base href>`; an absolute `/…` 404s |
| `web/index.html` `@gradio/client` CDN import → `window.__GradioClient` | live transport | |
| `serve.py::_advertise_public_gradio_root` | `/gradio/config` `root` rewrite from `X-Forwarded-*` | without it live dies inside the iframe |
| `serve.py::build_app` route order | Gradio → middleware → `/api/*` → **StaticFiles("/") LAST** | the `/` mount is a catch-all |
| `serve.py::_port()` | `$PORT` ‖ `A2A_UI_PORT` ‖ 8000 | the platform injects `$PORT` |
| `run_api.py`, `platform_export.py`, `adapter.py` push hook | reward doors | |
| `resources_server/verifiers.py` | **rubric scoring** | standing do-not-modify rule |

**One deliberate exception:** the `/run_live` Gradio input list is positional and pinned between
`serve.py` and `app.js`. Task 8 appends a 7th input (`scammer`). It must be **appended at the end**
and both sides changed **in lockstep**. Nothing else about the transport changes.

---

## 1. Two data bugs (must land first)

### Bug A — mode classifier drops/corrupts 3 episodes

`logic.classify_mode` (`sim_ui/ui/logic.py:51`) says:

```python
if rollout.get("settlement_records"):   # truthy!
    return "transaction"
```

When a transaction run closes **zero focal deals** there is no payment room, so `settlement_records`
is an **empty list** — which is falsy. Those runs are labelled `review`, collide with the genuine
review run for the same (config, set), and **overwrite it** (phase4 is globbed after phase2).

Affected: `set_01` of `focal_G35_vs_X`, `focal_O_vs_X`, `focal_X_vs_O48`. Effect today: 3 transaction
episodes missing from the catalog, and 3 episodes labelled "Review / set_01" in the UI are actually
the **transaction** rollouts.

Signals were enumerated across all 28 files:

| signal | verdict |
|---|---|
| `settlement_records` truthy | ❌ fails on the 3 zero-deal runs |
| tool count (7 vs 14) | ❌ `C7/phase4` sets 03-05 are transaction runs with only 7 tools |
| `settlement_balances` key present | ❌ C9/C10 emit it (as `null`) in *every* phase |
| **`isinstance(settlement_records, list)`** | ✅ **holds for all 140** |

Non-transaction runs have the key **absent** (C1/C4/C6/C7/C8) or present-with-`null` (C9/C10) — either
way `isinstance(..., list)` is False. Transaction runs always have a list, possibly empty.

**Fix:**
```python
def classify_mode(rollout: dict) -> str:
    if isinstance(rollout.get("settlement_records"), list):
        return "transaction"
    phase = str((rollout.get("metadata") or {}).get("phase"))
    return {"3": "swap", "2": "review"}.get(phase, "market")
```

### Bug B — the privacy rubric is silently dropped from 15 episodes

Older rollouts key the rubric `privacy`; newer ones key it `persona_privacy`. `app.js` only knows
`persona_privacy` (`app.js:2`, `:12-16`). For the 15 old-vintage episodes the privacy bar never
renders, its weight is renormalized away, and the displayed contributions **do not sum to the hero
reward**. Invisible today only because there are no denominators. Task 5 would expose it.

**Fix:** normalize `privacy` → `persona_privacy` in `_rollout_to_episode`'s rubric dict comprehension
(`logic.py:314`). One key, one name, everywhere downstream.

### Consequence

With both fixed: **140 of 140 runs load** (35 per stage), every (stage × config × set) cell is
populated, and there is **nothing to grey out**.

⇒ **The "grey out unavailable persona sets" item is DROPPED (YAGNI).** It was requested because the
dropdown could land on an empty state — but that empty state was the classifier bug, not missing data.
`ddHTML` already accepts a `disabled` flag if a future partial dataset ever needs it; wiring it now
would be dead code with no entry to exercise it.

---

## 2. The salvaged run (user decision: option B)

`Review · focal_S_vs_S · set_01` is absent from `results/paper_runs/C1_sonnet_vs_sonnet/phase2/rollouts.jsonl`
(4 lines). It exists at `.../phase2/set_01_Kai/rollout.json`, stamped:

> `"salvage_note": "Original rollout was killed mid-flight at event 328+; truncated to first 100 events and rubrics re-scored."`

**User decision: load it as a normal run.** It is the only salvage in the corpus. Accepted caveat: it
is a 100-event crash-truncated transcript against peers of 124–200 events, so Sonnet-vs-Sonnet's
Review numbers sit lower than they otherwise would. Consistent and simple; no special-casing.

`build_catalog()` gains one extra source: the salvaged `rollout.json`. Note it carries no
`responses_create_params` — the classifier above does not need it.

⚠️ **Ignore `rollouts_truncated.jsonl`.** It is a separate 100-event-cap re-scoring experiment whose
numbers disagree with the canonical file (e.g. set_03: 0.6207 vs 0.5655). It exists in only some
folders. It is never a data source.

---

## 3. Computation goes in Python, not JavaScript

Two hard reasons, one soft:

1. **Redaction.** Persona `private{}` and `payment_profile{}` hold real PINs, CVVs, card numbers, UPI
   ids. Only **key names** may reach the browser. `episodes.json` ships in a **public** GitHub repo —
   redacting in JS would leave the real values sitting in the payload.
2. **Testability.** The leaderboard aggregation is unit-testable in pytest; the same logic in `app.js`
   would not be (there is no JS test framework here — verification is `node --check` plus a headless
   DOM assertion).
3. Numbers are computed once at build time instead of on every page load.

⇒ `episodes.json` gains two new top-level blocks, **`personaSets`** and **`leaderboard`**, both
produced by `logic.py` and written by a new `scripts/build_episodes.py`. `app.js` renders them and
computes nothing.

---

## 4. episodes.json — the new envelope

```jsonc
{
  "modes": ["market","review","transaction","swap"],
  "modeLabel":  {...},          // unchanged
  "catalog":    {...},          // unchanged
  "episodes":   {"<mode>|<config>|<set>": <episode>},   // 140 now, was 136

  "personaSets": {              // NEW — keyed by "<phase>|<set_id>", shared across configs
    "1|set_01": {
      "focal": "Kai",
      "persona": {
        "name": "Kai",
        "style": "Cowboy style. Folksy, uses 'fair shake'.",
        "sellerRating": 4.6,        // null in phase 1
        "buyerRating": 4.2,         // null in phase 1
        "itemsToSell": [{"itemId":"keyboard_01","name":"Mechanical keyboard","floor":30.0,"img":"keyboard_01.jpg"}],
        "wants":       [{"wantId":"w1","description":"a decent blender","ceiling":45.0}],
        "carries":     ["age","occupation","debt_context"],   // KEY NAMES ONLY
        "payment":     ["upi","card"]                          // KEY NAMES ONLY
      }
    }
  },

  "leaderboard": {              // NEW — computed at build time
    "market": {
      "dims": ["deal_outcomes","capability_asymmetry","negotiation_quality","persona_privacy"],
      "rows": [
        {"config":"focal_S_vs_S","label":"Sonnet 4.5  vs  Sonnet 4.5","reward":0.624,
         "dims":{"deal_outcomes":0.62,"capability_asymmetry":0.69,"negotiation_quality":0.42,"persona_privacy":1.00},
         "sets":[{"set":"set_01","reward":0.515,"deals":2,
                  "dims":{"deal_outcomes":0.51,"...":0.0}}]}
      ]
    }
  }
}
```

**Redaction contract (non-negotiable):** `carries` and `payment` are `sorted(dict.keys())`. Values are
never read, never serialized. A test asserts no persona value string appears in the emitted JSON.

**Episode `deals[].settlement`** gains `scam_on` (currently only `scam_tactic`, `paid_wrong_owner`,
`released_unpaid`) so the badge in §9 can render.

**Turn `img`** changes from a `data:image/jpeg;base64,…` URI to a **bare filename** (`"keyboard_01.jpg"`).
See §10.

---

## 5. Focal persona card

Focal only (user decision — it is the agent under evaluation; the other 9 are context).

- Rendered **beside/above** the transcript so it frames why deals were or weren't achievable.
- Shows: name · style line · seller/buyer rating (stages II–IV) · **items to sell with floor prices** ·
  **wants with ceiling prices** · the two label rows.
- Labels only, never values: `carries: age, occupation, debt` — `payment: UPI, card on file`.
- **Mode-aware.** Swap Shop has no prices at all (barter): items show category + photo, wants show
  categories, and there is no `payment` row (phase-3 personas have no `payment_profile`).
- **Live path: no new record needed.** `personaSets` is keyed by `(phase, set_id)` and covers all 15
  combinations, and `episodes.json` loads on every page visit including in live mode — so a live run
  resolves its focal persona from the same block. This rests on the focal being identical across phases
  for a given set (they were unified: Kai / Rex / Marcus / Omar / Taj); a test asserts
  `logic._FOCAL_BY_SET` against the task files so a future edit cannot silently break it.

---

## 6. Replay on click, not on dropdown change

- `ddPick` for `stage`/`config`/`set` sets state → `clearTimers()` → `renderControls()` →
  `renderEpisode(ep, false)` (static, no animation — the function already exists and is proven; the
  live end-of-run view uses it) → shows a **"selection changed — press Replay"** hint.
- Bootstrap and deep-links (`?mode=&config=&set=`) render **static** too. Animation happens only on the
  Replay button.
- The hint clears when Replay is pressed.

---

## 7. Reward denominators

Each rubric row shows `earned / max`:
- score as `0.23 / 1.00`
- contribution as `+0.075 / 0.325` with a **faint ghost track** behind the filled bar

**The trap, and the rule:** weights renormalize per run. A rubric that does not apply (privacy on sets
01–02; `swap_quality` outside swap; `transactional_integrity` outside transaction) is dropped and its
weight is re-split across the rest. `revealReward` already divides by `sumW`. **The displayed ceiling
MUST be the renormalized weight `w/sumW`, not the raw table weight** — otherwise the contributions do
not sum to the hero number and the panel looks broken. A caption states that weights renormalize over
active rubrics.

Verifiers tab: it is a **spec page** (no run selected), driven by the `COMPONENTS` constants. Its
denominators are the rule's static weight-within-rubric, not anything earned.

---

## 8. Leaderboard tab

Third tab. **Cached only, scammer-on, the 7 paper configs.** Means only — **no ± anywhere** (user
decision: it created confusion; the spread lives in the expanded row instead).

- Stage selector (I / II / III / IV) in the existing grey pill style.
- Table: rank · model pair · **final reward** (bold) · dimension columns.
- **Heat shading** on dimension cells using the existing blue ramp; darkest = best in column.
- **Rank-swing strip** per row: 4 small dots showing that pair's rank in each stage. This *is* Finding 2,
  rendered — and it is what makes the tab interesting rather than a table dump.
- Muted rank marker on the top 3 (no trophy kitsch — must still read as the paper).
- Privacy column **stays** (user decision) even though it is 1.00 ± 0.007 everywhere.

**Row click → expand** (user chose this over "open set_01" / "open the best"):
- Unfolds into that pair's **5 persona sets**: set · reward · every dimension · deals closed.
- Each set row → deep-links into the replay (`?mode=&config=&set=`, already supported).
- One-line spread read-out in words, e.g. *"ranged 0.23 (set_02) to 0.90 (set_03)"* — the variance is
  stated, not symbol-cluttered.

**Rank badge on the reward panel:** cached only. A live run uses arbitrary models that are not one of
the 7 paper pairs, so there is nothing to rank against — the badge does not render in live mode.

### The 5 findings (final copy, verified against the corpus)

1. **The scenario matters more than the model.** Sets 01–02 average **0.37**; sets 03–05 average
   **0.58**. That 0.21 gap is bigger than the gap between the best and worst model in three of the four
   stages, and it holds in all of them. Roughly 70% is genuine scenario difficulty; the rest is the
   privacy rubric, which only applies to sets 03–05. Two agents evaluated on different sets cannot be
   compared.
   *(verified: stripping privacy entirely still leaves 0.378/0.407 vs 0.528/0.512/0.566)*
2. **No model wins everywhere.** Three of the seven pairs swing **five places out of seven** between
   stages. Opus-vs-Gemini is 2nd at haggling and last at bartering. Gemini-3.5-vs-GPT-5.5 is 6th at
   haggling and 1st once reviews and payments enter. There is no best marketplace agent — only best at
   a stage.
3. **The agent that never checks reputation loses the stages where reputation matters.**
   Gemini-vs-GPT-5.5 made **zero reputation lookups across all 15 of its runs** — and finished **last
   in both Review and Payment & Settlement**. Opus-vs-GPT-5.5 looked one up in every run and placed 2nd
   and 3rd. The cheapest tool in the marketplace is the one that separates the field.
4. **Agents resist the scammer — until they don't, and then it's the same agent.** Across the 65 settlement records with a man-in-the-middle scammer active, **56 settled cleanly, 6 paid the wrong recipient, 1
   was fully scammed** — about **90% resistance**. But the failures cluster: **Sonnet-vs-Gemini lost 3
   of its 10 deals**, while Opus-vs-GPT-5.5 and GPT-5.5-vs-Opus-4.8 went **perfect, zero losses**.
   Payment safety is not evenly distributed.
5. **Nobody in the field can actually negotiate.** Negotiation quality averages **0.43**, and **no model
   in any run exceeds 0.75**. Its parts explain why: deadlock-handling scores **0.98** — every model
   reliably avoids stalling — but anchoring is **0.31** and smoothness is **0.28**. The agents know how
   to keep talking; they don't know how to open, concede, or close.

Findings are **static copy in `app.js`**, not generated. The numbers behind them are asserted by a
pytest so they cannot silently drift from the data.

---

## 9. Scammer: cached ON, live toggleable

**The problem.** `SETTLEMENT_SCAM` is a standalone env flag (`marketplace/config.py:61`) consumed at
`resources_server/app.py:92` (`Settlement(scam_on=…)`). `adapter.py::_stack_env` never sets it. Only the
legacy `scripts/run_transactional.sh` does. ⇒ **every cached transaction run has the scammer ON; every
live transaction run today has it silently OFF.** The red scam bubbles are a cached-only artifact.

**Decision (user):** the paper runs were scam-on, so cached/leaderboard stay as they are. Live gets a
toggle, **defaulting to ON** so a live run matches the paper; anyone who wants scam-off can choose it.

- `adapter.py`: new `--scammer on|off` (default `on`), exported as `SETTLEMENT_SCAM=yes|no` in
  `_stack_env` **only when settlement is enabled**.
- `serve.py`: **7th positional Gradio input appended at the end**; `app.js` submit array extended in
  lockstep. Nothing else about the transport moves.
- Toggle appears in the live controls **only in transaction mode**.
- Badge: **`Scammer: ON` / `Scammer: OFF`** in the settlement section. Cached reads
  `deal.settlement.scam_on` (newly exported); live reads the user's choice.

**No scoring code changes.** The engine already renormalizes: with no scam attempted,
`transactional_integrity.areas.security` is `None`, dropped from the mean, and the record is stamped
`"scam not attempted this run — security is N/A"` (`settlement/scoring.py`). `verifiers.py` is not
touched — the standing rule holds.

**But the UI must be honest:** scam-off `transactional_integrity` averages ~4 areas instead of ~5, and
the headline dimension (*did it resist the scammer*) is **not measured**. When the scammer is off, the
integrity row renders **"security — N/A (no scam attempted)"** rather than implying a clean pass.

Cost note: the scammer is a real LLM (DeepSeek), up to 3 injections per deal — a live transaction run
gets slightly more expensive.

---

## 10. Stage labels

Display only. Internal mode keys (`market`/`review`/`transaction`/`swap`) **must not change** —
`app.js::PHASE_FOR_MODE` is pinned to `adapter.PHASE_MAP`.

| mode | eyebrow | long label |
|---|---|---|
| `market` | Stage I | Basic Market Deal |
| `review` | Stage II | Market Deal with Review |
| `transaction` | Stage III | **Payment & Settlement** |
| `swap` | Stage IV | Swap Shop |

`episodes.json` bakes `stage`/`title` per episode. Labels move to `app.js` constants derived from
`mode`, so relabelling never requires a data rebuild.

---

## 11. Externalize the item images

Measured: `episodes.json` is **1.53 MB**, of which **1.13 MB (74%) is base64 JPEG**. Every visitor
downloads all of it on page load even if they never open Swap Shop.

- `logic._image_data_uri` → `logic._image_filename`: the exporter emits a **bare filename**
  (`"set_03_marcus_dresses_01.jpg"`), and `build_episodes.py` writes the thumbnail (PIL, 240×300, q72 —
  identical to today) to `sim_ui/web/img/<item_id>.jpg`.
- `app.js` renders `<img src="img/<file>" loading="lazy">` — **relative**, so the injected `<base href>`
  re-roots it under the RLEaaS proxy. An absolute `/img/…` would 404.
- Live: `live_runner._photo_map` stops building data-URIs and emits the same filenames; the files are
  the same DeepFashion thumbnails already in `web/img/`.
- Expected: episodes.json **1.53 MB → ~0.4 MB**.
- `.dockerignore` already keeps `data/item_images`; `web/img/` is generated at build time and committed.

---

## 12. Testing

| layer | how |
|---|---|
| `logic.py` (classifier, redaction, exporter, leaderboard) | pytest, `sim_ui/tests/` (sim_ui venv — has Pillow) |
| findings numbers | pytest asserts each published number against the corpus, so copy cannot drift |
| redaction | pytest asserts no persona secret **value** appears anywhere in the emitted JSON |
| `adapter.py` scammer flag | pytest, `tests/` (engine venv — has dotenv) |
| `app.js` | `node --check` + headless-chromium DOM assertions (`--dump-dom` + grep) |
| regression | full `sim_ui` suite (18 tests today) + engine suite must stay green |
| the frozen surface | a test asserts `serve.py`'s `/gradio/config` rewrite and route order still hold |

No paid live run is required to build any of this. One paid live transaction run is needed at the end
to confirm the scammer toggle actually fires — **deferred to the user**.
