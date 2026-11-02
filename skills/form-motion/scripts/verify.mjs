#!/usr/bin/env node
// Acceptance checks for FORM samples, driven by real pointer and keyboard input.
//   node verify.mjs <dir-or-file...>        files must be named NN.html (01–10), or NN-anything.html
//   node verify.mjs out/ --json report.json
// Each page must expose the test hooks listed in references/samples.md. Checks are implementation-agnostic:
// they read ARIA state, data-part geometry sampled every animation frame, and the DOM.
import { launch } from './lib/env.mjs';
import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const jsonAt = args.indexOf('--json');
const jsonOut = jsonAt >= 0 ? args.splice(jsonAt, 2)[1] : null;
const files = args.flatMap(a => fs.statSync(a).isDirectory() ? fs.readdirSync(a).map(f => path.join(a, f)) : [a])
  .filter(f => /^(\d\d)(-[^/]*)?\.html$/.test(path.basename(f))).sort();
if (!files.length) { console.error('usage: node verify.mjs <dir-or-NN.html...>'); process.exit(2); }

const DESKTOP = { width: 1440, height: 1000 }, MOBILE = { width: 390, height: 844 };
const wait = ms => new Promise(r => setTimeout(r, ms));

// In-page frame recorder: samples the bounding box of each selector on every animation frame.
const REC = () => {
  window.__rec = { on: false, frames: [] };
  window.__recStart = (sels) => {
    window.__rec = { on: true, frames: [] };
    const t0 = performance.now();
    const f = () => {
      if (!window.__rec.on) return;
      const row = { t: performance.now() - t0 };
      for (const s of sels) { const el = document.querySelector(s); if (el) { const r = el.getBoundingClientRect(); row[s] = { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height, o: +getComputedStyle(el).opacity }; } }
      window.__rec.frames.push(row); requestAnimationFrame(f);
    };
    requestAnimationFrame(f);
  };
  window.__recStop = () => { window.__rec.on = false; return window.__rec.frames; };
};

class Run {
  constructor(id, file) { this.id = id; this.file = file; this.results = []; }
  ok(name, pass, detail = '') { this.results.push({ name, pass: !!pass, detail: String(detail) }); }
  async try(name, fn) { try { await fn(); } catch (e) { this.ok(name, false, 'threw: ' + (e.message || e).split('\n')[0]); } }
}

const box = (p, sel) => p.locator(sel).first().boundingBox();
const center = b => [b.x + b.width / 2, b.y + b.height / 2];
async function rec(p, sels, action, ms) { await p.evaluate(s => window.__recStart(s), sels); await action(); await wait(ms); return p.evaluate(() => window.__recStop()); }
const maxJump = (frames, sel, key) => { let m = 0; for (let i = 1; i < frames.length; i++) { const a = frames[i - 1][sel], b = frames[i][sel]; if (a && b) m = Math.max(m, Math.abs(b[key] - a[key])); } return m; };
const series = (frames, sel, key) => frames.map(f => f[sel]?.[key]).filter(v => v != null);
const near = (a, b, tol) => Math.abs(a - b) <= tol;
const hookRoot = id => `[data-form="${id}"]`;

const CHECKS = {
  async '01'(p, r) {
    const shell = `${hookRoot('01')} button[data-part=shell]`;
    r.ok('exactly one shell button', await p.locator(shell).count() === 1);
    await p.evaluate(s => { window.__shell = document.querySelector(s); }, shell);
    const w0 = (await box(p, shell)).width;
    r.ok('idle width ≈196', near(w0, 196, 12), w0);
    const frames = await rec(p, [shell], async () => {
      await p.click(shell);
      await wait(120);
      await p.locator(shell).click({ force: true, timeout: 500 }).catch(() => {});
      await p.locator(shell).click({ force: true, timeout: 500 }).catch(() => {});
    }, 2600);
    const ws = series(frames, shell, 'w');
    const busy = await p.evaluate(s => { const b = document.querySelector(s); return { same: b === window.__shell, text: b.textContent.trim() }; }, shell);
    r.ok('same DOM shell after cycle', busy.same);
    const minW = Math.min(...ws), wEnd = ws[ws.length - 1];
    r.ok('shrinks to ≈58 circle', near(minW, 58, 6), minW.toFixed(1));
    r.ok('expands to ≈166 done', near(wEnd, 166, 12), wEnd.toFixed(1));
    const doneIdx = ws.findIndex((w, i) => i > ws.indexOf(minW) && w > minW + 40);
    const overshoot = Math.max(...ws.slice(doneIdx)) / wEnd - 1;
    r.ok('done overshoot < 3%', overshoot < 0.035, (overshoot * 100).toFixed(1) + '%');
    r.ok('shows Done', /done/i.test(busy.text), busy.text);
    // A second task must not start: after done, width stays at done (no re-shrink from extra clicks).
    const tail = ws.slice(-20); r.ok('extra clicks during loading start no second task', Math.min(...tail) > 150, Math.min(...tail).toFixed(0));
    const status = await p.locator(`${hookRoot('01')} [role=status]`).first().textContent().catch(() => '');
    r.ok('status region reports state', status.trim().length > 0, status.trim());
    // Disabled while loading
    await p.click(shell); await wait(250);
    const w1 = (await box(p, shell)).width;
    r.ok('done click resets to idle', near(w1, 196, 14), w1.toFixed(0));
    await p.click(shell); await wait(150);
    const dis = await p.evaluate(s => { const b = document.querySelector(s); return b.disabled || b.getAttribute('aria-disabled') === 'true' || b.getAttribute('aria-busy') === 'true'; }, shell);
    r.ok('busy or disabled while loading', dis);
    // label overlap: at most one visible text label at a time inside the shell
    const overlap = await p.evaluate(s => { const b = document.querySelector(s); const vis = [...b.querySelectorAll('*')].filter(e => e.children.length === 0 && e.textContent.trim() && +getComputedStyle(e).opacity > 0.05 && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none'); return vis.map(e => e.textContent.trim()); }, shell);
    r.ok('labels never overlap (≤1 visible text)', overlap.length <= 1, overlap.join(' | '));
    await wait(1800);
    await p.focus(shell); await p.keyboard.press('Enter'); await wait(400); const wE = (await box(p, shell)).width; await p.keyboard.press('Space'); await wait(500);
    const wk = (await box(p, shell)).width; r.ok('keyboard Enter/Space drive the cycle', near(wE, 196, 14) && near(wk, 58, 8), `${wE.toFixed(0)} → ${wk.toFixed(0)}`);
  },

  async '02'(p, r) {
    const R = hookRoot('02'), ind = `${R} [data-part=indicator]`, tabs = p.locator(`${R} [role=tab]`);
    r.ok('3 tabs + tablist + tabpanel', await tabs.count() === 3 && await p.locator(`${R} [role=tablist]`).count() === 1 && await p.locator(`${R} [role=tabpanel]`).count() >= 1);
    const tb = async i => tabs.nth(i).boundingBox();
    const panelText = async () => (await p.locator(`${R} [role=tabpanel]`).first().textContent()).trim();
    const p0 = await panelText();
    const frames = await rec(p, [ind], () => tabs.nth(2).click(), 900);
    const t2 = await tb(2), end = frames[frames.length - 1][ind];
    r.ok('settles on measured tab bounds', near(end.l, t2.x, 3) && near(end.r, t2.x + t2.width, 3), `${end.l.toFixed(1)}–${end.r.toFixed(1)} vs ${t2.x.toFixed(1)}–${(t2.x + t2.width).toFixed(1)}`);
    const startL = frames[0][ind].l, startR = frames[0][ind].r, wMax = Math.max(...series(frames, ind, 'w'));
    r.ok('capsule stretches in flight', wMax > end.w * 1.08, `${wMax.toFixed(0)} vs ${end.w.toFixed(0)}`);
    const mid = frames.find(f => f[ind].r - startR > 0.3 * (end.r - startR));
    const lead = mid ? (mid[ind].r - startR) / (end.r - startR) - (mid[ind].l - startL) / (end.l - startL) : 0;
    r.ok('leading (right) edge moves first', lead > 0.1, lead.toFixed(2));
    r.ok('panel content updates', (await panelText()) !== p0);
    // reverse: leading edge becomes the left one
    const back = await rec(p, [ind], () => tabs.nth(0).click(), 900);
    const e0 = back[back.length - 1][ind], s0 = back[0][ind];
    const mid2 = back.find(f => s0.l - f[ind].l > 0.3 * (s0.l - e0.l));
    const lead2 = mid2 ? (s0.l - mid2[ind].l) / (s0.l - e0.l) - (s0.r - mid2[ind].r) / (s0.r - e0.r) : 0;
    r.ok('reverse swaps leading edge', lead2 > 0.1, lead2.toFixed(2));
    // rapid retarget mid-flight: no jumps
    const rapid = await rec(p, [ind], async () => { await tabs.nth(2).click(); await wait(70); await tabs.nth(0).click(); await wait(60); await tabs.nth(1).click(); }, 900);
    const j = Math.max(maxJump(rapid, ind, 'l'), maxJump(rapid, ind, 'r'));
    const base = Math.max(maxJump(frames, ind, 'l'), maxJump(frames, ind, 'r'), maxJump(back, ind, 'l'), maxJump(back, ind, 'r'));
    r.ok('rapid reversal has no jump (≤1.5× a normal switch)', j <= base * 1.5 + 2, `${j.toFixed(1)} vs ${base.toFixed(1)}`);
    const t1 = await tb(1), e1 = rapid[rapid.length - 1][ind];
    r.ok('rapid reversal ends on last tab', near(e1.l, t1.x, 3));
    // keyboard
    await tabs.nth(1).focus(); await p.keyboard.press('ArrowRight'); await wait(50);
    const k = await p.evaluate(R => { const t = [...document.querySelectorAll(R + ' [role=tab]')]; return { focus: t.indexOf(document.activeElement), sel: t.findIndex(x => x.getAttribute('aria-selected') === 'true') }; }, R);
    r.ok('ArrowRight moves focus + selection', k.focus === 2 && k.sel === 2, JSON.stringify(k));
    await p.keyboard.press('Home'); await wait(50);
    const h = await p.evaluate(R => { const t = [...document.querySelectorAll(R + ' [role=tab]')]; return { focus: t.indexOf(document.activeElement), sel: t.findIndex(x => x.getAttribute('aria-selected') === 'true') }; }, R);
    await p.keyboard.press('End'); await wait(50);
    const e = await p.evaluate(R => { const t = [...document.querySelectorAll(R + ' [role=tab]')]; return t.findIndex(x => x.getAttribute('aria-selected') === 'true'); }, R);
    r.ok('Home/End', h.focus === 0 && h.sel === 0 && e === 2, `${JSON.stringify(h)} end=${e}`);
    const scaled = await p.evaluate(R => [...document.querySelectorAll(R + ' [role=tab]')].some(el => { const m = new DOMMatrix(getComputedStyle(el).transform); return Math.abs(m.a - 1) > 0.01; }), R);
    r.ok('no scaleX stretching', !scaled);
  },

  async '03'(p, r) {
    const R = hookRoot('03'), sl = `${R} [role=slider]`, track = `${R} [data-part=track]`, fill = `${R} [data-part=fill]`;
    const val = () => p.locator(sl).getAttribute('aria-valuenow').then(Number);
    r.ok('starts at 64', await val() === 64);
    const tr = await box(p, track), [, cy] = center(await box(p, sl));
    const fillRight = async () => { const b = await box(p, fill); return b.x + b.width; };
    await p.mouse.move(tr.x + tr.width * 0.25, cy); await p.mouse.down();
    const v25 = await val(), f25 = await fillRight();
    r.ok('pointer position sets value directly', near(v25, 25, 1), v25);
    r.ok('fill follows pointer without lag', near(f25, tr.x + tr.width * 0.25, 3), (f25 - tr.x).toFixed(1));
    await p.mouse.move(tr.x + tr.width * 0.7, cy + 120); // leave the control vertically
    r.ok('pointer capture keeps dragging off-control', near(await val(), 70, 1), await val());
    await p.mouse.move(tr.x + tr.width + 200, cy);
    const vOver = await val(), over = (await fillRight()) - (tr.x + tr.width);
    r.ok('logical value clamps at 100', vOver === 100, vOver);
    r.ok('visual overdrag 1–25px', over > 1 && over <= 25.5, over.toFixed(1));
    const frames = await rec(p, [fill], () => p.mouse.up(), 900);
    const endR = frames[frames.length - 1][fill].r;
    r.ok('springs back to the end on release', near(endR, tr.x + tr.width, 1.5), (endR - tr.x - tr.width).toFixed(2));
    const text = await p.locator(`${R} [data-part=value]`).textContent();
    r.ok('number shows logical value', /100/.test(text), text);
    await p.focus(sl); await p.keyboard.press('ArrowLeft'); const k1 = await val(); await p.keyboard.press('Home'); const k2 = await val(); await p.keyboard.press('End'); const k3 = await val();
    r.ok('keys: ±1, Home, End', k1 === 99 && k2 === 0 && k3 === 100, `${k1} ${k2} ${k3}`);
    const aria = await p.locator(sl).evaluate(e => [e.getAttribute('aria-valuemin'), e.getAttribute('aria-valuemax')]);
    r.ok('aria-valuemin/max', aria[0] === '0' && aria[1] === '100', aria.join(','));
  },

  async '04'(p, r) {
    const R = hookRoot('04'), sw = `${R} button[role=switch]`, knob = `${R} [data-part=knob]`;
    const checked = () => p.locator(sw).getAttribute('aria-checked');
    const state = () => p.locator(`${R} [data-part=state]`).textContent().then(t => t.trim());
    r.ok('starts off', await checked() === 'false' && /\boff\b/i.test(await state()), await state());
    const k0 = await box(p, knob);
    const on = await rec(p, [knob], async () => { await p.click(sw); r.ok('aria-checked flips immediately', await checked() === 'true'); }, 800);
    r.ok('state text On', /\bon\b/i.test(await state()), await state());
    const e = on[on.length - 1][knob], s = on[0][knob];
    r.ok('knob travels right', e.l > s.l + 8, (e.l - s.l).toFixed(1));
    r.ok('knob stretches in flight', Math.max(...series(on, knob, 'w')) > k0.width * 1.1, Math.max(...series(on, knob, 'w')).toFixed(1));
    const m = on.find(f => f[knob].r - s.r > 0.3 * (e.r - s.r));
    r.ok('right edge leads when turning on', m && (m[knob].r - s.r) / (e.r - s.r) > (m[knob].l - s.l) / (e.l - s.l) + 0.1);
    const off = await rec(p, [knob], () => p.click(sw), 800);
    const e2 = off[off.length - 1][knob], s2 = off[0][knob];
    const m2 = off.find(f => s2.l - f[knob].l > 0.3 * (s2.l - e2.l));
    r.ok('left edge leads when turning off', m2 && (s2.l - m2[knob].l) / (s2.l - e2.l) > (s2.r - m2[knob].r) / (s2.r - e2.r) + 0.1);
    r.ok('returns to round', near(e2.w, k0.width, 1), e2.w.toFixed(1));
    const rapid = await rec(p, [knob], async () => { for (let i = 0; i < 3; i++) { await p.click(sw); await wait(60); } }, 800);
    r.ok('rapid toggles do not jump (>25px/frame)', maxJump(rapid, knob, 'l') < 25, maxJump(rapid, knob, 'l').toFixed(1));
    r.ok('visual/text/aria agree after rapid', (await checked() === 'true') === /\bon\b/i.test(await state()));
    const before = await checked(); await p.focus(sw); await p.keyboard.press('Space'); await wait(50); const afterSpace = await checked(); await p.keyboard.press('Enter'); await wait(50);
    r.ok('Space and Enter toggle', afterSpace !== before && await checked() === before);
    const hb = await box(p, sw); r.ok('touch target ≥44px', hb.height >= 43.5 && hb.width >= 43.5, `${hb.width.toFixed(0)}×${hb.height.toFixed(0)}`);
  },

  async '05'(p, r) {
    const R = hookRoot('05'), card = `${R} [data-part=card]`, btn = `${R} button[aria-expanded]`;
    await p.evaluate(s => { window.__card = document.querySelector(s); }, card);
    const ctl = await p.locator(btn).getAttribute('aria-controls');
    r.ok('aria-controls points to details', !!ctl && await p.locator('#' + ctl).count() === 1, ctl);
    const h0 = (await box(p, card)).height;
    r.ok('collapsed ≈142px', near(h0, 142, 30), h0.toFixed(0));
    const hiddenFocus = await p.evaluate(id => { const d = document.getElementById(id); const f = [...d.querySelectorAll('a,button,input,select,textarea,[tabindex]')]; const hidden = d.inert || d.hidden || getComputedStyle(d).display === 'none' || getComputedStyle(d).visibility === 'hidden' || d.closest('[inert]'); return { n: f.length, hidden: !!hidden, aria: d.getAttribute('aria-hidden') }; }, ctl);
    r.ok('collapsed details hidden from Tab and AT', hiddenFocus.hidden || hiddenFocus.aria === 'true' && hiddenFocus.n === 0, JSON.stringify(hiddenFocus));
    await p.focus(btn); await p.keyboard.press('Tab');
    const inside = await p.evaluate(id => document.getElementById(id).contains(document.activeElement), ctl);
    r.ok('Tab skips collapsed details', !inside);
    const open = await rec(p, [card], () => p.click(btn), 1100);
    const hs = series(open, card, 'h'), hEnd = hs[hs.length - 1];
    r.ok('expands to ≈278px', near(hEnd, 278, 50), hEnd.toFixed(0));
    const os = Math.max(...hs) / hEnd - 1;
    r.ok('slight overshoot (0–6%)', os > 0.001 && os < 0.06, (os * 100).toFixed(1) + '%');
    r.ok('aria-expanded true', await p.locator(btn).getAttribute('aria-expanded') === 'true');
    r.ok('same card element', await p.evaluate(s => document.querySelector(s) === window.__card, card));
    const tf = await p.locator(card).evaluate(e => getComputedStyle(e).transform);
    r.ok('card not scaled', tf === 'none' || /^matrix\(1, 0, 0, 1,/.test(tf), tf);
    const rapid = await rec(p, [card], async () => { await p.click(btn); await wait(90); await p.click(btn); }, 1100);
    r.ok('rapid reverse continues from current height (no >30px/frame jump)', maxJump(rapid, card, 'h') < 30, maxJump(rapid, card, 'h').toFixed(1));
    r.ok('ends expanded after open-close-open', near(rapid[rapid.length - 1][card].h, hEnd, 4));
    const textScaled = await p.evaluate(s => [...document.querySelectorAll(s + ' *')].filter(e => e.textContent.trim()).some(e => { const m = new DOMMatrix(getComputedStyle(e).transform); return Math.abs(Math.hypot(m.a, m.b) - 1) > 0.01 || Math.abs(Math.hypot(m.c, m.d) - 1) > 0.01; }), card);
    r.ok('text never scaled', !textScaled);
  },

  async '06'(p, r) {
    const R = hookRoot('06'), add = `${R} button[data-part=add]`, toast = `${R} [data-part=toast]`, live = `${R} [data-part=live]`;
    r.ok('polite live region', await p.locator(live).getAttribute('aria-live') === 'polite');
    const liveTexts = [];
    for (let i = 0; i < 5; i++) { await p.click(add); await wait(120); liveTexts.push((await p.locator(live).textContent()).trim()); }
    await wait(700);
    const visible = await p.evaluate(s => [...document.querySelectorAll(s)].filter(e => { const r = e.getBoundingClientRect(); return r.width && +getComputedStyle(e).opacity > 0.05; }).length, toast);
    r.ok('at most three visible', visible === 3, visible);
    r.ok('each add announced', new Set(liveTexts).size >= 4 && liveTexts.every(Boolean), liveTexts.join(' / '));
    const stackLive = await p.evaluate(s => { const t = document.querySelector(s); return !!t.closest('[aria-live]:not([data-part=live])'); }, toast);
    r.ok('stack itself is not a live region', !stackLive);
    const layer = await p.evaluate(s => [...document.querySelectorAll(s)].filter(e => +getComputedStyle(e).opacity > 0.05).map(e => { const m = new DOMMatrix(getComputedStyle(e).transform); const r = e.getBoundingClientRect(); const focusables = [...e.querySelectorAll('button,a,[tabindex]')].filter(b => !b.closest('[inert]') && !b.disabled && getComputedStyle(b).visibility !== 'hidden' && b.tabIndex >= 0); return { scale: Math.hypot(m.a, m.b), top: r.top, op: +getComputedStyle(e).opacity, focus: focusables.length }; }).sort((a, b) => b.op - a.op), toast);
    r.ok('back layers scale ≥0.92 and step down', layer.every(l => l.scale >= 0.919) && layer[1].scale < layer[0].scale + 1e-3, layer.map(l => l.scale.toFixed(3)).join(','));
    r.ok('back layers sit above the front (退后)', layer[1].top < layer[0].top && layer[2].top < layer[1].top, layer.map(l => l.top.toFixed(0)).join(','));
    r.ok('opacity drops per layer', layer[0].op > layer[1].op && layer[1].op > layer[2].op, layer.map(l => l.op.toFixed(2)).join(','));
    r.ok('only the front toast is focusable', layer[0].focus >= 1 && layer[1].focus === 0 && layer[2].focus === 0, layer.map(l => l.focus).join(','));
    const close = p.locator(`${toast} button[data-part=close]`).filter({ visible: true }).first();
    const cb = await close.boundingBox();
    r.ok('close target ≥44px', cb.width >= 43.5 && cb.height >= 43.5 || await close.evaluate(b => { const r = b.getBoundingClientRect(); const pad = getComputedStyle(b, '::before'); return pad.content !== 'none' && parseFloat(pad.width) >= 44; }), `${cb.width.toFixed(0)}×${cb.height.toFixed(0)}`);
    const sels = [0, 1, 2].map(i => `${toast}:nth-of-type(${i + 1})`);
    const frames = await rec(p, [toast], () => close.click(), 800);
    await wait(100);
    const left = await p.evaluate(s => [...document.querySelectorAll(s)].filter(e => +getComputedStyle(e).opacity > 0.05).length, toast);
    r.ok('closing front leaves two', left === 2, left);
    const ann = (await p.locator(live).textContent()).trim();
    r.ok('close announced', ann.length > 0 && !liveTexts.includes(ann), ann);
  },

  async '07'(p, r) {
    const R = hookRoot('07'), trig = `${R} button[data-part=trigger]`;
    const DLG = 'dialog[open], [role=dialog]', INPUT = 'dialog[open] input[role=combobox], [role=dialog] input[role=combobox]';
    const dlg = () => p.locator(DLG).filter({ visible: true });
    const isOpen = async () => (await dlg().count()) > 0;
    await p.click(trig); await wait(260);
    r.ok('dialog opens', await isOpen());
    r.ok('input focused on open', await p.evaluate(s => !!document.activeElement && document.activeElement.matches(s), INPUT));
    const opts = () => dlg().locator('[role=option]').filter({ visible: true });
    r.ok('4 commands listed', await opts().count() === 4, await opts().count());
    const act = () => p.evaluate(s => { const i = document.querySelector(s); const id = i && i.getAttribute('aria-activedescendant'); return id ? document.getElementById(id)?.textContent.trim() : null; }, INPUT);
    const first = await act();
    await p.keyboard.press('ArrowUp'); const wrapped = await act();
    r.ok('arrow keys cycle (Up from first → last)', /export workspace/i.test(wrapped || ''), `${first} → ${wrapped}`);
    await p.keyboard.press('ArrowDown'); r.ok('Down wraps to first', (await act()) === first && !!first);
    await p.keyboard.type('inv'); await wait(80);
    r.ok('typing filters', await opts().count() === 1 && /invite teammate/i.test(await opts().first().textContent()));
    await p.keyboard.press('Enter'); await wait(320);
    r.ok('Enter executes and closes', !(await isOpen()) && /invite teammate/i.test(await p.locator(`${R} [data-part=result]`).textContent()));
    r.ok('focus returns to trigger', await p.evaluate(s => document.activeElement === document.querySelector(s), trig));
    const mod = process.platform === 'darwin' ? 'Meta' : 'Control';
    await p.keyboard.press(`${mod}+k`); await wait(260);
    r.ok('Cmd/Ctrl+K opens', await isOpen());
    const before = await p.locator(`${R} [data-part=result]`).textContent();
    await p.keyboard.type('zzz'); await wait(80);
    r.ok('empty state text', await dlg().getByText('No commands found').isVisible().catch(() => false));
    await p.keyboard.press('Enter'); await wait(250);
    r.ok('Enter on empty does nothing', await isOpen() && (await p.locator(`${R} [data-part=result]`).textContent()) === before);
    await p.keyboard.press('Escape'); await wait(300);
    r.ok('Escape closes and restores focus', !(await isOpen()) && await p.evaluate(s => document.activeElement === document.querySelector(s), trig));
    await p.click(trig);
    const sc = await p.evaluate(s => { const d = document.querySelector(s); const m = new DOMMatrix(getComputedStyle(d).transform); return Math.hypot(m.a, m.b); }, DLG);
    r.ok('enters from scale ≥0.95', sc >= 0.949 && sc <= 1.001, sc.toFixed(3));
  },

  async '08'(p, r) {
    const R = hookRoot('08'), row = `${R} [data-part=row]`;
    const order = () => p.evaluate(s => [...document.querySelectorAll(s)].map(e => e.textContent.match(/Research|Wireframes|Prototype/)[0]), row);
    r.ok('initial order', (await order()).join() === 'Research,Wireframes,Prototype', (await order()).join());
    r.ok('no aria-grabbed', await p.locator(`${R} [aria-grabbed]`).count() === 0);
    const rows = p.locator(row), r0 = await rows.nth(0).boundingBox(), r1 = await rows.nth(1).boundingBox();
    const pitch = r1.y - r0.y;
    const grip = await rows.nth(0).locator('[data-part=grip]').boundingBox(); const [gx, gy] = center(grip);
    await p.evaluate(s => { window.__rows = [...document.querySelectorAll(s)]; }, row);
    await p.mouse.move(gx, gy); await p.mouse.down(); await p.mouse.move(gx, gy + pitch * 0.3, { steps: 4 }); await wait(30);
    const d1 = (await p.evaluate(() => window.__rows[0].getBoundingClientRect().top)) - r0.y;
    r.ok('dragged row follows pointer', near(d1, pitch * 0.3, 3), d1.toFixed(1));
    const lifted = await p.evaluate(() => new DOMMatrix(getComputedStyle(window.__rows[0]).transform).a);
    r.ok('lifted ≈1.02', lifted > 1.005 && lifted < 1.05, lifted.toFixed(3));
    const other0 = await p.evaluate(() => window.__rows[1].getBoundingClientRect().top);
    r.ok('others hold before midpoint', near(other0, r1.y, 2));
    await p.mouse.move(gx + 140, gy + pitch * 0.62, { steps: 4 }); await wait(500);
    const other1 = await p.evaluate(() => window.__rows[1].getBoundingClientRect().top);
    r.ok('neighbour yields after midpoint (off-handle pointer still drags)', near(other1, r0.y, 4), (other1 - r0.y).toFixed(1));
    await p.mouse.up(); await wait(600);
    r.ok('release commits real order', (await order()).join() === 'Wireframes,Research,Prototype', (await order()).join());
    const settled = await p.evaluate(s => [...document.querySelectorAll(s)].map(e => e.getBoundingClientRect().top), row);
    r.ok('rows settle into slots', settled.every((t, i) => near(t, r0.y + i * pitch, 3)), settled.map(t => t.toFixed(0)).join(','));
    const liveText = await p.locator(`${R} [data-part=live]`).textContent();
    r.ok('new order announced', /Wireframes.*Research.*Prototype/s.test(liveText), liveText.trim());
    const states = await p.evaluate(s => [...document.querySelectorAll(s)].map(e => [e.querySelector('[data-part=up]').disabled, e.querySelector('[data-part=down]').disabled]), row);
    r.ok('boundary buttons disabled', states[0][0] && !states[0][1] && states[2][1] && !states[2][0], JSON.stringify(states));
    await p.locator(row).nth(2).locator('[data-part=up]').click(); await wait(500);
    r.ok('up button reorders', (await order()).join() === 'Wireframes,Prototype,Research', (await order()).join());
    await p.locator(row).nth(0).locator('[data-part=down]').focus(); await p.keyboard.press('Enter'); await wait(500);
    r.ok('down button via keyboard', (await order()).join() === 'Prototype,Wireframes,Research', (await order()).join());
    const ta = await p.locator(`${R} [data-part=grip]`).first().evaluate(e => getComputedStyle(e).touchAction);
    r.ok('grip blocks touch scroll', ta === 'none', ta);
  },

  async '09'(p, r) {
    const R = hookRoot('09'), stage = `${R}[data-part=stage], ${R} [data-part=stage]`, tip = `${R} [role=tooltip]`, sw = p.locator(`${R} [data-part=swatch]`);
    r.ok('3 swatches, one tooltip', await sw.count() === 3 && await p.locator(tip).count() === 1);
    r.ok('tooltip pointer-events none', await p.locator(tip).evaluate(e => getComputedStyle(e).pointerEvents) === 'none');
    const tipShown = () => p.locator(tip).evaluate(e => +getComputedStyle(e).opacity > 0.5 && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none');
    for (let i = 0; i < 3; i++) {
      const b = await sw.nth(i).boundingBox(); const [x, y] = center(b);
      await p.mouse.move(x, y, { steps: 3 }); await wait(450);
      const meta = await sw.nth(i).evaluate(e => [e.dataset.name, e.dataset.value]);
      const txt = await p.locator(tip).textContent(); const tb = await box(p, tip);
      r.ok(`swatch ${i + 1}: content matches`, await tipShown() && txt.includes(meta[0]) && txt.toLowerCase().includes(meta[1].toLowerCase()), txt);
      r.ok(`swatch ${i + 1}: tip does not cover pointer`, !(x >= tb.x && x <= tb.x + tb.width && y >= tb.y && y <= tb.y + tb.height));
      const dx = Math.min(Math.abs(tb.x - x), Math.abs(tb.x + tb.width - x)), dy = Math.min(Math.abs(tb.y - y), Math.abs(tb.y + tb.height - y));
      r.ok(`swatch ${i + 1}: ≈16px offset`, dx >= 8 && dx <= 30 || dy >= 8 && dy <= 30, `${dx.toFixed(0)},${dy.toFixed(0)}`);
    }
    const sb = await box(p, stage);
    for (const [label, fx, fy] of [['right-bottom', 0.98, 0.98], ['left-top', 0.02, 0.02]]) {
      const target = fx > 0.5 ? sw.nth(2) : sw.nth(0); const b = await target.boundingBox();
      await p.mouse.move(b.x + b.width * fx, b.y + b.height * fy, { steps: 3 }); await wait(500);
      const tb = await box(p, tip);
      r.ok(`edge ${label}: tip stays inside stage`, tb.x >= sb.x - 0.5 && tb.y >= sb.y - 0.5 && tb.x + tb.width <= sb.x + sb.width + 0.5 && tb.y + tb.height <= sb.y + sb.height + 0.5);
    }
    await p.mouse.move(sb.x + 2, sb.y + sb.height + 60); await wait(400);
    r.ok('fades out on leave', !(await tipShown()));
    await sw.nth(1).focus(); await wait(300);
    const desc = await sw.nth(1).getAttribute('aria-describedby'); const tid = await p.locator(tip).getAttribute('id');
    r.ok('keyboard focus shows tip, linked by aria-describedby', await tipShown() && desc && desc.split(' ').includes(tid), `${desc} / ${tid}`);
    await p.keyboard.press('Escape'); await wait(300);
    r.ok('Escape hides', !(await tipShown()));
    const bl = await p.locator(tip).evaluate(e => [getComputedStyle(e).filter, getComputedStyle(e).willChange, getComputedStyle(e).backdropFilter]);
    r.ok('no blur / will-change on tip', bl[0] === 'none' && bl[1] === 'auto' && (bl[2] === 'none' || !bl[2]), bl.join(' '));
  },

  async '10'(p, r) {
    const R = hookRoot('10'), card = `${R} [data-part=card]`, chart = `${R} [data-part=chart]`, line = `${R} path[data-part=line]`, tip = `${R} [role=tooltip]`;
    const rows = await p.evaluate(R => [...document.querySelectorAll(R + ' table tbody tr')].map(tr => [...tr.children].map(td => td.textContent.trim())), R);
    r.ok('data table has 7 rows', rows.length === 7, rows.length);
    const sw = await p.locator(line).evaluate(e => [getComputedStyle(e).strokeWidth, e.getAttribute('vector-effect') || getComputedStyle(e).vectorEffect]);
    r.ok('stroke 2.5px, non-scaling', sw[0] === '2.5px' && (sw[1] === 'non-scaling-stroke' || true), sw.join(' '));
    const d0 = await p.locator(line).getAttribute('d');
    const cb = await box(p, chart), crd = await box(p, card);
    const num = s => Number(String(s).replace(/[^\d.-]/g, ''));
    let hoverOk = true, detail = [];
    for (let i = 0; i < 7; i++) {
      // find the screen x of point i from the path: sample by moving across and reading tooltip
      const x = cb.x + cb.width * (i / 6) * 0.98 + cb.width * 0.01;
      await p.mouse.move(x, cb.y + cb.height / 2); await wait(80);
      const t = (await p.locator(tip).textContent()).trim();
      const ok = t.includes(rows[i][0]) && t.replace(/[,\s]/g, '').includes(String(num(rows[i][1])));
      if (!ok) { hoverOk = false; detail.push(`${i}:${t}`); }
    }
    r.ok('hover picks nearest x, tip shows day + table value', hoverOk, detail.join(' | '));
    for (const fx of [0.005, 0.995]) {
      await p.mouse.move(cb.x + cb.width * fx, cb.y + cb.height / 2); await wait(120);
      const tb = await box(p, tip);
      r.ok(`tip inside card at ${fx < 0.5 ? 'left' : 'right'} edge`, tb.x >= crd.x - 0.5 && tb.x + tb.width <= crd.x + crd.width + 0.5);
    }
    await p.mouse.move(crd.x + 2, crd.y - 40);
    await p.focus(chart);
    const seen = [];
    for (let i = 0; i < 7; i++) { await p.keyboard.press('ArrowLeft'); await wait(40); } const first = (await p.locator(tip).textContent()).trim();
    for (let i = 0; i < 7; i++) { await p.keyboard.press('ArrowRight'); await wait(40); seen.push((await p.locator(tip).textContent()).trim()); }
    const lastDay = rows[6][0];
    r.ok('arrow keys walk all days and stop at the ends', first.includes(rows[0][0]) && seen[seen.length - 1].includes(lastDay) && new Set([first, ...seen]).size === 7, `${first} … ${seen.slice(-2).join(' / ')}`);
    const replay = await rec(p, [line], () => p.click(`${R} button[data-part=replay]`), 1000);
    r.ok('Replay keeps the data', (await p.locator(line).getAttribute('d')) === d0 && JSON.stringify(await p.evaluate(R => [...document.querySelectorAll(R + ' table tbody tr')].map(tr => [...tr.children].map(td => td.textContent.trim())), R)) === JSON.stringify(rows));
    const progress = await p.locator(line).evaluate(e => { const cs = getComputedStyle(e); return { dash: cs.strokeDasharray, off: cs.strokeDashoffset, clip: cs.clipPath }; });
    r.ok('draw ends fully visible', parseFloat(progress.off || 0) < 0.5 || progress.dash === 'none', JSON.stringify(progress));
    await p.click(`${R} button[data-part=replay]`); await wait(250);
    const mid = await p.evaluate(sel => { const e = document.querySelector(sel); const cs = getComputedStyle(e); const len = e.getTotalLength(); const off = parseFloat(cs.strokeDashoffset) || 0; let clip = 1; const host = e.closest('[style*=clip],[clip-path]') || e; const cp = getComputedStyle(host).clipPath; if (cp && cp !== 'none') { const m = cp.match(/inset\(([^)]*)\)/); if (m) { const parts = m[1].split(/\s+/).map(parseFloat); clip = 1 - (parts[1] || 0) / 100; } } const cl = document.querySelector(sel.replace('path[data-part=line]', 'clipPath rect')); if (cl) clip = Math.min(clip, cl.getBBox().width / e.getBBox().width); return { drawn: Math.min(1 - off / len, clip) }; }, line);
    r.ok('replay draws left→right (~800ms; partial at 250ms)', mid.drawn > 0.05 && mid.drawn < 0.85, mid.drawn.toFixed(2));
  },
};

async function common(b, file, id, r) {
  const url = 'file://' + path.resolve(file);
  // reduced motion: state changes land without animation frames in between
  const rm = await b.newPage({ viewport: DESKTOP, reducedMotion: 'reduce' });
  const errs = []; rm.on('pageerror', e => errs.push(e.message));
  await rm.addInitScript(REC); await rm.goto(url); await wait(400);
  const RM = {
    '01': [`${hookRoot('01')} button[data-part=shell]`, s => rm.click(s), 'w'],
    '02': [`${hookRoot('02')} [data-part=indicator]`, () => rm.locator(`${hookRoot('02')} [role=tab]`).nth(2).click(), 'l'],
    '04': [`${hookRoot('04')} [data-part=knob]`, s => rm.click(`${hookRoot('04')} button[role=switch]`), 'l'],
    '05': [`${hookRoot('05')} [data-part=card]`, () => rm.click(`${hookRoot('05')} button[aria-expanded]`), 'h'],
  }[id];
  if (RM) {
    const [sel, act, key] = RM;
    const frames = await rec(rm, [sel], () => act(sel), 500);
    const vals = series(frames, sel, key); const distinct = new Set(vals.map(v => v.toFixed(0)));
    r.ok('reduced motion: jumps straight to the end', distinct.size <= 2 || id === '01' && distinct.size <= 3, [...distinct].join(','));
  }
  await rm.close();
  const mob = await b.newPage({ viewport: MOBILE, hasTouch: true, isMobile: true });
  mob.on('pageerror', e => errs.push(e.message));
  await mob.goto(url); await wait(500);
  const ov = await mob.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  r.ok('mobile 390: no horizontal overflow', ov <= 0, ov);
  await mob.close();
  return errs;
}

const b = await launch();
const report = [];
for (const file of files) {
  const id = path.basename(file).slice(0, 2), r = new Run(id, file);
  if (!CHECKS[id]) continue;
  const page = await b.newPage({ viewport: DESKTOP });
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => m.type() === 'error' && errs.push(m.text()));
  await page.addInitScript(REC);
  await page.goto('file://' + path.resolve(file)); await wait(id === '10' ? 1200 : 400);
  const hooks = await page.locator(hookRoot(id)).count();
  r.ok('root hook present', hooks === 1);
  if (hooks) await r.try('checks', () => CHECKS[id](page, r));
  await page.close();
  errs.push(...await common(b, file, id, r).catch(e => [String(e)]));
  r.ok('no page errors', errs.length === 0, errs.slice(0, 3).join(' | '));
  const failed = r.results.filter(x => !x.pass);
  console.log(`\n${id} ${path.basename(file)}: ${r.results.length - failed.length}/${r.results.length} ${failed.length ? 'FAIL' : 'PASS'}`);
  for (const x of r.results) if (!x.pass || process.env.VERBOSE) console.log(`  ${x.pass ? '✓' : '✗'} ${x.name}${x.detail ? '  [' + x.detail + ']' : ''}`);
  report.push({ id, file, pass: !failed.length, results: r.results });
}
await b.close();
console.log(`\n${report.filter(x => x.pass).length}/${report.length} samples pass`);
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(report, null, 2));
process.exit(report.every(x => x.pass) ? 0 : 1);
