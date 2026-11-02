#!/usr/bin/env node
// Acceptance checks for a code-built 3D scene. Serves the folder, opens the page headless, drives it through
// window.__scene (state, floor(n), screenOf(n), advance(sec), go(shot, arg), setExplode(on), setTour(on)).
//   node check.mjs <folder> [--page demo.html] [--out dir]
// Checks: no errors; no images and no requests leaving the folder; the picture is a line drawing (ink share);
// the tour moves the camera; clicking a floor goes into it, cuts it open and lifts the floors above; explode
// separates parts and lists them; 120 s of travel keeps the chunk and object counts bounded; phone width;
// reduced motion is still. Frame rate is reported, not judged (headless GL is software).
import { launch } from './lib/env.mjs';
import { serve } from './serve.mjs';
import path from 'path';
import fs from 'fs';

const a = process.argv.slice(2);
const opt = (k, d) => { const i = a.indexOf(k); return i >= 0 ? a.splice(i, 2)[1] : d; };
const pageName = opt('--page', 'demo.html'), out = opt('--out', 'scene-check');
const dir = a[0]; if (!dir) { console.error('usage: node check.mjs <folder> [--page demo.html] [--out dir]'); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
const srv = await serve(dir);
const results = []; const ok = (name, pass, info = '') => { results.push({ name, pass, info }); console.log(`${pass ? '✓' : '✗'} ${name}${info ? ' — ' + info : ''}`); };
const GL = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];

async function open({ viewport = { width: 1280, height: 860 }, reduced = false } = {}) {
  const browser = await launch({ args: GL });
  const page = await browser.newPage({ viewport, reducedMotion: reduced ? 'reduce' : 'no-preference' });
  const errors = [], foreign = [], images = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => m.type() === 'error' && errors.push(m.text()));
  page.on('request', r => {
    const u = r.url();
    if (!u.startsWith(srv.url) && !u.startsWith('data:')) foreign.push(u);
    if (r.resourceType() === 'image' || /\.(png|jpe?g|webp|gif|avif|ktx2?|hdr|exr)(\?|$)/i.test(u)) images.push(u);
  });
  await page.goto(srv.url + pageName);
  await page.waitForFunction(() => window.__scene, null, { timeout: 30000 });
  await page.evaluate(() => window.__scene.advance(0.5));
  return { browser, page, errors, foreign, images };
}
const S = (page, fn, arg) => page.evaluate(fn, arg);
// Share of pixels that are ink (dark) in a screenshot, measured in the page.
const inkShare = (page, buf) => page.evaluate(async b64 => {
  const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
  const c = new OffscreenCanvas(img.width, img.height), x = c.getContext('2d'); x.drawImage(img, 0, 0);
  const d = x.getImageData(0, 0, img.width, img.height).data; let k = 0; for (let i = 0; i < d.length; i += 16) if (d[i] + d[i + 1] + d[i + 2] < 200) k++;
  return k / (d.length / 16);
}, buf.toString('base64'));

{
  const { browser, page, errors, foreign, images } = await open();
  // 1. Picture: a line drawing, not blank and not a grey wall.
  await S(page, () => { __scene.setTour(false); __scene.go('wide', null, 0); __scene.advance(1); });
  const wide = await page.screenshot({ path: path.join(out, 'wide.png') });
  const ink = await inkShare(page, wide);
  ok('wide shot reads as a line drawing (ink share 2–35 %)', ink > 0.02 && ink < 0.35, (ink * 100).toFixed(1) + '%');
  // 2. Tour moves the camera.
  await S(page, () => __scene.setTour(true));
  const c0 = (await S(page, () => __scene.state())).camera;
  await S(page, () => __scene.advance(10));
  const c1 = (await S(page, () => __scene.state())).camera;
  ok('tour moves the camera between shots', Math.hypot(c1[0] - c0[0], c1[1] - c0[1], c1[2] - c0[2]) > 1, `${c0} → ${c1}`);
  // 3. Click a floor in the wide shot.
  await S(page, () => { __scene.setTour(false); __scene.go('wide', null, 0); __scene.advance(0.5); });
  const st = await S(page, () => __scene.state()); const n = Math.round(st.cab) + 1;
  const [x, y] = await S(page, n => __scene.screenOf(n), n);
  await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.up();
  await S(page, () => __scene.advance(3));
  const s2 = await S(page, () => __scene.state()), f = await S(page, n => __scene.floor(n), s2.focus), up = await S(page, n => __scene.floor(n + 1), s2.focus);
  ok('click on a floor goes into that room', s2.shot === 'room' && s2.focus === n, `clicked ${n}, shot=${s2.shot} focus=${s2.focus}`);
  ok('focused room is cut open', f && f.cut < 0.05, `cut=${f?.cut?.toFixed(3)}`);
  ok('floors above lift away', up && up.lift > 2, `lift=${up?.lift?.toFixed(2)}`);
  await page.screenshot({ path: path.join(out, 'room.png') });
  // 4. Explode via the real button.
  await page.click('#explodeBtn'); await S(page, () => __scene.advance(2.5));
  const s3 = await S(page, () => __scene.state());
  const items = await page.$$eval('#partsList li', li => li.length);
  ok('explode separates the parts', s3.exploded > 0.95, `exploded=${s3.exploded.toFixed(3)}`);
  ok('part list shown', items >= 5 && await page.isVisible('#parts'), `${items} rows`);
  await page.screenshot({ path: path.join(out, 'explode.png') });
  await page.click('#explodeBtn'); await S(page, () => __scene.advance(3));
  ok('reassembles', (await S(page, () => __scene.state())).exploded < 0.01);
  // 5. Endless: 120 s of travel.
  await S(page, () => { __scene.go('ride', null, 0); __scene.advance(1); });
  const b0 = await S(page, () => __scene.state());
  await S(page, () => __scene.advance(120, 1 / 15));
  const b1 = await S(page, () => __scene.state());
  ok('travels on (≥ 25 floors in 120 s)', b1.cab - b0.cab >= 25, `${b0.cab.toFixed(1)} → ${b1.cab.toFixed(1)}`);
  ok('chunk and object counts stay bounded', Math.abs(b1.chunks - b0.chunks) <= 2 && b1.objects < b0.objects * 1.25, `chunks ${b0.chunks}→${b1.chunks}, objects ${b0.objects}→${b1.objects}`);
  await page.screenshot({ path: path.join(out, 'ride-after-120s.png') });
  // 6. Frame rate (info).
  const fps = await page.evaluate(() => new Promise(r => { let k = 0; const t0 = performance.now(); const f = () => { k++; performance.now() - t0 < 2000 ? requestAnimationFrame(f) : r(k / 2); }; requestAnimationFrame(f); }));
  console.log(`  info: ${fps} fps in headless software GL (judge frame rate on a real browser)`);
  ok('no page errors', !errors.length, errors.slice(0, 2).join(' | '));
  ok('no images loaded', !images.length, images.slice(0, 2).join(' '));
  ok('no requests outside the folder', !foreign.length, foreign.slice(0, 2).join(' '));
  await browser.close();
}
{
  const { browser, page } = await open({ viewport: { width: 390, height: 844 } });
  const o = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth - innerWidth, bar: document.querySelector('nav')?.getBoundingClientRect().toJSON() }));
  ok('phone: no horizontal overflow', o.overflow <= 0, `overflow=${o.overflow}`);
  ok('phone: controls inside the screen', o.bar && o.bar.left >= 0 && o.bar.right <= 390 && o.bar.bottom <= 844, JSON.stringify(o.bar && { l: o.bar.left | 0, r: o.bar.right | 0, b: o.bar.bottom | 0 }));
  await page.screenshot({ path: path.join(out, 'phone.png') });
  await browser.close();
}
{
  const { browser, page } = await open({ reduced: true });
  await page.waitForTimeout(400);
  const r1 = await page.screenshot(); await page.waitForTimeout(800); const r2 = await page.screenshot();
  ok('reduced motion: nothing moves on its own', Buffer.compare(r1, r2) === 0);
  await browser.close();
}
srv.close();
const failed = results.filter(r => !r.pass).length;
console.log(`\n${results.length - failed}/${results.length} passed · screenshots in ${out}`);
process.exit(failed ? 1 : 0);
