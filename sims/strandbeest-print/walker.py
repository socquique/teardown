# A 12-leg Strandbeest that walks on the Bambu TT motor (LA001, the one in the Marble Run kit 003), printed with
# no screws: every joint is a printed snap pin. The linkage is the one the simulator solves (jansen.js).
#
#   python3 sims/strandbeest-print/walker.py            # teardown-out/print/strandbeest-walker/
#   python3 sims/strandbeest-print/walker.py --flat 3.95 # D-shaft fit of the pinion, from the motor test piece
#
# Layout along the axle (z):  F0 |M1| F1 |M2| F2 |M3| F3 [gear] F4 [motor] F5 |M4| F6 |M5| F7 |M6| F8
# Each module M: web | leg (3 layers) | mirrored leg (the same parts turned round) | web, on one crank pin.
# The webs and hex couplers make a crankshaft; modules sit 120° apart on each side, 60° between sides,
# so the beast always has at least three feet down (checked in gait). The TT motor drives it through 12:48 gears.
import math, os, sys, json
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection, Mesh
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from walker_layers import HOLY, PARTS, solve, search_crankshaft

ARGS = sys.argv[1:]
def arg(k, d): return float(ARGS[ARGS.index(k) + 1]) if k in ARGS else d

S = arg('--scale', 1.0)          # mm per Jansen unit
T = 3.0                          # plate thickness
GAP = 0.4                        # air between layers
PITCH = T + GAP
R = 5.5                          # radius round each joint
PIN = 4.0                        # pin diameter
HOLE = 4.4                       # hole for a pin (turns freely)
CB_D, CB_H = 6.8, 1.4            # counterbore for pin head / barb
HEX = 6.0                        # crankshaft hex, across flats
HEX_HOLE = 6.3
AXLE_ROUND = 7.0                 # round part of the couplers, inside the frames
AXLE_HOLE = 7.4
FLAT = arg('--flat', 3.95)       # pinion D-hole flats (motor test: A 3.85, B 3.95, C 4.05)
GEAR_M, Z1, Z2 = 1.25, 12, 48    # 4:1, 59 rpm -> ~15 rpm
CD = GEAR_M * (Z1 + Z2) / 2      # 37.5 mm, motor shaft above the axle
SEG = 64
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'teardown-out', 'print', 'strandbeest-walker')

# ---------------------------------------------------------------- layers of one module
LAY = search_crankshaft(S, R, HOLE / 2)
assert 'layers' in LAY, LAY
L = LAY['layers']; K = LAY['K']               # leg parts on layers 2..K+1 (L half)
NL = 2 * K + 2                                # module inner layers: web(1) .. web(NL)
# layer index of every part in a module, both halves (M half = L half turned round)
def mod_layers():
    out = {'web_a': 1, 'web_b': NL}
    for n, l in L.items():
        if n == 'frame': continue
        out['L:' + n] = l
        out['M:' + n] = NL + 1 - l
    return out
ML = mod_layers()
MOD_W = NL * PITCH + T + GAP                 # module + one frame
z_layer = lambda l: (l - 1) * PITCH          # z of layer l's low face, from the low frame's high face + GAP

# ---------------------------------------------------------------- 2D helpers
def circ(c, r, n=SEG): return Point(c).buffer(r, n // 4)
def shape_of(joints, J, foot=None, extra=()):
    return unary_union([circ(J[k], R * 1.3 if k == foot else R) for k in joints] + list(extra)).convex_hull
def to_cs(poly):
    from shapely.geometry.polygon import orient
    polys = [poly] if poly.geom_type == 'Polygon' else list(poly.geoms)
    polys = [orient(q, 1.0) for q in polys]
    loops = []
    for p in polys:
        loops.append(list(p.exterior.coords)[:-1])
        loops += [list(i.coords)[:-1] for i in p.interiors]
    return CrossSection(loops)
def extrude(poly, h, z=0): return Manifold.extrude(to_cs(poly), h).translate([0, 0, z])
def cyl(d, h, x=0, y=0, z=0, seg=SEG): return Manifold.cylinder(h, d / 2, d / 2, seg).translate([x, y, z])
def hexp(af, h, x=0, y=0, z=0, rot=0):
    r = af / math.sqrt(3)
    pts = [(x + r * math.cos(rot + i * math.pi / 3), y + r * math.sin(rot + i * math.pi / 3)) for i in range(6)]
    return extrude(Polygon(pts), h, z)

# ---------------------------------------------------------------- leg parts (L half, local frame = pose θ=0)
J0 = solve(0, S)
JOINT_MEMBERS = {}
for p in PARTS[1:]:
    for k in p['joints']:
        if k != p.get('foot'): JOINT_MEMBERS.setdefault(k, []).append(p['name'])
JOINT_MEMBERS['A'] = ['link-j', 'link-k']; JOINT_MEMBERS['P'] = JOINT_MEMBERS['P'] + ['frame']
def lay_of(n): return 0 if n == 'frame' else L[n]
def cb_faces(name):
    """(joint, face) pairs where this part carries a counterbore: 'lo' = towards the frame, 'hi' = towards the centre."""
    out = []
    for k, mem in JOINT_MEMBERS.items():
        if k == 'A' or name not in mem: continue
        ls = {m: lay_of(m) for m in mem}
        if ls[name] == min(ls.values()): out.append((k, 'lo'))
        if ls[name] == max(ls.values()): out.append((k, 'hi'))
    return out

def leg_part(p):
    name = p['name']; js = p['joints']
    poly = shape_of(js, J0, p.get('foot'))
    if len(js) == 3:  # lighten the triangles: a window inset from the joints
        tri = Polygon([J0[k] for k in js])
        win = tri.buffer(-(R + 2.2), join_style=2)
        if not win.is_empty and win.area > 30: poly = poly.difference(win.buffer(1.2, join_style=1))
    m = extrude(poly, T)
    for k in js:
        if k == p.get('foot'): continue
        m = m - cyl(HOLE, T + 2, *J0[k], -1)
    for k, face in cb_faces(name):
        m = m - cyl(CB_D, CB_H + 0.01, *J0[k], -0.01 if face == 'lo' else T - CB_H)
    if p.get('foot'):  # a grippy pad: small ridges on the sole
        pass
    return m

def web():
    """crank arm: hex socket at O, pin hole at A (counterbored on the outer face, 'lo')."""
    poly = shape_of(['O', 'A'], J0, extra=[circ(J0['O'], R + 1.5)])
    m = extrude(poly, T) - hexp(HEX_HOLE, T + 2, *J0['O'], -1, rot=math.pi / 6)
    m = m - cyl(HOLE, T + 2, *J0['A'], -1) - cyl(CB_D, CB_H + 0.01, *J0['A'], -0.01)
    # assembly mark: a notch on the edge in line with a hex flat, so 120° steps are easy to count
    return m

# ---------------------------------------------------------------- pins
def pin(span):
    """snap pin for a stack of `span` mm: head in one counterbore, split barb in the other; lies flat to print."""
    L_ = span - 0.2
    head = cyl(CB_D - 0.4, CB_H - 0.2, 0, 0, 0)
    shank = cyl(PIN, L_, 0, 0, 0)
    lip_z = L_ - (CB_H - 0.1)
    lip = Manifold.cylinder(CB_H - 0.2, (HOLE + 0.6) / 2, PIN / 2 - 0.2, SEG).translate([0, 0, lip_z])
    m = head + shank + lip
    slot_len = min(6.0, L_ - CB_H - 1.0)
    m = m - Manifold.cube([1.2, PIN + 4, slot_len + 1]).translate([-0.6, -(PIN + 4) / 2, L_ - slot_len])
    # lie it down on a flat: rotate so the axis is along x, then shave 0.3 mm off the bottom
    m = m.rotate([0, 90, 0])
    bb = m.bounding_box()
    m = m - Manifold.cube([L_ + 10, 20, 10]).translate([bb[0] - 5, -10, bb[2] - 10 + 0.3])
    return m

def washer():
    return cyl(HOLE + 3.6, T, 0, 0, 0) - cyl(HOLE + 0.3, T + 2, 0, 0, -1)

# ---------------------------------------------------------------- gears (involute, FDM backlash)
def involute_gear(z, m, shift=0.0, backlash=0.3, n_inv=10):
    pa = math.radians(20)
    rp = m * z / 2; rb = rp * math.cos(pa); ra = rp + m * (1 + shift); rf = rp - m * (1.25 - shift)
    # tooth half-thickness angle at pitch circle (with shift, minus backlash)
    s = m * (math.pi / 2 + 2 * shift * math.tan(pa)) - backlash
    inv = lambda a: math.tan(a) - a
    half = s / (2 * rp) + inv(pa)
    pts = []
    for i in range(z):
        c = 2 * math.pi * i / z
        flank = []
        for t in np.linspace(0, 1, n_inv):
            r = max(rb, rf) + (ra - max(rb, rf)) * t
            a = math.acos(min(1, rb / r))
            flank.append((r, half - inv(a)))
        left = [(r * math.cos(c - th), r * math.sin(c - th)) for r, th in flank]
        right = [(r * math.cos(c + th), r * math.sin(c + th)) for r, th in reversed(flank)]
        root_a = c + 2 * math.pi / z / 2
        pts += [(rf * math.cos(c - half - 0.04), rf * math.sin(c - half - 0.04))] + left + right
        pts += [(rf * math.cos(c + half + 0.04), rf * math.sin(c + half + 0.04))]
    return Polygon(pts).buffer(0)

def pinion(width):
    g = extrude(involute_gear(Z1, GEAR_M, shift=0.3), width)
    d = cyl(5.6, width + 2, 0, 0, -1) ^ Manifold.cube([FLAT, 8, width + 2]).translate([-FLAT / 2, -4, -1])
    return g - d - cyl(2.2, width + 2, 0, 0, -1)

def big_gear(width):
    g = extrude(involute_gear(Z2, GEAR_M, shift=-0.3), width)
    g = g - hexp(HEX_HOLE, width + 2, 0, 0, -1, rot=math.pi / 6)
    for i in range(6):  # spokes: lighten
        a = 2 * math.pi * i / 6 + math.pi / 6
        g = g - cyl(13, width + 2, 17 * math.cos(a), 17 * math.sin(a), -1)
    return g

# ---------------------------------------------------------------- couplers (crankshaft between modules)
def coupler(parts):
    """parts: list of ('hex'|'round'|'cap', length) along +z; printed standing on its first section."""
    m = None; z = 0
    for kind, ln in parts:
        if kind == 'hex': s = hexp(HEX - 0.1, ln, 0, 0, z, rot=math.pi / 6)
        elif kind == 'round': s = cyl(AXLE_ROUND, ln, 0, 0, z)
        else: s = cyl(11, ln, 0, 0, z)
        m = s if m is None else m + s
        z += ln
    return m

# ---------------------------------------------------------------- frames
RAIL_Y = 56.0 * S
RAIL_X = 42.0
RAIL_W, RAIL_H = 6.0, 8.0
MOTOR_SLAB = 18.8 - 0.8 + 0.2  # the back frame has a 0.8 pocket for the gearbox
GEAR_SLAB = 0.4 + 4.6 + 0.4
def frame(p_lo, p_hi, kind='plain'):
    """A truss plate between two modules: bearing for the crankshaft at O, the fixed pivot P of the leg on its high
    side (head counterbored in the low face) and P' of the mirrored leg on its low side, and two closed holes for the
    rails. Motor frames add a plate round the motor's features."""
    from shapely.geometry import LineString
    J = J0; O = J['O']; P = J['P']; Pm = (-P[0], P[1])
    RL = (-RAIL_X, RAIL_Y); RR = (RAIL_X, RAIL_Y)
    bars = [(O, P), (O, Pm), (P, RL), (Pm, RR), (RL, RR), (O, RL), (O, RR), (P, Pm)]
    poly = unary_union([LineString([a, b]).buffer(4.5, cap_style=1) for a, b in bars] +
                       [circ(O, 9), circ(P, 7), circ(Pm, 7), Point(RL).buffer(7.5, cap_style=3), Point(RR).buffer(7.5, cap_style=3)])
    if kind in ('motor', 'motor_back'):
        poly = unary_union([poly, Polygon([(-16, CD - 14), (16, CD - 14), (16, CD + 36), (-16, CD + 36)]),
                            LineString([(-16, CD + 36), RL]).buffer(4.5), LineString([(16, CD + 36), RR]).buffer(4.5)])
    m = extrude(poly, T)
    m = m - cyl(AXLE_HOLE, T + 2, *O, -1)
    for x in (-RAIL_X, RAIL_X):
        m = m - Manifold.cube([RAIL_W + 0.3, RAIL_H + 0.3, T + 2]).translate([x - (RAIL_W + 0.3) / 2, RAIL_Y - (RAIL_H + 0.3) / 2, -1])
    if p_hi:
        m = m - cyl(HOLE, T + 2, *P, -1) - cyl(CB_D, CB_H + 0.01, *P, -0.01)
    if p_lo:
        m = m - cyl(HOLE, T + 2, *Pm, -1) - cyl(CB_D, CB_H + 0.01, *Pm, T - CB_H)
    if kind == 'motor':
        m = m - cyl(9.0, T + 2, 0, CD, -1) - cyl(4.1, T + 2, 0, CD + 11.15, -1)
        m = m - Manifold.cube([4.6, 5.6, T + 2]).translate([-2.3, CD + 30.7 - 2.8, -1])
        m = m - cyl(13, T + 2, 0, CD + 21, -1)  # lighten between pin and bump
    if kind == 'motor_back':
        m = m - Manifold.cube([22.8, 48.8, 0.8]).translate([-11.4, CD - 11.4, -0.001])
        m = m - Manifold.cube([4.6, 5.6, T + 2]).translate([-2.3, CD + 30.7 - 2.8, -1])  # the bump under the motor
    return m

def rail(total):
    """6 x 8 bar through the frames' rail holes, with a head at one end."""
    m = Manifold.cube([RAIL_W, RAIL_H, total + 4]).translate([-RAIL_W / 2, -RAIL_H / 2, 0])
    m = m + Manifold.cube([RAIL_W + 5, RAIL_H + 5, 2]).translate([-(RAIL_W + 5) / 2, -(RAIL_H + 5) / 2, -2])
    return m.rotate([0, 90, 0])

# ---------------------------------------------------------------- build the stack
def build():
    parts = {}
    for p in PARTS[1:]: parts[p['name']] = leg_part(p)
    parts['web'] = web()
    parts['washer'] = washer()
    # z layout
    zs = []; z = 0.0
    sections = ['mod', 'mod', 'mod', 'gear', 'motor', 'mod', 'mod', 'mod']
    zframes = [0.0]
    for s in sections:
        w = NL * PITCH + GAP if s == 'mod' else (GEAR_SLAB if s == 'gear' else MOTOR_SLAB)
        z = zframes[-1] + T + w
        zframes.append(z)
    return parts, sections, zframes

PARTS3D, SECTIONS, ZF = build()

# pin spans (mm, outer face to outer face) per joint
def span(lo, hi): return (hi - lo) * PITCH + T
PINS = {}
for k, mem in JOINT_MEMBERS.items():
    if k == 'A': continue
    ls = [lay_of(m) for m in mem]
    PINS[k] = span(min(ls), max(ls))
PINS['A'] = span(1, NL)
WASHERS_PER_MODULE = 0
for k, mem in list(JOINT_MEMBERS.items()):
    ls = sorted(lay_of(m) for m in mem) if k != 'A' else sorted([1, NL] + [ML['L:' + m] for m in mem] + [ML['M:' + m] for m in mem])
    gaps = [l for l in range(ls[0] + 1, ls[-1]) if l not in ls and not (k == 'P' and l == 1)]
    # P: layer 1 is the web's layer, the web never reaches P, so that gap needs a washer too
    if k == 'P': gaps = [l for l in range(ls[0] + 1, ls[-1]) if l not in ls]
    WASHERS_PER_MODULE += len(gaps) * (1 if k == 'A' else 2)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.stl'): os.remove(os.path.join(OUT, f))
    def save(name, man):
        mm = man.to_mesh(); t = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts)
        t.export(os.path.join(OUT, name + '.stl')); return t
    counts = {}
    for n in ['link-j', 'link-k', 'link-c', 'link-f', 'tri-upper', 'tri-foot']:
        counts[n] = 12
    counts['web'] = 12
    counts['washer'] = WASHERS_PER_MODULE * 6
    info = {}
    for n, man in PARTS3D.items():
        t = save(n, man); info[n] = t
    by_len = {}
    for k, sp in PINS.items(): by_len.setdefault(round(sp, 1), []).append(k)
    for sp, ks in sorted(by_len.items()):
        n = f'pin-{sp:.1f}mm-' + ''.join(sorted(ks))
        t = save(n, pin(sp)); info[n] = t
        counts[n] = sum({'A': 6}.get(k, 12) for k in ks)
    # frames
    fr = []
    for i, z in enumerate(ZF):
        below = SECTIONS[i - 1] if i > 0 else None
        above = SECTIONS[i] if i < len(SECTIONS) else None
        kind = 'motor' if (below == 'gear' and above == 'motor') else ('motor_back' if below == 'motor' else 'plain')
        fr.append((i, z, below == 'mod', above == 'mod', kind))
    fkinds = {}
    for i, z, lo, hi, kind in fr:
        key = (lo, hi, kind)
        fkinds.setdefault(key, []).append(i)
    for (lo, hi, kind), idx in fkinds.items():
        n = f'frame-{kind}' + ('-Plo' if lo else '') + ('-Phi' if hi else '')
        t = save(n, frame(lo, hi, kind)); info[n] = t; counts[n] = len(idx)
    # gears and couplers
    info['pinion'] = save('pinion', pinion(4.6)); counts['pinion'] = 1
    info['gear-48'] = save('gear-48', big_gear(4.6)); counts['gear-48'] = 1
    c_mod = coupler([('hex', T - 0.2), ('round', T + 2 * GAP), ('hex', T - 0.2)])
    info['coupler'] = save('coupler', c_mod); counts['coupler'] = 4
    c_end = coupler([('cap', 1.6), ('round', T + 2 * GAP), ('hex', T - 0.2)])
    info['coupler-end'] = save('coupler-end', c_end); counts['coupler-end'] = 2
    c_g1 = coupler([('hex', T - 0.2), ('round', T + 2 * GAP), ('hex', 2.2)])
    info['coupler-gear-short'] = save('coupler-gear-short', c_g1); counts['coupler-gear-short'] = 1
    c_g2 = coupler([('hex', 2.2), ('round', GAP + T + MOTOR_SLAB + T + GAP), ('hex', T - 0.2)])
    info['coupler-gear-long'] = save('coupler-gear-long', c_g2); counts['coupler-gear-long'] = 1
    info['rail'] = save('rail', rail(ZF[-1] + T)); counts['rail'] = 2
    meta = dict(S=S, T=T, GAP=GAP, PITCH=PITCH, R=R, layers=ML, K=K, NL=NL, ZF=ZF, sections=SECTIONS, pins=PINS,
                counts=counts, CD=CD, rail=[RAIL_X, RAIL_Y, RAIL_W, RAIL_H], motor_slab=MOTOR_SLAB, gear_slab=GEAR_SLAB,
                joints={p['name']: p['joints'] for p in PARTS}, holy=HOLY)
    json.dump(meta, open(os.path.join(OUT, 'walker.json'), 'w'), indent=1)
    tot = 0
    for n, t in info.items():
        c = counts.get(n, 1); tot += t.volume * c
        if t.extents is None: print("EMPTY", n); continue
        print(f"{n:28s} x{c:<3d} {t.extents[0]:6.1f} x {t.extents[1]:6.1f} x {t.extents[2]:5.1f} mm  closed={t.is_watertight}")
    print(f'plastic (solid) {tot/1000:.0f} cm3, overall width {ZF[-1]+T:.0f} mm')
