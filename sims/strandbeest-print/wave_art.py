# A breaking wave in layered relief, for a shadow-box frame. Every colour is a height band, so one filament change
# per band prints it on any printer (no AMS needed).
#   python3 sims/strandbeest-print/wave_art.py [--preview]   -> teardown-out/print/wave-art/
# The wave is drawn from curves (a logarithmic-spiral curl, a swell, foam claws along the lip), not traced from any
# picture. Bands nest: each sits entirely on the one below, so nothing prints in the air.
import math, os, sys
import numpy as np
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box as sbox
from shapely.ops import unary_union
from shapely import affinity

W = 110.0                               # art plate (square), fits a 120 mm frame
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'teardown-out', 'print', 'wave-art')
rng = np.random.default_rng(7)

def spiral(c, a, b, t0, t1, n=240):
    """logarithmic spiral r = a e^(b t) round c, t in radians (t grows inward when b < 0)."""
    t = np.linspace(t0, t1, n); r = a * np.exp(b * t)
    return np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)])

def band_along(pts, w0, w1):
    """a ribbon along a polyline whose width goes from w0 to w1 (outline polygon)."""
    pts = np.asarray(pts); d = np.gradient(pts, axis=0); d /= np.linalg.norm(d, axis=1)[:, None] + 1e-9
    nrm = np.column_stack([-d[:, 1], d[:, 0]]); w = np.linspace(w0, w1, len(pts))[:, None] / 2
    return Polygon(np.vstack([pts + nrm * w, (pts - nrm * w)[::-1]])).buffer(0)

def claws(edge, n, size, rot_out, seed, lean=0.7):
    """foam fingers along a curve: each a curling stroke ending in a round knuckle, leaning forward."""
    r = np.random.default_rng(seed); out = []
    pts = np.asarray(edge); L = len(pts)
    for i in np.linspace(3, L - 4, n).astype(int):
        p = pts[i]; d = pts[min(i + 2, L - 1)] - pts[max(i - 2, 0)]; d /= np.linalg.norm(d)
        nrm = np.array([-d[1], d[0]]) * rot_out
        s_ = size * (0.75 + 0.5 * r.random())
        # a little hooked finger: out, forward, and back round
        q = [p, p + nrm * s_ * 0.8, p + nrm * s_ * 1.5 + d * s_ * lean, p + nrm * s_ * 1.7 + d * s_ * (lean + 0.7),
             p + nrm * s_ * 1.35 + d * s_ * (lean + 1.0)]
        f = LineString(q).buffer(s_ * 0.26, cap_style=1, join_style=1)
        out.append(f.union(Point(q[-1]).buffer(s_ * 0.36, 16)).union(Point(q[2]).buffer(s_ * 0.3, 16)))
    return unary_union(out)

def design():
    frame = sbox(0, 0, W, W)
    sun = Point(84, 86).buffer(17, 64)
    xs = np.linspace(0, W, 240)
    sea_top = 24 + 3.5 * np.sin(xs / 11.0) + 2.5 * np.sin(xs / 4.7 + 1)
    sea = Polygon([(0, 0)] + list(zip(xs, sea_top)) + [(W, 0)])
    # the wave: a thick ribbon along a log spiral, from the swell on the right, up and over to the left, curling in
    C = (46, 54)
    path = spiral(C, 36, -0.17, -1.45, 3.9)
    wave_band = band_along(path, 38, 1.8)
    back = Polygon([(56, 24), (W, 20), (W, 34), (92, 34), (80, 30)])          # the back of the wave down to the sea
    body = unary_union([sea, wave_band, back]).buffer(1.5).buffer(-1.5)
    hollow = Point(C[0] + 1.5, C[1] - 1.0).buffer(9.0, 48)
    body = body.difference(hollow).intersection(frame)
    # water lines inside the wave, following the curl
    stripes_blue, stripes_light = [], []
    for k, (sh, w0, w1) in enumerate([(1.12, 7, 1.0), (0.98, 5, 0.9), (0.86, 4, 0.8), (0.75, 3, 0.6)]):
        pts = spiral(C, 36 * sh, -0.17, -1.35, 3.4)
        (stripes_blue if k % 2 else stripes_light).append(band_along(pts, w0, w1))
    for y0, ph in ((16, 0.0), (9, 1.7), (3, 2.9)):
        stripes_blue.append(band_along(np.column_stack([xs, y0 + 2.2 * np.sin(xs / 9 + ph)]), 3.0, 3.0))
    for y0, ph in ((12.5, 0.8), (6, 2.2)):
        stripes_light.append(band_along(np.column_stack([xs, y0 + 2.0 * np.sin(xs / 7 + ph)]), 1.5, 1.5))
    # foam: a white lip along the crest, two rows of claws, a few on the swell, spray
    # the crest's outer edge: the ribbon's outer side, from where it rises above the sea to the tip of the lip
    d_ = np.gradient(path, axis=0); d_ /= np.linalg.norm(d_, axis=1)[:, None]
    nrm = np.column_stack([-d_[:, 1], d_[:, 0]]); wv = np.linspace(38, 1.8, len(path))[:, None] / 2
    e1, e2 = path + nrm * wv, path - nrm * wv
    edge = e1 if np.linalg.norm(e1 - C, axis=1).mean() > np.linalg.norm(e2 - C, axis=1).mean() else e2
    sel = edge[int(len(edge) * 0.24):int(len(edge) * 0.93)]
    lip = band_along(sel - (sel - C) / np.linalg.norm(sel - C, axis=1)[:, None] * 1.2, 4.0, 1.2)
    row1 = claws(sel, 15, 5.0, -1, 3)
    inner = sel - (sel - C) / np.linalg.norm(sel - C, axis=1)[:, None] * 4.5
    row2 = claws(inner[10:-20], 9, 3.0, -1, 4)
    swell = claws(np.column_stack([xs[:95], sea_top[:95] - 0.5]), 9, 2.8, 1, 5, lean=1.0)
    spray = unary_union([Point(C[0] - 18 + rng.normal(0, 9), C[1] + 38 + rng.normal(0, 6)).buffer(0.7 + rng.random() * 1.6, 12) for _ in range(30)])
    foam = unary_union([lip, row1, row2, swell, spray])
    navy = body
    blue = navy.buffer(-2.0).union(unary_union(stripes_blue).intersection(navy.buffer(-0.8))).intersection(navy.buffer(-0.6))
    light = unary_union(stripes_light).intersection(blue.buffer(-0.6)).intersection(sbox(0, 9, W, W).union(sbox(0, 0, W, 14)))
    white = foam.intersection(frame.buffer(-1.0))
    return dict(sun=sun, navy=navy, blue=blue, light=light, white=white, frame=frame,
                sea=sea, wave_band=wave_band, back=back, foam_crest=unary_union([lip, row1, row2, spray]).intersection(frame.buffer(-1.0)),
                foam_sea=swell.intersection(frame.buffer(-1.0)), sea_top=(xs, sea_top))

BANDS = [  # name, z0, z1, colour
    ('crema', 0.0, 1.6, '#efe6d2'), ('rojo', 1.6, 2.4, '#c8372d'), ('marino', 2.4, 3.6, '#1d2f5e'),
    ('azul', 3.6, 4.8, '#2f6db3'), ('celeste', 4.8, 6.0, '#8cc8e8'), ('blanco', 6.0, 7.2, '#f8f8f4')]

def layers(D):
    """region printed in each band: the union of everything at or above it, so every band is supported."""
    white, light, blue, navy, sun = D['white'], D['light'], D['blue'], D['navy'], D['sun']
    L6 = white
    L5 = unary_union([light, L6])
    L4 = unary_union([blue, L5])
    L3 = unary_union([navy, L4])
    L2 = unary_union([sun, L3]).intersection(D['frame'])
    L1 = D['frame']
    return [L1, L2, L3, L4, L5, L6]

def preview(D, path):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.path import Path; from matplotlib.patches import PathPatch
    def patch(g, col):
        verts, codes = [], []
        for p in ([g] if g.geom_type == 'Polygon' else list(g.geoms)):
            for ring in [p.exterior] + list(p.interiors):
                c = np.asarray(ring.coords); verts += c.tolist(); codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
        return PathPatch(Path(verts, codes), fc=col, ec=(0, 0, 0, 0.35), lw=0.35)
    fig, ax = plt.subplots(figsize=(6, 6)); fig.patch.set_facecolor('#d9d4ca')
    for (name, z0, z1, col), reg in zip(BANDS, layers(D)):
        if not reg.is_empty: ax.add_patch(patch(reg, col))
    ax.add_patch(plt.Rectangle((-4, -4), W + 8, W + 8, fill=False, lw=14, ec='#161616'))
    ax.set_xlim(-8, W + 8); ax.set_ylim(-8, W + 8); ax.set_aspect('equal'); ax.axis('off')
    plt.savefig(path, dpi=130, bbox_inches='tight', facecolor='#d9d4ca')

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    D = design()
    preview(D, os.path.join(OUT, 'preview.png'))
    print('preview ok')

def build(D):
    """the art plate as one solid (bands stacked) plus one body per colour, the frame and its back."""
    from fidgets import ext, to_tm
    from manifold3d import Manifold
    import trimesh
    Ls = layers(D); bodies = []
    for (name, z0, z1, col), reg in zip(BANDS, Ls):
        reg = reg.buffer(0)
        if reg.is_empty: continue
        bodies.append((name, col, ext(reg, (z1 - z0) + (0.01 if name != 'blanco' else 0), z0)))
    plate = bodies[0][2]
    for _, _, b in bodies[1:]: plate = plate + b
    # frame: 124 square, a 104 window, a rebate behind for the 110 plate and a 2 mm back
    FW, WIN, DEP = 124.0, 104.0, 7.2 + 2.0 + 2.5
    def sq(c, h, z=0): return Manifold.cube([c, c, h]).translate([-c / 2, -c / 2, z])
    frame = sq(FW, DEP) - sq(WIN, DEP + 2, -1) - sq(W + 0.5, 7.2 + 2.0 + 0.01, 2.5)   # 2.5 mm lip in front
    frame = frame.translate([W / 2, W / 2, 0])
    back = sq(W + 0.2, 2.0).translate([W / 2, W / 2, 0])
    back = back - Manifold.cylinder(3, 4.2, 4.2, 48).translate([W / 2, W - 14, -1]) - Manifold.cube([4.2, 8, 3]).translate([W / 2 - 2.1, W - 22, -1])  # keyhole
    return plate, bodies, frame, back

if __name__ == '__main__' and '--build' in sys.argv:
    import trimesh
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fidgets import to_tm
    plate, bodies, frame, back = build(design())
    to_tm(plate).export(os.path.join(OUT, 'ola-cuadro-capas.stl'))
    for name, col, b in bodies: to_tm(b).export(os.path.join(OUT, f'ola-color-{BANDS.index(next(x for x in BANDS if x[0]==name))+1}-{name}.stl'))
    to_tm(frame).export(os.path.join(OUT, 'ola-marco.stl')); to_tm(back).export(os.path.join(OUT, 'ola-tapa-trasera.stl'))
    t = to_tm(plate); print('plate', t.extents.round(1), 'closed', t.is_watertight, 'vol cm3', round(t.volume / 1000, 1))
    for name, z0, z1, col in BANDS: print(f'  {z0:.1f}-{z1:.1f} mm  {name}')

if __name__ == '__main__' and '--web' in sys.argv:
    # the bands' outlines for the live page (sims/wave-art-live)
    import json
    from shapely.geometry.polygon import orient
    D = design(); out = {'W': W, 'bands': []}
    for (name, z0, z1, col), reg in zip(BANDS, layers(D)):
        reg = reg.buffer(0).simplify(0.06)
        polys = [reg] if reg.geom_type == 'Polygon' else list(reg.geoms)
        shapes = []
        for p in polys:
            if p.is_empty or p.area < 0.05: continue
            p = orient(p, 1.0)
            shapes.append({'outer': np.round(np.asarray(p.exterior.coords)[:-1], 2).tolist(),
                           'holes': [np.round(np.asarray(h.coords)[:-1], 2).tolist() for h in p.interiors if Polygon(h).area > 0.05]})
        out['bands'].append({'name': name, 'z0': z0, 'z1': z1, 'color': col, 'shapes': shapes})
    pth = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wave-art-shared', 'bands.json')
    json.dump(out, open(pth, 'w'), separators=(',', ':')); print(pth, os.path.getsize(pth) // 1024, 'KB')
