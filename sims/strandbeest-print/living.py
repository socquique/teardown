# A living picture: the relief wave (wave_art.py) cut into three bodies that move. The wave (with its water, lines
# and crest foam), the sea in front of it and the near sea each rock a degree or two on a pin hidden under the
# frame's lip. Behind the back panel (sky + sun, still) one camshaft carries three eccentric discs, each running in
# a yoke on its body's arm, so every body is pushed both ways and never hangs on gravity. TT motor, 7.4:1 (a cycle every 7.6 s).
#   python3 sims/strandbeest-print/living.py   -> teardown-out/print/living-wave/ (+ sims/wave-art-shared/living.json)
import math, os, sys, json
import numpy as np, trimesh
from manifold3d import Manifold
from shapely.geometry import Polygon, Point, LineString, box as sbox
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv; sys.argv = [sys.argv[0]]
from fidgets import cs, ext, cyl, rot, to_tm, gear_poly
from objects import box, d_hole
import wave_art as WA
sys.argv = _argv

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'teardown-out', 'print', 'living-wave')
SEG = 64
W = WA.W
WIN = (3.0, 3.0, 107.0, 107.0)        # window, art coordinates (y = 0 is the art's bottom edge)
IX0, IX1 = -12.0, 122.0                # inside of the box in x
YB = -30.0                             # top of the base
TOP = 126.0                            # inside top
PT, DT, PG = 2.4, 1.6, 1.2             # carrier sheet, decor layer, gap between bodies
BACK_T = 3.0                           # back panel: z from -3 to 0
SH_Y, SH_Z = -10.0, -20.0              # camshaft axis (along x)
SH_R, SH_FLAT = 3.0, 2.2
REAR = -60.0                           # inside of the rear cover
PIV_Y = -5.0                           # pivot pins
LEG_W = 5.0; LEG_Y0 = -16.0            # legs under the window; the drive leg's foot carries the arm
EXT = sbox(-6, -2, 116, 120)           # sheets run past the window under the lip

D = WA.design()
xs, st = D['sea_top']
def widen(poly):
    """stretch a region that touches the art's left/right edge out under the frame's lip."""
    add = []
    for strip, x0, x1 in ((sbox(-0.01, -10, 1.5, 130), -7, 1.5), (sbox(108.5, -10, 110.01, 130), 108.5, 117)):
        part = poly.intersection(strip)
        for g in getattr(part, 'geoms', [part]):
            if g.is_empty or g.area < 0.01: continue
            _, y0, _, y1 = g.bounds
            add.append(sbox(x0, y0, x1, y1))
    return unary_union([poly] + add).intersection(EXT).buffer(0)
Y1 = sbox(-20, 1.0, 140, 140)          # decor stays above the pins' caps

# --- the wave: its body tucks behind the sea below y = 14
C = (46, 54)
wave_reg = widen(unary_union([D['wave_band'], D['back']]).buffer(1.5).buffer(-1.5)
                 .difference(Point(C[0] + 1.5, C[1] - 1.0).buffer(9.0, 48)).intersection(sbox(-1, 12, 111, 111)))
SKIRT_TOP = 13.0                       # a hidden skirt behind the sea ties the wave to its legs
wave_reg = unary_union([wave_reg, sbox(-6, -2, 116, SKIRT_TOP)])
Y12 = sbox(-20, 12, 140, 140)
wave_blue = D['blue'].intersection(wave_reg.buffer(-0.4)).intersection(Y12)
wave_light = D['light'].intersection(wave_blue.buffer(-0.4))
wave_foam = D['foam_crest'].intersection(wave_reg.buffer(-0.3))
# --- the sea in front of it: down to below the window, its own stripes and swell foam
mid_reg = widen(unary_union([D['sea'], sbox(0, -2, 110, 4), D['foam_sea'].buffer(0.8)]))     # the foam stands on its own navy outline
mid_blue = mid_reg.buffer(-2.0).union(D['blue'].intersection(mid_reg.buffer(-0.4))).intersection(mid_reg.buffer(-0.4)).intersection(Y1)
mid_light = D['light'].intersection(mid_blue.buffer(-0.4))
mid_foam = D['foam_sea'].intersection(EXT)
# --- the near sea: a low swell across the bottom with a row of foam
nx = np.linspace(-6, 116, 200)
ny = 9.0 + 2.0 * np.sin(nx / 7.5 + 0.6) + 1.0 * np.sin(nx / 3.1)
near_reg = Polygon([(-6, -2)] + list(zip(nx, ny)) + [(116, -2)]).buffer(0).intersection(EXT)
near_claws = WA.claws(np.column_stack([nx[6:-6], ny[6:-6] - 0.6]), 13, 2.6, 1, 21, lean=1.0).intersection(EXT)
near_reg = unary_union([near_reg, near_claws.buffer(0.8)]).intersection(EXT)
near_blue = near_reg.buffer(-1.6).intersection(Y1)
near_light = WA.band_along(np.column_stack([nx, 4.6 + 1.2 * np.sin(nx / 6 + 2.0)]), 1.4, 1.4).intersection(near_blue.buffer(-0.5))
near_foam = near_claws.union(WA.band_along(np.column_stack([nx[3:-3], ny[3:-3] - 0.9]), 1.6, 1.6)).intersection(near_reg).intersection(Y1)

# bodies back to front; each body's first sheet is its carrier (legs, arm, yoke)
NAVY, BLUE, LIGHT, WHITE = '#1d2f5e', '#2f6db3', '#8cc8e8', '#f8f8f4'
BODIES = {
    'ola':       dict(pivot=94.0, drive=22.0, amp=2.2, phase=90.0,
                      sheets=[('ola', wave_reg, NAVY), ('ola-agua', wave_blue, BLUE), ('ola-rayas', wave_light, LIGHT), ('ola-espuma', wave_foam, WHITE)]),
    'mar':       dict(pivot=8.0, drive=80.0, amp=1.0, phase=210.0,
                      sheets=[('mar', mid_reg, NAVY), ('mar-agua', mid_blue, BLUE), ('mar-rayas', mid_light, LIGHT), ('mar-espuma', mid_foam, WHITE)]),
    'orilla':    dict(pivot=102.0, drive=40.0, amp=1.5, phase=330.0,
                      sheets=[('orilla', near_reg, NAVY), ('orilla-agua', near_blue, BLUE), ('orilla-rayas', near_light, LIGHT), ('orilla-espuma', near_foam, WHITE)]),
}
Z = {}; z = 3.0
for bn, b in BODIES.items():
    for i, (n, reg, col) in enumerate(b['sheets']):
        Z[n] = z; z += PT if i == 0 else DT
    b['z0'] = Z[b['sheets'][0][0]]; b['z1'] = z
    z += PG
LIP_Z = z - PG + 1.2                   # the frame's lip starts this far forward
for b in BODIES.values():
    b['D'] = abs(b['drive'] - b['pivot'])
    b['e'] = math.radians(b['amp']) * b['D']            # eccentricity for that swing
    b['R'] = b['e'] + 5.2                               # eccentric disc radius (round the shaft's 3.2 bore)
ZT = {n: (PT if i == 0 else DT) for b in BODIES.values() for i, (n, *_r) in enumerate(b['sheets'])}

def leg(x, y0, y1): return sbox(x - LEG_W / 2, y0, x + LEG_W / 2, y1)
def legs_of(b): return unary_union([leg(b['pivot'], PIV_Y - 4.0, 4.0), leg(b['drive'], LEG_Y0, 4.0)])

def yoke_dims(b):
    wy = b['R'] + 0.3; wz = b['R'] + b['e'] + 1.0               # window half sizes (disc moves ±e in z)
    return wy, wz, wy + 2.5, wz + 2.5

def clean(reg, min_area=0.6):
    reg = reg.buffer(-0.1).buffer(0.1)     # no corners touching at a point: every piece is a clean solid
    return unary_union([g for g in getattr(reg, 'geoms', [reg]) if g.area > min_area])
ARM_PEGS = (1.5, 4.5)                  # the arm's two pegs (y above LEG_Y0) into the drive leg
# The arms print lying on their −x face, so the pegs are horizontal on the bed. A round peg's underside would hang
# 0.25 mm over the bed and sag into a burr (seen in the first fit test), so each peg sits 0.45 mm toward the bed and is
# cut flat there: it prints on the bed, and its flat side just leaves a little room in the round hole. Tip chamfered.
PEG_R, PEG_SHIFT, PEG_L, PEG_TIP = 1.25, -0.45, 2.2, 0.4
def peg(x_arm, y, z0):
    """one arm peg standing on the arm's face z0 (pointing +z), for an arm whose −x face (x_arm − 1.5) is the bed."""
    xc = x_arm + PEG_SHIFT
    m = cyl(PEG_R, PEG_L - PEG_TIP, xc, y, z0) + cyl(PEG_R, PEG_TIP, xc, y, z0 + PEG_L - PEG_TIP, r2=PEG_R - 0.3)
    return m ^ box(x_arm - 1.5, x_arm + 1.5, y - 2, y + 2, z0 - 1, z0 + PEG_L + 1)

def body_parts(bn):
    """one body as {name: manifold} in art coordinates. Carrier and colours print together as ONE multicolour piece
    (AMS), back face on the bed: every colour is a column standing on the navy carrier up to its own height, the upper
    colours passing through the lower ones, so nothing floats and nothing is glued. The arm with its yoke is a
    separate piece pressed onto the drive leg by two pegs."""
    b = BODIES[bn]; out = {}
    carrier_reg = b['sheets'][0][1]
    dec = [clean(reg.intersection(carrier_reg.buffer(-0.4))) for (n, reg, col) in b['sheets'][1:]]
    base = b['z0'] + PT
    holes = None
    for on, ob in BODIES.items():          # room for the other bodies' pins to rock past
        if on != bn:
            h = cyl(5.0, 80, ob['pivot'], PIV_Y, -40); holes = h if holes is None else holes + h
    for i, (n, reg, col) in enumerate(b['sheets']):
        if i == 0:
            m = ext(clean(unary_union([reg, legs_of(b)])), PT, b['z0'])
            m = m - cyl(1.75, PT + 2, b['pivot'], PIV_Y, b['z0'] - 1)                    # 3.0 pin, 0.25 clearance
            for py in ARM_PEGS: m = m - cyl(1.2, 1.9, b['drive'] + PEG_SHIFT, LEG_Y0 + py, b['z0'] - 0.01)   # blind holes for the arm's pegs
            out[n] = m - holes
            continue
        k = i - 1
        above = unary_union(dec[k + 1:]) if dec[k + 1:] else Polygon()
        r = clean(dec[k].difference(above))
        if r.is_empty: continue
        out[n] = ext(r, DT * i, base) - holes
    # the arm: from the leg's back face straight back through the panel to the yoke round the eccentric
    wy, wz, oy, oz = yoke_dims(b); x = b['drive']; ztop = SH_Z + oz
    arm = box(x - 1.5, x + 1.5, LEG_Y0, LEG_Y0 + 6.0, ztop - 1, b['z0'] - 0.1)
    yoke = box(x - 1.5, x + 1.5, SH_Y - oy, SH_Y + oy, SH_Z - oz, ztop) - box(x - 3, x + 3, SH_Y - wy, SH_Y + wy, SH_Z - wz, SH_Z + wz)
    pegs = None
    for py in ARM_PEGS:
        p = peg(x, LEG_Y0 + py, b['z0'] - 0.6); pegs = p if pegs is None else pegs + p   # 0.05 press
    out[bn + '-brazo'] = arm + yoke + pegs
    return out

def body_angle(bn, t):
    b = BODIES[bn]
    yd = b['e'] * math.sin(math.radians(t + b['phase']))       # the disc centre's height above the shaft
    return math.degrees(math.asin(yd / b['D'])) * (1 if b['drive'] > b['pivot'] else -1)

def pose_body(parts, bn, t):
    b = BODIES[bn]; a = body_angle(bn, t)
    return {n: rot(m, a, (b['pivot'], PIV_Y)) for n, m in parts.items()}

def ecc(bn):
    """eccentric disc (local: axis z, disc centre at +x e), core 5.0 wide (1.0 play each side: the yoke tilts with its body) with a flange; a D washer closes the other side."""
    b = BODIES[bn]; e, R = b['e'], b['R']
    core = cyl(R, 5.0, e, 0, -2.5) + cyl(R + 1.8, 1.0, e, 0, 2.5)
    bore = d_hole(SH_R + 0.2, SH_FLAT + 0.2, 0, 12, -6)
    washer = cyl(R + 1.8, 1.0, e, 0, -3.5) - bore
    return core - bore, washer

def on_shaft(m, x, t):
    """put a part built round the local z axis onto the camshaft at x, turned to crank angle t
    (local +x points to (y, z) = (sin t, cos t))."""
    a = math.radians(t); c, s = math.cos(a), math.sin(a)
    return m.transform([[0, 0, 1, x], [s, -c, 0, SH_Y], [c, s, 0, SH_Z]])

# --- gear train behind the right of the panel: motor pinion 10 -> 40 | 14 -> 26 on the camshaft = 7.4:1
M_ = 1.0
ZP, ZB, ZC, ZS = 10, 40, 14, 26           # pinion, compound big/small, shaft gear (ZC + ZS = 40: centre distance 20)
RATIO = (ZB / ZP) * (ZS / ZC)
def gp(z, bl=0.5): return gear_poly(z, M_, M_ * z / 2 + 0.85 * M_, M_ * z / 2 - 1.25 * M_ - 0.1, math.pi * M_ / 2 - bl / 2)
GT = 4.0
GA = 90.0                              # x of the gear planes: shaft gear and compound's 10 at GA..GA+4
GB = GA + GT + 0.6                     # compound's 40 and the pinion
MB = GB + GT + 0.5                     # motor bracket (3 thick), motor body behind it toward +x
ANG = math.radians(45)
CPD = (SH_Y + 20 * math.sin(ANG), SH_Z - 20 * math.cos(ANG))       # compound (y, z): up and back from the shaft
MOT = (CPD[0] + 25.0, CPD[1])                                       # motor shaft straight above the compound
def at_yz(m, x, yz, deg):
    """a part built in its xy plane (axis z) turned by deg, placed with its axis along x at (y, z)."""
    return m.rotate([0, 0, deg]).transform([[0, 0, 1, x], [1, 0, 0, yz[0]], [0, 1, 0, yz[1]]])

TABS = (0.0, 48.0, 96.0); TAB = 1.8; TAB_L = 20.0       # panel tabs (y starts), how far they reach into the walls
RAILS = (GA - 3.0, MB - 2.0); RAIL_W = 4.0; RAIL_D = 1.6  # floor rails for the gearbox feet
MOTOR_RIB = (IX1 - (MB + 3.0 + 18.8)) + 0.05            # rib height: 0.05 mm of press on the motor's side
LIP = 5.0                                                 # snap lips of the frame and the rear cover
SHAFT_X0 = IX0 - 6.3                                      # the shaft's head sits just outside the left wall
BEAR_CLR = 0.3                                            # camshaft bearings (horizontal holes in the box wall and gearbox)
CSK_R = 5.64 / 2 + 0.2                                    # 90° countersink for an ISO 10642 / DIN 7991 M3 head (Ø5.64 per bd_warehouse) + 0.2

def ring(zc, r, inset):
    """a round bead (or groove) running round the inside of the box at depth zc, its centre `inset` mm inside the walls'
    inner faces (negative: inside the lid's lip)."""
    def rod(x0, y0, x1, y1):
        L_ = math.hypot(x1 - x0, y1 - y0)
        m = Manifold.cylinder(L_, r, r, 24)
        if x1 != x0: m = m.rotate([0, 90, 0]).translate([x0, y0, zc])
        else: m = m.rotate([-90, 0, 0]).translate([x0, y0, zc])
        return m
    a, b_, c, d = IX0 - inset, IX1 + inset, YB - inset, TOP + inset
    # only the middle 60 % of each side, clear of the corners
    w, h = b_ - a, d - c
    return (rod(a + 0.2 * w, c, a + 0.8 * w, c) + rod(a + 0.2 * w, d, a + 0.8 * w, d)
            + rod(a, c + 0.2 * h, a, c + 0.8 * h) + rod(b_, c + 0.2 * h, b_, c + 0.8 * h))

def fixed():
    F = {}
    back = box(IX0 + 0.2, IX1 - 0.2, YB + 0.2, TOP - 0.2, -BACK_T, 0)
    for b in BODIES.values():
        x = b['drive']
        back = back - box(x - 2.6, x + 2.6, LEG_Y0 - 1.0 - b['e'], LEG_Y0 + 7.0 + b['e'], -BACK_T - 1, 1)
    caps = None; screws = None
    for b in BODIES.values():
        # pivots: countersunk M3 screws (DIN 7991) from behind, flush with the panel's back; a printed cap threads onto
        # the tip in front of the carrier. A steel pin is far stronger than a printed 3 mm peg.
        zc = b['z0'] + PT
        need = zc + 0.35 + 1.2 + BACK_T                     # from the panel's back face to the cap's front
        b['screw'] = L_ = min(l for l in (10, 12, 16, 20, 25, 30, 35, 40) if l >= need)
        back = back - cyl(1.65, BACK_T + 2, b['pivot'], PIV_Y, -BACK_T - 1) - cyl(CSK_R, CSK_R - 1.65, b['pivot'], PIV_Y, -BACK_T - 0.01, r2=1.65)
        sc = cyl(2.8, 1.7, b['pivot'], PIV_Y, -BACK_T, r2=1.5) + cyl(1.5, L_ - 1.7, b['pivot'], PIV_Y, -BACK_T + 1.7)
        screws = sc if screws is None else screws + sc
        c = cyl(2.6, 1.2, b['pivot'], PIV_Y, zc + 0.35) - cyl(1.35, 3, b['pivot'], PIV_Y, zc)
        caps = c if caps is None else caps + c
    # tabs on the panel's sides slide in the box's grooves from behind
    for y0 in TABS:
        back = back + box(IX0 - TAB, IX0 + 0.5, y0, y0 + TAB_L, -BACK_T, 0) + box(IX1 - 0.5, IX1 + TAB, y0, y0 + TAB_L, -BACK_T, 0)
    F['back'] = back
    F['caps'] = caps; F['screws'] = screws
    F['cap_local'] = cyl(2.6, 1.2, 0, 0, 0) - cyl(1.35, 3, 0, 0, -1)         # 2.7 bore: grips the M3 thread
    F['sun'] = ext(D['sun'], 1.2, 0)                # red disc: printed with the sky in one piece (AMS)
    shaft = ((cyl(SH_R, GA + GT - SHAFT_X0, 0, 0, 0) + cyl(4.5, 2.0, 0, 0, 0)) ^ box(-5, SH_FLAT, -5, 5, -1, 400))   # head outside the left wall
    F['shaft_local'] = shaft                        # along local z from 0
    # --- the box: one tube (printed standing, no supports), the frame and the rear cover snap into its ends
    O = (IX0 - 4, IX1 + 4, YB - 4, TOP + 4)
    tube = box(O[0], O[1], O[2], O[3], REAR, LIP_Z) - box(IX0, IX1, YB, TOP, REAR - 1, LIP_Z + 1)
    tube = tube - Manifold.cylinder(6, SH_R + BEAR_CLR, SH_R + BEAR_CLR, SEG).rotate([0, 90, 0]).translate([IX0 - 5, SH_Y, SH_Z])
    for y0 in TABS:                                    # grooves for the panel's tabs, open at the back, closed at z = 0
        g = TAB + 0.25
        tube = tube - box(IX0 - g, IX0 + 0.01, y0 - 0.2, y0 + TAB_L + 0.2, REAR - 1, 0.0) - box(IX1 - 0.01, IX1 + g, y0 - 0.2, y0 + TAB_L + 0.2, REAR - 1, 0.0)
    for x0 in RAILS:                                   # rails in the floor for the gearbox's feet, same way in
        tube = tube - box(x0 - 0.2, x0 + RAIL_W + 0.2, YB - RAIL_D - 0.2, YB + 0.01, REAR - 1, -3.0)
    for zc in (LIP_Z - LIP / 2, REAR + LIP / 2):       # snap grooves round the inside, where the lids' beads click in
        tube = tube - ring(zc, 0.6, 0.0)
    # two ribs on the right wall press the TT motor against its bracket (it is located there by its boss, pin and bump)
    my_, mz_ = MOT
    for yc in (my_ - 4.0, my_ + 28.0):
        tube = tube + box(IX1 - MOTOR_RIB, IX1 + 0.01, yc - 2.0, yc + 2.0, mz_ - 9.0, mz_ + 9.0)
    F['tube'] = tube
    def lid(z_plate0, z_plate1, z_lip0, z_lip1):
        m = box(O[0], O[1], O[2], O[3], z_plate0, z_plate1)
        c = 0.15
        lip = box(IX0 + c, IX1 - c, YB + c, TOP - c, z_lip0, z_lip1) - box(IX0 + c + 2, IX1 - c - 2, YB + c + 2, TOP - c - 2, z_lip0 - 1, z_lip1 + 1)
        return m + lip + ring((z_lip0 + z_lip1) / 2, 0.45, -0.15)          # bead: 0.3 mm snap into the tube's groove
    frame = lid(LIP_Z, LIP_Z + 3, LIP_Z - LIP, LIP_Z + 0.01)
    F['frame'] = frame - box(WIN[0], WIN[2], WIN[1], WIN[3], LIP_Z - 1, LIP_Z + 4)
    rear = lid(REAR - 3, REAR, REAR - 0.01, REAR + LIP)
    F['rear'] = rear - box(50, 58, 96, 100, REAR - 4, REAR + 1) - cyl(5, 10, 54, 100, REAR - 4) \
                - box(IX1 - 40, IX1 - 4, 14, 70, REAR - 4, REAR + 1)                                   # hanging slot, motor window (cables)
    # --- gearbox: the motor plate and the shaft's bearing plate joined by a foot that slides on the floor rails
    my, mz = MOT
    zg0, zg1 = REAR + LIP + 0.3, -3.1
    br = box(MB, MB + 3.0, YB + 0.2, my + 42.0, zg0, zg1)
    br = br - Manifold.cylinder(5, 4.5, 4.5, SEG).rotate([0, 90, 0]).translate([MB - 1, my, mz]) \
            - Manifold.cylinder(5, 2.05, 2.05, SEG).rotate([0, 90, 0]).translate([MB - 1, my + 11.15, mz]) \
            - box(MB - 1, MB + 4, my + 30.7 - 2.8, my + 30.7 + 2.8, mz - 2.3, mz + 2.3)
    br = br + Manifold.cylinder(MB - GA + 1.0, 1.7, 1.7, SEG).rotate([0, -90, 0]).translate([MB + 0.01, CPD[0], CPD[1]])   # compound's pin
    bearing = box(GA - 3.6, GA - 0.6, YB + 0.2, SH_Y + 12.0, zg0, zg1) - Manifold.cylinder(5, SH_R + BEAR_CLR, SH_R + BEAR_CLR, SEG).rotate([0, 90, 0]).translate([GA - 4.6, SH_Y, SH_Z])
    foot = box(GA - 3.6, MB + 3.0, YB + 0.2, YB + 3.2, zg0, zg1)
    for x0 in RAILS: foot = foot + box(x0, x0 + RAIL_W, YB - RAIL_D, YB + 0.3, zg0, zg1)
    F['gearbox'] = br + bearing + foot
    F['motor'] = box(MB + 3.0, MB + 3.0 + 18.8, my - 11.2, my + 37.2, mz - 11.2, mz + 11.2)                # TT body (stand-in)
    F['g30'] = ext(gp(ZS), GT) - d_hole(SH_R + 0.2, SH_FLAT + 0.2, 0, GT + 2)
    F['g_comp'] = ext(gp(ZC), GT, 0) + cyl(M_ * ZC / 2 - 1.6, 0.8, 0, 0, GT - 0.1) + ext(gp(ZB), GT, GT + 0.6) - cyl(1.95, 20, 0, 0, -1)   # hub joins the two gears
    F['g_pin'] = ext(gp(10), GT, 0) - (cyl(2.8, 9, 0, 0, -1) ^ box(-1.975, 1.975, -4, 4, -2, 9))           # TT D-shaft
    for bn in BODIES: F['ecc_' + bn], F['washer_' + bn] = ecc(bn)
    return F

# gear phases (2D in each gear plane, local xy = world (y, z))
def g2d(z, c, a): return affinity.translate(affinity.rotate(gp(z), a, origin=(0, 0)), c[0], c[1])
def phases():
    s = (SH_Y, SH_Z)
    pc = max((g2d(ZC, CPD, a).distance(g2d(ZS, s, 0)), a) for a in np.linspace(0, 360 / ZC, 145))[1]
    pm = max((g2d(ZP, MOT, a).distance(g2d(ZB, CPD, pc)), a) for a in np.linspace(0, 360 / ZP, 145))[1]
    return pc, pm
PC, PM = phases()

def pose_all(F, bodies, t):
    """everything at crank angle t (degrees)."""
    P = {}
    for bn in BODIES:
        P.update({f'{bn}:{n}': m for n, m in pose_body(bodies[bn], bn, t).items()})
        b = BODIES[bn]
        P[f'ecc:{bn}'] = on_shaft(F['ecc_' + bn], b['drive'], t + b['phase'])
        P[f'washer:{bn}'] = on_shaft(F['washer_' + bn], b['drive'], t + b['phase'])
    P['shaft'] = on_shaft(F['shaft_local'], SHAFT_X0, t)
    # the shaft gear turns with the shaft: local rotation -t (see on_shaft); compound +t ZS/ZC; pinion -t RATIO
    P['g30'] = at_yz(F['g30'], GA, (SH_Y, SH_Z), -t)
    P['g_comp'] = at_yz(F['g_comp'], GA, CPD, PC + t * ZS / ZC)
    P['g_pin'] = at_yz(F['g_pin'], GB, MOT, PM - t * RATIO)
    for k in ('back', 'sun', 'tube', 'rear', 'frame', 'gearbox', 'motor'): P[k] = F[k]
    P['back'] = F['back'] + F['caps'] + F['screws']
    return P

def union(ms):
    u = None
    for m in ms: u = m if u is None else u + m
    return u

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.stl'): os.remove(os.path.join(OUT, f))
    F = fixed()
    bodies = {bn: body_parts(bn) for bn in BODIES}
    for bn in BODIES:
        for n, m in bodies[bn].items():
            if m.volume() < 1: print('EMPTY', n)
    print('screws M3 x', {k: v['screw'] for k, v in BODIES.items()})
    print('Z', {k: round(v, 1) for k, v in Z.items()}, 'LIP_Z', round(LIP_Z, 2))
    print('bodies', {k: dict(e=round(v['e'], 2), R=round(v['R'], 2)) for k, v in BODIES.items()}, 'phases', round(PC, 2), round(PM, 2))
    if '--fast' not in sys.argv:
        worst = {}
        def note(k, g, t):
            if k not in worst or g < worst[k][0]: worst[k] = (g, t)
        groups_fixed = ['back', 'sun', 'tube', 'rear', 'frame', 'gearbox', 'motor']
        for t in range(0, 360, 15):
            P = pose_all(F, bodies, t)
            G = {bn: union([m for k, m in P.items() if k.startswith(bn + ':')]) for bn in BODIES}
            for bn in BODIES:
                G['disc:' + bn] = P[f'ecc:{bn}'] + P[f'washer:{bn}']
            G['shaft'] = P['shaft'] + P['g30']
            G['g_comp'] = P['g_comp']; G['g_pin'] = P['g_pin']
            for k in groups_fixed: G[k] = P[k]
            keys = list(G)
            # pairs that are meant to touch: each disc on the shaft; the motor in its bracket, the pinion on the motor
            skip = {frozenset(('shaft', 'disc:' + bn)) for bn in BODIES} | {frozenset(('motor', 'gearbox')), frozenset(('motor', 'g_pin'))}
            for i, a in enumerate(keys):
                for c in keys[i + 1:]:
                    if a in groups_fixed and c in groups_fixed: continue
                    if frozenset((a, c)) in skip: continue
                    note(f'{a}/{c}', G[a].min_gap(G[c], 0.6), t)
        bad = {k: (round(v[0], 2), v[1]) for k, v in worst.items() if v[0] < 0.6}
        print('closest pairs (< 0.6 mm):', dict(sorted(bad.items(), key=lambda q: q[1][0])))
        # the hidden parts stay hidden: the wave's cut lower edge never shows in the window
        win = sbox(*WIN); worst_show = 0.0
        for t in range(0, 360, 10):
            def posed(reg, bn): return affinity.rotate(reg, body_angle(bn, t), origin=(BODIES[bn]['pivot'], PIV_Y))
            cover = unary_union([posed(BODIES['mar']['sheets'][0][1], 'mar'), posed(BODIES['orilla']['sheets'][0][1], 'orilla')])
            low = posed(wave_reg.intersection(sbox(-20, -10, 140, 15.0)), 'ola')
            worst_show = max(worst_show, low.intersection(win).difference(cover).area)
        print('wave cut edge visible (mm2, worst):', round(worst_show, 3))
    # --- export (each part flat on its back face; sheets keep their art layout)
    for bn in BODIES:
        for n, m in bodies[bn].items(): to_tm(m.translate([0, 0, -m.bounding_box()[2]])).export(os.path.join(OUT, f'{n}.stl'))
        to_tm(F['ecc_' + bn]).export(os.path.join(OUT, f'excentrica-{bn}.stl'))
        to_tm(F['washer_' + bn]).export(os.path.join(OUT, f'arandela-{bn}.stl'))
    to_tm(F['cap_local']).export(os.path.join(OUT, 'tapon-pasador-x3.stl'))
    for k, n in (('back', 'fondo-cielo'), ('sun', 'sol'), ('tube', 'caja'), ('rear', 'caja-tapa-trasera'), ('frame', 'marco'), ('gearbox', 'soporte-engranajes')):
        to_tm(F[k]).export(os.path.join(OUT, f'{n}.stl'))
    to_tm(F['shaft_local']).export(os.path.join(OUT, 'eje-levas.stl'))
    to_tm(F['g30']).export(os.path.join(OUT, 'engranaje-26.stl'))
    to_tm(F['g_comp']).export(os.path.join(OUT, 'engranaje-doble-40-14.stl'))
    to_tm(F['g_pin']).export(os.path.join(OUT, 'pinon-motor-10.stl'))
    # --- data for the page: every mesh in art coordinates, plus how each moves
    def mesh(m):
        t_ = to_tm(m); return dict(v=np.round(t_.vertices, 2).ravel().tolist(), f=t_.faces.ravel().tolist())
    parts = []
    for bn, b in BODIES.items():
        for (n, reg, col) in b['sheets']:
            if n in bodies[bn]: parts.append(dict(name=n, color=col, body=bn, mesh=mesh(bodies[bn][n])))
        parts.append(dict(name=bn + '-brazo', color='#9aa3ad', body=bn, mesh=mesh(bodies[bn][bn + '-brazo'])))
        parts.append(dict(name='excentrica-' + bn, color='#e0a030', ecc=bn, mesh=mesh(F['ecc_' + bn] + F['washer_' + bn])))
    parts.append(dict(name='caps', color='#9aa3ad', fixed=True, mesh=mesh(F['caps'])))
    parts.append(dict(name='screws', color='#c0c4c8', fixed=True, mesh=mesh(F['screws'])))
    for k, col in (('back', '#efe6d2'), ('sun', '#c8372d'), ('tube', '#2b2b2b'), ('rear', '#2b2b2b'), ('frame', '#2b2b2b'),
                   ('gearbox', '#9aa3ad'), ('motor', '#f2c200')):
        parts.append(dict(name=k, color=col, fixed=True, mesh=mesh(F[k])))
    parts.append(dict(name='shaft', color='#c0c4c8', shaft=True, mesh=mesh(F['shaft_local'])))
    for k, c, x, n, ph in (('g30', (SH_Y, SH_Z), GA, -1, 0.0), ('g_comp', CPD, GA, ZS / ZC, PC), ('g_pin', MOT, GB, -RATIO, PM)):
        parts.append(dict(name=k, color='#e0a030', gear=dict(x=x, y=c[0], z=c[1], ratio=n, phase=ph), mesh=mesh(F[k])))
    data = dict(WIN=WIN, IX0=IX0, IX1=IX1, YB=YB, TOP=TOP, LIP_Z=LIP_Z, REAR=REAR, SH_Y=SH_Y, SH_Z=SH_Z, PIV_Y=PIV_Y,
                bodies={k: dict(pivot=v['pivot'], drive=v['drive'], e=v['e'], D=v['D'], phase=v['phase'], amp=v['amp']) for k, v in BODIES.items()},
                parts=parts, rpm=59.0 / RATIO, ratio=RATIO, shaft_x=SHAFT_X0)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wave-art-shared', 'living.json')
    json.dump(data, open(p, 'w'), separators=(',', ':'))
    print('ok', os.path.getsize(p) // 1024, 'KB json;', len([f for f in os.listdir(OUT) if f.endswith('.stl')]), 'STL')
