---
name: ascii-backdrop
description: "Turn any subject into an animated ASCII-character backdrop behind a UI, like a dark AI prompt page with jellyfish drawn in drifting characters, or a swarm of colour-tile bodies that veer away from the cursor. The subject is open-ended: creatures, objects, particles, smoke, a word or logo, an image or video, or your own canvas draw function. Two print modes can be mixed: glyphs (brightness sets density) and tiles (coloured squares in the subject's own colours), with optional pointer and click interaction. Ships a dependency-free JS engine plus HTML and React wiring, with tunable glyph ramp, palette, density, depth layers and a clear zone that keeps text readable. Use when the user asks for an ASCII background, ASCII art animation, character-rain or glyph backdrop, or says 'make X into an animated ASCII background' / 'ASCII 背景' / '字符画动效'."
---

# ASCII Backdrop

A subject paints brightness; the engine prints that brightness as characters. Anything that can paint on a canvas can be the subject.

## How it works

Every frame, each layer's subject draws itself in white on a tiny offscreen canvas where one pixel is one character cell on screen. The engine reads each pixel's brightness, picks a glyph from a density ramp (default ` .':-=+ot%SX8@`), and colours it from a palette. Cells above `highlight` print as filled boxes, and a layer's `depth` dims it, which gives depth for free. A `clear` zone fades glyphs around the UI so headings and inputs stay readable.

Each layer also picks a print mode. The default `mode: 'glyph'` prints characters; `mode: 'tile'` prints rounded squares in the colours the subject actually paints (paint three colours and the tiles show three colours). Both can share a scene, for example glyph ripples under colour-tile bodies.

With `interactive: true`, a subject's `draw(ctx, t, s, env)` also receives `env.pointer` (the cursor in that layer's local units) and `env.clicks` (recent clicks with their age), enough for fleeing, following or click ripples.

Changing the subject means changing one draw function. The engine does not change.

## Files

- [`assets/ascii-backdrop.js`](assets/ascii-backdrop.js): engine and built-in subjects, no dependencies, exposed as `window.AsciiBackdrop`. Copy it into the project.
- [`assets/demo.html`](assets/demo.html): a dark prompt page with the backdrop behind it; switch subjects and palettes, or upload an image or video.
- [`scripts/check.mjs`](scripts/check.mjs): screenshots desktop, phone and reduced-motion views and reports errors and frame rate (needs Playwright).

## Steps

1. **Choose the subject.** Ask what it should say (a brand mascot, a product, a mood) instead of assuming a creature. Pick the source in this order:
   - Existing image, SVG, video or logo: `subjects.image(src, { invert, motion })`. Use `invert: true` for dark art on a light background.
   - A word, name or emoji: `subjects.text('…')`.
   - A preset fits: `jellyfish`, `school` (many small bodies), `cloud` (smoke, nebula), `strands` (kelp, hair; `flip: true` for flames), `rising` (fire, bubbles, sparks; `fall: true` for snow or rain), `solid` (spinning wireframe); for tile layers `wanderers` (tapered segmented bodies that wander and veer away from the cursor; colours are configurable), and for glyph layers `ripples` (ambient rings plus a ring per click).
   - Nothing fits: write `subjects.custom((ctx, t, s) => { … })` (see "Write a subject"). Presets are starting points, not the menu.
2. **Compose the layers.** `layers` is an array of `{ subject, x, y, scale, depth, drift, speed, timeOffset, rotate }`; `x` and `y` are 0–1 of the screen. A layout that works: one hero below the input, one above it, two faint ones at the sides (`depth` 0.4–0.6). Give repeats different `seed` or `timeOffset` values so they do not move in sync.
3. **Palette and clear zone.** `palette` lists 3–5 colours from dark to bright; `background` matches the page. Aim `clear: { x, y, rx, ry, strength }` at the heading and input.
4. **Wire it in.** Put a full-screen `<canvas>` behind the content (`position: fixed; inset: 0`), keep content above it, and give panels a translucent fill with `backdrop-filter`. React notes are below.
5. **Verify.** Run `node scripts/check.mjs page.html` and look at the three images: is the subject recognisable, are the heading and input clear, is the phone view too busy, does reduced motion show one still frame? Frame rate should be near 60; if not, raise `cell` or lower `fps`.

## Wiring

```html
<canvas id="bd" style="position:fixed;inset:0;width:100%;height:100%"></canvas>
<script src="ascii-backdrop.js"></script>
<script>
  const S = AsciiBackdrop.subjects;
  const bd = AsciiBackdrop.create(document.getElementById('bd'), {
    palette: ['#2b2552', '#4a5fbf', '#58c9c2', '#d8fff6'],
    clear: { x: 0.5, y: 0.46, rx: 0.3, ry: 0.2, strength: 0.85 },
    layers: [
      { subject: S.jellyfish({ seed: 1 }), x: 0.56, y: 0.76, scale: 0.72, depth: 1 },
      { subject: S.image('/logo.png', { invert: true }), x: 0.15, y: 0.3, scale: 0.4, depth: 0.5 },
    ],
  });
  bd.start();
</script>
```

React: call `create` inside `useEffect` and return `() => bd.destroy()`. When layers change, call `bd.setLayers(...)` instead of recreating the backdrop on every render.

## Tile mode and interaction

```js
const bd = AsciiBackdrop.create(canvas, {
  interactive: true,
  background: '#1b1a18', grid: 'dots',
  palette: ['#34322f', '#5f5c56', '#9a968e', '#e6e2da'],
  tile: { size: 12, gap: 2, radius: 2 },            // square size, gap, corner radius
  layers: [
    { subject: S.ripples(), x: 0.5, y: 0.5, scale: 1.9, depth: 0.7 },             // glyph ripples
    { subject: S.wanderers({ count: 7 }), mode: 'tile', x: 0.5, y: 0.5, scale: 1.7 },  // tile bodies
  ],
});
```

- Tile layers paint real colours, not white. Use dark grey instead of pure black for dark markings; pure black reads as empty. Pass your own colours with `wanderers({ colors: [{ base, mark, accent }] })`.
- `tile.color: 'palette'` maps tiles to the palette by brightness instead; `tile.glyphs` sets how often a small glyph (`·o•`) appears inside a tile.
- Read interaction from `env` instead of storing state in the subject. Write fleeing as "the closer the cursor, the further the push" so any moment can still be sampled directly.

## Write a subject

```js
const lighthouse = AsciiBackdrop.subjects.custom((ctx, t, s) => {
  // Draw around the origin, roughly inside [-s/2, s/2]. Brighter, more opaque white = denser glyphs.
  ctx.fillRect(-s * 0.05, -s * 0.3, s * 0.1, s * 0.6);                    // tower
  AsciiBackdrop.helpers.softDot(ctx, 0, -s * 0.32, s * 0.12, 0.9);        // lamp
  ctx.save(); ctx.rotate(t * 0.8);                                          // beam
  ctx.globalAlpha *= 0.35; ctx.fillRect(0, -s * 0.33, s * 0.6, s * 0.03); ctx.restore();
});
```

- Brightness is the whole language: use alpha, gradients and line width to decide where glyphs are dense. A flat white area becomes a wall of filled boxes; give it a gradient or lower alpha.
- Animate from `t` (seconds) and `env` only, never from the previous frame, so reduced motion, screenshots and recordings can sample any moment.
- Keep lines at least about one cell wide (`s * 0.015` or more), or they break into scattered dots.
- Helpers: `helpers.softDot(ctx, x, y, r, alpha)` for soft glows; `helpers.strand(ctx, points, w0, w1, a0, a1)` for lines that taper and fade from root to tip (tentacles, hair, kelp, smoke).

## Options

| Option | Default | Meaning |
|---|---|---|
| `cell` | `{w:9,h:15}` | Character cell size; larger is coarser and cheaper |
| `ramp` | `RAMPS.dense` | Glyphs from sparse to dense; also `soft`, `binary`, `blocks`, `dots` |
| `cutoff` / `highlight` | 0.06 / 0.9 | Below cutoff stays empty; above highlight prints a filled box |
| `texture` / `shimmer` | 0.3 / 0.12 | Brightness grain and glyph flicker; set 0 for a still poster |
| `grid` | `'lines'` | Background grid: `'lines'`, `'dots'` or `false` |
| `fps` | 30 | 30 is enough for a character backdrop |

## Gotchas

- Cross-origin images taint the canvas and the engine cannot read pixels. Use same-origin, `data:` or `blob:` URLs, or a server that sends CORS headers. Pages opened from `file://` treat local images as cross-origin too.
- Handled by the engine: high-DPI sharpness, resize, pausing in hidden tabs, and a single still frame under `prefers-reduced-motion`.
- Keep the UI copy neutral; do not copy another product's name or interface text.
