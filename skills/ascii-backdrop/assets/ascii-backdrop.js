/* ascii-backdrop.js — turn any moving subject into an animated ASCII backdrop. No dependencies.

   How it works: every frame each layer's subject draws itself in white on a tiny offscreen canvas
   (one pixel per character cell). The engine reads the brightness of each pixel and prints a glyph
   from a density ramp, coloured by a palette. So the subject can be anything that can paint:
   a built-in shape, a word, an image or video, or your own draw function.

   const bd = AsciiBackdrop.create(canvas, {
     layers: [{ subject: AsciiBackdrop.subjects.jellyfish(), x: .3, y: .35, scale: .55, depth: 1 }],
   });
   bd.start();
*/
(function (root) {
  'use strict';

  const RAMPS = {
    dense: " .':-=+ot%SX8@",
    soft: " .·:'ot%S8@",
    binary: ' 01',
    blocks: ' ░▒▓█',
    dots: ' ·•●',
  };

  const DEFAULTS = {
    cell: { w: 9, h: 15 },
    font: '500 12px "JetBrains Mono", "SF Mono", ui-monospace, Menlo, monospace',
    ramp: RAMPS.dense,
    palette: ['#2b2552', '#4a5fbf', '#58c9c2', '#d8fff6'], // low → high intensity
    background: '#05070b',
    cutoff: 0.06, // cells dimmer than this stay empty
    highlight: 0.9, // cells brighter than this print as a filled box
    texture: 0.3, // per-cell brightness grain so solid areas mix glyphs, 0–1
    shimmer: 0.12, // random glyph flicker, 0–1
    shimmerRate: 6, // glyph changes per second
    grid: 'lines', // 'lines' | 'dots' | false
    gridAlpha: 0.05,
    clear: null, // {x, y, rx, ry, strength}: fades glyphs around the UI so text stays readable
    fps: 30,
    // Tile layers ({ mode: 'tile' }) print square cells in the colours the subject paints.
    tile: { size: 12, gap: 2, radius: 2, color: 'source', texture: 0.12, glyphs: 0.08, glyphChars: '·o•' },
    interactive: false, // pass pointer position and recent clicks to subjects as draw(ctx, t, s, env)
    layers: [],
  };

  /* ---------- small helpers ---------- */
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const lerp = (a, b, t) => a + (b - a) * t;
  function hash(x, y, z) {
    let h = (x * 374761393 + y * 668265263 + z * 2147483647) | 0;
    h = (h ^ (h >>> 13)) * 1274126177;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
  }
  function hexRgb(h) {
    const s = h.replace('#', '');
    const n = parseInt(s.length === 3 ? s.replace(/./g, (c) => c + c) : s, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function paletteFn(stops) {
    const rgb = stops.map(hexRgb);
    return (t) => {
      const f = clamp(t, 0, 1) * (rgb.length - 1);
      const i = Math.min(Math.floor(f), rgb.length - 2);
      const k = f - i;
      return rgb[i].map((c, j) => Math.round(lerp(c, rgb[i + 1][j], k)));
    };
  }

  /* ---------- engine ---------- */
  function create(canvas, options) {
    const o = Object.assign({}, DEFAULTS, options);
    o.cell = Object.assign({}, DEFAULTS.cell, options && options.cell);
    o.tile = Object.assign({}, DEFAULTS.tile, options && options.tile);
    const ctx = canvas.getContext('2d');
    const bg = document.createElement('canvas');
    let pal = paletteFn(o.palette);
    let W = 0, H = 0, dpr = 1;
    let raf = 0, running = false, last = 0, t0 = performance.now(), tFrozen = null;
    const reduced = root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches;
    // Two passes share the layer list: 'glyph' layers print characters, 'tile' layers print coloured squares.
    function makePass(mode) {
      const c = document.createElement('canvas');
      return { mode, canvas: c, ctx: c.getContext('2d', { willReadFrequently: true }), cols: 0, rows: 0, cw: 0, ch: 0 };
    }
    const passes = { glyph: makePass('glyph'), tile: makePass('tile') };
    const pointer = { x: 0, y: 0, active: false };
    let clicks = [];

    function sizePass(P, cw, ch) {
      P.cw = cw; P.ch = ch;
      P.cols = Math.ceil(W / cw); P.rows = Math.ceil(H / ch);
      P.canvas.width = P.cols; P.canvas.height = P.rows;
    }

    function resize() {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(root.devicePixelRatio || 1, 2);
      W = Math.max(1, Math.round(r.width));
      H = Math.max(1, Math.round(r.height));
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      sizePass(passes.glyph, o.cell.w, o.cell.h);
      sizePass(passes.tile, o.tile.size, o.tile.size);
      drawGrid();
      if (!running) frame(performance.now(), true);
    }

    function drawGrid() {
      bg.width = canvas.width;
      bg.height = canvas.height;
      const b = bg.getContext('2d');
      b.setTransform(dpr, 0, 0, dpr, 0, 0);
      b.fillStyle = o.background;
      b.fillRect(0, 0, W, H);
      if (!o.grid) return;
      const [r, g, bl] = hexRgb(o.palette[o.palette.length - 1]);
      b.fillStyle = b.strokeStyle = `rgba(${r},${g},${bl},${o.gridAlpha})`;
      const { cols, rows } = passes.glyph;
      if (o.grid === 'lines') {
        b.lineWidth = 0.5;
        b.beginPath();
        for (let x = 0; x <= W; x += o.cell.w * 2) { b.moveTo(x + 0.25, 0); b.lineTo(x + 0.25, H); }
        for (let y = 0; y <= H; y += o.cell.h * 2) { b.moveTo(0, y + 0.25); b.lineTo(W, y + 0.25); }
        b.stroke();
      } else {
        for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++)
          if (hash(x, y, 7) < 0.035) b.fillRect(x * o.cell.w + o.cell.w / 2, y * o.cell.h + o.cell.h / 2, 1, 1);
      }
    }

    // Paint the pass's layers into its low-res source canvas: one pixel per cell.
    // Glyph layers paint white light (brightness = density); tile layers paint real colours.
    function paintSource(P, t, now) {
      const sctx = P.ctx, cols = P.cols, rows = P.rows;
      sctx.setTransform(1, 0, 0, 1, 0, 0);
      sctx.globalCompositeOperation = 'source-over';
      sctx.globalAlpha = 1;
      sctx.fillStyle = '#000';
      sctx.fillRect(0, 0, cols, rows);
      sctx.globalCompositeOperation = P.mode === 'glyph' ? 'lighter' : 'source-over';
      // cells may be taller than wide; stretch x so subjects keep their real proportions on screen
      const ax = P.ch / P.cw;
      const unit = Math.min(cols / ax, rows);
      let any = false;
      for (const L of o.layers) {
        if (!L || !L.subject || (L.mode || 'glyph') !== P.mode) continue;
        any = true;
        const d = L.drift || {};
        const lx = (L.x ?? 0.5) + (d.x || 0) * Math.sin(t * (d.speed || 0.15) + (d.phase || 0));
        const ly = (L.y ?? 0.5) + (d.y || 0) * Math.cos(t * (d.speed || 0.15) * 0.8 + (d.phase || 0));
        const s = unit * (L.scale ?? 0.5);
        const rot = L.rotate || 0;
        // screen point → this layer's local drawing units
        const toLocal = (px, py) => {
          const gx = (px / P.cw - lx * cols) / ax, gy = py / P.ch - ly * rows;
          return { x: gx * Math.cos(-rot) - gy * Math.sin(-rot), y: gx * Math.sin(-rot) + gy * Math.cos(-rot) };
        };
        const env = {
          pointer: o.interactive && pointer.active ? toLocal(pointer.x, pointer.y) : null,
          clicks: o.interactive ? clicks.map((c) => Object.assign(toLocal(c.x, c.y), { age: (now - c.at) / 1000 })) : [],
        };
        sctx.save();
        sctx.translate(lx * cols, ly * rows);
        sctx.scale(ax, 1);
        sctx.rotate(rot);
        sctx.globalAlpha = clamp(L.depth ?? 1, 0, 1);
        sctx.fillStyle = sctx.strokeStyle = '#fff';
        try { L.subject.draw(sctx, t * (L.speed ?? 1) + (L.timeOffset || 0), s, env); } catch (e) { console.warn(e); }
        sctx.restore();
      }
      return any;
    }

    function clearFactor(x, y, cols, rows) {
      const c = o.clear;
      if (!c) return 1;
      const dx = (x / cols - c.x) / c.rx, dy = (y / rows - c.y) / c.ry;
      return 1 - (c.strength ?? 0.8) * clamp(1 - Math.sqrt(dx * dx + dy * dy), 0, 1) ** 0.6;
    }

    function drawGlyphs(P, t) {
      const px = P.ctx.getImageData(0, 0, P.cols, P.rows).data;
      ctx.font = o.font;
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'center';
      const ramp = o.ramp, R = ramp.length - 1, cw = P.cw, ch = P.ch;
      const tick = Math.floor(t * o.shimmerRate);
      for (let y = 0; y < P.rows; y++) {
        for (let x = 0; x < P.cols; x++) {
          const i = (y * P.cols + x) * 4;
          let v = (Math.max(px[i], px[i + 1], px[i + 2]) / 255) * clearFactor(x, y, P.cols, P.rows);
          if (o.texture) v *= 1 - o.texture * hash(x, y, Math.floor(t * 1.5) + 11);
          if (v < o.cutoff) continue;
          const jitter = o.shimmer ? (hash(x, y, tick) - 0.5) * o.shimmer * 2 : 0;
          const k = clamp(Math.round((v + jitter) * R), 1, R);
          const [r, g, b] = pal(Math.pow(v, 0.85));
          const a = clamp(0.25 + v * 1.1, 0, 1);
          if (v > o.highlight) {
            ctx.fillStyle = `rgba(${r},${g},${b},${a * 0.9})`;
            ctx.fillRect(x * cw + 0.5, y * ch + 1, cw - 1, ch - 2);
            ctx.fillStyle = o.background;
          } else {
            ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
          }
          ctx.fillText(ramp[k], x * cw + cw / 2, y * ch + ch / 2);
        }
      }
    }

    function drawTiles(P, t) {
      const px = P.ctx.getImageData(0, 0, P.cols, P.rows).data;
      const T = o.tile, sz = P.cw, gap = T.gap, r0 = Math.min(T.radius, (sz - gap) / 2);
      const tick = Math.floor(t * 1.5);
      ctx.font = `600 ${Math.round(sz * 0.55)}px ${o.font.split('px ').pop()}`;
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'center';
      for (let y = 0; y < P.rows; y++) {
        for (let x = 0; x < P.cols; x++) {
          const i = (y * P.cols + x) * 4;
          let r = px[i], g = px[i + 1], b = px[i + 2];
          const f = clearFactor(x, y, P.cols, P.rows) * (1 - (T.texture || 0) * hash(x, y, tick + 5));
          const v = (Math.max(r, g, b) / 255) * f;
          if (v < o.cutoff) continue;
          if (T.color === 'palette') [r, g, b] = pal(v);
          else { r *= f; g *= f; b *= f; }
          ctx.fillStyle = `rgb(${r | 0},${g | 0},${b | 0})`;
          const X = x * sz + gap / 2, Y = y * sz + gap / 2, S = sz - gap;
          if (r0 > 0 && ctx.roundRect) { ctx.beginPath(); ctx.roundRect(X, Y, S, S, r0); ctx.fill(); }
          else ctx.fillRect(X, Y, S, S);
          if (T.glyphs && v > 0.55 && hash(x, y, 31) < T.glyphs) {
            ctx.fillStyle = 'rgba(0,0,0,0.55)';
            ctx.fillText(T.glyphChars[Math.floor(hash(x, y, 37) * T.glyphChars.length)], X + S / 2, Y + S / 2 + 0.5);
          }
        }
      }
    }

    function frame(now, force) {
      if (!force && running) raf = requestAnimationFrame(frame);
      if (!force && now - last < 1000 / o.fps) return;
      last = now;
      const t = tFrozen ?? (now - t0) / 1000;
      clicks = clicks.filter((c) => now - c.at < 6000);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(bg, 0, 0);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (paintSource(passes.glyph, t, now)) drawGlyphs(passes.glyph, t);
      if (paintSource(passes.tile, t, now)) drawTiles(passes.tile, t);
    }

    // The canvas sits behind the UI, so listen on the window.
    function onMove(e) { pointer.x = e.clientX - canvas.getBoundingClientRect().left; pointer.y = e.clientY - canvas.getBoundingClientRect().top; pointer.active = true; }
    function onLeave() { pointer.active = false; }
    function onDown(e) { onMove(e); clicks.push({ x: pointer.x, y: pointer.y, at: performance.now() }); if (clicks.length > 8) clicks.shift(); }
    if (o.interactive) {
      root.addEventListener('pointermove', onMove, { passive: true });
      root.addEventListener('pointerdown', onDown, { passive: true });
      document.addEventListener('pointerleave', onLeave);
    }

    const ro = root.ResizeObserver ? new ResizeObserver(resize) : null;
    function onVis() { if (document.hidden) pause(); else if (wanted) start(); }
    let wanted = false;
    function start() {
      wanted = true;
      if (running) return;
      if (reduced) { tFrozen = 2.2; frame(performance.now(), true); return; }
      running = true;
      raf = requestAnimationFrame(frame);
    }
    function pause() { running = false; cancelAnimationFrame(raf); }
    function stop() { wanted = false; pause(); }

    if (ro) ro.observe(canvas); else root.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', onVis);
    resize();

    return {
      start, stop,
      get options() { return o; },
      set(patch) {
        Object.assign(o, patch);
        if (patch.tile) o.tile = Object.assign({}, DEFAULTS.tile, patch.tile);
        if (patch.palette) pal = paletteFn(o.palette);
        if (patch.palette || patch.grid !== undefined || patch.background || patch.cell || patch.tile) resize();
        if (!running) frame(performance.now(), true);
      },
      setLayers(layers) { o.layers = layers; if (!running) frame(performance.now(), true); },
      snapshot(t) { tFrozen = t; frame(performance.now(), true); tFrozen = null; },
      destroy() {
        stop(); ro && ro.disconnect();
        document.removeEventListener('visibilitychange', onVis);
        root.removeEventListener('pointermove', onMove);
        root.removeEventListener('pointerdown', onDown);
        document.removeEventListener('pointerleave', onLeave);
      },
    };
  }

  /* ---------- subjects ----------
     A subject is { draw(ctx, t, s, env) }: draw around the origin, roughly inside [-s/2, s/2].
     Glyph layers: paint white; brightness becomes glyph density. Tile layers: paint real colours.
     env.pointer is the cursor in the same local units (or null); env.clicks is [{ x, y, age }].
     Brightness (alpha, gradients, line width) becomes glyph density. Nothing here is special:
     any function that paints works. These are starting points, not the menu. */

  const TAU = Math.PI * 2;

  function softDot(ctx, x, y, r, a) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, `rgba(255,255,255,${a})`);
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, TAU);
    ctx.fill();
  }

  // A trailing line that fades from root to tip; the building block for tentacles, hair, kelp, smoke.
  function strand(ctx, pts, w0, w1, a0, a1) {
    for (let j = 1; j < pts.length; j++) {
      const k = j / (pts.length - 1);
      ctx.strokeStyle = `rgba(255,255,255,${lerp(a0, a1, k)})`;
      ctx.lineWidth = lerp(w0, w1, k);
      ctx.beginPath();
      ctx.moveTo(pts[j - 1][0], pts[j - 1][1]);
      ctx.lineTo(pts[j][0], pts[j][1]);
      ctx.stroke();
    }
  }

  const subjects = {
    // Any draw function. This is the general case; everything below is a preset of it.
    custom(draw) { return { draw }; },

    // Pulsing bell with trailing tentacles. The origin is the rim of the bell; tentacles hang below it.
    jellyfish({ tentacles = 8, arms = 3, seed = 1 } = {}) {
      return {
        draw(ctx, t, s) {
          const p = 0.5 + 0.5 * Math.sin(t * 1.4 + seed);
          const bw = s * 0.3 * (1 + 0.08 * p), bh = s * 0.27 * (1 - 0.12 * p);
          ctx.lineCap = 'round';
          // tentacles: a wave travels from the bell to the tip, so they trail instead of wagging
          for (let i = 0; i < tentacles; i++) {
            const f = tentacles === 1 ? 0.5 : i / (tentacles - 1);
            const x0 = lerp(-bw * 0.9, bw * 0.9, f);
            const L = s * (0.75 + 0.45 * hash(i, seed, 3));
            const pts = [];
            for (let j = 0; j <= 36; j++) {
              const k = j / 36;
              const sway = Math.sin(t * 1.2 - k * 5 + i * 1.9 + seed) * s * 0.09 * k + Math.sin(t * 0.4 + i) * s * 0.05 * k * k;
              pts.push([x0 * (1 - 0.35 * k) + sway, k * L]);
            }
            strand(ctx, pts, s * 0.014, s * 0.002, 0.55, 0.0);
          }
          for (let a = 0; a < arms; a++) {
            const x0 = (a - (arms - 1) / 2) * bw * 0.22;
            const pts = [];
            for (let j = 0; j <= 24; j++) {
              const k = j / 24;
              pts.push([x0 + Math.sin(t * 0.9 - k * 4 + a * 2) * s * 0.05 * (0.2 + k), k * s * 0.5]);
            }
            strand(ctx, pts, s * 0.03, s * 0.006, 0.45, 0.02);
          }
          // bell: bright dome with a scalloped rim
          const g = ctx.createRadialGradient(0, -bh * 0.55, 0, 0, -bh * 0.3, bw * 1.15);
          g.addColorStop(0, 'rgba(255,255,255,1)');
          g.addColorStop(0.45, 'rgba(255,255,255,0.85)');
          g.addColorStop(0.8, 'rgba(255,255,255,0.45)');
          g.addColorStop(1, 'rgba(255,255,255,0.2)');
          ctx.fillStyle = g;
          ctx.beginPath();
          ctx.ellipse(0, 0, bw, bh, 0, Math.PI, TAU);
          const lobes = 9;
          for (let i = 1; i <= lobes; i++) {
            const xa = bw - (2 * bw * (i - 0.5)) / lobes, xb = bw - (2 * bw * i) / lobes;
            ctx.quadraticCurveTo(xa, bh * 0.14 * (1 + 0.4 * Math.sin(t * 3 + i)), xb, 0);
          }
          ctx.fill();
          ctx.strokeStyle = 'rgba(255,255,255,0.8)';
          ctx.lineWidth = s * 0.016;
          ctx.beginPath();
          ctx.ellipse(0, 0, bw, bh, 0, Math.PI * 1.08, Math.PI * 1.92);
          ctx.stroke();
          for (let i = 0; i < 4; i++) softDot(ctx, (i - 1.5) * bw * 0.32, -bh * 0.3, bw * 0.22, 0.35);
        },
      };
    },

    // A loose school of small bodies moving together — fish, birds, sparks.
    school({ count = 26, seed = 2 } = {}) {
      return {
        draw(ctx, t, s) {
          for (let i = 0; i < count; i++) {
            const ph = hash(i, seed, 1) * TAU, r = 0.15 + 0.25 * hash(i, seed, 2);
            const sp = 0.25 + 0.15 * hash(i, seed, 4);
            const x = Math.cos(t * sp + ph) * s * r * 1.4, y = Math.sin(t * sp * 1.3 + ph) * s * r * 0.7;
            const dx = -Math.sin(t * sp + ph) * 1.4, dy = Math.cos(t * sp * 1.3 + ph) * 0.9;
            const len = s * (0.08 + 0.04 * hash(i, seed, 5));
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(Math.atan2(dy, dx));
            ctx.globalAlpha *= 0.55 + 0.45 * hash(i, seed, 6);
            ctx.beginPath();
            ctx.ellipse(0, 0, len, len * 0.4, 0, 0, TAU);
            ctx.moveTo(-len * 0.9, 0);
            ctx.lineTo(-len * 1.5, len * 0.35 * Math.sin(t * 8 + i));
            ctx.lineTo(-len * 1.5, -len * 0.35);
            ctx.fill();
            ctx.restore();
          }
        },
      };
    },

    // Drifting soft blobs: smoke, nebula, clouds, aurora.
    cloud({ puffs = 14, seed = 3 } = {}) {
      return {
        draw(ctx, t, s) {
          for (let i = 0; i < puffs; i++) {
            const ph = hash(i, seed, 1) * TAU;
            const x = Math.sin(t * 0.17 + ph) * s * 0.35 + (hash(i, seed, 2) - 0.5) * s * 0.4;
            const y = Math.cos(t * 0.13 + ph * 1.3) * s * 0.18 + (hash(i, seed, 3) - 0.5) * s * 0.25;
            softDot(ctx, x, y, s * (0.12 + 0.12 * hash(i, seed, 4)), 0.35 + 0.3 * Math.sin(t * 0.5 + ph) ** 2);
          }
        },
      };
    },

    // Rooted strands swaying in a current: kelp, grass, hair, flames (set flip:true for upward fire).
    strands({ count = 9, seed = 4, flip = false } = {}) {
      return {
        draw(ctx, t, s) {
          ctx.lineCap = 'round';
          const dir = flip ? -1 : 1;
          for (let i = 0; i < count; i++) {
            const x0 = (i / Math.max(1, count - 1) - 0.5) * s * 0.7;
            const L = s * (0.5 + 0.4 * hash(i, seed, 1));
            const pts = [];
            for (let j = 0; j <= 30; j++) {
              const k = j / 30;
              pts.push([x0 + Math.sin(t * 0.8 - k * 3 + i) * s * 0.14 * k, dir * (s * 0.45 - k * L)]);
            }
            strand(ctx, pts, s * 0.05, s * 0.012, 0.95, 0.2);
          }
        },
      };
    },

    // Particles that rise, shrink and fade: fire, bubbles, sparks, steam. Set fall:true for snow or rain.
    rising({ count = 70, seed = 6, fall = false, spread = 0.5 } = {}) {
      return {
        draw(ctx, t, s) {
          const dir = fall ? 1 : -1;
          for (let i = 0; i < count; i++) {
            const sp = 0.25 + 0.35 * hash(i, seed, 1);
            const life = (t * sp + hash(i, seed, 2)) % 1;
            const x = (hash(i, seed, 3) - 0.5) * s * spread * (1 - 0.6 * life) + Math.sin(t * 2 + i) * s * 0.03 * life;
            const y = -dir * s * 0.45 + dir * life * s * 0.95;
            softDot(ctx, x, y, s * (0.09 * (1 - life) + 0.015), 0.9 * (1 - life));
          }
        },
      };
    },

    // For tile layers ({ mode: 'tile' }): tapered, segmented bodies that wander on smooth paths in their own
    // colours and veer away from the cursor. Pass your own colour sets; each is { base, mark, accent }.
    wanderers({ count = 6, seed = 7, colors } = {}) {
      const P = colors || [
        { base: '#e6e2da', mark: '#9aa7b8', accent: null },
        { base: '#c9d3cf', mark: '#6f8f8a', accent: '#3a3f44' },
        { base: '#d9c7a7', mark: '#efe6d6', accent: null },
        { base: '#b9b3c9', mark: '#e6e2da', accent: '#45414f' },
      ];
      return {
        draw(ctx, t, s, env) {
          for (let i = 0; i < count; i++) {
            const h = (k) => hash(i, seed, k);
            const sp = 0.05 + 0.05 * h(1), ph = h(2) * TAU;
            const path = (tt) => [
              Math.sin(tt * sp + ph) * s * 0.42 + Math.sin(tt * sp * 2.3 + ph * 2) * s * 0.07,
              Math.cos(tt * sp * 0.8 + ph * 1.7) * s * 0.2 + Math.sin(tt * sp * 1.9 + ph) * s * 0.04,
            ];
            let [x, y] = path(t);
            const [x2, y2] = path(t + 0.2);
            let dir = Math.atan2(y2 - y, x2 - x);
            const len = s * (0.1 + 0.04 * h(3));
            if (env && env.pointer) { // veer away: push and turn, strongest when the cursor is close
              const dx = x - env.pointer.x, dy = y - env.pointer.y, d = Math.hypot(dx, dy) || 1;
              const k = Math.exp(-((d / (len * 1.6)) ** 2));
              x += (dx / d) * len * 0.9 * k;
              y += (dy / d) * len * 0.9 * k;
              const away = Math.atan2(dy, dx);
              dir += Math.atan2(Math.sin(away - dir), Math.cos(away - dir)) * k * 0.8;
            }
            const pat = P[Math.floor(h(4) * P.length)];
            const deep = 0.55 + 0.45 * h(5);
            const beat = t * (3 + 2 * h(6)) + ph;
            const N = 16, spine = [];
            for (let k = 0; k <= N; k++) {
              const u = k / N, back = u * len, sway = Math.sin(beat - u * 4) * len * 0.12 * u * u;
              spine.push([x - Math.cos(dir) * back - Math.sin(dir) * sway, y - Math.sin(dir) * back + Math.cos(dir) * sway]);
            }
            ctx.save();
            ctx.globalAlpha *= deep;
            for (let k = N; k >= 0; k--) {
              const u = k / N;
              const prof = u < 0.2 ? 0.7 + 1.5 * u : 1 - (u - 0.2) * 1.05;
              const r = len * 0.21 * Math.max(prof, 0.12);
              const mark = hash(i * 7 + Math.floor(u * 5), seed, 9) < 0.5;
              const accent = pat.accent && hash(i * 13 + k, seed, 10) < 0.18;
              ctx.fillStyle = accent ? pat.accent : mark && u > 0.08 ? pat.mark : pat.base;
              ctx.beginPath();
              ctx.arc(spine[k][0], spine[k][1], r, 0, TAU);
              ctx.fill();
            }
            ctx.restore();
          }
        },
      };
    },

    // Water rings for glyph layers: a few slow ambient rings plus a ring for every click.
    ripples({ ambient = 5, seed = 8, period = 7 } = {}) {
      function ring(ctx, x, y, r, a) {
        if (a <= 0.01 || r <= 0) return;
        ctx.strokeStyle = `rgba(255,255,255,${a})`;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, TAU);
        ctx.stroke();
      }
      return {
        draw(ctx, t, s, env) {
          for (let i = 0; i < ambient; i++) {
            const life = ((t + hash(i, seed, 1) * period) % period) / period;
            const cycle = Math.floor((t + hash(i, seed, 1) * period) / period);
            const x = (hash(i, cycle, 2) - 0.5) * s, y = (hash(i, cycle, 3) - 0.5) * s * 0.6;
            for (let k = 0; k < 2; k++) ring(ctx, x, y, s * 0.12 * (life + k * 0.15), 0.5 * (1 - life));
          }
          for (const c of (env && env.clicks) || []) {
            for (let k = 0; k < 3; k++) {
              const age = c.age - k * 0.25;
              if (age > 0) ring(ctx, c.x, c.y, age * s * 0.09, 0.9 * (1 - age / 3.5));
            }
          }
        },
      };
    },

    // A wireframe solid turning in 3D: products, logos-as-objects, planets.
    solid({ shape = 'icosa', seed = 5 } = {}) {
      const V = [], E = [];
      if (shape === 'cube') {
        for (let i = 0; i < 8; i++) V.push([(i & 1) * 2 - 1, (i >> 1 & 1) * 2 - 1, (i >> 2 & 1) * 2 - 1]);
        for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) if ([1, 2, 4].includes(i ^ j)) E.push([i, j]);
      } else {
        const p = (1 + Math.sqrt(5)) / 2;
        [[-1, p, 0], [1, p, 0], [-1, -p, 0], [1, -p, 0], [0, -1, p], [0, 1, p], [0, -1, -p], [0, 1, -p], [p, 0, -1], [p, 0, 1], [-p, 0, -1], [-p, 0, 1]].forEach((v) => V.push(v));
        for (let i = 0; i < 12; i++) for (let j = i + 1; j < 12; j++) {
          const d = V[i].reduce((a, c, k) => a + (c - V[j][k]) ** 2, 0);
          if (Math.abs(d - 4) < 0.01) E.push([i, j]);
        }
      }
      return {
        draw(ctx, t, s) {
          const a = t * 0.4 + seed, b = t * 0.27;
          const P = V.map(([x, y, z]) => {
            let X = x * Math.cos(a) - z * Math.sin(a), Z = x * Math.sin(a) + z * Math.cos(a);
            let Y = y * Math.cos(b) - Z * Math.sin(b); Z = y * Math.sin(b) + Z * Math.cos(b);
            const k = s * 0.22 / (1 + Z * 0.15);
            return [X * k, Y * k, Z];
          });
          ctx.lineCap = 'round';
          for (const [i, j] of E) {
            ctx.strokeStyle = `rgba(255,255,255,${0.9 - (P[i][2] + P[j][2]) * 0.12})`;
            ctx.lineWidth = s * 0.025;
            ctx.beginPath(); ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[j][0], P[j][1]); ctx.stroke();
          }
          for (const p of P) softDot(ctx, p[0], p[1], s * 0.035, 0.9 - p[2] * 0.15);
        },
      };
    },

    // Any word, name or emoji, breathing slowly.
    text(str, { weight = 800, family = 'system-ui, sans-serif' } = {}) {
      return {
        draw(ctx, t, s) {
          const k = 1 + 0.03 * Math.sin(t * 1.2);
          ctx.font = `${weight} ${s * 0.32 * k}px ${family}`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.globalAlpha *= 0.85 + 0.15 * Math.sin(t * 0.9);
          ctx.fillText(str, 0, 0);
        },
      };
    },

    // Any picture, SVG, video or canvas. Bright = dense; use invert for dark art on light paper.
    // motion: 'breathe' | 'sway' | 'float' | 'none'.
    image(source, { invert = false, motion = 'float', fit = 1 } = {}) {
      let img = source;
      if (typeof source === 'string') { img = new Image(); img.crossOrigin = 'anonymous'; img.src = source; }
      let tinted = null, tintedFor = null;
      function prepared() {
        const w = img.videoWidth || img.naturalWidth || img.width, h = img.videoHeight || img.naturalHeight || img.height;
        if (!w || !h) return null;
        if (!invert) return { el: img, w, h };
        if (tintedFor !== img.src) {
          tinted = document.createElement('canvas'); tinted.width = w; tinted.height = h;
          const c = tinted.getContext('2d');
          c.drawImage(img, 0, 0);
          c.globalCompositeOperation = 'difference'; c.fillStyle = '#fff'; c.fillRect(0, 0, w, h);
          c.globalCompositeOperation = 'destination-in'; c.drawImage(img, 0, 0); // keep transparent areas empty
          tintedFor = img.src;
        }
        return { el: tinted, w, h };
      }
      return {
        draw(ctx, t, s) {
          const p = prepared();
          if (!p) return;
          const k = (s * fit) / Math.max(p.w, p.h);
          ctx.save();
          if (motion === 'breathe' || motion === 'float') ctx.scale(1 + 0.03 * Math.sin(t * 1.3), 1 + 0.03 * Math.sin(t * 1.3));
          if (motion === 'sway' || motion === 'float') ctx.rotate(0.05 * Math.sin(t * 0.7));
          if (motion === 'float') ctx.translate(0, Math.sin(t * 0.9) * s * 0.03);
          ctx.drawImage(p.el, (-p.w * k) / 2, (-p.h * k) / 2, p.w * k, p.h * k);
          ctx.restore();
        },
      };
    },
  };

  root.AsciiBackdrop = { create, subjects, RAMPS, helpers: { softDot, strand, hash, lerp, clamp } };
})(typeof window !== 'undefined' ? window : globalThis);
