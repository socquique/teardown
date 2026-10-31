// Exports a machine's solid parts to STL, in millimetres, for 3D printing or CAD.
//
//   node sims/export-stl.mjs v8                  # teardown-out/stl/v8/
//   node sims/export-stl.mjs cessna --pose 0.5   # landing gear half way through its stroke
//   node sims/export-stl.mjs strandbeest --out ~/prints/beast
//   node sims/export-stl.mjs cessna --scale 0.1  # a 1:10 model instead of full size
//
// Writes two things:
//   assembly.stl     every solid part where the simulator puts it, at the pose asked for
//   parts/NN-*.stl   each distinct part once, on its own, lying on z = 0 and centred on x/y
// plus report.txt: one line per part with its size, how many copies the machine uses, and whether its mesh is closed
// (a slicer needs closed meshes; an open one is flagged so it can be repaired first).
//
// Overlays (arrows, glows, glass, sails, labels) are skipped: anything with a MeshBasicMaterial, a hidden material or
// a transparent one below half opacity. The simulators are built to look right, not to print: teeth, bores and
// clearances are visual, so treat the parts as a starting point for models, not as working mechanisms.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as THREE from 'three';
import {STLExporter} from 'three/addons/exporters/STLExporter.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));

// --- a tiny stand-in for the browser: the models draw a few labels to a 2D canvas, which an STL does not need
if (typeof globalThis.document === 'undefined') {
  const ctx = new Proxy({}, {get: (t, k) => (k === 'measureText' ? () => ({width: 0}) : k in t ? t[k] : () => ctx), set: (t, k, v) => ((t[k] = v), true)});
  globalThis.document = {createElement: () => ({width: 0, height: 0, style: {}, getContext: () => ctx})};
}
const warn = console.warn;
console.warn = (...a) => (String(a[0]).startsWith('THREE.Material') ? 0 : warn(...a));

// --- each machine: how to build it, how to pose it, and its units in millimetres
const MACHINES = {
  v8: {
    async build() {
      const {buildEngine} = await import('./v8-shared/engine.js');
      return buildEngine({});
    },
    pose: (m, p) => m.update(p * 720, {}), // pose 0..1 = crank angle 0..720°
    root: (m) => m.root,
    mm: 1,
  },
  cessna: {
    async build() {
      const {buildGear} = await import('./cessna-shared/gear.js');
      return buildGear();
    },
    pose: (m, p) => m.update({stroke: p}), // pose 0..1 = gear down..up
    root: (m) => m.root,
    mm: 1000,
  },
  strandbeest: {
    async build() {
      const {buildBeast} = await import('./strandbeest-shared/beast.js');
      const {PALETTES} = await import('./strandbeest-shared/stage.js');
      return buildBeast(PALETTES.sand);
    },
    pose: (m, p) => m.update(p * Math.PI * 2, 0, 0, {}), // pose 0..1 = one turn of the crank
    root: (m) => m.group,
    mm: 1000,
  },
};

// --- args
const argv = process.argv.slice(2);
const name = argv.find((a) => !a.startsWith('--') && !argv[argv.indexOf(a) - 1]?.startsWith('--'));
const opt = (k, d) => (argv.includes(`--${k}`) ? argv[argv.indexOf(`--${k}`) + 1] : d);
if (!MACHINES[name]) {
  console.error(`usage: node sims/export-stl.mjs <${Object.keys(MACHINES).join('|')}> [--pose 0..1] [--scale k] [--out dir]`);
  process.exit(1);
}
const M = MACHINES[name];
const pose = Number(opt('pose', 0));
const userScale = Number(opt('scale', 1));
const out = path.resolve(opt('out', path.join(HERE, '..', 'teardown-out', 'stl', name)));

// --- build and pose
const machine = await M.build();
try {
  M.pose(machine, pose);
} catch (e) {
  console.warn(`pose skipped: ${e.message}`);
}
const root = M.root(machine);
root.updateMatrixWorld(true);
// work in the machine's own frame (the stage may scale or place the root), converted to millimetres
const toRoot = root.matrixWorld.clone().invert();

const solid = (mat) => {
  const ms = Array.isArray(mat) ? mat : [mat];
  return ms.some((x) => x && x.visible !== false && !x.isMeshBasicMaterial && !(x.transparent && x.opacity < 0.5));
};
const shown = (o) => {
  for (let p = o; p; p = p.parent) if (!p.visible) return false;
  return true;
};

// every solid mesh (instanced meshes expanded), with its matrix in millimetres
const k0 = M.mm * userScale;
const scale = new THREE.Matrix4().makeScale(k0, k0, k0).multiply(toRoot);
const items = [];
root.traverse((o) => {
  if (!o.isMesh || !o.geometry?.attributes?.position || !shown(o) || !solid(o.material)) return;
  if (o.isInstancedMesh) {
    const im = new THREE.Matrix4();
    for (let i = 0; i < o.count; i++) {
      o.getMatrixAt(i, im);
      items.push({o, world: scale.clone().multiply(o.matrixWorld).multiply(im)});
    }
  } else items.push({o, world: scale.clone().multiply(o.matrixWorld)});
});

// a geometry baked by a matrix: non-indexed, winding flipped where the matrix mirrors
function bake(geo, m) {
  const g = (geo.index ? geo.toNonIndexed() : geo.clone()).applyMatrix4(m);
  for (const k of Object.keys(g.attributes)) if (k !== 'position') g.deleteAttribute(k);
  if (m.determinant() < 0) {
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i += 3) {
      const [x, y, z] = [p.getX(i + 1), p.getY(i + 1), p.getZ(i + 1)];
      p.setXYZ(i + 1, p.getX(i + 2), p.getY(i + 2), p.getZ(i + 2));
      p.setXYZ(i + 2, x, y, z);
    }
  }
  return g;
}

// open edges: edges used by a single triangle once positions are welded to 1 µm (0 means the mesh is closed)
function openEdges(g) {
  const p = g.attributes.position;
  const key = (i) => `${Math.round(p.getX(i) * 1000)},${Math.round(p.getY(i) * 1000)},${Math.round(p.getZ(i) * 1000)}`;
  const edges = new Map();
  for (let i = 0; i < p.count; i += 3) {
    const k = [key(i), key(i + 1), key(i + 2)];
    if (k[0] === k[1] || k[1] === k[2] || k[0] === k[2]) continue; // degenerate
    for (let e = 0; e < 3; e++) {
      const [a, b] = [k[e], k[(e + 1) % 3]];
      const id = a < b ? `${a}|${b}` : `${b}|${a}`;
      edges.set(id, (edges.get(id) || 0) + 1);
    }
  }
  let open = 0;
  for (const n of edges.values()) if (n === 1) open++;
  return open;
}

function merge(geos) {
  let n = 0;
  for (const g of geos) n += g.attributes.position.count;
  const arr = new Float32Array(n * 3);
  let o = 0;
  for (const g of geos) arr.set(g.attributes.position.array, o), (o += g.attributes.position.array.length);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
  return g;
}

const exporter = new STLExporter();
const write = (file, geo) => {
  const data = exporter.parse(new THREE.Mesh(geo), {binary: true});
  fs.writeFileSync(file, Buffer.from(data.buffer, data.byteOffset, data.byteLength));
};

fs.mkdirSync(path.join(out, 'parts'), {recursive: true});
for (const f of fs.readdirSync(path.join(out, 'parts'))) if (f.endsWith('.stl')) fs.unlinkSync(path.join(out, 'parts', f));

// --- the parts: each distinct shape once (rotation and position dropped), lying flat on z = 0
function flat(o, world) {
  const s = new THREE.Vector3();
  world.decompose(new THREE.Vector3(), new THREE.Quaternion(), s);
  const g = bake(o.geometry, new THREE.Matrix4().makeScale(s.x, s.y, s.z));
  g.computeBoundingBox();
  const size = g.boundingBox.getSize(new THREE.Vector3());
  // lay it on its largest face: put the shortest side vertical
  const axis = size.x <= size.y && size.x <= size.z ? 'x' : size.y <= size.z ? 'y' : 'z';
  if (axis === 'x') g.rotateY(Math.PI / 2);
  if (axis === 'y') g.rotateX(Math.PI / 2);
  g.computeBoundingBox();
  const c = g.boundingBox.getCenter(new THREE.Vector3());
  g.translate(-c.x, -c.y, -g.boundingBox.min.z);
  g.computeBoundingBox();
  return g;
}
// two parts are the same if they have the same triangles, the same size and the same spread of vertices (to 0.01 mm)
function signature(g) {
  const p = g.attributes.position.array;
  let a = 0;
  for (let i = 0; i < p.length; i++) a += Math.abs(p[i]);
  const sz = g.boundingBox.getSize(new THREE.Vector3());
  return [p.length, sz.x.toFixed(2), sz.y.toFixed(2), sz.z.toFixed(2), (a / p.length).toFixed(2)].join(':');
}
const parts = new Map();
const kept = [];
for (const it of items) {
  const {o, world} = it;
  const g = flat(o, world);
  if (g.boundingBox.max.z < 0.01) continue; // a flat sheet (shadow, decal, ground mark): nothing to print
  kept.push(it);
  const id = signature(g);
  if (parts.has(id)) parts.get(id).count++;
  else parts.set(id, {o, g, count: 1});
}
// --- the assembly
write(path.join(out, 'assembly.stl'), merge(kept.map(({o, world}) => bake(o.geometry, world))));

const lines = [];
let k = 0;
for (const {o, g, count} of [...parts.values()].sort((a, b) => b.count - a.count)) {
  const sz = g.boundingBox.getSize(new THREE.Vector3());
  const kind = (o.name || o.geometry.type.replace(/Geometry$/, '') || 'part').replace(/[^\w-]+/g, '_').toLowerCase();
  const file = `${String(++k).padStart(2, '0')}-${kind}.stl`;
  write(path.join(out, 'parts', file), g);
  const open = openEdges(g);
  lines.push(`${file.padEnd(28)} ${sz.x.toFixed(1)} × ${sz.y.toFixed(1)} × ${sz.z.toFixed(1)} mm   ×${String(count).padEnd(4)} ${open ? `OPEN (${open} edges)` : 'closed'}`);
}
const report = [`${name} at pose ${pose}, scale ${userScale}: ${kept.length} solid parts, ${parts.size} distinct`, '', ...lines, ''].join('\n');
fs.writeFileSync(path.join(out, 'report.txt'), report);
console.log(report);
console.log(`→ ${path.relative(process.cwd(), out) || '.'}`);
