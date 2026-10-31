# Pocket Jansen leg: one plate, snap pins, no screws, no motor. Turn the wheel with a thumb and the foot walks.
#   python3 sims/strandbeest-print/pocket.py [--scale 0.8]      -> teardown-out/print/pocket-leg/
# Same linkage as the simulator (jansen.js), same snap pins as the walker. The layers are searched so that, over a
# full turn, no two parts on a layer overlap and no pin passes through a part that is not on it.
import math, os, sys, json, itertools
import numpy as np, trimesh
from manifold3d import Manifold
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0]] + (['--scale', sys.argv[sys.argv.index('--scale') + 1]] if '--scale' in sys.argv else ['--scale', '0.8'])
import walker as W
from walker_layers import PARTS, solve, outline, sat, dist

S = W.S; R = W.R; T = W.T; PITCH = W.PITCH; GAP = W.GAP
WHEEL_R = W.HOLY['m'] * S + R + 6.5
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'teardown-out', 'print', 'pocket-leg')

# ---------------------------------------------------------------- layer search: frame 0 (the grip), wheel and parts 1..K
legs = PARTS[1:]
ALL = [dict(name='frame', joints=['O', 'P'])] + [dict(name='wheel', joints=['O', 'A'])] + legs
GRIP = [(-W.J0['P'][0] * 0 + 18, -6), (55, -6)]  # the handle runs back from O, away from the leg
def out_of(p, J):
    if p['name'] == 'wheel': return [(J['O'][0] + WHEEL_R * math.cos(2 * math.pi * i / 36), J['O'][1] + WHEEL_R * math.sin(2 * math.pi * i / 36)) for i in range(36)]
    if p['name'] == 'frame':
        pts = [q for k in ('O', 'P') for q in [(J[k][0] + 7 * math.cos(a), J[k][1] + 7 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]]
        pts += [(x + 9 * math.cos(a), y + 9 * math.sin(a)) for x, y in [(30, -2), (62, -2)] for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        from walker_layers import hull
        return hull(pts)
    return outline(p, J, R)
n = len(ALL); clash = [[False] * n for _ in range(n)]; hit = {k: set() for k in 'OABCDEP'}
for s in range(360):
    J = solve(2 * math.pi * s / 360, S)
    o = [out_of(p, J) for p in ALL]
    for a in range(n):
        for b in range(a + 1, n):
            if not clash[a][b] and sat(o[a], o[b], 0.6): clash[a][b] = clash[b][a] = True
        for k in hit:
            if k not in ALL[a]['joints'] and dist(o[a], J[k]) < W.HOLE / 2 + 0.6: hit[k].add(a)
best = None
for K in range(2, 7):
    for lay in itertools.product(range(1, K + 1), repeat=n - 1):
        L = (0,) + lay
        if any(clash[a][b] and L[a] == L[b] for a in range(n) for b in range(a + 1, n)): continue
        ok = True; span = 0
        for k in hit:
            mem = [i for i, p in enumerate(ALL) if k in p['joints'] and not (k == 'F')]
            ls = sorted(L[i] for i in mem)
            if len(set(ls)) != len(ls) or any(ls[0] <= L[i] <= ls[-1] for i in hit[k]): ok = False; break
            span += ls[-1] - ls[0]
        if ok and (best is None or span < best[0]): best = (span, L)
    if best: break
LAY = {p['name']: l for p, l in zip(ALL, best[1])}
print('layers', LAY)

# ---------------------------------------------------------------- parts
J0 = W.J0
def cbs(name):
    out = []
    for k in 'OABCDEP':
        mem = [p['name'] for p in ALL if k in p['joints'] and k != 'F']
        if name not in mem or len(mem) < 2: continue
        ls = {m: LAY[m] for m in mem}
        if ls[name] == min(ls.values()): out.append((k, 'lo'))
        if ls[name] == max(ls.values()): out.append((k, 'hi'))
    return out
def holes(m, name, joints):
    for k in joints:
        if k == 'F': continue
        m = m - W.cyl(W.HOLE, T + 2, *J0[k], -1)
    for k, face in cbs(name):
        m = m - W.cyl(W.CB_D, W.CB_H + 0.01, *J0[k], -0.01 if face == 'lo' else T - W.CB_H)
    return m
parts = {}
for p in legs: parts[p['name']] = W.leg_part(p)  # walker's parts already carry their own counterbores...
# ...but those follow the walker's layers; rebuild them with this stack's counterbores
for p in legs:
    poly = W.shape_of(p['joints'], J0, p.get('foot'))
    if len(p['joints']) == 3:
        tri = Polygon([J0[k] for k in p['joints']]); win = tri.buffer(-(R + 2.2), join_style=2)
        if not win.is_empty and win.area > 30: poly = poly.difference(win.buffer(1.2, join_style=1))
    parts[p['name']] = holes(W.extrude(poly, T), p['name'], p['joints'])
# thumb wheel: knurled rim, the crank pin A on it
rim = Polygon([((WHEEL_R - (0.9 if (i // 3) % 2 else 0)) * math.cos(2 * math.pi * i / 240), (WHEEL_R - (0.9 if (i // 3) % 2 else 0)) * math.sin(2 * math.pi * i / 240)) for i in range(240)])
wheel = W.extrude(rim, T)
for a in (math.pi * 0.66, math.pi * 1.33):  # two windows opposite A
    aa = math.atan2(J0['A'][1], J0['A'][0]) + a
    wheel = wheel - W.cyl(WHEEL_R * 0.55, T + 2, WHEEL_R * 0.52 * math.cos(aa), WHEEL_R * 0.52 * math.sin(aa), -1)
parts['wheel'] = holes(wheel, 'wheel', ['O', 'A'])
# grip: holds O and P, a handle you can hold or hang on a keyring
O, P = J0['O'], J0['P']
grip = unary_union([LineString([O, P]).buffer(7, cap_style=1), LineString([O, (30, -2)]).buffer(7, cap_style=1),
                    LineString([(30, -2), (62, -2)]).buffer(9, cap_style=1)])
gm = W.extrude(grip, T) - W.cyl(6, T + 2, 66, -2, -1)  # keyring hole
parts['frame'] = holes(gm, 'frame', ['O', 'P'])

# pins
def span(k):
    ls = [LAY[p['name']] for p in ALL if k in p['joints'] and k != 'F']
    return (max(ls) - min(ls)) * PITCH + T
PINS = {}
for k in 'OABCDEP':
    PINS.setdefault(round(span(k), 1), []).append(k)
washers = []
for k in 'OABCDEP':
    ls = sorted(LAY[p['name']] for p in ALL if k in p['joints'])
    washers += [(k, l) for l in range(ls[0] + 1, ls[-1]) if l not in ls]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.stl'): os.remove(os.path.join(OUT, f))
    meshes = []
    def tm(man): mm = man.to_mesh(); return trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts)
    for nme, man in parts.items():
        t = tm(man); t.export(os.path.join(OUT, nme + '.stl')); meshes.append((nme, t))
    for sp, ks in PINS.items():
        t = tm(W.pin(sp)); nme = f'pin-{sp}mm-{"".join(ks)}'
        for _ in ks: meshes.append((nme, t))
        t.export(os.path.join(OUT, nme + '.stl'))
    for k, l in washers:
        t = tm(W.washer()); meshes.append(('washer', t))
    # one plate: lay everything out in a row/grid
    x = y = rowh = 0; placed = []
    for nme, t in sorted(meshes, key=lambda q: -q[1].extents[1]):
        c = t.copy(); c.apply_translation(-c.bounds[0])
        if x + c.extents[0] > 175: x = 0; y += rowh + 3; rowh = 0
        c.apply_translation([x + 3, y + 3, 0]); placed.append(c); x += c.extents[0] + 3; rowh = max(rowh, c.extents[1])
    plate = trimesh.util.concatenate(placed); plate.export(os.path.join(OUT, 'pocket-leg-plate.stl'))
    json.dump(dict(layers=LAY, S=S, T=T, GAP=GAP, PITCH=PITCH, wheel_r=WHEEL_R, pins={str(k): v for k, v in PINS.items()}, washers=washers),
              open(os.path.join(OUT, 'pocket.json'), 'w'), indent=1)
    vol = sum(t.volume for _, t in meshes)
    print(f'plate {plate.extents[0]:.0f} x {plate.extents[1]:.0f} mm, {len(meshes)} pieces, {vol/1000:.1f} cm3, all closed: {all(t.is_watertight for _, t in meshes)}')
    print('pins', PINS, 'washers', washers)
