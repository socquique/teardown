# Wave theater: the layered-relief wave (wave_art.py) at the back of a box, and in front of it three twisted rollers
# that turn like a baroque stage sea, driven by the Bambu TT motor. Neighbouring rollers turn opposite ways, so the
# crests seem to roll toward you in layers.
#   python3 sims/strandbeest-print/theater.py [--web]   -> teardown-out/print/wave-theater/
import math, os, sys, json
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection
from shapely.geometry import Polygon, Point
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fidgets import cs, ext, cyl, disc, rot, to_tm, gear_poly
from objects import box, d_hole
import wave_art as WA

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'teardown-out', 'print', 'wave-theater')
SEG = 96
ART = WA.W                         # 110 mm art plate
T = 4.0                            # walls
IW = ART + 2.0                     # inner width (x)
X0, X1 = 0.0, IW                   # inner faces
H = 126.0                          # inner height (y up from the base top)
DEPTH = 64.0                       # inner depth (z toward the viewer, back panel at z = 0)
BASE = 4.0
M_ = 1.0; ZR = 20                  # roller gears: module 1, 20 teeth -> centre distance 20
# rollers: front-low to back-high, 20 mm apart so their gears mesh in a chain
ROLLERS = [dict(c=(30.0, 56.0), lobes=3, twist=-540.0, r=8.0, amp=1.5, color='#1d2f5e'),
           dict(c=(44.1, 41.9), lobes=4, twist=540.0, r=8.0, amp=1.4, color='#2f6db3'),
           dict(c=(58.2, 27.8), lobes=3, twist=-540.0, r=8.0, amp=1.5, color='#8cc8e8')]
# each c is (y height above the base top, z distance in front of the back panel)
L_ROLL = IW - 1.2
SH_R = 3.0                          # axle stubs

def profile(r, lobes, amp, n=180):
    """a rounded wave crest section: a circle swelled into `lobes` crests, each leaning (a breaking face)."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        k = (t * lobes / (2 * math.pi)) % 1.0
        crest = math.exp(-((k - 0.35) / 0.17) ** 2) + 0.45 * math.exp(-((k - 0.62) / 0.25) ** 2)   # steep front, long back
        rr = r - amp + 2.0 * amp * crest
        pts.append((rr * math.cos(t), rr * math.sin(t)))
    return Polygon(pts).buffer(0)

def roller(R):
    """a twisted crest roller along x with axle stubs; the right stub has a D flat for its gear."""
    body = Manifold.extrude(cs(profile(R['r'], R['lobes'], R['amp'])), L_ROLL, 200, R['twist'])
    stub_l = cyl(SH_R, T + 1.0, 0, 0, -(T + 1.0))
    stub_r = (cyl(SH_R, T + 5.0, 0, 0, L_ROLL) ^ box(-SH_R - 1, SH_R - 0.8, -SH_R - 1, SH_R + 1, L_ROLL - 1, L_ROLL + T + 6))   # ends in the gear plane
    m = body + stub_l + stub_r
    return m   # axis along +z here; placed along x later

def gp(z, bl=0.75): return gear_poly(z, M_, M_ * z / 2 + 0.8 * M_, M_ * z / 2 - 1.25 * M_ - 0.1, math.pi * M_ / 2 - bl / 2)

def build():
    parts = {}
    # --- the box: base, two walls, back panel with a pocket for the art plate, a top bar
    base = box(-T, IW + T, 0, BASE, -T, DEPTH + 4)                       # (x, y, z) with y up
    back = box(-T, IW + T, BASE, BASE + H, -T, 0) - box(0, ART, BASE + 6, BASE + 6 + ART, -2.0, 0.01)  # art sits in a 2 mm pocket
    def wall(x0):
        w = box(x0, x0 + T, BASE, BASE + H, 0, DEPTH)
        for R in ROLLERS:
            y, z = R['c']
            w = w - Manifold.cylinder(T + 2, SH_R + 0.35, SH_R + 0.35, SEG).rotate([0, 90, 0]).translate([x0 - 1, BASE + y, z])
        return w
    wl, wr = wall(-T), wall(IW)
    top = box(-T, IW + T, BASE + H, BASE + H + T, -T, DEPTH)
    # --- rollers placed along x (axis), centres from ROLLERS
    rl = []
    for i, R in enumerate(ROLLERS):
        y, z = R['c']
        m = roller(R).rotate([0, 90, 0])     # axis z -> x
        rl.append(m.translate([0.6, BASE + y, z]))
    # --- gears outside the right wall: one 20-tooth gear per roller, a 10/40 compound and the motor pinion
    gx = IW + T + 0.6                       # gear plane starts here (x), 4 mm thick
    GT = 4.0
    rg = []
    for i, R in enumerate(ROLLERS):
        y, z = R['c']
        g = ext(gp(ZR), GT) - d_hole(SH_R + 0.25, SH_R - 0.8 + 0.25, 0, GT + 2)
        rg.append((g, (BASE + y, z)))
    # compound 40/10: its 10 drives the first roller gear (centre distance 15), its 40 is driven by the motor's 10 (25)
    y1, z1 = BASE + ROLLERS[0]['c'][0], ROLLERS[0]['c'][1]
    ang = math.radians(-30)
    cpd = (y1 + 15 * math.sin(ang), z1 + 15 * math.cos(ang))             # below and in front of roller 1
    ang2 = math.radians(110)                                              # the motor sits up the side
    mot = (cpd[0] + 25 * math.sin(ang2), cpd[1] + 25 * math.cos(ang2))
    comp = ext(gp(10), GT, 0) + ext(gp(40), GT, GT + 0.6) - cyl(1.85, 20, 0, 0, -1)   # turns on a 3.5 mm pin from the wall
    pin_m = ext(gp(10), GT, 0) - (cyl(2.8, 9, 0, 0, -1) ^ box(-1.975, 1.975, -4, 4, -2, 9))   # TT D-shaft
    # the compound turns on a pin standing out of the right wall
    wr = wr + Manifold.cylinder(2 * GT + 1.6, 1.7, 1.7, SEG).rotate([0, 90, 0]).translate([IW + T - 0.01, cpd[0], cpd[1]])
    # motor: shaft face against a bracket, the gearbox body going up the side, a back plate behind it
    MB = gx + GT + 0.6 + GT + 0.5
    my, mz = mot
    def plate(x0):
        return box(x0, x0 + 3.0, 0, my + 42, mz - 15, mz + 15)
    bracket = plate(MB) - Manifold.cylinder(5, 4.5, 4.5, SEG).rotate([0, 90, 0]).translate([MB - 1, my, mz]) \
              - Manifold.cylinder(5, 2.05, 2.05, SEG).rotate([0, 90, 0]).translate([MB - 1, my + 11.15, mz]) \
              - box(MB - 1, MB + 4, my + 30.7 - 2.8, my + 30.7 + 2.8, mz - 2.3, mz + 2.3)
    mback = plate(MB + 3.0 + 18.8 + 0.2)
    motor = box(MB + 3.0, MB + 3.0 + 18.8, my - 11.2, my + 37.2, mz - 11.2, mz + 11.2)
    base = box(-T, MB + 3.0 + 18.8 + 3.2 + 4, 0, BASE, -T, DEPTH + 4)
    return dict(bracket=bracket, mback=mback, motor=motor, MB=MB, base=base, back=back, wl=wl, wr=wr, top=top, rollers=rl, rgears=rg, comp=comp, cpd=cpd, mot=mot, pin_m=pin_m, gx=gx, GT=GT)

def place_gear(g, yz, gx, deg, dz=0.0):
    """a gear built in its own xy plane (axis z) placed on the side wall: axis along x at (y, z)."""
    return g.rotate([0, 0, deg]).rotate([0, 90, 0]).translate([gx + dz, yz[0], yz[1]])

def pose(B, deg):
    """roller 1 turned by deg; rollers alternate; the compound and pinion follow."""
    P = {k: B[k] for k in ('base', 'back', 'wl', 'wr', 'top')}
    for i, (m, R) in enumerate(zip(B['rollers'], ROLLERS)):
        s = deg * (-1) ** i
        y, z = R['c']
        P[f'roller{i}'] = m.translate([0, -(BASE + y), -z]).rotate([s, 0, 0]).translate([0, BASE + y, z])
        P[f'rgear{i}'] = place_gear(B['rgears'][i][0], B['rgears'][i][1], B['gx'], -s + (9 if i % 2 else 0))   # alternate tooth phase
    P['compound'] = place_gear(B['comp'], B['cpd'], B['gx'], deg * 2 + 18)
    P['pinion'] = place_gear(B['pin_m'], B['mot'], B['gx'] + B['GT'] + 0.6, -deg * 8)
    return P

def mesh_phase(B):
    """search the gear phases that mesh (2D, in each gear plane)."""
    from shapely import affinity
    def at(poly, yz, a): return affinity.translate(affinity.rotate(poly, a, origin=(0, 0)), yz[1], yz[0])
    return None

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    B = build()
    # mesh phases: chain of equal gears alternates; search each offset so neighbours mesh
    from shapely import affinity
    def g2d(z, yz, a): return affinity.translate(affinity.rotate(gp(z), a - 90, origin=(0, 0)), yz[0], yz[1])   # 2D = world (y, z)
    yzs = [B['rgears'][i][1] for i in range(3)]
    ph = [0.0]
    for i in (1, 2):
        best = max((g2d(ZR, yzs[i], a).distance(g2d(ZR, yzs[i - 1], ph[i - 1])), a) for a in np.linspace(0, 18, 73))
        ph.append(best[1])
    pc = max((g2d(10, B['cpd'], a).distance(g2d(ZR, yzs[0], ph[0])), a) for a in np.linspace(0, 36, 73))[1]
    big = lambda a: g2d(40, B['cpd'], a)
    pm = max((g2d(10, B['mot'], a).distance(big(pc)), a) for a in np.linspace(0, 36, 73))[1]
    print('phases', [round(p, 2) for p in ph], round(pc, 2), round(pm, 2))
    def turn(m, yz, s_):   # turn about the x axis through (y, z)
        return m.translate([0, -yz[0], -yz[1]]).rotate([s_, 0, 0]).translate([0, yz[0], yz[1]])
    def poseP(deg):
        P = {k: B[k] for k in ('base', 'back', 'wl', 'wr', 'top', 'bracket', 'mback', 'motor')}
        for i, (m, R) in enumerate(zip(B['rollers'], ROLLERS)):
            s_ = deg * (-1) ** i; y, z = R['c']
            P[f'roller{i}'] = turn(m, (BASE + y, z), s_)
            P[f'rgear{i}'] = turn(place_gear(B['rgears'][i][0], yzs[i], B['gx'], ph[i]), yzs[i], s_)
        P['compound'] = turn(place_gear(B['comp'], B['cpd'], B['gx'], pc), B['cpd'], -deg * ZR / 10)
        P['pinion'] = turn(place_gear(B['pin_m'], B['mot'], B['gx'] + B['GT'] + 0.6, pm), B['mot'], deg * ZR / 10 * 40 / 10)
        return P
    pairs = [('roller0', 'roller1'), ('roller1', 'roller2'), ('roller0', 'roller2'), ('rgear0', 'rgear1'), ('rgear1', 'rgear2'),
             ('compound', 'rgear0'), ('compound', 'pinion'), ('compound', 'rgear1'), ('pinion', 'rgear0'), ('pinion', 'rgear1'),
             ('roller0', 'base'), ('roller2', 'back'), ('roller0', 'wl'), ('roller0', 'wr'), ('compound', 'base'), ('pinion', 'base'),
             ('compound', 'bracket'), ('pinion', 'wr'), ('compound', 'rgear2'), ('motor', 'wr'), ('motor', 'base'), ('rgear0', 'bracket'), ('rgear2', 'bracket')]
    worst = {}
    for deg in np.linspace(0, 120, 25):
        P = poseP(deg)
        for a, b in pairs:
            g = P[a].min_gap(P[b], 1.0)
            if (a, b) not in worst or g < worst[(a, b)][0]: worst[(a, b)] = (g, deg)
    print('min gaps:', {f'{a}/{b}': round(v[0], 3) for (a, b), v in worst.items()})
    names = {'base': 'base', 'back': 'fondo', 'wl': 'pared-izq', 'wr': 'pared-der', 'top': 'techo', 'bracket': 'soporte-motor', 'mback': 'tapa-motor'}
    for k, n in names.items(): to_tm(B[k]).export(os.path.join(OUT, f'teatro-{n}.stl'))
    for i, R in enumerate(ROLLERS): to_tm(roller(R)).export(os.path.join(OUT, f'teatro-rodillo-{i+1}.stl'))
    to_tm(ext(gp(ZR), B['GT']) - d_hole(SH_R + 0.25, SH_R - 0.8 + 0.25, 0, B['GT'] + 2)).export(os.path.join(OUT, 'teatro-engranaje-20-x3.stl'))
    to_tm(B['comp']).export(os.path.join(OUT, 'teatro-engranaje-40-10.stl')); to_tm(B['pin_m']).export(os.path.join(OUT, 'teatro-pinon-10-motor.stl'))
    json.dump(dict(IW=IW, T=T, H=H, DEPTH=DEPTH, BASE=BASE, ART=ART, L_ROLL=L_ROLL, rollers=ROLLERS, cpd=B['cpd'], mot=B['mot'], gx=B['gx'], GT=B['GT'], MB=B['MB'],
                   phases=dict(r=ph, c=pc, m=pm), rpm=59 / 8),
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wave-art-shared', 'theater.json'), 'w'), indent=1)
    print('roller rpm at 5 V:', round(59 / 8, 1))
