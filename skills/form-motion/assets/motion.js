// FORM motion kit: an exact damped spring that retargets from the current position and velocity.
// Every sample uses it. Plain script, no dependencies; exposes window.FormMotion.
// Also works as an ES module: `import './motion.js'` then read globalThis.FormMotion.
(function (root) {
  const reduced = root.matchMedia ? root.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  // One Motion drives several named values. `w` is the spring's angular frequency (higher = faster);
  // damping ratio 0.84 gives a small overshoot (~1–2 %). Values are a pure function of time since the last
  // retarget, so interrupting a motion never jumps: set() samples the current trajectory first.
  class Motion {
    constructor(initial, render, { w = 22, zeta = 0.84 } = {}) {
      this.s = {}; this.render = render; this.raf = 0; this.zeta = zeta;
      for (const [k, v] of Object.entries(initial)) this.s[k] = { x: v, v: 0, to: v, t: performance.now(), w };
      this.draw();
    }
    sample(s, now) {
      const t = (now - s.t) / 1000, z = this.zeta, w = s.w, a = z * w, b = w * Math.sqrt(1 - z * z);
      const d = s.x - s.to, c = (s.v + a * d) / b, e = Math.exp(-a * t), co = Math.cos(b * t), si = Math.sin(b * t);
      return { x: s.to + e * (d * co + c * si), v: e * ((-a * d + b * c) * co + (-a * c - b * d) * si) };
    }
    values() { const now = performance.now(); return Object.fromEntries(Object.entries(this.s).map(([k, s]) => [k, this.sample(s, now).x])); }
    velocities() { const now = performance.now(); return Object.fromEntries(Object.entries(this.s).map(([k, s]) => [k, this.sample(s, now).v])); }
    draw() { this.render(this.values()); }
    // targets: {key: to}; speeds: {key: w} to give one value a different spring (e.g. leading vs trailing edge);
    // velocities: {key: v} to hand over a release velocity (e.g. after a drag).
    set(targets, speeds = {}, velocities = {}) {
      const now = performance.now();
      for (const [k, to] of Object.entries(targets)) {
        const old = this.s[k], p = this.sample(old, now);
        this.s[k] = { x: reduced.matches ? to : p.x, v: reduced.matches ? 0 : (velocities[k] ?? p.v), to, t: now, w: speeds[k] || old.w };
      }
      reduced.matches ? this.draw() : this.start();
    }
    // Jump without animation (direct manipulation while dragging, or reduced motion).
    snap(targets) { const now = performance.now(); for (const [k, to] of Object.entries(targets)) this.s[k] = { ...this.s[k], x: to, to, v: 0, t: now }; this.draw(); }
    settled() { const now = performance.now(); return Object.values(this.s).every(s => { const p = this.sample(s, now); return Math.abs(p.x - s.to) <= 0.01 && Math.abs(p.v) <= 0.05; }); }
    start() {
      if (this.raf) return;
      const tick = () => { this.raf = 0; this.draw(); if (!this.settled()) this.raf = requestAnimationFrame(tick); };
      this.raf = requestAnimationFrame(tick);
    }
    dispose() { cancelAnimationFrame(this.raf); this.raf = 0; }
  }

  root.FormMotion = { Motion, reduced, clamp };
})(typeof window !== 'undefined' ? window : globalThis);
