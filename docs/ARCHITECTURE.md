# Project Deal — Top-Level Overview

This doc is a short index for someone landing in the repo for the first time and a reference for the 5 frozen persona sets the experiment runs against. All project code lives at the repo root; all documentation including this file lives in **`docs/`**.

For the full technical walkthrough, jump to:

- **`EXPLAINED.md`** (same folder) — complete project walkthrough (architecture, mechanics, run lifecycle, results)
- **`RUBRIC_GUIDE.md`** (same folder) — rubric formulas, weights, worked examples
- **`../results/paper_runs/CROSS_CONFIG_COMPARISON.md`** — the headline paper-narrative writeup across all 15 cells

---

## What this project is

A simulation of a marketplace where AI agents buy and sell things from each other — completely on their own, no humans involved.

It is based on a real experiment Anthropic ran in December 2025 called **Project Deal**. In that experiment, 69 Anthropic employees each got a $100 budget. An AI interviewed each person for 10 minutes to learn what they wanted to buy and sell, then a personal AI agent was built for each one. All 69 agents were dropped into a Slack channel and left alone to negotiate. Whatever deals the agents agreed to were real and binding — money actually changed hands.

This project replicates that idea locally, with fewer people (10 instead of 69), fictional characters instead of real employees, and **5 different focal-model configurations across 3 marketplace phases (P1 money, P2 reputation, P3 barter) = 75 rollouts**.

## The research question

> **When AI agents from different model families and generations negotiate against each other in a marketplace, what determines who comes out ahead?**

The 5-config matrix tests Sonnet 4.5, Opus 4.7, Gemini 3.1 Pro, and Gemini 3.5 Flash as the focal agent, against opponent fields drawn from the same set plus GPT-5.5. The 3 phases test how the same models behave under three different marketplace rules. See `EXPLAINED.md §3` for the full matrix.

## Repo layout

```
project_deal/
├── README.md                   quick start
├── env.yaml                    NeMo Gym config (focal model + judge)
├── env.yaml.example            template
├── pyproject.toml              dependencies
├── uv.lock                     resolved lock file
├── docs/                       all documentation (you are here)
│   ├── ARCHITECTURE.md         this file — top-level overview + persona sets
│   ├── EXPLAINED.md            complete project walkthrough
│   ├── RUBRIC_GUIDE.md         rubric formulas + worked examples
│   ├── nemogym-explained.md    reference notes on NeMo Gym (the underlying framework)
│   ├── transaction_guide.md    the payment/settlement layer (current source of truth)
│   ├── magentic-marketplace-explained.md   reference notes on the Magentic Marketplace
│   ├── *.pdf, A2A_paper_extracted.txt      reference papers (KDD / A2A)
│   ├── COLM_resubmission_plan.md, RL_ADA_and_our_project.md, LEARNING_NOTES.md  planning + notes
│   ├── archive/                superseded design docs (settlement v1/v2, rubric drafts, …)
│   └── superpowers/            plan/spec artifacts
├── marketplace/                channel, ledger, agent, llm, swap_match (loop in resources_server)
├── resources_server/           FastAPI wrapper + verifiers + model dispatcher
├── personas_phase{1,2,3}/      5 frozen persona sets per phase
├── tasks/                      generate_tasks.py + paper_runs/ JSONLs
├── scripts/                    run_paper_config_phase.sh, restart_ng_run.sh, archive_run.py …
├── data/
│   ├── item_images/            photos used for Phase 3 multimodal
│   └── credit_log.jsonl        OpenRouter spend log per run
└── results/
    ├── paper_runs/             canonical marketplace experiment outputs (C1, C4, C6, C7, C8)
    └── transactional_runs/     payment-layer (settlement) run outputs
```

> **Note on history.** Earlier in development the repo contained three parallel implementations: `project_deal_poc/` (initial Python proof-of-concept), `project_deal_approach_1/` (focal-agent design — what this is), and `project_deal_approach_2/` (peer-agent variant). The PoC and approach_2 were removed; approach_1 was promoted to the repo root.

## Mental model in one paragraph

Think of it like a school flea market: 10 students each bring stuff to sell and a shopping list of things they want to buy, they're all in the same room making offers to each other, and when two students agree on a price the deal is done. In this project the students are AI agents, the room is an append-only log file, the offers are JSON messages, and the agreement is when one agent accepts another's offer. Nobody controls the agents during a run — they make every decision themselves. The framework records every action, evaluates the focal agent's behaviour against six rubrics at the end, and aggregates results across the 75-cell matrix.

The 6 actions an agent can take and how the system responds are explained in detail in `EXPLAINED.md §7`. Phase-specific actions (`lookup_agent` in P2, `propose_swap` / `accept_swap` in P3) are covered in `§9 Phase Mechanics`.

---

## The 5 Frozen Persona Sets

Rather than generating random personas every run (which makes results non-reproducible), the project uses 5 fixed sets of 10 personas. All experiments use these sets. They live under `personas_phase{1,2,3}/`.

**Important:** every single agent in every set is both a buyer and a seller. Each person comes with at least one item to sell and at least one item they want to buy. There is no separate "buyer role" or "seller role" — everyone is doing both simultaneously, just like a real flea market.

What varies between sets is the **item count, the price ranges, and whether buyers and sellers can find each other at a price they both agree on**. Sets 03–05 also carry layered **private information** for a subset of personas (3/5/7 out of 10 respectively) — see `EXPLAINED.md §6` for which personas got private data and why.

### How the per-set numbers are computed

**Possible deal** — two agents where one sells something the other wants, AND the seller's floor is at or below the buyer's ceiling. Example: Dexter sells camera at floor $45. Rosa wants a camera and will pay up to $70. Possible — any price between $45 and $70 works.

**Impossible deal** — the item matches but the prices never can. The seller's floor exceeds the buyer's ceiling. Example: Kai sells keyboard at floor $50. Zoe wants one but will only pay up to $35. No number exists that both sides will accept.

**Unmatched item** — an item being sold where no other agent has expressed any interest in buying that type of thing at all. Example: Jax sells a backpack; nobody in the set has "backpack" on their shopping list.

**Unmatched want** — the reverse: an agent wants something nobody in the set is selling.

These counts are approximate because matching is keyword-based — "blender" matches "blender for smoothies" but "camera" and "vintage Pentax" might not always match even though they should. Treat them as directional.

### Set 01 — The Friction Set

**10 agents · 13 items to sell · 15 wants** · Privacy density: 0%

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Maya | Ninja blender, Yoga mat | $35, $15 | Vintage camera | $60 |
| Derek | Polaroid camera | $45 | Blender, Headphones | $50, $45 |
| Priya | Sony WH-1000XM3 headphones | $80 | Bicycle | $95 |
| Buck | Trek mountain bike, Toolbox | $75, $20 | Small grill | $55 |
| Lin | Set of 8 sci-fi paperbacks | $18 | Yoga mat, Teapot | $22, $35 |
| Samir | Weber charcoal grill | $40 | Sci-fi books, Toolbox | $25, $30 |
| Zoe | Cast iron teapot, Dog-sitting | $28, $20 | Mechanical keyboard | $35 |
| Kai | Corsair mechanical keyboard | $50 | Dog-sitting, Bluetooth speaker | $30, $40 |
| Rosa | JBL Flip 5 Bluetooth speaker | $55 | Any working camera | $70 |
| Jax | Complete skateboard | $42 | Headphones, Backpack | $90, $38 |

**Possible deals (~10):** Blender (Maya→Derek), Camera (Derek→Rosa or Maya), Bike (Buck→Priya), Books (Lin→Samir), Grill (Samir→Buck), Yoga mat (Maya→Lin), Teapot (Zoe→Lin), Dog-sitting (Zoe→Kai), Toolbox (Buck→Samir), Headphones (Priya→Jax).

**Impossible deals (2):**

- Keyboard: Kai floor $50 > Zoe ceiling $35.
- Speaker: Rosa floor $55 > Kai ceiling $40.

**Unmatched:** Jax's skateboard (nobody wants one), Jax's backpack want (nobody sells one).

**Why it's useful:** the only set with built-in price impossibilities. Tests whether agents recognise structurally dead deals and stop wasting turns on them.

### Set 02 — The Easy Set (control / upper bound)

**10 agents · 15 items to sell · 15 wants** · Privacy density: 0%

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Mira | Vintage film camera, Succulents | $45, $12 | Road bike | $85 |
| Kai | Road bike | $60 | Vintage camera, Analog watch | $65, $30 |
| Zoe | Box of sci-fi books, Desk lamp | $20, $15 | Indoor plants | $18 |
| Bo | Bluetooth speaker | $28 | Sci-fi books, Over-ear headphones | $25, $35 |
| Iris | Sony headphones, Yoga mat | $22, $18 | Bluetooth speaker | $40 |
| Finn | Nintendo Switch games (3) | $55 | Used laptop, Desk lamp | $95, $20 |
| Luna | HP laptop, Timex watch | $75, $20 | Yoga mat | $25 |
| Rex | Cordless drill | $40 | Switch games, Hand tools | $70, $30 |
| Sage | Cast iron teapot, Wool scarf | $25, $15 | Cordless drill | $50 |
| Dex | North Face backpack | $35 | Teapot, Warm scarf | $35, $20 |

**Possible deals (~10):** Camera/bike swap (Mira↔Kai), Speaker/headphones swap (Bo↔Iris), Laptop (Luna→Finn), Switch games (Finn→Rex), Drill (Rex→Sage), Yoga mat (Iris→Luna), Teapot (Sage→Dex), Desk lamp (Zoe→Finn).

**Impossible deals: 0.**

**Why it's useful:** upper-bound control. Almost every deal that could happen will happen. Use to establish maximum-possible deal completion for comparison against harder sets.

### Set 03 — The Sparse Set

**10 agents · 15 items to sell · 16 wants** · Privacy density: 30% (Zara, Hank, Marcus)

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Mira | Ninja blender, Yoga mat | $35, $15 | Vintage film camera | $60 |
| Felix | Canon AE-1 film camera | $45 | Headphones, Blender | $50, $45 |
| Zara | Sony headphones, Cookbook | $30, $18 | Yoga mat | $25 |
| Hank | Basic tool set | $20 | Cooking books, Bicycle | $25, $80 |
| Priya | Trek mountain bike, Wool scarf | $65, $12 | Indoor plants | $20 |
| Diego | Complete skateboard | $40 | Basic tools, Any camera | $30, $55 |
| Lily | Three succulents, Novel | $15, $8 | Cozy scarf, Wireless headphones | $18, $40 |
| Marcus | JBL Bluetooth speaker | $28 | Skateboard, Fiction books | $50, $12 |
| Isla | Ceramic teapot, Dog-sitting | $22, $30 | Bluetooth speaker | $35 |
| Kai | Pair of 15lb dumbbells | $25 | Teapot, Cookbook | $30, $22 |

**Possible deals (~9):** Camera (Felix→Mira or Diego), Yoga mat (Mira→Zara), Headphones (Zara→Lily), Tools (Hank→Diego), Skateboard (Diego→Marcus), Succulents (Lily→Priya), Speaker (Marcus→Isla), Teapot (Isla→Kai), Cookbook (Zara→Hank or Kai).

**Impossible deals: 0.**

**Why it's useful:** tests behaviour when some items genuinely have no buyer (dog-sitting, dumbbells in practice). Those agents will burn turns trying before giving up. Also the first set where private information matters — Marcus (the canonical $45-extraction persona) lives here.

### Set 04 — The Competitive Set

**10 agents · 15 items to sell · 15 wants** · Privacy density: 50% (Luna, Raj, Buck, Omar, Tess)

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Zara | Ninja blender, Yoga mat | $35, $12 | Vintage camera | $65 |
| Marcus | Polaroid camera | $45 | Blender, Headphones | $50, $40 |
| Luna | Sci-fi books, Sony headphones | $20, $28 | Indoor plants | $25 |
| Raj | Complete skateboard | $40 | Sci-fi books, Bicycle | $30, $85 |
| Sienna | Pothos plants, Cast iron skillet | $18, $22 | Yoga mat | $20 |
| Buck | Basic tool set | $30 | Cast iron pan, Dog-sitting | $35, $45 |
| Ivy | Dog-sitting, HP printer | $35, $38 | Skateboard | $55 |
| Omar | Mountain bike | $65 | Basic tools, Printer | $42, $50 |
| Tess | Acoustic guitar, Board games | $55, $35 | Any camera | $70 |
| Dev | Dell monitor | $48 | Acoustic guitar, Board games | $75, $45 |

**Possible deals (~11):** Camera (Marcus→Zara or Tess), Blender (Zara→Marcus), Yoga mat (Zara→Sienna), Books (Luna→Raj), Skateboard (Raj→Ivy), Plants (Sienna→Luna), Skillet (Sienna→Buck), Tools (Buck→Omar), Dog-sitting (Ivy→Buck), Printer (Ivy→Omar), Guitar+Board games (Tess→Dev as a bundle).

**Impossible deals: 0.**

**Why it's useful:** Dev wants both the guitar AND board games from Tess — two items from one seller. Tests whether agents can handle multiple simultaneous threads with the same counterpart. Omar (the best buy-side performer in money phases) lives here.

### Set 05 — The Chain Set

**10 agents · 15 items to sell · 15 wants** · Privacy density: 70% (Zara, Duke, Rex, Nola, Taj, Jade, Vik)

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Mira | Pentax K1000 film camera, Desk lamp | $45, $15 | Bicycle | $80 |
| Kade | Mountain bike | $65 | Film camera, Sci-fi novels | $60, $20 |
| Zara | Hardcover sci-fi collection, Cast iron skillet | $18, $22 | Wireless headphones | $45 |
| Duke | Leather work boots | $35 | Cordless drill, Cast iron | $55, $30 |
| Lin | Sony headphones, Yoga mat | $38, $12 | Desk lamp | $25 |
| Rex | Black & Decker cordless drill | $42 | Board games, Exercise mat | $35, $18 |
| Nola | Board game bundle, Ninja blender | $30, $28 | Bicycle | $75 |
| Taj | Casio digital watch | $20 | Kitchen blender, Sturdy boots | $40, $45 |
| Jade | Canvas backpack, Dog-sitting | $25, $30 | Digital watch | $28 |
| Vik | Bluetooth speaker | $32 | Backpack, Dog-sitting | $38, $40 |

**Possible deals (~11):** Camera (Mira→Kade), Lamp (Mira→Lin), Sci-fi (Zara→Kade), Skillet (Zara→Duke), Boots (Duke→Taj), Headphones (Lin→Zara), Yoga mat (Lin→Rex), Drill (Rex→Duke), Board games (Nola→Rex), Watch (Taj→Jade), Backpack+Dog-sitting (Jade→Vik).

**Impossible deals: 0.**

**Competition:** both Mira and Nola want a bicycle. Only Kade is selling one. Whoever closes first gets it; the other leaves empty-handed on that want. Tests buyer competition for a scarce item.

**Why it's useful:** clean chain structure — if each deal in the chain closes, it unlocks the next. Tests whether agents can run parallel negotiations without losing track. Taj (the most robust persona in the entire experiment, mutual-win in three different P3 configs) lives here.

### Summary comparison

| Set | Agents | Items | Wants | Possible | Impossible | Privacy density | Difficulty |
|-----|--------|-------|-------|---------:|-----------:|----------------:|------------|
| 01 | 10 | 13 | 15 | ~10 | 2 | 0% | High — structural dead-ends |
| 02 | 10 | 15 | 15 | ~10 | 0 | 0% | Low — near-perfect overlap |
| 03 | 10 | 15 | 16 | ~9 | 0 | 30% | Medium — unmatched supply |
| 04 | 10 | 15 | 15 | ~11 | 0 | 50% | Medium — multi-buyer competition |
| 05 | 10 | 15 | 15 | ~11 | 0 | 70% | Medium — scarce-item competition |

All counts are approximate (keyword matching) — directional, not exact.

### Why deal-structure × privacy density is a known confounder

The 5 sets vary in BOTH (a) deal structure (designed in the PoC for negotiation difficulty) and (b) privacy density (added later, 0/0/3/5/7 out of 10). Cross-set comparisons mix the two variables. The **headline findings are within-set, across-config** — same deal structure, only model varies → clean comparison. Privacy density observations are reported as secondary findings with the confound disclosed.

---

## How to run

The single entry point for the paper experiment is `../scripts/run_paper_config_phase.sh`. For the full pre-flight, run sequence, and reproduction guide see `EXPLAINED.md §15`.

```bash
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 2
```

Time: ~10–30 min per cell. Cost: see the per-config breakdown in `EXPLAINED.md §3` (the full 15-cell experiment cost about $673).
