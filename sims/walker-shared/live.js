// The printable walker as a page you drive: it walks on its TT motor over a pale floor, the feet that are down glow,
// and the panels read the same crank angle that poses the parts. Views 1-5, ISOLATE a module (I), EXPLODE (E),
// TRACE the feet (T), the motor's voltage on a slider, PAUSE (space), orbit and zoom. Left alone it tours itself;
// any input hands control over, 20 s of quiet hands it back.
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {GTAOPass} from 'three/addons/postprocessing/GTAOPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {buildWalker, bodyX, FEET, feetDown, FOOT_LOW, META, MM, MODULES, MOTOR_RPM, onGround, PAD, PHASE, RATIO, STRIDE} from './walker.js';

const W = 1600;
const H = 900;
const IDLE = 20;
const D2R = Math.PI / 180;
const P = {bg: '#e9e2d6', floor: '#d6c5a6', leg: '#f6f2ea', tri: '#efe9dd', frame: '#3f444c', pin: '#c8382c', gear: '#2f3238', accent: '#e2672a', accent2: '#c8382c', foot: '#6f6a64', ink: '#3a342b', soft: '#8a7f6c'};
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const ease = (x) => {
  const u = clamp(x, 0, 1);
  return u * u * (3 - 2 * u);
};

const CSS = `
html,body{margin:0;background:${P.bg};overflow:hidden}
#app{position:absolute!important;inset:auto!important;left:0;top:0;width:${W}px;height:${H}px;transform-origin:0 0;font-family:Inter,sans-serif;color:${P.ink}}
#gl{position:absolute;inset:0;width:${W}px;height:${H}px;touch-action:none;cursor:grab}
.hd{position:absolute;left:48px;top:36px}
.hd b{display:block;font:700 13px Inter;letter-spacing:3px}
.hd span{display:block;margin-top:6px;font:600 11px 'JetBrains Mono',monospace;letter-spacing:1px;color:${P.soft}}
.panel{position:absolute;background:rgba(246,242,234,.86);border:1px solid rgba(110,98,78,.35);padding:14px 16px;font:600 11px 'JetBrains Mono',monospace;letter-spacing:.6px}
.panel h4{margin:0 0 10px;font:700 9.5px Inter;letter-spacing:2px;color:${P.soft}}
.big{font:700 44px 'JetBrains Mono',monospace;letter-spacing:-1px;line-height:1}
.big small{font-size:15px;color:${P.soft};margin-left:4px}
.row{display:flex;justify-content:space-between;gap:18px;margin-top:5px}
.row i{font-style:normal;color:${P.soft}}
.acc{color:${P.accent}}
.btns{position:absolute;left:50%;bottom:34px;transform:translateX(-50%);display:flex;gap:8px}
.vb{height:30px;padding:0 13px;display:flex;align-items:center;gap:7px;border:1px solid rgba(110,98,78,.5);background:rgba(246,242,234,.92);font:700 9.5px Inter;letter-spacing:1.6px;cursor:pointer;user-select:none}
.vb kbd{font:600 9px 'JetBrains Mono';color:${P.soft}}
.vb.on{background:${P.ink};color:#f6f2ea;border-color:${P.ink}}
.vb.on kbd{color:#cbbfa9}
.tour{position:absolute;left:50%;top:36px;transform:translateX(-50%);display:flex;align-items:center;gap:7px;height:22px;padding:0 11px;border:1px solid rgba(110,98,78,.5);background:rgba(246,242,234,.92);font:700 8.5px Inter;letter-spacing:1.4px;cursor:pointer}
.tour i{width:6px;height:6px;border-radius:50%;background:${P.accent}}
.tour.on i{animation:bl 1.2s steps(2) infinite}@keyframes bl{50%{opacity:.15}}
.sl{position:absolute;right:48px;bottom:34px;width:300px}
.sl input{width:100%;accent-color:${P.accent}}
.note{position:absolute;left:48px;bottom:84px;font:600 10px 'JetBrains Mono';color:${P.soft};letter-spacing:.5px}
`;

export function runLive() {
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);
  const app = document.getElementById('app');
  const canvas = document.createElement('canvas');
  canvas.id = 'gl';
  app.appendChild(canvas);

  // ------------------------------------------------------------ stage
  const renderer = new THREE.WebGLRenderer({canvas, antialias: false, powerPreference: 'high-performance'});
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(P.bg);
  scene.fog = new THREE.Fog(P.bg, 1.6, 4.2);
  const pm = new THREE.PMREMGenerator(renderer);
  scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  const camera = new THREE.PerspectiveCamera(26, W / H, 0.01, 30);
  const hemi = new THREE.HemisphereLight('#fbf7f1', '#cdb48c', 0.9);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight('#fff6ea', 2.1);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = sun.shadow.camera.bottom = -0.35;
  sun.shadow.camera.right = sun.shadow.camera.top = 0.35;
  sun.shadow.camera.near = 0.1;
  sun.shadow.camera.far = 3;
  sun.shadow.bias = -0.0004;
  sun.shadow.radius = 4;
  scene.add(sun, sun.target);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({color: P.floor, roughness: 0.95}));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);
  // marks on the floor every 5 cm so the walking reads
  const marks = new THREE.Group();
  for (let i = -60; i <= 60; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.0012, i % 4 ? 0.025 : 0.06), new THREE.MeshBasicMaterial({color: '#c4ae89'}));
    m.rotation.x = -Math.PI / 2;
    m.position.set(i * 0.05, 0.0004, 0.16);
    marks.add(m);
  }
  scene.add(marks);

  const walker = buildWalker(P);
  const body = new THREE.Group();
  body.scale.setScalar(MM);
  body.add(walker.root);
  walker.root.position.z = -walker.zMid; // axle centred on the scene's z = 0
  scene.add(body);
  const AXLE_H = (-FOOT_LOW + PAD) * MM; // axle height above the floor

  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(4, 4, {type: THREE.HalfFloatType, samples: 4}));
  composer.addPass(new RenderPass(scene, camera));
  const gtao = new GTAOPass(scene, camera, 4, 4);
  gtao.blendIntensity = 0.7;
  gtao.updateGtaoMaterial({radius: 0.03, distanceExponent: 1.4, thickness: 0.3, scale: 1, samples: 12, screenSpaceRadius: false});
  composer.addPass(gtao);
  composer.addPass(new OutputPass());

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 0.18;
  controls.maxDistance = 2.2;
  controls.maxPolarAngle = Math.PI * 0.49;

  // ------------------------------------------------------------ views (camera offset from the body, target height)
  const VIEWS = {
    1: {name: '3/4', off: [0.42, 0.26, 0.58], ty: 0.09},
    2: {name: 'SIDE', off: [0.0, 0.1, 0.78], ty: 0.08},
    3: {name: 'FRONT', off: [0.74, 0.12, 0.0], ty: 0.08},
    4: {name: 'TOP', off: [0.02, 0.8, 0.12], ty: 0.05},
    5: {name: 'DRIVE', off: [0.1, 0.16, 0.26], ty: 0.15, tz: 0.0},
  };

  // ------------------------------------------------------------ overlay
  const el = (html) => {
    const d = document.createElement('div');
    d.innerHTML = html;
    app.appendChild(d.firstElementChild);
    return app.lastElementChild;
  };
  el(`<div class="hd"><b>STRANDBEEST · PRINT KIT</b><span>12 LEGS · TT MOTOR LA001 · NO SCREWS · FROM jansen.js</span></div>`);
  const tour = el(`<div class="tour on"><i></i>AUTO TOUR</div>`);
  const left = el(`<div class="panel" style="left:48px;top:96px;width:236px">
    <h4>FEET ON THE GROUND</h4>
    <div class="big"><span id="fd">0</span><small>/ 12</small></div>
    <canvas id="ch" width="408" height="250" style="width:204px;height:125px;margin-top:12px"></canvas>
    <div class="row"><i>never fewer than</i><span id="fmin">3</span></div>
  </div>`);
  const right = el(`<div class="panel" style="right:48px;top:96px;width:236px">
    <h4>DRIVE</h4>
    <div class="row"><i>motor</i><span><span id="mv">5.0</span> V · <span id="mr">59</span> rpm</span></div>
    <div class="row"><i>gears</i><span>12 : 48 → 4 : 1</span></div>
    <div class="row"><i>crankshaft</i><span><span id="cr">14.8</span> rpm</span></div>
    <div class="row"><i>crank angle</i><span id="ca">0°</span></div>
    <div class="row"><i>stride / turn</i><span>${Math.abs(STRIDE).toFixed(0)} mm</span></div>
    <div class="row"><i>speed</i><span class="acc"><span id="sp">0</span> mm/s</span></div>
    <h4 style="margin-top:16px">PRINT</h4>
    <div class="row"><i>legs</i><span>6 modules × 2</span></div>
    <div class="row"><i>printed parts</i><span id="np"></span></div>
    <div class="row"><i>screws</i><span>0 · snap pins</span></div>
    <div class="row"><i>plates</i><span>5 × 250 mm</span></div>
    <div class="row"><i>module</i><span>${META.NL} layers × ${META.PITCH} mm</span></div>
  </div>`);
  const nParts = Object.values(META.counts).reduce((a, b) => a + b, 0);
  right.querySelector('#np').textContent = nParts;
  const btnDefs = [
    ['1', '3/4'],
    ['2', 'SIDE'],
    ['3', 'FRONT'],
    ['4', 'TOP'],
    ['5', 'DRIVE'],
    ['I', 'ISOLATE'],
    ['E', 'EXPLODE'],
    ['T', 'TRACE FEET'],
    ['␣', 'PAUSE'],
  ];
  const bar = el(`<div class="btns"></div>`);
  const btn = {};
  for (const [k, label] of btnDefs) {
    const b = document.createElement('div');
    b.className = 'vb';
    b.innerHTML = `<kbd>${k}</kbd>${label}`;
    bar.appendChild(b);
    btn[k] = b;
  }
  const sl = el(`<div class="sl panel" style="padding:10px 14px"><h4 style="margin-bottom:4px">MOTOR VOLTAGE</h4><input type="range" min="0" max="6" step="0.1" value="5"></div>`);
  const volt = sl.querySelector('input');
  el(`<div class="note">orange = foot on the ground · drag to orbit · wheel to zoom</div>`);

  // contact chart: 12 rows (feet) across one crank turn, stance in ink, the current angle as a line
  const ch = left.querySelector('#ch');
  const cg = ch.getContext('2d');
  const chartBase = document.createElement('canvas');
  chartBase.width = ch.width;
  chartBase.height = ch.height;
  {
    const g = chartBase.getContext('2d');
    const rowH = ch.height / FEET.length;
    let fmin = 99;
    for (let n = 0; n < 360; n++) fmin = Math.min(fmin, feetDown(n * D2R));
    left.querySelector('#fmin').textContent = fmin;
    FEET.forEach((f, i) => {
      g.fillStyle = i % 2 ? 'rgba(110,98,78,.07)' : 'rgba(110,98,78,.13)';
      g.fillRect(0, i * rowH, ch.width, rowH - 2);
      g.fillStyle = f.side === 'L' ? P.ink : '#7b7366';
      for (let n = 0; n < 360; n++) if (onGround(i, n * D2R)) g.fillRect((n / 360) * ch.width, i * rowH + 3, ch.width / 360 + 0.6, rowH - 8);
    });
  }

  // ------------------------------------------------------------ state, input, tour
  const st = {th: 0, view: 1, iso: -1, explode: 0, exT: 0, trace: false, paused: false, volt: 5, auto: true, last: 0};
  let camT = 1;
  let camFrom = null;
  const setView = (v) => {
    st.view = v;
    camFrom = {pos: camera.position.clone(), tgt: controls.target.clone()};
    camT = 0;
  };
  const touch = () => {
    st.auto = false;
    st.last = performance.now() / 1000;
    tour.classList.remove('on');
  };
  const act = (k, user = true) => {
    if (user) touch();
    if ('12345'.includes(k)) setView(Number(k));
    if (k === 'I') {
      st.iso = st.iso >= 0 ? -1 : MODULES[MODULES.length - 1]; // the module nearest the side camera
      if (st.iso >= 0 && st.view !== 2) setView(2);
    }
    if (k === 'E') st.exT = st.exT ? 0 : 1;
    if (k === 'T') st.trace = !st.trace;
    if (k === '␣') st.paused = !st.paused;
  };
  for (const [k] of btnDefs) btn[k].onclick = () => act(k);
  addEventListener('keydown', (e) => {
    const k = e.key === ' ' ? '␣' : e.key.toUpperCase();
    if (btn[k]) {
      e.preventDefault();
      act(k);
    }
  });
  canvas.addEventListener('pointerdown', touch);
  canvas.addEventListener('wheel', touch, {passive: true});
  volt.oninput = () => {
    touch();
    st.volt = Number(volt.value);
  };
  tour.onclick = () => {
    st.auto = true;
    tour.classList.add('on');
  };
  // the tour: a script of operator moves, looped
  const TOUR = [
    [0, () => act('1', false)],
    [7, () => act('2', false)],
    [12, () => act('T', false)],
    [18, () => act('I', false)],
    [26, () => act('I', false)],
    [26.1, () => act('T', false)],
    [27, () => act('5', false)],
    [34, () => act('E', false)],
    [37, () => act('3', false)],
    [43, () => act('E', false)],
    [45, () => act('4', false)],
    [51, () => act('1', false)],
  ];
  const TOUR_LEN = 58;
  let tourT = 0;
  let tourI = 0;

  // ------------------------------------------------------------ resize
  const fit = () => {
    const k = Math.min(innerWidth / W, innerHeight / H);
    app.style.transform = `scale(${k})`;
    app.style.left = `${(innerWidth - W * k) / 2}px`;
    app.style.top = `${(innerHeight - H * k) / 2}px`;
    const pr = Math.min(devicePixelRatio || 1, 2) * k;
    renderer.setPixelRatio(pr);
    renderer.setSize(W, H, false);
    canvas.style.width = `${W}px`;
    canvas.style.height = `${H}px`;
    composer.setPixelRatio(pr);
    composer.setSize(W, H);
  };
  addEventListener('resize', fit);
  fit();

  // ------------------------------------------------------------ loop
  let prev = performance.now() / 1000;
  let fps = 60;
  const camGoal = () => {
    const v = VIEWS[st.view];
    const bx = body.position.x;
    return {pos: new THREE.Vector3(bx + v.off[0], v.off[1] + (v.ty ?? 0.08), v.off[2]), tgt: new THREE.Vector3(bx, v.ty ?? 0.08, v.tz ?? 0)};
  };
  {
    const g = camGoal();
    camera.position.copy(g.pos);
    controls.target.copy(g.tgt);
  }
  const loop = () => {
    const now = performance.now() / 1000;
    const rdt = now - prev;
    const dt = Math.min(0.05, rdt);
    prev = now;
    fps = fps * 0.95 + (1 / Math.max(dt, 1e-3)) * 0.05;
    if (!st.auto && now - st.last > IDLE) {
      st.auto = true;
      tour.classList.add('on');
      st.volt = 5;
      volt.value = 5;
    }
    if (st.auto) {
      tourT += rdt;
      while (tourI < TOUR.length && tourT >= TOUR[tourI][0]) TOUR[tourI++][1]();
      if (tourT > TOUR_LEN) {
        tourT = 0;
        tourI = 0;
        st.iso = -1;
        st.exT = 0;
        st.trace = false;
      }
    }
    const motorRpm = MOTOR_RPM * (st.volt / 5);
    const crankRpm = motorRpm / RATIO;
    if (!st.paused) st.th += ((crankRpm * 2 * Math.PI) / 60) * dt;
    st.explode += (st.exT - st.explode) * (1 - Math.exp(-dt * 4));
    // body: walks along -x/+x by the stance feet; stands on the floor
    const bx = bodyX(st.th) * MM;
    body.position.set(bx, AXLE_H, 0);
    walker.update(st.th, {iso: st.iso, explode: st.explode, trace: st.trace, hot: true});
    marks.position.x = 0;
    sun.position.set(bx + 0.6, 1.1, 0.7);
    sun.target.position.set(bx, 0, 0);
    // camera follows the body; eases between views unless the visitor is orbiting
    const g = camGoal();
    if (camT < 1) {
      camT = Math.min(1, camT + rdt / 1.4);
      const k = ease(camT);
      camera.position.lerpVectors(camFrom.pos, g.pos, k);
      controls.target.lerpVectors(camFrom.tgt, g.tgt, k);
    } else {
      const d = new THREE.Vector3(bx - controls.target.x, 0, 0);
      camera.position.add(d);
      controls.target.add(d);
    }
    controls.update();
    // panels
    const deg = ((st.th / D2R) % 360 + 360) % 360;
    left.querySelector('#fd').textContent = feetDown(st.th);
    right.querySelector('#mv').textContent = st.volt.toFixed(1);
    right.querySelector('#mr').textContent = motorRpm.toFixed(0);
    right.querySelector('#cr').textContent = crankRpm.toFixed(1);
    right.querySelector('#ca').textContent = `${deg.toFixed(0)}°`;
    right.querySelector('#sp').textContent = ((Math.abs(STRIDE) * crankRpm) / 60).toFixed(0);
    cg.clearRect(0, 0, ch.width, ch.height);
    cg.drawImage(chartBase, 0, 0);
    const rowH = ch.height / FEET.length;
    FEET.forEach((f, i) => {
      if (!onGround(i, st.th)) return;
      cg.fillStyle = P.accent;
      cg.fillRect((deg / 360) * ch.width - 3, i * rowH + 2, 6, rowH - 6);
    });
    cg.fillStyle = P.accent;
    cg.fillRect((deg / 360) * ch.width - 1, 0, 2, ch.height);
    for (const [k, on] of [['1', st.view === 1], ['2', st.view === 2], ['3', st.view === 3], ['4', st.view === 4], ['5', st.view === 5], ['I', st.iso >= 0], ['E', st.exT > 0], ['T', st.trace], ['␣', st.paused]]) btn[k].classList.toggle('on', on);
    gtao.enabled = fps > 40 || st.paused;
    composer.render();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  window.__walker = {st, act};
}
