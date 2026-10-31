# Independent check of the 12-leg walker, from the STLs it wrote (not from walker.py's own geometry):
#   python3 sims/strandbeest-print/verify_walker.py teardown-out/print/strandbeest-walker
# Own Jansen solver; real outlines sliced from the STLs; every degree of the crank.
import json, math, sys, os
import numpy as np, trimesh
from shapely.geometry import Polygon, Point, LineString
from shapely import affinity
from shapely.ops import unary_union

D = sys.argv[1]
M = json.load(open(os.path.join(D, 'walker.json')))
S, T, PITCH = M['S'], M['T'], M['PITCH']
H = M['holy']
def cc(p0, r0, p1, r1):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; d = math.hypot(dx, dy)
    a = (r0*r0 - r1*r1 + d*d)/(2*d); h = math.sqrt(max(0, r0*r0 - a*a))
    mx, my = p0[0]+a*dx/d, p0[1]+a*dy/d
    return (mx + h*dy/d, my - h*dx/d), (mx - h*dy/d, my + h*dx/d)
def solve(th):
    P = (-H['a'], -H['l']); A = (H['m']*math.cos(th), H['m']*math.sin(th))
    B = max(cc(A, H['j'], P, H['b']), key=lambda q: q[1]); C = min(cc(A, H['k'], P, H['c']), key=lambda q: q[1])
    Dd = min(cc(B, H['e'], P, H['d']), key=lambda q: q[0]); E = min(cc(Dd, H['f'], C, H['g']), key=lambda q: q[0])
    F = min(cc(E, H['h'], C, H['i']), key=lambda q: q[1])
    return {k: (v[0]*S, v[1]*S) for k, v in dict(O=(0, 0), P=P, A=A, B=B, C=C, D=Dd, E=E, F=F).items()}

def outline(name):
    m = trimesh.load(os.path.join(D, name + '.stl'))
    sec = m.section(plane_origin=[0, 0, T / 2 + 0.3], plane_normal=[0, 0, 1])  # below the counterbores' depth? mid
    g = Polygon()
    for loop in sec.discrete: g = g.symmetric_difference(Polygon(loop[:, :2]).buffer(0))
    full = Polygon()
    for loop in sec.discrete:
        p = Polygon(loop[:, :2]).buffer(0)
        if p.area > full.area: full = p
    return g, full, m
J0 = solve(0)
legs = ['link-j', 'link-k', 'link-c', 'link-f', 'tri-upper', 'tri-foot', 'web']
JS = dict(M['joints']); JS['web'] = ['O', 'A']
shapes = {n: outline(n) for n in legs}
closed = {f[:-4]: trimesh.load(os.path.join(D, f)).is_watertight for f in os.listdir(D) if f.endswith('.stl')}

def place(n, J, solid=True):
    js = JS['crank' if n == 'web' else n]
    o0, p0, o, p = J0[js[0]], J0[js[1]], J[js[0]], J[js[1]]
    rot = math.atan2(p[1]-o[1], p[0]-o[0]) - math.atan2(p0[1]-o0[1], p0[0]-o0[0])
    g = shapes[n][1 if solid else 0]
    g = affinity.rotate(g, rot, origin=o0, use_radians=True)
    return affinity.translate(g, o[0]-o0[0], o[1]-o0[1])

lay = {k.split(':')[-1]: v for k, v in M['layers'].items() if k.startswith('L:')}
lay['web'] = 1
problems = []
members = {}
for n, js in JS.items():
    if n == 'crank': continue
    for k in js:
        if k == 'F' and n == 'tri-foot': continue
        members.setdefault(k, []).append(n)
members['P'] = members.get('P', []) + ['frame']
members['A'] = ['web', 'link-j', 'link-k']
pinR = 2.2; washerR = 4.0 + 0.4
washers = {'P': [1], 'A': [l for l in range(2, max(lay.values()) + 1) if l not in [lay['link-j'], lay['link-k']]]}
rails = [Point(-M['rail'][0], M['rail'][1]).buffer(1), Point(M['rail'][0], M['rail'][1]).buffer(1)]
rail_boxes = [Polygon([(x - M['rail'][2]/2, M['rail'][1] - M['rail'][3]/2), (x + M['rail'][2]/2, M['rail'][1] - M['rail'][3]/2),
                       (x + M['rail'][2]/2, M['rail'][1] + M['rail'][3]/2), (x - M['rail'][2]/2, M['rail'][1] + M['rail'][3]/2)]) for x in (-M['rail'][0], M['rail'][0])]
min_gap = {}
foot_low, other_low = 1e9, 1e9
sweep = Polygon()
for deg in range(360):
    J = solve(math.radians(deg))
    pl = {n: place(n, J) for n in legs}
    sweep = sweep.union(unary_union(list(pl.values()))) if deg % 10 == 0 else sweep
    for a in legs:
        for b in legs:
            if a < b and lay[a] == lay[b]:
                ar = pl[a].intersection(pl[b]).area
                if ar > 0.01: problems.append((deg, 'overlap', a, b, round(ar, 2)))
                min_gap[(a, b)] = min(min_gap.get((a, b), 1e9), pl[a].distance(pl[b]))
    for k, mem in members.items():
        ls = [0 if m == 'frame' else (lay[m] if k != 'A' else lay[m]) for m in mem]
        lo, hi = min(ls), max(ls)
        if k == 'A': hi = 99  # the crank pin runs through the whole module
        for n in legs:
            if n in mem: continue
            if lo <= lay[n] <= hi and pl[n].distance(Point(J[k])) < pinR: problems.append((deg, 'pin', k, n))
        for wl in washers.get(k, []):
            for n in legs:
                if n not in mem and lay[n] == wl and pl[n].distance(Point(J[k])) < washerR: problems.append((deg, 'washer', k, n))
    for n in legs:
        for rb in rail_boxes:
            if pl[n].intersects(rb.buffer(0.5)): problems.append((deg, 'rail', n))
    foot_low = min(foot_low, pl['tri-foot'].bounds[1])
    other_low = min(other_low, min(pl[n].bounds[1] for n in legs if n != 'tri-foot'))

# gears: rotate together at 4:1 and check the teeth never overlap
pin_g = trimesh.load(os.path.join(D, 'pinion.stl')).section(plane_origin=[0, 0, 2.3], plane_normal=[0, 0, 1])
gear_g = trimesh.load(os.path.join(D, 'gear-48.stl')).section(plane_origin=[0, 0, 2.3], plane_normal=[0, 0, 1])
def poly_of(sec):
    loops = sorted([Polygon(l[:, :2]).buffer(0) for l in sec.discrete], key=lambda p: -p.area)
    return loops[0]
pg, gg = poly_of(pin_g), poly_of(gear_g)
gear_ok = True; gear_min = 1e9
for i in range(40):
    a = i * 2 * math.pi / 12 / 40
    p = affinity.translate(affinity.rotate(pg, a + math.pi / 12, origin=(0, 0), use_radians=True), 0, M['CD'])
    g = affinity.rotate(gg, -a / 4, origin=(0, 0), use_radians=True)
    if p.intersection(g).area > 0.01: gear_ok = False
    gear_min = min(gear_min, p.distance(g))
# frames must stay clear of the legs' joints' pins? frames are on their own layers; check ground clearance instead
frame_low = trimesh.load(os.path.join(D, 'frame-plain-Plo-Phi.stl')).bounds[0][1]
gear_low = -gg.bounds[3]
print('meshes closed:', all(closed.values()), [k for k, v in closed.items() if not v])
print('problems:', len(problems), problems[:8])
print('min gap on a shared layer (mm):', {f'{a}/{b}': round(v, 1) for (a, b), v in min_gap.items()})
print(f'ground: foot lowest {foot_low:.1f}; legs otherwise {other_low:.1f}; frames {frame_low:.1f}; big gear {gear_low:.1f} (y, axle = 0)')
print('gears mesh without overlap:', gear_ok, ' smallest gap', round(gear_min, 2))
