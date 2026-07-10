# Docker Packaging (Step 4) — Design

**Date:** 2026-07-10
**Status:** approved (brainstorm), ready for implementation plan
**Scope:** `Dockerfile` + `.dockerignore` + `.env.example` so the platform (or anyone) can
`docker build` then `docker run` the project_deal marketplace box on any OS. **Do NOT touch**
`resources_server/verifiers.py`, the engine, or the rubrics. Nothing committed (standing directive).

---

## 1. Goal & non-goals

**Goal.** One `docker build` produces a self-contained image whose `docker run` serves the marketplace UI
+ reward doors on `$PORT`; a run spawns the full NeMo Gym stack **inside the same container**. The build is
deterministic and works on fresh Linux (it rebuilds every venv from scratch).

**Non-goals.**
- No engine / rubric / verifiers change.
- No RLEaaS-side wiring (env-var injection, connector, tile) — that's Step 6.
- No paid end-to-end live run in CI — deferred to the user (costs OpenRouter credit).
- No multi-stage size optimization for v1 (single stage; image is large by nature — 5 venvs + Ray).

---

## 2. What runs where (why 5 venvs, why no Ray at build)

The container hosts one long-lived web process that spawns the engine stack on demand:

```
docker run  →  CMD: sim_ui/.venv/bin/python -m sim_ui.serve   (PID 1, binds $PORT — UI + reward doors)
                     │  a run (via /run_live or /api/run) spawns:
                     └─ adapter.py (engine .venv) → restart_ng_run.sh → ng_run
                            └─ Ray launches 3 NeMo Gym servers, each in its OWN venv (port 11000 / 8765, internal)
```

**Five venvs**, all built at image-build time:
1. `.venv` (engine) — adapter.py + `marketplace/` + `resources_server/`; `uv sync` + editable `nemo_gym_lib`.
2. `sim_ui/.venv` — the web server (FastAPI + uvicorn + gradio + pillow). **Kept separate** because gradio's
   deps downgrade `starlette` and break the ng_run FastAPI stack — the split is mandatory, not cosmetic.
3–5. the 3 NeMo Gym subserver venvs (`responses_api_models/openai_model`,
   `responses_api_agents/simple_agent`, `resources_servers/marketplace`) — **NeMo Gym's own architecture**
   runs each server as a separate process with its own venv.

**No Ray at build.** Building a venv is pure dependency install (`uv venv` + `uv pip install`) — no servers,
no ports, no `/dev/shm`. Ray only launches at RUN time when an actual rollout starts. Booting ng_run at build
was considered and rejected (fragile: Ray in a build sandbox can fail the image build). Because
`skip_venv_if_present` is enabled, ng_run's first boot inside the container **skips** venv setup (the venvs are
already baked) → fast, offline first run.

---

## 3. Dockerfile (single stage, BuildKit — optimized for FAST REBUILDS)

Rebuild speed (not size) is the priority: **BuildKit `uv` cache mounts** (wheels persist across builds, outside
the image) + **layer ordering** (heavy deps installed before source, so a code edit doesn't re-run the multi-GB
dep install). See §3a for the caching rationale.

```
# syntax=docker/dockerfile:1
FROM python:3.12-slim
# system deps ng_run needs at RUN time: pgrep/pkill (procps), lsof, curl, bash, git, ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
      lsof procps curl bash git ca-certificates && rm -rf /var/lib/apt/lists/*
# uv (pinned) — installer method + version firmed at build-test
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
ENV UV_CACHE_DIR=/root/.cache/uv
WORKDIR /app/project_deal

# ---- heavy, rarely-changing layer: engine 3rd-party deps BEFORE source ----
# copy only the manifests so this layer caches unless deps change
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
      uv venv --python 3.12 .venv && uv sync --no-install-project

# ---- now the source (busts on any code change, but deps above stay cached) ----
COPY . .
RUN mkdir -p nemo_gym_lib/cache       # egg_base needs the dir for the editable build

# ---- finish the 5 venvs (wheels come from the cache mount = fast on rebuild) ----
# 1. engine: install the project itself + editable nemo_gym
RUN --mount=type=cache,target=/root/.cache/uv \
      uv sync && VIRTUAL_ENV="$PWD/.venv" uv pip install -e ./nemo_gym_lib
# 2. sim_ui
RUN --mount=type=cache,target=/root/.cache/uv \
      uv venv sim_ui/.venv && VIRTUAL_ENV="$PWD/sim_ui/.venv" uv pip install -r sim_ui/requirements.txt
# 3-5. subservers (each from its own dir; relative editables in requirements.txt resolve from there)
RUN --mount=type=cache,target=/root/.cache/uv \
      for d in responses_api_models/openai_model responses_api_agents/simple_agent resources_servers/marketplace; do \
        ( cd "nemo_gym_lib/$d" && uv venv --seed --python 3.12 .venv && \
          VIRTUAL_ENV="$PWD/.venv" uv pip install -r requirements.txt ) ; done

ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f "http://127.0.0.1:${PORT}/api/health" || exit 1
CMD ["sh", "-c", "sim_ui/.venv/bin/python -m sim_ui.serve"]
```

Notes:
- `sim_ui.serve` already reads `PORT` (`serve._port()` from B1). `ENV PORT=8000` is the standalone default;
  RLEaaS overrides with `-e PORT`.
- The exact `uv` install line + version pin is firmed at build-test (installer vs `pip install uv`).
- `build-essential` added ONLY if a wheel fails to build on slim (decided at build-test).
- **No `uv cache clean`** — the cache mount is not an image layer, so it keeps the image lean AND makes rebuilds
  fast; cleaning would wipe the cross-build wheel cache.
- If `uv sync --no-install-project` behaves unexpectedly for this project, the fallback is a single
  `uv venv && uv sync` after the source copy (still cache-mounted) — resolved at build-test.

## 3a. Build-caching rationale (rebuild-again-and-again = fast)

- **`uv` cache mount** (`--mount=type=cache,target=/root/.cache/uv`, with `UV_CACHE_DIR` pointed there): the slow
  part is DOWNLOADING wheels (torch/ray/pyarrow, GBs). The cache mount persists them across builds and is NOT
  baked into the image. So even when a source edit invalidates a venv-build layer, uv reinstalls from local
  cached wheels — no re-download.
- **Layer ordering** (manifests → `uv sync --no-install-project` → source → editable installs): the heavy
  3rd-party dep layer is keyed only on `pyproject.toml`/`uv.lock`, so ordinary code edits leave it cached and
  only the fast editable step re-runs.
- **Multi-stage is NOT used.** It mainly reduces size (a non-goal here) and our **editable** installs bake
  absolute `.pth` paths (`-e ./nemo_gym_lib`, `-e ../../`) that break if venvs are copied between stages at a
  different path. Cache mounts deliver the rebuild-speed win in a single stage without that risk. Multi-stage
  size-slimming stays an optional later pass (§9).
- **Build requires BuildKit** (default in Docker 29.0.0 here). Command: `DOCKER_BUILDKIT=1 docker build ...`
  (or plain `docker build` — BuildKit is default in modern Docker).

---

## 4. Secrets — never baked

- `.dockerignore` excludes `.env`. No secret enters the image.
- At run time: `docker run -e OPENROUTER_API_KEY=... -e PORT=... [-e RLEAAS_CALLBACK_URL -e RLEAAS_TOKEN -e RLEAAS_ENV_NAME] image`.
- `marketplace/config.py::load_dotenv()` and `restart_ng_run.sh` both tolerate a missing `.env` (verified) →
  env vars supplied by `docker run` are used directly.
- **Cached UI needs no key.** Only live runs need `OPENROUTER_API_KEY`.

---

## 5. `.dockerignore`

Exclude (host junk / secrets / machine-specific / runtime scratch):
```
.env
env.yaml            # holds policy/judge api keys; regenerated at runtime — leak vector + dead weight
**/.venv
.git
**/__pycache__
*.pyc
results/adapter_runs
results/smoke
outputs
data/ng_run
data/ng_run_live
nemo_gym_lib/build
nemo_gym_lib/cache/*
.superpowers
```
KEEP (needed in the image): `results/paper_runs` (cached-mode source), `data/item_images` (swap photos),
`sim_ui/web/episodes.json` (cached data), the 3 subserver `requirements.txt`, `uv.lock`, `env.yaml.example`.

---

## 6. `.env.example`

```
# Required for LIVE runs (OpenRouter). Cached UI needs nothing.
OPENROUTER_API_KEY=

# Injected by the RLEaaS platform at runtime (Step 6) — leave blank locally.
RLEAAS_CALLBACK_URL=
RLEAAS_TOKEN=
RLEAAS_ENV_NAME=project_deal_marketplace

# UI port. RLEaaS injects $PORT; local default is 8000.
# PORT=8000
```

---

## 7. Testing (the build IS the from-scratch test)

- **`docker build -t project-deal-marketplace .` succeeding = the test** — all 5 venvs build clean on fresh
  Linux (the whole point of Step 4: catches a Mac-only wheel or bad pin at build, visibly).
- Smoke `docker run -p 8000:8000 project-deal-marketplace`, then:
  - `GET /` → 200 (static UI loads; cached mode works with **no key**).
  - `GET /api/health` → `{"status":"ok"}`.
- **Paid live check deferred to the user:** a real `POST /api/run` (or `/run_live`) boots ng_run + runs a
  rollout inside the container = OpenRouter credit.
- `docker` 29.0.0 IS available on this box and `/` has ~121G free → the real build-test runs locally.

---

## 8. Flagged risks (integrate-time, not blockers)

- **Ray `/dev/shm`:** a **container** defaults to 64MB shm regardless of host (this box's host has 109G, but
  that doesn't reach the container), which can be tight for Ray; RLEaaS's `docker run` shm-size is unknown.
  Mitigation: `--shm-size` at run (we pass it for our own paid smoke), or a Ray object-store cap env — decided
  at integrate-time.
- **Image size = 5.68GB** (actual, measured after build; earlier ~4.3G estimate was low): COPY context **223M** (the 2.5G `nemo_gym_lib/cache` is already
  `.dockerignore`d), venvs **~3.85G**, base+apt ~250M, after `uv cache clean`. Disk ample (`/` ~121G free), so not
  disk-constrained — but a 4.3G image means slow build (downloads GBs) + slow registry push/pull for RLEaaS.
  Per-subserver venv (~800M) = `ray 190M + pyarrow 149M` (needed) + `wandb 83M + mlflow 49M + fontTools 21M`
  (dev/experiment-tracking, unused at runtime), installed ×4 by `nemo-gym[dev]`.
- **First live `/api/run` blocks ~11s** while ng_run boots — RLEaaS's proxy must tolerate the wait (the
  blocking-door decision from B1).
- **Runtime user:** runs as root for v1 (simplest); revisit if RLEaaS mandates non-root.

---

## 9. Open items (tracked, not blocking)

- Pin the exact `uv` install method + version in the Dockerfile at build-test.
- Confirm slim has every wheel; add `build-essential` only if a build fails.
- Verify the final image size and whether `results/paper_runs` can be trimmed (cached UI actually reads
  `sim_ui/web/episodes.json`, not `paper_runs`, at serve time — trimming is a size optimization for later).
- **Image slimming (deferred):** dropping `[dev]` from the subserver installs (`nemo-gym` instead of
  `nemo-gym[dev]`) would save ~600M–1G (wandb/mlflow/fontTools ×4), but `requirements.txt` pins `[dev]` and boot
  code may import those — needs a build+boot test before changing. Multi-stage builds could also dedup, later.
