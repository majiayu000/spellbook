#!/usr/bin/env node
// Real Chromium regressions. Requires Playwright; CHROME_PATH may select an installed browser.
// node regression.mjs [artifact-directory]
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const assets = fileURLToPath(new URL('../assets/', import.meta.url));
const out = path.resolve(process.argv[2] || 'ascii-regression');
await mkdir(out, { recursive: true });
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96"><rect width="96" height="96" fill="white"/></svg>';
const server = createServer(async (req, res) => {
  if (req.url.startsWith('/image')) {
    if (req.url.includes('slow')) await new Promise((r) => setTimeout(r, 1800));
    res.writeHead(200, { 'Content-Type': 'image/svg+xml' }); res.end(svg); return;
  }
  if (req.url === '/fixture') {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end('<style>canvas,img{width:192px;height:192px}body{margin:0;background:#222}.host{position:relative;width:192px;height:192px}</style><canvas id="bd"></canvas><div class="host"><img id="img"></div><script src="/ascii-backdrop.js"></script>'); return;
  }
  const name = req.url === '/demo' ? 'demo.html' : path.basename(req.url);
  try {
    res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript; charset=utf-8' : 'text/html; charset=utf-8');
    res.end(await readFile(path.join(assets, name)));
  }
  catch { res.writeHead(404); res.end(); }
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined });
const results = [];
async function test(name, run, options = {}) {
  const page = await browser.newPage(options);
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  try {
    await page.goto(origin + '/fixture');
    const evidence = await run(page);
    assert.deepEqual(errors, [], 'unexpected page errors');
    results.push({ name, pass: true, evidence });
  } catch (e) { results.push({ name, pass: false, error: e.message, errors }); }
  await page.close();
}
try {
  await test('reduced-motion asynchronous image redraw retains frozen time', async (page) => {
    await page.evaluate(() => {
      window.times = [];
      window.engine = AsciiBackdrop.create(document.querySelector('#bd'), {
        grid: false, texture: 0, shimmer: 0,
        layers: [{ subject: AsciiBackdrop.subjects.image('/image-slow', { motion: 'none' }), scale: 1 },
          { subject: { draw(c, t) { times.push(t); } } }],
      });
      engine.start();
      engine.snapshot(0);
      window.before = document.querySelector('#bd').toDataURL();
      window.drawsBefore = times.length;
    });
    await page.waitForTimeout(2200);
    const evidence = await page.evaluate(() => ({ changed: before !== document.querySelector('#bd').toDataURL(),
      redraws: times.length - drawsBefore, times: times.slice(drawsBefore) }));
    await page.screenshot({ path: path.join(out, 'reduced-image.png') });
    assert.equal(evidence.changed, true, JSON.stringify(evidence));
    assert.ok(evidence.redraws >= 1 && evidence.times.every((t) => t === 2.2), JSON.stringify(evidence));
    return evidence;
  }, { reducedMotion: 'reduce' });

  await test('reduced-motion stop before image load prevents redraw', async (page) => {
    await page.evaluate(() => {
      window.ResizeObserver = undefined;
      const canvas = document.querySelector('#bd');
      window.draws = 0; window.signals = 0;
      canvas.addEventListener('ascii-backdrop:frame', () => signals++);
      window.source = new Image(); source.src = '/image-slow-stopped';
      const engine = AsciiBackdrop.create(canvas, {
        grid: false, texture: 0, shimmer: 0,
        layers: [{ subject: AsciiBackdrop.subjects.image(source, { motion: 'none' }), scale: 1 },
          { subject: { draw() { draws++; } } }],
      });
      engine.start(); engine.stop();
      window.beforeStop = { draws, signals, pixels: canvas.toDataURL() };
    });
    await page.waitForFunction(() => source.complete && source.naturalWidth > 0);
    await page.waitForTimeout(100);
    const evidence = await page.evaluate(() => ({ loaded: source.naturalWidth > 0,
      before: { draws: beforeStop.draws, signals: beforeStop.signals }, after: { draws, signals },
      unchanged: beforeStop.pixels === document.querySelector('#bd').toDataURL() }));
    assert.deepEqual(evidence.after, evidence.before, JSON.stringify(evidence));
    assert.ok(evidence.loaded && evidence.unchanged, JSON.stringify(evidence));
    return evidence;
  }, { reducedMotion: 'reduce' });

  await test('inverted mutable canvas refreshes pixels', async (page) => {
    const evidence = await page.evaluate(() => {
      const source = document.createElement('canvas'); source.width = source.height = 32;
      const sx = source.getContext('2d');
      const target = document.querySelector('#bd'); target.width = target.height = 32;
      const ctx = target.getContext('2d');
      const subject = AsciiBackdrop.subjects.image(source, { invert: true, motion: 'none' });
      const sample = (color) => {
        sx.fillStyle = color; sx.fillRect(0, 0, 32, 32);
        ctx.clearRect(0, 0, 32, 32); ctx.save(); ctx.translate(16, 16); subject.draw(ctx, 0, 32); ctx.restore();
        return [...ctx.getImageData(16, 16, 1, 1).data];
      };
      return { first: sample('black'), second: sample('white') };
    });
    assert.equal(evidence.first[0], 255); assert.equal(evidence.second[0], 0, JSON.stringify(evidence));
    return evidence;
  });

  await test('inverted playing video refreshes pixels', async (page) => {
    const evidence = await page.evaluate(async () => {
      const source = document.createElement('canvas'); source.width = source.height = 32;
      const sx = source.getContext('2d'); sx.fillStyle = 'black'; sx.fillRect(0, 0, 32, 32);
      const stream = source.captureStream(30);
      const video = document.createElement('video'); video.muted = true; video.srcObject = stream;
      try {
        await video.play();
        const target = document.querySelector('#bd'); target.width = target.height = 32;
        const ctx = target.getContext('2d');
        const subject = AsciiBackdrop.subjects.image(video, { invert: true, motion: 'none' });
        const sample = () => {
          ctx.clearRect(0, 0, 32, 32); ctx.save(); ctx.translate(16, 16); subject.draw(ctx, 0, 32); ctx.restore();
          return [...ctx.getImageData(16, 16, 1, 1).data];
        };
        await new Promise((r) => setTimeout(r, 150)); const first = sample();
        sx.fillStyle = 'white'; sx.fillRect(0, 0, 32, 32);
        await new Promise((r) => setTimeout(r, 150));
        return { first, second: sample(), playing: !video.paused };
      } finally { video.pause(); stream.getTracks().forEach((track) => track.stop()); }
    });
    assert.ok(evidence.playing && evidence.first[0] > 240 && evidence.second[0] < 15, JSON.stringify(evidence));
    return evidence;
  });

  await test('destroy removes fallback resize work', async (page) => {
    const evidence = await page.evaluate(() => {
      window.ResizeObserver = undefined;
      let draws = 0;
      const engine = AsciiBackdrop.create(document.querySelector('#bd'), { layers: [{ subject: { draw() { draws++; } } }] });
      engine.destroy();
      const before = draws;
      dispatchEvent(new Event('resize')); dispatchEvent(new Event('resize'));
      return { before, after: draws };
    });
    assert.equal(evidence.after, evidence.before, JSON.stringify(evidence)); return evidence;
  });

  for (const slow of [true, false]) await test(`load reveal ${slow ? 'delayed >1.4s' : 'already loaded'}`, async (page) => {
    await page.evaluate(async (slow) => {
      const img = document.querySelector('#img'); img.src = '/image-' + (slow ? 'slow' : 'fast');
      if (!slow) await img.decode();
      window.revealer = AsciiBackdrop.reveal(img, { trigger: 'load', duration: 1000 });
    }, slow);
    if (slow) await page.waitForFunction(() => document.querySelector('#img').complete);
    const alpha = () => page.evaluate(() => {
      const cv = document.querySelector('.host canvas');
      const data = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
      let n = 0; for (let i = 3; i < data.length; i += 4) if (data[i]) n++;
      return n;
    });
    const initial = await alpha();
    await page.screenshot({ path: path.join(out, `reveal-${slow ? 'slow' : 'loaded'}-start.png`) });
    await page.waitForTimeout(550); const middle = await alpha();
    await page.waitForTimeout(1000); const end = await alpha();
    assert.ok(initial > 10000 && middle > end && end === 0, JSON.stringify({ initial, middle, end }));
    return { initial, middle, end };
  });

  await test('destroy cancels reveal load callback and scheduled work', async (page) => {
    const evidence = await page.evaluate(async () => {
      const img = document.querySelector('#img'); img.src = '/image-slow-destroy';
      const reveal = AsciiBackdrop.reveal(img, { trigger: 'load' });
      const cv = img.nextElementSibling;
      let lateDraws = 0, lateRafs = 0;
      const originalDraw = CanvasRenderingContext2D.prototype.drawImage;
      CanvasRenderingContext2D.prototype.drawImage = function (...args) { lateDraws++; return originalDraw.apply(this, args); };
      const originalRaf = window.requestAnimationFrame;
      window.requestAnimationFrame = (...args) => { lateRafs++; return originalRaf(...args); };
      reveal.destroy();
      await new Promise((r) => setTimeout(r, 2200));
      return { lateDraws, lateRafs, detached: !cv.isConnected };
    });
    assert.deepEqual(evidence, { lateDraws: 0, lateRafs: 0, detached: true }); return evidence;
  });

  await test('completed-frame signal tracks low fps and stop', async (page) => {
    const evidence = await page.evaluate(async () => {
      let draws = 0, signals = 0;
      const cv = document.querySelector('#bd');
      cv.addEventListener('ascii-backdrop:frame', () => signals++);
      const engine = AsciiBackdrop.create(cv, { fps: 8, layers: [{ subject: { draw() { draws++; } } }] });
      engine.start();
      const start = { draws, signals };
      await new Promise((r) => setTimeout(r, 2000));
      const active = { draws: draws - start.draws, signals: signals - start.signals };
      engine.stop(); const before = signals;
      await new Promise((r) => setTimeout(r, 500));
      return { active, afterStop: signals - before };
    });
    assert.ok(evidence.active.draws >= 10 && evidence.active.draws <= 17, JSON.stringify(evidence));
    assert.equal(evidence.active.signals, evidence.active.draws, JSON.stringify(evidence));
    assert.equal(evidence.afterStop, 0); return evidence;
  });

  await test('failed initialization emits no completed frames', async (page) => {
    const evidence = await page.evaluate(() => {
      let signals = 0, failed = false;
      document.querySelector('#bd').addEventListener('ascii-backdrop:frame', () => signals++);
      try { AsciiBackdrop.create(document.querySelector('#bd'), { palette: null }); }
      catch { failed = true; }
      return { failed, signals };
    });
    assert.deepEqual(evidence, { failed: true, signals: 0 }); return evidence;
  });

  await test('phone uses device viewport and responsive rail', async (page) => {
    await page.goto(origin + '/demo');
    await page.waitForTimeout(500);
    const evidence = await page.evaluate(() => ({ width: document.documentElement.clientWidth,
      phoneLayout: matchMedia('(max-width: 640px)').matches, rail: getComputedStyle(document.querySelector('.rail')).display }));
    await page.screenshot({ path: path.join(out, 'phone.png') });
    assert.deepEqual(evidence, { width: 390, phoneLayout: true, rail: 'none' }); return evidence;
  }, { viewport: { width: 390, height: 844 }, isMobile: true });
} finally {
  await browser.close(); server.close();
}
await writeFile(path.join(out, 'results.json'), JSON.stringify(results, null, 2) + '\n');
for (const result of results) console.log(JSON.stringify(result));
if (results.some((r) => !r.pass)) process.exitCode = 1;
