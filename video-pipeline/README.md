# Video pipeline (HyperFrames in this sandbox)

Rendering HTML → MP4 with [HyperFrames](https://github.com/heygen-com/hyperframes)
**does** work here. These scripts make it reproducible.

## One-time setup

```bash
./video-pipeline/setup.sh      # ~3 min, writes ~700 MB into .tools/ (gitignored)
```

## Render

```bash
source .tools/env.sh
./video-pipeline/render.sh examples/my-video out.mp4 --quality looks -f 30
```

Composition format: a single `index.html` with `data-composition-id`,
`data-width/height/duration`, and clips carrying `data-start`, `data-duration`,
`data-track-index`. Animate with GSAP via `window.__timelines[id]`.

⚠️ `init` scaffolds a CDN `<script src="https://cdn.jsdelivr.net/...">`. This
sandbox cannot reach jsdelivr — vendor GSAP locally (`.tools/node_modules/gsap/dist/gsap.min.js`)
or the page loads with no timeline and capture hangs.

## What had to be worked around

| Problem | Fix in `setup.sh` |
| --- | --- |
| No GPU/EGL; Chromium 153 crashes at startup | Strip `--use-angle=swiftshader` / `--use-gl=angle` from the binary |
| Chrome download hosts blocked | Chromium comes from npm (`@sparticuz/chromium`) |
| `libnspr4` / `libnss3` missing | Unpacked from the same npm package into `.tools/bin/libs` |
| No system FFmpeg | `@ffmpeg-installer` + `@ffprobe-installer` on PATH |
| New `puppeteer-core` can't drive Chromium 153 | Pinned to `19.11.1` |

## Measured performance

- 10 s of 1080p30, `--quality looks`, 1 worker: **~34 s** (~3.4× realtime)
- Low-memory host: HyperFrames pins itself to 1 capture worker; `-w` is ignored

## Free 2D animation

`video-pipeline/2d/` turns a one-line brief into a rendered 2D animation — no
API key, no credits. See [2d/README.md](2d/README.md).

```bash
./video-pipeline/2d/make.py --title "Hello Chennai" --subtitle "made with code" \
    --seconds 8 --out projects/hello --render
```

## Proof (`examples/hello`)

`examples/hello/index.html` is a 6 s 1080p30 title card rendered by this
pipeline to `examples/hello/hello.mp4` (180 frames, ~22 s wall clock).
Commit regenerated renders to LFS or keep them out of Git.
