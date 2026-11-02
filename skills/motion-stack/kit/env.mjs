// Copy of dimensional-drawing-motion/adapters/headless/env.mjs (kept separate so this skill runs on its own).
// Find a Chromium and an ffmpeg that already exist on this machine, so the
// scripts run without `npx playwright install` or a PATH tweak.
import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { homedir, platform } from 'node:os';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

function cacheDirs() {
  const h = homedir();
  return [
    process.env.PLAYWRIGHT_BROWSERS_PATH,
    platform() === 'darwin' && join(h, 'Library/Caches/ms-playwright'),
    platform() === 'linux' && join(h, '.cache/ms-playwright'),
    platform() === 'win32' && join(h, 'AppData/Local/ms-playwright'),
  ].filter(Boolean);
}

// Relative paths of the executable inside a ms-playwright browser folder.
const EXES = [
  'chrome-headless-shell-mac-arm64/chrome-headless-shell',
  'chrome-headless-shell-mac-x64/chrome-headless-shell',
  'chrome-headless-shell-linux64/chrome-headless-shell',
  'chrome-headless-shell-win64/chrome-headless-shell.exe',
  'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
  'chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
  'chrome-linux64/chrome',
  'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
  'chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium',
  'chrome-linux/chrome',
  'chrome-win/chrome.exe',
];
const SYSTEM = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
];

export function findChromium() {
  if (process.env.CHROMIUM_PATH && existsSync(process.env.CHROMIUM_PATH)) return { path: process.env.CHROMIUM_PATH, from: 'CHROMIUM_PATH' };
  // What the installed playwright expects, if it is there.
  try {
    const p = require('playwright').chromium.executablePath();
    if (p && existsSync(p)) return { path: p, from: 'playwright default' };
  } catch {}
  // Newest cached build of any version: headless shell first, then full chromium.
  for (const dir of cacheDirs()) {
    if (!existsSync(dir)) continue;
    const names = readdirSync(dir).filter(n => /^chromium(_headless_shell)?-\d+$/.test(n))
      .sort((a, b) => (b.includes('headless') - a.includes('headless')) || (+b.split('-')[1] - +a.split('-')[1]));
    for (const n of names) for (const e of EXES) {
      const p = join(dir, n, e);
      if (existsSync(p)) return { path: p, from: `cache ${n}` };
    }
  }
  for (const p of SYSTEM) if (existsSync(p)) return { path: p, from: 'system browser' };
  return null;
}

export function findFfmpeg() {
  const cands = [process.env.FFMPEG_PATH, 'ffmpeg', '/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/usr/bin/ffmpeg'].filter(Boolean);
  for (const c of cands) {
    try { execFileSync(c, ['-version'], { stdio: 'ignore' }); return { path: c, from: c === 'ffmpeg' ? 'PATH' : c }; } catch {}
  }
  // Playwright ships an ffmpeg for video recording, but without libx264, so it is only a last resort.
  return null;
}

export async function launch(opts = {}) {
  let chromium;
  try { ({ chromium } = require('playwright')); }
  catch { throw new Error('playwright is not installed: run `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install` in ' + new URL('..', import.meta.url).pathname); }
  const c = findChromium();
  if (!c) throw new Error('no Chromium found: run `npx playwright install chromium-headless-shell` or set CHROMIUM_PATH');
  return chromium.launch({ executablePath: c.path, ...opts });
}
