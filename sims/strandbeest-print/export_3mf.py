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

CK = None
def parts():
    """(name, [(manifold, colour key), ...]) for every printed piece; several entries = one multicolour print (AMS)."""
    F = L.fixed(); out = []
    ck = {L.NAVY: 'marino', L.BLUE: 'azul', L.LIGHT: 'celeste', L.WHITE: 'blanco'}
    for bn, b in L.BODIES.items():
        P = L.body_parts(bn)
        out.append((bn, [(P[n], ck[col]) for (n, reg, col) in b['sheets'] if n in P]))
        out.append((f'{bn}-brazo', [(P[bn + '-brazo'], 'gris')]))
        out.append((f'excentrica-{bn}', [(F['ecc_' + bn], 'gris')]))
        out.append((f'arandela-{bn}', [(F['washer_' + bn], 'gris')]))
    out.append(('cielo-y-sol', [(F['back'], 'crema'), (F['sun'], 'rojo')]))
    for k, n, c in (('tube', 'caja', 'negro'), ('frame', 'marco', 'negro'), ('rear', 'tapa-trasera', 'negro'),
                    ('gearbox', 'soporte-engranajes', 'gris')):
        out.append((n, [(F[k], c)]))
    for i in range(3): out.append((f'tapon-pasador-{i + 1}', [(F['cap_local'], 'gris')]))
    out.append(('eje-levas', [(F['shaft_local'], 'gris')]))
    out.append(('engranaje-26', [(F['g30'], 'gris')]))
    out.append(('engranaje-doble-40-14', [(F['g_comp'], 'gris')]))
    out.append(('pinon-motor-10', [(F['g_pin'], 'gris')]))
    return out

FORCED = {'caja': np.eye(3),                                                     # standing on its back rim: walls vertical
          'soporte-engranajes': trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])[:3, :3]}   # on its rails

ROTS = [np.eye(3)] + [trimesh.transformations.rotation_matrix(a, ax)[:3, :3]
                      for ax, a in (([1, 0, 0], math.pi), ([1, 0, 0], math.pi / 2), ([1, 0, 0], -math.pi / 2),
                                    ([0, 1, 0], math.pi / 2), ([0, 1, 0], -math.pi / 2))]

def lay_flat(tms, R=None):
    """the axis-aligned orientation with the most area touching the bed (ties: the lowest); same turn for every part."""
    tm = trimesh.util.concatenate(tms)
    if R is None:
        best = None
        for Rc in ROTS:
            v = tm.vertices @ Rc.T
            z0 = v[:, 2].min()
            f = tm.faces; n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
            a = np.linalg.norm(n, axis=1) / 2
            on = (np.abs(v[f][:, :, 2] - z0).max(axis=1) < 1e-3) & (n[:, 2] < 0)
            score = (round(a[on].sum(), 0), -(v[:, 2].max() - z0))
            if best is None or score > best[0]: best = (score, Rc)
        R = best[1]
    out = []
    for t in tms:
        m = t.copy(); m.vertices = m.vertices @ R.T; out.append(m)
    lo = np.min([m.bounds[0] for m in out], axis=0)
    for m in out: m.vertices -= lo
    return out

def footprint_turn(ms):
    """turn about z so the longer side runs along x."""
    tm = trimesh.util.concatenate(ms)
    w, d = tm.extents[:2]
    if d > w:
        for m in ms: m.vertices = m.vertices[:, [1, 0, 2]] * [1, -1, 1]
        lo = np.min([m.bounds[0] for m in ms], axis=0)
        for m in ms: m.vertices -= lo
    return ms

def ext_of(ms): return trimesh.util.concatenate(ms).extents if isinstance(ms, list) else ms.extents
def pack(items):
    """shelf packing of (name, mesh) into beds; returns [[(name, mesh, x, y), ...], ...]."""
    U = BED - 2 * MARGIN
    items = sorted(items, key=lambda it: -ext_of(it[1])[1])
    beds = []
    for name, m in items:
        w, d = ext_of(m)[:2]
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
        xs = [x + ext_of(m)[0] for _, m, x, _ in bed['items']]; ys = [y + ext_of(m)[1] for _, m, _, y in bed['items']]
        ox = (U - max(xs)) / 2 + MARGIN; oy = (U - max(ys)) / 2 + MARGIN
        out.append([(n, m, x + ox, y + oy) for n, m, x, y in bed['items']])
    return out

def write_3mf(path, objects, title):
    """objects: [(name, [(trimesh, colour key), ...], (x, y))]. Standard 3MF core + materials colour group; a piece with
    several colours is one object made of components, one per colour (Bambu Studio maps each to a filament)."""
    used = [k for k in ORDER if any(c == k for o in objects for _, c in o[1])]
    model = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="es-ES" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">',
             f' <metadata name="Title">{title}</metadata>', ' <metadata name="Designer">socquique</metadata>',
             ' <resources>', '  <m:colorgroup id="1">']
    model += [f'   <m:color color="{COLOURS[k][1]}FF"/>' for k in used]
    model += ['  </m:colorgroup>']
    build = []; oid = 2
    def mesh_obj(name, m, key):
        nonlocal oid
        i = oid; oid += 1
        model.append(f'  <object id="{i}" type="model" name="{name}" pid="1" pindex="{used.index(key)}">')
        model.append('   <mesh><vertices>')
        model.extend(f'    <vertex x="{a:.6f}" y="{b:.6f}" z="{c:.6f}"/>' for a, b, c in m.vertices)
        model.append('   </vertices><triangles>')
        model.extend(f'    <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        model.append('   </triangles></mesh>')
        model.append('  </object>')
        return i
    for name, parts_, (x, y) in objects:
        if len(parts_) == 1:
            top = mesh_obj(f'{name} ({COLOURS[parts_[0][1]][0]})', parts_[0][0], parts_[0][1])
        else:
            ids = [mesh_obj(f'{name} - {COLOURS[c][0]}', m, c) for m, c in parts_]
            top = oid; oid += 1
            model.append(f'  <object id="{top}" type="model" name="{name}"><components>')
            model.extend(f'   <component objectid="{i}"/>' for i in ids)
            model.append('  </components></object>')
        build.append(f'  <item objectid="{top}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {y:.3f} 0"/>')
    model += [' </resources>', ' <build>'] + build + [' </build>', '</model>']
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', '\n'.join(model))

PLATES = [  # (plate name, pieces) — AMS plates mix colours inside one piece; one-colour plates need no swaps
    ('olas-AMS', ['ola', 'mar', 'orilla']),
    ('cielo-y-sol-AMS', ['cielo-y-sol']),
    ('caja-negro', ['caja']),
    ('marco-negro', ['marco']),
    ('tapa-negro', ['tapa-trasera']),
    ('mecanismo-gris', None),            # everything else
]

if __name__ == '__main__':
    pieces = {}
    for name, lst in parts():
        tms = [to_tm(m) for m, c in lst]
        if len(lst) == 1 and len(lst[0][0].decompose()) > 1: print('WARNING: more than one piece in', name)
        ms = lay_flat(tms, FORCED.get(name))
        ms = footprint_turn(ms)
        pieces[name] = list(zip(ms, [c for _, c in lst]))
    taken = set(); plates = []
    for pname, names in PLATES:
        names = names or [n for n in pieces if n not in taken]
        taken |= set(names)
        for k, bed in enumerate(pack([(n, [m for m, _ in pieces[n]]) for n in names])):
            plates.append((pname if k == 0 else f'{pname}-{k + 1}', bed))
    cols = math.ceil(math.sqrt(len(plates)))
    allobj = []
    pdir = os.path.join(OUT, 'por-placa'); os.makedirs(pdir, exist_ok=True)
    for f in os.listdir(pdir): os.remove(os.path.join(pdir, f))
    for i, (pname, bed) in enumerate(plates):
        r, c = divmod(i, cols)
        ox, oy = c * STRIDE, -r * STRIDE
        objs = [(n, pieces[n], (x, y)) for n, ms, x, y in bed]
        allobj += [(n, p, (x + ox, y + oy)) for n, p, (x, y) in objs]
        tag = f'placa-{i + 1}-{pname}'
        write_3mf(os.path.join(pdir, f'{tag}.3mf'), objs, f'Cuadro vivo · {tag}')
        h = max(ext_of(ms)[2] for _, ms, _, _ in bed)
        cl = sorted({COLOURS[c][0] for n, *_ in bed for _, c in pieces[n]})
        print(f'plate {i + 1}: {pname:16s} {len(bed):2d} pieces, {len(cl)} colours ({", ".join(cl)}), tallest {h:.1f} mm:', ', '.join(n for n, *_ in bed))
    write_3mf(os.path.join(OUT, 'cuadro-vivo.3mf'), allobj, 'Cuadro vivo · La ola')
    for f in [os.path.join(OUT, 'cuadro-vivo.3mf')] + [os.path.join(pdir, f) for f in sorted(os.listdir(pdir))]:
        s_ = trimesh.load(f)
        bad = [k for k, g in s_.geometry.items() if not g.is_watertight]
        assert not bad, (f, bad)
    print(len(plates), 'plates;', len(allobj), 'pieces; every mesh watertight on reload')
