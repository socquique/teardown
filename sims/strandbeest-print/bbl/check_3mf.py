# Checks a Bambu Studio project 3MF the way Bambu Studio's loader (src/libslic3r/Format/bbs_3mf.cpp) and plate list
# (src/slic3r/GUI/PartPlate.cpp) read it, so mistakes show up here and not on the user's screen:
#  - Application starts with "BambuStudio-" (otherwise: "not from Bambu Lab, geometry and colour only", no plates)
#  - project_settings.config present and non-empty (otherwise plates are ignored)
#  - every component points at an existing file and object; sub-object ids unique across files (Bambu keys them by id)
#  - model_settings: every object and part exists; every part's extruder within the filament list
#  - plates: every instance is a real object, used once, and lies inside its plate's rectangle
#    (columns = ceil-ish sqrt(n), stride = bed × 1.2, row r goes to −y)
#  - meshes watertight, nothing below the bed, objects on a plate don't overlap
#   python3 bbl/check_3mf.py file.3mf [...]
import sys, zipfile, json, math, xml.etree.ElementTree as ET
import numpy as np, trimesh

NS = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
P = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'

def cols_for(n):          # PartPlate.hpp compute_colum_count
    v = math.sqrt(n); r = round(v)
    return r + 1 if v > r else r

def check(path):
    errs = []; z = zipfile.ZipFile(path); names = set(z.namelist())
    main = ET.fromstring(z.read('3D/3dmodel.model'))
    app = {m.get('name'): (m.text or '') for m in main.findall(NS + 'metadata')}.get('Application', '')
    if not app.startswith('BambuStudio-'): errs.append(f'Application is {app!r}: Bambu loads geometry and colour only')
    if 'Metadata/project_settings.config' not in names: errs.append('no project_settings.config: plates would be ignored')
    cfg = json.loads(z.read('Metadata/project_settings.config'))
    if not cfg: errs.append('empty project settings')
    nfil = len(cfg.get('filament_colour', []))
    for k in ('printer_settings_id', 'print_settings_id', 'filament_settings_id', 'printable_area'):
        if not cfg.get(k): errs.append(f'project settings lack {k}')
    W = max(float(p.split('x')[0]) for p in cfg['printable_area']); D = max(float(p.split('x')[1]) for p in cfg['printable_area'])
    # sub-objects
    subs = {}; seen_ids = {}
    for n in names:
        if n.startswith('3D/Objects/') and n.endswith('.model'):
            for o in ET.fromstring(z.read(n)).iter(NS + 'object'):
                i = o.get('id')
                if i in seen_ids: errs.append(f'sub-object id {i} in both {seen_ids[i]} and {n}: Bambu would give both the same mesh')
                seen_ids[i] = n
                V = np.array([[float(v.get(a)) for a in 'xyz'] for v in o.iter(NS + 'vertex')])
                T = np.array([[int(t.get(a)) for a in ('v1', 'v2', 'v3')] for t in o.iter(NS + 'triangle')])
                subs[(n, i)] = trimesh.Trimesh(V, T, process=True)
    tops = {}
    for o in main.iter(NS + 'object'):
        comps = []
        for c in o.iter(NS + 'component'):
            f = c.get(P + 'path', '').lstrip('/'); i = c.get('objectid')
            if (f, i) not in subs: errs.append(f'object {o.get("id")}: component {f}#{i} missing')
            else: comps.append((i, subs[(f, i)]))
        tops[o.get('id')] = comps
    items = {}
    for it in main.iter(NS + 'item'):
        t = [float(v) for v in it.get('transform').split()]
        items[it.get('objectid')] = np.array(t[9:12])
    # model settings
    ms = ET.fromstring(z.read('Metadata/model_settings.config'))
    for o in ms.findall('object'):
        oid = o.get('id')
        if oid not in tops: errs.append(f'model_settings object {oid} not in the model'); continue
        cid = {i for i, _ in tops[oid]}
        for p in o.findall('part'):
            if p.get('id') not in cid: errs.append(f'object {oid}: part {p.get("id")} is not one of its components')
            ex = {m.get('key'): m.get('value') for m in p.findall('metadata')}.get('extruder')
            if ex and not (1 <= int(ex) <= nfil): errs.append(f'object {oid} part {p.get("id")}: extruder {ex} > {nfil} filaments')
    plates = ms.findall('plate'); cols = cols_for(len(plates)); used = set(); report = []
    for k, pl in enumerate(plates):
        md = {m.get('key'): m.get('value') for m in pl.findall('metadata')}
        r, c = divmod(int(md['plater_id']) - 1, cols)
        ox, oy = c * W * 1.2, -r * D * 1.2
        boxes = []
        for mi in pl.findall('model_instance'):
            oid = {m.get('key'): m.get('value') for m in mi.findall('metadata')}['object_id']
            if oid not in tops: errs.append(f'plate {k + 1}: unknown object {oid}'); continue
            if oid in used: errs.append(f'object {oid} on two plates')
            used.add(oid)
            allv = np.vstack([m.vertices for _, m in tops[oid]]) + items[oid]
            lo, hi = allv.min(0), allv.max(0)
            if lo[0] < ox - 0.01 or hi[0] > ox + W + 0.01 or lo[1] < oy - 0.01 or hi[1] > oy + D + 0.01:
                errs.append(f'plate {k + 1} ({md.get("plater_name")}): object {oid} outside the plate {lo[:2].round(1)}..{hi[:2].round(1)}')
            if lo[2] < -0.01: errs.append(f'object {oid} below the bed ({lo[2]:.2f})')
            for i, m in tops[oid]:
                if not m.is_watertight: errs.append(f'object {oid} part {i}: mesh not watertight')
            boxes.append((oid, lo, hi))
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                (ia, la, ha), (ib, lb, hb) = boxes[a], boxes[b]
                if (la[:2] < hb[:2] - 0.5).all() and (lb[:2] < ha[:2] - 0.5).all():
                    errs.append(f'plate {k + 1}: objects {ia} and {ib} overlap')
        report.append(f'{md.get("plater_name")}: {len(boxes)}')
    for oid in tops:
        if oid not in used: errs.append(f'object {oid} on no plate')
    return errs, f'{cfg["printer_settings_id"]}, {nfil} filaments, plates: ' + ', '.join(report)

if __name__ == '__main__':
    bad = 0
    for f in sys.argv[1:]:
        errs, rep = check(f)
        print(('OK   ' if not errs else 'FAIL ') + f + '\n     ' + rep)
        for e in errs: print('     - ' + e)
        bad += bool(errs)
    sys.exit(bad)
