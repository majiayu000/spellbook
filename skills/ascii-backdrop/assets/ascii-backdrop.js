/* ascii-backdrop.js — turn any moving subject into an animated ASCII backdrop. No dependencies.

   How it works: every frame each layer's subject draws itself on a small offscreen canvas
   (a few pixels per character cell). The engine reads those pixels and prints each cell in the
   layer's mode: a glyph from a density ramp, an edge-following or shape-matched glyph, a braille
   dot pattern, an ordered-dither dot, or a coloured tile. So the subject can be anything that can
   paint: a built-in shape, a word, an image or video, a per-pixel function, or your own draw code.

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
    katakana: ' ･ｰﾆｿｼﾂﾃﾊﾈﾒﾑﾜ',
    classic: ' .:-=+*#%@',
  };

  // Dark → bright. Pass one as `palette`; `background` should be at or below the first stop.
  const PALETTES = {
    abyss: ['#2b2552', '#4a5fbf', '#58c9c2', '#d8fff6'],
    ember: ['#3a1410', '#a3341c', '#f08a2c', '#fff1c8'],
    mono: ['#1b1f26', '#4b5563', '#9ca3af', '#f3f4f6'],
    phosphor: ['#0b2a12', '#14702e', '#33ff66', '#d6ffe0'],
    amber: ['#2a1a05', '#7a4a08', '#ffb000', '#fff0c2'],
    duo: ['#1a1a1a', '#555550', '#bdbab2', '#f2efe8'],
  };

  const DEFAULTS = {
    cell: { w: 9, h: 15 },
    font: '500 12px "JetBrains Mono", "SF Mono", ui-monospace, Menlo, monospace',
    ramp: RAMPS.dense,
    palette: PALETTES.abyss, // low → high intensity
    background: '#05070b',
    cutoff: 0.06, // cells dimmer than this stay empty
    highlight: 0.9, // glyph cells brighter than this print as a filled box
    texture: 0.3, // per-cell brightness grain so solid areas mix glyphs, 0–1
    shimmer: 0.12, // random glyph flicker, 0–1
    shimmerRate: 6, // glyph changes per second
    grid: 'lines', // 'lines' | 'dots' | false
    gridAlpha: 0.05,
    clear: null, // {x, y, rx, ry, strength}: fades output around the UI so text stays readable
    fps: 30,
    // Glyph layers: edges swaps in / \ | - along strong edges; match 'shape' picks the glyph whose
    // shape best fits the cell (sharper outlines, more work per frame) instead of using the ramp.
    glyph: { edges: false, edgeStrength: 0.35, match: 'ramp', charset: null, contrast: 1.6 },
    // Tile layers ({ mode: 'tile' }) print square cells in the colours the subject paints.
    tile: { size: 12, gap: 2, radius: 2, color: 'source', texture: 0.12, glyphs: 0.08, glyphChars: '·o•' },
    // Braille layers ({ mode: 'braille' }): each character cell holds a 2×4 dot grid.
    braille: { threshold: 0.35, dither: true },
    // Dither layers ({ mode: 'dither' }): ordered (Bayer 4×4) dots or squares on a fine grid.
    dither: { size: 6, shape: 'dot', levels: 4 },
    // Brighten whatever sits under the cursor, for every non-tile layer. Needs interactive: true.
    pointerGlow: null, // { radius: 120, strength: 0.6 } in CSS px
    // Terminal look on top of the frame. Keep it subtle; flicker is skipped under reduced motion.
    crt: null, // { scanlines: 0.18, glow: 0.35, vignette: 0.35, flicker: 0.03 }
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
  const BAYER4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
  const reducedMotion = () => !!(root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches);

  /* ---------- shape matching: glyph shape vectors over a 2×3 sub-grid (after Alex Harri) ---------- */
  const shapeTables = new Map();
  function shapeTable(font, chars, cw, ch) {
    const key = font + '|' + chars + '|' + cw + 'x' + ch;
    if (shapeTables.has(key)) return shapeTables.get(key);
    const S = 4, w = cw * S, h = ch * S;
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const x = c.getContext('2d', { willReadFrequently: true });
    x.font = font.replace(/(\d+(\.\d+)?)px/, (m, n) => n * S + 'px');
    x.textAlign = 'center'; x.textBaseline = 'middle';
    const list = [];
    for (const g of chars) {
      x.fillStyle = '#000'; x.fillRect(0, 0, w, h);
      x.fillStyle = '#fff'; x.fillText(g, w / 2, h / 2);
      const d = x.getImageData(0, 0, w, h).data, v = [0, 0, 0, 0, 0, 0];
      for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
        const k = Math.min(2, Math.floor((py / h) * 3)) * 2 + Math.min(1, Math.floor((px / w) * 2));
        v[k] += d[(py * w + px) * 4] / 255;
      }
      list.push({ g, v: v.map((s) => s / ((w * h) / 6)) });
    }
    const max = [0, 1, 2, 3, 4, 5].map((k) => Math.max(1e-6, ...list.map((e) => e.v[k])));
    for (const e of list) e.v = e.v.map((s, k) => s / max[k]);
    const table = { list, cache: new Map() };
    shapeTables.set(key, table);
    return table;
  }
  function nearestGlyph(table, v) {
    let key = 0;
    for (let k = 0; k < 6; k++) key = key * 16 + Math.min(15, Math.round(v[k] * 15));
    const hit = table.cache.get(key);
    if (hit) return hit;
    let best = ' ', bd = Infinity;
    for (const e of table.list) {
      let d = 0;
      for (let k = 0; k < 6; k++) { const q = e.v[k] - v[k]; d += q * q; }
      if (d < bd) { bd = d; best = e.g; }
    }
    if (table.cache.size > 60000) table.cache.clear();
    table.cache.set(key, best);
    return best;
  }

  /* ---------- engine ---------- */
  // Keep image readiness internal: reduced-motion instances redraw only when their sources load.
  const imageSources = new WeakMap();
  function create(canvas, options) {
    options = options || {};
    const o = Object.assign({}, DEFAULTS, options);
    for (const k of ['cell', 'glyph', 'tile', 'braille', 'dither']) o[k] = Object.assign({}, DEFAULTS[k], options[k]);
    const ctx = canvas.getContext('2d');
    const bg = document.createElement('canvas');
    const glowCanvas = document.createElement('canvas');
    let pal = paletteFn(o.palette);
    let W = 0, H = 0, dpr = 1;
    let raf = 0, running = false, destroyed = false, last = 0, t0 = performance.now(), tFrozen = null;
    const reduced = reducedMotion();
    const watchedSources = new Set();
    function redrawSource() { if (wanted) frame(performance.now(), true); }
    function watchSources() {
      if (!reduced) return;
      const sources = new Set(o.layers.map((L) => L && imageSources.get(L.subject)).filter(Boolean));
      for (const source of watchedSources) if (!sources.has(source)) {
        source.removeEventListener('load', redrawSource);
        source.removeEventListener('loadeddata', redrawSource);
        watchedSources.delete(source);
      }
      for (const source of sources) if (!watchedSources.has(source) && source.addEventListener) {
        source.addEventListener('load', redrawSource);
        source.addEventListener('loadeddata', redrawSource);
        watchedSources.add(source);
      }
    }
    // One pass per print mode; each samples its own offscreen canvas with sx×sy samples per cell.
    function makePass(mode) {
      const c = document.createElement('canvas');
      return { mode, canvas: c, ctx: c.getContext('2d', { willReadFrequently: true }), cols: 0, rows: 0, cw: 0, ch: 0, sx: 1, sy: 1 };
    }
    const passes = { glyph: makePass('glyph'), braille: makePass('braille'), dither: makePass('dither'), tile: makePass('tile') };
    const pointer = { x: 0, y: 0, active: false };
    let clicks = [];

    function sizePass(P, cw, ch, sx, sy) {
      Object.assign(P, { cw, ch, sx, sy });
      P.cols = Math.ceil(W / cw); P.rows = Math.ceil(H / ch);
      P.canvas.width = P.cols * sx; P.canvas.height = P.rows * sy;
    }
    function sizeAll() {
      const shape = o.glyph.match === 'shape';
      sizePass(passes.glyph, o.cell.w, o.cell.h, shape ? 2 : 1, shape ? 3 : 1);
      sizePass(passes.braille, o.cell.w, o.cell.h, 2, 4);
      sizePass(passes.dither, o.dither.size, o.dither.size, 1, 1);
      sizePass(passes.tile, o.tile.size, o.tile.size, 1, 1);
    }

    function resize() {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(root.devicePixelRatio || 1, 2);
      W = Math.max(1, Math.round(r.width));
      H = Math.max(1, Math.round(r.height));
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      sizeAll();
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

    // Paint the pass's layers into its offscreen canvas. Non-tile layers paint white light
    // (brightness = density); tile layers paint real colours.
    function paintSource(P, t, now) {
      const sctx = P.ctx, sw = P.canvas.width, sh = P.canvas.height;
      sctx.setTransform(1, 0, 0, 1, 0, 0);
      sctx.globalCompositeOperation = 'source-over';
      sctx.globalAlpha = 1;
      sctx.fillStyle = '#000';
      sctx.fillRect(0, 0, sw, sh);
      sctx.globalCompositeOperation = P.mode === 'tile' ? 'source-over' : 'lighter';
      const spx = P.cw / P.sx, spy = P.ch / P.sy; // screen px per source px
      const ax = spy / spx; // stretch x so subjects keep their real proportions on screen
      const unit = Math.min(sw / ax, sh);
      let any = false;
      for (const L of o.layers) {
        if (!L || !L.subject || (L.mode || 'glyph') !== P.mode) continue;
        any = true;
        const d = L.drift || {};
        const lx = (L.x ?? 0.5) + (d.x || 0) * Math.sin(t * (d.speed || 0.15) + (d.phase || 0));
        const ly = (L.y ?? 0.5) + (d.y || 0) * Math.cos(t * (d.speed || 0.15) * 0.8 + (d.phase || 0));
        const s = unit * (L.scale ?? 0.5);
        const rot = L.rotate || 0;
        const toLocal = (px, py) => { // screen point → this layer's local drawing units
          const gx = (px / spx - lx * sw) / ax, gy = py / spy - ly * sh;
          return { x: gx * Math.cos(-rot) - gy * Math.sin(-rot), y: gx * Math.sin(-rot) + gy * Math.cos(-rot) };
        };
        const env = {
          pointer: o.interactive && pointer.active ? toLocal(pointer.x, pointer.y) : null,
          clicks: o.interactive ? clicks.map((c) => Object.assign(toLocal(c.x, c.y), { age: (now - c.at) / 1000 })) : [],
        };
        sctx.save();
        sctx.translate(lx * sw, ly * sh);
        sctx.scale(ax, 1);
        sctx.rotate(rot);
        sctx.globalAlpha = clamp(L.depth ?? 1, 0, 1);
        sctx.fillStyle = sctx.strokeStyle = '#fff';
        try { L.subject.draw(sctx, t * (L.speed ?? 1) + (L.timeOffset || 0), s, env); } catch (e) { console.warn(e); }
        sctx.restore();
      }
      return any;
    }

    // Per-cell brightness factors shared by every non-tile pass: the clear zone scales, the cursor glow adds.
    function factors(x, y, P) {
      let mul = 1, add = 0;
      const c = o.clear;
      if (c) {
        const dx = (x / P.cols - c.x) / c.rx, dy = (y / P.rows - c.y) / c.ry;
        mul = 1 - (c.strength ?? 0.8) * clamp(1 - Math.sqrt(dx * dx + dy * dy), 0, 1) ** 0.6;
      }
      const g = o.pointerGlow;
      if (g && o.interactive && pointer.active) {
        const dx = (x + 0.5) * P.cw - pointer.x, dy = (y + 0.5) * P.ch - pointer.y;
        add = (g.strength ?? 0.6) * Math.exp(-(dx * dx + dy * dy) / ((g.radius ?? 120) ** 2));
      }
      return [mul, add];
    }
    function adjust(v, x, y, P, tg) {
      const [mul, add] = factors(x, y, P);
      v = v * mul + add;
      if (o.texture && tg >= 0) v *= 1 - o.texture * hash(x, y, tg);
      return v;
    }

    const EDGE_CHARS = ['-', '\\', '|', '/'];
    function drawGlyphs(P, t) {
      const px = P.ctx.getImageData(0, 0, P.canvas.width, P.canvas.height).data;
      const G = o.glyph, cols = P.cols, rows = P.rows, sw = P.canvas.width;
      const ramp = o.ramp, R = ramp.length - 1, cw = P.cw, ch = P.ch;
      const tick = Math.floor(t * o.shimmerRate), tg = Math.floor(t * 1.5) + 11;
      const lum = (sx, sy) => { const i = (sy * sw + sx) * 4; return Math.max(px[i], px[i + 1], px[i + 2]) / 255; };
      // per-cell brightness grid (mean of the sub-samples)
      const V = new Float32Array(cols * rows);
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
        let s = 0;
        for (let j = 0; j < P.sy; j++) for (let i = 0; i < P.sx; i++) s += lum(x * P.sx + i, y * P.sy + j);
        V[y * cols + x] = s / (P.sx * P.sy);
      }
      const table = G.match === 'shape' ? shapeTable(o.font, G.charset || ' .,:;-_=+!/\\|()<>[]{}^~\'"`*#%&@$0OoXxVvTtLlIiYy', cw, ch) : null;
      const vec = [0, 0, 0, 0, 0, 0];
      ctx.font = o.font;
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'center';
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const raw = V[y * cols + x];
          const v = adjust(raw, x, y, P, tg);
          if (v < o.cutoff) continue;
          let glyph;
          if (table) {
            // 2×3 sub-samples → shape vector, contrast-boosted, nearest glyph
            let m = 1e-6;
            for (let k = 0; k < 6; k++) { vec[k] = lum(x * 2 + (k & 1), y * 3 + (k >> 1)); m = Math.max(m, vec[k]); }
            for (let k = 0; k < 6; k++) vec[k] = Math.pow(vec[k] / m, G.contrast) * Math.min(1, v * 1.4);
            glyph = nearestGlyph(table, vec);
            if (glyph === ' ') continue;
          } else {
            const jitter = o.shimmer ? (hash(x, y, tick) - 0.5) * o.shimmer * 2 : 0;
            glyph = ramp[clamp(Math.round((v + jitter) * R), 1, R)];
          }
          if (G.edges && x > 0 && y > 0 && x < cols - 1 && y < rows - 1) {
            const at = (i, j) => V[(y + j) * cols + (x + i)];
            const sx = at(1, -1) + 2 * at(1, 0) + at(1, 1) - at(-1, -1) - 2 * at(-1, 0) - at(-1, 1);
            const sy = at(-1, 1) + 2 * at(0, 1) + at(1, 1) - at(-1, -1) - 2 * at(0, -1) - at(1, -1);
            if (Math.hypot(sx, sy) > G.edgeStrength) {
              // the edge runs perpendicular to the gradient (measured in screen px, y down);
              // quantise to 0/45/90/135 degrees: - \ | /
              const a = (((Math.atan2(sy / ch, sx / cw) + Math.PI / 2) % Math.PI) + Math.PI) % Math.PI;
              glyph = EDGE_CHARS[Math.round(a / (Math.PI / 4)) % 4];
            }
          }
          const [r, g, b] = pal(Math.pow(v, 0.85));
          const a = clamp(0.25 + v * 1.1, 0, 1);
          if (!table && v > o.highlight) {
            ctx.fillStyle = `rgba(${r},${g},${b},${a * 0.9})`;
            ctx.fillRect(x * cw + 0.5, y * ch + 1, cw - 1, ch - 2);
            ctx.fillStyle = o.background;
          } else {
            ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
          }
          ctx.fillText(glyph, x * cw + cw / 2, y * ch + ch / 2);
        }
      }
    }

    // braille dot bits for (column, row) inside the 2×4 cell
    const BRAILLE_BIT = [[0x01, 0x08], [0x02, 0x10], [0x04, 0x20], [0x40, 0x80]];
    function drawBraille(P, t) {
      const px = P.ctx.getImageData(0, 0, P.canvas.width, P.canvas.height).data;
      const B = o.braille, sw = P.canvas.width, tg = Math.floor(t * 1.5) + 11;
      ctx.font = o.font.replace(/(\d+(\.\d+)?)px/, (m, n) => Math.round(n * 1.25) + 'px');
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'center';
      for (let y = 0; y < P.rows; y++) {
        for (let x = 0; x < P.cols; x++) {
          let bits = 0, sum = 0;
          const [mul, add] = factors(x, y, P);
          for (let j = 0; j < 4; j++) for (let i = 0; i < 2; i++) {
            const sx = x * 2 + i, sy = y * 4 + j, k = (sy * sw + sx) * 4;
            const v = (Math.max(px[k], px[k + 1], px[k + 2]) / 255) * mul + add;
            sum += v;
            const th = B.dither ? B.threshold * 0.5 + BAYER4[(sy & 3) * 4 + (sx & 3)] * B.threshold : B.threshold;
            if (v > th) bits |= BRAILLE_BIT[j][i];
          }
          if (!bits) continue;
          const v = clamp(sum / 8, 0, 1) * (1 - (o.texture || 0) * 0.5 * hash(x, y, tg));
          const [r, g, b] = pal(0.35 + v * 0.65);
          ctx.fillStyle = `rgba(${r},${g},${b},${clamp(0.45 + v, 0, 1)})`;
          ctx.fillText(String.fromCharCode(0x2800 + bits), x * P.cw + P.cw / 2, y * P.ch + P.ch / 2);
        }
      }
    }

    function drawDither(P) {
      const px = P.ctx.getImageData(0, 0, P.cols, P.rows).data;
      const D = o.dither, sz = P.cw, levels = Math.max(2, D.levels | 0);
      for (let y = 0; y < P.rows; y++) {
        for (let x = 0; x < P.cols; x++) {
          const i = (y * P.cols + x) * 4;
          const v = clamp(adjust(Math.max(px[i], px[i + 1], px[i + 2]) / 255, x, y, P, -1), 0, 1);
          if (v < o.cutoff) continue;
          const th = BAYER4[(y & 3) * 4 + (x & 3)];
          if (v < th * 0.9) continue;
          const q = Math.ceil(v * (levels - 1)) / (levels - 1); // posterised level sets size and colour
          const [r, g, b] = pal(q);
          ctx.fillStyle = `rgb(${r},${g},${b})`;
          const cx = x * sz + sz / 2, cy = y * sz + sz / 2, rad = (sz / 2) * (0.45 + 0.5 * q);
          if (D.shape === 'square') ctx.fillRect(cx - rad, cy - rad, rad * 2, rad * 2);
          else { ctx.beginPath(); ctx.arc(cx, cy, rad, 0, Math.PI * 2); ctx.fill(); }
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
      const c = o.clear;
      for (let y = 0; y < P.rows; y++) {
        for (let x = 0; x < P.cols; x++) {
          const i = (y * P.cols + x) * 4;
          let r = px[i], g = px[i + 1], b = px[i + 2];
          let f = 1 - (T.texture || 0) * hash(x, y, tick + 5);
          if (c) {
            const dx = (x / P.cols - c.x) / c.rx, dy = (y / P.rows - c.y) / c.ry;
            f *= 1 - (c.strength ?? 0.8) * clamp(1 - Math.sqrt(dx * dx + dy * dy), 0, 1) ** 0.6;
          }
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

    // Terminal finish: soft phosphor glow, scanlines, vignette and a faint flicker.
    function drawCrt(t) {
      const C = o.crt;
      if (C.glow) {
        glowCanvas.width = canvas.width; glowCanvas.height = canvas.height;
        const g = glowCanvas.getContext('2d');
        g.filter = `blur(${Math.round(4 * dpr)}px)`;
        g.drawImage(canvas, 0, 0);
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalCompositeOperation = 'lighter';
        ctx.globalAlpha = C.glow;
        ctx.drawImage(glowCanvas, 0, 0);
        ctx.restore();
      }
      if (C.scanlines) {
        ctx.fillStyle = `rgba(0,0,0,${C.scanlines})`;
        for (let y = 0; y < H; y += 3) ctx.fillRect(0, y, W, 1);
      }
      if (C.vignette) {
        const v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.max(W, H) * 0.75);
        v.addColorStop(0, 'rgba(0,0,0,0)');
        v.addColorStop(1, `rgba(0,0,0,${C.vignette})`);
        ctx.fillStyle = v;
        ctx.fillRect(0, 0, W, H);
      }
      if (C.flicker && !reduced) {
        ctx.fillStyle = `rgba(0,0,0,${C.flicker * hash(Math.floor(t * 24), 3, 9)})`;
        ctx.fillRect(0, 0, W, H);
      }
    }

    function frame(now, force) {
      if (destroyed) return;
      if (!force && running) raf = requestAnimationFrame(frame);
      if (!force && now - last < 1000 / o.fps) return;
      last = now;
      const t = tFrozen ?? (now - t0) / 1000;
      clicks = clicks.filter((c) => now - c.at < 6000);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(bg, 0, 0);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (paintSource(passes.glyph, t, now)) drawGlyphs(passes.glyph, t);
      if (paintSource(passes.braille, t, now)) drawBraille(passes.braille, t);
      if (paintSource(passes.dither, t, now)) drawDither(passes.dither);
      if (paintSource(passes.tile, t, now)) drawTiles(passes.tile, t);
      if (o.crt) drawCrt(t);
      // Emitted only after a complete backdrop frame, for external performance measurement.
      canvas.dispatchEvent(new Event('ascii-backdrop:frame', { bubbles: true }));
    }

    // The canvas sits behind the UI, so listen on the window.
    function onMove(e) { const r = canvas.getBoundingClientRect(); pointer.x = e.clientX - r.left; pointer.y = e.clientY - r.top; pointer.active = true; }
    function onLeave() { pointer.active = false; }
    function onDown(e) { onMove(e); clicks.push({ x: pointer.x, y: pointer.y, at: performance.now() }); if (clicks.length > 8) clicks.shift(); }
    function syncInteraction() {
      root.removeEventListener('pointermove', onMove);
      root.removeEventListener('pointerdown', onDown);
      document.removeEventListener('pointerleave', onLeave);
      if (o.interactive && !destroyed) {
        root.addEventListener('pointermove', onMove, { passive: true });
        root.addEventListener('pointerdown', onDown, { passive: true });
        document.addEventListener('pointerleave', onLeave);
      } else { pointer.active = false; clicks = []; }
    }
    syncInteraction();

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
    watchSources();
    resize();

    return {
      start, stop,
      get options() { return o; },
      set(patch) {
        for (const k of Object.keys(patch)) {
          if (['cell', 'glyph', 'tile', 'braille', 'dither'].includes(k)) o[k] = Object.assign({}, o[k], patch[k]);
          else o[k] = patch[k];
        }
        if (patch.palette) pal = paletteFn(o.palette);
        if (patch.layers) watchSources();
        if ('interactive' in patch) syncInteraction();
        if (['palette', 'grid', 'background', 'cell', 'tile', 'dither', 'glyph'].some((k) => k in patch)) resize();
        if (!running) frame(performance.now(), true);
      },
      setLayers(layers) { o.layers = layers; watchSources(); if (!running) frame(performance.now(), true); },
      snapshot(t) { const previous = tFrozen; tFrozen = t; frame(performance.now(), true); tFrozen = previous; },
      destroy() {
        destroyed = true;
        stop(); ro && ro.disconnect();
        root.removeEventListener('resize', resize);
        for (const source of watchedSources) {
          source.removeEventListener('load', redrawSource);
          source.removeEventListener('loadeddata', redrawSource);
        }
        watchedSources.clear();
        document.removeEventListener('visibilitychange', onVis);
        syncInteraction();
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

    // A per-pixel function, like a fragment shader: fn(u, v, t) with u, v in [-0.5, 0.5] returns brightness
    // 0–1, or [r, g, b] (0–255) for tile layers. Good for plasma, interference, noise fields, gradients.
    field(fn, { resolution = 1 } = {}) {
      const c = document.createElement('canvas');
      const x = c.getContext('2d');
      return {
        draw(ctx, t, s) {
          const n = Math.max(2, Math.round(s * resolution));
          if (c.width !== n) { c.width = c.height = n; }
          const img = x.createImageData(n, n), d = img.data;
          for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
            const out = fn(i / (n - 1) - 0.5, j / (n - 1) - 0.5, t);
            const k = (j * n + i) * 4;
            if (Array.isArray(out)) { d[k] = out[0]; d[k + 1] = out[1]; d[k + 2] = out[2]; }
            else { const g = clamp(out, 0, 1) * 255; d[k] = d[k + 1] = d[k + 2] = g; }
            d[k + 3] = 255;
          }
          x.putImageData(img, 0, 0);
          ctx.imageSmoothingEnabled = true;
          ctx.drawImage(c, -s / 2, -s / 2, s, s);
        },
      };
    },

    // A shaded 3D solid by ray marching a signed distance function: 'torus' | 'sphere' | 'box' | 'capsule',
    // or your own (p) => distance with p = [x, y, z]. Lit from the upper left; it slowly turns.
    sdf({ shape = 'torus', spin = 0.6, light = [-0.5, -0.7, -0.6] } = {}) {
      const len3 = (p) => Math.hypot(p[0], p[1], p[2]);
      const SHAPES = {
        torus: (p) => Math.hypot(Math.hypot(p[0], p[2]) - 0.62, p[1]) - 0.26,
        sphere: (p) => len3(p) - 0.75,
        box: (p) => { const q = p.map((v) => Math.abs(v) - 0.55); return len3(q.map((v) => Math.max(v, 0))) + Math.min(Math.max(q[0], q[1], q[2]), 0) - 0.06; },
        capsule: (p) => Math.hypot(p[0], Math.max(Math.abs(p[1]) - 0.45, 0), p[2]) - 0.32,
      };
      const dist = typeof shape === 'function' ? shape : SHAPES[shape] || SHAPES.torus;
      const L = (() => { const m = len3(light); return light.map((v) => v / m); })();
      return subjects.field((u, v, t) => {
        const a = t * spin, b = t * spin * 0.7;
        const rot = (p) => { // turn the object, not the camera
          let [x, y, z] = p;
          [x, z] = [x * Math.cos(a) - z * Math.sin(a), x * Math.sin(a) + z * Math.cos(a)];
          [y, z] = [y * Math.cos(b) - z * Math.sin(b), y * Math.sin(b) + z * Math.cos(b)];
          return [x, y, z];
        };
        const f = (p) => dist(rot(p));
        const ro = [0, 0, -2.6], rd = (() => { const d = [u * 1.2, v * 1.2, 1.5]; const m = len3(d); return d.map((q) => q / m); })();
        let tt = 0;
        for (let i = 0; i < 48; i++) {
          const p = [ro[0] + rd[0] * tt, ro[1] + rd[1] * tt, ro[2] + rd[2] * tt];
          const d = f(p);
          if (d < 0.002) {
            const e = 0.002, n = [
              f([p[0] + e, p[1], p[2]]) - f([p[0] - e, p[1], p[2]]),
              f([p[0], p[1] + e, p[2]]) - f([p[0], p[1] - e, p[2]]),
              f([p[0], p[1], p[2] + e]) - f([p[0], p[1], p[2] - e]),
            ];
            const m = len3(n) || 1;
            const diff = Math.max(0, (n[0] * L[0] + n[1] * L[1] + n[2] * L[2]) / m); // L points toward the light
            return 0.12 + 0.88 * diff;
          }
          tt += d;
          if (tt > 6) break;
        }
        return 0;
      }, { resolution: 0.9 });
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
        if (!tinted || tintedFor !== img.src || !('naturalWidth' in img)) {
          if (!tinted) tinted = document.createElement('canvas');
          if (tinted.width !== w || tinted.height !== h) { tinted.width = w; tinted.height = h; }
          const c = tinted.getContext('2d');
          c.globalCompositeOperation = 'source-over'; c.clearRect(0, 0, w, h);
          c.drawImage(img, 0, 0);
          c.globalCompositeOperation = 'difference'; c.fillStyle = '#fff'; c.fillRect(0, 0, w, h);
          c.globalCompositeOperation = 'destination-in'; c.drawImage(img, 0, 0); // keep transparent areas empty
          tintedFor = img.src;
        }
        return { el: tinted, w, h };
      }
      const subject = {
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
      imageSources.set(subject, img);
      return subject;
    },
  };

  /* ---------- page helpers: text decode and image reveal ---------- */

  const SCRAMBLE_CHARS = '!<>-_\\/[]{}=+*^?#%@$01';

  // Decode an element's text: characters cycle through noise and settle left to right.
  // trigger: 'load' | 'hover' | 'view' | 'manual'. Returns { play, destroy }.
  function scramble(el, { trigger = 'load', duration = 900, stagger = 28, chars = SCRAMBLE_CHARS, seed = 1 } = {}) {
    const final = el.textContent;
    let raf = 0;
    function play() {
      cancelAnimationFrame(raf);
      if (reducedMotion()) { el.textContent = final; return; }
      const t0 = performance.now();
      const step = (now) => {
        const e = now - t0;
        let out = '', done = true;
        for (let i = 0; i < final.length; i++) {
          const settle = i * stagger + duration * (0.4 + 0.6 * hash(i, seed, 3));
          if (e >= settle || final[i] === ' ') out += final[i];
          else { done = false; out += chars[Math.floor(hash(i, Math.floor(e / 50), seed) * chars.length)]; }
        }
        el.textContent = out;
        if (!done) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    }
    let io = null;
    if (trigger === 'load') play();
    if (trigger === 'hover') el.addEventListener('pointerenter', play);
    if (trigger === 'view' && root.IntersectionObserver) {
      io = new IntersectionObserver((es) => es.forEach((x) => x.isIntersecting && play()), { threshold: 0.6 });
      io.observe(el);
    }
    return {
      play,
      destroy() { cancelAnimationFrame(raf); el.textContent = final; el.removeEventListener('pointerenter', play); io && io.disconnect(); },
    };
  }

  // Show an image as characters that dissolve cell by cell into the picture.
  // The image must be same-origin (or data:/blob:). It needs a positioned parent; the overlay sits on top.
  // trigger: 'scroll' (progress follows the element through the viewport) | 'hover' | 'load' | 'manual'.
  // pattern: 'down' | 'up' | 'center' | 'edges' | 'random'. Returns { progress(p), destroy }.
  function reveal(img, opts = {}) {
    const o = Object.assign({ trigger: 'hover', pattern: 'center', cell: { w: 8, h: 13 }, ramp: RAMPS.dense,
      color: '#e8e4dc', background: '#0d0d0d', band: 0.12, duration: 1100,
      font: '500 11px "JetBrains Mono", ui-monospace, Menlo, monospace' }, opts);
    const cv = document.createElement('canvas');
    cv.setAttribute('aria-hidden', 'true');
    Object.assign(cv.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', pointerEvents: 'none' });
    img.insertAdjacentElement('afterend', cv);
    const ctx = cv.getContext('2d');
    const sample = document.createElement('canvas');
    const sx = sample.getContext('2d', { willReadFrequently: true });
    let lum = null, cols = 0, rows = 0, W = 0, H = 0, dpr = 1, p = 0, target = 0, raf = 0;
    let destroyed = false, loadStarted = false;
    function prepare() {
      if (destroyed) return;
      const r = img.getBoundingClientRect();
      if (!r.width || !(img.naturalWidth || img.videoWidth)) return;
      dpr = Math.min(root.devicePixelRatio || 1, 2);
      W = r.width; H = r.height;
      cv.width = W * dpr; cv.height = H * dpr;
      cols = Math.ceil(W / o.cell.w); rows = Math.ceil(H / o.cell.h);
      sample.width = cols; sample.height = rows;
      sx.drawImage(img, 0, 0, cols, rows);
      const d = sx.getImageData(0, 0, cols, rows).data;
      lum = new Float32Array(cols * rows);
      for (let i = 0; i < cols * rows; i++) lum[i] = (0.2126 * d[i * 4] + 0.7152 * d[i * 4 + 1] + 0.0722 * d[i * 4 + 2]) / 255;
      draw();
      if (o.trigger === 'load' && !loadStarted) { loadStarted = true; animateTo(1); }
    }
    function order(x, y) { // 0 = dissolves first, 1 = last
      const u = x / cols, v = y / rows, n = hash(x, y, 77) * 0.15;
      if (o.pattern === 'down') return v * 0.85 + n;
      if (o.pattern === 'up') return (1 - v) * 0.85 + n;
      if (o.pattern === 'edges') return (1 - Math.max(Math.abs(u - 0.5), Math.abs(v - 0.5)) * 2) * 0.85 + n;
      if (o.pattern === 'random') return hash(x, y, 78);
      return Math.min(1, Math.hypot(u - 0.5, (v - 0.5) * (H / W)) * 1.6) * 0.85 + n;
    }
    function draw() {
      if (!lum) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      if (reducedMotion()) return;
      ctx.font = o.font; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      const R = o.ramp.length - 1, [r, g, b] = hexRgb(o.color), tick = Math.floor(performance.now() / 60);
      const pp = p * (1 + o.band); // progress runs a band past 1 so the last cells clear fully
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
        const k = Math.min(1, order(x, y));
        if (pp > k + o.band) continue; // fully revealed: the image shows through
        const edge = pp > k; // inside the moving band: bright noise glyphs over the picture
        const X = x * o.cell.w, Y = y * o.cell.h;
        if (!edge) { ctx.fillStyle = o.background; ctx.fillRect(X, Y, o.cell.w, o.cell.h); }
        const v = lum[y * cols + x];
        const ch = edge ? SCRAMBLE_CHARS[Math.floor(hash(x, y, tick) * SCRAMBLE_CHARS.length)] : o.ramp[Math.max(1, Math.round(v * R))];
        ctx.fillStyle = `rgba(${r},${g},${b},${edge ? 0.95 : 0.25 + v * 0.75})`;
        ctx.fillText(ch, X + o.cell.w / 2, Y + o.cell.h / 2);
      }
    }
    function animateTo(to) {
      if (destroyed) return;
      target = to;
      cancelAnimationFrame(raf);
      if (reducedMotion()) { p = to; draw(); return; }
      let last = performance.now();
      const step = (now) => {
        const dp = (now - last) / o.duration; last = now;
        p = to > p ? Math.min(to, p + dp) : Math.max(to, p - dp);
        draw();
        if (p !== target) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    }
    function onScroll() {
      const r = img.getBoundingClientRect(), vh = root.innerHeight;
      p = clamp((vh - r.top) / (vh * 0.6 + r.height * 0.4) - 0.2, 0, 1);
      draw();
    }
    const enter = () => animateTo(1), leave = () => animateTo(0);
    const host = img.parentElement;
    if (o.trigger === 'hover') { host.addEventListener('pointerenter', enter); host.addEventListener('pointerleave', leave); }
    if (o.trigger === 'scroll') root.addEventListener('scroll', onScroll, { passive: true });
    const ro = root.ResizeObserver ? new ResizeObserver(() => { prepare(); if (o.trigger === 'scroll') onScroll(); }) : null;
    if (img.complete === false && img.addEventListener) img.addEventListener('load', prepare, { once: true });
    if (ro) ro.observe(img);
    prepare();
    return {
      progress(v) { cancelAnimationFrame(raf); p = target = clamp(v, 0, 1); draw(); },
      play: enter, rewind: leave,
      destroy() {
        destroyed = true;
        cancelAnimationFrame(raf); ro && ro.disconnect(); cv.remove();
        img.removeEventListener('load', prepare);
        host.removeEventListener('pointerenter', enter); host.removeEventListener('pointerleave', leave);
        root.removeEventListener('scroll', onScroll);
      },
    };
  }

  root.AsciiBackdrop = { create, subjects, scramble, reveal, RAMPS, PALETTES, helpers: { softDot, strand, hash, lerp, clamp } };
})(typeof window !== 'undefined' ? window : globalThis);
