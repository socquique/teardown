# Four fidgets, each checked over its whole motion before you print it.
#   python3 sims/strandbeest-print/fidgets.py [geneva|planetary|ratchet|lambda ...]  -> teardown-out/print/fidgets/
#
#   geneva     Geneva drive: turn the wheel, the cross steps 90° and locks. Print-in-place, one piece.
#   planetary  Herringbone planetary spinner: spin the ring, the sun and planets turn. Print-in-place.
#   ratchet    Ratchet spinner with printed spring pawls: clicks one way, locks the other. Print-in-place.
#   lambda     Chebyshev's lambda linkage: turn the wheel, the bird's head runs dead straight, then flies back.
#              Snap pins, one plate.
# Every check runs on the parts themselves (manifold min_gap / intersection), pose by pose.
import math, os, sys, json
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection
from shapely.geometry import Polygon, Point, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'teardown-out', 'print', 'fidgets')
SEG = 96
PIP = 0.35      # print-in-place gap between parts that must come apart
RUN = 0.2       # clearance kept while moving

def cs(poly):
    polys = [poly] if poly.geom_type == 'Polygon' else list(poly.geoms)
    loops = []
    for p in polys:
        p = orient(p, 1.0)
        loops.append(list(p.exterior.coords)[:-1]); loops += [list(i.coords)[:-1] for i in p.interiors]
    return CrossSection(loops)
def ext(poly, h, z=0, twist=0, div=0): return Manifold.extrude(cs(poly), h, div, twist).translate([0, 0, z])
def cyl(r, h, x=0, y=0, z=0, r2=None): return Manifold.cylinder(h, r, r if r2 is None else r2, SEG).translate([x, y, z])
def disc(r, c=(0, 0), n=SEG): return Point(c).buffer(r, n // 4)
def rot(m, deg, c=(0, 0)): return m.translate([-c[0], -c[1], 0]).rotate([0, 0, deg]).translate([c[0], c[1], 0])
def to_tm(m):
    mm = m.to_mesh(); t = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=True)
    keep = [b for b in t.split(only_watertight=False) if abs(b.volume) > 1e-3]  # drop zero-volume slivers
    return trimesh.util.concatenate(keep) if len(keep) > 1 else keep[0]
def gap(a, b, search=2.0): return a.min_gap(b, search)

def post_with_cap(c, r_post, z0, z1, r_cap):
    """a post from the base with a 45° cone cap: it holds a wheel down without any overhang."""
    p = cyl(r_post, z1 - z0, *c, z0)
    cone = Manifold.cylinder(r_cap - r_post, r_post, r_cap, SEG).translate([c[0], c[1], z1])
    return p + cone + cyl(r_cap, 1.2, *c, z1 + r_cap - r_post)
def bore_for_cap(c, r_hole, z_top, r_cap, clear):
    """the matching hole in the wheel: straight bore, then a 45° countersink up to the top face."""
    h = r_cap - r_hole + clear
    return cyl(r_hole, 50, *c, z_top - 50) + Manifold.cylinder(h + 0.01, r_hole, r_hole + h + 0.01, SEG).translate([c[0], c[1], z_top - h])

# ====================================================================== GENEVA
def geneva():
    n = 4; C = 30.0
    a = C * math.sin(math.pi / n); b = C * math.cos(math.pi / n)        # crank radius, wheel radius
    pin_r = 2.6; slot_w = 2 * pin_r + 1.0
    G = (C, 0.0)
    b_out = math.hypot(b, pin_r) + 0.4
    rl = C - b_out - 0.6 + 6.0                                          # locking disc radius
    Z_BASE, L1, L2 = 2.4, 3.0, 5.0                                      # base, driver disc, working layer
    z1 = Z_BASE + PIP                       # driver disc bottom
    z2 = z1 + L1 + PIP                      # working layer bottom (Geneva cross, locking disc, pin)
    ztop = z2 + L2
    # Geneva cross (working layer only): disc, 4 slots, 4 concave locking arcs
    gen = disc(b_out, G)
    for k in range(n):
        ang = math.pi + k * 2 * math.pi / n                             # slots point at the driver at k = 0
        d = (math.cos(ang), math.sin(ang))
        slot_in = C - a - 1.2
        p0 = (G[0] + d[0] * slot_in, G[1] + d[1] * slot_in); p1 = (G[0] + d[0] * (b_out + 2), G[1] + d[1] * (b_out + 2))
        gen = gen.difference(LineString([p0, p1]).buffer(slot_w / 2, cap_style=1))
        ab = ang + math.pi / n                                          # locking arcs on the bisectors
        cc = (G[0] + C * math.cos(ab), G[1] + C * math.sin(ab))
        gen = gen.difference(disc(rl + 0.45, cc))
    gen = gen.difference(disc(3.0 + 0.4, G))
    # driver: disc in L1 (knurled rim to turn it), locking disc with a crescent and the pin in L2
    R_RIM = C - 3.0 - 0.4 - PIP - 0.3                                    # clear of the cross's post
    rim = Polygon([((R_RIM - (0.8 if (i // 4) % 2 else 0)) * math.cos(2 * math.pi * i / 280),
                    (R_RIM - (0.8 if (i // 4) % 2 else 0)) * math.sin(2 * math.pi * i / 280)) for i in range(280)])
    lock = disc(rl).difference(disc(b_out + 1.6, (C, 0)))               # crescent faces the pin (θ = 0 at +x)
    drv = ext(rim.difference(disc(3.0 + 0.4)), L1, z1) + ext(lock.difference(disc(3.0 + 0.4)), L2 + PIP, z2 - PIP - 0.001)
    drv = drv + cyl(pin_r, L2 + PIP, a, 0, z2 - PIP - 0.001)
    # Geneva wheel: the cross plus an indicator fin on top
    gw = ext(gen, L2, z2) + ext(LineString([(G[0], G[1]), (G[0] + b * 0.75, 0)]).buffer(1.2).difference(disc(4.6 + 0.6, G)), 1.2, ztop - 0.001)
    # base with posts and a pedestal under the cross where the driver disc doesn't reach
    base_poly = unary_union([disc(R_RIM + 2), disc(b_out + 3, G)]).convex_hull
    base = ext(base_poly, Z_BASE)
    ped = disc(b_out + 1, G).difference(disc(R_RIM + PIP + 0.3)).difference(disc(3.0 + 0.4 + 0.2, G))
    base = base + ext(ped, L1 + PIP, Z_BASE - 0.001)
    r_cap = 4.6
    base = base + post_with_cap((0, 0), 3.0, 0, ztop + 0.45 - (r_cap - 3.0), r_cap)
    base = base + post_with_cap(G, 3.0, 0, ztop + 0.45 - (r_cap - 3.0), r_cap)
    drv = drv - bore_for_cap((0, 0), 3.0 + 0.4, ztop, r_cap, 0.0)
    gw = gw - bore_for_cap(G, 3.0 + 0.4, ztop, r_cap, 0.0)
    def gen_angle(th):
        t = (math.degrees(th) + 180) % 360 - 180
        if abs(t) <= 180 / n:
            px, py = a * math.cos(th), a * math.sin(th)
            return math.degrees(math.atan2(py, px - C)) - 180
        return -180 / n if t > 0 else 180 / n
    def pose(deg):
        th = math.radians(deg)
        return {'base': base, 'driver': rot(drv, deg), 'cross': rot(gw, gen_angle(th), G)}
    return dict(parts={'base': base, 'driver': drv, 'cross': gw}, pose=pose, sweep=range(0, 360, 3),
                pairs=[('driver', 'cross'), ('driver', 'base'), ('cross', 'base')], pip=True,
                note=f'Geneva n={n}, centres {C} mm, crank {a:.1f} mm, cross {2*b_out:.1f} mm')


# ====================================================================== PLANETARY (herringbone gear bearing)
def gear_poly(z, m, ra, rf, s_pitch, n_inv=12):
    """involute teeth: tip radius ra, root rf, tooth thickness s_pitch on the pitch circle (mm)."""
    pa = math.radians(20); rp = m * z / 2; rb = rp * math.cos(pa)
    inv = lambda a: math.tan(a) - a
    half = s_pitch / (2 * rp) + inv(pa)
    pts = []
    for i in range(z):
        c = 2 * math.pi * i / z
        fl = []
        for t in np.linspace(0, 1, n_inv):
            r = max(rb, rf) + (ra - max(rb, rf)) * t
            fl.append((r, half - inv(math.acos(min(1, rb / r)))))
        pts.append((rf * math.cos(c - half - 0.02), rf * math.sin(c - half - 0.02)))
        pts += [(r * math.cos(c - th), r * math.sin(c - th)) for r, th in fl]
        pts += [(r * math.cos(c + th), r * math.sin(c + th)) for r, th in reversed(fl)]
        pts.append((rf * math.cos(c + half + 0.02), rf * math.sin(c + half + 0.02)))
    return Polygon(pts).buffer(0)

def herring(poly, h, twist_deg, z=0):
    """herringbone: twist one way over the lower half, back over the upper half."""
    lo = Manifold.extrude(cs(poly), h / 2, 16, twist_deg)
    hi = Manifold.extrude(cs(poly), h / 2, 16, -twist_deg).rotate([0, 0, twist_deg]).translate([0, 0, h / 2])
    return (lo + hi).translate([0, 0, z])

def planetary():
    m = 1.5; Zs, Zp, Zr = 12, 12, 36; N = 4                       # (Zs + Zr) / N = 12: planets fit evenly
    H = 11.0; beta = math.radians(25); BL = 0.8; CL = 0.45; BLR = 1.3   # print-in-place backlash
    rs, rp_, rr = m * Zs / 2, m * Zp / 2, m * Zr / 2; cd = rs + rp_
    tw = lambda r: math.degrees((H / 2) * math.tan(beta) / r)      # twist over half the height
    ext_gear = lambda z: gear_poly(z, m, m * z / 2 + 0.8 * m, m * z / 2 - m - CL, math.pi * m / 2 - BL / 2)  # short teeth: no knife tips
    sun_p = ext_gear(Zs).difference(Polygon([(3.5 * math.cos(a), 3.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 7)[:-1]]))
    planet_p = ext_gear(Zp)
    ring_hole = gear_poly(Zr, m, rr + m + CL, rr - 0.8 * m, math.pi * m / 2 + BLR - BL / 2)   # the ring's tooth spaces as a gear
    R_OUT = rr + m + CL + 6.0
    knurl = Polygon([((R_OUT - (0.9 if (i // 3) % 2 else 0)) * math.cos(2 * math.pi * i / 300),
                      (R_OUT - (0.9 if (i // 3) % 2 else 0)) * math.sin(2 * math.pi * i / 300)) for i in range(300)])
    sun = herring(sun_p, H, tw(rs))
    ring = herring(knurl.difference(ring_hole), H, -tw(rr))   # internal mesh: same hand as the planets
    planet0 = herring(planet_p, H, -tw(rp_))
    # phase each planet so its teeth sit in the sun's and ring's gaps (searched on the z = 0 section)
    def planet_at(gamma, spin):
        return rot(rot(planet0, spin).translate([cd, 0, 0]), gamma)
    best = None
    for k in range(120):                                            # planet phase against the sun
        spin = 360 / Zp * k / 120
        g = shift(affinity_rot(planet_p, spin, (0, 0)), cd, 0).distance(sun_p)
        if best is None or g > best[0]: best = (g, spin)
    spin0 = best[1]
    p1 = shift(affinity_rot(planet_p, spin0, (0, 0)), cd, 0)
    ring_body = knurl.difference(ring_hole)
    best = None
    for k in range(120):                                            # then the ring against that planet
        r0 = 360 / Zr * k / 120
        g = affinity_rot(ring_body, r0, (0, 0)).distance(p1)
        if best is None or g > best[0]: best = (g, r0)
    ring = rot(ring, best[1]); R0 = best[1]
    planets = []
    for i in range(N):
        gamma = 360 / N * i
        planets.append(planet_at(gamma, spin0 + gamma * (Zs / Zp)))   # rolling the planet round the sun keeps the mesh
    parts = {'ring': ring, 'sun': sun}
    for i, p in enumerate(planets): parts[f'planet{i+1}'] = p
    def pose(psi):
        # sun held still, ring turned by psi: carrier c = psi Zr/(Zr+Zs), planet spin = c (1 + Zs/Zp)
        c = psi * Zr / (Zr + Zs)
        P = {'ring': rot(ring, psi), 'sun': sun}  # ring already carries its phase R0
        for i in range(N):
            gamma = 360 / N * i
            P[f'planet{i+1}'] = planet_at(gamma + c, spin0 + (gamma + c) * (Zs / Zp))  # rot() about the centre adds gamma + c
        return P
    pairs = [('sun', f'planet{i+1}') for i in range(N)] + [('ring', f'planet{i+1}') for i in range(N)] + \
            [(f'planet{i+1}', f'planet{(i+1)%N+1}') for i in range(N)]
    return dict(parts=parts, pose=pose, sweep=np.linspace(0, 360 / Zr * 3, 13), pairs=pairs, pip=True,
                note=f'herringbone m{m}, sun {Zs} / planets {N}x{Zp} / ring {Zr}, {2*R_OUT:.0f} mm, {H} mm tall, helix {math.degrees(beta):.0f}°')

def affinity_rot(p, deg, c):
    from shapely import affinity; return affinity.rotate(p, deg, origin=c)
def shift(p, x, y):
    from shapely import affinity; return affinity.translate(p, x, y)

# ====================================================================== RATCHET (printed spring pawls)
def ratchet():
    N = 24; R_V, R_T = 21.0, 19.4                                   # tooth valleys and tips (inside the ring)
    H = 10.0; ZT = 4.0                                              # height; teeth and pawls below ZT, bearing above
    R_OUT = 29.0; R_HUB = 16.4; R_CORE = 11.0
    # ring teeth: saw profile, ramp rising as the angle grows, then a radial drop
    pts = []
    for i in range(N):
        a0 = 2 * math.pi * i / N; da = 2 * math.pi / N
        for t in np.linspace(0, 0.54, 8):                           # flat valley: room for a pawl tip
            pts.append((R_V * math.cos(a0 + da * t), R_V * math.sin(a0 + da * t)))
        for t in np.linspace(0.54, 0.92, 10):                       # ramp
            r = R_V - (R_V - R_T) * (t - 0.54) / 0.38
            pts.append((r * math.cos(a0 + da * t), r * math.sin(a0 + da * t)))
        pts.append((R_T * math.cos(a0 + da * 0.95), R_T * math.sin(a0 + da * 0.95)))   # the drop: what the pawl stops on
    teeth_hole = Polygon(pts).buffer(0)
    knurl = Polygon([((R_OUT - (0.9 if (i // 3) % 2 else 0)) * math.cos(2 * math.pi * i / 300),
                      (R_OUT - (0.9 if (i // 3) % 2 else 0)) * math.sin(2 * math.pi * i / 300)) for i in range(300)])
    ring = ext(knurl.difference(teeth_hole), ZT, 0)
    # bearing above: ring bore R_HUB + PIP with a 45° V ridge pointing in; the hub carries the matching groove
    def revolve_profile(prof):
        return Manifold.revolve(CrossSection([prof]), SEG)
    rb = R_HUB + PIP; zc = ZT + (H - ZT) / 2; vd = 2.0
    ring_b = revolve_profile([(rb, ZT), (R_OUT - 0.9, ZT), (R_OUT - 0.9, H), (rb, H), (rb, zc + vd), (rb - vd, zc), (rb, zc - vd)])
    ring = ring + ring_b
    hub_b = revolve_profile([(0.01, ZT - 0.01), (R_HUB, ZT - 0.01), (R_HUB, zc - vd - PIP * 1.41), (R_HUB - vd - PIP * 0.0, zc - PIP * 0.41),
                             (R_HUB - vd - PIP * 0.0, zc + PIP * 0.41), (R_HUB, zc + vd + PIP * 1.41), (R_HUB, H), (0.01, H)])
    # pawls: three curved spring arms from the core, tips resting in tooth valleys
    hub_t = disc(R_CORE)
    tip_r_out = R_V - PIP
    arms = []
    for k in range(3):
        base = 2 * math.pi * k / 3
        a_tip = base + 2 * math.pi / N * 0.5                        # mid-valley, clear of both flanks
        arc = [((R_HUB - 0.8) * math.cos(a_tip - t), (R_HUB - 0.8) * math.sin(a_tip - t)) for t in np.linspace(0.05, 0.95, 20)]
        arm = LineString(arc).buffer(0.6, cap_style=2)              # 1.2 mm spring
        root = LineString([(R_CORE * math.cos(a_tip - 0.95), R_CORE * math.sin(a_tip - 0.95)), arc[-1]]).buffer(1.1)
        # the tip: a wedge from the arm out to the valley, ramp-shaped like the teeth
        aw = 2 * math.pi / N
        tip = Polygon([((R_HUB - 1.4) * math.cos(a_tip - 0.10), (R_HUB - 1.4) * math.sin(a_tip - 0.10)),
                       ((R_HUB - 1.4) * math.cos(a_tip + 0.02), (R_HUB - 1.4) * math.sin(a_tip + 0.02)),
                       (tip_r_out * math.cos(a_tip + 0.02), tip_r_out * math.sin(a_tip + 0.02)),
                       (tip_r_out * math.cos(a_tip - 0.05), tip_r_out * math.sin(a_tip - 0.05))])
        arms.append(unary_union([arm, root, tip]))
    hub2d = unary_union([hub_t] + arms)
    hub = ext(hub2d.difference(disc(R_CORE - 0.5)), ZT - 0.4, 0) + ext(disc(R_CORE), ZT, 0) + hub_b   # pawls stop 0.4 below the ring's bearing
    hub = hub - Manifold.sphere(14, SEG).translate([0, 0, H + 14 - 1.6])   # thumb dimple on top
    # find the tooth phase that leaves every pawl tip PIP clear of the ring
    best = None
    for k in range(240):
        r0 = 360 / N * k / 240
        g = rot(ring, r0).min_gap(hub, 1.0)
        if best is None or g > best[0]: best = (g, r0)
    ring = rot(ring, best[1])
    def pose(d): return {'ring': rot(ring, d), 'hub': hub}
    return dict(parts={'ring': ring, 'hub': hub}, pose=pose, sweep=[], pairs=[('ring', 'hub')], pip=True,
                note=f'{N} teeth, 3 spring pawls 1.2 mm, {2*R_OUT:.0f} mm, {H} mm tall', extra=dict(N=N, R_V=R_V, R_T=R_T, tip=tip_r_out))

# ====================================================================== LAMBDA (Chebyshev), snap pins
def lam():
    import itertools
    sys.argv = [sys.argv[0], '--scale', '1.0']
    import walker as W                                              # snap pins and washers from the walker
    u = 9.0; T = 3.0; GAP = 0.4; PITCH = T + GAP; R = 5.0
    A = (0.0, 0.0); D = (2 * u, 0.0)
    def pose_j(th):
        B = (u * math.cos(th), u * math.sin(th))
        dx, dy = D[0] - B[0], D[1] - B[1]; d = math.hypot(dx, dy); r = 2.5 * u
        a_ = d / 2; h = math.sqrt(max(0, r * r - a_ * a_)); mx, my = B[0] + dx / 2, B[1] + dy / 2
        C = max([(mx + h * dy / d, my - h * dx / d), (mx - h * dy / d, my + h * dx / d)], key=lambda q: q[1])
        P = (2 * C[0] - B[0], 2 * C[1] - B[1])
        return dict(A=A, B=B, C=C, D=D, P=P)
    J0 = pose_j(0.0)
    WR = 2 * u - 5.0                                                # thumb wheel: clear of the pin and washer at D
    PATH = [pose_j(math.radians(n))['P'] for n in range(360)]
    y_line = min(p[1] for p in PATH)
    bird = unary_union([disc(5.5, (0, 7.5)), Polygon([(4.5, 9), (11, 8.2), (4.8, 6.4)]), disc(1.2, (1.5, 9)).buffer(0)])
    bird = bird.difference(disc(1.1, (1.8, 9.0)))                   # an eye
    shapes = {
        'wheel': (['A', 'B'], lambda J: Polygon([((WR - (0.8 if (i // 3) % 2 else 0)) * math.cos(2 * math.pi * i / 240),
                                                   (WR - (0.8 if (i // 3) % 2 else 0)) * math.sin(2 * math.pi * i / 240)) for i in range(240)])),
        'rocker': (['D', 'C'], lambda J: LineString([J['D'], J['C']]).buffer(R)),
        'coupler': (['B', 'C', 'P'], lambda J: unary_union([LineString([J['B'], J['P']]).buffer(R),
                                                              shift(bird, *J['P'])])),
    }
    x0 = min(p[0] for p in PATH) - 6; x1 = max(p[0] for p in PATH) + 12
    base_shape = unary_union([LineString([A, D]).buffer(R + 2), disc(R + 2, A), disc(R + 2, D),
                              LineString([(-WR + 4, -6), (-WR - 18, -6)]).buffer(7),       # handle
                              LineString([D, (D[0] + 14, y_line - 9)]).buffer(4.5),        # strut up to the branch
                              LineString([(x0, y_line - 9), (x1, y_line - 9)]).buffer(2.5, cap_style=1)])  # the branch
    def placed(name, J):
        js, f = shapes[name]; return f(J)
    # layer search over a full turn, as for the legs
    names = ['wheel', 'rocker', 'coupler']
    clash = {}
    joints = {'A': ['base', 'wheel'], 'B': ['wheel', 'coupler'], 'C': ['coupler', 'rocker'], 'D': ['base', 'rocker']}
    hits = {k: set() for k in joints}
    for n in range(0, 360, 2):
        J = pose_j(math.radians(n)); out = {nm: placed(nm, J) for nm in names}; out['base'] = base_shape
        for a, b in itertools.combinations(out, 2):
            if out[a].distance(out[b]) < 0.6: clash[(a, b)] = clash[(b, a)] = True
        for k, mem in joints.items():
            for nm in out:
                if nm not in mem and out[nm].distance(Point(J[k])) < W.HOLE / 2 + 0.6: hits[k].add(nm)
    best = None
    for lay in itertools.product(range(1, 6), repeat=3):
        L = dict(zip(names, lay)); L['base'] = 0
        if any(clash.get((a, b)) and L[a] == L[b] for a, b in itertools.combinations(L, 2)): continue
        ok = True; sp = 0
        for k, mem in joints.items():
            ls = [L[m] for m in mem]
            if len(set(ls)) < 2 or any(min(ls) <= L[o] <= max(ls) for o in hits[k]): ok = False; break
            sp += max(ls) - min(ls)
        if ok and (best is None or sp < best[0]): best = (sp, L)
    assert best, (clash.keys(), hits)
    LAY = best[1]
    def holes(m, name, js):
        for k in js:
            if k == 'P': continue
            m = m - cyl(W.HOLE / 2, T + 2, *J0[k], -1)
            mem = joints[k]; ls = {mm: LAY[mm] for mm in mem}
            if ls[name] == min(ls.values()): m = m - cyl(W.CB_D / 2, W.CB_H + 0.01, *J0[k], -0.01)
            if ls[name] == max(ls.values()): m = m - cyl(W.CB_D / 2, W.CB_H + 0.01, *J0[k], T - W.CB_H)
        return m
    parts = {'base': holes(ext(base_shape, T), 'base', ['A', 'D'])}
    for nm in names:
        js, f = shapes[nm]; parts[nm] = holes(ext(f(J0), T), nm, js)
    z = lambda nm: LAY[nm] * PITCH
    def rigid(nm, J):
        js = shapes[nm][0]; o0, p0, o, p = J0[js[0]], J0[js[1]], J[js[0]], J[js[1]]
        r = math.degrees(math.atan2(p[1] - o[1], p[0] - o[0]) - math.atan2(p0[1] - o0[1], p0[0] - o0[0]))
        return rot(parts[nm], r, o0).translate([o[0] - o0[0], o[1] - o0[1], z(nm)])
    def pose(deg):
        J = pose_j(math.radians(deg)); P = {'base': parts['base']}
        for nm in names: P[nm] = rigid(nm, J)
        return P
    pins = {}
    for k, mem in joints.items():
        ls = [LAY[m] for m in mem]; sp = round((max(ls) - min(ls)) * PITCH + T, 1)
        pins.setdefault(sp, []).append(k)
    washers = [(k, l) for k, mem in joints.items() for l in range(min(LAY[m] for m in mem) + 1, max(LAY[m] for m in mem)) if l not in [LAY[m] for m in mem]]
    for sp, ks in pins.items(): parts[f'pin-{sp}mm-' + ''.join(ks)] = W.pin(sp)
    for i, _ in enumerate(washers):  # slim washers (6.4 mm): the rocker passes 3.8 mm from B
        parts[f'washer{i+1}'] = cyl(3.2, T, 0, 0, 0) - cyl((W.HOLE + 0.3) / 2, T + 2, 0, 0, -1)
    moving = ['base'] + names
    return dict(parts=parts, pose=pose, sweep=range(0, 360, 4), pairs=list(itertools.combinations(moving, 2)), pip=False,
                note=f'unit {u} mm: crank {u}, ground {2*u}, links {2.5*u}, coupler {5*u}; straight run {(max(p[0] for p in PATH if p[1] < y_line + 0.02*u) - min(p[0] for p in PATH if p[1] < y_line + 0.02*u)):.0f} mm; layers {LAY}; pins {pins}; washers {washers}',
                layers=LAY, pose_j=pose_j)

FIDGETS = {'geneva': geneva, 'planetary': planetary, 'ratchet': ratchet, 'lambda': lam}

def check(f, name):
    parts = f['parts']
    res = {'name': name, 'note': f['note']}
    # print pose: separate bodies need PIP clearance
    if f['pip']:
        res['print_gaps'] = {f'{a}/{b}': round(gap(parts[a], parts[b]), 3) for a, b in f['pairs']}
    worst = {}
    for s in f['sweep']:
        P = f['pose'](s)
        for a, b in f['pairs']:
            g = gap(P[a], P[b], 1.0)
            if (a, b) not in worst or g < worst[(a, b)][0]: worst[(a, b)] = (g, s)
    res['run_min_gap'] = {f'{a}/{b}': (round(v[0], 3), v[1]) for (a, b), v in worst.items()}
    res['closed'] = {k: to_tm(v).is_watertight for k, v in parts.items()}
    return res

if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if a in FIDGETS] or list(FIDGETS)
    os.makedirs(OUT, exist_ok=True)
    for nm in names:
        f = FIDGETS[nm]()
        d = os.path.join(OUT, nm); os.makedirs(d, exist_ok=True)
        allp = None; x = y = rowh = 0; placed = []
        for k, m in f['parts'].items():
            to_tm(m).export(os.path.join(d, f'{nm}-{k}.stl'))
            if f['pip']:
                allp = m if allp is None else allp + m
            else:  # lay the parts out side by side on one plate
                t = to_tm(m); t.apply_translation(-t.bounds[0])
                if x + t.extents[0] > 175: x = 0; y += rowh + 3; rowh = 0
                t.apply_translation([x, y, 0]); placed.append(t); x += t.extents[0] + 3; rowh = max(rowh, t.extents[1])
        if f['pip']: to_tm(allp).export(os.path.join(d, f'{nm}-print-in-place.stl'))
        else: trimesh.util.concatenate(placed).export(os.path.join(d, f'{nm}-plate.stl'))
        r = check(f, nm)
        print(json.dumps(r, indent=1))
