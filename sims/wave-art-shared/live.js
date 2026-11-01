// The layered-relief wave (sims/strandbeest-print/wave_art.py) as a page: the frame on a shelf, a raking light that
// sweeps across so the relief throws its shadows, the six colour bands pulled apart, and the print itself rising
// band by band as it would on the bed. Every outline comes from the same shapes the STLs are cut from (bands.json).
// Views 1-4, EXPLODE (E), LIGHT (L), PRINT (P), PAUSE (space), orbit and zoom; left alone it tours itself.
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import DATA from './bands.json';

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

export function runLive() {
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

  // ------------------------------------------------------------ the piece
  // art plate in its own frame: x right, y up, z toward the viewer; the frame stands on the shelf, leaning slightly
  const piece = new THREE.Group();
  piece.position.set(0, 0, 10);
  piece.rotation.x = -4 * D2R;
  scene.add(piece);
  const art = new THREE.Group();
  art.position.set(-W / 2, (FRAME - W) / 2, 0);
  piece.add(art);
  const clip = new THREE.Plane(new THREE.Vector3(0, 0, -1), 999);
  const bands = DATA.bands.map((b, i) => {
    const shapes = b.shapes.map(({outer, holes}) => {
      const s = new THREE.Shape(outer.map(([x, y]) => new THREE.Vector2(x, y)));
      for (const h of holes) s.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
      return s;
    });
    const h = b.z1 - b.z0;
    const g = new THREE.ExtrudeGeometry(shapes, {depth: h, bevelEnabled: true, bevelThickness: 0.12, bevelSize: 0.12, bevelSegments: 1, curveSegments: 4});
    g.computeVertexNormals();
    const m = new THREE.MeshStandardMaterial({color: b.color, roughness: 0.62, metalness: 0, clippingPlanes: [clip], clipShadows: true});
    const mesh = new THREE.Mesh(g, m);
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.position.z = b.z0;
    art.add(mesh);
    // a fine ink edge so pale bands read against each other
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(g, 35), new THREE.LineBasicMaterial({color: '#1c1a17', transparent: true, opacity: 0.18, clippingPlanes: [clip]}));
    mesh.add(e);
    return {mesh, edges: e, ...b, i};
  });
  // frame: 124 square, a 2.5 mm lip in front of the plate, matte black
  const frameShape = new THREE.Shape([[-62, 0], [62, 0], [62, FRAME], [-62, FRAME]].map(([x, y]) => new THREE.Vector2(x, y)));
  frameShape.holes.push(new THREE.Path([[-WIN / 2, (FRAME - WIN) / 2], [WIN / 2, (FRAME - WIN) / 2], [WIN / 2, (FRAME + WIN) / 2], [-WIN / 2, (FRAME + WIN) / 2]].map(([x, y]) => new THREE.Vector2(x, y))));
  const frameMat = new THREE.MeshStandardMaterial({color: '#121212', roughness: 0.6, transparent: true});
  const frameFront = new THREE.Mesh(new THREE.ExtrudeGeometry(frameShape, {depth: LIP, bevelEnabled: true, bevelThickness: 0.6, bevelSize: 0.6, bevelSegments: 2}), frameMat);
  frameFront.position.z = PLATE_T;
  const sideShape = new THREE.Shape([[-62, 0], [62, 0], [62, FRAME], [-62, FRAME]].map(([x, y]) => new THREE.Vector2(x, y)));
  sideShape.holes.push(new THREE.Path([[-(W / 2 + 0.25), (FRAME - W) / 2 - 0.25], [W / 2 + 0.25, (FRAME - W) / 2 - 0.25], [W / 2 + 0.25, (FRAME + W) / 2 + 0.25], [-(W / 2 + 0.25), (FRAME + W) / 2 + 0.25]].map(([x, y]) => new THREE.Vector2(x, y))));
  const frameSide = new THREE.Mesh(new THREE.ExtrudeGeometry(sideShape, {depth: PLATE_T + 2, bevelEnabled: false}), frameMat);
  frameSide.position.z = -2;
  const back = new THREE.Mesh(new THREE.BoxGeometry(W + 0.2, W + 0.2, 2), new THREE.MeshStandardMaterial({color: '#202020', roughness: 0.7}));
  back.position.set(0, FRAME / 2, -1);
  for (const m of [frameFront, frameSide, back]) {
    m.castShadow = m.receiveShadow = true;
    piece.add(m);
  }

  // ------------------------------------------------------------ overlay
  const el = (h) => {
    const d = document.createElement('div');
    d.innerHTML = h;
    return d.firstElementChild;
  };
  app.appendChild(el(`<div class="panel title"><h1>OLA · CUADRO EN RELIEVE</h1><p>124 × 124 mm · 6 colores · 7,2 mm de relieve</p></div>`));
  const bandPanel = el(`<div class="panel bands"><h2>COLOR = ALTURA</h2>${DATA.bands
    .map((b, i) => `<div class="band" data-i="${i}"><i style="background:${b.color}"></i><b>${b.name}</b><span>${b.z0.toFixed(1)}–${b.z1.toFixed(1)} mm</span></div>`)
    .reverse()
    .join('')}</div>`);
  app.appendChild(bandPanel);
  const rows = [...bandPanel.querySelectorAll('.band')];
  app.appendChild(el(`<div class="panel info"><h2>IMPRESIÓN</h2>
    <div><span>impresora</span>cualquiera</div><div><span>cambios</span>5 de filamento</div><div><span>alturas</span>1,6·2,4·3,6·4,8·6,0</div>
    <div><span>soportes</span>ninguno</div><div><span>capa</span>0,2 mm</div><div><span>marco</span>negro, aparte</div></div>`));
  const cap = el(`<div class="cap"></div>`);
  app.appendChild(cap);
  const chip = el(`<div class="chip on"><i></i>VISITA AUTOMÁTICA</div>`);
  app.appendChild(chip);
  const btnDefs = [
    ['1', 'FRENTE'],
    ['2', '3/4'],
    ['3', 'RASANTE'],
    ['4', 'DETALLE'],
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
    1: {pos: [0, 70, 330], tgt: [0, 66, 0]},
    2: {pos: [-190, 120, 250], tgt: [0, 64, 0]},
    3: {pos: [210, 52, 120], tgt: [-10, 64, 0]},
    4: {pos: [-30, 120, 120], tgt: [-12, 92, 4]},
  };
  const S = {view: 1, explode: 0, exT: 0, light: true, print: 0, printT: -1, paused: false, t: 0, auto: true, idle: 0, lightPh: 0};
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
    [0, () => (goView(1), (S.exT = 0), (S.light = true)), 'Una ola rompiente, seis colores, todo PLA'],
    [7, () => goView(3), 'Con luz rasante, el relieve proyecta sus sombras'],
    [14, () => goView(2), 'Cada color es una franja de altura'],
    [18, () => (S.exT = 1), 'Despiece: crema, rojo, marino, azul, celeste, blanco'],
    [26, () => (S.exT = 0), ''],
    [28, () => (goView(1), (S.printT = 0)), 'Así sale de la impresora: cambio de filamento en cada franja'],
    [40, () => goView(4), 'La espuma: la última capa, en blanco'],
    [47, () => goView(2), ''],
  ];
  const TOUR_LEN = 53;
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
    bands.forEach((b) => (b.mesh.position.z = b.z0 + ex * b.i * 9));
    frameMat.opacity = 1 - ex * 0.85;
    frameFront.position.z = PLATE_T + ex * 60;
    frameFront.visible = frameMat.opacity > 0.05;
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
    frameFront.visible = frameFront.visible && printZ >= 999;
    frameSide.visible = printZ >= 999 || false;
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
  window.__wave = {S, act};
}
