#!/usr/bin/env bash
# Render a HyperFrames composition to MP4.
#   ./video-pipeline/render.sh <project-dir> [output.mp4] [extra hyperframes args...]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$(cd "${1:?usage: render.sh <project-dir> [output.mp4] [args...]}"; pwd)"
if [ -n "${2:-}" ]; then
  # resolve before the cd below, so relative paths mean relative to the caller
  OUT="$(cd "$(dirname "$2")" 2>/dev/null && pwd)/$(basename "$2")" || OUT="$PWD/$2"
  mkdir -p "$(dirname "$OUT")"
else
  OUT="$PROJECT/renders/$(basename "$PROJECT")_$(date +%Y-%m-%d_%H-%M-%S).mp4"
fi
shift 2 2>/dev/null || shift 1

source "$ROOT/.tools/env.sh"

mkdir -p "$(dirname "$OUT")"
echo "==> Rendering $PROJECT -> $OUT"
cd "$PROJECT"
node "$ROOT/.tools/node_modules/hyperframes/bin/hyperframes.mjs" render -o "$OUT" "$@"
echo "==> Done: $OUT"
