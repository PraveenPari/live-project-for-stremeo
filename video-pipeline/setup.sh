#!/usr/bin/env bash
# Reproducibly provision the HyperFrames render toolchain in this sandbox.
#
# Why this exists: the sandbox has no GPU, no EGL, no system FFmpeg, and no
# outbound access to Google's Chrome download hosts. So we:
#   1. take Chromium from npm (@sparticuz/chromium ships it as a brotli blob),
#   2. strip the ANGLE/SwiftShader flags that crash on a GPU-less host,
#   3. unpack the matching NSS/NSPR shared libraries,
#   4. put ffmpeg/ffprobe on PATH from npm,
#   5. pin puppeteer-core to 19.x (the version that speaks Chromium 153's CDP).
#
# Everything lands under .tools/ which is gitignored (hundreds of MB).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
mkdir -p "$TOOLS"

echo "==> Installing render dependencies (npm)"
cd "$TOOLS"
# npm refuses a bare ".tools" as a package name, so write the manifest by hand
[ -f package.json ] || printf '{"name":"hyperframes-toolchain","version":"1.0.0","private":true}\n' > package.json
npm install --no-audit --no-fund --silent \
  hyperframes@0.9.52 \
  @sparticuz/chromium@latest \
  @ffmpeg-installer/ffmpeg @ffprobe-installer/ffprobe \
  puppeteer-core@19.11.1 gsap

echo "==> Unpacking Chromium"
node - "$TOOLS" <<'NODE'
const fs = require('fs'), zlib = require('zlib'), path = require('path');
const tools = process.argv[2];
const bin = path.join(tools, 'node_modules/@sparticuz/chromium/bin');
const out = path.join(tools, 'bin');
fs.mkdirSync(out, { recursive: true });

// Chromium binary, with the GPU-flag strings neutralised. On a host with no
// EGL/GPU, "--use-angle=swiftshader" makes Chromium crash before DevTools
// answers, so HyperFrames' hardcoded flags have to become no-ops.
const browser = zlib.brotliDecompressSync(fs.readFileSync(path.join(bin, 'chromium.br')));
const patched = browser.toString('latin1')
  .replace(/--use-angle=swiftshader/g, '--use-angle=swiftshaderxx')
  .replace(/--use-gl=angle/g, '--use-gl=anglexx');
const exe = path.join(out, 'chromium');
fs.writeFileSync(exe, Buffer.from(patched, 'latin1'));
fs.chmodSync(exe, 0o755);
console.log('    chromium ->', exe);

// NSS/NSPR libs Chromium dlopens at startup.
const libs = path.join(out, 'libs');
fs.mkdirSync(libs, { recursive: true });
for (const name of ['al2023.tar.br', 'aws.tar.br']) {
  const p = path.join(bin, name);
  if (!fs.existsSync(p)) continue;
  fs.writeFileSync(path.join(out, 'libs.tar'), zlib.brotliDecompressSync(fs.readFileSync(p)));
  require('child_process').execSync(`tar -xf "${path.join(out, 'libs.tar')}" -C "${libs}"`);
  fs.rmSync(path.join(out, 'libs.tar'));
}
NODE

# tar unpacks to libs/lib/*.so — flatten so one LD_LIBRARY_PATH entry works.
find "$TOOLS/bin/libs" -name '*.so*' -exec mv -t "$TOOLS/bin/libs" {} + 2>/dev/null || true
find "$TOOLS/bin/libs" -type d -empty -delete 2>/dev/null || true

echo "==> Linking ffmpeg / ffprobe"
ln -sf "$TOOLS/node_modules/@ffmpeg-installer/linux-x64/ffmpeg" "$TOOLS/bin/ffmpeg"
ln -sf "$TOOLS/node_modules/@ffprobe-installer/linux-x64/ffprobe" "$TOOLS/bin/ffprobe"

cat > "$TOOLS/env.sh" <<EOF
# Source this before rendering:  source .tools/env.sh
export PATH="$TOOLS/bin:\$PATH"
export LD_LIBRARY_PATH="$TOOLS/bin/libs:\${LD_LIBRARY_PATH:-}"
export HYPERFRAMES_BROWSER_PATH="$TOOLS/bin/chromium"
export HYPERFRAMES_SKIP_SKILLS=1
EOF

echo "==> Smoke test"
source "$TOOLS/env.sh"
ffmpeg -hide_banner -version | head -1
"$HYPERFRAMES_BROWSER_PATH" --version

echo
echo "Toolchain ready. Render with:"
echo "  source .tools/env.sh"
echo "  ./video-pipeline/render.sh <project-dir> <output.mp4>"
