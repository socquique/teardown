# Coloured 3MF of the living picture, ready for Bambu Studio / OrcaSlicer: every part laid flat in its print
# orientation, tagged with its colour (3MF colour group, so the slicer offers to create one filament per colour),
# grouped one colour per plate so a plate never swaps filament.
#   python3 sims/strandbeest-print/export_3mf.py   -> teardown-out/print/living-wave/cuadro-vivo.3mf (+ por-placa/*.3mf)
import os, sys, math, zipfile, uuid, itertools
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv; sys.argv = [sys.argv[0]]
import living as L
from fidgets import to_tm
sys.argv = _argv

OUT = L.OUT
BED = 256.0; MARGIN = 6.0; GAP = 6.0          # P2S / A1 bed; keep off the edges
STRIDE = BED * 1.2                              # Bambu lays plates out 1/5 of a bed apart
COLOURS = {  # name, hex
    'marino': ('Azul marino', '#1D2F5E'), 'azul': ('Azul', '#2F6DB3'), 'celeste': ('Celeste', '#8CC8E8'),
    'blanco': ('Blanco', '#F8F8F4'), 'crema': ('Crema', '#EFE6D2'), 'rojo': ('Rojo', '#C8372D'),
    'negro': ('Negro', '#2B2B2B'), 'gris': ('Gris', '#9AA3AD')}
ORDER = list(COLOURS)

def parts():
    """(name, manifold, colour key) for every printed part."""
    F = L.fixed(); out = []
    for bn, b in L.BODIES.items():
        P = L.body_parts(bn)
        for i, (n, reg, col) in enumerate(b['sheets']):
            if n not in P: continue
            key = {L.NAVY: 'marino', L.BLUE: 'azul', L.LIGHT: 'celeste', L.WHITE: 'blanco'}[col]
            out.append((n, P[n], key))
        out.append((f'excentrica-{bn}', F['ecc_' + bn], 'gris'))
        out.append((f'arandela-{bn}', F['washer_' + bn], 'gris'))
    for k, n, c in (('back', 'fondo-cielo', 'crema'), ('sun', 'sol', 'rojo'), ('frame', 'marco', 'negro'),
                    ('base', 'caja-base', 'negro'), ('side_l', 'caja-lado-izq', 'negro'), ('side_r', 'caja-lado-der', 'negro'),
                    ('top', 'caja-techo', 'negro'), ('rear', 'caja-tapa-trasera', 'negro'),
                    ('bracket', 'soporte-motor', 'gris'), ('bearing', 'soporte-eje', 'gris')):
        out.append((n, F[k], c))
    for i in range(3): out.append((f'tapon-pasador-{i + 1}', F['cap_local'], 'gris'))
    out.append(('eje-levas', F['shaft_local'], 'gris'))
    out.append(('engranaje-26', F['g30'], 'gris'))
    out.append(('engranaje-doble-40-14', F['g_comp'], 'gris'))
    out.append(('pinon-motor-10', F['g_pin'], 'gris'))
    return out

ROTS = [np.eye(3)] + [trimesh.transformations.rotation_matrix(a, ax)[:3, :3]
                      for ax, a in (([1, 0, 0], math.pi), ([1, 0, 0], math.pi / 2), ([1, 0, 0], -math.pi / 2),
                                    ([0, 1, 0], math.pi / 2), ([0, 1, 0], -math.pi / 2))]

def lay_flat(tm):
    """the axis-aligned orientation with the most area touching the bed (ties: the lowest)."""
    best = None
    for R in ROTS:
        v = tm.vertices @ R.T
        z0 = v[:, 2].min()
        f = tm.faces; n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        a = np.linalg.norm(n, axis=1) / 2
        on = (np.abs(v[f][:, :, 2] - z0).max(axis=1) < 1e-3) & (n[:, 2] < 0)
        contact = a[on].sum(); h = v[:, 2].max() - z0
        score = (round(contact, 0), -h)
        if best is None or score > best[0]: best = (score, R)
    R = best[1]
    m = tm.copy(); m.vertices = m.vertices @ R.T
    m.vertices -= [m.bounds[0][0], m.bounds[0][1], m.bounds[0][2]]
    return m, best[0][0]

def footprint_turn(m):
    """turn about z so the longer side runs along x."""
    w, d = m.extents[:2]
    if d > w:
        m.vertices = m.vertices[:, [1, 0, 2]] * [1, -1, 1]
        m.vertices -= m.bounds[0]
    return m

def pack(items):
    """shelf packing of (name, mesh) into beds; returns [[(name, mesh, x, y), ...], ...]."""
    U = BED - 2 * MARGIN
    items = sorted(items, key=lambda it: -it[1].extents[1])
    beds = []
    for name, m in items:
        w, d = m.extents[:2]
        assert w <= U and d <= U, f'{name} does not fit the bed ({w:.0f} x {d:.0f})'
        placed = False
        for bed in beds:
            for shelf in bed['shelves']:
                if shelf['x'] + w <= U and d <= shelf['h']:
                    bed['items'].append((name, m, shelf['x'], shelf['y'])); shelf['x'] += w + GAP; placed = True; break
            if placed: break
            if bed['top'] + d <= U:
                bed['shelves'].append({'y': bed['top'], 'h': d, 'x': w + GAP}); bed['items'].append((name, m, 0.0, bed['top']))
                bed['top'] += d + GAP; placed = True; break
        if not placed:
            beds.append({'shelves': [{'y': 0.0, 'h': d, 'x': w + GAP}], 'items': [(name, m, 0.0, 0.0)], 'top': d + GAP})
    out = []
    for bed in beds:   # centre the group on the bed
        xs = [x + m.extents[0] for _, m, x, _ in bed['items']]; ys = [y + m.extents[1] for _, m, _, y in bed['items']]
        ox = (U - max(xs)) / 2 + MARGIN; oy = (U - max(ys)) / 2 + MARGIN
        out.append([(n, m, x + ox, y + oy) for n, m, x, y in bed['items']])
    return out

def write_3mf(path, objects, title):
    """objects: [(name, trimesh, colour key, (x, y))]. Standard 3MF core + materials colour group."""
    used = [k for k in ORDER if any(o[2] == k for o in objects)]
    model = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="es-ES" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">',
             f' <metadata name="Title">{title}</metadata>', ' <metadata name="Designer">socquique</metadata>',
             ' <metadata name="Application">teardown living.py</metadata>',
             ' <resources>', '  <m:colorgroup id="1">']
    model += [f'   <m:color color="{COLOURS[k][1]}FF"/>' for k in used]
    model += ['  </m:colorgroup>']
    build = []
    for i, (name, m, key, (x, y)) in enumerate(objects):
        oid = i + 2
        model.append(f'  <object id="{oid}" type="model" name="{name} ({COLOURS[key][0]})" pid="1" pindex="{used.index(key)}">')
        model.append('   <mesh><vertices>')
        model += [f'    <vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices]
        model.append('   </vertices><triangles>')
        model += [f'    <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces]
        model.append('   </triangles></mesh>')
        model.append('  </object>')
        build.append(f'  <item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {y:.3f} 0"/>')
    model += [' </resources>', ' <build>'] + build + [' </build>', '</model>']
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', '\n'.join(model))

if __name__ == '__main__':
    groups = {k: [] for k in ORDER}
    for name, man, key in parts():
        tm = to_tm(man)
        comps = man.decompose()
        if len(comps) > 1 and name in ('fondo-cielo',) or (len(comps) > 1 and not name.split('-')[-1] in ('espuma', 'rayas', 'agua')): print('WARNING: more than one piece in', name, len(comps))
        m, contact = lay_flat(tm)
        m = footprint_turn(m)
        groups[key].append((name, m))
    plates = []
    for key in ORDER:
        if groups[key]:
            for bed in pack(groups[key]): plates.append((key, bed))
    cols = math.ceil(math.sqrt(len(plates)))
    allobj = []
    pdir = os.path.join(OUT, 'por-placa'); os.makedirs(pdir, exist_ok=True)
    for f in os.listdir(pdir): os.remove(os.path.join(pdir, f))
    for i, (key, bed) in enumerate(plates):
        r, c = divmod(i, cols)
        ox, oy = c * STRIDE, -r * STRIDE
        allobj += [(n, m, key, (x + ox, y + oy)) for n, m, x, y in bed]
        tag = f'placa-{i + 1:02d}-{COLOURS[key][0].lower().replace(" ", "-")}'
        write_3mf(os.path.join(pdir, f'{tag}.3mf'), [(n, m, key, (x, y)) for n, m, x, y in bed], f'Cuadro vivo · {tag}')
        h = max(m.extents[2] for _, m, _, _ in bed)
        print(f'plate {i + 1}: {COLOURS[key][0]:12s} {len(bed):2d} parts, tallest {h:.1f} mm:', ', '.join(n for n, *_ in bed))
    write_3mf(os.path.join(OUT, 'cuadro-vivo.3mf'), allobj, 'Cuadro vivo · La ola')
    # check: read back
    for f in [os.path.join(OUT, 'cuadro-vivo.3mf')] + [os.path.join(pdir, f) for f in sorted(os.listdir(pdir))]:
        s = trimesh.load(f)
        geoms = list(s.geometry.values()) if hasattr(s, 'geometry') else [s]
        assert all(g.is_watertight for g in geoms), f
    print(len(plates), 'plates;', len(allobj), 'objects; all watertight on reload')
