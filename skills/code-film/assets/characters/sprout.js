/* ========== CHARACTER: Sprout. Pear body, a sprout that emotes, a red scarf. ==========
   Contract: makeCharacter() returns { root, pose(p, tt) }, and EXPRESSIONS maps names to face objects.
   p: x y z ry rx rz scale sq breath lean armL armR swing hug reach walk stride leaf face
   face: eye (oval|happy|wide) lid sad blink lookX lookY mouth (smile|bigsmile|flat|o|wobble) blush tear sweat */
const EXPRESSIONS = {
  平静: { mouth: 'smile', leaf: 0 },
  开心: { eye: 'happy', mouth: 'bigsmile', blush: 1, leaf: .9 },
  惊讶: { eye: 'wide', mouth: 'o', leaf: 1 },
  难过: { lid: .22, sad: .34, mouth: 'wobble', leaf: -1 },
  无语: { lid: .5, mouth: 'flat', lookX: .5, leaf: -.25 },
  生气: { lid: .3, sad: -.34, mouth: 'flat', blush: 1, leaf: .55 },
  害羞: { lookX: -.8, lookY: .5, mouth: 'smile', blush: 1.4, leaf: -.45 },
  感动: { s: 1.1, mouth: 'wobble', tear: 1, blush: 1, leaf: .35 },
};
function drawSproutFace(x, f, tt) {
  const W = 1024, H = 640, ink = '#2a1c14', lx = (f.lookX || 0) * 26, ly = (f.lookY || 0) * 20;
  x.clearRect(0, 0, W, H);
  const eyes = [[352, 292], [672, 292]];
  if (f.blush) { const a = Math.min(.5, .3 * f.blush); for (const [ex] of eyes) { const c = ex < 512 ? ex - 112 : ex + 112, g = x.createRadialGradient(c, 408, 4, c, 408, 92); g.addColorStop(0, `rgba(232,104,84,${a})`); g.addColorStop(1, 'rgba(232,104,84,0)'); x.fillStyle = g; x.beginPath(); x.ellipse(c, 408, 96, 62, 0, 0, 7); x.fill(); } }
  for (const [ex0, ey0] of eyes) {
    const ex = ex0 + lx, ey = ey0 + ly, big = (f.eye === 'wide' ? 1.18 : 1) * (f.s || 1), rw = 66 * big, rh = 88 * big, tilt = (f.sad || 0) * (ex0 < 512 ? -1 : 1), lid = clamp((f.lid || 0) + (f.blink || 0));
    x.strokeStyle = ink; x.fillStyle = ink; x.lineCap = 'round';
    if (f.eye === 'happy') { x.lineWidth = 26; x.beginPath(); x.arc(ex, ey + 34, 70, Math.PI * 1.14, Math.PI * 1.86); x.stroke(); continue; }
    if (lid > .94) { x.lineWidth = 20; x.beginPath(); x.moveTo(ex - rw, ey + 10); x.quadraticCurveTo(ex, ey + 26, ex + rw, ey + 10); x.stroke(); continue; }
    x.save(); x.translate(ex, ey); x.rotate(tilt); x.translate(-ex, -ey);
    x.beginPath(); x.rect(ex - 160, ey - rh + lid * rh * 1.75, 320, 400); x.clip();
    const g = x.createLinearGradient(0, ey - rh, 0, ey + rh); g.addColorStop(0, '#20140e'); g.addColorStop(.62, '#2e1c12'); g.addColorStop(1, '#6a3c20');
    x.fillStyle = g; x.beginPath(); x.ellipse(ex, ey, rw, rh, 0, 0, 7); x.fill();
    x.fillStyle = 'rgba(255,240,214,.34)'; x.beginPath(); x.ellipse(ex + rw * .1, ey + rh * .62, rw * .52, rh * .18, 0, 0, 7); x.fill();
    x.fillStyle = '#fff'; x.beginPath(); x.ellipse(ex - rw * .3, ey - rh * .36, rw * .3, rh * .25, -.3, 0, 7); x.fill();
    x.beginPath(); x.ellipse(ex + rw * .32, ey + rh * .14, rw * .12, rh * .1, 0, 0, 7); x.fill();
    x.restore();
    if (lid > .04) { x.save(); x.translate(ex, ey); x.rotate(tilt); x.translate(-ex, -ey); x.lineWidth = 15; x.beginPath(); x.moveTo(ex - rw - 8, ey - rh + lid * rh * 1.75); x.lineTo(ex + rw + 8, ey - rh + lid * rh * 1.75); x.stroke(); x.restore(); }
  }
  const mx = 512 + lx * .7, my = 412 + ly * .4; x.strokeStyle = ink; x.fillStyle = ink; x.lineCap = 'round'; x.lineWidth = 15;
  switch (f.mouth) {
    case 'smile': x.beginPath(); x.arc(mx, my - 24, 38, .34, Math.PI - .34); x.stroke(); break;
    case 'bigsmile': x.beginPath(); x.moveTo(mx - 50, my - 8); x.quadraticCurveTo(mx, my + 2, mx + 50, my - 8); x.quadraticCurveTo(mx + 42, my + 62, mx, my + 62); x.quadraticCurveTo(mx - 42, my + 62, mx - 50, my - 8); x.fill(); x.fillStyle = '#e8705c'; x.beginPath(); x.ellipse(mx, my + 44, 26, 15, 0, 0, 7); x.fill(); break;
    case 'o': x.beginPath(); x.ellipse(mx, my + 8, 24, 30, 0, 0, 7); x.fill(); break;
    case 'flat': x.beginPath(); x.moveTo(mx - 34, my); x.lineTo(mx + 34, my); x.stroke(); break;
    case 'wobble': x.beginPath(); for (let i = -42; i <= 42; i += 5) { const y = my + Math.sin(i * .16 + tt * 15) * 8; i === -42 ? x.moveTo(mx + i, y) : x.lineTo(mx + i, y); } x.stroke(); break;
  }
  if (f.tear) { x.fillStyle = 'rgba(150,212,244,.92)'; for (const [ex] of eyes) { const l = 64 + Math.sin(tt * 4 + ex) * 10; x.beginPath(); x.roundRect(ex - 12, 366, 24, l, 12); x.fill(); x.beginPath(); x.ellipse(ex, 372, 42, 13, 0, 0, 7); x.fill(); } }
  if (f.sweat) { const u = (tt * .9) % 1, y = 120 + u * 90; x.fillStyle = 'rgba(150,212,244,.95)'; x.beginPath(); x.moveTo(800, y - 42); x.bezierCurveTo(834, y, 826, y + 30, 800, y + 30); x.bezierCurveTo(774, y + 30, 766, y, 800, y - 42); x.fill(); }
}
function makeCharacter() {
  const root = new THREE.Group(), pivot = new THREE.Group(); root.add(pivot);
  const P = [[.001, .13], [.3, .135], [.54, .22], [.655, .44], [.635, .7], [.55, .96], [.41, 1.18], [.22, 1.33], [.001, 1.385]];
  const prof = new THREE.SplineCurve(P.map(([r, y]) => new THREE.Vector2(r, y))).getPoints(96);
  const skin = canvasTex(64, 512, (x, w, h) => { const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#FBE6A6'); g.addColorStop(.42, '#F6D57F'); g.addColorStop(.74, '#F0B860'); g.addColorStop(1, '#D9893F'); x.fillStyle = g; x.fillRect(0, 0, w, h); });
  const mat = new THREE.MeshPhysicalMaterial({ map: skin, roughness: .5, clearcoat: .42, clearcoatRoughness: .42, sheen: .7, sheenRoughness: .55, sheenColor: new THREE.Color(0xfff0d0), envMapIntensity: .78 });
  const body = new THREE.Mesh(new THREE.LatheGeometry(prof, 128), mat); body.castShadow = body.receiveShadow = true; pivot.add(body);
  // the face rides the body: a slice of the same surface carries the drawn eyes
  const faceTex = canvasTex(1024, 640);
  const slice = prof.filter(p => p.y > .52 && p.y < 1.24).map(p => new THREE.Vector2(p.x + .006, p.y));
  const face = new THREE.Mesh(new THREE.LatheGeometry(slice, 72, -1.2, 2.4), new THREE.MeshBasicMaterial({ map: faceTex, transparent: true, depthWrite: false, side: THREE.DoubleSide })); pivot.add(face);
  const footM = new THREE.MeshPhysicalMaterial({ color: 0xD98640, roughness: .46, clearcoat: .5, clearcoatRoughness: .4, envMapIntensity: .7 });
  const feet = [-1, 1].map(s => { const g = new THREE.Group(); g.position.set(s * .27, .1, .04); root.add(g); const m = new THREE.Mesh(new THREE.SphereGeometry(.2, 40, 28), footM); m.scale.set(.95, .52, 1.32); m.castShadow = m.receiveShadow = true; g.add(m); return g; });
  const arms = [-1, 1].map(s => { const g = new THREE.Group(); g.position.set(s * .63, .42, .04); pivot.add(g); const m = new THREE.Mesh(new THREE.CapsuleGeometry(.092, .2, 12, 28), mat); m.position.y = -.14; m.castShadow = true; g.add(m); return g; });
  // the scarf: a soft ring and one tail that trails behind the motion
  const wool = new THREE.MeshPhysicalMaterial({ color: 0xC8452F, roughness: .72, sheen: 1, sheenRoughness: .5, sheenColor: new THREE.Color(0xff9a78), envMapIntensity: .55 });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(.625, .08, 24, 96), wool); ring.rotation.x = Math.PI / 2; ring.position.y = .54; ring.scale.z = 1.3; ring.castShadow = true; pivot.add(ring);
  const tail = new THREE.Group(); tail.position.set(.32, .5, .56); pivot.add(tail);
  const cloth = new THREE.Mesh(roundedBox(.2, .36, .07, .03, 6), wool); cloth.position.y = -.17; cloth.castShadow = true; tail.add(cloth);
  // the sprout: a stem and two leaves on hinges. It is the character's second face.
  const green = new THREE.MeshPhysicalMaterial({ color: 0x5FA54A, roughness: .42, clearcoat: .6, clearcoatRoughness: .3, side: THREE.DoubleSide, envMapIntensity: .8 });
  const stem = new THREE.Group(); stem.position.y = 1.36; pivot.add(stem);
  const sc = new THREE.QuadraticBezierCurve3(new THREE.Vector3(0, -.03, 0), new THREE.Vector3(.01, .08, 0), new THREE.Vector3(.0, .16, 0));
  const st = new THREE.Mesh(new THREE.TubeGeometry(sc, 12, .026, 12), green); st.castShadow = true; stem.add(st);
  const leafGeo = () => {
    const g = new THREE.PlaneGeometry(1, 1, 24, 12), p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const u = p.getX(i) + .5, v = p.getY(i) * 2, w = Math.sin(Math.PI * Math.pow(u, .78)) * .17; p.setXYZ(i, u * .5, Math.abs(v) * w * .4 + Math.sin(u * 2.4) * .07, v * w); }
    g.computeVertexNormals(); return g;
  };
  const leaves = [-1, 1].map(s => { const g = new THREE.Group(); g.position.y = .16; g.rotation.y = s < 0 ? Math.PI : 0; stem.add(g); const m = new THREE.Mesh(leafGeo(), green); m.castShadow = true; g.add(m); return g; });
  let faceKey = '';
  return {
    root, mat,
    pose(p, tt) {
      root.position.set(p.x, p.y, p.z); root.rotation.set(0, p.ry || 0, 0);
      const sq = p.sq || 0, b = p.breath || 0, k = p.scale || 1;
      pivot.scale.set(k * (1 + sq * .6), k * (1 - sq + b), k * (1 + sq * .6));
      pivot.rotation.set((p.rx || 0) + (p.lean || 0), 0, p.rz || 0);
      const st = p.stride || 0, a = p.walk || 0;
      feet.forEach((g, i) => { const ph = a + i * Math.PI; g.position.y = .1 + Math.max(0, Math.sin(ph)) * .17 * st; g.position.z = .04 + Math.cos(ph) * .24 * st; g.rotation.x = -Math.sin(ph + .6) * .5 * st; });
      arms.forEach((g, i) => {
        const s = i ? 1 : -1, raise = i ? (p.armR || 0) : (p.armL || 0), swing = Math.sin(a + i * Math.PI) * .55 * st, hug = p.hug || 0, reach = p.reach || 0;
        g.rotation.set(lerp(lerp(swing, -1.15, hug), -2.5, reach), 0, lerp(s * (.28 + raise * 1.75), s * -.1, Math.max(hug, reach)));
      });
      const f = p.face || {}, base = p.leaf ?? f.leaf ?? 0, wind = Math.sin(a * .5 + 1) * .2 * st + (p.flutter || 0);
      leaves.forEach((g, i) => { g.rotation.z = lerp(.1, .95, clamp(base * .5 + .5)) - .75 + (i ? wind : -wind); });
      stem.rotation.z = -(p.rz || 0) * 1.6 - wind * .3;
      tail.rotation.set(lerp(.1, 1, st) * .5 + Math.sin(a * .5) * .12 * st, 0, .08);
      const key = JSON.stringify(f) + (f.mouth === 'wobble' || f.sweat || f.tear ? Math.floor(tt * 30) : '');
      if (key !== faceKey) { faceKey = key; drawSproutFace(faceTex.userData.ctx, f, tt); faceTex.needsUpdate = true; }
    },
  };
}
