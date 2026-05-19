# NeMo Gym — Complete Reference

**Date:** 2026-05-15
**Relevant project:** `project_deal_nemogym/`

---

## 1. What NeMo Gym Is (One Line)

A framework from NVIDIA that lets you run an AI agent inside a controlled environment, score how well it does using your own rubrics, and collect those scored runs at scale — either for evaluation (comparing models) or for RL training (making a model better).

---

## 2. The Core Idea

NeMo Gym is built around one loop:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   TASK  ──►  AGENT  ──►  ENVIRONMENT  ──►  SCORE   │
│                               │                     │
│              ◄────────────────┘                     │
│           (agent sees result, acts again)           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

You define:
- **What the task is** (a JSONL file of scenarios)
- **What the environment is** (a FastAPI server you write)
- **How to score it** (a `verify()` function inside that server)

NeMo Gym handles the rest — running the loop, collecting results, scaling to thousands of parallel runs.

---

## 3. The Honest Distinction — NeMo Gym vs Project Deal

This matters a lot for understanding how we use it.

**What NeMo Gym natively expects:**

```
One policy LLM being tested
         │
         ▼
   Fixed environment
   (other agents are scripted, not LLMs)
         │
         ▼
   Verifier scores the policy
```

One model. One environment. One score. The environment doesn't change — only the model being tested does.

**What Project Deal actually is:**

```
10 LLM agents, all peers
Alice ◄──► Bob ◄──► Carol ◄──► Dave...

No fixed environment.
The other agents ARE the environment.
Everyone affects everyone.
```

These are different. NeMo Gym is not natively designed for a true multi-agent peer system. We use it as a **wrapper and scorer** — our full marketplace simulation runs inside NeMo Gym's Resources Server, and NeMo Gym handles experiment management and scoring on the outside.

---

## 4. Setup

### 4.1 Prerequisites

| Requirement | Detail |
|---|---|
| Python | 3.12+ (NeMo Gym requires this — note our existing PoC uses 3.10+) |
| Package manager | `uv` |
| Git | For cloning the repo |
| API key | OpenRouter (already have this) — OpenAI-compatible, works out of the box |
| GPU | Not required for the library itself |
| RAM | 8 GB minimum, 16 GB recommended |
| OS | Linux, macOS (Intel/Apple Silicon), Windows WSL2 |

---

### 4.2 Installation

```bash
git clone git@github.com:NVIDIA-NeMo/Gym.git
cd Gym
uv venv --python 3.12
source .venv/bin/activate
uv sync
```

That's it. No CUDA, no GPU setup needed for evaluation runs.

---

### 4.3 Model Configuration (`env.yaml`)

Create this file in the project root. This is the **only file you change when swapping models**:

```yaml
policy_base_url: https://openrouter.ai/api/v1
policy_api_key: your_openrouter_key_here
policy_model_name: anthropic/claude-sonnet-4-5
```

To compare with Haiku — change one line:
```yaml
policy_model_name: anthropic/claude-haiku-4-5
```

NeMo Gym works with any OpenAI-compatible endpoint. OpenRouter qualifies.

---

## 5. The 3-Server Architecture

When you run `ng_run`, three local servers start simultaneously:

```
┌────────────────────────┐  one tool call   ┌──────────────────────────────┐
│   AGENT SERVER         │ ───────────────► │   RESOURCES SERVER           │
│   (NeMo Gym built-in)  │ ◄─────────────── │   (YOU write this)           │
│                        │  result back     │                              │
│   - Reads task JSONL   │                  │   - FastAPI app              │
│   - Sends task to      │                  │   - Exposes tool endpoints   │
│     Resources Server   │                  │   - Runs your simulation     │
│   - Calls verify()     │                  │   - Has verify()             │
│   - Saves output JSONL │                  │                              │
└────────────────────────┘                  └──────────────────────────────┘
           │
           │ LLM calls (only used in Approach 1 — focal agent mode)
           ▼
┌────────────────────────┐
│   MODEL SERVER         │
│   (OpenRouter)         │
│   set in env.yaml      │
└────────────────────────┘
```

**Important:** For our Approach 2 (full peer marketplace), the Agent Server just fires one trigger — `run_marketplace` — and waits. All 10 agent LLM calls happen inside the Resources Server, going directly to OpenRouter from inside your Python code. The NeMo Gym Model Server is not in the loop for Approach 2.

---

## 6. The 4 Building Blocks

Every NeMo Gym setup has four parts. Once you understand these, everything else makes sense.

---

### Block 1 — Tasks

A JSONL file. Each line = one scenario sent to the environment.

```json
{
  "responses_create_params": {
    "input": [{"role": "user", "content": "Run marketplace: persona_set=set_01, model_config=all_sonnet, seed=42"}],
    "tools": [{
      "type": "function",
      "name": "run_marketplace",
      "description": "Run the full multi-agent marketplace simulation",
      "parameters": {
        "type": "object",
        "properties": {
          "persona_set":   {"type": "string"},
          "model_config":  {"type": "string"},
          "seed":          {"type": "integer"}
        },
        "required": ["persona_set", "model_config", "seed"]
      }
    }]
  },
  "metadata": {
    "persona_set": "set_01",
    "model_config": "all_sonnet",
    "seed": 42,
    "expected_possible_deals": 8
  }
}
```

Each line is independent. NeMo Gym can run them in parallel.

---

### Block 2 — Resources Server

The environment. A FastAPI app you write. It has:

1. **Tool endpoints** — functions the agent can call
2. **verify()** — the rubric that scores the run and returns a float

```python
class MarketplaceResourcesServer(SimpleResourcesServer):

    def setup_webserver(self) -> FastAPI:
        app = super().setup_webserver()
        app.post("/run_marketplace")(self.run_marketplace)
        return app

    async def run_marketplace(self, body: RunMarketplaceRequest) -> RunMarketplaceResponse:
        # Your full marketplace simulation runs here
        # channel.py, ledger.py, scheduler.py, agent.py — all imported
        result = run_full_simulation(
            persona_set=body.persona_set,
            model_config=body.model_config,
            seed=body.seed
        )
        return RunMarketplaceResponse(result=result)

    async def verify(self, body: MarketplaceVerifyRequest) -> BaseVerifyResponse:
        run_result = extract_result(body.response)
        reward = compute_reward(run_result, body.metadata)
        return BaseVerifyResponse(**body.model_dump(), reward=reward)
```

---

### Block 3 — The Agent

The thing being run or tested. For Approach 2 (full marketplace), the "agent" is just a dummy trigger — it fires `/run_marketplace` once and gets the full result back.

For Approach 1 (focal agent), the agent is the policy LLM set in `env.yaml`. It makes multiple tool calls, one per negotiation action.

---

### Block 4 — Verifiers

The rubric. The `verify()` function receives the **entire conversation history** — every tool call made, every response, all outcomes — and returns a float between 0.0 and 1.0.

This is where your evaluation logic lives. No verifier = no comparable numbers. With a verifier = you can run 1000 configurations and rank them automatically.

---

## 7. Running an Experiment

```bash
# Terminal 1 — start all servers
ng_run "+config_paths=[resources_servers/marketplace/configs/marketplace.yaml,responses_api_models/openai_model/configs/openai_model.yaml]"

# Terminal 2 — collect rollouts
ng_collect_rollouts \
  +agent_name=marketplace_agent \
  +input_jsonl_fpath=tasks/marketplace_tasks.jsonl \
  +output_jsonl_fpath=results/sonnet_rollouts.jsonl \
  +limit=10 \
  +num_repeats=3   # run each task 3 times for statistical reliability
```

**Key flags for `ng_collect_rollouts`:**

| Flag | What it does |
|---|---|
| `+limit` | How many tasks from the JSONL to run |
| `+num_repeats` | How many times to repeat each task |
| `+num_samples_in_parallel` | Run this many tasks at the same time |
| `+max_output_tokens` | Cap on LLM output length |
| `+temperature` | LLM temperature for the policy model |

**Output:** Each line in `output_jsonl_fpath` = one full run + reward score + complete tool call history.

---

## 8. Two Approaches — How Each Uses NeMo Gym

---

### Approach 1: One Focal Agent, Swap the Model

**The question it answers:** "How well does model X negotiate as an individual participant?"

**Setup:**
- One persona (index 0 in the set) becomes the **focal agent** — the policy LLM set in `env.yaml`
- The other 9 agents run inside the Resources Server with a fixed model (Sonnet as baseline)
- The focal agent makes tool calls — one per action: `make_offer`, `accept_offer`, etc.
- The Resources Server processes each action, runs the affected opponent agents, returns updated state
- At the end, `verify()` scores the focal agent only

**How the data flows:**

```
Task: "You are Alice (persona index 0). Marketplace state: [...]"
        │
        ▼
NeMo Gym Agent Server calls policy LLM (env.yaml model)
        │
LLM decides: make_offer to Bob, $40
        │
        ▼
Resources Server receives: POST /make_offer
- Records offer in channel
- Runs Bob's LLM turn internally (Bob is inside the server)
- Bob counters at $43
- Returns updated state to Alice
        │
        ▼
LLM decides: accept_offer at $43
        │
        ▼
Resources Server: deal sealed, updates ledger
        │
... continues until Alice is done or max turns hit
        │
        ▼
verify() scores Alice's full trajectory → reward: 0.74
```

**To compare models:**
Change `policy_model_name` in `env.yaml`. Run `ng_collect_rollouts` again. Same task, same opponents, different model. Scores are directly comparable.

**Model config values for Approach 1:**
```
focal_sonnet  → persona[0] = claude-sonnet-4-5, all others = claude-sonnet-4-5
focal_haiku   → persona[0] = claude-haiku-4-5,  all others = claude-sonnet-4-5
```

---

### Approach 2: Full Peer Marketplace, All Agents Running

**The question it answers:** "What emerges when all agents are peers? Do stronger models extract disproportionate value?"

**This is the Project Deal replication.**

**Setup:**
- ALL 10 agents run as LLM peers inside the Resources Server
- The NeMo Gym Agent Server fires exactly **one tool call** — `run_marketplace`
- The Resources Server runs the full simulation (your existing scheduler.py, all agents as LLMs)
- `verify()` scores the aggregate outcome of the whole run

**How the data flows:**

```
Task: "Run marketplace: persona_set=set_01, model_config=mixed, seed=42"
        │
        ▼
NeMo Gym Agent Server fires: POST /run_marketplace
        │
        ▼
Resources Server runs FULL simulation:
  - Loads persona set
  - Assigns models per model_config
  - Runs scheduler: picks agent → LLM call → records action → next agent → ...
  - All LLM calls go directly to OpenRouter from inside the server
  - Continues until done or max turns
  - Returns: deals, channel log, per-agent gains, turns used
        │
        ▼
verify() receives the full result → computes system-level scores → reward: 0.71
```

**Model config values for Approach 2:**
```
all_sonnet  → all 10 agents use claude-sonnet-4-5
all_haiku   → all 10 agents use claude-haiku-4-5
mixed       → persona[0–4] get claude-sonnet-4-5
              persona[5–9] get claude-haiku-4-5
              (deterministic split, not random — keeps results reproducible)
```

---

## 9. Rubrics (Verifiers)

### Approach 1 Rubrics — Individual Agent Score

Applied to the focal agent's trajectory. Answers: "How well did this agent negotiate?"

---

**Rubric 1 — Deal Completion Rate** | Weight: 35%

Did the focal agent close everything it needed to?

```python
score = deals_closed / (items_to_sell + items_to_buy)
# 0.0 = closed nothing
# 1.0 = closed everything
```

---

**Rubric 2 — Seller Price Quality** | Weight: 25%

For items sold, how close to the ceiling (best possible price) did the agent get?

```python
score = (price_received - floor_price) / (ceiling_price - floor_price)
# 0.0 = sold at floor (worst — just above minimum)
# 1.0 = sold at ceiling (best — maximum possible)
# Averaged across all items sold
```

---

**Rubric 3 — Buyer Price Quality** | Weight: 20%

For items bought, how much below budget did the agent pay?

```python
score = (budget - price_paid) / budget
# 0.0 = paid the full budget (worst)
# Higher = paid less, saved more
```

---

**Rubric 4 — Turn Efficiency** | Weight: 15%

How many turns did the agent use? A decisive agent closes faster.

```python
score = 1 - (focal_agent_turns_used / max_turns_allowed)
# 0.0 = dragged on to the last turn (indecisive)
# 1.0 = finished immediately (unrealistic but best case)
```

---

**Rubric 5 — Constraint Compliance** | Weight: 5%

Did the agent ever go below floor price as a seller, or above budget as a buyer?

```python
score = 1.0  # no violations
score = 0.0  # any violation occurred
# Binary. A model that breaks constraints is not a trustworthy negotiating agent.
```

---

**Combined Score:**
```python
final_reward = (
    0.35 * deal_completion_rate  +
    0.25 * seller_price_quality  +
    0.20 * buyer_price_quality   +
    0.15 * turn_efficiency       +
    0.05 * constraint_compliance
)
# Weights are adjustable parameters in verifiers.py — not hardcoded.
```

---

**Example model comparison output:**

| | Deal rate | Seller price | Buyer price | Turns | Final reward |
|---|---|---|---|---|---|
| Alice (Sonnet) | 1.0 | 0.87 | 0.40 | 0.80 | **0.82** |
| Alice (Haiku) | 0.5 | 0.37 | 0.14 | 0.60 | **0.45** |

*Numbers above are illustrative examples, not actual run results.*

---

### Approach 2 Rubrics — System Level Score

Applied to the full marketplace run. Answers: "How well did the whole marketplace perform? Did model strength create unfair outcomes?"

---

**Rubric 1 — Market Closure Rate**

Of all deals that COULD have happened, what percentage actually closed?

A **possible deal** = at least one agent has item X listed at or below their ceiling, AND at least one other agent has item X in their wants with a budget >= the seller's floor. Same definition as in the existing PoC's `analyze.py`.

```python
score = deals_sealed / possible_deals
# 0.0 = no trades at all
# 1.0 = every possible trade completed
```

---

**Rubric 2 — Average Price Surplus Per Deal**

For each closed deal, how much total value was created? Surplus = seller's gain above floor + buyer's saving below budget.

```python
surplus_per_deal = (price_sealed - seller_floor) + (buyer_budget - price_sealed)
score = mean(surplus_per_deal across all deals) / theoretical_max_surplus
# High score = agents found good prices for both sides
# Low score = value left on the table or deals closed at bad prices
```

---

**Rubric 3 — Model Advantage Score** *(the Project Deal headline finding)*

In mixed runs, do Sonnet agents extract more value than Haiku agents from the same marketplace?

```python
# Per-agent value extracted (gain = value above minimum they could have accepted):
agent_gain = sum(price_sold - floor_price for each item sold)
           + sum(budget - price_paid for each item bought)

sonnet_avg_gain = mean(agent_gain for all Sonnet agents in the run)
haiku_avg_gain  = mean(agent_gain for all Haiku agents in the run)

advantage_ratio = sonnet_avg_gain / haiku_avg_gain
# 1.0 = perfectly equal — model strength gave no advantage
# 2.0 = Sonnet extracted twice as much value as Haiku
# Only meaningful in mixed runs — in all_sonnet or all_haiku runs, set to N/A
```

This metric directly replicates Project Deal's **invisible disadvantage** finding — the observation that Opus agents extracted more value than Haiku agents even when negotiating as peers.

---

**Rubric 4 — Negotiation Speed**

Average number of turns from first offer to deal sealed, across all deals in the run.

```python
speed = mean(turns_to_close for each sealed deal)
# Lower = more decisive agents reaching agreement faster
# Higher = more back-and-forth, more passes, slower convergence
```

---

**Rubric 5 — Fairness Score (Gini Coefficient)**

How unequal is value distribution across all agents in the run?

```python
gains = [agent_gain for each agent in the run]
gini = gini_coefficient(gains)
# 0.0 = perfectly equal — every agent extracted the same value
# 1.0 = completely unequal — one agent took everything

# In mixed runs: a rising Gini means Sonnet agents are
# systematically extracting more than Haiku agents.
# The marketplace is structurally unfair by model capability.
```

---

**Example full comparison table (illustrative, not actual results):**

| Run config | Closure rate | Avg surplus | Sonnet gain | Haiku gain | Advantage ratio | Speed |
|---|---|---|---|---|---|---|
| All Sonnet | 0.85 | $28 | $32 | — | N/A | 4.2 turns |
| Mixed 50/50 | 0.72 | $19 | $30 | $14 | **2.1x** | 7.8 turns |
| All Haiku | 0.55 | $11 | — | $13 | N/A | 11.3 turns |

The **advantage ratio in the mixed run** is the headline number. It answers whether model capability creates unfair outcomes in a peer marketplace — the same question Project Deal asked with 69 real humans.

---

## 10. Full Experiment Plan

### Approach 2 Runs (Full Peer Marketplace)

| Experiment | Model config | Persona sets | Seeds | Rollouts |
|---|---|---|---|---|
| Baseline Sonnet | all_sonnet | set_01 → set_05 | 42, 43, 44 | 15 |
| Baseline Haiku | all_haiku | set_01 → set_05 | 42, 43, 44 | 15 |
| Mixed 50/50 | mixed | set_01 → set_05 | 42, 43, 44 | 15 |
| **Subtotal** | | | | **45** |

### Approach 1 Runs (Focal Agent)

| Experiment | Focal model | Opponents | Persona sets | Seeds | Rollouts |
|---|---|---|---|---|---|
| Focal Sonnet baseline | Sonnet | All Sonnet | set_01 → set_05 | 42, 43, 44 | 15 |
| Focal Haiku test | Haiku | All Sonnet | set_01 → set_05 | 42, 43, 44 | 15 |
| **Subtotal** | | | | | **30** |

**Grand total: 75 rollouts.**

At ~80 LLM calls per run × 75 runs = ~6,000 API calls.
At Sonnet pricing on OpenRouter: roughly **$3–5 for the full experiment set.**

---

## 11. File Structure for `project_deal_nemogym/`

```
project_deal_nemogym/
│
├── env.yaml                    # policy_base_url, policy_api_key, policy_model_name
├── pyproject.toml              # Python 3.12, nemo_gym as dependency
│
├── resources_server/
│   ├── app.py                  # The Resources Server — marketplace engine + verify()
│   ├── verifiers.py            # All 10 rubric functions (5 per approach)
│   ├── model_config.py         # Maps config name → per-agent model assignments
│   │                           # Valid values:
│   │                           #   all_sonnet   → all 10 = claude-sonnet-4-5
│   │                           #   all_haiku    → all 10 = claude-haiku-4-5
│   │                           #   mixed        → persona[0–4]=sonnet, [5–9]=haiku
│   │                           #   focal_sonnet → persona[0]=sonnet, rest=sonnet
│   │                           #   focal_haiku  → persona[0]=haiku,  rest=sonnet
│   └── configs/
│       └── marketplace.yaml    # ng_run config — tells NeMo Gym how to start this server
│
├── tasks/
│   ├── generate_tasks.py       # Generates marketplace_tasks.jsonl from persona sets
│   └── marketplace_tasks.jsonl # 45 tasks (5 sets × 3 configs × 3 seeds)
│
├── results/                    # Output rollouts — one file per experiment batch
│   ├── all_sonnet_rollouts.jsonl
│   ├── mixed_rollouts.jsonl
│   ├── all_haiku_rollouts.jsonl
│   ├── focal_sonnet_rollouts.jsonl
│   └── focal_haiku_rollouts.jsonl
│
├── analysis/
│   └── compare.py              # Reads results/, prints the comparison tables
│
└── marketplace/                # Core simulation code — imported from existing PoC
    ├── channel.py
    ├── ledger.py
    ├── agent.py
    ├── scheduler.py
    ├── build_agents.py
    ├── llm.py
    └── personas/               # The 5 frozen persona sets (set_01 through set_05)
```

The `marketplace/` folder reuses existing PoC code directly. No rewrite of the simulation logic.

---

## 12. What NeMo Gym Gives Us vs What We Already Had

| | Existing PoC | With NeMo Gym |
|---|---|---|
| Run the simulation | ✅ | ✅ (same code, inside Resources Server) |
| Repeat runs with same settings | Manual | `+num_repeats=3` flag |
| Structured output per run | `data/runs/` archive | Standardized JSONL rollout format |
| Score each run with rubrics | ❌ | ✅ `verify()` returns reward float |
| Compare models directly | Manual analysis | Same tasks → different `env.yaml` → compare rewards |
| Run many in parallel | ❌ | `+num_samples_in_parallel` |
| RL training pipeline ready | ❌ | ✅ rollout format feeds NeMo RL / VeRL directly |

---

## 13. Key Facts to Remember

- **Python 3.12 required** — NeMo Gym strictly requires this. The existing PoC stays at 3.10+. New project uses a separate venv.
- **OpenRouter is fully compatible** — it's an OpenAI-compatible endpoint. Set it in `env.yaml`. Done.
- **The simulation runs unchanged inside the Resources Server** — `channel.py`, `ledger.py`, `scheduler.py` are imported as-is. NeMo Gym wraps around them.
- **Approach 2 fires one tool call** — the NeMo Gym agent triggers `/run_marketplace` once. The full 10-agent simulation happens inside. NeMo Gym's LLM policy loop is not involved.
- **Approach 1 uses the policy loop** — the focal agent makes multiple tool calls (one per negotiation action). The Model Server / `env.yaml` model is the focal agent.
- **Rubric weights are parameters** — defined in `verifiers.py`, not hardcoded. You can reweight based on what you're studying.
- **Mixed model config is deterministic** — persona[0–4] always get Sonnet, persona[5–9] always get Haiku. Not random. This keeps results reproducible across seeds.
- **NeMo Gym is early development** — APIs evolve. Lock to a specific commit when building to avoid surprise breakage.
