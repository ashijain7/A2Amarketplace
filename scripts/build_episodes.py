#!/usr/bin/env python
"""Build sim_ui/web/episodes.json + sim_ui/web/img/ from the cached paper runs.

The SINGLE producer of the frontend's data file. Run it with the sim_ui venv
(it needs Pillow):

    sim_ui/.venv/bin/python scripts/build_episodes.py

Item photos are written as real .jpg files instead of being inlined as base64
(that made the JSON 1.53 MB; it is now ~0.4 MB and the browser lazy-loads only
the photos it actually shows).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))   # so `sim_ui` resolves when run as a plain script

from sim_ui.ui import logic


def build(out_dir: Path) -> dict:
    img_dir = out_dir / "img"
    cat = logic.Catalog()
    modes = cat.modes()

    episodes = {}
    for entry in cat.entries:
        ep = logic.load_episode(entry)
        episodes[f"{entry.mode}|{entry.config}|{entry.set_id}"] = logic.episode_to_frontend(ep)

    # write every referenced thumbnail exactly once
    for rollout_img in logic.all_item_image_paths():
        logic.write_thumbnail(rollout_img, img_dir)

    return {
        "modes": modes,
        "modeLabel": {m: logic.MODE_LABEL[m] for m in modes},
        "catalog": {
            m: {c: {"label": "  vs  ".join(logic.models_for(c)), "sets": cat.sets(m, c)}
                for c in cat.configs(m)}
            for m in modes
        },
        "episodes": episodes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "sim_ui" / "web"),
                    help="output dir (default sim_ui/web)")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = build(out_dir)
    dest = out_dir / "episodes.json"
    dest.write_text(json.dumps(data))
    kb = dest.stat().st_size / 1024
    n_img = len(list((out_dir / "img").glob("*.jpg")))
    print(f"wrote {dest}  ({len(data['episodes'])} episodes, {kb:.0f} KB)")
    print(f"wrote {out_dir / 'img'}  ({n_img} thumbnails)")


if __name__ == "__main__":
    main()
