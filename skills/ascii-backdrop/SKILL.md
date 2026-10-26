---
name: ascii-backdrop
description: "Turn any subject into an animated ASCII backdrop behind a UI, like a dark prompt page with jellyfish drawn in drifting characters, or a swarm of colour-tile bodies that veer away from the cursor. The subject is open-ended: creatures, objects, particles, smoke, a word or logo, an image or video, a per-pixel field, a shaded 3D solid, or your own canvas draw function. Six print modes can be mixed: brightness glyphs, edge-following glyphs, shape-matched glyphs, braille dots, ordered-dither dots and colour tiles; plus cursor glow, click ripples, a CRT terminal finish, and two page helpers (text decode and image-to-ASCII dissolve). Ships a dependency-free JS engine with HTML and React wiring. Use when the user asks for an ASCII background, ASCII art animation, glyph or braille backdrop, text scramble/decode, or an ASCII image reveal, or says 'ASCII 背景' / '字符画动效'."
---

# ASCII Backdrop

A subject paints brightness or colour on a small canvas; the engine prints every character cell as a glyph, dot or tile. Anything that can paint on a canvas can be the subject.

## How it works

Every frame, each layer's subject draws itself on a small offscreen canvas (a few pixels per character cell). The engine reads those pixels and prints them in the layer's `mode`. A lower `depth` dims a layer, which gives depth for free; a `clear` zone fades output around the UI so headings and inputs stay readable. Changing the subject means changing one draw function; the engine does not change.

| Print mode | Layer setting | Look | Frame cost at 1440×900 (measured) |
|---|---|---|---|
| Brightness glyphs | default `mode: 'glyph'` | Glyph from the density ramp; the brightest cells print as filled boxes | ~8 ms |
| Edge glyphs | `glyph: { edges: true }` | `/ \ \| -` follow strong edges | ~8 ms |
| Shape matching | `glyph: { match: 'shape' }` | Samples a 2×3 grid per cell and picks the glyph whose shape fits best, for crisper outlines (after Alex Harri) | ~5 ms (cached) |
| Braille | `mode: 'braille'` | 2×4 dots per cell, twice the resolution, optional Bayer dither | ~6 ms |
| Dither | `mode: 'dither'` | Bayer 4×4 ordered dither, dots or squares sized by level | ~6 ms |
| Colour tiles | `mode: 'tile'` | Rounded squares in the colours the subject paints | ~3 ms |

Subjects paint in white (brightness = density); only tile layers paint real colours. Layers in different modes can share one scene.

## Files

- [`assets/ascii-backdrop.js`](assets/ascii-backdrop.js): engine, built-in subjects and page helpers, no dependencies, exposed as `window.AsciiBackdrop`. Copy it into the project.
- [`assets/demo.html`](assets/demo.html): a dark prompt page with the backdrop behind it; switch subjects, print modes, glyph sets, CRT and palettes; the heading decodes; a corner card shows the image dissolve; upload an image or video.
- [`scripts/check.mjs`](scripts/check.mjs): screenshots desktop, phone and reduced-motion views and reports errors and frame rate (needs Playwright).

## Steps

1. **Choose the subject.** Ask what it should say (a brand mascot, a product, a mood) instead of assuming a creature. Pick the source in this order:
   - Existing image, SVG, video or logo: `subjects.image(src, { invert, motion })`. Use `invert: true` for dark art on a light background.
   - A word, name or emoji: `subjects.text('…')`.
   - A mathematical field (plasma, interference, noise, gradients): `subjects.field((u, v, t) => brightness)` with u, v in [-0.5, 0.5], like a fragment shader.
   - A shaded 3D solid: `subjects.sdf({ shape: 'torus' | 'sphere' | 'box' | 'capsule' })`, or pass your own `(p) => distance`.
   - Presets: `jellyfish`, `school` (many small bodies), `cloud` (smoke, nebula), `strands` (kelp, hair; `flip: true` for flames), `rising` (fire, bubbles, sparks; `fall: true` for snow or rain), `solid` (spinning wireframe), `ripples` (ambient rings plus a ring per click), `wanderers` (tile-mode segmented bodies that wander and veer away from the cursor).
   - Nothing fits: `subjects.custom((ctx, t, s, env) => { … })` (see "Write a subject"). Presets are starting points, not the menu.
2. **Choose the print mode.** Edge glyphs or shape matching for clean outlines; braille for fine shading; dither for a printed, retro look; tiles for coloured subjects.
3. **Compose the layers.** Each layer is `{ subject, mode, x, y, scale, depth, drift, speed, timeOffset, rotate }`; `x` and `y` are 0–1 of the screen. A layout that works: one hero below the input, one above it, two faint ones at the sides (`depth` 0.4–0.6). Give repeats different `seed` or `timeOffset` values so they do not move in sync.
4. **Palette, glyphs and finish.** `palette` lists 3–5 colours from dark to bright; built-ins are `PALETTES.abyss / ember / mono / phosphor / amber / duo`. `background` matches the page. Glyph sets: `RAMPS.dense / soft / classic / binary / blocks / dots / katakana`. Add `crt` for a terminal look and keep it subtle. Aim `clear` at the heading and input.
5. **Wire it in.** Put a full-screen `<canvas>` behind the content (`position: fixed; inset: 0`), keep content above it, and give panels a translucent fill with `backdrop-filter`. React notes are below.
6. **Verify.** Run `node scripts/check.mjs page.html` and look at the three images: is the subject recognisable, are the heading and input clear, is the phone view too busy, does reduced motion show one still frame? Frame rate should be near 60. Fields and CRT cost about 16–17 ms per frame; if frames drop, raise `cell`, lower `fps`, or lower the field's `resolution`.

## Wiring

```html
<canvas id="bd" style="position:fixed;inset:0;width:100%;height:100%"></canvas>
<script src="ascii-backdrop.js"></script>
<script>
  const { subjects: S, PALETTES } = AsciiBackdrop;
  const bd = AsciiBackdrop.create(document.getElementById('bd'), {
    palette: PALETTES.abyss,
    clear: { x: 0.5, y: 0.46, rx: 0.3, ry: 0.2, strength: 0.85 },
    glyph: { edges: true },                                    // outlines in / \ | -
    interactive: true, pointerGlow: { radius: 110, strength: 0.35 },
    layers: [
      { subject: S.jellyfish({ seed: 1 }), x: 0.56, y: 0.76, scale: 0.72, depth: 1 },
      { subject: S.sdf({ shape: 'torus' }), mode: 'braille', x: 0.15, y: 0.3, scale: 0.45, depth: 0.6 },
    ],
  });
  bd.start();
</script>
```

React: call `create` inside `useEffect` and return `() => bd.destroy()`. When layers change, call `bd.setLayers(...)`; when options change, call `bd.set({...})`. Do not recreate the backdrop on every render.

## Tile mode and interaction

```js
const bd = AsciiBackdrop.create(canvas, {
  interactive: true,
  background: '#1b1a18', grid: 'dots',
  palette: ['#34322f', '#5f5c56', '#9a968e', '#e6e2da'],
  tile: { size: 12, gap: 2, radius: 2 },            // square size, gap, corner radius
  layers: [
    { subject: S.ripples(), x: 0.5, y: 0.5, scale: 1.9, depth: 0.7 },                  // glyph ripples
    { subject: S.wanderers({ count: 7 }), mode: 'tile', x: 0.5, y: 0.5, scale: 1.7 },  // tile bodies
  ],
});
```

- Tile layers paint real colours. Use dark grey instead of pure black for dark markings; pure black reads as empty. Pass your own colours with `wanderers({ colors: [{ base, mark, accent }] })`.
- With `interactive: true`, subjects receive `env.pointer` (the cursor in that layer's local units) and `env.clicks` (recent clicks with their age). `pointerGlow` brightens output near the cursor on every non-tile layer without any subject code.
- Read interaction from `env` instead of storing state in the subject. Write fleeing as "the closer the cursor, the further the push" so any moment can still be sampled directly.

## Page helpers

```js
// Heading text cycles through noise and settles left to right. trigger: 'load' | 'hover' | 'view' | 'manual'
AsciiBackdrop.scramble(document.querySelector('h1'), { trigger: 'view', duration: 900 });

// An image shows as characters, then dissolves cell by cell into the picture.
// trigger: 'hover' | 'scroll' | 'load' | 'manual'; pattern: 'center' | 'edges' | 'down' | 'up' | 'random'.
// The image needs a positioned parent and must be same-origin.
const r = AsciiBackdrop.reveal(document.querySelector('.hero img'), { trigger: 'scroll', pattern: 'edges' });
r.progress(0.5); // drive it yourself, 0–1
```

Both show the final state immediately under reduced motion.

## Write a subject

```js
const lighthouse = AsciiBackdrop.subjects.custom((ctx, t, s) => {
  // Draw around the origin, roughly inside [-s/2, s/2]. Brighter, more opaque white = denser output.
  ctx.fillRect(-s * 0.05, -s * 0.3, s * 0.1, s * 0.6);                    // tower
  AsciiBackdrop.helpers.softDot(ctx, 0, -s * 0.32, s * 0.12, 0.9);        // lamp
  ctx.save(); ctx.rotate(t * 0.8);                                          // beam
  ctx.globalAlpha *= 0.35; ctx.fillRect(0, -s * 0.33, s * 0.6, s * 0.03); ctx.restore();
});
const plasma = AsciiBackdrop.subjects.field((u, v, t) => 0.5 + 0.5 * Math.sin(10 * u + t) * Math.cos(8 * v - t));
```

- Brightness is the whole language: use alpha, gradients and line width to decide where output is dense. A flat white area becomes a wall of filled boxes; give it a gradient or lower alpha.
- Animate from `t` (seconds) and `env` only, never from the previous frame, so reduced motion, screenshots and recordings can sample any moment.
- Keep lines at least about one cell wide (`s * 0.015` or more), or they break into scattered dots.
- Helpers: `helpers.softDot(ctx, x, y, r, alpha)` for soft glows; `helpers.strand(ctx, points, w0, w1, a0, a1)` for lines that taper and fade from root to tip.

## Options

| Option | Default | Meaning |
|---|---|---|
| `cell` | `{w:9,h:15}` | Character cell size; larger is coarser and cheaper |
| `ramp` | `RAMPS.dense` | Glyphs from sparse to dense |
| `glyph` | `{ edges:false, match:'ramp' }` | Edge glyphs and shape matching; `edgeStrength` sets edge sensitivity, `contrast` the shape-match contrast |
| `braille` | `{ threshold:0.35, dither:true }` | Dot threshold and Bayer dither |
| `dither` | `{ size:6, shape:'dot', levels:4 }` | Grid size, `'dot'` or `'square'`, brightness levels |
| `tile` | `{ size:12, gap:2, radius:2, color:'source' }` | Tile size, gap, corner radius, colour source |
| `pointerGlow` | `null` | `{ radius, strength }`; needs `interactive: true` |
| `crt` | `null` | `{ scanlines, glow, vignette, flicker }`; 0.15–0.35 reads well |
| `cutoff` / `highlight` | 0.06 / 0.9 | Below cutoff stays empty; above highlight prints a filled box |
| `texture` / `shimmer` | 0.3 / 0.12 | Brightness grain and glyph flicker; set 0 for a still poster |
| `grid` | `'lines'` | Background grid: `'lines'`, `'dots'` or `false` |
| `fps` | 30 | 30 is enough for a character backdrop |

## Out of scope

Character fluid simulation (needs per-frame state), morphing between two ASCII images, webcam input (needs device permission), and a WebGL shader build. Build those separately instead of growing this engine.

## Gotchas

- Cross-origin images taint the canvas and the engine cannot read pixels. Use same-origin, `data:` or `blob:` URLs, or a server that sends CORS headers. Pages opened from `file://` treat local images as cross-origin too.
- Keep CRT scanlines and flicker subtle; flicker is skipped under reduced motion. Do not put body text under the CRT finish.
- Handled by the engine: high-DPI sharpness, resize, pausing in hidden tabs, and a single still frame under `prefers-reduced-motion`.
- Keep the UI copy neutral; do not copy another product's name or interface text.
