"""
Launch the Agent-to-Agent Marketplace sim UI.

    cd project_deal && .venv/bin/python -m sim_ui.app            # default port 8000
    A2A_UI_PORT=7860 .venv/bin/python -m sim_ui.app

Cached replay only for now; the Live path (adapter.py) wires in at Step 3b.
"""
import os

from sim_ui.ui.dashboard import build_demo


def main():
    port = int(os.environ.get("A2A_UI_PORT", "8000"))
    demo = build_demo()
    demo.queue().launch(server_name="0.0.0.0", server_port=port, share=False,
                        show_error=True, quiet=False)


if __name__ == "__main__":
    main()
