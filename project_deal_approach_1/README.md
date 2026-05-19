# Project Deal — Approach 1 (Focal Agent)

Phase 1 marketplace simulation. One focal LLM agent is evaluated against
9 fixed-model opponents inside a NeMo Gym Resources Server.

## Setup

    cd project_deal_approach_1
    uv venv --python 3.12
    source .venv/bin/activate
    uv sync

Set `OPENROUTER_API_KEY` in your shell, then copy `env.yaml.example` to
`env.yaml` and update the model names if needed.

## Generate personas

    python scripts/generate_private_fields.py

## Generate tasks

    python tasks/generate_tasks.py --phase 1

## Run

See `docs/superpowers/specs/2026-05-15-approach-1-design.md` section 11.
