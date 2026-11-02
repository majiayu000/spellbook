#!/usr/bin/env node
// Screenshot the real project map and record where its main blocks sit.
// usage: MOTION_KIT=<motion-stack kit> node capture.mjs <map index.html> <out dir>
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { launch } = await import(process.env.MOTION_KIT + '/env.mjs');
const [src, out] = process.argv.slice(2);
const browser = await launch();
const page = await browser.newPage({ viewport: { width: +(process.env.VW || 1600), height: 900 }, deviceScaleFactor: 2 });
await page.goto(pathToFileURL(src).href);
// lay the map out in one column so the whole blocker chain is visible, not scrolled
await page.addStyleTag({ content: '.workspace.grid{grid-template-columns:1fr !important} .chain{overflow:visible !important}' });
await page.waitForTimeout(800);
const rects = await page.evaluate(() => {
  const r = (el, key) => { const b = el.getBoundingClientRect(); return { key, cls: el.className || '', x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height }; };
  const pick = (sel, key) => [...document.querySelectorAll(sel)].filter(e => e.offsetParent || e.getClientRects().length).map((e, i) => r(e, key + (i ? i : '')));
  return {
    page: { w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight },
    blocks: [
      ...pick('header.header', 'header'),
      ...pick('section.panel.brief', 'brief'),
      ...pick('section.route.track', 'track'),
      ...pick('.milestone.current', 'current'),
      ...pick('.milestone', 'ms'),
      ...pick('section.chain-card', 'chain'),
      ...pick('.chain-node', 'node'),
      ...pick('section.panel.parts-panel', 'parts'),
      ...pick('section.panel.remaining', 'remaining'),
      ...pick('section.panel.changes-panel', 'changes'),
      ...pick('section.panel.uncertain-panel', 'uncertain'),
      ...pick('aside.aside', 'aside'),
      ...pick('.brief-row', 'row'),
    ],
    paths: [...document.querySelectorAll('.chain svg path')].filter(p => p.getTotalLength() > 20).map(p => {
      const m = p.getScreenCTM(), L = p.getTotalLength(), pts = [];
      for (let i = 0; i <= 40; i++) { const q = p.getPointAtLength(L * i / 40); pts.push([+(m.a * q.x + m.c * q.y + m.e + scrollX).toFixed(1), +(m.b * q.x + m.d * q.y + m.f + scrollY).toFixed(1)]); }
      const cs = getComputedStyle(p);
      return { pts, dashed: cs.strokeDasharray !== 'none', marker: !!p.getAttribute('marker-end'), stroke: cs.stroke };
    }),
  };
});
fs.mkdirSync(out, { recursive: true });
await page.screenshot({ path: out + '/map.png', fullPage: true });
fs.writeFileSync(out + '/rects.json', JSON.stringify(rects, null, 1));
console.log(JSON.stringify(rects.page), rects.blocks.length, 'blocks');
await browser.close();
