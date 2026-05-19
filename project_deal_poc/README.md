# Project Deal PoC

A small, faithful replication of Anthropic's December 2025 **Project Deal**
experiment: autonomous AI agents representing simulated "humans" in a shared
marketplace, negotiating and closing deals with zero human intervention.

This is a **proof of concept**, not a production system. It exists to
demonstrate the mechanical core of agent-to-agent commerce: that LLM agents
given different system prompts can find each other in a shared channel,
exchange offers in natural language, and reach binding agreements.

## What this replicates from Project Deal

| Project Deal | This PoC |
| ---- | ---- |
| 69 Anthropic employees | 6 fictional personas (you can change `--n-personas`) |
| 10-minute Claude interview | One `interview.py` call that invents the personas |
| Custom system prompt per person | Same — `build_agents.py` slots persona into a template |
| Slack channel for negotiation | A local `channel.jsonl` file (append-only, auditable) |
| Random-loop scheduler | Same — `scheduler.py` picks an active agent at random each turn |
| Binding deals, no human override | Same — sealed deals go to `deals.json` |
| Floor / ceiling price constraints | Same — enforced by the scheduler before sealing |
| 4 parallel runs (A/B/C/D) | Single run for the PoC; trivially extensible |

## What this does **not** replicate

- Real humans (the personas are LLM-generated)
- Real money or real goods (it's all in JSON)
- Many-buyer-one-seller auction dynamics (small N means fewer collisions)
- The full Opus-vs-Haiku invisible-disadvantage study (one-line model swap if
  you want to try it)

## Setup

1. **Install dependencies** (Python 3.10+):
   ```bash
   pip install -r requirements.txt
   ```

2. **Get an OpenRouter API key** at https://openrouter.ai and add it to a
   `.env` file in the project root:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
   (See `.env.example`.)

3. **Run it**:
   ```bash
   # From the parent directory of project_deal_poc/
   python -m project_deal_poc.run --regenerate-personas
   ```

   This will:
   - Generate 6 fictional personas with Claude
   - Build a system prompt for each
   - Run the marketplace loop (default 60 turns max)
   - Save the transcript and deals to `project_deal_poc/data/`

4. **See what happened**:
   ```bash
   python -m project_deal_poc.analyze
   ```

## File layout

```
project_deal_poc/
├── config.py              # paths, model names, constants
├── llm.py                 # OpenRouter API wrapper + JSON parsing
├── interview.py           # generates personas via Claude
├── build_agents.py        # turns personas into system prompts
├── channel.py             # the JSONL channel (append-only log)
├── ledger.py              # closed deals + sold-item tracking
├── agent.py               # single agent turn logic
├── scheduler.py           # marketplace loop, validation, deal sealing
├── run.py                 # main entry point (orchestrates everything)
├── analyze.py             # post-run summary
├── prompts/
│   ├── interviewer.txt    # system prompt for persona generation
│   └── agent_template.txt # system prompt template for marketplace agents
└── data/                  # written at runtime
    ├── personas.json      # the 6 personas
    ├── channel.jsonl      # the full marketplace transcript
    └── deals.json         # closed deals
```

## Useful command flags

```bash
# Generate fresh personas instead of reusing existing ones
python -m project_deal_poc.run --regenerate-personas

# Try the same run with a weaker model — Project Deal's "Haiku" angle
python -m project_deal_poc.run --model anthropic/claude-haiku-4.5

# Reproducible run (same scheduler order)
python -m project_deal_poc.run --seed 42

# Bigger marketplace
python -m project_deal_poc.run --regenerate-personas --n-personas 8 --max-turns 80
```

## How a turn works

Every turn the scheduler:

1. Picks a random agent that still has business to do.
2. Builds a human-readable summary of the marketplace state from that
   agent's perspective (its own items + wants, others' active listings,
   open offers on its listings, recent messages, closed deals).
3. Calls the LLM with the agent's system prompt + that summary.
4. Parses the agent's response, which must be a single JSON object with
   an `action`, `target`, `price`, and `message`.
5. Validates the action against the channel and ledger (e.g., can't accept
   an already-sold item, can't sell below floor, can't offer on your own
   listing).
6. If the action seals a deal, both items are marked sold and the deal is
   recorded.

This loop runs until everyone is done, the channel stalls, or `--max-turns`
is hit.

## Cost estimate

A typical run with 6 agents and default settings on Claude Sonnet 4.5 is
60-80 LLM calls of roughly 2-3K tokens each. At Sonnet pricing this is
well under $1 per full run. Haiku is much cheaper.

## Honest known limitations

- **Description matching is loose.** Buyer `description` fields aren't tightly
  matched to seller `name` fields — we just track the buyer's highest open
  ceiling and use it for floor/ceiling checks. For 6 agents this is fine;
  for larger runs you'd want semantic matching.
- **No reputation, no memory across runs.** Each marketplace run is fresh.
- **No tie-breaking between simultaneous offers.** The seller agent itself
  decides which offer to accept on its turn, which is the same as Project
  Deal but does mean a slow seller can miss out.
- **Claude sometimes outputs malformed JSON.** The parser tolerates common
  quirks (markdown fences, prose around the object); truly broken responses
  are treated as a pass on that turn.

## Where to take it next

If you want to extend the PoC, the most natural next steps:

1. **Run 4 parallel marketplaces with the same personas**, exactly like
   Project Deal's A/B/C/D design. Each is just another `run_marketplace()`
   call with a different model mix.
2. **Mix models in a single run** — pass per-agent model assignments to
   the scheduler instead of a single `model` argument.
3. **Compare prices on identical items across runs** — your own miniature
   "invisible disadvantage" experiment.
4. **Add a "post-experiment survey" call** where each agent rates how fair
   its deals felt, replicating Project Deal's 1-7 fairness rating.
5. **Port to LangGraph** as a learning exercise once you understand the
   plain-Python version.
