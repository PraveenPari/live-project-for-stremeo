# Free 2D animation, rendered here

Three free engines, all verified rendering MP4s in this sandbox. No API key, no
credits, no stock footage. Every one is deterministic — same input, same frames.

| Engine | Use it for | Entry point |
| --- | --- | --- |
| **Procedural canvas** (this repo's own) | title cards, mascots, story shorts, explainer scenery | `make.py` |
| **Lottie** | After Effects / Illustrator exports, character rigs, icon animation | `scaffolds/lottie/` |
| **p5.js** | generative art, loops, data-driven motion backgrounds | `scaffolds/p5/` |

Manim was evaluated and **rejected**: it needs Cairo + Pango system libraries
that cannot be installed here (no apt). It works on your own machine.

## Quick start

```bash
./video-pipeline/setup.sh                       # once per sandbox
./video-pipeline/2d/make.py \
    --title "Hello Chennai" \
    --subtitle "made with code, not credits" \
    --seconds 8 --out projects/hello --render
```

That writes a self-contained project and renders `projects/hello/hello.mp4`.
Output is 1920×1080 at 30 fps by default; pass `--width/--height` for vertical
(`1080 --height 1920`).

Useful flags: `--palette 0..3` forces a colour scheme (otherwise it is derived
from the title, so the same title always looks the same), `--fps 24`, `--render`
to encode immediately.

## What the procedural film does

A character walks in from the left, stops on his mark, waves, and exits; the sky
goes from morning to dusk while the sun sinks and stars fade in; hills parallax,
clouds drift, grass sways; the title wipes in with an underline, the subtitle
follows, both fade out at the end. All of it is a pure function of time `t`, so
no frame depends on the previous one — that is what makes the render seekable
and reproducible.

Edit `template/anim.js` to change behaviour; edit `template/config.template.json`
to expose more variables.

## Lottie / After Effects

```bash
# 1. export your animation as a Lottie JSON from After Effects (Bodymovin) or Figma
# 2. drop it in as anim.json and set the stage size to the animation's w/h
mkdir -p projects/my-lottie && cp video-pipeline/2d/scaffolds/lottie/index.html projects/my-lottie/
cp path/to/export.json projects/my-lottie/anim.json
```

The scaffold already does the two things that matter: `autoplay:false` and a
GSAP proxy timeline that calls `goToAndStop(t * fps, true)`. Lottie is pushed to
`window.__hfLottie` so HyperFrames can find it.

## p5.js generative

`scaffolds/p5/index.html` shows the `hf-seek` pattern: draw from
`e.detail.time` and never from `frameCount`. Replace `__renderAt` with your sketch.
Note that `p5` is available from npm (`p5.min.js`) — copy it next to `index.html`.

## Verified performance

Measured on this 2-core sandbox, 1080p30, `--quality looks`:

| Job | Time |
| --- | --- |
| 6 s title card | 22 s |
| 8 s procedural film (above) | ~36 s |
| 10 s title card, 300 frames | 34 s |
| 3 s Lottie at 1200² , draft | 9 s |

Roughly 3–4× realtime for flat 2D work. Heavy canvas work or lots of
per-frame gradients will be slower; drop to `--quality draft` while iterating.

## Limits worth knowing

- This sandbox has **no GPU**, so everything renders through software
  rasterisation. That is fine for 2D; it is not a good place for 3D/shader work.
- Capture is pinned to **one worker** (low-memory profile), so long films scale
  roughly linearly. A 60 s film is ~4 minutes.
- Anything that reaches the network at render time will hang: vendor your fonts,
  scripts and media into the project folder (the generator already does this).

## Contributing a new engine

Add a `scaffolds/<name>/` folder with an `index.html` that follows the seek
contract (`hf-seek` listener, no rAF clock, no network at render time), prove it
renders, and add a row to the table above.
