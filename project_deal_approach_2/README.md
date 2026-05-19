# Project Deal — Approach 2 (Full Peer Marketplace)

All 10 agents are LLM peers. NeMo Gym fires a single tool call per task; the Resources Server runs the full 10-agent simulation inside. Phase 1 produces the headline `advantage_ratio` metric.

See `docs/superpowers/specs/2026-05-15-approach-2-design.md` for the full design.

## Quickstart

```bash
cd /Users/ashijain/Documents/projectdealpoc/project_deal_approach_2
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env  # then fill in your OPENROUTER_API_KEY
```

## Phase 1 commands

```bash
python scripts/generate_private_fields.py
python tasks/generate_tasks.py --phase 1
bash scripts/run_experiment.sh phase_1
python analysis/compare.py --phase 1
```
