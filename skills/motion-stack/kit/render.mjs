#!/usr/bin/env node
// Render any browser scene (Three.js, PixiJS, p5, Paper, Matter, anime.js, plain canvas/SVG…)
// to MP4 as a pure function of time, and write a manifest that says how to get the same file again.
//
// The scene is an HTML page that sets
//   window.motion = { width, height, fps, duration, seed?, setup?(), frame(t), audio?() }
// frame(t) must draw the state at t from t alone. audio() may return an AudioBuffer
// (e.g. from Tone.Offline) or { sampleRate, channels: [Float32Array…] }; it is muxed into the MP4.
//
// usage:
//   node render.mjs scene.html --out film.mp4            render the film (+ film.mp4.manifest.json)
//   node render.mjs scene.html --still 2.5 --out f.png   one frame
//   node render.mjs scene.html --sheet 0,1,2.5,4 --out beats.png   contact sheet of several frames
//   node render.mjs scene.html --pure                    check frame(t) is pure (out-of-order hashes)
//   node render.mjs --check                              report Chromium and ffmpeg
// options: --root <dir> (served as /, default: scene's folder) --fps --duration --width --height
//          --from <s> --to <s> (render a range) --crf 18 --audio file.wav (overrides motion.audio)
//          --real-clock (do not freeze performance.now/Date.now/Math.random)
//          --lufs -14 (loudness target for the film's sound) --no-loudnorm (leave the level as rendered)
//          --no-audio (skip motion.audio(): a silent film)

import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, readdirSync } from 'node:fs';
import { createServer } from 'node:http';
import { spawn, spawnSync, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { dirname, resolve, relative, join, extname, sep } from 'node:path';
import { createRequire } from 'node:module';
import { findChromium, findFfmpeg } from './env.mjs';

const require = createRequire(import.meta.url);

const argv = process.argv.slice(2), o = { _: [] };
for (let i = 0; i < argv.length; i++) {
  if (!argv[i].startsWith('--')) { o._.push(argv[i]); continue; }
  const k = argv[i].slice(2), v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
  o[k] = v;
}

if (o.check) {
  const c = findChromium(), f = findFfmpeg();
  console.log('chromium:', c ? `${c.path} (${c.from})` : 'MISSING  (npx playwright install chromium-headless-shell, or CHROMIUM_PATH)');
  console.log('ffmpeg:  ', f ? `${f.path} (${f.from})` : 'MISSING  (brew install ffmpeg, or FFMPEG_PATH)');
  process.exit(c && f ? 0 : 1);
}
const SCENE = o._[0] && resolve(o._[0]);
if (!SCENE || !existsSync(SCENE)) { console.error('usage: node render.mjs scene.html [--out film.mp4]  (see SKILL.md)'); process.exit(1); }
const ROOT = resolve(o.root || dirname(SCENE));
if (!SCENE.startsWith(ROOT + sep)) { console.error('--root must contain the scene'); process.exit(1); }

// ---------- static server (ES modules and import maps do not load from file://) ----------
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.wasm': 'application/wasm', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.otf': 'font/otf',
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.glsl': 'text/plain', '.frag': 'text/plain', '.vert': 'text/plain' };
const served = new Set();
const remote = new Set();
const server = createServer((req, res) => {
  if (req.url === '/favicon.ico') { res.writeHead(204).end(); return; }
  const p = resolve(ROOT, '.' + decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !existsSync(p) || statSync(p).isDirectory()) { res.writeHead(404).end(); return; }
  served.add(relative(ROOT, p));
  res.writeHead(200, { 'content-type': MIME[extname(p).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-store' });
  res.end(readFileSync(p));
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const URL_ = `http://127.0.0.1:${server.address().port}/${relative(ROOT, SCENE).split(sep).join('/')}`;

// ---------- browser ----------
let chromium;
try { ({ chromium } = require('playwright')); }
catch { console.error(`playwright not found: run \`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install\` in ${dirname(new URL(import.meta.url).pathname)}`); process.exit(1); }
const exe = findChromium();
if (!exe) { console.error('no Chromium found: npx playwright install chromium-headless-shell, or set CHROMIUM_PATH'); process.exit(1); }
// SwiftShader gives WebGL without a GPU and the same pixels on every run.
const browser = await chromium.launch({ executablePath: exe.path, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
const errors = [];
async function openPage(viewport) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  page.on('pageerror', e => { errors.push(e.message); console.error('[scene error]', e.message); });
  page.on('console', m => { if (m.type() === 'error') console.error('[scene console]', m.text()); });
  page.on('request', r => { const u = r.url(); if (!u.startsWith('http://127.0.0.1') && !u.startsWith('data:') && !u.startsWith('blob:')) remote.add(u); });
  if (!o['real-clock']) await page.addInitScript(() => {
    // Frozen clock and seeded random: libraries that read time or Math.random see the frame's time.
    let now = 0, s = 0x9e3779b9;
    const EPOCH = Date.UTC(2026, 0, 1);
    window.__setNow = ms => { now = ms; };
    window.__seed = n => { s = (n >>> 0) || 1; };
    performance.now = () => now;
    Date.now = () => EPOCH + now;
    Math.random = () => { s |= 0; s = (s + 0x6d2b79f5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  });
  return page;
}

// Probe the scene's own size first, then open it at that size.
const probe = await openPage({ width: 800, height: 600 });
await probe.goto(URL_, { waitUntil: 'load' });
await probe.waitForFunction(() => window.motion && typeof window.motion.frame === 'function', null, { timeout: 20000 })
  .catch(() => { console.error('scene never set window.motion = { frame(t) … }'); process.exit(1); });
const meta = await probe.evaluate(() => { const m = window.motion; return { width: m.width, height: m.height, fps: m.fps, duration: m.duration, seed: m.seed }; });
await probe.close();
const W = +(o.width || meta.width || 1920), H = +(o.height || meta.height || 1080);
const FPS = +(o.fps || meta.fps || 30), DUR = +(o.duration || meta.duration || 5);

const page = await openPage({ width: W, height: H });
await page.goto(URL_, { waitUntil: 'load' });
await page.waitForFunction(() => window.motion && typeof window.motion.frame === 'function', null, { timeout: 20000 });
await page.evaluate(async seed => {
  if (window.__seed && seed != null) window.__seed(seed);
  if (window.motion.setup) await window.motion.setup();
  if (document.fonts) await document.fonts.ready;
}, meta.seed ?? 1);

async function draw(t) {
  await page.evaluate(async t => {
    if (window.__setNow) window.__setNow(t * 1000);
    await window.motion.frame(t);
    await new Promise(r => requestAnimationFrame(() => r()));
  }, t);
  return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: W, height: H } });
}
const sha = b => createHash('sha256').update(b).digest('hex');
const FF = o.ffmpeg || (findFfmpeg() || {}).path;
const run = (cmd, args) => new Promise((ok, no) => spawn(cmd, args, { stdio: ['ignore', 'inherit', 'inherit'] }).on('close', c => (c ? no(new Error(`${cmd} exited ${c}`)) : ok())));
const done = async code => { await browser.close(); server.close(); process.exit(code); };

// ---------- one frame ----------
if (o.still !== undefined) {
  const out = resolve(o.out || 'frame.png');
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, await draw(+o.still));
  console.log(`still t=${o.still} → ${out}`);
  await done(errors.length ? 3 : 0);
}

// ---------- contact sheet ----------
if (o.sheet) {
  const ts = String(o.sheet).split(',').map(Number);
  const out = resolve(o.out || 'sheet.png');
  const tmp = join(dirname(out), `.sheet-${process.pid}`);
  mkdirSync(tmp, { recursive: true });
  for (const [i, t] of ts.entries()) writeFileSync(join(tmp, `${String(i).padStart(3, '0')}.png`), await draw(t));
  const cols = Math.min(ts.length, 4), rows = Math.ceil(ts.length / cols), tw = 480, th = Math.round(tw * H / W / 2) * 2;
  const label = ts.map((t, i) => `[${i}:v]scale=${tw}:${th}[v${i}]`).join(';');
  const layout = ts.map((_, i) => `${(i % cols) * tw}_${Math.floor(i / cols) * th}`).join('|');
  const inputs = ts.flatMap((_, i) => ['-i', join(tmp, `${String(i).padStart(3, '0')}.png`)]);
  const fc = ts.length === 1 ? `${label};[v0]copy` : `${label};${ts.map((_, i) => `[v${i}]`).join('')}xstack=inputs=${ts.length}:layout=${layout}:fill=gray`;
  await run(FF, ['-y', '-loglevel', 'error', ...inputs, '-filter_complex', fc, '-frames:v', '1', out]);
  execFileSync('rm', ['-rf', tmp]);
  console.log(`sheet ${rows}×${cols}, left→right, top→bottom: t = ${ts.join(', ')} → ${out}`);
  await done(errors.length ? 3 : 0);
}

// ---------- purity check ----------
if (o.pure) {
  const n = 6, ts = Array.from({ length: n }, (_, i) => Math.round(((i + 0.5) / n) * DUR * FPS) / FPS);
  const forward = []; for (const t of ts) forward.push(sha(await draw(t)));
  const order = [...ts.keys()].reverse(); const back = [];
  for (const i of order) back[i] = sha(await draw(ts[i]));
  const bad = ts.filter((_, i) => forward[i] !== back[i]);
  console.log(bad.length ? `NOT PURE: frames at t=${bad.join(', ')} differ when drawn out of order` : `pure: ${n} frames identical forward and backward`);
  await done(bad.length ? 2 : 0);
}

// ---------- film ----------
if (!FF) { console.error('ffmpeg not found: brew install ffmpeg, or --ffmpeg /path'); await done(1); }
const OUT = resolve(o.out || 'film.mp4');
mkdirSync(dirname(OUT), { recursive: true });
// Audio first: it is offline and takes seconds, so a broken audio() fails here, before minutes of frames.
let audio = o.audio ? resolve(o.audio) : null, audioFrom = audio ? 'file' : null;
if (!audio && !o['no-audio']) {
  const b64 = await page.evaluate(async () => {
    if (!window.motion.audio) return null;
    let a = await window.motion.audio();
    if (a && typeof a.get === 'function' && !(a instanceof AudioBuffer)) a = a.get(); // ToneAudioBuffer
    const sr = a.sampleRate, ch = a instanceof AudioBuffer ? Array.from({ length: a.numberOfChannels }, (_, i) => a.getChannelData(i)) : a.channels;
    const n = ch[0].length, c = ch.length, buf = new DataView(new ArrayBuffer(44 + n * c * 2));
    const s = (o, str) => [...str].forEach((ch, i) => buf.setUint8(o + i, ch.charCodeAt(0)));
    s(0, 'RIFF'); buf.setUint32(4, 36 + n * c * 2, true); s(8, 'WAVEfmt '); buf.setUint32(16, 16, true); buf.setUint16(20, 1, true);
    buf.setUint16(22, c, true); buf.setUint32(24, sr, true); buf.setUint32(28, sr * c * 2, true); buf.setUint16(32, c * 2, true); buf.setUint16(34, 16, true);
    s(36, 'data'); buf.setUint32(40, n * c * 2, true);
    for (let i = 0, off = 44; i < n; i++) for (let k = 0; k < c; k++, off += 2) buf.setInt16(off, Math.max(-1, Math.min(1, ch[k][i])) * 0x7fff, true);
    const bytes = new Uint8Array(buf.buffer); let bin = '';
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  }).catch(e => {
    console.error(`\naudio() failed before any frame was rendered:\n  ${String(e.message || e).split('\n')[0]}\n` +
      'fix the sound and run again, or add --no-audio for a silent film (Tone: one mono synth cannot start twice at the same time; space triggers apart or use a PolySynth)');
    return { failed: true };
  });
  if (b64 && b64.failed) await done(4);
  if (b64) { audio = OUT.replace(/\.mp4$/i, '.wav'); writeFileSync(audio, Buffer.from(b64, 'base64')); audioFrom = 'motion.audio()'; }
}
const from = +(o.from || 0), to = +(o.to ?? DUR);
const N = Math.round((to - from) * FPS);
const silent = OUT.replace(/\.mp4$/i, '') + `.video-${process.pid}.mp4`;
const ff = spawn(FF, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', String(o.crf || 18), '-preset', 'medium', '-movflags', '+faststart', silent],
  { stdio: ['pipe', 'inherit', 'inherit'] });
const t0 = Date.now();
for (let i = 0; i < N; i++) {
  const buf = await draw(from + i / FPS);
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % FPS === 0) process.stdout.write(`\rframe ${i}/${N}`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));

if (audio) await run(FF, ['-y', '-loglevel', 'error', '-i', silent, '-ss', String(from), '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT]);
else await run(FF, ['-y', '-loglevel', 'error', '-i', silent, '-c', 'copy', OUT]);
execFileSync('rm', ['-f', silent]);
// Loudness: offline synths come out quiet or uneven; bring the mix to a target (two-pass loudnorm, video copied untouched).
let loud = null;
if (audio && !o['no-loudnorm']) {
  const target = +(o.lufs ?? -14);
  const measure = f => { const r = spawnSync(FF, ['-hide_banner', '-nostats', '-i', f, '-af', `loudnorm=I=${target}:TP=-1.5:LRA=11:print_format=json`, '-f', 'null', '-'], { encoding: 'utf8' });
    const j = r.stderr.slice(r.stderr.lastIndexOf('{')); return JSON.parse(j.slice(0, j.indexOf('}') + 1)); };
  const m1 = measure(OUT);
  const tmp = OUT.replace(/\.mp4$/i, '') + `.loud-${process.pid}.mp4`;
  await run(FF, ['-y', '-loglevel', 'error', '-i', OUT, '-c:v', 'copy', '-af',
    `loudnorm=I=${target}:TP=-1.5:LRA=11:measured_I=${m1.input_i}:measured_TP=${m1.input_tp}:measured_LRA=${m1.input_lra}:measured_thresh=${m1.input_thresh}:offset=${m1.target_offset}:linear=true`,
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', tmp]);
  execFileSync('mv', [tmp, OUT]);
  const m2 = measure(OUT);
  loud = { target_lufs: target, before_lufs: +m1.input_i, after_lufs: +m2.input_i, after_true_peak: +m2.input_tp };
  console.log(`\nloudness ${loud.before_lufs} → ${loud.after_lufs} LUFS (target ${target}, true peak ${loud.after_true_peak} dBTP)`);
}
const secs = ((Date.now() - t0) / 1000).toFixed(1);
console.log(`\r${N} frames${audio ? ' + audio' : ''} → ${OUT}  (${secs} s)`);

// ---------- manifest: everything needed to get this file again ----------
const fonts = await page.evaluate(() => document.fonts ? [...document.fonts].map(f => `${f.family} ${f.weight} ${f.style} ${f.status}`) : []);
const webgl = await page.evaluate(() => { try { const g = document.createElement('canvas').getContext('webgl2'); const d = g.getExtension('WEBGL_debug_renderer_info'); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER); } catch { return null; } });
function deps() {
  const pj = join(ROOT, 'package.json');
  if (!existsSync(pj)) return {};
  const want = { ...JSON.parse(readFileSync(pj, 'utf8')).dependencies };
  for (const k of Object.keys(want)) { const p = join(ROOT, 'node_modules', k, 'package.json'); want[k] = existsSync(p) ? JSON.parse(readFileSync(p, 'utf8')).version : `NOT INSTALLED (${want[k]})`; }
  return want;
}
function files() {
  const out = {};
  for (const f of [...served].sort()) if (!f.startsWith('node_modules')) out[f] = sha(readFileSync(join(ROOT, f))).slice(0, 16);
  return out;
}
const ffv = execFileSync(FF, ['-version']).toString().split('\n')[0];
const manifest = {
  out: relative(ROOT, OUT), sha256: sha(readFileSync(OUT)), rendered: new Date().toISOString(), render_seconds: +secs,
  command: `node ${relative(ROOT, new URL(import.meta.url).pathname)} ${process.argv.slice(2).join(' ')}`.replace(/\s+/g, ' '),
  scene: relative(ROOT, SCENE), size: [W, H], fps: FPS, range: [from, to], frames: N, seed: meta.seed ?? 1, clock: o['real-clock'] ? 'real' : 'frozen',
  audio: audio ? { from: audioFrom, file: relative(ROOT, audio), sha256: sha(readFileSync(audio)).slice(0, 16), loudness: loud } : null,
  libraries: deps(), files: files(), fonts, remote_requests: [...remote],
  engine: { chromium: exe.path, chromium_version: browser.version(), webgl, ffmpeg: ffv, node: process.version, playwright: require('playwright/package.json').version },
  scene_errors: errors,
};
writeFileSync(OUT + '.manifest.json', JSON.stringify(manifest, null, 2));
console.log(`manifest → ${OUT}.manifest.json`);
if (remote.size) console.warn(`warning: ${remote.size} request(s) left the machine (CDN fonts/libs); the film may not reproduce offline:\n  ${[...remote].join('\n  ')}`);
if (errors.length) console.warn(`warning: ${errors.length} scene error(s), see manifest.scene_errors`);
await done(errors.length ? 3 : 0);
