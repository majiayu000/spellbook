#!/usr/bin/env node
// repo-film: one command from a repo + time window to a finished MP4.
// usage: node make.mjs --repo <path> --since "2026-11-01 20:00" --until "2026-11-02 06:00"
//          [--out <dir>] [--branch main] [--map auto|none|<index.html>] [--config film.json] [--sheet-only]
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL = path.dirname(HERE);
// the motion-stack kit: $MOTION_KIT, else a sibling skill (same install), else the usual runtime folders
const KIT = [process.env.MOTION_KIT, path.join(SKILL, '..', 'motion-stack', 'kit'),
  ...['.claude/skills', '.codex/skills', '.agents/skills'].map(d => path.join(os.homedir(), d, 'motion-stack', 'kit'))]
  .find(k => k && fs.existsSync(path.join(k, 'render.mjs'))) || '';
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => {
  if (x.startsWith('--')) a.push([x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]); return a; }, []));
const die = m => { console.error('repo-film: ' + m); process.exit(1); };
if (!args.repo || !args.since || !args.until) die('need --repo, --since and --until');
if (!KIT) die('motion-stack kit not found: install the motion-stack skill next to this one, or set MOTION_KIT');
const repo = path.resolve(args.repo);
const name = path.basename(repo);
const out = path.resolve(args.out || path.join(os.homedir(), 'Videos/repo-film', `${name}-${String(args.since).slice(0, 10)}`));
if (!fs.existsSync(path.join(KIT, 'node_modules/playwright'))) die(`motion-stack kit is not set up: cd ${KIT} && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install`);
const run = (cmd, a, opt = {}) => execFileSync(cmd, a, { stdio: ['ignore', 'pipe', 'inherit'], ...opt }).toString();

// 1. project folder from the template
fs.mkdirSync(path.join(out, 'assets'), { recursive: true });
fs.mkdirSync(path.join(out, 'out'), { recursive: true });
for (const f of ['scene.html', 'package.json']) fs.copyFileSync(path.join(SKILL, 'template', f), path.join(out, f));
if (!fs.existsSync(path.join(out, 'node_modules/tone'))) {
  const shared = path.join(KIT, '..', 'examples/drop/node_modules');
  if (fs.existsSync(path.join(shared, 'tone'))) { fs.rmSync(path.join(out, 'node_modules'), { force: true, recursive: true }); fs.symlinkSync(shared, path.join(out, 'node_modules')); }
  else run('npm', ['install', '--silent', '--no-audit', '--no-fund'], { cwd: out });
}
fs.mkdirSync(path.join(out, 'fonts'), { recursive: true });
for (const [src, dst] of [['/System/Library/Fonts/SFNSMono.ttf', 'SFNSMono.ttf'], ['/System/Library/Fonts/SFNS.ttf', 'SFNS.ttf']])
  if (fs.existsSync(src) && !fs.existsSync(path.join(out, 'fonts', dst))) fs.copyFileSync(src, path.join(out, 'fonts', dst));

// 2. git lanes
const lanesArgs = [path.join(HERE, 'lanes.py'), repo, '--since', args.since, '--until', args.until];
if (args.branch) lanesArgs.push('--branch', args.branch);
const nightJson = run('python3', lanesArgs);
fs.writeFileSync(path.join(out, 'assets/night.json'), nightJson);
const night = JSON.parse(nightJson);
const N = night.commits.length, B = night.segments.length;

// 3. the you-are-here map, if there is one
let mapFile = null;
if (args.map !== 'none') {
  const cands = args.map && args.map !== 'auto' ? [path.resolve(args.map)]
    : ['index.public.html', 'index.html'].map(f => path.join(repo, '.project-map', f));
  mapFile = cands.find(f => fs.existsSync(f)) || null;
}
if (mapFile) {
  const html = fs.readFileSync(mapFile, 'utf8');
  if (/\/Users\/|\/home\/|[A-Z]:\\\\Users/.test(html)) console.warn(`repo-film: warning: ${mapFile} contains local paths; they will be visible in the film`);
  run('node', [path.join(HERE, 'capture.mjs'), mapFile, path.join(out, 'assets')], { env: { ...process.env, MOTION_KIT: KIT } });
}

// 4. words: defaults from the data, overridden by --config
const def = {
  hasMap: !!mapFile,
  sub: `${night.repo.toUpperCase()} · ${night.from} → ${night.to}`,
  startLabel: `${night.commits[0].t.slice(-5)} 开工`,
  captions: [
    ['你离开了。', 'You step away.'],
    ['agent 们接着干。', 'The agents keep going.'],
    B ? [`${N} 个提交，${B} 条分支。`, `${N} commits. ${B} branches.`] : [`${N} 个提交。`, `${N} commits.`],
    ...(mapFile ? [['回来，打开一页。', 'Come back. Open one page.']] : []),
  ],
  end: { title: night.repo, tagline: `${night.from} → ${night.to}`, taglineEn: `${N} commits · ${B} branches · ${night.merges} merges`, lines: [], meta: '' },
};
const cfg = args.config ? JSON.parse(fs.readFileSync(path.resolve(args.config), 'utf8')) : {};
const film = { ...def, ...cfg, end: { ...def.end, ...(cfg.end || {}) }, hasMap: def.hasMap };
fs.writeFileSync(path.join(out, 'assets/film.js'), 'window.FILM = ' + JSON.stringify(film, null, 1) + ';\n');

// 5. render: beat sheet first, then the purity check, then the film
const render = a => run('node', [path.join(KIT, 'render.mjs'), 'scene.html', ...a], { cwd: out, stdio: ['ignore', 'pipe', 'inherit'] });
const dur = mapFile ? 24 : 13.4;
const beats = mapFile ? [0.6, 2.5, 4.5, 6.5, 8.0, 10.2, 12.0, 14.0, 16.5, 18.8, 22.0] : [0.6, 2.5, 4.5, 6.5, 8.0, 9.0, 11.5];
render(['--sheet', beats.join(','), '--out', 'out/beats.png']);
console.log(`beats  → ${path.join(out, 'out/beats.png')}`);
if (!args['sheet-only']) {
  render(['--pure']);
  const final = path.join(out, 'out', `${night.repo}-film.mp4`);
  render(['--out', final]);                      // the kit brings the sound to -14 LUFS itself
  const m = JSON.parse(fs.readFileSync(final + '.manifest.json', 'utf8'));
  if (m.scene_errors?.length || m.remote_requests?.length) console.warn('repo-film: manifest has errors or remote requests:', m.scene_errors, m.remote_requests);
  console.log(`film   → ${final}  (${dur}s, ${N} commits, ${B} branches${mapFile ? ', with map' : ''})`);
}
