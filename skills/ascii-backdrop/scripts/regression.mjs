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
  if (req.url.startsWith('/responsive-')) {
    const wide = req.url.includes('white');
    res.writeHead(200, { 'Content-Type': 'image/svg+xml' });
    res.end(`<svg xmlns="http://www.w3.org/2000/svg" width="${wide ? 192 : 96}" height="96"><rect width="100%" height="100%" fill="${wide ? 'white' : 'black'}"/></svg>`); return;
  }
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

  await test('inverted responsive image follows picture candidate and dimensions', async (page) => {
    await page.evaluate(async () => {
      const picture = document.createElement('picture'), source = document.createElement('source');
      source.media = '(min-width: 800px)'; source.srcset = '/responsive-white.svg';
      window.responsiveImage = new Image(); responsiveImage.src = '/responsive-black.svg';
      picture.append(source, responsiveImage); document.body.append(picture);
      await responsiveImage.decode();
      window.responsiveSubject = AsciiBackdrop.subjects.image(responsiveImage, { invert: true, motion: 'none' });
      const target = document.querySelector('#bd'); target.width = target.height = 192;
      window.sampleResponsive = () => {
        const ctx = target.getContext('2d'); ctx.clearRect(0, 0, 192, 192);
        ctx.save(); ctx.translate(96, 96); responsiveSubject.draw(ctx, 0, 192); ctx.restore();
        return { pixel: [...ctx.getImageData(96, 96, 1, 1).data], src: responsiveImage.src,
          currentSrc: responsiveImage.currentSrc, width: responsiveImage.naturalWidth, height: responsiveImage.naturalHeight };
      };
      window.firstResponsive = sampleResponsive();
    });
    await page.setViewportSize({ width: 1000, height: 700 });
    await page.waitForFunction(() => responsiveImage.currentSrc.endsWith('/responsive-white.svg') &&
      responsiveImage.complete && responsiveImage.naturalWidth === 192);
    const evidence = await page.evaluate(() => ({ first: firstResponsive, second: sampleResponsive() }));
    assert.equal(evidence.first.pixel[0], 255, JSON.stringify(evidence));
    assert.equal(evidence.second.pixel[0], 0, JSON.stringify(evidence));
    assert.equal(evidence.first.src, evidence.second.src, 'fallback src must remain unchanged');
    assert.notEqual(evidence.first.currentSrc, evidence.second.currentSrc);
    assert.deepEqual([evidence.second.width, evidence.second.height], [192, 96]);
    return evidence;
  }, { viewport: { width: 600, height: 700 } });

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

  for (const slow of [false, true]) await test(`reduced reveal stays visible through hover and scroll (${slow ? 'delayed' : 'cached'})`, async (page) => {
    const evidence = await page.evaluate(async (slow) => {
      const img = document.querySelector('#img'); img.src = '/image-' + (slow ? 'slow-reduced' : 'fast-reduced');
      if (!slow) await img.decode();
      const hover = AsciiBackdrop.reveal(img);
      if (slow) await img.decode();
      // Allow the actual image load and ResizeObserver callbacks to prepare both paths.
      await new Promise((resolve) => requestAnimationFrame(resolve));
      const opaquePixels = () => {
        const cv = img.nextElementSibling;
        const data = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
        let n = 0; for (let i = 3; i < data.length; i += 4) if (data[i]) n++;
        return n;
      };
      const initial = opaquePixels();
      img.parentElement.dispatchEvent(new PointerEvent('pointerenter'));
      const entered = opaquePixels();
      img.parentElement.dispatchEvent(new PointerEvent('pointerleave'));
      const left = opaquePixels();
      hover.rewind(); hover.progress(0);
      const manual = opaquePixels();
      hover.destroy();
      img.parentElement.style.marginTop = '2000px';
      const scroll = AsciiBackdrop.reveal(img, { trigger: 'scroll' });
      dispatchEvent(new Event('scroll'));
      const belowViewport = opaquePixels();
      img.parentElement.style.marginTop = '0px';
      dispatchEvent(new Event('scroll'));
      const inViewport = opaquePixels();
      scroll.destroy();
      return { initial, entered, left, manual, belowViewport, inViewport };
    }, slow);
    assert.ok(Object.values(evidence).every((count) => count === 0), JSON.stringify(evidence));
    return evidence;
  }, { reducedMotion: 'reduce' });

  await test('reveal overlay follows image bounds inside padded bordered captioned parent', async (page) => {
    await page.evaluate(async () => {
      const img = document.querySelector('#img'), host = img.parentElement;
      Object.assign(host.style, { width: '280px', height: 'auto', padding: '24px 30px 18px 22px', border: '6px solid #a565fc' });
      Object.assign(img.style, { display: 'block', width: '180px', height: '120px', marginLeft: '11px' });
      const caption = document.createElement('p'); caption.id = 'caption'; caption.textContent = 'Caption stays outside the reveal mask';
      Object.assign(caption.style, { margin: '12px 0 0', height: '32px', background: '#154c32', color: 'white' });
      host.append(caption);
      img.src = '/image-layout'; await img.decode();
      window.revealer = AsciiBackdrop.reveal(img, { trigger: 'manual' });
    });
    const bounds = () => page.evaluate(() => {
      const img = document.querySelector('#img'), cv = img.nextElementSibling;
      const image = img.getBoundingClientRect(), mask = cv.getBoundingClientRect(), caption = document.querySelector('#caption').getBoundingClientRect();
      const rect = (r) => ({ x: r.x, y: r.y, width: r.width, height: r.height });
      const overlap = Math.max(0, Math.min(mask.right, caption.right) - Math.max(mask.left, caption.left)) *
        Math.max(0, Math.min(mask.bottom, caption.bottom) - Math.max(mask.top, caption.top));
      return { image: rect(image), mask: rect(mask), captionOverlap: overlap };
    });
    const initial = await bounds();
    await page.screenshot({ path: path.join(out, 'reveal-layout-initial.png') });
    await page.evaluate(() => Object.assign(document.querySelector('#img').style, { width: '220px', height: '140px' }));
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const resized = await bounds();
    await page.screenshot({ path: path.join(out, 'reveal-layout-resized.png') });
    for (const stage of [initial, resized]) {
      assert.ok(Object.keys(stage.image).every((key) => Math.abs(stage.image[key] - stage.mask[key]) < 0.5), JSON.stringify({ initial, resized }));
      assert.equal(stage.captionOverlap, 0, JSON.stringify({ initial, resized }));
    }
    return { initial, resized };
  });

  await test('viewport-only image movement repositions reveal and destroy removes listener', async (page) => {
    await page.evaluate(async () => {
      const css = document.createElement('style');
      css.textContent = '.host{width:240px;height:auto;padding:24px 30px}#img{display:block;width:180px;height:120px}@media(max-width:640px){.host{padding:12px 10px}}';
      document.head.append(css);
      const img = document.querySelector('#img'); img.src = '/image-responsive'; await img.decode();
      const caption = document.createElement('p'); caption.textContent = 'Caption below the image'; img.parentElement.append(caption);
      window.resizeListeners = new Set();
      const add = window.addEventListener.bind(window), remove = window.removeEventListener.bind(window);
      window.addEventListener = (type, listener, ...args) => { if (type === 'resize') resizeListeners.add(listener); return add(type, listener, ...args); };
      window.removeEventListener = (type, listener, ...args) => { if (type === 'resize') resizeListeners.delete(listener); return remove(type, listener, ...args); };
      window.revealer = AsciiBackdrop.reveal(img, { trigger: 'manual' });
      window.mask = img.nextElementSibling;
    });
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const bounds = () => page.evaluate(() => {
      const rect = (el) => { const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; };
      return { image: rect(document.querySelector('#img')), mask: rect(mask), listeners: resizeListeners.size };
    });
    const wide = await bounds();
    await page.setViewportSize({ width: 390, height: 720 });
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const narrow = await bounds();
    await page.screenshot({ path: path.join(out, 'reveal-viewport-narrow.png') });
    await page.evaluate(() => revealer.destroy());
    await page.setViewportSize({ width: 900, height: 720 });
    const destroyed = await page.evaluate(() => ({ listeners: resizeListeners.size, detached: !mask.isConnected }));
    const detail = JSON.stringify({ wide, narrow, destroyed });
    assert.notEqual(wide.image.x, narrow.image.x, detail);
    assert.equal(wide.image.width, narrow.image.width, detail);
    assert.equal(wide.image.height, narrow.image.height, detail);
    assert.deepEqual(wide.mask, wide.image, detail); assert.deepEqual(narrow.mask, narrow.image, detail);
    assert.equal(wide.listeners, 1, detail); assert.equal(narrow.listeners, 1, detail);
    assert.deepEqual(destroyed, { listeners: 0, detached: true }, detail);
    return { wide, narrow, destroyed };
  }, { viewport: { width: 900, height: 720 } });

  await test('interactive option reconciles pointer listeners across toggles and destroy', async (page) => {
    await page.evaluate(() => {
      window.ResizeObserver = undefined;
      window.layoutReads = 0; window.lastEnv = null;
      const canvas = document.querySelector('#bd');
      const originalRect = canvas.getBoundingClientRect.bind(canvas);
      canvas.getBoundingClientRect = () => { layoutReads++; return originalRect(); };
      window.engine = AsciiBackdrop.create(canvas, {
        layers: [{ subject: { draw(c, t, s, env) { lastEnv = { pointer: env.pointer, clicks: env.clicks.length }; } } }],
      });
    });
    const evidence = [];
    for (const [index, interactive] of [false, true, false, true].entries()) {
      await page.evaluate((enabled) => {
        engine.set({ interactive: enabled });
        if (enabled) engine.set({ interactive: enabled }); // repeated set must not duplicate listeners
        layoutReads = 0;
      }, interactive);
      await page.mouse.move(48 + index, 50);
      await page.mouse.down(); await page.mouse.up();
      evidence.push(await page.evaluate(() => {
        engine.snapshot(0);
        return { interactive: engine.options.interactive, reads: layoutReads, ...lastEnv };
      }));
    }
    await page.evaluate(() => { engine.destroy(); layoutReads = 0; });
    await page.mouse.move(70, 70); await page.mouse.down(); await page.mouse.up();
    const afterDestroy = await page.evaluate(() => layoutReads);
    const detail = JSON.stringify({ phases: evidence, afterDestroy });
    for (const phase of evidence) {
      if (phase.interactive) assert.ok(phase.reads === 2 && phase.pointer && phase.clicks === 1, detail);
      else assert.ok(phase.reads === 0 && phase.pointer === null && phase.clicks === 0, detail);
    }
    assert.equal(afterDestroy, 0, detail);
    return { phases: evidence, afterDestroy };
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

  await test('60Hz rounded timestamps preserve 24 and 30fps pacing and forced snapshots', async (page) => {
    const evidence = await page.evaluate(() => {
      window.ResizeObserver = undefined;
      let now = 0, pending = null;
      const nativeRaf = requestAnimationFrame, nativeCancel = cancelAnimationFrame;
      const nowDescriptor = Object.getOwnPropertyDescriptor(performance, 'now');
      Object.defineProperty(performance, 'now', { configurable: true, value: () => now });
      window.requestAnimationFrame = (callback) => { pending = callback; return 1; };
      window.cancelAnimationFrame = () => { pending = null; };
      const results = [];
      try {
        for (const fps of [24, 30]) {
          now = 0;
          let draws = 0, signals = 0;
          const times = [], canvas = document.querySelector('#bd');
          const onFrame = () => signals++;
          canvas.addEventListener('ascii-backdrop:frame', onFrame);
          const engine = AsciiBackdrop.create(canvas, { fps, grid: false,
            layers: [{ subject: { draw(c, t) { draws++; times.push(t); } } }] });
          try {
            engine.start();
            const initial = { draws, signals };
            for (let frame = 1; frame <= 600; frame++) {
              now = Math.round(frame * (1000 / 60) * 10) / 10;
              const callback = pending; pending = null; callback(now);
            }
            const active = { draws: draws - initial.draws, signals: signals - initial.signals };
            engine.stop();
            const beforeSnapshots = signals;
            engine.snapshot(7); engine.snapshot(8);
            results.push({ fps, simulatedMs: now, active,
              forcedFrames: signals - beforeSnapshots, snapshotTimes: times.slice(-2) });
          } finally { engine.destroy(); canvas.removeEventListener('ascii-backdrop:frame', onFrame); }
        }
      } finally {
        window.requestAnimationFrame = nativeRaf; window.cancelAnimationFrame = nativeCancel;
        if (nowDescriptor) Object.defineProperty(performance, 'now', nowDescriptor); else delete performance.now;
      }
      return results;
    });
    for (const result of evidence) {
      assert.ok(Math.abs(result.active.draws - result.fps * 10) <= 1, JSON.stringify(evidence));
      assert.equal(result.active.signals, result.active.draws, JSON.stringify(evidence));
      assert.equal(result.forcedFrames, 2, JSON.stringify(evidence));
      assert.deepEqual(result.snapshotTimes, [7, 8], JSON.stringify(evidence));
    }
    return evidence;
  });

  await test('real Chrome completed frames track 24 and 30fps', async (page) => {
    const evidence = await page.evaluate(async () => {
      const results = [], canvas = document.querySelector('#bd');
      for (const fps of [24, 30]) {
        let draws = 0, signals = 0;
        const onFrame = () => signals++;
        canvas.addEventListener('ascii-backdrop:frame', onFrame);
        const engine = AsciiBackdrop.create(canvas, { fps, grid: false,
          layers: [{ subject: { draw() { draws++; } } }] });
        try {
          engine.start();
          const initial = { draws, signals }, start = performance.now();
          await new Promise((resolve) => setTimeout(resolve, 2000));
          const elapsedMs = performance.now() - start;
          engine.stop();
          results.push({ target: fps, draws: draws - initial.draws, signals: signals - initial.signals,
            elapsedMs, actualFps: (signals - initial.signals) * 1000 / elapsedMs });
        } finally { engine.destroy(); canvas.removeEventListener('ascii-backdrop:frame', onFrame); }
      }
      return results;
    });
    for (const result of evidence) {
      assert.equal(result.signals, result.draws, JSON.stringify(evidence));
      assert.ok(Math.abs(result.actualFps - result.target) < 2, JSON.stringify(evidence));
    }
    return evidence;
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

  await test('demo releases replaced uploads and cancels pending playback', async (page) => {
    await page.addInitScript(() => {
      window.uploadUrls = []; window.revokedUrls = []; window.uploadVideos = []; window.uploadRejections = [];
      const create = URL.createObjectURL.bind(URL), revoke = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = (blob) => { const url = create(blob); uploadUrls.push(url); return url; };
      URL.revokeObjectURL = (url) => { revokedUrls.push(url); return revoke(url); };
      const play = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function (...args) { uploadVideos.push(this); return play.apply(this, args); };
      addEventListener('unhandledrejection', (event) => uploadRejections.push(event.reason.name));
    });
    await page.goto(origin + '/demo');
    const bytes = await page.evaluate(async () => {
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = 32;
      const ctx = canvas.getContext('2d'), stream = canvas.captureStream(20), chunks = [];
      const recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp8' });
      recorder.ondataavailable = (event) => chunks.push(event.data);
      recorder.start();
      let frame = 0;
      const timer = setInterval(() => { ctx.fillStyle = `rgb(${frame++ * 20 % 255},100,180)`; ctx.fillRect(0, 0, 32, 32); }, 40);
      await new Promise((r) => setTimeout(r, 600));
      await new Promise((r) => { recorder.onstop = r; recorder.stop(); });
      clearInterval(timer); stream.getTracks().forEach((track) => track.stop());
      return Array.from(new Uint8Array(await new Blob(chunks).arrayBuffer()));
    });
    const buffer = Buffer.from(bytes);
    await writeFile(path.join(out, 'upload-fixture.webm'), buffer);
    const uploadVideo = async (name) => {
      await page.setInputFiles('#file', { name, mimeType: 'video/webm', buffer });
      await page.waitForFunction(() => uploadVideos.length && !uploadVideos.at(-1).paused && uploadVideos.at(-1).readyState >= 2);
    };
    await uploadVideo('first.webm');
    await page.click('[data-p="ember"]'); await page.click('[data-r="braille"]');
    const retained = await page.evaluate(() => ({ created: uploadUrls.length, revoked: revokedUrls.length, playing: !uploadVideos[0].paused }));
    await page.click('[data-s="jellyfish"]');
    const preset = await page.evaluate(() => ({ paused: uploadVideos[0].paused, src: uploadVideos[0].getAttribute('src'), revoked: revokedUrls.length }));
    await uploadVideo('second.webm'); await uploadVideo('replacement.webm');
    const replaced = await page.evaluate(() => ({ paused: uploadVideos[1].paused, src: uploadVideos[1].getAttribute('src'),
      created: uploadUrls.length, revoked: revokedUrls.length, currentPlaying: !uploadVideos[2].paused }));
    await page.setInputFiles('#file', { name: 'image.svg', mimeType: 'image/svg+xml', buffer: Buffer.from(svg) });
    // Both changes and preset selection occur in one task, before the real media load/play promises settle.
    await page.evaluate(({ bytes, svg }) => {
      const input = document.querySelector('#file');
      const change = (file) => { const data = new DataTransfer(); data.items.add(file); input.files = data.files; input.dispatchEvent(new Event('change', { bubbles: true })); };
      change(new File([new Uint8Array(bytes)], 'pending.webm', { type: 'video/webm' }));
      change(new File([svg], 'pending.svg', { type: 'image/svg+xml' }));
      document.querySelector('[data-s="jellyfish"]').click();
    }, { bytes, svg });
    await page.waitForTimeout(250);
    const final = await page.evaluate(() => ({ created: uploadUrls.length, revoked: revokedUrls.length,
      uniqueRevoked: new Set(revokedUrls).size, allRevoked: uploadUrls.every((url) => revokedUrls.includes(url)),
      videos: uploadVideos.map((video) => ({ paused: video.paused, src: video.getAttribute('src') })), rejections: uploadRejections }));
    const detail = JSON.stringify({ retained, preset, replaced, final });
    assert.deepEqual(retained, { created: 1, revoked: 0, playing: true }, detail);
    assert.deepEqual(preset, { paused: true, src: null, revoked: 1 }, detail);
    assert.deepEqual(replaced, { paused: true, src: null, created: 3, revoked: 2, currentPlaying: true }, detail);
    assert.ok(final.created === 6 && final.revoked === 6 && final.uniqueRevoked === 6 && final.allRevoked, detail);
    assert.ok(final.videos.every((video) => video.paused && video.src === null), detail);
    assert.deepEqual(final.rejections, [], detail);
    return { retained, preset, replaced, final };
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
