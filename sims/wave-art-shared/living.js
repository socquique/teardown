// The living picture (sims/strandbeest-print/living.py): the relief wave cut into three bodies that rock on hidden
// pins, driven from behind the sky panel by three eccentric discs on one camshaft and the TT motor at 12:1. Every
// mesh is the STL geometry itself (living.json); every movement is the same kinematics the verification sweeps.
// Views 1-4, MECANISMO (M: the box turns to glass), DESPIECE (E), RITMO (R: real speed or x4), PAUSA (space).
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import L from './living.json';

const D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const ease = (x) => {
  const u = clamp(x, 0, 1);
  return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
};

const CSS = `
html,body{margin:0;height:100%;background:#e7dfd2;overflow:hidden;font-family:Inter,system-ui,sans-serif;color:#2a2622}
#app,#app *{color:#2a2622}
.info span,.info h2,.title p,.legend span{color:#6d6458!important}
.btns button.on,.btns button.on *{color:#f3ede2!important}
#gl{position:fixed;inset:0;width:100%;height:100%;display:block;touch-action:none}
.panel{position:fixed;background:rgba(246,241,232,.9);border:1px solid rgba(60,50,40,.18);padding:14px 16px;backdrop-filter:blur(6px)}
.title{left:22px;top:20px;padding:0;background:none;border:none}
.title h1{margin:0;font:700 13px/1 Inter,sans-serif;letter-spacing:3px}
.title p{margin:6px 0 0;font:500 10px/1.4 'JetBrains Mono',monospace;letter-spacing:1px}
.legend{left:22px;top:78px;width:210px;font:500 11px/1 'JetBrains Mono',monospace}
.legend h2,.info h2{margin:0 0 10px;font:700 9px/1 Inter,sans-serif;letter-spacing:2px;color:#6d6458}
.row{display:flex;align-items:center;gap:9px;margin:7px 0}
.row i{display:block;width:14px;height:14px;border:1px solid rgba(0,0,0,.25)}
.row b{font-weight:600;min-width:58px}
.row .bar{flex:1;height:4px;background:rgba(60,50,40,.12);position:relative}
.row .bar u{position:absolute;top:-2px;width:3px;height:8px;background:#c8372d;left:50%}
.info{right:22px;top:20px;width:220px;font:500 11px/1.7 'JetBrains Mono',monospace}
.info div{display:flex;justify-content:space-between}
.btns{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);display:flex;gap:6px;flex-wrap:wrap;justify-content:center}
.btns button{font:700 9px/1 Inter,sans-serif;letter-spacing:1.5px;padding:9px 12px;border:1px solid rgba(60,50,40,.25);background:rgba(246,241,232,.92);color:#2a2622;cursor:pointer}
.btns button.on{background:#2a2622;color:#f3ede2}
.btns button small{opacity:.55;margin-right:5px}
.chip{position:fixed;left:50%;top:62px;transform:translateX(-50%);font:700 9px/1 Inter,sans-serif;letter-spacing:1.6px;padding:7px 11px;border:1px solid rgba(60,50,40,.3);background:rgba(246,241,232,.9);cursor:pointer;display:flex;gap:7px;align-items:center}
.chip i{width:6px;height:6px;border-radius:50%;background:#c8372d}
.chip.on i{animation:b 1.2s steps(2) infinite}@keyframes b{50%{opacity:.15}}
.cap{position:fixed;left:50%;bottom:66px;transform:translateX(-50%);font:600 12px/1.3 'JetBrains Mono',monospace;letter-spacing:1px;color:#3b342c;background:rgba(246,241,232,.85);padding:7px 12px;white-space:nowrap;transition:opacity .4s}
@media (max-width:820px){.legend,.info{display:none}}
`;

// the kinematics, as in living.py
const bodyAngle = (b, t) => {
  const yd = b.e * Math.sin((t + b.phase) * D2R);
  return Math.asin(yd / b.D) / D2R * (b.drive > b.pivot ? 1 : -1);
};
const onShaft = (m4, x, t) => {          // local z -> world x, local +x -> (y, z) = (sin t, cos t)
  const a = t * D2R, c = Math.cos(a), s = Math.sin(a);
  m4.set(0, 0, 1, x, s, -c, 0, L.SH_Y, c, s, 0, L.SH_Z, 0, 0, 0, 1);
  return m4;
};
const atYZ = (m4, x, y, z, deg) => {     // rotate about local z by deg, then local z -> world x
  const a = deg * D2R, c = Math.cos(a), s = Math.sin(a);
  // [[0,0,1],[1,0,0],[0,1,0]] * Rz
  m4.set(0, 0, 1, x, c, -s, 0, y, s, c, 0, z, 0, 0, 0, 1);
  return m4;
};

export function runLiving() {
  const st = document.createElement('style');
  st.textContent = CSS;
  document.head.appendChild(st);
  const app = document.getElementById('app') || document.body;
  const canvas = document.createElement('canvas');
  canvas.id = 'gl';
  app.appendChild(canvas);

  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 0.9;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#e7dfd2');
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.35;
  const camera = new THREE.PerspectiveCamera(32, 1, 1, 5000);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.minDistance = 90;
  controls.maxDistance = 900;

  const shelf = new THREE.Mesh(new THREE.BoxGeometry(700, 18, 260), new THREE.MeshStandardMaterial({color: '#b58a5c', roughness: 0.7}));
  shelf.position.set(0, -9, 0);
  shelf.receiveShadow = true;
  scene.add(shelf);
  scene.add(new THREE.HemisphereLight('#fffaf0', '#8a7a66', 0.45));
  const key = new THREE.DirectionalLight('#fff4e2', 2.0);
  key.position.set(-120, 230, 420);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, {left: -140, right: 140, top: 200, bottom: -40, near: 10, far: 900});
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.3;
  scene.add(key, key.target);
  key.target.position.set(0, 80, 0);
  const rim = new THREE.DirectionalLight('#dfe8ff', 0.6);
  rim.position.set(200, 120, -260);
  scene.add(rim);

  // ------------------------------------------------------------ the piece, art coordinates (x right, y up, z out)
  const piece = new THREE.Group();
  piece.position.set(-(L.IX0 + L.IX1) / 2, -(L.YB - 4), 0);
  scene.add(piece);
  const geo = (mesh) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(mesh.v, 3));
    g.setIndex(mesh.f);
    const n = g.toNonIndexed();
    n.computeVertexNormals();
    return n;
  };
  const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({color, roughness: 0.62, ...extra});
  const edges = (g, op = 0.14) => new THREE.LineSegments(new THREE.EdgesGeometry(g, 30), new THREE.LineBasicMaterial({color: '#1c1a17', transparent: true, opacity: op}));
  const bodies = {}, bodyOrder = Object.keys(L.bodies);
  for (const [bn, b] of Object.entries(L.bodies)) {
    const g = new THREE.Group();
    g.position.set(b.pivot, L.PIV_Y, 0);
    const inner = new THREE.Group();
    inner.position.set(-b.pivot, -L.PIV_Y, 0);
    g.add(inner);
    piece.add(g);
    bodies[bn] = {...b, g, inner};
  }
  const fixed = {}, glass = [], eccs = [], gears = [];
  let shaft = null;
  for (const p of L.parts) {
    const g = geo(p.mesh);
    const m = new THREE.Mesh(g, mat(p.color, p.name === 'motor' ? {roughness: 0.45} : p.gear || p.ecc || p.shaft ? {roughness: 0.4, metalness: 0.1} : {}));
    m.castShadow = m.receiveShadow = true;
    if (p.body) {
      bodies[p.body].inner.add(m);
      m.add(edges(g));
    } else if (p.ecc) {
      m.matrixAutoUpdate = false;
      piece.add(m);
      eccs.push({m, b: L.bodies[p.ecc]});
    } else if (p.shaft) {
      m.matrixAutoUpdate = false;
      piece.add(m);
      shaft = m;
    } else if (p.gear) {
      m.matrixAutoUpdate = false;
      piece.add(m);
      gears.push({m, ...p.gear});
    } else {
      piece.add(m);
      fixed[p.name] = m;
      if (['back', 'frame', 'side_l', 'side_r', 'top', 'rear', 'base'].includes(p.name)) {
        m.material.transparent = true;
        glass.push(m);
      }
      if (['back', 'sun', 'frame'].includes(p.name)) m.add(edges(g, 0.1));
    }
  }
  const sunAndBack = [fixed.back, fixed.sun];

  // ------------------------------------------------------------ overlay
  const el = (h) => {
    const d = document.createElement('div');
    d.innerHTML = h;
    return d.firstElementChild;
  };
  const Wt = L.IX1 - L.IX0 + 8, Ht = L.TOP - L.YB + 8, Dt = L.LIP_Z + 3 - (L.REAR - 3);
  app.appendChild(el(`<div class="panel title"><h1>CUADRO VIVO · LA OLA</h1><p>${Wt.toFixed(0)} × ${Ht.toFixed(0)} × ${Dt.toFixed(0)} mm · TT · ciclo ${(60 / L.rpm).toFixed(0)} s</p></div>`));
  const NAMES = {ola: ['la ola', '#1d2f5e'], mar: ['el mar', '#2f6db3'], orilla: ['la orilla', '#8cc8e8']};
  const legend = el(`<div class="panel legend"><h2>LO QUE SE MUEVE</h2>${bodyOrder
    .map((bn) => `<div class="row"><i style="background:${NAMES[bn][1]}"></i><b>${NAMES[bn][0]}</b><div class="bar"><u data-b="${bn}"></u></div></div>`)
    .join('')}<div class="row" style="margin-top:12px"><i style="background:#efe6d2"></i><b>cielo y sol</b><span>quietos</span></div></div>`);
  app.appendChild(legend);
  const ticks = Object.fromEntries([...legend.querySelectorAll('u')].map((u) => [u.dataset.b, u]));
  app.appendChild(el(`<div class="panel info"><h2>MECANISMO</h2>
    <div><span>motor</span>TT · 5 V · 59 rpm</div><div><span>reducción</span>10:40 · 14:26 = ${L.ratio.toFixed(1)}:1</div>
    <div><span>eje de levas</span>${L.rpm.toFixed(1)} rpm</div>
    ${bodyOrder.map((bn) => `<div><span>${NAMES[bn][0]}</span>±${L.bodies[bn].amp.toFixed(1)}° · e ${L.bodies[bn].e.toFixed(2)}</div>`).join('')}
    <div><span>holgura mín.</span>0,23 mm</div><div><span>soportes</span>ninguno</div></div>`));
  const cap = el(`<div class="cap"></div>`);
  app.appendChild(cap);
  const chip = el(`<div class="chip on"><i></i>VISITA AUTOMÁTICA</div>`);
  app.appendChild(chip);
  const btnDefs = [
    ['1', 'FRENTE'],
    ['2', '3/4'],
    ['3', 'DETRÁS'],
    ['4', 'LEVAS'],
    ['M', 'MECANISMO'],
    ['E', 'DESPIECE'],
    ['R', 'RITMO ×4'],
    [' ', 'PAUSA'],
  ];
  const btnBar = el(`<div class="btns"></div>`);
  const btn = {};
  for (const [k, label] of btnDefs) {
    const b = document.createElement('button');
    b.innerHTML = `<small>${k === ' ' ? '␣' : k}</small>${label}`;
    btnBar.appendChild(b);
    btn[k] = b;
  }
  app.appendChild(btnBar);

  // ------------------------------------------------------------ state
  const VIEWS = {
    1: {pos: [0, 95, 330], tgt: [0, 88, 0]},
    2: {pos: [-230, 150, 260], tgt: [0, 70, -10]},
    3: {pos: [-190, 140, -290], tgt: [0, 50, -25]},
    4: {pos: [-200, 45, -210], tgt: [0, 15, -20]},
  };
  const S = {mech: 0, mechT: 0, explode: 0, exT: 0, fast: false, paused: false, t: 0, th: 0, auto: true, idle: 0};
  let camFrom = null, camTo = null, camT = 1;
  const goView = (v) => {
    camFrom = {pos: camera.position.clone(), tgt: controls.target.clone()};
    camTo = {pos: new THREE.Vector3(...VIEWS[v].pos), tgt: new THREE.Vector3(...VIEWS[v].tgt)};
    camT = 0;
    S.view = v;
  };
  camera.position.set(...VIEWS[1].pos);
  controls.target.set(...VIEWS[1].tgt);
  let caption = '';
  const say = (s) => {
    caption = s;
    cap.textContent = s;
    cap.style.opacity = s ? 1 : 0;
  };
  const act = (k, user = true) => {
    if (user) {
      S.auto = false;
      S.idle = 0;
      chip.classList.remove('on');
    }
    if ('1234'.includes(k) && k) goView(Number(k));
    if (k === '3' || k === '4') S.mechT = 1;
    if (k === 'M') S.mechT = S.mechT ? 0 : 1;
    if (k === 'E') S.exT = S.exT ? 0 : 1;
    if (k === 'R') S.fast = !S.fast;
    if (k === ' ') S.paused = !S.paused;
    btn.M.classList.toggle('on', !!S.mechT);
    btn.E.classList.toggle('on', !!S.exT);
    btn.R.classList.toggle('on', S.fast);
    btn[' '].classList.toggle('on', S.paused);
  };
  for (const [k] of btnDefs) btn[k].onclick = () => act(k);
  addEventListener('keydown', (e) => {
    const k = e.key === ' ' ? ' ' : e.key.toUpperCase();
    if (btn[k]) {
      e.preventDefault();
      act(k);
    }
  });
  for (const ev of ['pointerdown', 'wheel']) canvas.addEventListener(ev, () => act('', true), {passive: true});
  let tour0 = 0, lastStep = -1;
  chip.onclick = () => {
    S.auto = true;
    tour0 = S.t;
    lastStep = -1;
    chip.classList.add('on');
  };
  const TOUR = [
    [0, () => (goView(1), (S.mechT = 0), (S.exT = 0), (S.fast = false)), 'Nada está pegado encima: la ola misma respira'],
    [12, () => (S.fast = true), 'A ×4: la ola, el mar y la orilla, cada uno a su compás'],
    [22, () => (goView(2), (S.fast = false)), 'Cada lámina pivota en un pasador escondido bajo el marco'],
    [32, () => (goView(3), (S.mechT = 1)), 'Detrás del cielo: un eje de levas y el motor TT a 7,4:1'],
    [44, () => goView(4), 'Tres excéntricas en horquillas: empujan y tiran, sin muelles'],
    [56, () => (goView(2), (S.mechT = 0), (S.exT = 1)), 'Despiece: tres cuerpos, cuatro colores cada uno'],
    [66, () => (S.exT = 0), ''],
  ];
  const TOUR_LEN = 72;

  // ------------------------------------------------------------ loop
  const resize = () => {
    const w = innerWidth, h = innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  addEventListener('resize', resize);
  resize();
  const M4 = new THREE.Matrix4();
  let last = performance.now();
  const frame = (dt) => {
    if (!S.paused) S.t += dt;
    if (!S.auto) {
      S.idle += dt;
      if (S.idle > 25) chip.onclick();
    }
    if (S.auto) {
      const tt = (S.t - tour0) % TOUR_LEN;
      let step = -1;
      TOUR.forEach(([t0], i) => (tt >= t0 ? (step = i) : 0));
      if (step !== lastStep && step >= 0) {
        lastStep = step;
        TOUR[step][1]();
        say(TOUR[step][2]);
        act('', false);
      }
      if (tt < 0.05 && lastStep === TOUR.length - 1) lastStep = -1;
    } else if (caption) say('');
    if (camT < 1 && camFrom) {
      camT = Math.min(1, camT + dt / 2.4);
      const k = ease(camT);
      camera.position.lerpVectors(camFrom.pos, camTo.pos, k);
      controls.target.lerpVectors(camFrom.tgt, camTo.tgt, k);
    }
    // crank angle: the camshaft turns at L.rpm (x4 on request)
    if (!S.paused) S.th += dt * L.rpm * 6 * (S.fast ? 4 : 1);
    const t = S.th;
    S.mech += (S.mechT - S.mech) * Math.min(1, dt * 3);
    S.explode += (S.exT - S.explode) * Math.min(1, dt * 2.5);
    const ex = S.explode;
    bodyOrder.forEach((bn, i) => {
      const b = bodies[bn], a = bodyAngle(b, t);
      b.g.rotation.z = a * D2R;
      b.g.position.z = ex * (20 + 26 * i);
      const f = (a / b.amp + 1) / 2;
      ticks[bn].style.left = `${(f * 100).toFixed(1)}%`;
    });
    fixed.frame.position.z = ex * 80;
    fixed.rear.position.z = -ex * 40;
    for (const e of eccs) e.m.matrix.copy(onShaft(M4, e.b.drive, t + e.b.phase));
    shaft.matrix.copy(onShaft(M4, L.shaft_x, t));
    for (const g of gears) g.m.matrix.copy(atYZ(M4, g.x, g.y, g.z, g.phase + g.ratio * t));
    // mechanism view: the box goes to glass, the sky panel thins so the cams show through
    const k = S.mech;
    for (const m of glass) {
      const o = m === fixed.back ? 1 - 0.7 * k : m === fixed.frame ? 1 - 0.6 * k : 1 - 0.85 * k;
      m.material.opacity = o;
      m.material.depthWrite = o > 0.98;
      m.castShadow = o > 0.5;
    }
    fixed.sun.material.transparent = true;
    fixed.sun.material.opacity = 1 - 0.7 * k;
  };
  const loop = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    frame(dt);
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  window.__living = {S, act, frame, bodies, camera, controls, render: () => (controls.update(), renderer.render(scene, camera))};
}
