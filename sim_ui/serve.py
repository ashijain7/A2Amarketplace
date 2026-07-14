"""
Serve the Agent-to-Agent Marketplace UI *through Gradio* (Route 1).

One FastAPI process:
  •  our exact static app (sim_ui/web) at  /          — unchanged look, our HTML/JS/CSS
  •  a Gradio app mounted at              /gradio     — Gradio's backend (queuing/SSE),
                                                        where the LIVE path (adapter.py) lands at Step 3b

This is the "any custom frontend with Gradio's backend" pattern: RLEaaS embeds `/`
via local_url exactly like every other env, and we keep Gradio in the process for live.

    cd project_deal && .venv/bin/python -m sim_ui.serve            # port 8000
    A2A_UI_PORT=7860 .venv/bin/python -m sim_ui.serve
"""
import json
import os
from pathlib import Path

import gradio as gr
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

WEB = Path(__file__).parent / "web"


def _gradio_backend() -> gr.Blocks:
    """Gradio backend mounted at /gradio. Exposes ONE streaming API endpoint,
    /run_live, consumed by the static front-end via @gradio/client. Each yield
    is one live record (seed/event/room/reward/done/error)."""
    from . import live_runner

    # NOTE: the inputs are POSITIONAL — the front-end submits an array. Adding one here
    # without adding it to web/app.js (or vice versa) silently shifts every argument.
    def run_live(phase, set_id, focal, opponent, max_turns, seed, scammer, record):
        params = {
            "phase": phase, "set": set_id, "focal": focal, "opponent": opponent,
            "max_turns": int(max_turns or 100), "seed": int(seed or 42),
            "scammer": (str(scammer).lower() != "off"),   # default ON
            # Default OFF: a run is saved only when the human asks for it.
            "record": (str(record).lower() == "on"),
        }
        for record_ in live_runner.stream_live_run(params):
            yield record_

    with gr.Blocks(title="Agent-to-Agent Marketplace — backend") as demo:
        gr.Markdown("Live-run backend. UI is served at **/**; this exposes `/run_live`.")
        i_phase = gr.Textbox(visible=False)
        i_set = gr.Textbox(visible=False)
        i_focal = gr.Textbox(visible=False)
        i_opp = gr.Textbox(visible=False)
        i_turns = gr.Number(visible=False)
        i_seed = gr.Number(visible=False)
        i_scam = gr.Textbox(visible=False)
        i_record = gr.Textbox(visible=False)
        o_rec = gr.JSON(visible=False)
        trigger = gr.Button("run_live", visible=False)
        trigger.click(
            run_live,
            inputs=[i_phase, i_set, i_focal, i_opp, i_turns, i_seed, i_scam, i_record],
            outputs=o_rec,
            api_name="run_live",
        )
    return demo


def _first(value: str | None) -> str:
    """First entry of a possibly comma-joined forwarded header."""
    return (value or "").split(",")[0].strip()


def _public_root_from(request) -> str | None:
    """Public url of our Gradio mount, from the host's proxy headers (else None)."""
    prefix = _first(request.headers.get("x-forwarded-prefix"))
    host = _first(request.headers.get("x-forwarded-host"))
    if not (prefix and host):
        return None
    proto = _first(request.headers.get("x-forwarded-proto")) or "http"
    return f"{proto}://{host}{prefix.rstrip('/')}/gradio"


def _advertise_public_gradio_root(app: FastAPI) -> None:
    """
    Rewrite the absolute `root` Gradio advertises in /gradio/config when a host
    reverse-proxies us.

    Gradio's browser client takes `root` from that config and uses it for every later
    call. Behind a proxy Gradio only sees our private address (http://localhost:8012),
    so the client gets pointed somewhere the viewer's browser cannot reach.

    Nothing Gradio offers fixes this from the outside: `x-forwarded-host` and
    `x-gradio-server` both lose the host's path prefix (mounting pins Gradio's own
    root_path to "/gradio", which overwrites their path), and a full-url root_path —
    the documented escape — lands in the ASGI scope, where route matching strips it
    off the path and every Gradio route 404s. So the config is corrected on the way
    out, which is exactly the one value that is wrong.

    Only this app knows it mounts Gradio at /gradio, which is why this lives here and
    not in the host's (application-agnostic) proxy. No proxy headers -> untouched.
    """

    @app.middleware("http")
    async def _rewrite_gradio_config_root(request, call_next):
        response = await call_next(request)
        if not request.url.path.rstrip("/").endswith("/gradio/config"):
            return response
        public_root = _public_root_from(request)
        if not public_root or response.status_code != 200:
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            config = json.loads(body)
        except ValueError:
            return Response(
                content=body,
                status_code=response.status_code,
                media_type=response.media_type,
            )
        config["root"] = public_root
        return JSONResponse(config, status_code=response.status_code)


def build_app() -> FastAPI:
    app = FastAPI(title="Agent-to-Agent Marketplace")
    # mount Gradio FIRST so /gradio wins over the "/" static catch-all
    app = gr.mount_gradio_app(app, _gradio_backend(), path="/gradio")
    _advertise_public_gradio_root(app)
    # reward doors (POST /api/run, GET /api/result/*, /api/health) — BEFORE "/"
    from . import run_api
    run_api.register_routes(app)
    # serve the exact static UI at the root (html=True -> index.html for /)
    app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
    return app


def _port() -> int:
    return int(os.environ.get("PORT") or os.environ.get("A2A_UI_PORT") or 8000)


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=_port())
