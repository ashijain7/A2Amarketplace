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
import os
from pathlib import Path

import gradio as gr
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

WEB = Path(__file__).parent / "web"


def _gradio_backend() -> gr.Blocks:
    """Gradio backend mounted at /gradio. Exposes ONE streaming API endpoint,
    /run_live, consumed by the static front-end via @gradio/client. Each yield
    is one live record (seed/event/room/reward/done/error)."""
    from . import live_runner

    def run_live(phase, set_id, focal, opponent, max_turns, seed):
        params = {
            "phase": phase, "set": set_id, "focal": focal, "opponent": opponent,
            "max_turns": int(max_turns or 100), "seed": int(seed or 42),
        }
        for record in live_runner.stream_live_run(params):
            yield record

    with gr.Blocks(title="Agent-to-Agent Marketplace — backend") as demo:
        gr.Markdown("Live-run backend. UI is served at **/**; this exposes `/run_live`.")
        i_phase = gr.Textbox(visible=False)
        i_set = gr.Textbox(visible=False)
        i_focal = gr.Textbox(visible=False)
        i_opp = gr.Textbox(visible=False)
        i_turns = gr.Number(visible=False)
        i_seed = gr.Number(visible=False)
        o_rec = gr.JSON(visible=False)
        trigger = gr.Button("run_live", visible=False)
        trigger.click(
            run_live,
            inputs=[i_phase, i_set, i_focal, i_opp, i_turns, i_seed],
            outputs=o_rec,
            api_name="run_live",
        )
    return demo


def build_app() -> FastAPI:
    app = FastAPI(title="Agent-to-Agent Marketplace")
    # mount Gradio FIRST so /gradio wins over the "/" static catch-all
    app = gr.mount_gradio_app(app, _gradio_backend(), path="/gradio")
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
