// A Strandbeest leg you can print and turn by hand: the same linkage the simulator solves (jansen.js), rebuilt as flat
// FDM parts that actually work. Every link is a plate with rounded ends, the two rigid triangles of Jansen's leg are
// single plates, and every joint is an M3 screw with a nyloc nut.
//
//   node sims/strandbeest-print/kit.mjs                 # teardown-out/print/strandbeest-leg/
//   node sims/strandbeest-print/kit.mjs --scale 2       # 2 mm per Jansen unit (bigger leg)
//
// What makes it work rather than just look right:
//  - layers: each part sits on a layer chosen by search, so that over a whole turn of the crank no two parts on the
//    same layer ever overlap, and no screw ever passes through a part that is not on it. The search is checked at
//    every degree of the crank.
//  - clearances: moving joints get a 3.4 mm hole on an M3 screw; the frame gets 2.8 mm so the screws thread in and
//    stay put; layers sit 0.4 mm apart and printed washers fill the gaps, so nothing rubs or binds.
//  - the frame holds the crank axle and the fixed pivot at Jansen's exact offset, and the crank has a handle.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as THREE from 'three';
import {STLExporter} from 'three/addons/exporters/STLExporter.js';
import {HOLY, solveLeg} from '../strandbeest-shared/jansen.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const opt = (k, d) => (argv.includes(`--${k}`) ? Number(argv[argv.indexOf(`--${k}`) + 1]) : d);
const outArg = argv.includes('--out') ? argv[argv.indexOf('--out') + 1] : null;

// ------------------------------------------------------------ parameters (millimetres)
const P = {
  scale: opt('scale', 1.5), // mm per Jansen unit: 1.5 gives a leg about 15 cm tall
  t: opt('thick', 3.2), // plate thickness
  gap: 0.4, // air between layers
  R: 5.5, // radius of the rounded ends around each hole
  holeMove: 3.4, // M3 clearance: the part turns on the screw
  holeFix: 2.8, // M3 self-tapping into the frame: the screw is fixed
  pinR: 1.7, // what a screw sweeps, for the collision check
  headR: 3.4, // what a screw head or nut sweeps (M3 socket head 5.5 mm, nut 6.4 mm across corners), one layer past the stack
  washerOD: 7.5,
  steps: 360,
};
const PITCH = P.t + P.gap;

// ------------------------------------------------------------ the mechanism
// joint positions in mm for crank angle th, with the crank axle O at the origin
const S = P.scale;
const pose = (th) => {
  const L = solveLeg(th);
  const o = {};
  for (const k in L) o[k] = [L[k][0] * S, L[k][1] * S];
  return o;
};
// parts: name, the joints they carry, and which holes are fixed (threaded) rather than turning
const PARTS = [
  {name: 'crank', joints: ['O', 'A'], wheel: true}, // a wheel you turn by its rim
  {name: 'link-j', joints: ['A', 'B']},
  {name: 'link-k', joints: ['A', 'C']},
  {name: 'link-c', joints: ['P', 'C']},
  {name: 'link-f', joints: ['D', 'E']},
  {name: 'triangle-upper', joints: ['P', 'B', 'D']},
  {name: 'triangle-foot', joints: ['C', 'E', 'F'], foot: 'F'},
];
const FRAME = {name: 'frame', joints: ['O', 'P'], tab: true}; // with a tab to hold it by or screw it to a board
const WHEEL_R = () => HOLY.m * P.scale + P.R + 1;
const TAB = [42, 0]; // tab end, mm from O, away from the leg

// a part's outline at a pose: convex hull of a circle of radius R around each joint (the foot gets a bigger pad)
const circle = ([x, y], r, n = 20) => Array.from({length: n}, (_, i) => [x + r * Math.cos((i / n) * 2 * Math.PI), y + r * Math.sin((i / n) * 2 * Math.PI)]);
function hull(pts) {
  const p = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [];
  for (const q of p) {
    while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop();
    lo.push(q);
  }
  const up = [];
  for (const q of p.reverse()) {
    while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop();
    up.push(q);
  }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}
const outline = (part, J) => {
  const pts = part.joints.flatMap((k) => circle(J[k], k === part.foot ? P.R * 1.25 : P.R));
  if (part.wheel) pts.push(...circle(J.O, WHEEL_R(), 36));
  if (part.tab) pts.push(...circle(TAB, 9, 24), ...circle([TAB[0], -12], 9, 24), ...circle([TAB[0], 12], 9, 24));
  return hull(pts);
};

// convex polygon overlap (separating axis), with a margin so near-misses count as hits
function overlap(a, b, margin = 0.3) {
  for (const poly of [a, b])
    for (let i = 0; i < poly.length; i++) {
      const [x0, y0] = poly[i];
      const [x1, y1] = poly[(i + 1) % poly.length];
      const nx = y1 - y0;
      const ny = x0 - x1;
      const len = Math.hypot(nx, ny);
      const pr = (P) => P.map(([x, y]) => (x * nx + y * ny) / len);
      const pa = pr(a);
      const pb = pr(b);
      if (Math.max(...pa) + margin < Math.min(...pb) || Math.max(...pb) + margin < Math.min(...pa)) return false;
    }
  return true;
}
// distance from a point to a convex polygon (0 inside)
function distTo(poly, [px, py]) {
  let inside = true;
  let d = Infinity;
  for (let i = 0; i < poly.length; i++) {
    const [x0, y0] = poly[i];
    const [x1, y1] = poly[(i + 1) % poly.length];
    if ((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0) < 0) inside = false;
    const t = Math.max(0, Math.min(1, ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / ((x1 - x0) ** 2 + (y1 - y0) ** 2)));
    d = Math.min(d, Math.hypot(px - x0 - t * (x1 - x0), py - y0 - t * (y1 - y0)));
  }
  return inside ? 0 : d;
}

// ------------------------------------------------------------ what can never share a layer, and which screws hit what
const ALL = [FRAME, ...PARTS];
const n = ALL.length;
const clash = Array.from({length: n}, () => Array(n).fill(false)); // the two parts overlap at some angle
const pinHits = {}; // joint -> set of parts that pass over that joint's screw at some angle
const headHits = {}; // joint -> set of parts that pass over its screw head or nut
const JOINT_NAMES = [...new Set(ALL.flatMap((p) => p.joints))].filter((k) => !ALL.every((p) => p.foot !== k) || ALL.filter((p) => p.joints.includes(k)).length > 1);
for (const k of JOINT_NAMES) (pinHits[k] = new Set()), (headHits[k] = new Set());
for (let s = 0; s < P.steps; s++) {
  const J = pose((s / P.steps) * 2 * Math.PI);
  const outl = ALL.map((p) => outline(p, J));
  for (let a = 0; a < n; a++) {
    for (let b = a + 1; b < n; b++) if (!clash[a][b] && overlap(outl[a], outl[b])) clash[a][b] = clash[b][a] = true;
    for (const k of JOINT_NAMES) {
      if (ALL[a].joints.includes(k)) continue;
      const d = distTo(outl[a], J[k]);
      if (d < P.pinR + 0.8) pinHits[k].add(a);
      if (d < P.headR + 0.8) headHits[k].add(a);
    }
  }
}

// ------------------------------------------------------------ the layer search
// layer 0 is the frame; the moving parts take layers 1..L. A valid stack: no two clashing parts on one layer, no part
// on a layer that one of the screws passes through unless the screw is its own. Among valid stacks, the fewest layers,
// then the shortest screws.
const members = (k) => ALL.map((p, i) => (p.joints.includes(k) ? i : -1)).filter((i) => i >= 0);
function check(layer) {
  for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) if (clash[a][b] && layer[a] === layer[b]) return false;
  for (const k of JOINT_NAMES) {
    const m = members(k);
    if (m.length < 2) continue;
    const ls = m.map((i) => layer[i]);
    if (new Set(ls).size !== ls.length) return false;
    const lo = Math.min(...ls);
    const hi = Math.max(...ls);
    for (const i of pinHits[k]) if (layer[i] >= lo && layer[i] <= hi) return false;
    // the head (or nut) sits one layer past each end; screws into the frame have only the top one
    for (const i of headHits[k]) if (layer[i] === hi + 1 || (lo > 0 && layer[i] === lo - 1)) return false;
  }
  return true;
}
const screwLen = (layer) =>
  JOINT_NAMES.reduce((s, k) => {
    const ls = members(k).map((i) => layer[i]);
    return ls.length < 2 ? s : s + Math.max(...ls) - Math.min(...ls);
  }, 0);
let best = null;
for (let L = 2; L <= 7 && !best; L++) {
  const layer = Array(n).fill(0);
  const rec = (i) => {
    if (i === n) {
      if (check(layer) && (!best || screwLen(layer) < screwLen(best))) best = [...layer];
      return;
    }
    for (let l = 1; l <= L; l++) {
      layer[i] = l;
      rec(i + 1);
    }
  };
  rec(1);
}
if (!best) throw new Error('no layer stack found');
const LAYERS = Math.max(...best);

// ------------------------------------------------------------ geometry
const shape2 = (pts) => {
  const sh = new THREE.Shape();
  pts.forEach(([x, y], i) => (i ? sh.lineTo(x, y) : sh.moveTo(x, y)));
  sh.closePath();
  return sh;
};
const hole = ([x, y], d) => {
  const h = new THREE.Path();
  h.absarc(x, y, d / 2, 0, Math.PI * 2, true);
  return h;
};
// a part laid out in its own frame (rigid, so any pose will do): first joint at the origin
function partGeo(part, J, fixed = false) {
  const o = J[part.joints[0]];
  const loc = (q) => [q[0] - o[0], q[1] - o[1]];
  const pts = part.joints.flatMap((k) => circle(loc(J[k]), k === part.foot ? P.R * 1.25 : P.R, 48));
  if (part.wheel) pts.push(...circle([0, 0], WHEEL_R(), 96));
  const sh = shape2(hull(pts));
  for (const k of part.joints) if (k !== part.foot) sh.holes.push(hole(loc(J[k]), fixed ? P.holeFix : P.holeMove));
  // the wheel: grip notches round the rim, and windows to make it light
  if (part.wheel) {
    const R0 = WHEEL_R();
    const pts2 = [];
    for (let i = 0; i < 240; i++) {
      const a = (i / 240) * Math.PI * 2;
      const r = R0 - (Math.floor(i / 5) % 2 ? 0.8 : 0);
      pts2.push([r * Math.cos(a), r * Math.sin(a)]);
    }
    const w = shape2(pts2);
    w.holes.push(hole([0, 0], P.holeMove), hole(loc(J.A), P.holeMove));
    const aA = Math.atan2(loc(J.A)[1], loc(J.A)[0]);
    for (const da of [Math.PI * 0.5, Math.PI, Math.PI * 1.5]) w.holes.push(hole([Math.cos(aA + da) * R0 * 0.55, Math.sin(aA + da) * R0 * 0.55], R0 * 0.5));
    return new THREE.ExtrudeGeometry(w, {depth: P.t, bevelEnabled: false, curveSegments: 24});
  }
  const g = new THREE.ExtrudeGeometry(sh, {depth: P.t, bevelEnabled: false, curveSegments: 24});
  return g;
}
function mergeAll(gs) {
  const nonIdx = gs.map((g) => (g.index ? g.toNonIndexed() : g));
  const n = nonIdx.reduce((s, g) => s + g.attributes.position.count, 0);
  const arr = new Float32Array(n * 3);
  let o = 0;
  for (const g of nonIdx) arr.set(g.attributes.position.array, o), (o += g.attributes.position.array.length);
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(arr, 3));
  return out;
}

// the frame: a plate holding O and P (threaded), with a foot to stand it upright and clear of the moving parts
function frameGeo(J) {
  const pts = [...circle(J.O, P.R + 2, 48), ...circle(J.P, P.R + 2, 48), ...circle(TAB, 9, 48), ...circle([TAB[0], -12], 9, 48), ...circle([TAB[0], 12], 9, 48)];
  const sh = shape2(hull(pts));
  sh.holes.push(hole(J.O, P.holeFix), hole(J.P, P.holeFix), hole([TAB[0], -12], 4.5), hole([TAB[0], 12], 4.5));
  const plate = new THREE.ExtrudeGeometry(sh, {depth: P.t + 1, bevelEnabled: false, curveSegments: 24});
  return plate;
}
const washer = (h) => {
  const sh = shape2(circle([0, 0], P.washerOD / 2, 48));
  sh.holes.push(hole([0, 0], P.holeMove));
  return new THREE.ExtrudeGeometry(sh, {depth: h, bevelEnabled: false, curveSegments: 24});
};

// ------------------------------------------------------------ output
const out = path.resolve(outArg || path.join(HERE, '..', '..', 'teardown-out', 'print', 'strandbeest-leg'));
fs.mkdirSync(out, {recursive: true});
for (const f of fs.readdirSync(out)) if (f.endsWith('.stl')) fs.unlinkSync(path.join(out, f));
const exporter = new STLExporter();
const write = (file, geo) => {
  const d = exporter.parse(new THREE.Mesh(geo), {binary: true});
  fs.writeFileSync(path.join(out, file), Buffer.from(d.buffer, d.byteOffset, d.byteLength));
};
const J0 = pose(0);
const geos = {frame: frameGeo(J0)};
for (const p of PARTS) geos[p.name] = partGeo(p, J0);
let i = 0;
for (const [name, g] of Object.entries(geos)) write(`${String(++i).padStart(2, '0')}-${name}.stl`, g);

// washers: at each joint, fill the empty layers between the parts on its screw
const bom = [];
let washers = 0;
const screws = [];
const zOf = (l) => (l === 0 ? 0 : P.t + 1 + P.gap + (l - 1) * PITCH); // frame is 1 mm thicker
for (const k of JOINT_NAMES) {
  const m = members(k);
  if (m.length < 2) continue;
  const ls = m.map((i) => best[i]).sort((a, b) => a - b);
  let fill = 0;
  for (let l = ls[0] + 1; l < ls[ls.length - 1]; l++) if (!ls.includes(l)) fill++;
  washers += fill;
  const top = zOf(ls[ls.length - 1]) + P.t;
  const bottom = zOf(ls[0]);
  screws.push({k, len: top - bottom, parts: m.map((i) => ALL[i].name), fixed: m.includes(0)});
}
write(`${String(++i).padStart(2, '0')}-washer-x${washers + 2}.stl`, washer(P.gap + P.t - 0.2));

// the assembly at crank angle 0, for a look in the slicer or a viewer
const asm = [];
const place = (g, part, J, l) => {
  const o = J[part.joints[0]];
  const g2 = (g.index ? g.toNonIndexed() : g.clone()).translate(o[0], o[1], zOf(l));
  asm.push(g2);
};
asm.push(geos.frame.clone());
PARTS.forEach((p, idx) => {
  // rebuild each part at pose 0 in place (rigid parts: translate only, they were laid out at pose 0)
  place(geos[p.name], p, J0, best[idx + 1]);
});
write('assembly.stl', mergeAll(asm));

// ------------------------------------------------------------ report
const STD = [6, 8, 10, 12, 16, 20, 25, 30];
const nutLen = (len) => STD.find((s) => s >= len + 4.5) ?? Math.ceil(len + 5); // room for a nyloc nut
const fixLen = (len) => [...STD].reverse().find((s) => s <= len - 0.5); // threads into the frame, tip flush with its back
const lines = [];
lines.push(`Strandbeest leg — printable kit, ${P.scale} mm per Jansen unit`);
lines.push('');
lines.push(`Layers (0 = frame): ${ALL.map((p, k) => `${p.name}=${best[k]}`).join(', ')}`);
fs.writeFileSync(path.join(out, 'layers.json'), JSON.stringify({scale: P.scale, t: P.t, gap: P.gap, R: P.R, headR: P.headR, pinR: P.pinR, layers: Object.fromEntries(ALL.map((p, k) => [p.name, best[k]])), joints: Object.fromEntries(ALL.map((p) => [p.name, p.joints]))}, null, 1));
lines.push(`Checked at every 1° of the crank: no two parts on a layer overlap; no screw passes through a part that is not on it.`);
lines.push('');
lines.push('Screws');
for (const s of screws) lines.push(`  ${s.k}: M3 × ${s.fixed ? fixLen(s.len) : nutLen(s.len)} ${s.fixed ? '(threads into the frame, no nut)' : '+ M3 nyloc nut, snug, not tight'} — ${s.parts.join(', ')}`);
lines.push('');
lines.push('Print');
lines.push(`  PLA or PETG, 0.2 mm layers, 3 walls, 30 % infill, flat on the bed, no supports.`);
lines.push(`  Washers: ${washers} fill the empty layers on the screws; the rest are spares.`);
lines.push(`  Holes are ${P.holeMove} mm (turning) and ${P.holeFix} mm (frame, threaded). If a joint is stiff, run a 3.5 mm drill through it.`);
lines.push('');
lines.push('Assemble');
lines.push('  Hold the frame by its tab, or screw the tab (two 4 mm holes) to the side of an upright stick so the leg can swing freely. Build up from the frame: on each screw put the');
lines.push('  parts in layer order, a washer wherever a layer is empty, then the nut. Turn the wheel by its rim.');
const report = lines.join('\n') + '\n';
fs.writeFileSync(path.join(out, 'README.txt'), report);
console.log(report);
console.log(`→ ${out}`);
export {best, ALL, PARTS, pose, outline, zOf, P, JOINT_NAMES, members};
