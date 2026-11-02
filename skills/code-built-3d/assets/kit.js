// Code-built 3D kit: build scenes from parts written as code, render them like a technical illustration
// (flat 3-tone faces, thin ink edges, white haze), move an orthographic camera between shots, cut shells away,
// explode assemblies into labelled parts, stream endless chunks. No textures or image files anywhere.
// ES module. Needs an import map with "three" and "three/addons/" (see demo.html).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/BufferGeometryUtils.js';

export { THREE };
export const reduced = matchMedia('(prefers-reduced-motion: reduce)');
export const ease = t => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * t * (t * (t * 6 - 15) + 10)); // smootherstep
export const lerp = (a, b, t) => a + (b - a) * t;

// Deterministic randomness: the same seed always builds the same city.
export function rng(seed) {
  let s = typeof seed === 'number' ? seed >>> 0 : [...String(seed)].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 2166136261);
  const next = () => { s += 0x6d2b79f5; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  next.range = (a, b) => a + (b - a) * next();
  next.int = (a, b) => Math.floor(next.range(a, b + 1));
  next.pick = arr => arr[Math.floor(next() * arr.length)];
  next.chance = p => next() < p;
  return next;
}

/* ---------- look: tones baked per face, one shader for faces, one for edges ---------- */
// Tones are lightness 0..1. Faces are shaded by orientation, the way an isometric illustration is coloured:
// tops lightest, the two faces toward the camera a step and two steps darker.
export const TONES = { white: 1, light: 0.97, mid: 0.9, grey: 0.8, dark: 0.5, ink: 0.16 };
function shade(n) {
  if (n.y > 0.5) return 1;
  if (n.y < -0.5) return 0.62;
  if (Math.abs(n.x) >= Math.abs(n.z)) return n.x > 0 ? 0.92 : 0.8;
  return n.z > 0 ? 0.85 : 0.76;
}
function bakeColors(geo, tone, tint) {
  const n = geo.attributes.normal, c = new Float32Array(n.count * 3), v = new THREE.Vector3();
  for (let i = 0; i < n.count; i++) {
    v.fromBufferAttribute(n, i); const l = tone * shade(v);
    c[i * 3] = l * tint[0]; c[i * 3 + 1] = l * tint[1]; c[i * 3 + 2] = l * tint[2];
  }
  geo.setAttribute('color', new THREE.BufferAttribute(c, 3));
}

const FOG = `uniform vec3 uBg;uniform float uFocusY,uVNear,uVFar,uDNear,uDFar,uOpacity;`;
const VS = (line) => `${FOG}attribute vec3 color;varying vec3 vC;varying float vF;
void main(){vec4 wp=modelMatrix*vec4(position,1.);vec4 mv=viewMatrix*wp;gl_Position=projectionMatrix*mv;
${line ? 'gl_Position.z-=0.0006*gl_Position.w;' : ''}
float fv=smoothstep(uVNear,uVFar,abs(wp.y-uFocusY));float fd=smoothstep(uDNear,uDFar,-mv.z);vF=max(fv,fd);vC=color;}`;
const FS = `${FOG}varying vec3 vC;varying float vF;void main(){gl_FragColor=vec4(mix(vC,uBg,min(vF,1.)),uOpacity);}`;

export function createLook({ bg = '#f3f3f0', ink = '#1d1e1d', tint = [1, 0.996, 0.985] } = {}) {
  const uniforms = {
    uBg: { value: new THREE.Color(bg) }, uFocusY: { value: 0 },
    // Haze: vertical distance from the focus height, plus depth beyond the focus plane (the camera sits 400 away).
    uVNear: { value: 18 }, uVFar: { value: 46 }, uDNear: { value: 404 }, uDFar: { value: 452 }, uOpacity: { value: 1 },
  };
  const face = new THREE.ShaderMaterial({ uniforms, vertexShader: VS(false), fragmentShader: FS, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  const edge = new THREE.ShaderMaterial({ uniforms, vertexShader: VS(true), fragmentShader: FS });
  const inkC = new THREE.Color(ink);
  return { uniforms, face, edge, bg: new THREE.Color(bg), ink: inkC, tint };
}

/* ---------- parts and assemblies ---------- */
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new THREE.Vector3(1, 1, 1);

// An assembly is a named list of parts. Every part keeps a name, a role ('shell' parts can be cut away),
// a size and an explode direction, so the same assembly can be drawn whole, cut open, exploded or listed.
export class Assembly {
  constructor(name, look) { this.name = name; this.look = look; this.parts = []; }
  _add(name, geo, { tone = 'light', at = [0, 0, 0], rot = [0, 0, 0], role = 'part', explode = null, edges = 25, label } = {}) {
    _m.compose(new THREE.Vector3(...at), _q.setFromEuler(_e.set(...rot)), _s);
    geo.applyMatrix4(_m);
    if (geo.index) geo = geo.toNonIndexed();
    geo.computeVertexNormals();
    bakeColors(geo, typeof tone === 'number' ? tone : TONES[tone], this.look.tint);
    const eg = edges ? new THREE.EdgesGeometry(geo, edges) : null;
    if (eg) bakeFlat(eg, this.look.ink);
    geo.computeBoundingBox();
    const part = { name, label: label || name, role, geo, eg, explode, box: geo.boundingBox.clone() };
    this.parts.push(part); return part;
  }
  // Boxes and cylinders are placed by the centre of their base, which is how things stand on floors.
  box(name, w, h, d, o = {}) { return this._add(name, new THREE.BoxGeometry(w, h, d).translate(0, h / 2, 0), o); }
  cyl(name, r, h, o = {}) { return this._add(name, new THREE.CylinderGeometry(o.r2 ?? r, r, h, o.seg ?? 10).translate(0, h / 2, 0), { edges: 40, ...o }); }
  cone(name, r, h, o = {}) { return this._add(name, new THREE.ConeGeometry(r, h, o.seg ?? 7).translate(0, h / 2, 0), { edges: 40, ...o }); }
  ball(name, r, o = {}) { return this._add(name, new THREE.IcosahedronGeometry(r, o.detail ?? 1), { edges: 30, ...o }); }
  // A polyline drawn in ink only (cables, railings, frames).
  line(name, points, o = {}) {
    const g = new THREE.BufferGeometry().setFromPoints(points.flatMap((p, i) => i ? [points[i - 1], p] : []));
    bakeFlat(g, this.look.ink); g.computeBoundingBox();
    const part = { name, label: o.label || name, role: o.role || 'part', geo: null, eg: g, explode: o.explode || null, box: g.boundingBox.clone() };
    this.parts.push(part); return part;
  }
  // Merged: two draw calls per role. Separate: one Object3D per part (needed to explode or pick parts).
  build({ separate = false } = {}) {
    const root = new THREE.Group(); root.name = this.name; root.userData.assembly = this;
    const roles = {};
    const holder = r => roles[r] || (roles[r] = Object.assign(new THREE.Group(), { name: r }));
    if (!separate) {
      const by = {};
      for (const p of this.parts) (by[p.role] ||= []).push(p);
      for (const [r, ps] of Object.entries(by)) {
        const g = holder(r), faces = ps.filter(p => p.geo).map(p => p.geo), edges = ps.filter(p => p.eg).map(p => p.eg);
        if (faces.length) g.add(new THREE.Mesh(mergeGeometries(faces), this.look.face));
        if (edges.length) g.add(new THREE.LineSegments(mergeGeometries(edges), this.look.edge));
      }
    } else {
      for (const p of this.parts) {
        const o = new THREE.Group(); o.name = p.name; o.userData.part = p;
        if (p.geo) o.add(new THREE.Mesh(p.geo, this.look.face));
        if (p.eg) o.add(new THREE.LineSegments(p.eg, this.look.edge));
        p.object = o; holder(p.role).add(o);
      }
    }
    for (const g of Object.values(roles)) root.add(g);
    root.userData.roles = roles;
    return root;
  }
  // The part list: the same data a dimensional drawing or an exploded view needs.
  manifest() {
    const s = new THREE.Vector3(), c = new THREE.Vector3();
    return this.parts.filter(p => p.role !== 'shell').map(p => {
      p.box.getSize(s); p.box.getCenter(c);
      return { name: p.label, role: p.role, size: [s.x, s.y, s.z].map(v => +v.toFixed(2)), at: [c.x, c.y, c.z].map(v => +v.toFixed(2)) };
    });
  }
}
function bakeFlat(g, color) {
  const n = g.attributes.position.count, c = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { c[i * 3] = color.r; c[i * 3 + 1] = color.g; c[i * 3 + 2] = color.b; }
  g.setAttribute('color', new THREE.BufferAttribute(c, 3));
}
export function dispose(obj) {
  obj.traverse(o => { if (o.geometry && !o.userData.keepGeometry) o.geometry.dispose(); });
  obj.removeFromParent();
}

/* ---------- exploding and cutting ---------- */
// Explode a separately built assembly, amount 0..1. Parts spread a little outward and rise in layers (higher parts
// rise more), so a crowded room opens upward instead of pushing parts through its own walls. bounds (Box3, optional)
// keeps every part's footprint inside, e.g. the room's floor.
export function exploder(root, { spread = 0.6, lift = 1.6, bounds = null } = {}) {
  const a = root.userData.assembly, center = new THREE.Vector3(), tmp = new THREE.Vector3();
  const boxes = a.parts.filter(p => p.object && p.role !== 'shell');
  const all = new THREE.Box3(); boxes.forEach(p => all.union(p.box)); all.getCenter(center);
  const items = boxes.map((p, i) => {
    p.box.getCenter(tmp); const d = p.explode ? new THREE.Vector3(...p.explode) : tmp.clone().sub(center).setY(0);
    if (d.lengthSq() < 1e-4) d.set(0.3, 0, 0.3);
    const h = (tmp.y - all.min.y) / Math.max(1e-3, all.max.y - all.min.y);
    const off = d.multiplyScalar(spread).add(new THREE.Vector3(0, lift * (0.5 + 1.3 * h) + 0.12 * (i % 4), 0));
    if (bounds) for (const k of ['x', 'z']) {
      if (p.box.min[k] + off[k] < bounds.min[k]) off[k] = bounds.min[k] - p.box.min[k];
      if (p.box.max[k] + off[k] > bounds.max[k]) off[k] = bounds.max[k] - p.box.max[k];
    }
    return { p, home: p.object.position.clone(), off };
  });
  return amount => { for (const it of items) it.p.object.position.copy(it.home).addScaledVector(it.off, amount); };
}
// Lower a shell group like a wall sinking into the floor (1 = standing, 0 = gone).
export function setShell(group, amount) {
  group.scale.y = Math.max(0.001, amount); group.visible = amount > 0.002;
}

/* ---------- stage: renderer, orthographic camera, shots ---------- */
export function createStage(canvas, look, { view = 34 } = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setClearColor(look.bg, 1);
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 1200);
  const resize = () => {
    const w = canvas.clientWidth || innerWidth, h = canvas.clientHeight || innerHeight, a = w / h;
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setSize(w, h, false);
    const v = a < 1 ? view / a * 0.85 : view; // portrait screens: keep the width
    camera.left = -v * a / 2; camera.right = v * a / 2; camera.top = v / 2; camera.bottom = -v / 2; camera.updateProjectionMatrix();
  };
  resize(); addEventListener('resize', resize);
  return { renderer, scene, camera, resize };
}

// A shot is { target: [x,y,z], zoom, az (degrees around y), el (degrees above horizon) }. Moving between shots
// interpolates every value with smootherstep; zoom interpolates in log space so pushes feel even.
export class Director {
  constructor(camera, shot) { this.camera = camera; this.from = this.to = this._norm(shot); this.t = 1; this.dur = 1; this.apply(this.to); }
  _norm(s) { return { target: new THREE.Vector3(...(s.target.isVector3 ? s.target.toArray() : s.target)), zoom: s.zoom ?? 1, az: s.az ?? 45, el: s.el ?? 32 }; }
  current() { const k = ease(this.t); const a = this.from, b = this.to; return { target: a.target.clone().lerp(b.target, k), zoom: Math.exp(lerp(Math.log(a.zoom), Math.log(b.zoom), k)), az: lerp(a.az, b.az, k), el: lerp(a.el, b.el, k) }; }
  go(shot, dur = 2.4) { this.from = this.current(); this.to = this._norm(shot); this.t = reduced.matches || dur <= 0 ? 1 : 0; this.dur = dur; }
  // Keep the same framing but follow a moving target (no new ease).
  follow(target) { this.to.target.set(...target); if (this.t >= 1) this.from.target.copy(this.to.target); }
  update(dt) { if (this.t < 1) this.t = Math.min(1, this.t + dt / this.dur); const c = this.current(); this.apply(c); return c; }
  apply(c) {
    const az = THREE.MathUtils.degToRad(c.az), el = THREE.MathUtils.degToRad(c.el), d = 400;
    this.camera.position.set(c.target.x + d * Math.cos(el) * Math.sin(az), c.target.y + d * Math.sin(el), c.target.z + d * Math.cos(el) * Math.cos(az));
    this.camera.zoom = c.zoom; this.camera.lookAt(c.target); this.camera.updateProjectionMatrix();
  }
  get moving() { return this.t < 1; }
}

/* ---------- picking and labels ---------- */
export function picker(stage, targets, { hover, click } = {}) {
  const ray = new THREE.Raycaster(), p = new THREE.Vector2(), el = stage.renderer.domElement;
  let last = null, downAt = null;
  const hit = e => {
    const r = el.getBoundingClientRect(); p.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(p, stage.camera); const h = ray.intersectObjects(targets(), false)[0]; return h ? h.object : null;
  };
  el.addEventListener('pointermove', e => { const o = hit(e); if (o !== last) { last = o; hover?.(o); el.style.cursor = o ? 'pointer' : ''; } });
  el.addEventListener('pointerleave', () => { last = null; hover?.(null); });
  el.addEventListener('pointerdown', e => { downAt = [e.clientX, e.clientY]; });
  el.addEventListener('pointerup', e => { if (downAt && Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) < 6) click?.(hit(e)); downAt = null; });
}
// Box outline used to show what the pointer is over.
export function outline(look) {
  const g = new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1)); bakeFlat(g, look.ink);
  const o = new THREE.LineSegments(g, look.edge); o.visible = false; o.userData.keepGeometry = true;
  o.fit = box => { const s = new THREE.Vector3(), c = new THREE.Vector3(); box.getSize(s); box.getCenter(c); o.scale.copy(s).addScalar(0.3); o.position.copy(c); o.visible = true; };
  return o;
}
// DOM labels pinned to 3D points; hidden while their point is hazed out or off screen.
export function labels(stage, layer) {
  const items = new Set(), v = new THREE.Vector3();
  return {
    add(el, point, { maxFog = 0.6, when = null } = {}) { layer.append(el); const it = { el, point, maxFog, when }; items.add(it); return () => { items.delete(it); el.remove(); }; },
    update(focusY, vFar) {
      const w = stage.renderer.domElement.clientWidth, h = stage.renderer.domElement.clientHeight;
      for (const it of items) {
        const p = typeof it.point === 'function' ? it.point() : it.point; v.copy(p).project(stage.camera);
        const fog = Math.abs(p.y - focusY) / vFar, on = (!it.when || it.when()) && fog < it.maxFog && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05;
        it.el.hidden = !on;
        if (on) it.el.style.transform = `translate(${((v.x + 1) / 2 * w).toFixed(1)}px, ${((1 - v.y) / 2 * h).toFixed(1)}px)`;
      }
    },
  };
}

/* ---------- endless chunks ---------- */
// Keeps chunks [i - behind, i + ahead] alive around a moving coordinate; make(i) builds one, drop(i, obj) frees it.
export function streamer({ size, ahead = 3, behind = 2, make, drop }) {
  const live = new Map();
  return {
    live,
    update(coord) {
      const c = Math.floor(coord / size);
      for (let i = c - behind; i <= c + ahead; i++) if (!live.has(i)) live.set(i, make(i));
      for (const [i, o] of live) if (i < c - behind || i > c + ahead) { drop(i, o); live.delete(i); }
    },
  };
}
