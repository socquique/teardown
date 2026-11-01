// The wave theater (sims/strandbeest-print/theater.py): the layered wave at the back of a box, three twisted rollers in
// front turning like a stage sea on the TT motor. Built on the relief page: the frame on a shelf, a raking light that
// sweeps across so the relief throws its shadows, the six colour bands pulled apart, and the print itself rising
// band by band as it would on the bed. Every outline comes from the same shapes the STLs are cut from (bands.json).
// Views 1-4, EXPLODE (E), LIGHT (L), PRINT (P), PAUSE (space), orbit and zoom; left alone it tours itself.
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import DATA from './bands.json';
import TH from './theater.json';

const D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const ease = (x) => {
  const u = clamp(x, 0, 1);
  return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
};
const W = DATA.W;
const FRAME = 124, WIN = 104, LIP = 2.5, PLATE_T = 7.2;

const CSS = `
html,body{margin:0;height:100%;background:#e7dfd2;overflow:hidden;font-family:Inter,system-ui,sans-serif;color:#2a2622}
#app,#app *{color:#2a2622}
.title p,.band span,.info span,.bands h2,.info h2{color:#6d6458!important}
.btns button.on,.btns button.on *{color:#f3ede2!important}
#gl{position:fixed;inset:0;width:100%;height:100%;display:block;touch-action:none}
.panel{position:fixed;background:rgba(246,241,232,.9);border:1px solid rgba(60,50,40,.18);padding:14px 16px;backdrop-filter:blur(6px)}
.title{left:22px;top:20px;padding:0;background:none;border:none}
.title h1{margin:0;font:700 13px/1 Inter,sans-serif;letter-spacing:3px}
.title p{margin:6px 0 0;font:500 10px/1.4 'JetBrains Mono',monospace;letter-spacing:1px;color:#6d6458}
.bands{left:22px;top:78px;width:200px}
.bands h2,.info h2{margin:0 0 10px;font:700 9px/1 Inter,sans-serif;letter-spacing:2px;color:#6d6458}
.band{display:flex;align-items:center;gap:9px;margin:6px 0;font:500 11px/1 'JetBrains Mono',monospace;transition:opacity .3s}
.band i{display:block;width:16px;height:16px;border:1px solid rgba(0,0,0,.25)}
.band b{font-weight:600;min-width:62px}
.band span{color:#7a7166}
.band.dim{opacity:.32}
.band.hot b{color:#c8372d}
.info{right:22px;top:20px;width:210px;font:500 11px/1.7 'JetBrains Mono',monospace}
.info div{display:flex;justify-content:space-between}
.info span{color:#7a7166}
.btns{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);display:flex;gap:6px}
.btns button{font:700 9px/1 Inter,sans-serif;letter-spacing:1.5px;padding:9px 12px;border:1px solid rgba(60,50,40,.25);background:rgba(246,241,232,.92);color:#2a2622;cursor:pointer}
.btns button.on{background:#2a2622;color:#f3ede2}
.btns button small{opacity:.55;margin-right:5px}
.chip{position:fixed;left:50%;top:20px;transform:translateX(-50%);font:700 9px/1 Inter,sans-serif;letter-spacing:1.6px;padding:7px 11px;border:1px solid rgba(60,50,40,.3);background:rgba(246,241,232,.9);cursor:pointer;display:flex;gap:7px;align-items:center}
.chip i{width:6px;height:6px;border-radius:50%;background:#c8372d}
.chip.on i{animation:b 1.2s steps(2) infinite}@keyframes b{50%{opacity:.15}}
.cap{position:fixed;left:50%;bottom:66px;transform:translateX(-50%);font:600 12px/1.3 'JetBrains Mono',monospace;letter-spacing:1px;color:#3b342c;background:rgba(246,241,232,.85);padding:7px 12px;white-space:nowrap;transition:opacity .4s}
@media (max-width:820px){.bands,.info{display:none}}
`;

export function runTheater() {
  const st = document.createElement('style');
  st.textContent = CSS;
  document.head.appendChild(st);
  const app = document.getElementById('app') || document.body;
  const canvas = document.createElement('canvas');
  canvas.id = 'gl';
  app.appendChild(canvas);

  // ------------------------------------------------------------ renderer and studio
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.NeutralToneMapping;   // keeps the filament colours true
  renderer.toneMappingExposure = 0.9;
  renderer.localClippingEnabled = true;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#e7dfd2');
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.35;
  const camera = new THREE.PerspectiveCamera(32, 1, 1, 5000);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.minDistance = 120;
  controls.maxDistance = 900;
  controls.target.set(0, 70, 0);

  // shelf and wall
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(2000, 1200), new THREE.MeshStandardMaterial({color: '#ece5d8', roughness: 0.95}));
  wall.position.set(0, 400, -40);
  wall.receiveShadow = true;
  scene.add(wall);
  const shelf = new THREE.Mesh(new THREE.BoxGeometry(700, 18, 200), new THREE.MeshStandardMaterial({color: '#b58a5c', roughness: 0.7}));
  shelf.position.set(0, -9, 40);
  shelf.receiveShadow = true;
  shelf.castShadow = true;
  scene.add(shelf);

  // lights: a soft fill and a raking key that can sweep
  scene.add(new THREE.HemisphereLight('#fffaf0', '#8a7a66', 0.35));
  const key = new THREE.DirectionalLight('#fff4e2', 2.0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, {left: -110, right: 110, top: 160, bottom: -30, near: 10, far: 900});
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.25;
  scene.add(key, key.target);
  key.target.position.set(0, 70, 0);

  // ------------------------------------------------------------ the theater (mm: x right, y up, z toward the viewer)
  const piece = new THREE.Group();
  piece.position.set(-TH.IW / 2, 0, -20);
  scene.add(piece);
  const art = new THREE.Group();
  art.position.set(0, TH.BASE + 6, -2.0);
  piece.add(art);
  const clip = new THREE.Plane(new THREE.Vector3(0, 0, -1), 999);
  const bands = DATA.bands.map((b, i) => {
    const shapes = b.shapes.map(({outer, holes}) => {
      const s = new THREE.Shape(outer.map(([x, y]) => new THREE.Vector2(x, y)));
      for (const h of holes) s.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
      return s;
    });
    const g = new THREE.ExtrudeGeometry(shapes, {depth: b.z1 - b.z0, bevelEnabled: true, bevelThickness: 0.12, bevelSize: 0.12, bevelSegments: 1, curveSegments: 4});
    g.computeVertexNormals();
    const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({color: b.color, roughness: 0.62, clippingPlanes: [clip]}));
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.position.z = b.z0;
    art.add(mesh);
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(g, 35), new THREE.LineBasicMaterial({color: '#1c1a17', transparent: true, opacity: 0.16})));
    return {mesh, ...b, i};
  });
  const black = new THREE.MeshStandardMaterial({color: '#151515', roughness: 0.6, transparent: true});
  const boxM = (x0, x1, y0, y1, z0, z1, mat = black) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, y1 - y0, z1 - z0), mat);
    m.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
    m.castShadow = m.receiveShadow = true;
    piece.add(m);
    return m;
  };
  const T = TH.T, H = TH.H, B = TH.BASE, IW = TH.IW, DEP = TH.DEPTH;
  const shell = [
    boxM(-T, IW + T, 0, B, -T, DEP + 4),
    boxM(-T, IW + T, B, B + H, -T - 0.01, -2.01),
    boxM(-T, 0, B, B + H, -T, DEP),
    boxM(IW, IW + T, B, B + H, -T, DEP),
    boxM(-T, IW + T, B + H, B + H + T, -T, DEP),
  ];
  // the art's mat: a cream panel round the pocket so the box reads as a stage
  boxM(0, IW, B, B + H, -2.0, -1.99, new THREE.MeshStandardMaterial({color: '#efe6d2', roughness: 0.9}));
  // rollers: the same twisted crest section as the STL, turned about x
  const prof = (r, lobes, amp, n = 160) => {
    const out = [];
    for (let i = 0; i < n; i++) {
      const t = (2 * Math.PI * i) / n;
      const k = ((t * lobes) / (2 * Math.PI)) % 1;
      const crest = Math.exp(-(((k - 0.35) / 0.17) ** 2)) + 0.45 * Math.exp(-(((k - 0.62) / 0.25) ** 2));
      const rr = r - amp + 2 * amp * crest;
      out.push([rr * Math.cos(t), rr * Math.sin(t)]);
    }
    return out;
  };
  const rollerGeo = (R) => {
    const P = prof(R.r, R.lobes, R.amp), n = P.length, NS = 120, L = TH.L_ROLL;
    const pos = [], idx = [];
    for (let j = 0; j <= NS; j++) {
      const f = j / NS, a = (R.twist * f * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
      for (const [u, v] of P) {
        const uu = u * c - v * s, vv = u * s + v * c;     // the section turned by the twist
        pos.push(0.6 + f * L, vv, -uu);                  // extrusion axis -> x, (u, v) -> (z = -u, y = v)
      }
    }
    for (let j = 0; j < NS; j++)
      for (let i = 0; i < n; i++) {
        const a = j * n + i, b = j * n + ((i + 1) % n), c = (j + 1) * n + i, d = (j + 1) * n + ((i + 1) % n);
        idx.push(a, c, b, b, c, d);
      }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  };
  const rollers = TH.rollers.map((R, i) => {
    const pivot = new THREE.Group();
    pivot.position.set(0, B + R.c[0], R.c[1]);
    piece.add(pivot);
    const mesh = new THREE.Mesh(rollerGeo(R), new THREE.MeshStandardMaterial({color: R.color, roughness: 0.55, side: THREE.DoubleSide}));
    mesh.castShadow = mesh.receiveShadow = true;
    pivot.add(mesh);
    const axle = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, IW + 2 * T + 2, 24).rotateZ(Math.PI / 2), new THREE.MeshStandardMaterial({color: R.color}));
    axle.position.x = IW / 2;
    pivot.add(axle);
    return {pivot, dir: i % 2 ? -1 : 1};
  });
  // side gears and the motor (outside the right wall)
  const gearDisc = (r, th, color) => new THREE.Mesh(new THREE.CylinderGeometry(r, r, th, 48).rotateZ(Math.PI / 2), new THREE.MeshStandardMaterial({color, roughness: 0.5}));
  const sideG = new THREE.Group();
  piece.add(sideG);
  const gear20 = TH.rollers.map((R, i) => {
    const g = gearDisc(10.4, TH.GT, '#c9a35a');
    g.position.set(TH.gx + TH.GT / 2, B + R.c[0], R.c[1]);
    sideG.add(g);
    return g;
  });
  const comp = new THREE.Group();
  comp.position.set(0, TH.cpd[0], TH.cpd[1]);
  const c10 = gearDisc(5.4, TH.GT, '#c9a35a'), c40 = gearDisc(20.4, TH.GT, '#b98a45');
  c10.position.x = TH.gx + TH.GT / 2;
  c40.position.x = TH.gx + TH.GT + 0.6 + TH.GT / 2;
  comp.add(c10, c40);
  sideG.add(comp);
  // spokes so the turning reads
  for (const g of [...gear20, c40]) {
    for (let k = 0; k < 3; k++) {
      const sp = new THREE.Mesh(new THREE.BoxGeometry(TH.GT + 0.4, 1.2, g === c40 ? 30 : 15), new THREE.MeshStandardMaterial({color: '#7a5a2a'}));
      sp.rotation.x = (k * Math.PI) / 3;
      g.add(sp);
    }
  }
  const motor = new THREE.Group();
  const [my, mz] = TH.mot;
  const mb = boxM(TH.MB + 3, TH.MB + 3 + 18.8, my - 11.2, my + 37.2, mz - 11.2, mz + 11.2, new THREE.MeshStandardMaterial({color: '#e7c234', roughness: 0.5}));
  const can = new THREE.Mesh(new THREE.CylinderGeometry(10, 10, 20, 32), new THREE.MeshStandardMaterial({color: '#b9bdc3', metalness: 0.8, roughness: 0.3}));
  can.position.set(TH.MB + 3 + 9.4, my + 37.2 + 10, mz);
  piece.add(can);
  boxM(TH.MB, TH.MB + 3, 0, my + 42, mz - 15, mz + 15);
  boxM(TH.MB + 3 + 18.8 + 0.2, TH.MB + 3 + 18.8 + 3.2, 0, my + 42, mz - 15, mz + 15);
  const pin10 = gearDisc(5.4, TH.GT, '#d0592a');
  pin10.position.set(TH.gx + TH.GT + 0.6 + TH.GT / 2, my, mz);
  sideG.add(pin10);
  const frameMat = black, frameFront = shell[4], frameSide = shell[2], PLATE_T_ = 7.2;

  // ------------------------------------------------------------ overlay
  const el = (h) => {
    const d = document.createElement('div');
    d.innerHTML = h;
    return d.firstElementChild;
  };
  app.appendChild(el(`<div class="panel title"><h1>TEATRO DE OLAS</h1><p>${(TH.IW + 2 * TH.T).toFixed(0)} × ${(TH.BASE + TH.H + TH.T).toFixed(0)} mm · motor TT · ${TH.rpm.toFixed(1)} rpm</p></div>`));
  const bandPanel = el(`<div class="panel bands"><h2>COLOR = ALTURA</h2>${DATA.bands
    .map((b, i) => `<div class="band" data-i="${i}"><i style="background:${b.color}"></i><b>${b.name}</b><span>${b.z0.toFixed(1)}–${b.z1.toFixed(1)} mm</span></div>`)
    .reverse()
    .join('')}</div>`);
  app.appendChild(bandPanel);
  const rows = [...bandPanel.querySelectorAll('.band')];
  app.appendChild(el(`<div class="panel info"><h2>MECANISMO</h2>
    <div><span>motor</span>TT · 5 V · 59 rpm</div><div><span>reducción</span>10:40 · 10:20 = 8:1</div><div><span>rodillos</span>${TH.rpm.toFixed(1)} rpm, alternos</div>
    <div><span>ola atrás</span>6 colores fijos</div><div><span>holgura mín.</span>0,33 mm</div><div><span>soportes</span>ninguno</div></div>`));
  const cap = el(`<div class="cap"></div>`);
  app.appendChild(cap);
  const chip = el(`<div class="chip on"><i></i>VISITA AUTOMÁTICA</div>`);
  app.appendChild(chip);
  const btnDefs = [
    ['1', 'FRENTE'],
    ['2', '3/4'],
    ['3', 'MOTOR'],
    ['4', 'MAR'],
    ['E', 'DESPIECE'],
    ['L', 'LUZ'],
    ['P', 'IMPRIMIR'],
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
    1: {pos: [0, 72, 360], tgt: [0, 66, 0]},
    2: {pos: [-200, 120, 280], tgt: [0, 60, 0]},
    3: {pos: [310, 90, 170], tgt: [40, 50, 0]},
    4: {pos: [-10, 40, 140], tgt: [-5, 40, 20]},
  };
  const S = {view: 1, explode: 0, exT: 0, light: true, print: 0, printT: -1, paused: false, t: 0, auto: true, idle: 0, lightPh: 0, th: 0, rpm: TH.rpm};
  let camFrom = null, camTo = null, camT = 1;
  const goView = (v) => {
    S.view = v;
    camFrom = {pos: camera.position.clone(), tgt: controls.target.clone()};
    camTo = {pos: new THREE.Vector3(...VIEWS[v].pos), tgt: new THREE.Vector3(...VIEWS[v].tgt)};
    camT = 0;
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
    if ('1234'.includes(k)) goView(Number(k));
    if (k === 'E') S.exT = S.exT ? 0 : 1;
    if (k === 'L') S.light = !S.light;
    if (k === 'P') {
      S.printT = 0;
      S.exT = 0;
    }
    if (k === ' ') S.paused = !S.paused;
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
  chip.onclick = () => {
    S.auto = true;
    tour0 = S.t;
    chip.classList.add('on');
  };
  // the tour: [time, action, caption]
  const TOUR = [
    [0, () => (goView(1), (S.exT = 0)), 'Tres rodillos helicoidales: el mar avanza sin fin'],
    [9, () => goView(4), 'Rodillos vecinos giran al revés: las crestas se cruzan'],
    [17, () => goView(3), 'El motor TT del kit, 8:1 con engranajes impresos'],
    [25, () => goView(2), 'Detrás, la gran ola en relieve, quieta'],
    [33, () => (S.exT = 1), 'Despiece de la ola: seis colores, seis alturas'],
    [40, () => (S.exT = 0), ''],
  ];
  const TOUR_LEN = 46;
  let tour0 = 0, lastStep = -1;

  // ------------------------------------------------------------ loop
  const resize = () => {
    const w = innerWidth, h = innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  addEventListener('resize', resize);
  resize();
  let last = performance.now();
  const loop = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!S.paused) S.t += dt;
    if (!S.auto) {
      S.idle += dt;
      if (S.idle > 20) {
        S.auto = true;
        tour0 = S.t;
        lastStep = -1;
        chip.classList.add('on');
      }
    }
    if (S.auto) {
      const tt = (S.t - tour0) % TOUR_LEN;
      let step = -1;
      TOUR.forEach(([t0], i) => (tt >= t0 ? (step = i) : 0));
      if (step !== lastStep && step >= 0) {
        lastStep = step;
        TOUR[step][1]();
        say(TOUR[step][2]);
      }
      if (tt < 0.05 && lastStep === TOUR.length - 1) lastStep = -1;
    } else if (caption) say('');
    // camera move
    if (camT < 1 && camFrom) {
      camT = Math.min(1, camT + dt / 2.2);
      const k = ease(camT);
      camera.position.lerpVectors(camFrom.pos, camTo.pos, k);
      controls.target.lerpVectors(camFrom.tgt, camTo.tgt, k);
    }
    // explode: bands pull apart toward the viewer, the frame drops back and fades
    S.explode += (S.exT - S.explode) * Math.min(1, dt * 2.5);
    const ex = S.explode;
    bands.forEach((b) => (b.mesh.position.z = b.z0 + ex * b.i * 7));
    for (const r of rollers) r.pivot.visible = ex < 0.5;
    // the sea: crank angle from the motor's speed, rollers alternate, gears follow
    if (!S.paused) S.th += dt * S.rpm * 6 * D2R;
    rollers.forEach((r) => (r.pivot.rotation.x = r.dir * S.th));
    gear20.forEach((g, i) => (g.rotation.x = (i % 2 ? -1 : 1) * S.th));
    comp.rotation.x = -S.th * 2;
    pin10.rotation.x = S.th * 8;
    // print: a plane rises through the plate, band by band
    let printZ = 999;
    if (S.printT >= 0) {
      if (!S.paused) S.printT += dt;
      const p = S.printT / 10;
      printZ = p < 1 ? p * PLATE_T : 999;
      if (S.printT > 11) S.printT = -1;
    }
    art.updateMatrixWorld(true);
    clip.set(new THREE.Vector3(0, 0, -1), printZ).applyMatrix4(art.matrixWorld);   // the plane lives in the plate's frame
    const cur = printZ < 999 ? DATA.bands.findIndex((b) => printZ >= b.z0 && printZ < b.z1) : -1;
    rows.forEach((r) => {
      const i = Number(r.dataset.i);
      r.classList.toggle('hot', i === cur);
      r.classList.toggle('dim', cur >= 0 && i > cur);
    });
    // light: a raking key that sweeps slowly from side to side
    if (!S.paused) S.lightPh += dt * (S.light ? 0.35 : 0);
    const a = Math.sin(S.lightPh) * 62 * D2R;
    const lp = new THREE.Vector3(Math.sin(a) * 260, 120 + Math.cos(S.lightPh * 0.7) * 30, Math.cos(a) * 140 + 60);
    key.position.copy(lp);
    for (const [k, on] of [['1', S.view === 1], ['2', S.view === 2], ['3', S.view === 3], ['4', S.view === 4], ['E', S.exT > 0], ['L', S.light], ['P', S.printT >= 0], [' ', S.paused]]) btn[k].classList.toggle('on', on);
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  window.__theater = {S, act};
}
