# Four desk objects with a reason to exist, each checked over its motion before printing.
#   python3 sims/strandbeest-print/objects.py [wave|orrery|flower|calendar ...]  -> teardown-out/print/objects/
#
#   wave      24 slats on a camshaft of eccentrics make a sea wave that rolls forever, driven by the Bambu TT motor
#             through 12:60 gears (about 12 waves a minute). Flat-faced followers on eccentrics: a pure sine.
#   orrery    Sun, Earth and Moon: one turn of the crank is a year, and the Moon goes round 12.36 times relative to
#             the Sun-Earth line (true value 12.37), so its phases come out right.
#   flower    Push the stem and eight petals open; let go and they close.
#   calendar  Day, month and weekday rings on one core, printed in place, clicking into place at each value.
import math, os, sys, json, itertools
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fidgets as F
from fidgets import cs, ext, cyl, disc, rot, to_tm, gear_poly, PIP

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'teardown-out', 'print', 'objects')
SEG = 96

def box(x0, x1, y0, y1, z0, z1): return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
def text_poly(s, size, xy=(0, 0), font='DejaVu Sans', weight='bold', anchor='c'):
    """outline of a string as shapely polygons (matplotlib's TextPath), centred at xy."""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    tp = TextPath((0, 0), s, size=size, prop=FontProperties(family=font, weight=weight))
    polys = []
    for verts in tp.to_polygons():
        if len(verts) >= 3: polys.append(Polygon(verts).buffer(0))
    g = Polygon()
    for p in sorted(polys, key=lambda q: -q.area): g = g.symmetric_difference(p)
    b = g.bounds
    dx = xy[0] - (b[0] + b[2]) / 2 if anchor == 'c' else xy[0] - b[0]
    return affinity.translate(g, dx, xy[1] - (b[1] + b[3]) / 2)
def d_hole(r, flat, angle_deg, h, z=-1):
    """a D-shaped hole: round radius r with one flat at distance `flat` from the centre, turned by angle."""
    m = cyl(r, h, 0, 0, z) ^ box(-r - 1, flat, -r - 1, r + 1, z - 1, z + h + 1)
    return m.rotate([0, 0, angle_deg])

# ====================================================================== WAVE
def wave():
    N = 24; P = 4.2; CAM_T = 4.0; SLAT_T = 3.0
    rc, e = 10.0, 5.0                                   # cam radius and eccentricity: 10 mm of lift
    WAVES = 1.25                                        # wavelengths along the row
    AX = 36.0                                           # shaft axis height (the 60-tooth gear clears the base)
    BASE = 3.0
    SH_R, SH_FLAT = 3.5, 2.5                            # D-shaft
    X0, X1 = -CAM_T / 2, (N - 1) * P + CAM_T / 2        # cam stack
    WALL = 4.0; WG = 0.6
    xl, xr = X0 - WG - WALL, X1 + WG                    # wall low faces
    FOOT_W, FOOT_H, BLADE_W, H_SLAT = 14.0, 2.5, 6.0, 72.0
    foot_lo = AX + rc - e                               # lowest foot bottom
    C1 = AX + rc + e + FOOT_H + 3.0 + 1.5               # lower comb bottom: clear of the foot and its taper at full lift
    C2 = C1 + 34.0                                      # upper comb bottom
    CT = 3.0
    M_, Z1, Z2 = 1.0, 12, 60
    CD = M_ * (Z1 + Z2) / 2                             # 36 mm: pinion behind the shaft at the same height
    phase = lambda i: 360.0 * WAVES * i / N
    # --- camshaft (D) printed lying on its flat, cams with numbered D-holes
    SH_L = (xr + WALL + 1 + 5.0 + 1.0) - (xl - 3.0)     # through both walls, the gear, a collar
    shaft = (cyl(SH_R, SH_L) ^ box(-SH_R - 1, SH_FLAT, -SH_R - 1, SH_R + 1, -1, SH_L + 1)).rotate([0, 90, 0]).translate([xl - 3.0, 0, AX])
    def cam(i):
        g = disc(rc, (e, 0))
        lab = text_poly(str(i + 1), 4.2, (e + 4.6, 0))
        m = ext(g, CAM_T) - d_hole(SH_R + 0.25, SH_FLAT + 0.25, -phase(i) + 0, CAM_T + 2) - ext(lab, 0.6, CAM_T - 0.6)
        return m  # local: axis at origin, z = thickness; eccentric towards +x at phase 0
    cams = [cam(i) for i in range(N)]
    # --- slat: foot, blade, a crest on top (local: foot bottom at z = 0, centred on x = 0, y = 0)
    crest = unary_union([Point(0, H_SLAT - 4).buffer(4.2), Polygon([(-3, H_SLAT - 8), (3, H_SLAT - 8), (3, H_SLAT - 4), (-3, H_SLAT - 4)]),
                         Point(2.6, H_SLAT + 0.6).buffer(2.2)]).difference(Point(4.8, H_SLAT - 1.6).buffer(2.0))
    slat2d = unary_union([Polygon([(-FOOT_W / 2, 0), (FOOT_W / 2, 0), (FOOT_W / 2, FOOT_H), (BLADE_W / 2, FOOT_H + 3),
                                   (BLADE_W / 2, H_SLAT - 6), (-BLADE_W / 2, H_SLAT - 6), (-BLADE_W / 2, FOOT_H + 3), (-FOOT_W / 2, FOOT_H)]), crest])
    slat = ext(slat2d, SLAT_T).rotate([90, 0, 0]).rotate([0, 0, 90]).translate([-SLAT_T / 2, 0, 0])  # profile in yz, thickness in x
    # --- combs: teeth with open slots, the lower one open to the back, the upper one to the front
    def comb(z, open_back):
        L = (xr + WALL + 2) - (xl - 2)
        m = box(xl - 2, xr + WALL + 2, -9.0, 9.0, z, z + CT)
        for i in range(N):
            x = i * P
            if open_back: m = m - box(x - SLAT_T / 2 - 0.35, x + SLAT_T / 2 + 0.35, -BLADE_W / 2 - 0.5, 20, z - 1, z + CT + 1)
            else: m = m - box(x - SLAT_T / 2 - 0.35, x + SLAT_T / 2 + 0.35, -20, BLADE_W / 2 + 0.5, z - 1, z + CT + 1)
        return m
    comb_lo, comb_hi = comb(C1, True), comb(C2, False)
    # --- walls: bearing for the shaft, U-slots for the combs (open to the side each comb slides in from)
    def wall(x0, motor_side):
        m = box(x0, x0 + WALL, -16.0, 16.0, BASE, C2 + CT + 6) + box(x0, x0 + WALL, -16.0, 16.0, BASE - 2, BASE)  # tab into the base
        m = m - cyl(SH_R + 0.5, WALL + 2, 0, 0, -1).rotate([0, 90, 0]).translate([x0 - 1 + WALL + 2, 0, AX]) if False else m - Manifold.cylinder(WALL + 2, SH_R + 0.5, SH_R + 0.5, SEG).rotate([0, 90, 0]).translate([x0 - 1, 0, AX])
        m = m - box(x0 - 1, x0 + WALL + 1, -9.2, 17, C1 - 0.2, C1 + CT + 0.2)         # lower comb comes in from the back
        m = m - box(x0 - 1, x0 + WALL + 1, -17, 9.2, C2 - 0.2, C2 + CT + 0.2)         # upper comb from the front
        return m
    wl, wr = wall(xl, False), wall(xr, True)
    # --- gears outside the right wall, motor on a bracket behind
    gx = xr + WALL + 1.0
    gear = ext(gear_poly(Z2, M_, M_ * Z2 / 2 + 0.8 * M_, M_ * Z2 / 2 - 1.25 * M_ - 0.1, math.pi * M_ / 2 - 0.35), 5.0)
    gear = gear - d_hole(SH_R + 0.2, SH_FLAT + 0.2, 0, 7)
    for k in range(6):
        a = 2 * math.pi * k / 6; gear = gear - cyl(6.5, 7, 17 * math.cos(a), 17 * math.sin(a), -1)
    pin_ = ext(gear_poly(Z1, M_, M_ * Z1 / 2 + 0.8 * M_, M_ * Z1 / 2 - 1.25 * M_ - 0.1, math.pi * M_ / 2 - 0.35), 4.6)
    pin_ = pin_ - (cyl(2.8, 7, 0, 0, -1) ^ box(-1.975, 1.975, -4, 4, -2, 8))       # TT shaft: Ø5.4, flats 3.7 (+0.25)
    BR = gx + 5.0 + 0.5                                                          # motor bracket (motor's shaft face)
    # pinion: on the motor shaft through the bracket, in the gear's plane
    bracket = box(BR, BR + 3.0, CD - 14, CD + 40, BASE - 2, AX + 16)
    bracket = bracket - Manifold.cylinder(5, 4.5, 4.5, SEG).rotate([0, 90, 0]).translate([BR - 1, CD, AX])
    bracket = bracket - Manifold.cylinder(5, 2.05, 2.05, SEG).rotate([0, 90, 0]).translate([BR - 1, CD + 11.15, AX])
    bracket = bracket - box(BR - 1, BR + 4, CD + 30.7 - 2.8, CD + 30.7 + 2.8, AX - 2.3, AX + 2.3)
    MB = BR + 3.0 + 18.8 + 0.2                                                   # back plate behind the motor
    back = box(MB, MB + 3.0, CD - 14, CD + 40, BASE - 2, AX + 16)
    # mesh phase of the pinion against the gear (searched in the gear plane)
    gp = gear_poly(Z2, M_, M_ * Z2 / 2 + 0.8 * M_, M_ * Z2 / 2 - 1.25 * M_ - 0.1, math.pi * M_ / 2 - 0.35)
    pp = gear_poly(Z1, M_, M_ * Z1 / 2 + 0.8 * M_, M_ * Z1 / 2 - 1.25 * M_ - 0.1, math.pi * M_ / 2 - 0.35)
    # gear plane after rotate([0,90,0]): local (x, y) -> world (z = -x, y); the pinion sits at local x = 0, y = CD
    PH0 = max(((affinity.translate(affinity.rotate(pp, a, origin=(0, 0)), 0, CD).distance(gp)), a) for a in np.linspace(0, 30, 61))[1]
    motor_box = box(BR + 3.0, BR + 3.0 + 18.8, CD - 11.2, CD + 37.2, AX - 11.2, AX + 11.2)   # LA001 gearbox envelope
    base = box(xl - 8, MB + 3.0 + 6, -22, CD + 44, 0, BASE)
    for x0, w in ((xl, WALL), (xr, WALL), (BR, 3.0), (MB, 3.0)):
        base = base - box(x0 - 0.15, x0 + w + 0.15, -16.15 if w == WALL else CD - 14.15, 16.15 if w == WALL else CD + 40.15, BASE - 2.2, BASE + 0.1)
    collar = (cyl(SH_R + 3.5, 3) - d_hole(SH_R + 0.2, SH_FLAT + 0.2, 0, 5))
    def pose(deg):
        P_ = {'base': base, 'wall_l': wl, 'wall_r': wr, 'comb_lo': comb_lo, 'comb_hi': comb_hi, 'bracket': bracket, 'back': back,
              'motor': motor_box, 'shaft': shaft.translate([0, 0, -AX]).rotate([deg, 0, 0]).translate([0, 0, AX]),
              'gear': gear.rotate([0, 0, deg]).rotate([0, 90, 0]).translate([gx, 0, AX]),
              'pinion': pin_.rotate([0, 0, PH0 - deg * Z2 / Z1]).rotate([0, 90, 0]).translate([gx, CD, AX])}
        for i in range(N):
            ph = math.radians(phase(i) + deg)
            # cam turned with the shaft (about x), at x_i
            c = cams[i].rotate([0, 0, phase(i) + deg])     # eccentric direction in the cam's own plane
            c = c.rotate([0, 90, 0]).translate([i * P - CAM_T / 2, 0, AX])
            P_[f'cam{i}'] = c
            top = AX + rc - e * math.cos(ph)              # flat follower rests on the eccentric's top (eccentric points down at 0)
            P_[f'slat{i}'] = slat.translate([i * P, 0, top])
        return P_
    parts = {'base': base, 'wall-left': wl, 'wall-right': wr, 'comb-lower': comb_lo, 'comb-upper': comb_hi, 'motor-bracket': bracket,
             'motor-back': back, 'shaft': shaft, 'gear-60': gear, 'pinion-12': pin_, 'collar': collar, 'slat': slat}
    for i in range(N): parts[f'cam-{i+1:02d}'] = cams[i]
    pairs = [(f'slat{i}', k) for i in range(N) for k in ('comb_lo', 'comb_hi', 'wall_l', 'wall_r')] + \
            [(f'slat{i}', f'cam{j}') for i in range(N) for j in (i - 1, i + 1) if 0 <= j < N] + \
            [(f'slat{i}', f'slat{i+1}') for i in range(N - 1)] + [(f'cam{i}', k) for i in (0, N - 1) for k in ('wall_l', 'wall_r')] + \
            [('gear', 'pinion'), ('gear', 'base'), ('gear', 'wall_r'), ('gear', 'bracket'), ('pinion', 'base'), ('motor', 'base'),
             ('shaft', 'comb_lo'), ('gear', 'motor')]
    colors = {'slat': (0.18, 0.47, 0.72), 'cam': (0.93, 0.91, 0.86), 'comb': (0.95, 0.95, 0.95), 'wall': (0.25, 0.27, 0.31),
              'base': (0.25, 0.27, 0.31), 'motor': (0.91, 0.76, 0.2), 'gear': (0.82, 0.36, 0.16), 'pinion': (0.82, 0.36, 0.16),
              'bracket': (0.25, 0.27, 0.31), 'back': (0.25, 0.27, 0.31), 'shaft': (0.7, 0.7, 0.7)}
    return dict(parts=parts, pose=pose, sweep=range(0, 360, 15), pairs=pairs, colors=colors,
                note=f'{N} slats, lift {2*e:.0f} mm, {WAVES} waves along, TT 59 rpm / 5 = {59*Z1/Z2:.1f} waves per minute',
                info=dict(N=N, CD=CD, AX=AX))

# ====================================================================== ORRERY
def orrery():
    sys.argv = [sys.argv[0], '--scale', '1.0']
    import walker as W                                   # snap pins
    m = 1.0
    ZS, ZA, ZB, ZI, ZM = 60, 15, 34, 15, 11             # fixed sun gear -> a/b compound -> idler -> moon gear
    ratio = (ZS / ZA) * (ZB / ZM)                       # moon arm turns per year relative to the arm: synodic months
    def gp(z, bl=0.75): return gear_poly(z, m, m * z / 2 + 0.8 * m, m * z / 2 - 1.25 * m - 0.1, math.pi * m / 2 - bl / 2)
    BASE_T = 4.0; GT = 3.6; G = 0.4
    z1 = BASE_T + G                                     # plane 1: sun gear (fixed) and a
    z2 = z1 + GT + G                                    # plane 2: b, idler, moon gear
    za = z2 + GT + G                                    # arm plate
    AT = 3.4
    rA = m * (ZS + ZA) / 2                              # 37.5
    B = (rA, 0.0); dBI = m * (ZB + ZI) / 2; dIM = m * (ZI + ZM) / 2
    E = (rA + 25.0, 0.0)                                # Earth (moon gear) on the arm
    # idler position: circle intersection, on the +y side
    dx, dy = E[0] - B[0], E[1] - B[1]; d = math.hypot(dx, dy); aa = (dBI ** 2 - dIM ** 2 + d * d) / (2 * d); hh = math.sqrt(dBI ** 2 - aa * aa)
    I = (B[0] + aa * dx / d - hh * dy / d, B[1] + aa * dy / d + hh * dx / d)
    POST_R = 4.0
    # base: disc, the sun gear on it (fixed), the central post up to the Sun
    SUN_Z = za + AT + 26.0
    base = cyl(62, BASE_T) + ext(gp(ZS).difference(disc(POST_R + 0.01)), GT, z1 - G) + cyl(POST_R, SUN_Z - 6, 0, 0, 0)
    base = base + cyl(6.5, za - G - (z1 - G + GT) + 0.01, 0, 0, z1 - G + GT - 0.01)   # collar the arm rides on
    sun_ball = Manifold.sphere(15, SEG).translate([0, 0, 15]) - cyl(POST_R + 0.25, 10, 0, 0, -1) - box(-20, 20, -20, 20, -20, 0.6)  # flat bottom
    # arm: hub on the post, a plate out past the Earth, counterbored holes for the gear pins, a knob to push the year round
    arm2d = unary_union([disc(POST_R + 5.0), LineString([(0, 0), (E[0] + 10, 0)]).buffer(6.5), disc(8.5, B), disc(7.0, I), disc(8.0, E),
                         LineString([(0, 0), (-24, 0)]).buffer(6.0)]).difference(disc(POST_R + 0.35))
    arm = ext(arm2d, AT, za)
    for c in (B, I): arm = arm - cyl(W.HOLE / 2, AT + 2, *c, za - 1) - cyl(W.CB_D / 2, W.CB_H + 0.01, *c, za + AT - W.CB_H)
    arm = arm - cyl(3.4, AT + 2, *E, za - 1)                        # the moon gear's tube passes up through here
    arm = arm + cyl(4.2, 9.0, -24, 0, za + AT)                       # knob, on the stub opposite the Earth (clear of the Moon)
    cb_bottom = lambda c: cyl(W.CB_D / 2, W.CB_H + 0.01, *c, -0.01)
    # compound a/b and the idler, each with a counterbore underneath for its pin's barb
    ab = ext(gp(ZA).difference(disc(W.HOLE / 2)), GT, 0) + ext(gp(ZB).difference(disc(W.HOLE / 2)), GT + G, GT - 0.01)
    ab = (ab - cb_bottom((0, 0))).translate([B[0], B[1], z1])
    idl = (ext(gp(ZI).difference(disc(W.HOLE / 2)), GT, 0) - cb_bottom((0, 0))).translate([I[0], I[1], z2])
    # moon gear with a tube up through the arm ending in a hex peg; the Moon's arm (hex hole) and the Earth press on top
    TOP = za + AT + G                                                 # moon arm bottom
    mg = ext(gp(ZM).difference(disc(1.0)), GT, z2) + cyl(3.0, TOP - (z2 + GT) + 0.01, 0, 0, z2 + GT - 0.01)
    hexpeg = lambda r, h, z: ext(Polygon([(r * math.cos(k * math.pi / 3), r * math.sin(k * math.pi / 3)) for k in range(6)]), h, z)
    mg = mg + hexpeg(2.6, 2.6 + 5.0, TOP - 0.01)
    moon_arm = ext(unary_union([disc(5.2), LineString([(0, 0), (24, 0)]).buffer(2.6), disc(3.6, (24, 0))]), 2.6, TOP) - hexpeg(2.85, 4, TOP - 1)
    moon_arm = moon_arm + Manifold.sphere(4.5, SEG).translate([24, 0, TOP + 2.6 + 4.5 - 0.8])
    EZ = TOP + 2.6
    earth = Manifold.sphere(9.0, SEG).translate([0, 0, 9.0]) - hexpeg(2.85, 5.2, -1) - box(-12, 12, -12, 12, -12, 0.6)
    mg, moon_arm = mg.translate([E[0], E[1], 0]), moon_arm.translate([E[0], E[1], 0])
    span_ab = (za + AT) - z1; span_i = (za + AT) - z2
    pins = {f'pin-{span_ab:.1f}mm-compound': W.pin(span_ab), f'pin-{span_i:.1f}mm-idler': W.pin(span_i)}
    ph = {}
    # mesh phases on the z planes (2D), arm angle 0
    def best(poly_fixed, mk, n=90, period=24):
        return max(((mk(a).distance(poly_fixed)), a) for a in np.linspace(0, period, n))[1]
    sunP = gp(ZS)
    pa = best(sunP, lambda a: affinity.translate(affinity.rotate(gp(ZA), a, origin=(0, 0)), *B), period=360 / ZA)
    bP = affinity.translate(affinity.rotate(gp(ZB), pa, origin=(0, 0)), *B)
    pi_ = best(bP, lambda a: affinity.translate(affinity.rotate(gp(ZI), a, origin=(0, 0)), *I), period=360 / ZI)
    iP = affinity.translate(affinity.rotate(gp(ZI), pi_, origin=(0, 0)), *I)
    pm = best(iP, lambda a: affinity.translate(affinity.rotate(gp(ZM), a, origin=(0, 0)), *E), period=360 / ZM)
    ab = rot(ab, pa, B); idl = rot(idl, pi_, I); mg = rot(mg, pm, E); moon_arm = rot(moon_arm, pm, E)
    def pose(deg):
        # arm turned by deg about the post; relative to the arm the fixed sun turns -deg
        ra = -deg * ZS / ZA                            # compound: relative to the arm (one external mesh flips: +deg*ZS/ZA? sign below)
        rel_a = deg * ZS / ZA                          # sun turns -deg relative to the arm -> a turns +deg*ZS/ZA
        rel_i = -rel_a * ZB / ZI
        rel_m = -rel_i * ZI / ZM
        P_ = {'base': base, 'sun': sun_ball.translate([0, 0, SUN_Z - 6])}
        Rz = lambda mm: mm.rotate([0, 0, deg])
        P_['arm'] = Rz(arm)
        P_['ab'] = Rz(rot(ab, rel_a, B)); P_['idler'] = Rz(rot(idl, rel_i, I)); P_['moongear'] = Rz(rot(mg, rel_m, E))
        P_['moonarm'] = Rz(rot(moon_arm, rel_m, E)); P_['earth'] = Rz(rot(earth.translate([E[0], E[1], EZ]), rel_m, E))
        return P_
    parts = {'base': base, 'sun': sun_ball, 'arm': arm, 'compound-15-34': ab, 'idler-15': idl, 'moon-gear': mg, 'moon-arm': moon_arm, 'earth': earth}
    parts.update(pins)
    pairs = [('base', 'ab'), ('base', 'idler'), ('base', 'moongear'), ('ab', 'idler'), ('idler', 'moongear'), ('ab', 'moongear'),
             ('arm', 'ab'), ('arm', 'idler'), ('arm', 'moongear'), ('arm', 'base'), ('sun', 'arm'), ('sun', 'moonarm'), ('moonarm', 'arm'), ('earth', 'arm'), ('sun', 'earth')]
    colors = {'base': (0.2, 0.22, 0.3), 'sun': (0.96, 0.72, 0.18), 'arm': (0.55, 0.42, 0.25), 'ab': (0.8, 0.62, 0.3), 'idler': (0.8, 0.62, 0.3),
              'moongear': (0.8, 0.62, 0.3), 'moonarm': (0.85, 0.85, 0.85), 'earth': (0.2, 0.45, 0.8)}
    return dict(parts=parts, pose=pose, sweep=np.linspace(0, 360 / ratio * 2, 25), pairs=pairs, colors=colors,
                note=f'gears {ZS}->{ZA}/{ZB}->{ZI}->{ZM}: {ratio:.3f} synodic months a year (true 12.368), sidereal {ratio + 1:.3f} (true 13.369)')

# ====================================================================== FLOWER
def flower():
    NP = 6; RH = 16.0                                   # petals, hinge radius
    A_C, A_O = 10.0, 68.0                               # petal angle from vertical: closed bud, open
    DT = 8.0; RS = 5.5; LK = 12.0                       # tail length, slider pivot radius, link length
    PL = 52.0; PT = 2.0                                 # petal length and thickness
    PIN = 1.9                                           # holes for 1.75 mm filament used as pins
    half = math.pi / NP
    def w_at(sv):                                       # petal width: fits the bud at its closed angle, then a rounded tip
        r = RH + sv * math.sin(math.radians(A_C))
        return max(6.0, min(2 * r * math.tan(half) - 3.0, 8.0 + max(0.0, sv - 7.0) * 0.9, 34.0))   # narrow through the calyx, then widening
    prof = [(w_at(sv) / 2, sv) for sv in np.linspace(0, PL * 0.78, 14)]
    tipc = (0.0, PL * 0.78); tr = prof[-1][0]
    outline = [(-x, y) for x, y in prof] + [(tipc[0] + tr * math.cos(t), tipc[1] + tr * math.sin(t)) for t in np.linspace(math.pi, 0, 18)] + [(x, y) for x, y in reversed(prof)]
    blade2d = Polygon(outline).buffer(0).difference(Point(0, 0).buffer(3.0))
    vein = LineString([(0, 6), (0, PL * 0.85)]).buffer(0.6)
    # petal frame: hinge axis along y at the origin, blade in the y-z plane (x 0.5..2.5), tail along -x
    blade = ext(blade2d, PT, 0.5).rotate([0, -90, 0]).rotate([0, 0, 90]).rotate([0, 0, 0])
    def to_petal_frame(m2d, x0, h):  # 2D (u = width -> y, v = length -> z), thickness along x from x0
        return ext(m2d, h, 0).rotate([0, -90, 0]).rotate([90, 0, 0]).translate([x0 + h, 0, 0])
    def pf(m2d, x0, h):
        mm = ext(m2d, h, 0)                               # (u, v, w) -> (x = x0 + w, y = u, z = v)
        T = np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float)
        return mm.transform(T)
    petal = pf(blade2d, 0.5, PT) + pf(vein, 0.5 + PT - 0.01, 0.5)
    wb = w_at(0)
    barrel = Manifold.cylinder(wb, 2.5, 2.5, SEG).rotate([90, 0, 0]).translate([0, wb / 2, 0])
    petal = petal + barrel + box(0.0, 2.5, -wb / 2, wb / 2, 0, 6.0)
    tail = (box(-DT, 0, 1.5, 2.7, -1.6, 1.6) + box(-DT, 0, -2.7, -1.5, -1.6, 1.6)                 # a fork round the link
            + Manifold.cylinder(1.2, 2.0, 2.0, SEG).rotate([90, 0, 0]).translate([-DT, 2.7, 0])
            + Manifold.cylinder(1.2, 2.0, 2.0, SEG).rotate([90, 0, 0]).translate([-DT, -1.5, 0]))
    petal = petal + tail
    petal = petal - Manifold.cylinder(2 * wb, PIN / 2, PIN / 2, SEG).rotate([90, 0, 0]).translate([0, wb, 0])
    petal = petal - Manifold.cylinder(10, PIN / 2, PIN / 2, SEG).rotate([90, 0, 0]).translate([-DT, 5, 0])
    # calyx: spokes between the petal slots, hinge pin holes through them, a stem tube underneath
    slot_w = wb + 0.8
    calyx2d = disc(RH + 5).difference(disc(10.2))
    for k in range(NP):
        a = 2 * math.pi * k / NP
        calyx2d = calyx2d.difference(affinity.rotate(Polygon([(7, -slot_w / 2), (RH + 6, -slot_w / 2), (RH + 6, slot_w / 2), (7, slot_w / 2)]), a, origin=(0, 0), use_radians=True))
    calyx = ext(calyx2d, 6.0, -3.0)
    for k in range(NP):  # hinge pin holes: tangential at radius RH
        calyx = calyx - Manifold.cylinder(2 * (RH + 6), PIN / 2, PIN / 2, SEG).rotate([90, 0, 0]).translate([RH, RH + 6, 0]).rotate([0, 0, 360 * k / NP])
    STEM_L = 90.0; TUBE_R, TUBE_IR = 11.4, 10.0
    calyx = calyx + (cyl(TUBE_R, STEM_L, 0, 0, -3.0 - STEM_L + 0.01) - cyl(TUBE_IR, STEM_L + 2, 0, 0, -3.0 - STEM_L - 1))
    calyx = calyx + ext(disc(TUBE_R).difference(disc(TUBE_IR)), 0.01, -3.0)
    def T_of_(a): ar = math.radians(a); return (RH - DT * math.cos(ar), DT * math.sin(ar))
    def zs_of_(a): t = T_of_(a); dr = t[0] - RS; return t[1] - math.sqrt(LK * LK - dr * dr)
    HUB_H_, ROD_L_ = 7.0, 40.0
    pz0 = zs_of_(A_C) - HUB_H_ / 2 - ROD_L_ + 3 - 1.0; pz1 = zs_of_(A_O) - HUB_H_ / 2 - ROD_L_ + 6 + 1.0
    calyx = calyx - box(-1.3, 1.3, 0, TUBE_R + 1, pz0, pz1)         # vertical slot in the stem for the slider's peg
    # link and slider
    link = (box(-1.2, 1.2, -2.2, 2.2, 0, LK).rotate([0, 0, 0]))
    link = (Manifold.cylinder(2.4, 2.0, 2.0, SEG).rotate([90, 0, 0]).translate([0, 1.2, 0]) +
            Manifold.cylinder(2.4, 2.0, 2.0, SEG).rotate([90, 0, 0]).translate([0, 1.2, LK])).hull()
    link = link - Manifold.cylinder(4, PIN / 2, PIN / 2, SEG).rotate([90, 0, 0]).translate([0, 2, 0]) - Manifold.cylinder(4, PIN / 2, PIN / 2, SEG).rotate([90, 0, 0]).translate([0, 2, LK])
    HUB_R, HUB_H = 7.6, 7.0
    hub = cyl(HUB_R, HUB_H, 0, 0, -HUB_H / 2)
    for k in range(NP):
        hub = hub - box(RS - 3.0, HUB_R + 1, -1.5, 1.5, -HUB_H / 2 - 1, HUB_H / 2 + 1).rotate([0, 0, 360 * k / NP])
        hub = hub - Manifold.cylinder(2 * HUB_R, PIN / 2, PIN / 2, SEG).rotate([90, 0, 0]).translate([RS, HUB_R, 0]).rotate([0, 0, 360 * k / NP])
    ROD_L = 40.0
    slider = hub + cyl(2.6, ROD_L, 0, 0, -HUB_H / 2 - ROD_L + 0.01) + box(-1.0, 1.0, 0, TUBE_R + 2.5, -HUB_H / 2 - ROD_L + 3, -HUB_H / 2 - ROD_L + 6)
    collar = cyl(TUBE_R + 4.0, 8, 0, 0, 0) - cyl(TUBE_R + 0.35, 10, 0, 0, -1) - box(-1.15, 1.15, TUBE_R - 0.5, TUBE_R + 3.0, 3, 6.4)
    # kinematics
    def T_of(a): ar = math.radians(a); return (RH - DT * math.cos(ar), DT * math.sin(ar))
    def zs_of(a):
        t = T_of(a); dr = t[0] - RS; return t[1] - math.sqrt(LK * LK - dr * dr)
    zc, zo = zs_of(A_C), zs_of(A_O)
    def pose(u):                                        # u = 0 closed .. 1 open
        a = A_C + (A_O - A_C) * u; zs = zs_of(a); t = T_of(a)
        ang_l = math.degrees(math.atan2(t[0] - RS, t[1] - zs))     # link tilt from vertical, outward
        P_ = {'calyx': calyx, 'slider': slider.translate([0, 0, zs])}
        for k in range(NP):
            P_[f'petal{k}'] = petal.rotate([0, a, 0]).translate([RH, 0, 0]).rotate([0, 0, 360 * k / NP])
            P_[f'link{k}'] = link.rotate([0, ang_l, 0]).translate([RS, 0, zs]).rotate([0, 0, 360 * k / NP])
        P_['collar'] = collar.translate([0, 0, -HUB_H / 2 - ROD_L + 0.5 + zs])
        return P_
    parts = {'calyx-stem': calyx, 'petal': petal, 'link': link, 'slider': slider, 'collar': collar}
    pairs = [(f'petal{k}', f'petal{(k + 1) % NP}') for k in range(NP)] + [(f'petal{k}', 'calyx') for k in range(NP)] + \
            [(f'link{k}', 'calyx') for k in range(NP)] + [(f'link{k}', f'link{(k + 1) % NP}') for k in range(NP)] + \
            [(f'link{k}', f'petal{(k + 1) % NP}') for k in range(NP)] + [('slider', 'calyx')] + [(f'petal{k}', 'slider') for k in range(NP)]
    colors = {'petal': (0.93, 0.42, 0.55), 'calyx': (0.3, 0.55, 0.3), 'link': (0.95, 0.85, 0.4), 'slider': (0.95, 0.85, 0.4), 'collar': (0.3, 0.55, 0.3)}
    return dict(parts=parts, pose=pose, sweep=np.linspace(0, 1, 13), pairs=pairs, colors=colors, frame_deg=1.0,
                note=f'{NP} petals {A_C:.0f}°..{A_O:.0f}°, stroke {zo - zc:.1f} mm of the ring on the stem, pins: 1.75 mm filament')

# ====================================================================== CALENDAR
def calendar():
    R_C, R_O = 18.0, 30.0                                # core radius, ring outer radius
    RH_, G = 11.0, PIP                                   # ring height, gaps
    FL = 3.0; R_F = R_O + 4.0                            # base and cap flanges
    rings = [('mes', ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'], 6.0),
             ('dia', [str(i) for i in range(1, 32)], 5.6),
             ('semana', ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM'], 6.0)]   # bottom to top
    z0 = FL + G
    zr = [z0 + i * (RH_ + G) for i in range(3)]
    H = zr[-1] + RH_ + G + FL
    NOTCH_D = 0.9; NOTCH_R = 1.6
    core = cyl(R_C, H) + cyl(R_F, FL) + cyl(R_F, FL, 0, 0, H - FL)
    # front markers: a V notch in both flanges at angle 0 (+x)
    for zz in (0, H - FL):
        core = core - ext(Polygon([(R_F + 1, -2.5), (R_F + 1, 2.5), (R_O + 1.0, 0)]), FL + 2, zz - 1)
    parts = {}; ring_parts = {}
    for (name, labels, size), z in zip(rings, zr):
        n = len(labels)
        bore = disc(R_C + G, n=192)
        for k in range(n):
            a = 2 * math.pi * k / n
            bore = bore.union(disc(NOTCH_R, ((R_C + G + NOTCH_D - NOTCH_R) * math.cos(a), (R_C + G + NOTCH_D - NOTCH_R) * math.sin(a))))
        ring = ext(disc(R_O, n=256).difference(bore), RH_, z)
        for k, lab in enumerate(labels):
            a = 2 * math.pi * k / n
            tp = text_poly(lab, size, (0, 0))
            tx = ext(tp, 1.4, 0)                          # (u, v, w): u along the rim, v up, w out
            rh = np.array([math.cos(a), math.sin(a), 0.0]); th = np.array([-math.sin(a), math.cos(a), 0.0])
            M3 = np.column_stack([th, [0, 0, 1], rh])
            T = np.column_stack([M3, rh * (R_O - 0.6) + np.array([0, 0, z + RH_ / 2])])
            ring = ring + tx.transform(T)
        ring_parts[name] = ring
        # detent springs in the core for this ring: two arcs near the surface, bumps resting in notches 0 and n/2
        for side in (0.0, 2 * math.pi * round(n / 2) / n):    # both bumps sit on a notch, also for 7 and 31
            arm_a0, arm_a1 = side - 0.75, side                    # 43° of arc, free end at the notch
            arm = Polygon([((R_C - 1.3) * math.cos(t), (R_C - 1.3) * math.sin(t)) for t in np.linspace(arm_a0, arm_a1, 30)] +
                          [(R_C * math.cos(t), R_C * math.sin(t)) for t in np.linspace(arm_a1, arm_a0, 30)])
            gap_ = Polygon([((R_C - 3.2) * math.cos(t), (R_C - 3.2) * math.sin(t)) for t in np.linspace(arm_a0 + 0.06, arm_a1 + 0.25, 30)] +
                           [((R_C + 1) * math.cos(t), (R_C + 1) * math.sin(t)) for t in np.linspace(arm_a1 + 0.25, arm_a0 + 0.06, 30)])
            bump = disc(1.3, ((R_C - 0.4) * math.cos(side), (R_C - 0.4) * math.sin(side)))   # reaches R_C + 0.9
            cut = gap_.difference(arm.buffer(0.001)).difference(Polygon([((R_C - 1.3) * math.cos(t), (R_C - 1.3) * math.sin(t)) for t in np.linspace(arm_a0 - 0.2, arm_a0 + 0.06, 6)] + [(0, 0)]))
            core = core - ext(cut, RH_ - 2, z + 1) + ext(unary_union([arm, bump]).intersection(disc(R_C + 0.9)), RH_ - 2, z + 1)
    # the detent springs need room: check they sit inside the core and the bumps reach the notches
    parts['core'] = core
    for k, v in ring_parts.items(): parts[f'ring-{k}'] = v
    def pose(deg):
        P_ = {'core': core}
        for (name, labels, size) in rings:
            n = len(labels); step = 360 / n
            P_[f'ring-{name}'] = rot(ring_parts[name], round(deg / step) * step)   # rests at a notch
        return P_
    pairs = [('core', f'ring-{n}') for n, _, _ in rings] + [('ring-mes', 'ring-dia'), ('ring-dia', 'ring-semana')]
    colors = {'core': (0.22, 0.24, 0.3), 'ring-mes': (0.93, 0.91, 0.86), 'ring-dia': (0.85, 0.36, 0.16), 'ring-semana': (0.93, 0.91, 0.86)}
    return dict(parts=parts, pose=pose, sweep=[0], pairs=pairs, colors=colors, pip=True,
                note=f'{2*R_F:.0f} mm across, {H:.0f} mm tall; 12 months, 31 days, 7 weekdays, a click at each')

OBJECTS = {'wave': wave, 'orrery': orrery, 'flower': flower, 'calendar': calendar}

def check(o, names=None):
    worst = {}
    for s in o['sweep']:
        P_ = o['pose'](s)
        for a, b in o['pairs']:
            g = P_[a].min_gap(P_[b], 1.0)
            if (a, b) not in worst or g < worst[(a, b)][0]: worst[(a, b)] = (g, s)
    bad = {f'{a}/{b}': (round(v[0], 3), v[1]) for (a, b), v in worst.items() if v[0] < 0.25}
    return worst, bad

if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if a in OBJECTS] or list(OBJECTS)
    for nm in names:
        o = OBJECTS[nm]()
        d = os.path.join(OUT, nm); os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            if f.endswith('.stl'): os.remove(os.path.join(d, f))
        closed = {}
        for k, m in o['parts'].items():
            t = to_tm(m); t.export(os.path.join(d, f'{nm}-{k}.stl')); closed[k] = t.is_watertight
        worst, bad = check(o)
        print(nm, o['note'])
        print(' closed:', all(closed.values()), [k for k, v in closed.items() if not v])
        print(' min gaps < 0.25 mm:', bad if bad else 'none')
        print(' tightest:', sorted(((round(v[0], 2), f'{a}/{b}') for (a, b), v in worst.items()))[:6])
