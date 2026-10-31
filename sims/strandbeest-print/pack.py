# Lays the walker's parts out on print plates (one STL per plate, parts as separate bodies: in Bambu Studio use
# "Split to objects" if you want to move them).   python3 sims/strandbeest-print/pack.py <dir> [bed_mm]
import json, os, sys, math
import numpy as np, trimesh

D = sys.argv[1]
BED = float(sys.argv[2]) if len(sys.argv) > 2 else 250.0
GAP = 4.0
meta = json.load(open(os.path.join(D, 'walker.json')))
items = []
for name, n in meta['counts'].items():
    m = trimesh.load(os.path.join(D, name + '.stl'))
    # turn it in the bed plane so its 2D bounding box is smallest
    best = None
    for a in np.radians(np.arange(0, 180, 3)):
        R = trimesh.transformations.rotation_matrix(a, [0, 0, 1])
        v = trimesh.transform_points(m.vertices, R)
        w, h = np.ptp(v[:, 0]), np.ptp(v[:, 1])
        if best is None or w * h < best[0]: best = (w * h, a, w, h)
    _, a, w, h = best
    if w < h: a += math.pi / 2; w, h = h, w
    mm = m.copy(); mm.apply_transform(trimesh.transformations.rotation_matrix(a, [0, 0, 1]))
    mm.apply_translation(-mm.bounds[0])
    for _ in range(n): items.append((name, mm, w, h))
items.sort(key=lambda t: (-t[3], -t[2]))
plates = [[]]
x = y = shelf_h = 0.0
for name, m, w, h in items:
    if x + w > BED:
        x = 0; y += shelf_h + GAP; shelf_h = 0
    if y + h > BED:
        plates.append([]); x = y = shelf_h = 0
    plates[-1].append((name, m, x, y))
    x += w + GAP; shelf_h = max(shelf_h, h)
outd = os.path.join(D, 'plates'); os.makedirs(outd, exist_ok=True)
for f in os.listdir(outd): os.remove(os.path.join(outd, f))
summary = []
for i, pl in enumerate(plates):
    ms = []
    names = {}
    for name, m, x, y in pl:
        c = m.copy(); c.apply_translation([x + 3, y + 3, 0]); ms.append(c); names[name] = names.get(name, 0) + 1
    trimesh.util.concatenate(ms).export(os.path.join(outd, f'plate-{i+1:02d}.stl'))
    summary.append((i + 1, names))
for i, names in summary: print(f'plate {i:2d}: ' + ', '.join(f'{k} x{v}' for k, v in names.items()))
