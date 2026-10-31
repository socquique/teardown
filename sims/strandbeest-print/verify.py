# usage: python3 sims/strandbeest-print/verify.py teardown-out/print/strandbeest-leg   (needs: pip install trimesh shapely)
# Independent check of the printed leg: own Jansen solver, real STL outlines, every degree of the crank.
import json, math, sys, numpy as np, trimesh
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
D = sys.argv[1]
L = json.load(open(f'{D}/layers.json'))
S = L['scale']
H = dict(a=38, b=41.5, c=39.3, d=40.1, e=55.8, f=39.4, g=36.7, h=65.7, i=49, j=50, k=61.9, l=7.8, m=15)
def cc(p0, r0, p1, r1):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; d = math.hypot(dx, dy)
    a = (r0*r0 - r1*r1 + d*d)/(2*d); h = math.sqrt(max(0, r0*r0 - a*a))
    mx, my = p0[0]+a*dx/d, p0[1]+a*dy/d
    return (mx + h*dy/d, my - h*dx/d), (mx - h*dy/d, my + h*dx/d)
def solve(th):
    P = (-H['a'], -H['l']); A = (H['m']*math.cos(th), H['m']*math.sin(th))
    B = max(cc(A, H['j'], P, H['b']), key=lambda q: q[1])
    C = min(cc(A, H['k'], P, H['c']), key=lambda q: q[1])
    Dd = min(cc(B, H['e'], P, H['d']), key=lambda q: q[0])
    E = min(cc(Dd, H['f'], C, H['g']), key=lambda q: q[0])
    F = min(cc(E, H['h'], C, H['i']), key=lambda q: q[1])
    J = dict(O=(0, 0), P=P, A=A, B=B, C=C, D=Dd, E=E, F=F)
    return {k: (v[0]*S, v[1]*S) for k, v in J.items()}
names = {'frame': '01', 'crank': '02', 'link-j': '03', 'link-k': '04', 'link-c': '05', 'link-f': '06', 'triangle-upper': '07', 'triangle-foot': '08'}
J0 = solve(0)
shapes, closed = {}, {}
for n, num in names.items():
    m = trimesh.load(f'{D}/{num}-{n}.stl'); m.merge_vertices()
    closed[n] = m.is_watertight and m.is_volume
    sec = m.section(plane_origin=[0, 0, 1.5], plane_normal=[0, 0, 1])
    g = Polygon()
    for loop in sec.discrete:
        g = g.symmetric_difference(Polygon(loop[:, :2]).buffer(0))
    shapes[n] = g
def place(n, J):
    js = L['joints'][n]
    if n == 'frame': return shapes[n]
    o0 = J0[js[0]]; p0 = J0[js[1]]; o = J[js[0]]; p = J[js[1]]
    rot = math.atan2(p[1]-o[1], p[0]-o[0]) - math.atan2(p0[1]-o0[1], p0[0]-o0[0])
    g = affinity.rotate(shapes[n], rot, origin=(0, 0), use_radians=True)
    return affinity.translate(g, o[0], o[1])
# rigidity: every joint of each part lands where the solver puts it, at every angle
worst_rig, worst_overlap, problems = 0, 0, []
lay = L['layers']
joints = sorted({k for js in L['joints'].values() for k in js if k != 'F'})
for deg in range(360):
    J = solve(math.radians(deg))
    for n in names:
        if n == 'frame': continue
        js = L['joints'][n]; o0 = J0[js[0]]; p0 = J0[js[1]]; o = J[js[0]]; p = J[js[1]]
        rot = math.atan2(p[1]-o[1], p[0]-o[0]) - math.atan2(p0[1]-o0[1], p0[0]-o0[0])
        for k in js:
            x, y = J0[k][0]-o0[0], J0[k][1]-o0[1]
            q = (o[0] + x*math.cos(rot) - y*math.sin(rot), o[1] + x*math.sin(rot) + y*math.cos(rot))
            worst_rig = max(worst_rig, math.dist(q, J[k]))
    placed = {n: place(n, J) for n in names}
    ns = list(names)
    for i in range(len(ns)):
        for j in range(i+1, len(ns)):
            if lay[ns[i]] == lay[ns[j]]:
                a = placed[ns[i]].intersection(placed[ns[j]]).area
                if a > 0.01: problems.append((deg, 'overlap', ns[i], ns[j], round(a, 2)))
    for k in joints:
        mem = [n for n in names if k in L['joints'][n]]
        ls = [lay[n] for n in mem]; lo, hi = min(ls), max(ls)
        for n in names:
            if n in mem: continue
            pt = Point(J[k])
            if lo <= lay[n] <= hi and placed[n].distance(pt) < L['pinR']: problems.append((deg, 'screw', k, n))
            if (lay[n] == hi+1 or (lo > 0 and lay[n] == lo-1)) and placed[n].distance(pt) < L['headR']: problems.append((deg, 'head/nut', k, n))
print('meshes closed:', all(closed.values()), {k: v for k, v in closed.items() if not v})
print('rigidity error max (mm):', round(worst_rig, 6))
print('problems:', len(problems)); print(problems[:10])
# clearance margin: smallest gap on the same layer over the turn
mins = {}
for deg in range(0, 360, 2):
    J = solve(math.radians(deg)); placed = {n: place(n, J) for n in names}
    for a in names:
        for b in names:
            if a < b and lay[a] == lay[b]:
                d = placed[a].distance(placed[b]); mins[(a, b)] = min(mins.get((a, b), 1e9), d)
print('min gap on shared layers (mm):', {f'{a}/{b}': round(d, 2) for (a, b), d in mins.items()})
tot = sum(trimesh.load(f'{D}/{num}-{n}.stl').volume for n, num in names.items())
print('plastic cm3 (solid):', round(tot/1000, 1))
