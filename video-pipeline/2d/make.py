#!/usr/bin/env python3
"""
Generate a free 2D animation video from a one-line brief.

    ./video-pipeline/2d/make.py --title "Hello Chennai" \
        --subtitle "made with code, not credits" \
        --out projects/hello-chennai --seconds 8 --render

Everything is procedural: no stock footage, no paid model, no API key.
The chosen palette is derived from the title text, so the same title
always produces the same film (deterministic, like the renderer).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).resolve().parent / "template"
TOOLS = ROOT / ".tools"

# Hand-tuned palettes; one is picked deterministically from the title.
PALETTES = [
    {   # golden hour
        "skyTop": "#8ecae6", "skyBottom": "#ffd6a5",
        "duskTop": "#3d5a80", "duskBottom": "#ee9b7a",
        "sun": "#ffb703", "hillFar": "#9bbf8a", "hillNear": "#5c8f5a",
        "groundTop": "#7fb069", "groundBottom": "#3f6b46",
        "grass": "#2f5d3a", "leaf": "#4a8c4f", "trunk": "#7a5230",
        "body": "#e4572e", "skin": "#f4c9a3", "accent": "#ffb703", "ink": "#1d2b36",
    },
    {   # mint morning
        "skyTop": "#caf0f8", "skyBottom": "#ade8f4",
        "duskTop": "#5e60ce", "duskBottom": "#f7b2d9",
        "sun": "#ffd60a", "hillFar": "#a8dadc", "hillNear": "#7ba9a0",
        "groundTop": "#94d2bd", "groundBottom": "#4f772d",
        "grass": "#386641", "leaf": "#52b788", "trunk": "#6b4f3a",
        "body": "#3a86ff", "skin": "#f2c6a0", "accent": "#ff006e", "ink": "#102a43",
    },
    {   # dusk purple
        "skyTop": "#bde0fe", "skyBottom": "#ffc8dd",
        "duskTop": "#3a0ca3", "duskBottom": "#f72585",
        "sun": "#ffd166", "hillFar": "#b8a1d9", "hillNear": "#7b6aa8",
        "groundTop": "#8e7cc3", "groundBottom": "#3c2a63",
        "grass": "#4b3b6b", "leaf": "#7d5ba6", "trunk": "#5a3e2b",
        "body": "#ff6b6b", "skin": "#f6c8a8", "accent": "#ffd166", "ink": "#1a1033",
    },
    {   # forest story
        "skyTop": "#d8f3dc", "skyBottom": "#ffe8c2",
        "duskTop": "#2d6a4f", "duskBottom": "#f4a261",
        "sun": "#f9c74f", "hillFar": "#95d5b2", "hillNear": "#52b788",
        "groundTop": "#74c69d", "groundBottom": "#1b4332",
        "grass": "#1b4332", "leaf": "#40916c", "trunk": "#6b4f3a",
        "body": "#f3722c", "skin": "#f2c6a0", "accent": "#f9c74f", "ink": "#081c15",
    },
]


def pick_palette(seed_text: str) -> dict:
    h = int(hashlib.sha256(seed_text.encode()).hexdigest(), 16)
    return PALETTES[h % len(PALETTES)]


def write_fonts_css(out: Path) -> None:
    """Copy only the latin weights we use, and reference them relatively."""
    faces = [
        ("Outfit", 900, "@fontsource/outfit/files/outfit-latin-900-normal.woff2"),
        ("Outfit", 700, "@fontsource/outfit/files/outfit-latin-700-normal.woff2"),
        ("Inter", 600, "@fontsource/inter/files/inter-latin-600-normal.woff2"),
        ("Inter", 400, "@fontsource/inter/files/inter-latin-400-normal.woff2"),
    ]
    fonts_dir = out / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    css = ["/* vendored from npm — the sandbox cannot reach Google Fonts */"]
    for family, weight, rel in faces:
        src = TOOLS / "node_modules" / rel
        if not src.exists():
            raise SystemExit(f"missing font asset {src}; run video-pipeline/setup.sh")
        dest = fonts_dir / src.name
        shutil.copy2(src, dest)
        css.append(
            "@font-face{font-family:'%s';font-style:normal;font-weight:%d;"
            "font-display:block;src:url('fonts/%s') format('woff2')}"
            % (family, weight, src.name)
        )
    (out / "fonts.css").write_text("\n".join(css) + "\n")


def build(out: Path, title: str, subtitle: str, seconds: float,
          width: int, height: int, palette: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)

    cfg = {
        "name": title.lower().replace(" ", "-"),
        "width": width,
        "height": height,
        "duration": seconds,
        "title": title,
        "subtitle": subtitle,
        "palette": palette,
    }

    html = (TEMPLATE / "index.html").read_text()
    for key, value in {
        "{{TITLE}}": title,
        "{{WIDTH}}": str(width),
        "{{HEIGHT}}": str(height),
        "{{DURATION}}": str(seconds),
        "{{CONFIG_JSON}}": json.dumps(cfg, indent=2),
    }.items():
        html = html.replace(key, value)
    (out / "index.html").write_text(html)

    shutil.copy2(TEMPLATE / "anim.js", out / "anim.js")
    gsap = TOOLS / "node_modules" / "gsap" / "dist" / "gsap.min.js"
    if not gsap.exists():
        raise SystemExit(f"missing {gsap}; run video-pipeline/setup.sh")
    shutil.copy2(gsap, out / "gsap.min.js")
    write_fonts_css(out)

    print(f"  project  {out}")
    print(f"  size     {width}x{height}, {seconds:g}s")
    print(f"  palette  {palette['skyTop']} → {palette['duskBottom']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--title", required=True, help="big on-screen title")
    p.add_argument("--subtitle", default="", help="smaller line under it")
    p.add_argument("--out", required=True, help="project directory to create")
    p.add_argument("--seconds", type=float, default=8.0)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--palette", type=int, default=None,
                   help="force a palette index (0-3); default derives it from the title")
    p.add_argument("--render", action="store_true", help="render an MP4 after generating")
    p.add_argument("--fps", type=int, default=30)
    args = p.parse_args()

    out = Path(args.out).resolve()
    palette = PALETTES[args.palette % len(PALETTES)] if args.palette is not None else pick_palette(args.title)

    print("==> Generating 2D animation")
    build(out, args.title, args.subtitle, args.seconds, args.width, args.height, palette)

    if not args.render:
        print("\nRender it with:\n  ./video-pipeline/render.sh %s" % args.out)
        return 0

    video = out / f"{out.name}.mp4"
    print("\n==> Rendering")
    cmd = [str(ROOT / "video-pipeline" / "render.sh"), str(out), str(video),
           "--quality", "looks", "-f", str(args.fps)]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
