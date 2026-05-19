# Project Deal × NeMo Gym — Design Document

**Date:** 2026-05-15
**Project folder:** `project_deal_nemogym/`
**Status:** Design approved, ready for implementation planning

---

## 1. What We Are Building

A new project, `project_deal_nemogym/`, that runs the Project Deal multi-agent marketplace simulation and evaluates it using NeMo Gym's infrastructure — specifically its rollout collection, verifier scoring, and structured output format.

The goal is to:
1. Run the marketplace simulation multiple times with different model configurations
2. Score each run using well-defined rubrics (verifiers)
3. Produce structured, comparable results — especially the "model advantage" finding from the original Project Deal experiment

---

## 2. What NeMo Gym Actually Is (and Is Not)

### What it is

NeMo Gym is built around evaluating and training **one policy model** by putting it in a situation repeatedly, scoring how it does, and using those scores for improvement.

```
┌──────────┐     question      ┌──────────────┐
│  POLICY  │ ────────────────► │  ENVIRONMENT │
│  (LLM)   │ ◄──────────────── │  (fixed)     │
└──────────┘     feedback      └──────────────┘
                                      │
                               VERIFIER scores it
                                reward = 0.82
```

Built-in use cases: math problems, coding tasks, tool-use benchmarks. One model. One environment. One score per run.

### What it is NOT (for our purposes)

NeMo Gym is not natively designed for **multi-agent peer systems** where every agent is an LLM and every agent affects every other. That is what Project Deal is.

| | NeMo Gym native design | Project Deal |
|---|---|---|
| How many LLMs? | 1 (the policy) | 10 (all peers) |
| What is the environment? | A fixed scripted world | The other agents |
| What changes between runs? | The model improves | Different model mix |
| What are you measuring? | How good is this one model? | What emerges from agent interaction? |
| Analogy | One student taking an exam | 10 people negotiating in a room |

### How we use NeMo Gym anyway

We use NeMo Gym for three things it does well:
- **Resources Server** — wrap our marketplace as a FastAPI server with a `verify()` endpoint
- **Rollout collection** — `ng_collect_rollouts` runs the simulation N times, saves structured JSONL output
- **Reward scoring** — the verifier produces a float per run, making results directly comparable

The multi-agent peer simulation runs **inside** the Resources Server, unchanged. NeMo Gym wraps the outside.

---

## 3. NeMo Gym Setup

### Prerequisites

- Python 3.12+ (NeMo Gym requirement — note: existing PoC uses 3.10+, new project uses 3.12)
- `uv` package manager
- Git
- OpenRouter API key (already have this)

### Installation

```bash
git clone git@github.com:NVIDIA-NeMo/Gym.git nemo_gym_lib
cd nemo_gym_lib
uv venv --python 3.12 && source .venv/bin/activate
uv sync
```

### Model Configuration (`env.yaml`)

Create this file in the project root. This is the **only file you change to swap models**:

```yaml
policy_base_url: https://openrouter.ai/api/v1
policy_api_key: your_openrouter_key_here
policy_model_name: anthropic/claude-sonnet-4-5
```

To compare models, change one line:
```yaml
policy_model_name: anthropic/claude-haiku-4-5
```

OpenRouter is fully compatible — NeMo Gym works with any OpenAI-compatible endpoint.

### The 3-Server Architecture

When you run `ng_run`, three local servers start simultaneously:

```
┌──────────────────────┐   tool calls    ┌──────────────────────────┐
│   AGENT SERVER       │ ──────────────► │   RESOURCES SERVER       │
│   (NeMo Gym built-in)│ ◄────────────── │   (YOU write this)       │
│                      │  tool responses │                          │
│   Reads task JSONL → │                 │   - Exposes HTTP endpoints│
│   calls /run_market  │                 │   - Runs the full        │
│   once per task →    │                 │     marketplace inside   │
│   calls verify()     │                 │   - Has verify()         │
└──────────────────────┘                 └──────────────────────────┘
          │
          │ LLM calls (via env.yaml) — only used for Approach 1 focal agent
          ▼                             In Approach 2, the marketplace's
┌──────────────────────┐               LLM calls go directly to OpenRouter
│   MODEL SERVER       │               from inside the Resources Server —
│   (OpenRouter)       │               NOT through this policy server.
│   policy_model_name  │
└──────────────────────┘
```

**Important:** In Approach 2 (full peer marketplace), the NeMo Gym Agent Server makes exactly **one tool call** — `run_marketplace` — and waits for the full simulation result. All 10 agent LLM calls happen inside the Resources Server, going directly to OpenRouter using the existing PoC's `llm.py`. The Model Server / policy loop is only relevant for Approach 1 (focal agent).

### Running an Experiment

```bash
# Step 1: start all servers
ng_run "+config_paths=[resources_servers/marketplace/configs/marketplace.yaml,responses_api_models/openai_model/configs/openai_model.yaml]"

# Step 2: collect rollouts (in a separate terminal)
ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath=tasks/marketplace_tasks.jsonl \
  +output_jsonl_fpath=results/sonnet_rollouts.jsonl \
  +limit=10 \
  +num_repeats=3
```

Each line in the output JSONL = one full marketplace run + reward score + full trajectory.

---

## 4. How the Marketplace Fits Into NeMo Gym

### The Architecture

The full peer marketplace simulation runs **inside** the Resources Server. All 10 agents are LLMs. The existing `channel.py`, `ledger.py`, `scheduler.py`, `agent.py` are imported directly.

```
┌──────────────────────────────────────────────────────────┐
│  NeMo Gym Resources Server  (resources_server/app.py)    │
│                                                          │
│  POST /run_marketplace  ←── NeMo Gym triggers this once  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  MARKETPLACE SIMULATION (your existing code)       │  │
│  │                                                    │  │
│  │  Alice (LLM) ◄──► Bob (LLM) ◄──► Carol (LLM)...  │  │
│  │  channel.py  ledger.py  scheduler.py  agent.py     │  │
│  │                                                    │  │
│  │  All 10 agents run as peers. Fully unchanged.      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  verify()  ←── called at the end, scores the whole run  │
└──────────────────────────────────────────────────────────┘
```

NeMo Gym's job: trigger the simulation, collect the output, call verify(), save everything.

### What a Task Looks Like (`tasks/marketplace_tasks.jsonl`)

Each line is one experiment scenario:

```json
{
  "responses_create_params": {
    "input": [{"role": "user", "content": "Run marketplace scenario: persona_set=set_01, model_config=all_sonnet, seed=42"}],
    "tools": [{"type": "function", "name": "run_marketplace", "description": "Run the full multi-agent marketplace simulation", "parameters": {"type": "object", "properties": {"persona_set": {"type": "string"}, "model_config": {"type": "string"}, "seed": {"type": "integer"}}, "required": ["persona_set", "model_config", "seed"]}}]
  },
  "metadata": {
    "persona_set": "set_01",
    "model_config": "all_sonnet",
    "seed": 42,
    "expected_possible_deals": 8
  }
}
```

Tasks cover all combinations:
- 5 persona sets × 3 model configs (all-sonnet, mixed, all-haiku) × 3 seeds = 45 rollouts

---

## 5. Two Approaches — Both Implemented

### Approach 1: One Focal Agent, Swap the Model

**What it is:** Pick one persona (e.g. Alice). Run Alice with Sonnet. Same marketplace, same 9 opponents (fixed to Sonnet). Then run Alice with Haiku. Compare Alice's individual scores.

**What it answers:** "How well does model X negotiate as an individual agent?"

**Best for:** Clean model benchmarking. Isolates the model variable.

**Key difference from full Project Deal:** The 9 opponents are held constant (Sonnet). Alice is the only thing that changes.

### Approach 2: Full Marketplace, All Agents, Mixed Models

**What it is:** All 10 agents run as full LLM peers. Compare:
- Run A: All 10 = Sonnet
- Run B: 5 = Sonnet, 5 = Haiku (randomly assigned)
- Run C: All 10 = Haiku

**What it answers:** "What emerges from agent interaction when models have different capabilities? Do stronger models extract disproportionate value?"

**This is the Project Deal replication.** The headline finding from Project Deal was that Opus agents got better deals than Haiku agents in mixed marketplaces — the "invisible disadvantage."

---

## 6. Rubrics (Verifiers)

### Approach 1 Rubrics — Individual Agent

Applied per focal agent, per run.

---

**Rubric 1 — Deal Completion Rate** (weight: 35%)

Did the focal agent close all the deals it needed to?

```python
score = deals_closed / (items_to_sell + items_to_buy)
# 0.0 = closed nothing, 1.0 = closed everything
```

---

**Rubric 2 — Seller Price Quality** (weight: 25%)

For items sold, how close to the ceiling did the agent get?

```python
score = (price_received - floor_price) / (ceiling_price - floor_price)
# 0.0 = sold at floor (worst), 1.0 = sold at ceiling (best)
# Averaged across all items sold
```

---

**Rubric 3 — Buyer Price Quality** (weight: 20%)

For items bought, how much below budget did the agent pay?

```python
score = (budget - price_paid) / budget
# 0.0 = paid full budget (worst), higher = better deal
```

---

**Rubric 4 — Turn Efficiency** (weight: 15%)

How many turns did the agent use? Fewer = more decisive.

```python
score = 1 - (agent_turns_used / max_turns_allowed)
# 0.0 = used all turns, 1.0 = finished immediately
```

---

**Rubric 5 — Constraint Compliance** (weight: 5%)

Did the agent ever violate floor/ceiling constraints?

```python
score = 1.0  # if no violations
score = 0.0  # if any violation occurred
```

---

**Combined Score:**
```python
final_reward = (
    0.35 * deal_completion_rate     +
    0.25 * seller_price_quality     +
    0.20 * buyer_price_quality      +
    0.15 * turn_efficiency          +
    0.05 * constraint_compliance
)
```

**Example comparison output:**

| | Deal rate | Seller price | Buyer price | Turns | Final reward |
|---|---|---|---|---|---|
| Alice (Sonnet) | 1.0 | 0.87 | 0.40 | 0.80 | **0.82** |
| Alice (Haiku) | 0.5 | 0.37 | 0.14 | 0.60 | **0.45** |

---

### Approach 2 Rubrics — Full Marketplace / System Level

Applied to the whole marketplace run, not any single agent.

---

**Rubric 1 — Market Closure Rate**

Of all deals that COULD have happened, what % actually closed?

A **possible deal** is defined as: at least one agent has item X listed for sale at or below their ceiling, AND at least one other agent has item X in their wants with a budget >= the seller's floor price. This is the same definition used in the existing PoC's `analyze.py` (the "possible" column in run summaries).

```python
score = deals_sealed / possible_deals
# 0.0 = no trades happened, 1.0 = every possible trade was completed
```

Comparison:
```
All-Sonnet:  0.85  (found 85% of possible trades)
All-Haiku:   0.55  (missed 45% of possible trades)
```

---

**Rubric 2 — Average Price Surplus Per Deal**

For each deal, how much total value was created? Surplus = what the seller gained above their floor + what the buyer saved below their budget.

```python
surplus = (price_sealed - seller_floor) + (buyer_budget - price_sealed)
score = mean(surplus across all deals) / theoretical_max_surplus
```

A high-surplus marketplace means both sides are negotiating well. A low-surplus marketplace means agents are leaving value on the table or not reaching mutually good prices.

---

**Rubric 3 — Model Advantage Score** *(the Project Deal finding)*

In mixed runs, do Sonnet agents extract more value than Haiku agents from the same marketplace?

```python
# Per-agent value extracted:
agent_gain = sum(
    (price_sold - floor_price)      # for each item sold
    + (budget - price_paid)         # for each item bought
)

sonnet_avg_gain = mean(agent_gain for all Sonnet agents)
haiku_avg_gain  = mean(agent_gain for all Haiku agents)

advantage_ratio = sonnet_avg_gain / haiku_avg_gain
# 1.0 = equal, 2.0 = Sonnet extracted twice as much value
```

**This is the headline metric.** It directly replicates Project Deal's invisible disadvantage finding.

Expected output:
```
Mixed run (5 Sonnet / 5 Haiku):
  Sonnet agents avg gain: $32
  Haiku agents avg gain:  $14
  Advantage ratio: 2.3x  ← Sonnet extracted 2.3x more value
```

---

**Rubric 4 — Negotiation Speed**

Average number of turns from first offer to deal sealed, across all deals in the run.

```python
score = mean(turns_to_close per deal)
# Lower is better — fewer back-and-forths means more decisive agents
```

Comparison:
```
All-Sonnet:  4.2 turns/deal  (decisive)
Mixed:       7.8 turns/deal  (Sonnet-Haiku pairs take longer to agree)
All-Haiku:  11.3 turns/deal  (slow, many passes and re-offers)
```

---

**Rubric 5 — Fairness Score (Gini Coefficient)**

In mixed runs, how unequal is value distribution across agents?

```python
gains = [agent_gain for all agents]
gini = gini_coefficient(gains)
# 0.0 = perfectly equal (everyone extracted the same value)
# 1.0 = completely unequal (one agent got everything)
```

In mixed runs, if Sonnet agents consistently extract more, the Gini score rises — the marketplace is structurally unfair by model capability.

---

**Full Comparison Table (Approach 2):**

*Note: numbers below are illustrative examples only, not actual run results. Real values will be produced by running the experiment.*

| Run config | Closure rate | Avg surplus | Sonnet gain | Haiku gain | Advantage ratio | Speed |
|---|---|---|---|---|---|---|
| All Sonnet | 0.85 | $28 | $32 | — | — | 4.2 turns |
| 50/50 Mixed | 0.72 | $19 | $30 | $14 | **2.1x** | 7.8 turns |
| All Haiku | 0.55 | $11 | — | $13 | — | 11.3 turns |

---

## 7. File Structure for `project_deal_nemogym/`

```
project_deal_nemogym/
├── env.yaml                          # policy_base_url, policy_api_key, policy_model_name
├── pyproject.toml                    # Python 3.12, nemo_gym dependency
│
├── resources_server/
│   ├── app.py                        # The Resources Server — marketplace + verify()
│   ├── verifiers.py                  # All 5+5 rubric functions
│   ├── model_config.py               # Maps config name → per-agent model assignments
│   │                                 # Valid configs:
│   │                                 #   "all_sonnet"  → all 10 agents use claude-sonnet-4-5
│   │                                 #   "all_haiku"   → all 10 agents use claude-haiku-4-5
│   │                                 #   "mixed"       → first 5 personas get sonnet,
│   │                                 #                   last 5 get haiku (deterministic,
│   │                                 #                   not random, so results are reproducible)
│   │                                 #   "focal_sonnet"→ persona index 0 gets sonnet,
│   │                                 #                   all others get sonnet (Approach 1 baseline)
│   │                                 #   "focal_haiku" → persona index 0 gets haiku,
│   │                                 #                   all others get sonnet (Approach 1 test)
│   └── configs/
│       └── marketplace.yaml          # ng_run config for this server
│
├── tasks/
│   ├── generate_tasks.py             # Script to generate marketplace_tasks.jsonl
│   └── marketplace_tasks.jsonl       # 45 scenarios (5 sets × 3 configs × 3 seeds)
│
├── results/                          # Output rollouts, one file per experiment run
│   ├── sonnet_all_rollouts.jsonl
│   ├── mixed_rollouts.jsonl
│   └── haiku_all_rollouts.jsonl
│
├── analysis/
│   └── compare.py                    # Reads results/, prints comparison tables
│
└── marketplace/                      # Symlink or copy of project_deal_poc core modules
    ├── channel.py
    ├── ledger.py
    ├── agent.py
    ├── scheduler.py
    ├── build_agents.py
    └── personas/                     # The 5 frozen persona sets from the PoC
```

The `marketplace/` folder reuses the existing PoC code directly. No rewrite needed.

---

## 8. The Resources Server — Core Logic Sketch

```python
# resources_server/app.py

class MarketplaceResourcesServer(SimpleResourcesServer):

    def setup_webserver(self) -> FastAPI:
        app = super().setup_webserver()
        app.post("/run_marketplace")(self.run_marketplace)
        return app

    async def run_marketplace(self, body: RunMarketplaceRequest) -> RunMarketplaceResponse:
        # body contains: persona_set, model_config, seed

        # 1. Load personas
        personas = load_persona_set(body.persona_set)

        # 2. Build agents with model assignments from model_config
        #    e.g. "mixed" → 5 agents get sonnet, 5 get haiku
        agents = build_agents(personas, model_config=body.model_config)

        # 3. Run the full marketplace simulation (your existing scheduler)
        result = run_marketplace(agents, seed=body.seed)

        return RunMarketplaceResponse(
            deals=result.deals,
            channel_log=result.channel,
            agent_gains=result.per_agent_gains,
            turns_used=result.turns_used,
        )

    async def verify(self, body: MarketplaceVerifyRequest) -> BaseVerifyResponse:
        # body.response contains the full tool call history
        # Extract the run_marketplace result from the tool call output
        run_result = extract_run_result(body.response)

        # Compute rubrics
        reward = compute_system_reward(run_result, body.metadata)

        return BaseVerifyResponse(**body.model_dump(), reward=reward)
```

---

## 9. Experiment Plan

Run all experiments in this order:

| Experiment | Model config | Persona sets | Seeds | Rollouts |
|---|---|---|---|---|
| Baseline Sonnet | All 10 = Sonnet | set_01 to set_05 | 42, 43, 44 | 15 |
| Baseline Haiku | All 10 = Haiku | set_01 to set_05 | 42, 43, 44 | 15 |
| Mixed 50/50 | 5 Sonnet / 5 Haiku | set_01 to set_05 | 42, 43, 44 | 15 |
| **Total** | | | | **45 rollouts** |

Plus Approach 1 focal-agent runs:
| Experiment | Focal agent | Opponents | Persona sets | Seeds | Rollouts |
|---|---|---|---|---|---|
| Focal Sonnet | Sonnet | All Sonnet | set_01 to set_05 | 42, 43, 44 | 15 |
| Focal Haiku | Haiku | All Sonnet | set_01 to set_05 | 42, 43, 44 | 15 |

**Grand total: 75 rollouts.** At ~80 LLM calls per run, that's ~6,000 API calls. At Sonnet pricing, roughly $3–5 total.

---

## 10. Key Design Decisions

1. **NeMo Gym wraps the outside, not the inside.** The multi-agent peer simulation runs unchanged inside the Resources Server. NeMo Gym is the experiment runner, not the agent controller.

2. **Python 3.12 for `project_deal_nemogym/`.** The existing PoC stays at 3.10+. This is a new project with a new venv.

3. **OpenRouter as the model server.** Fully compatible with NeMo Gym's OpenAI-compatible endpoint support. Model swaps = one line change in `env.yaml`.

4. **Both approaches implemented.** Approach 1 (focal agent) gives clean individual benchmarks. Approach 2 (full peer marketplace) gives the Project Deal replication with the model advantage finding.

5. **Rubric weights are adjustable.** The weights in `verifiers.py` are parameters, not hardcoded. Different research questions may weight deal completion vs. price quality differently.

6. **Persona sets reused from the PoC.** The 5 frozen sets (`set_01.json` through `set_05.json`) are reused directly, giving continuity with earlier run findings.
