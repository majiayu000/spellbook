#!/usr/bin/env node
// Screenshot a page that uses ascii-backdrop at desktop and phone size and with reduced motion;
// print the frame rate and any page errors.
//   npm i -D playwright && npx playwright install chromium
//   node check.mjs path/to/page.html [out-prefix]
// Set CHROME_PATH to use an existing Chrome or Chromium instead of Playwright's download.
import { chromium } from 'playwright';
import path from 'node:path';

const page = path.resolve(process.argv[2] || 'page.html');
const out = process.argv[3] || page.replace(/\.html$/, '');
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined });
const errors = [];
for (const [name, viewport] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  const p = await browser.newPage({ viewport, isMobile: name === 'phone' });
  p.on('pageerror', (e) => errors.push(`${name}: ${e}`));
  p.on('console', (m) => m.type() === 'error' && errors.push(`${name}: ${m.text()}`));
  await p.goto('file://' + page);
  await p.waitForTimeout(2500);
  await p.screenshot({ path: `${out}-${name}.png` });
  const frames = await p.evaluate(() => new Promise((resolve) => {
    const counts = new Map(), t0 = performance.now();
    const onFrame = (event) => counts.set(event.target, (counts.get(event.target) || 0) + 1);
    document.addEventListener('ascii-backdrop:frame', onFrame);
    setTimeout(() => {
      document.removeEventListener('ascii-backdrop:frame', onFrame);
      const elapsed = performance.now() - t0;
      resolve([...counts].map(([canvas, count], i) =>
        `${canvas.id || 'canvas ' + (i + 1)}: ${(count * 1000 / elapsed).toFixed(1)} completed backdrop frames/s`));
    }, 2000);
  }));
  console.log(`${name}: ${out}-${name}.png, ${frames.join('; ') || '0 completed backdrop frames/s (no frame signal observed)'}`);
  await p.close();
}
const still = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
await still.goto('file://' + page);
await still.waitForTimeout(1500);
await still.screenshot({ path: `${out}-reduced.png` });
console.log(`reduced motion: ${out}-reduced.png (should be one still frame)`);
console.log(errors.length ? 'ERRORS\n' + errors.join('\n') : 'no errors');
await browser.close();
