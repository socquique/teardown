# Writes sims/walker-shared/parts.json for the live page (sims/walker-live): every part's outline (with holes) sliced
# from the STLs walker.py made, plus the layout (layers, frame positions, gears, rails).
#   python3 sims/strandbeest-print/export_web.py teardown-out/print/strandbeest-walker
import json, os, sys
import numpy as np, trimesh
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

D = sys.argv[1]
M = json.load(open(os.path.join(D, 'walker.json')))
T = M['T']
def outline(name, z=None):
    m = trimesh.load(os.path.join(D, name + '.stl'))
    z = z if z is not None else (m.bounds[0][2] + m.bounds[1][2]) / 2
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    g = Polygon()
    for loop in sec.discrete: g = g.symmetric_difference(Polygon(loop[:, :2]).buffer(0))
    g = g.simplify(0.05)
    polys = [g] if g.geom_type == 'Polygon' else list(g.geoms)
    out = []
    for p in polys:
        p = orient(p, 1.0)
        out.append({'outer': np.round(np.array(p.exterior.coords)[:-1], 2).tolist(),
                    'holes': [np.round(np.array(h.coords)[:-1], 2).tolist() for h in p.interiors]})
    return out
names = ['link-j', 'link-k', 'link-c', 'link-f', 'tri-upper', 'tri-foot', 'web', 'pinion', 'gear-48']
names += [n for n in M['counts'] if n.startswith('frame-')]
meta = {k: M[k] for k in ('S', 'T', 'GAP', 'PITCH', 'R', 'layers', 'NL', 'ZF', 'sections', 'CD', 'rail', 'motor_slab', 'gear_slab', 'counts', 'pins')}
data = {'meta': meta, 'parts': {n: outline(n) for n in names}}
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'walker-shared', 'parts.json')
json.dump(data, open(p, 'w'), separators=(',', ':'))
print(p, os.path.getsize(p) // 1024, 'KB')
