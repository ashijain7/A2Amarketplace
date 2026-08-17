#!/usr/bin/env python3
"""Render the paper to a single markdown file with every page embedded as a
base64 image.

Why: VS Code webviews on this setup cannot fetch local files (PNG and PDF
previews come up blank), but they do render markdown, and a data: URI needs no
fetch. So the pages travel inside the document itself.

Usage: make_preview_md.py [--dpi 80] [--pdf <path>] [--out <path>]
"""
import argparse, base64, subprocess, tempfile
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "A2A_COLM_2026"

ap = argparse.ArgumentParser()
ap.add_argument("--pdf", default=str(D / "Agent_to_Agent_marketplace_COLM.pdf"))
ap.add_argument("--out", default=str(D / "PAPER_PREVIEW.md"))
ap.add_argument("--dpi", type=int, default=80)
a = ap.parse_args()

with tempfile.TemporaryDirectory() as td:
    subprocess.run(["pdftoppm", "-r", str(a.dpi), "-jpeg", a.pdf, f"{td}/p"], check=True)
    pages = sorted(Path(td).glob("p-*.jpg"))
    # which page does the bibliography start on? worth flagging while we are
    # fighting a page limit.
    txt = subprocess.run(["pdftotext", a.pdf, "-"], capture_output=True, text=True).stdout
    refs = None
    for i in range(1, len(pages) + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), a.pdf, "-"],
                           capture_output=True, text=True).stdout
        if any(l.strip() == "References" for l in t.split("\n")):
            refs = i
            break
    out = [f"# Paper preview — {len(pages)} pages",
           "",
           f"Body runs to page **{refs - 1}** ({'References starts on page ' + str(refs) if refs else 'no bibliography found'}).",
           "Regenerate with `python3 scripts/make_preview_md.py` after each build.",
           ""]
    for i, p in enumerate(pages, 1):
        b64 = base64.b64encode(p.read_bytes()).decode()
        tag = "  ← body ends here" if refs and i == refs else ""
        out.append(f"### Page {i}{tag}")
        out.append(f'<img src="data:image/jpeg;base64,{b64}" width="700">')
        out.append("")
Path(a.out).write_text("\n".join(out))
mb = Path(a.out).stat().st_size / 1e6
print(f"wrote {a.out}  ({len(pages)} pages, {mb:.1f} MB)")
