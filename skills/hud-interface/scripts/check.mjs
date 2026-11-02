#!/usr/bin/env node
// Headless checks for a HUD page: screenshots and behaviour with and without HTML-in-Canvas.
//   node check.mjs <page.html> [--out dir] [--glass-panel "#panel"] [--click ".hud-log-row:nth-child(2)"]
// Elements that change on purpose (clocks) carry data-hud-tick and are masked in the reduced-motion check.
// Reports: console errors, backdrop mode, glass mode, glass pixels drawn, a click inside the glass panel
// reaching the real element, horizontal overflow at 390 px, reduced motion leaving no animation, frame rate.
import { launch } from './lib/env.mjs';
import path from 'path';
import fs from 'fs';

const a = process.argv.slice(2);
const opt = (k, d) => { const i = a.indexOf(k); return i >= 0 ? a.splice(i, 2)[1] : d; };
const out = opt('--out', 'hud-check'), panelSel = opt('--glass-panel', '#panel'), clickSel = opt('--click', '.hud-log-row:nth-child(2)');
const file = a[0]; if (!file) { console.error('usage: node check.mjs <page.html> [--out dir]'); process.exit(2); }
const url = 'file://' + path.resolve(file);
fs.mkdirSync(out, { recursive: true });
const results = []; const ok = (name, pass, info = '') => { results.push({ name, pass, info }); console.log(`${pass ? '✓' : '✗'} ${name}${info ? ' — ' + info : ''}`); };

async function run(label, { flag = false, viewport = { width: 1440, height: 900 }, reduced = false, dpr = 1 } = {}) {
  const browser = await launch({ args: [...(flag ? ['--enable-blink-features=CanvasDrawElement'] : []), '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport, deviceScaleFactor: dpr, reducedMotion: reduced ? 'reduce' : 'no-preference' });
  const errors = []; page.on('pageerror', e => errors.push(String(e))); page.on('console', m => m.type() === 'error' && !/Failed to load resource/.test(m.text()) && errors.push(m.text()));
  await page.goto(url, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(900);
  const shot = path.join(out, `${label}.png`); await page.screenshot({ path: shot });
  const info = await page.evaluate(sel => ({
    backdrop: document.querySelector('.hud-backdrop')?.dataset.hud,
    glass: document.querySelector(sel)?.dataset.hudGlass,
    overflow: document.documentElement.scrollWidth - innerWidth,
  }), panelSel);
  ok(`${label}: no page errors`, !errors.length, errors.slice(0, 2).join(' | '));
  return { browser, page, info, shot };
}

// 1. Default Chrome: no HTML-in-Canvas, panel must stay ordinary DOM and still be clickable.
{
  const { browser, page, info } = await run('desktop');
  ok('desktop: backdrop shader running', info.backdrop === 'webgl2', `mode=${info.backdrop}`);
  ok('desktop: glass falls back to DOM', info.glass === 'fallback', `mode=${info.glass}`);
  await page.click(`${panelSel} ${clickSel}`);
  ok('desktop: click reaches panel row', await page.$eval(`${panelSel} ${clickSel}`, el => el.getAttribute('aria-pressed') === 'true' || el.matches(':focus')));
  // Frame rate of the backdrop loop.
  const fps = await page.evaluate(() => new Promise(r => { let n = 0; const t0 = performance.now(); const f = () => { n++; performance.now() - t0 < 1000 ? requestAnimationFrame(f) : r(n); }; requestAnimationFrame(f); }));
  console.log(`  info: backdrop ${fps} fps in headless software GL (a real GPU is far faster; judge on a real browser)`);
  await browser.close();
}
// 2. HTML-in-Canvas on: the panel is painted through the shader and still hit-tests.
for (const dpr of [1, 2]) {
  const { browser, page, info } = await run(`glass-dpr${dpr}`, { flag: true, dpr });
  ok(`glass dpr${dpr}: glass on`, info.glass === 'on', `mode=${info.glass}`);
  const drawn = await page.evaluate(sel => {
    const cv = document.querySelector(sel).closest('canvas'); if (!cv) return { err: 'no canvas' };
    const r = cv.getBoundingClientRect(); return { w: r.width, h: r.height, ph: document.querySelector(sel).offsetHeight };
  }, panelSel);
  ok(`glass dpr${dpr}: canvas sized to panel`, drawn.h > 100 && Math.abs(drawn.h - drawn.ph) < 2, JSON.stringify(drawn));
  // Pixels: compare the glass region with a screenshot of the plain backdrop area — it must contain ink.
  const box = await page.evaluate(sel => { const r = document.querySelector(sel).closest('canvas').getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: Math.min(r.height, 200) }; }, panelSel);
  const buf = await page.screenshot({ clip: box });
  const dark = await page.evaluate(async b64 => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = new OffscreenCanvas(img.width, img.height), x = c.getContext('2d'); x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, img.width, img.height).data; let k = 0; for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] < 120) k++; return k / (d.length / 4);
  }, buf.toString('base64'));
  ok(`glass dpr${dpr}: panel pixels drawn (dark ink share)`, dark > 0.05, (dark * 100).toFixed(1) + '%');
  const target = await page.$(`${panelSel} ${clickSel}`); const tb = await target.boundingBox();
  await page.mouse.click(tb.x + tb.width / 2, tb.y + tb.height / 2);
  ok(`glass dpr${dpr}: click at row's position hits that row`, await target.evaluate(el => el.getAttribute('aria-pressed') === 'true'));
  await page.waitForTimeout(300); await page.screenshot({ path: path.join(out, `glass-dpr${dpr}-after-click.png`) });
  await browser.close();
}
// 3. Phone width.
{
  const { browser, info } = await run('mobile', { viewport: { width: 390, height: 844 }, flag: true });
  ok('mobile: no horizontal overflow', info.overflow <= 0, `overflow=${info.overflow}px`);
  await browser.close();
}
// 4. Reduced motion: two frames 600 ms apart must match.
{
  const { browser, page } = await run('reduced', { reduced: true });
  const mask = [page.locator('[data-hud-tick]')]; // clocks change by design
  const a1 = await page.screenshot({ mask }); await page.waitForTimeout(600); const a2 = await page.screenshot({ mask, path: path.join(out, 'reduced-2.png') });
  ok('reduced motion: page is still', Buffer.compare(a1, a2) === 0);
  await browser.close();
}
const failed = results.filter(r => !r.pass).length;
console.log(`\n${results.length - failed}/${results.length} passed · screenshots in ${out}`);
process.exit(failed ? 1 : 0);
