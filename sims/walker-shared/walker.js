// The printable 12-leg walker, built from the real outlines of its printed parts (parts.json, sliced from the STLs
// that walker.py writes) and posed by jansen.js: every leg part, crank web, frame, gear and pin sits where the print
// kit puts it. One input, the crank angle, poses everything; the body moves by the feet that are on the ground.
// Units: the kit's millimetres, scaled to metres for the scene.
import * as THREE from 'three';
import {HOLY, solveLeg} from '../strandbeest-shared/jansen.js';
import DATA from './parts.json';

export const META = DATA.meta;
export const MM = 0.001;
const {S, T, GAP, PITCH, NL, ZF, CD} = META;
const D2R = Math.PI / 180;
export const SECTIONS = META.sections;
// crank phase of each module along the axle: 120° apart on each side, 60° between the sides
export const PHASE = {0: 0, 1: 120, 2: 240, 5: 60, 6: 180, 7: 300};
export const MODULES = Object.keys(PHASE).map(Number);
export const PAD = META.R * 1.3; // the foot's rounded end
const JOINTS_OF = {'link-j': ['A', 'B'], 'link-k': ['A', 'C'], 'link-c': ['P', 'C'], 'link-f': ['D', 'E'], 'tri-upper': ['P', 'B', 'D'], 'tri-foot': ['C', 'E', 'F'], web: ['O', 'A']};

const sc = (J) => {
  const o = {};
  for (const k in J) o[k] = [J[k][0] * S, J[k][1] * S];
  return o;
};
export const J0 = sc(solveLeg(0));
export const legL = (th) => sc(solveLeg(th));
// the mirrored leg on the same crank pin, in the L leg's own frame before the turn: L solved at (pi - th)
export const legMraw = (th) => sc(solveLeg(Math.PI - th));

// ------------------------------------------------------------ gait: feet, contact, body motion (tabulated once)
const N = 720;
const footAt = (th, mirror) => {
  if (!mirror) return legL(th).F;
  const f = legMraw(th).F;
  return [-f[0], f[1]];
};
export const FEET = [];
for (const m of MODULES) for (const mirror of [false, true]) FEET.push({m, mirror, side: m < 4 ? 'L' : 'R'});
let ymin = Infinity;
for (let n = 0; n < N; n++) ymin = Math.min(ymin, legL((n / N) * 2 * Math.PI).F[1]);
export const FOOT_LOW = ymin;
export const CONTACT_TOL = 1.0 * S; // a foot within 1 mm of its lowest is on the ground
export const footOf = (i, th) => footAt(th + PHASE[FEET[i].m] * D2R, FEET[i].mirror);
export const onGround = (i, th) => footOf(i, th)[1] < FOOT_LOW + CONTACT_TOL;
// body x: the feet on the ground do not slide, so the body moves by minus the stance feet's motion
const BODY = new Float64Array(N + 1);
{
  let x = 0;
  for (let n = 0; n < N; n++) {
    const a = (n / N) * 2 * Math.PI;
    const b = ((n + 1) / N) * 2 * Math.PI;
    let sum = 0;
    let k = 0;
    for (let i = 0; i < FEET.length; i++) {
      if (!onGround(i, a)) continue;
      sum += footOf(i, b)[0] - footOf(i, a)[0];
      k++;
    }
    x -= k ? sum / k : 0;
    BODY[n + 1] = x;
  }
}
export const STRIDE = BODY[N]; // mm per crank turn (signed)
export const bodyX = (th) => {
  const turns = Math.floor(th / (2 * Math.PI));
  const u = (th / (2 * Math.PI) - turns) * N;
  const n = Math.floor(u);
  return turns * STRIDE + BODY[n] + (BODY[n + 1] - BODY[n]) * (u - n);
};
export const feetDown = (th) => FEET.reduce((s, _, i) => s + (onGround(i, th) ? 1 : 0), 0);

// ------------------------------------------------------------ geometry
function shapeOf(p) {
  const sh = new THREE.Shape(p.outer.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const h of p.holes) sh.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
  return sh;
}
const GEO = {};
export function geo(name, depth = T) {
  const key = name + depth;
  if (!GEO[key]) {
    const g = new THREE.ExtrudeGeometry(DATA.parts[name].map(shapeOf), {depth, bevelEnabled: true, bevelThickness: 0.35, bevelSize: 0.35, bevelSegments: 1, curveSegments: 6});
    g.translate(0, 0, 0.35);
    g.scale(1, 1, depth / (depth + 0.7));
    g.computeVertexNormals();
    GEO[key] = g;
  }
  return GEO[key];
}

export function buildWalker(P) {
  const root = new THREE.Group(); // in mm; the caller scales it to metres
  const mat = (color, o = {}) => new THREE.MeshStandardMaterial({color, roughness: 0.55, metalness: 0, ...o});
  const M = {
    leg: mat(P.leg),
    tri: mat(P.tri),
    web: mat(P.accent2, {roughness: 0.45}),
    frame: mat(P.frame, {roughness: 0.5, metalness: 0.1}),
    pin: mat(P.pin, {roughness: 0.4}),
    gear: mat(P.gear, {roughness: 0.45}),
    motor: mat('#e8c23a', {roughness: 0.42}),
    can: new THREE.MeshStandardMaterial({color: '#c9ccd1', roughness: 0.3, metalness: 0.9}),
    shaft: new THREE.MeshStandardMaterial({color: '#bfc3c8', roughness: 0.25, metalness: 1}),
    foot: mat(P.foot),
    cable: mat('#2b2b2b', {roughness: 0.7}),
    ghost: new THREE.MeshStandardMaterial({color: P.leg, transparent: true, opacity: 0.06, depthWrite: false, roughness: 0.6}),
    hot: mat(P.accent, {roughness: 0.5}),
  };
  const add = (parent, g, m) => {
    const mesh = new THREE.Mesh(g, m);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.matrixAutoUpdate = false;
    parent.add(mesh);
    return mesh;
  };
  const zLayer = (i, l) => ZF[i] + T + GAP + (l - 1) * PITCH;
  // modules: one group each so the exploded view can slide it along the axle
  const mods = [];
  const pinGeo = new THREE.CylinderGeometry(2, 2, 1, 12).rotateX(Math.PI / 2).translate(0, 0, 0.5);
  for (const i of MODULES) {
    const g = new THREE.Group();
    root.add(g);
    const parts = [];
    for (const [key, l] of Object.entries(META.layers)) {
      const half = key === 'web_a' ? 'L' : key === 'web_b' ? 'M' : key[0];
      const name = key.startsWith('web') ? 'web' : key.slice(2);
      const holder = new THREE.Group();
      holder.matrixAutoUpdate = false;
      g.add(holder);
      if (half === 'M') holder.matrix.makeRotationY(Math.PI).setPosition(0, 0, zLayer(i, l) + T);
      else holder.matrix.makeTranslation(0, 0, zLayer(i, l));
      const m = name === 'web' ? M.web : name.startsWith('tri') ? M.tri : M.leg;
      const mesh = add(holder, geo(name), m);
      mesh.userData.base = m;
      parts.push({mesh, name, half});
    }
    // pins: one per joint of each half, the crank pin A through the whole module
    const pins = [];
    const span = (lo, hi) => [zLayer(i, lo), zLayer(i, hi) + T];
    const L = Object.fromEntries(Object.entries(META.layers).map(([k, v]) => [k, v]));
    const lay = (n, h) => L[`${h}:${n}`];
    const pinDefs = [
      ['A', 'L', span(1, NL)],
      ...['L', 'M'].flatMap((h) => {
        const z = (n) => lay(n, h);
        const lo = (...ns) => Math.min(...ns.map(z));
        const hi = (...ns) => Math.max(...ns.map(z));
        const fr = h === 'L' ? [ZF[i], zLayer(i, hi('link-c', 'tri-upper')) + T] : [zLayer(i, lo('link-c', 'tri-upper')), ZF[i + 1] + T];
        return [
          ['B', h, span(lo('link-j', 'tri-upper'), hi('link-j', 'tri-upper'))],
          ['C', h, span(lo('link-c', 'tri-foot', 'link-k'), hi('link-c', 'tri-foot', 'link-k'))],
          ['D', h, span(lo('link-f', 'tri-upper'), hi('link-f', 'tri-upper'))],
          ['E', h, span(lo('link-f', 'tri-foot'), hi('link-f', 'tri-foot'))],
          ['P', h, fr],
        ];
      }),
    ];
    for (const [k, h, [z0, z1]] of pinDefs) {
      const mesh = add(g, pinGeo, M.pin);
      pins.push({mesh, k, h, z0, z1});
    }
    mods.push({i, g, parts, pins, phase: PHASE[i] * D2R});
  }
  // frames
  const frames = [];
  ZF.forEach((z, i) => {
    const below = i > 0 ? SECTIONS[i - 1] : null;
    const above = i < SECTIONS.length ? SECTIONS[i] : null;
    const kind = below === 'gear' && above === 'motor' ? 'motor' : below === 'motor' ? 'motor_back' : 'plain';
    const name = `frame-${kind}` + (below === 'mod' ? '-Plo' : '') + (above === 'mod' ? '-Phi' : '');
    const mesh = add(root, geo(name), M.frame);
    mesh.matrix.makeTranslation(0, 0, z);
    frames.push({mesh, i, z});
  });
  // rails
  const [rx, ry, rw, rh] = META.rail;
  const railLen = ZF[ZF.length - 1] + T + 4;
  for (const x of [-rx, rx]) {
    const r = add(root, new THREE.BoxGeometry(rw, rh, railLen), M.frame);
    r.matrix.makeTranslation(x, ry, railLen / 2 - 2);
  }
  // crankshaft: hex couplers through every frame, turning with the crank
  const hex = add(root, new THREE.CylinderGeometry(3.46, 3.46, ZF[ZF.length - 1] + T + 3, 6).rotateX(Math.PI / 2).translate(0, 0, (ZF[ZF.length - 1] + T) / 2), M.shaft);
  // gears in the gear bay, motor in the motor bay
  const gi = SECTIONS.indexOf('gear');
  const zg = ZF[gi] + T + GAP;
  const gear = add(root, geo('gear-48', 4.6), M.gear);
  const pinion = add(root, geo('pinion', 4.6), M.web);
  const mi = SECTIONS.indexOf('motor');
  const zm = ZF[mi] + T; // the motor's shaft face against the motor plate
  const motor = new THREE.Group();
  root.add(motor);
  {
    const box = add(motor, new THREE.BoxGeometry(22.4, 48.4, 18.8), M.motor);
    box.matrix.makeTranslation(0, CD - 11.2 + 24.2, zm + 9.4);
    const can = add(motor, new THREE.CylinderGeometry(10.2, 10.2, 22, 32), M.can);
    can.matrix.makeTranslation(0, CD - 11.2 + 48.4 + 11, zm + 9.4);
    const shaft = add(motor, new THREE.CylinderGeometry(2.7, 2.7, 8.5, 16).rotateX(Math.PI / 2), M.shaft);
    shaft.matrix.makeTranslation(0, CD, zm - 4.25);
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, CD + 48.4 + 11, zm + 9.4),
      new THREE.Vector3(0, CD + 64, zm + 9.4),
      new THREE.Vector3(70, CD + 58, zm + 9.4),
      new THREE.Vector3(150, -40, zm + 9.4),
      new THREE.Vector3(190, -98, zm + 9.4),
    ]);
    add(motor, new THREE.TubeGeometry(curve, 40, 1.6, 8), M.cable).matrix.identity();
  }
  // foot traces, one module's two feet, drawn in the body frame
  const traces = [];
  for (const mirror of [false, true]) {
    const pts = [];
    for (let n = 0; n <= 180; n++) {
      const f = footAt((n / 180) * 2 * Math.PI, mirror);
      pts.push(new THREE.Vector3(f[0], f[1], 0));
    }
    const line = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true), 240, 0.7, 6, true), M.hot);
    line.visible = false;
    line.matrixAutoUpdate = false;
    root.add(line);
    traces.push(line);
  }

  const T4 = new THREE.Matrix4();
  const rigid = (mesh, js, J, extra) => {
    const o0 = J0[js[0]];
    const p0 = J0[js[1]];
    const o = J[js[0]];
    const p = J[js[1]];
    const rot = Math.atan2(p[1] - o[1], p[0] - o[0]) - Math.atan2(p0[1] - o0[1], p0[0] - o0[0]);
    mesh.matrix.makeTranslation(o[0], o[1], 0).multiply(T4.makeRotationZ(rot)).multiply(new THREE.Matrix4().makeTranslation(-o0[0], -o0[1], 0));
  };

  /** pose for crank angle th; ops: {iso: module index to keep solid or -1, explode 0..1, trace: bool, hot: contact accent} */
  function update(th, ops = {}) {
    const iso = ops.iso ?? -1;
    const ex = ops.explode ?? 0;
    const mid = (ZF[0] + ZF[ZF.length - 1]) / 2;
    for (const m of mods) {
      const a = th + m.phase;
      const JL = legL(a);
      const JM = legMraw(a);
      for (const p of m.parts) {
        rigid(p.mesh, JOINTS_OF[p.name], p.half === 'L' ? JL : JM);
        const ghost = iso >= 0 && iso !== m.i;
        p.mesh.material = ghost ? M.ghost : p.mesh.userData.base;
        p.mesh.castShadow = !ghost;
      }
      for (const pn of m.pins) {
        const J = pn.h === 'L' ? JL : JM;
        const q = pn.h === 'L' ? J[pn.k] : [-J[pn.k][0], J[pn.k][1]];
        pn.mesh.matrix.makeTranslation(q[0], q[1], pn.z0).multiply(T4.makeScale(1, 1, pn.z1 - pn.z0));
        pn.mesh.visible = !(iso >= 0 && iso !== m.i);
      }
      const zc = (ZF[m.i] + ZF[m.i + 1]) / 2;
      m.g.position.z = (zc - mid) * ex * 1.6;
      // the feet that are down glow
      for (const p of m.parts) {
        if (p.name !== 'tri-foot') continue;
        const i = FEET.findIndex((f) => f.m === m.i && f.mirror === (p.half === 'M'));
        if (ops.hot && onGround(i, th) && !(iso >= 0 && iso !== m.i)) p.mesh.material = M.hot;
      }
    }
    for (const f of frames) {
      f.mesh.matrix.makeTranslation(0, 0, f.z + (f.z - mid) * ex * 1.6);
      f.mesh.material = iso >= 0 ? M.ghost : M.frame;
    }
    hex.matrix.makeRotationZ(th);
    gear.matrix.makeTranslation(0, 0, zg).multiply(T4.makeRotationZ(th));
    pinion.matrix.makeTranslation(0, CD, zg).multiply(T4.makeRotationZ(-4 * th + Math.PI / 12));
    const zIso = iso >= 0 ? (ZF[iso] + ZF[iso + 1]) / 2 : 0;
    traces.forEach((t, k) => {
      t.visible = !!ops.trace;
      t.matrix.makeTranslation(0, 0, iso >= 0 ? zLayer(iso, k ? NL - 2 : 3) : ZF[0] - 6);
    });
  }
  return {root, update, mods, frames, motor, gear, pinion, M, zMid: (ZF[0] + ZF[ZF.length - 1] + T) / 2, width: ZF[ZF.length - 1] + T};
}

export const MOTOR_RPM = 59; // Bambu LA001 at 5 V, no load
export const RATIO = 4; // 12:48
