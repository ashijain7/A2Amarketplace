# Project Deal

A multi-agent marketplace simulation built on NVIDIA's NeMo Gym. One focal LLM agent is evaluated against 9 fixed-model opponents across three marketplace mechanics (money, reputation, barter) and five model configurations.

The full experiment matrix (5 configs × 3 phases × 5 persona sets = 75 rollouts) is documented in `docs/EXPLAINED.md`. The headline paper-narrative writeup is at `results/paper_runs/CROSS_CONFIG_COMPARISON.md`.

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

Where the first argument is one of `focal_S_vs_S` (C1), `focal_S_vs_G` (C4), `focal_O_vs_G` (C6), `focal_G_vs_X` (C7), `focal_G35_vs_X` (C8), and the second is the phase (1, 2, or 3). See `docs/EXPLAINED.md §15` for the full run guide.

## Docs

- `docs/EXPLAINED.md` — complete project walkthrough
- `docs/RUBRIC_GUIDE.md` — rubric formulas, weights, worked examples
- `docs/ARCHITECTURE.md` — repo-layout overview and the 5 frozen persona sets
- `docs/nemogym-explained.md` — reference notes on the NeMo Gym framework
- `results/paper_runs/CROSS_CONFIG_COMPARISON.md` — the paper narrative across all 15 cells
