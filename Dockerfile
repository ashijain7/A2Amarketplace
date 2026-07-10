# syntax=docker/dockerfile:1
FROM python:3.12-slim

# system deps ng_run needs at RUN time: pgrep/pkill (procps), lsof, curl, bash, git, ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
      lsof procps curl bash git ca-certificates && rm -rf /var/lib/apt/lists/*

# uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
ENV UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app/project_deal

# ---- heavy, rarely-changing layer: engine 3rd-party deps BEFORE source ----
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
      uv venv --python 3.12 .venv && uv sync --no-install-project

# ---- source (busts on code change; deps layer above stays cached) ----
COPY . .
RUN mkdir -p nemo_gym_lib/cache

# ---- finish the 5 venvs (wheels come from the cache mount = fast rebuild) ----
# 1. engine: install the project + editable nemo_gym
RUN --mount=type=cache,target=/root/.cache/uv \
      uv sync && VIRTUAL_ENV="$PWD/.venv" uv pip install -e ./nemo_gym_lib
# 2. sim_ui
RUN --mount=type=cache,target=/root/.cache/uv \
      uv venv sim_ui/.venv && VIRTUAL_ENV="$PWD/sim_ui/.venv" uv pip install -r sim_ui/requirements.txt
# 3-5. subservers
RUN --mount=type=cache,target=/root/.cache/uv \
      for d in responses_api_models/openai_model responses_api_agents/simple_agent resources_servers/marketplace; do \
        ( cd "nemo_gym_lib/$d" && uv venv --seed --python 3.12 .venv && \
          VIRTUAL_ENV="$PWD/.venv" uv pip install -r requirements.txt ) ; done

ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f "http://127.0.0.1:${PORT}/api/health" || exit 1
CMD ["sh", "-c", "sim_ui/.venv/bin/python -m sim_ui.serve"]
