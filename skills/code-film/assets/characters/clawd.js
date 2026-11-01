/* ========== CHARACTER: Clawd, the default lead of every film. Two feet. Do not delete or swap it. ==========
   Uses FACES and drawFace from the film template. */
const HEX = { orange: 0xD97757 };
const BODY = { w: 1.7, h: 1.15, d: 1.12, cy: .835, R: 1.34 };
function makeClawd() {
  const root = new THREE.Group();
  const mat = new THREE.MeshPhysicalMaterial({ color: HEX.orange, roughness: .46, clearcoat: .55, clearcoatRoughness: .32, emissive: 0xffa040, emissiveIntensity: 0, envMapIntensity: .7 });
  const g = roundedBox(BODY.w, BODY.h, BODY.d, .25, 30);
  const P = g.attributes.position, tp = new Float32Array(P.count * 3), tn = new Float32Array(P.count * 3), v = new THREE.Vector3();
  for (let i = 0; i < P.count; i++) {
    v.fromBufferAttribute(P, i).normalize();
    tn.set([v.x, v.y, v.z], i * 3);
    tp.set([v.x * BODY.R, v.y * BODY.R * 1.04, v.z * BODY.R], i * 3);
  }
  g.morphAttributes.position = [new THREE.BufferAttribute(tp, 3)];
  g.morphAttributes.normal = [new THREE.BufferAttribute(tn, 3)];
  const body = new THREE.Mesh(g, mat);
  body.position.y = BODY.cy; body.castShadow = true; body.receiveShadow = true; root.add(body);

  const faceTex = canvasTex(512, 320);
  const fg = new THREE.PlaneGeometry(1.36, .85, 28, 18), fp = fg.attributes.position, ftp = new Float32Array(fp.count * 3);
  for (let i = 0; i < fp.count; i++) {
    const X = fp.getX(i), Y = fp.getY(i) + .05, Z = BODY.d / 2 + .004;
    fp.setXYZ(i, X, Y, Z);
    v.set(X, Y, Z).normalize();
    ftp.set([v.x * (BODY.R + .006), v.y * (BODY.R * 1.04 + .006), v.z * (BODY.R + .006)], i * 3);
  }
  fg.morphAttributes.position = [new THREE.BufferAttribute(ftp, 3)];
  const face = new THREE.Mesh(fg, new THREE.MeshBasicMaterial({ map: faceTex, color: 0xffffff, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
  body.add(face);

  const legG = roundedBox(.4, .3, .5, .13, 7), nubG = roundedBox(.34, .3, .42, .13, 7);
  const legs = [[-.4, 0], [.4, 0]].map(([x, z]) => {
    const m = new THREE.Mesh(legG, mat); m.position.set(x, .15, z); m.castShadow = true; root.add(m); return m;
  });
  const nubs = [-1, 1].map(s => { const m = new THREE.Mesh(nubG, mat); m.castShadow = true; m.userData.s = s; root.add(m); return m; });

  let faceKey = '';
  return {
    root, mat, face, faceTex,
    pose(p, tt) {
      root.position.set(p.x, p.y, p.z);
      root.rotation.set(p.rx || 0, p.ry || 0, p.rz || 0);
      const sq = p.sq || 0, inf = p.inflate || 0, b = p.breath || 0;
      root.scale.set(p.scale * (1 + sq * .6), p.scale * (1 - sq + b), p.scale * (1 + sq * .6));
      body.morphTargetInfluences[0] = inf; face.morphTargetInfluences[0] = inf;
      mat.roughness = lerp(.46, .16, inf); mat.clearcoat = lerp(.55, 1, inf); mat.clearcoatRoughness = lerp(.32, .08, inf);
      mat.emissiveIntensity = (p.glow || 0) * .2;
      legs.forEach((m, i) => {
        const a = (p.walk || 0) + i * Math.PI, st = p.stride || 0;
        m.position.y = lerp(.15, BODY.cy - BODY.R * 1.02, inf) + Math.max(0, Math.sin(a)) * .15 * st;
        m.position.z = Math.cos(a) * .2 * st;
        m.position.x = [-.4, .4][i] * (1 - inf * .45);
      });
      for (const m of nubs) {
        const s = m.userData.s, arm = s < 0 ? (p.armL || 0) : (p.armR || 0);
        let x = s * (BODY.w / 2 + .1 + inf * (BODY.R - .78)), y = BODY.cy - .06 + arm * .32, z = 0, rz = s * arm * 1.1;
        const blend = (u, tx, ty, tz) => { x = lerp(x, tx, u); y = lerp(y, ty, u); z = lerp(z, tz, u); rz = lerp(rz, 0, u); };
        if (p.typing) { const w = Math.sin(tt * 44 + s * 1.3) * .06; blend(p.typing, s * .42, .56 + w, .68 + w * .4); }
        if (p.hug) blend(p.hug, s * .36, .45, .86);
        if (p.cover) blend(p.cover, s * .19, .68, .74);
        if (p.salute && s < 0) blend(p.salute, -.62, 1.28, .56);
        if (p.reach) blend(p.reach, s * .36, 1.4, .72);
        m.position.set(x, y, z); m.rotation.z = rz;
      }
      const f = p.face, k = JSON.stringify(f) + (f.eye === 'spiral' || f.mouth === 'wobble' || f.sweat || f.tear ? Math.floor(tt * 30) : '');
      if (k !== faceKey) { faceKey = k; drawFace(faceTex.userData.ctx, f, tt); faceTex.needsUpdate = true; }
    },
  };
}
const makeCharacter = makeClawd;
const EXPRESSIONS = { 平静: FACES.idle, 开心: FACES.boop, 惊讶: FACES.oops, 难过: { lid: .3, sad: .3, mouth: 'wobble' }, 无语: FACES.deadpan, 生气: { lid: .3, sad: -.3, mouth: 'flat' }, 害羞: { mouth: 'smile', blush: 1, lookX: -.8 }, 感动: FACES.moved };
