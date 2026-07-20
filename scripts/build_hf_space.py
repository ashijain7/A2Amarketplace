"""Assemble the static Hugging Face Space from sim_ui/web.

The Space is `sdk: static` — Hugging Face serves the files directly, with no server behind
them. That is enough because cached mode is entirely client-side: app.js fetches
episodes.json and the thumbnails in web/img and renders from those. Only the Live half
needs a backend, and this build hides it (see A2A_CACHED_ONLY in app.js).

WHY A SCRIPT AND NOT A MANUAL COPY. The Space published on 2026-07-10 carried a
hand-adapted 36 kB app.js. Nothing kept it in step with the real one, so it drifted four
versions behind: 136 episodes instead of 140, no reward-breakdown panel, no measured
episode summary, and photos still inlined as data URIs (1.53 MB of episodes.json). Here
the only edit is one injected <script> line and the Gradio import dropped; everything else
is copied byte for byte, so the next update is `python scripts/build_hf_space.py` again.

DO NOT FORGET web/img. Episodes reference photos by FILENAME now, not as data URIs. Upload
episodes.json without the img directory and every item photo 404s — which is exactly what
a naive file-by-file copy of the old Space would produce.

Usage:  uv run python scripts/build_hf_space.py [--out DIR]
"""

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "sim_ui" / "web"

# The Space's own README. Deliberately NOT the repo's README.md: that one is rendered by
# the RLEaaS Simulations panel, where a YAML front-matter block would show up as junk.
README = """---
title: A2A Marketplace
emoji: 🤝
colorFrom: gray
colorTo: blue
sdk: static
pinned: false
short_description: {short_description}
---

# Agent-to-Agent Marketplace

A cached, read-only replay of {n_episodes} recorded rollouts from the A2A Marketplace
environment. One focal LLM agent is evaluated against fixed-model opponents across four
stages — Market Deal, Review, Transaction and Swap Shop — over five persona sets and
seven model pairings.

Every reward on this page was produced by the environment's own verifiers; nothing here is
recomputed in the browser. The **Verifiers & Rewards** tab shows how each rubric is built
and which parts are deterministic (D) versus judged by an LLM (J). The **Leaderboard** tab
ranks the model pairings per stage.

This is a replay only — no live execution, no API keys, no model calls.
"""

# The Live half needs /api/models, /api/run and a Gradio socket. None of that exists on a
# static host, so the flag hides the Mode switch and the Gradio client import is dropped.
FLAG = '<script>window.A2A_CACHED_ONLY = true;</script>\n'
GRADIO_IMPORT = re.compile(
    r'<script type="module">\s*import \{ Client \}.*?</script>\s*',
    re.DOTALL,
)


def build(out: Path) -> dict:
    if not (WEB / "episodes.json").exists():
        raise SystemExit(f"missing {WEB/'episodes.json'} — run scripts/build_episodes.py first")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    shutil.copy2(WEB / "app.js", out / "app.js")
    shutil.copy2(WEB / "episodes.json", out / "episodes.json")
    shutil.copytree(WEB / "img", out / "img")

    html = (WEB / "index.html").read_text()
    html, n_dropped = GRADIO_IMPORT.subn("", html)
    if n_dropped != 1:
        raise SystemExit(
            f"expected exactly 1 Gradio import in index.html, found {n_dropped} — "
            "the tail of that file changed; re-check before publishing"
        )
    html = html.replace('<script src="app.js">', FLAG + '<script src="app.js">')
    if "A2A_CACHED_ONLY" not in html:
        raise SystemExit("failed to inject the cached-only flag — app.js tag not found")
    (out / "index.html").write_text(html)

    episodes = json.loads((WEB / "episodes.json").read_text())
    n = len(episodes["episodes"])
    (out / "README.md").write_text(README.format(
        n_episodes=n,
        short_description=f"Cached replays of {n} agent-to-agent negotiation rollouts",
    ))

    imgs = len(list((out / "img").iterdir()))
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    return {"out": out, "episodes": n, "images": imgs, "bytes": size}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "hf_space"))
    a = ap.parse_args()
    r = build(Path(a.out))
    print(f"built {r['out']}")
    print(f"  episodes : {r['episodes']}")
    print(f"  images   : {r['images']}")
    print(f"  size     : {r['bytes']/1e6:.2f} MB")
