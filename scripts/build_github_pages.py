#!/usr/bin/env python3
"""Build the dependency-free GitHub Pages artifact."""
from __future__ import annotations
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"dist_pages"
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir()
for name in ["index.html","app.js","web.css","manifest.webmanifest","service-worker.js"]: shutil.copy2(ROOT/"web"/name,OUT/name)
shutil.copy2(ROOT/"static"/"styles.css",OUT/"styles.css")
shutil.copy2(ROOT/"static"/"logo.png",OUT/"logo.png")
(OUT/".nojekyll").write_text("",encoding="utf-8")
print(f"Built GitHub Pages artifact: {OUT}")
