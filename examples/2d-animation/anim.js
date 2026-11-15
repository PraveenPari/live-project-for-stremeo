// Free 2D animation stage for HyperFrames.
//
// Deterministic by construction: every pixel is a pure function of `t`
// (seconds). No clock, no rAF, no Math.random — so a frame rendered twice is
// byte-identical, and the renderer can seek in any order.
//
// HyperFrames drives us through the `hf-seek` event.

(function () {
  const STAGE = document.getElementById("stage");
  const cfg = JSON.parse(document.getElementById("anim-config").textContent);
  const W = cfg.width, H = cfg.height;
  const DURATION = cfg.duration;

  const PALETTE = cfg.palette;
  const GROUND_Y = H * 0.86;
  const SUN = { x: W * 0.82, y: H * 0.2, r: 118 };
  const HORIZON = H * 0.72;

  // ---------------------------------------------------------------- helpers

  // mulberry32 — small seeded PRNG so "random" scenery never changes between renders
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const lerp = (a, b, u) => a + (b - a) * u;
  const ease = {
    inOut: (u) => (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2),
    out: (u) => 1 - Math.pow(1 - u, 3),
    in: (u) => u * u * u,
    back: (u) => 1 + 2.70158 * Math.pow(u - 1, 3) + 1.70158 * Math.pow(u - 1, 2),
    elastic: (u) =>
      u === 0 || u === 1 ? u : Math.pow(2, -10 * u) * Math.sin((u * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1,
  };

  // --------------------------------------------------------------- scenery

  // Pre-computed hills + grass so the PRNG never runs during a seek.
  const farHills = (() => {
    const rnd = mulberry32(1337), pts = [];
    for (let x = -200; x <= W + 200; x += 90) {
      pts.push({ x, y: HORIZON - 40 - rnd() * 95 });
    }
    return pts;
  })();

  const nearHills = (() => {
    const rnd = mulberry32(7331), pts = [];
    for (let x = -200; x <= W + 200; x += 130) {
      pts.push({ x, y: HORIZON + 20 - rnd() * 55 });
    }
    return pts;
  })();

  const clouds = (() => {
    const rnd = mulberry32(99), out = [];
    for (let i = 0; i < 4; i++) {
      out.push({
        x: rnd() * W,
        y: H * 0.1 + rnd() * H * 0.16,
        s: 0.7 + rnd() * 0.6,
        speed: 6 + rnd() * 10,
      });
    }
    return out;
  })();

  const stars = (() => {
    const rnd = mulberry32(4242), out = [];
    for (let i = 0; i < 90; i++) {
      out.push({ x: rnd() * W, y: rnd() * HORIZON, s: 0.8 + rnd() * 2.2, tw: rnd() * 6.28 });
    }
    return out;
  })();

  const grass = (() => {
    const rnd = mulberry32(555), out = [];
    for (let i = 0; i < 220; i++) {
      const y = GROUND_Y + rnd() * (H - GROUND_Y) * 0.95;
      out.push({ x: rnd() * W, y, h: 10 + rnd() * 26, ph: rnd() * 6.28 });
    }
    return out;
  })();

  // ------------------------------------------------------------- character

  // A tiny rig: walk cycle, blink, squash, arm swing. All keyed off t.
  function drawCharacter(g, t, opts) {
    const { x, scale = 1, walkFrom, walkTo, enterAt, leaveAt, facing = 1, wave = null } = opts;

    // Walk path is eased across its window so the character settles on its mark.
    const walkT = clamp((t - walkFrom) / Math.max(0.001, walkTo - walkFrom), 0, 1);
    const px = lerp(opts.startX, x, ease.inOut(walkT));
    const walking = t > walkFrom && t < walkTo;

    // Entrance pop (overshoot) and exit fade.
    let pop = 1, alpha = 1;
    if (enterAt != null) pop = clamp(ease.back(clamp((t - enterAt) / 0.55, 0, 1)), 0, 1.15);
    if (leaveAt != null && t > leaveAt) alpha = clamp(1 - (t - leaveAt) / 0.4, 0, 1);
    if (alpha <= 0) return;

    const bob = walking ? Math.abs(Math.sin(t * 9.5)) * 7 : Math.sin(t * 2.1) * 2.4;
    const squash = walking ? 1 + Math.sin(t * 19) * 0.03 : 1 + Math.sin(t * 2.1) * 0.008;

    const bobY = GROUND_Y + 6 - bob;
    const bodyH = 132 * scale * pop;
    const bodyW = 96 * scale * pop;
    const headR = 40 * scale * pop;

    g.save();
    g.globalAlpha = alpha;
    g.translate(px, bobY);
    g.scale(facing, 1);

    // shadow
    g.globalAlpha = alpha * 0.25;
    g.fillStyle = "#000";
    g.beginPath();
    g.ellipse(0, 4, bodyW * 0.62, 11, 0, 0, Math.PI * 2);
    g.fill();
    g.globalAlpha = alpha;

    const swing = walking ? Math.sin(t * 9.5) : 0;

    // legs
    g.strokeStyle = PALETTE.ink;
    g.lineWidth = 15 * scale;
    g.lineCap = "round";
    for (const side of [-1, 1]) {
      const a = swing * side * 0.7;
      const kx = Math.sin(a) * 34 * scale, ky = -Math.cos(a) * 4 * scale;
      g.beginPath();
      g.moveTo(side * 14 * scale, -bodyH * 0.36);
      g.lineTo(side * 14 * scale + kx, -6 + Math.abs(ky) * 0.4);
      g.stroke();
    }

    // body
    g.fillStyle = PALETTE.body;
    g.beginPath();
    g.roundRect(-bodyW / 2, -bodyH * 0.38 - bodyH * 0.62 * squash, bodyW, bodyH * 0.62 * squash, 26 * scale);
    g.fill();

    // arms — start at the shoulder on the body *edge* and swing outward, so
    // they read against the silhouette instead of disappearing into the torso
    g.strokeStyle = PALETTE.body;
    g.lineWidth = 14 * scale;
    g.lineCap = "round";
    for (const side of [-1, 1]) {
      const waving = wave && side === 1 && t > wave.at && t < wave.until;
      // rest pose angles the arm down-and-out; walk swings it fore/aft
      // negative swings the arm up; ~-2.8 is nearly vertical
      const a = waving
        ? -2.78 + Math.sin((t - wave.at) * 13) * 0.26
        : side * (0.42 + swing * -side * 0.5);

      const sx = side * bodyW * 0.46;
      const sy = -bodyH * 0.78;
      // angle 0 = straight down; positive swings outward for this side
      const armLen = (waving ? 62 : 50) * scale;
      const ex = sx + Math.sin(a) * armLen * side * -1;
      const ey = sy + Math.cos(a) * armLen;
      g.beginPath();
      g.moveTo(sx, sy);
      g.quadraticCurveTo(sx + (ex - sx) * 0.3, sy + (ey - sy) * 0.7, ex, ey);
      g.stroke();

      // hand, so the gesture reads at small sizes
      g.fillStyle = PALETTE.skin;
      g.beginPath();
      g.arc(ex, ey, 8.5 * scale, 0, Math.PI * 2);
      g.fill();
    }

    // head
    const headY = -bodyH * 0.98 - headR * 0.85;
    g.fillStyle = PALETTE.skin;
    g.beginPath();
    g.arc(0, headY, headR, 0, Math.PI * 2);
    g.fill();

    // hair cap
    g.fillStyle = PALETTE.ink;
    g.beginPath();
    g.arc(0, headY - headR * 0.18, headR * 0.99, Math.PI * 1.03, Math.PI * 1.97);
    g.fill();

    // eyes — blink on a 3.4 s cycle, offset so it never looks mechanical
    const blinkPhase = ((t + 0.9) % 3.4) / 3.4;
    const blinking = blinkPhase > 0.94;
    g.fillStyle = PALETTE.ink;
    for (const side of [-1, 1]) {
      const ex = side * headR * 0.34, ey = headY - headR * 0.02;
      if (blinking) {
        g.fillRect(ex - 5, ey - 1.5, 10, 3);
      } else {
        g.beginPath();
        g.arc(ex, ey, 4.6, 0, Math.PI * 2);
        g.fill();
      }
    }

    // smile
    g.strokeStyle = PALETTE.ink;
    g.lineWidth = 3.4;
    g.beginPath();
    g.arc(0, headY + headR * 0.3, headR * 0.4, 0.25 * Math.PI, 0.75 * Math.PI);
    g.stroke();

    // cheeks
    g.fillStyle = PALETTE.accent;
    g.globalAlpha = alpha * 0.5;
    for (const side of [-1, 1]) {
      g.beginPath();
      g.arc(side * headR * 0.62, headY + headR * 0.28, 6, 0, Math.PI * 2);
      g.fill();
    }

    g.restore();
  }

  // ------------------------------------------------------------ draw frame

  function drawScene(g, t) {
    const u = clamp(t / DURATION, 0, 1);

    // Sky gradient shifts from day to dusk across the film.
    const sky = g.createLinearGradient(0, 0, 0, HORIZON);
    sky.addColorStop(0, lerpColor(PALETTE.skyTop, PALETTE.duskTop, ease.inOut(u)));
    sky.addColorStop(1, lerpColor(PALETTE.skyBottom, PALETTE.duskBottom, ease.inOut(u)));
    g.fillStyle = sky;
    g.fillRect(0, 0, W, HORIZON + 2);

    // stars fade in as dusk arrives
    const starA = clamp((ease.inOut(u) - 0.45) / 0.55, 0, 1);
    if (starA > 0) {
      for (const s of stars) {
        const tw = 0.55 + 0.45 * Math.sin(t * 2.2 + s.tw);
        g.globalAlpha = starA * tw;
        g.fillStyle = "#fff";
        g.beginPath();
        g.arc(s.x, s.y, s.s, 0, Math.PI * 2);
        g.fill();
      }
      g.globalAlpha = 1;
    }

    // sun / moon sinking slowly
    const sunY = lerp(SUN.y, HORIZON - 30, ease.inOut(u));
    g.fillStyle = lerpColor(PALETTE.sun, "#f4f1ea", ease.inOut(u));
    g.beginPath();
    g.arc(SUN.x, sunY, SUN.r, 0, Math.PI * 2);
    g.fill();

    // soft halo
    const halo = g.createRadialGradient(SUN.x, sunY, SUN.r * 0.6, SUN.x, sunY, SUN.r * 2.6);
    halo.addColorStop(0, "rgba(255,214,120,0.34)");
    halo.addColorStop(1, "rgba(255,214,120,0)");
    g.fillStyle = halo;
    g.fillRect(0, 0, W, HORIZON);

    // drifting clouds
    for (const c of clouds) {
      const cx = ((c.x + t * c.speed) % (W + 400)) - 200;
      g.fillStyle = "rgba(255,255,255,0.72)";
      g.beginPath();
      g.ellipse(cx, c.y, 92 * c.s, 30 * c.s, 0, 0, Math.PI * 2);
      g.ellipse(cx + 56 * c.s, c.y + 8 * c.s, 62 * c.s, 24 * c.s, 0, 0, Math.PI * 2);
      g.ellipse(cx - 58 * c.s, c.y + 10 * c.s, 54 * c.s, 22 * c.s, 0, 0, Math.PI * 2);
      g.fill();
    }

    // far hills (parallax: drift slower than the foreground)
    const drift = t * 5;
    g.fillStyle = PALETTE.hillFar;
    g.beginPath();
    g.moveTo(-200, HORIZON + 60);
    for (const p of farHills) g.lineTo(p.x - drift * 0.4, p.y);
    g.lineTo(W + 200, HORIZON + 60);
    g.closePath();
    g.fill();

    // near hills
    g.fillStyle = PALETTE.hillNear;
    g.beginPath();
    g.moveTo(-200, HORIZON + 120);
    for (const p of nearHills) g.lineTo(p.x - drift * 0.8, p.y);
    g.lineTo(W + 200, HORIZON + 120);
    g.closePath();
    g.fill();

    // ground
    const ground = g.createLinearGradient(0, GROUND_Y - 60, 0, H);
    ground.addColorStop(0, PALETTE.groundTop);
    ground.addColorStop(1, PALETTE.groundBottom);
    g.fillStyle = ground;
    g.fillRect(0, GROUND_Y - 48, W, H - GROUND_Y + 48);

    // grass blades swaying on a sine wave
    g.strokeStyle = PALETTE.grass;
    g.lineWidth = 3;
    g.lineCap = "round";
    for (const b of grass) {
      const sway = Math.sin(t * 2.5 + b.ph + b.x * 0.01) * 4;
      g.beginPath();
      g.moveTo(b.x, b.y);
      g.quadraticCurveTo(b.x + sway * 0.5, b.y - b.h * 0.6, b.x + sway, b.y - b.h);
      g.stroke();
    }

    // background trees first, so the character passes in front of them
    drawTree(g, W * 0.09, GROUND_Y + 10, 0.72, t + 1.7);
    drawTree(g, W * 0.86, GROUND_Y + 26, 1.0, t);

    // the character enters from the left, stops centre, waves, exits right
    drawCharacter(g, t, {
      startX: -180,
      x: W * 0.5,
      scale: 1.35,
      walkFrom: 0.4,
      walkTo: 2.6,
      enterAt: 0.0,
      leaveAt: DURATION - 0.9,
      wave: { at: 2.9, until: DURATION - 1.0 },
    });
  }

  function drawTree(g, x, baseY, scale, t) {
    const sway = Math.sin(t * 1.3) * 3 * scale;
    g.save();
    g.translate(x, baseY);
    g.strokeStyle = PALETTE.trunk;
    g.lineWidth = 14 * scale;
    g.lineCap = "round";
    g.beginPath();
    g.moveTo(0, 0);
    g.quadraticCurveTo(sway * 0.4, -70 * scale, sway, -128 * scale);
    g.stroke();

    const cx = sway, cy = -150 * scale;
    g.fillStyle = PALETTE.leaf;
    for (const [dx, dy, r] of [
      [0, 0, 52],
      [-38, 16, 38],
      [36, 14, 40],
      [4, -34, 36],
    ]) {
      g.beginPath();
      g.arc(cx + dx * scale, cy + dy * scale, r * scale, 0, Math.PI * 2);
      g.fill();
    }
    g.restore();
  }

  function lerpColor(a, b, u) {
    const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16);
    const r = Math.round(lerp((pa >> 16) & 255, (pb >> 16) & 255, u));
    const gg = Math.round(lerp((pa >> 8) & 255, (pb >> 8) & 255, u));
    const bb = Math.round(lerp(pa & 255, pb & 255, u));
    return `rgb(${r},${gg},${bb})`;
  }

  // -------------------------------------------------------------- title text

  // Canvas text, so it is never a DOM tween and stays inside the seek contract.
  function drawTitles(g, t) {
    const inA = clamp((t - 0.15) / 0.5, 0, 1);
    const inB = clamp((t - 2.7) / 0.6, 0, 1);
    const out = clamp((DURATION - t) / 0.6, 0, 1);
    const alpha = Math.min(out, 1);

    g.save();
    g.textAlign = "center";
    g.globalAlpha = alpha;

    // main title
    if (inA > 0) {
      const y = lerp(H * 0.28, H * 0.235, ease.out(inA));
      g.globalAlpha = alpha * inA;
      g.fillStyle = PALETTE.ink;
      g.font = `900 ${Math.round(H * 0.105)}px Outfit, Inter, sans-serif`;
      g.fillText(cfg.title, W / 2, y);

      // underline wipe
      const w = ease.out(inA) * 420;
      g.fillStyle = PALETTE.accent;
      g.fillRect(W / 2 - w / 2, y + 26, w, 9);
    }

    // subtitle
    if (inB > 0) {
      g.globalAlpha = alpha * inB;
      g.fillStyle = PALETTE.ink;
      g.font = `600 ${Math.round(H * 0.038)}px Inter, sans-serif`;
      g.fillText(cfg.subtitle, W / 2, H * 0.335 + (1 - ease.out(inB)) * 18);
    }
    g.restore();
  }

  // ------------------------------------------------------------------ stage

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  canvas.style.cssText = `position:absolute;inset:0;width:${W}px;height:${H}px;display:block`;
  STAGE.appendChild(canvas);
  const g = canvas.getContext("2d", { alpha: false });

  function renderAt(t) {
    g.save();
    g.clearRect(0, 0, W, H);
    drawScene(g, t);
    drawTitles(g, t);
    g.restore();
  }

  window.addEventListener("hf-seek", (e) => renderAt(e.detail.time));
  renderAt(0);

  // HyperFrames wants one paused, seekable timeline per composition. The canvas
  // is redrawn from `hf-seek`, but a single proxy tween gives the renderer a
  // timeline to seek — and drives the canvas through it as well.
  if (window.gsap) {
    const proxy = { t: 0 };
    const tl = gsap.timeline({ paused: true });
    tl.to(proxy, {
      t: DURATION,
      duration: DURATION,
      ease: "none",
      onUpdate: () => renderAt(proxy.t),
    });
    window.__timelines = window.__timelines || {};
    window.__timelines[STAGE.dataset.compositionId || "main"] = tl;
  }
})();
