// HUD interface kit: liquid-marble backdrop shader, optional HTML-in-Canvas glass panels, SVG ring text
// and barcodes. Plain script, no dependencies; exposes window.Hud. Every effect degrades: no WebGL2 → CSS
// gradient, no HTML-in-Canvas → the panel stays ordinary DOM, reduced motion → one still frame.
(function (root) {
  const doc = root.document;
  const reduced = root.matchMedia('(prefers-reduced-motion: reduce)');
  const css = (name, el = doc.documentElement) => getComputedStyle(el).getPropertyValue(name).trim();
  // Noise level from <html data-hud-level="quiet|normal|loud">: scales every shader effect.
  const level = () => ({ quiet: 0.35, normal: 0.7, loud: 1 })[doc.documentElement.dataset.hudLevel] ?? 0.35;

  function rgb(color) {
    const c = doc.createElement('canvas').getContext('2d');
    c.fillStyle = color || '#000'; const h = c.fillStyle;
    if (h[0] === '#') return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16) / 255);
    return (h.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(v => +v / 255);
  }

  function program(gl, fs) {
    const vs = '#version 300 es\nin vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
    const pr = gl.createProgram();
    for (const [type, src] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      gl.attachShader(pr, s);
    }
    gl.linkProgram(pr); gl.useProgram(pr);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const u = {}; const n = gl.getProgramParameter(pr, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const a = gl.getActiveUniform(pr, i); u[a.name] = gl.getUniformLocation(pr, a.name); }
    return u;
  }

  const NOISE = `
float h(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;mat2 m=mat2(1.6,1.2,-1.2,1.6);for(int i=0;i<5;i++){v+=a*n(p);p=m*p;a*=.5;}return v;}`;

  // Domain-warped fbm read as ink in water: paper ground, ink veins, a tint pooling in the warp.
  const MARBLE = `#version 300 es
precision highp float;uniform vec2 res;uniform float t,lv;uniform vec3 paper,ink,tint;out vec4 o;${NOISE}
void main(){vec2 p=(gl_FragCoord.xy-.5*res)/res.y*1.6;float s=t*.025;
  vec2 q=vec2(fbm(p+s),fbm(p+vec2(5.2,1.3)-s));
  vec2 r=vec2(fbm(p+2.6*q+vec2(1.7,9.2)+s*1.4),fbm(p+2.6*q+vec2(8.3,2.8)));
  float f=fbm(p+2.4*r);vec2 uv=gl_FragCoord.xy/res;float edge=smoothstep(.25,.75,distance(uv,vec2(.5)));
  float band=sin(f*16.+q.x*7.+r.y*3.);
  float vein=1.-smoothstep(0.,.06+.04*lv,abs(band));
  float pool=smoothstep(.35,.85,f);
  vec3 c=mix(paper,mix(paper,ink,.16+.16*lv),pool);
  c=mix(c,mix(paper,ink,.5+.25*lv),vein*smoothstep(.2,.8,q.y)*(.45+.45*lv));
  c=mix(c,tint,smoothstep(.45,.95,r.y)*edge*(.35+.4*lv));
  c=mix(c,paper,(.45-.25*lv)*(1.-edge));
  o=vec4(c+(h(gl_FragCoord.xy+t)-.5)*.025,1.);}`;

  // A DOM panel drawn as a texture, bent at its rim like thick glass, with a lens under the pointer.
  const GLASS = `#version 300 es
precision highp float;uniform sampler2D tex;uniform vec2 res,m;uniform float t,lv,hover;out vec4 o;
void main(){vec2 uv=gl_FragCoord.xy/res;uv.y=1.-uv.y;vec2 c=uv-.5;
  float e=min(min(uv.x,1.-uv.x),min(uv.y,1.-uv.y));float rim=1.-smoothstep(0.,.05,e);
  vec2 d=normalize(c+1e-5);vec2 u=uv-d*rim*rim*.02*lv;
  vec2 dm=uv-m;u-=dm*.06*lv*hover*exp(-dot(dm,dm)*60.);
  float ca=(.0012+.004*rim)*lv;
  vec4 g=texture(tex,u);float r=texture(tex,u+d*ca).r,b=texture(tex,u-d*ca).b;
  vec3 col=vec3(r,g.g,b);
  float sweep=smoothstep(.02,0.,abs(fract(uv.y*.7-t*.08)-.5))*.06*max(lv-.6,0.);
  col+=sweep+rim*.05*lv;
  o=vec4(col*g.a,g.a);}`;

  // Full-viewport backdrop. Pass the canvas; colors come from --hud-paper, --hud-ink, --hud-tint.
  function backdrop(canvas) {
    const gl = canvas.getContext('webgl2', { antialias: false, premultipliedAlpha: false });
    if (!gl) { canvas.dataset.hud = 'fallback'; return null; }
    let u; try { u = program(gl, MARBLE); } catch (e) { console.warn('hud backdrop', e); canvas.dataset.hud = 'fallback'; return null; }
    canvas.dataset.hud = 'webgl2';
    const t0 = performance.now(); let raf = 0, colors;
    const pick = () => { colors = ['--hud-paper', '--hud-ink', '--hud-tint'].map(k => rgb(css(k))); };
    const size = () => { const k = Math.min(devicePixelRatio, 1.5) * 0.5; canvas.width = innerWidth * k; canvas.height = innerHeight * k; gl.viewport(0, 0, canvas.width, canvas.height); };
    const frame = () => {
      raf = 0; gl.uniform2f(u.res, canvas.width, canvas.height); gl.uniform1f(u.t, reduced.matches ? 40 : (performance.now() - t0) / 1000);
      gl.uniform1f(u.lv, level()); gl.uniform3fv(u.paper, colors[0]); gl.uniform3fv(u.ink, colors[1]); gl.uniform3fv(u.tint, colors[2]);
      gl.drawArrays(gl.TRIANGLES, 0, 3); if (!reduced.matches && !doc.hidden) raf = requestAnimationFrame(frame);
    };
    const restart = () => { pick(); if (!raf) raf = requestAnimationFrame(frame); };
    pick(); size(); frame();
    addEventListener('resize', () => { size(); restart(); });
    reduced.addEventListener('change', restart); doc.addEventListener('visibilitychange', restart);
    new MutationObserver(restart).observe(doc.documentElement, { attributes: true, attributeFilter: ['data-hud-level', 'data-theme', 'class'] });
    return { restart };
  }

  const glassSupported = () => {
    const c = doc.createElement('canvas'); const gl = c.getContext('webgl2');
    return !!(gl && typeof gl.texElementSubImage2D === 'function' && 'requestPaint' in c && 'updateElementGeometry' in c);
  };

  // Wrap a panel in <canvas content="drawable"> so it is painted through the glass shader. The panel stays
  // live DOM: focus, text selection and clicks hit the real elements. Unsupported → nothing changes.
  function glass(panel) {
    if (!glassSupported()) { panel.dataset.hudGlass = 'fallback'; return null; }
    const cv = doc.createElement('canvas');
    cv.setAttribute('content', 'drawable'); cv.setAttribute('layoutsubtree', '');
    cv.className = 'hud-glass-canvas';
    panel.before(cv); cv.append(panel); panel.setAttribute('drawable', '');
    const gl = cv.getContext('webgl2', { premultipliedAlpha: true, alpha: true });
    let u; try { u = program(gl, GLASS); } catch (e) { console.warn('hud glass', e); cv.replaceWith(panel); panel.dataset.hudGlass = 'fallback'; return null; }
    panel.dataset.hudGlass = 'on';
    // Chrome 156 only accepts the element into immutable storage: texStorage2D, then texElementSubImage2D.
    let tex = null;
    const alloc = () => {
      if (tex) gl.deleteTexture(tex);
      tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
      for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
      gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, cv.width, cv.height);
    };
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    const t0 = performance.now(); let raf = 0, hover = 0, hoverTo = 0, m = [0.5, 0.5], dpr = 1;
    const size = () => {
      dpr = devicePixelRatio; const r = cv.getBoundingClientRect();
      cv.width = Math.max(1, Math.round(r.width * dpr)); cv.height = Math.max(1, Math.round(r.height * dpr)); gl.viewport(0, 0, cv.width, cv.height); alloc();
      cv.requestPaint();
    };
    const draw = () => {
      raf = 0; hover += (hoverTo - hover) * (reduced.matches ? 1 : 0.15);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform2f(u.res, cv.width, cv.height); gl.uniform2f(u.m, m[0], m[1]); gl.uniform1f(u.hover, hover);
      gl.uniform1f(u.t, (performance.now() - t0) / 1000); gl.uniform1f(u.lv, level()); gl.uniform1i(u.tex, 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      const moving = Math.abs(hoverTo - hover) > 0.01 || (level() > 0.6 && !reduced.matches);
      if (moving && !doc.hidden) raf = requestAnimationFrame(draw);
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(draw); };
    cv.addEventListener('paint', () => {
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texElementSubImage2D(gl.TEXTURE_2D, 0, 0, 0, panel, { width: cv.width, height: cv.height });
      // WebGL does not place the element for hit testing; map it 1:1 onto the canvas (CSS px → device px).
      cv.updateElementGeometry(panel, { canvasTransform: new DOMMatrix().scale(dpr) });
      kick();
    });
    cv.addEventListener('pointermove', e => { const r = cv.getBoundingClientRect(); m = [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]; hoverTo = 1; kick(); });
    cv.addEventListener('pointerleave', () => { hoverTo = 0; kick(); });
    // A drawable canvas does not size itself from its children: follow the panel's laid-out height.
    const fit = () => { const h = panel.offsetHeight; if (h && Math.abs(cv.offsetHeight - h) > 0.5) cv.style.height = h + 'px'; };
    new ResizeObserver(fit).observe(panel); fit();
    new ResizeObserver(size).observe(cv);
    new MutationObserver(kick).observe(doc.documentElement, { attributes: true, attributeFilter: ['data-hud-level'] });
    size();
    return { canvas: cv, repaint: () => cv.requestPaint() };
  }

  // Text along a circle. el: an empty element; text repeats to fill the circumference.
  function ring(el, text, { size = 360, font = 11, gap = '  ·  ' } = {}) {
    const ns = 'http://www.w3.org/2000/svg', r = size / 2 - font, id = 'hud-ring-' + Math.random().toString(36).slice(2, 8);
    const svg = doc.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', `0 0 ${size} ${size}`); svg.setAttribute('aria-hidden', 'true');
    const path = doc.createElementNS(ns, 'path'); path.id = id; path.setAttribute('fill', 'none');
    path.setAttribute('d', `M ${size / 2 - r},${size / 2} a ${r},${r} 0 1,1 ${2 * r},0 a ${r},${r} 0 1,1 ${-2 * r},0`);
    const t = doc.createElementNS(ns, 'text'); t.setAttribute('font-size', font);
    const tp = doc.createElementNS(ns, 'textPath'); tp.setAttribute('href', '#' + id);
    const reps = Math.max(1, Math.floor((2 * Math.PI * r) / ((text.length + gap.length) * font * 0.62)));
    tp.textContent = Array(reps).fill(text).join(gap) + gap;
    t.append(tp); svg.append(path, t); el.replaceChildren(svg);
    return svg;
  }

  // Decorative barcode from a string (deterministic, not a real symbology).
  function barcode(el, seed = 'HUD', { bars = 48, height = 18 } = {}) {
    let s = [...seed].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
    const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
    let x = 0, rects = '';
    for (let i = 0; i < bars; i++) { const w = 1 + Math.floor(rnd() * 3); if (i % 2 === 0) rects += `<rect x="${x}" width="${w}" height="${height}"/>`; x += w; }
    el.innerHTML = `<svg viewBox="0 0 ${x} ${height}" width="${x}" height="${height}" aria-hidden="true" fill="currentColor">${rects}</svg>`;
  }

  root.Hud = { backdrop, glass, glassSupported, ring, barcode, level, reduced };
})(window);
