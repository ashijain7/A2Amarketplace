# Project Deal

A multi-agent marketplace simulation built on NVIDIA's NeMo Gym. One focal LLM agent is evaluated against 9 fixed-model opponents across three marketplace mechanics (money, reputation, barter) and five model configurations.

The full experiment matrix (5 configs × 3 phases × 5 persona sets = 75 rollouts) is documented in `docs/marketplace_guide.md`. The headline paper-narrative writeup is at `results/paper_runs/CROSS_CONFIG_COMPARISON.md`.

## Setup

```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync
```

Create a `.env` file with `OPENROUTER_API_KEY=...`, then copy `env.yaml.example` to `env.yaml` (the run scripts edit `env.yaml`'s `policy_model_name` automatically per config).

## Run one cell of the experiment

```bash
bash scripts/run_paper_config_phase.sh focal_G35_vs_X 2
```

Where the first argument is one of `focal_S_vs_S` (C1), `focal_S_vs_G` (C4), `focal_O_vs_G` (C6), `focal_G_vs_X` (C7), `focal_G35_vs_X` (C8), and the second is the phase (1, 2, or 3). See `docs/marketplace_guide.md §15` for the full run guide.

## Docs

- `docs/marketplace_guide.md` — complete walkthrough of the marketplace experiment (earlier phases: architecture, mechanics, run lifecycle)
- `docs/RUBRIC_GUIDE.md` — rubric formulas, weights, worked examples
- `docs/transaction_guide.md` — the transaction/settlement layer (payment, scammer, transactional-integrity rubric)
- `docs/ARCHITECTURE.md` — repo-layout overview and the 5 frozen persona sets
- `docs/nemogym-explained.md` — reference notes on the NeMo Gym framework
- `docs/papers/` — reference papers + planning notes (A2A, KDD, COLM, magentic-marketplace)
- `docs/archive/` — superseded design docs (settlement v1/v2, rubric drafts)
- `results/paper_runs/CROSS_CONFIG_COMPARISON.md` — the paper narrative across all 15 cells
