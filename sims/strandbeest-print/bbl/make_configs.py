# Builds Bambu Studio project settings (Metadata/project_settings.config) for each printer from Bambu's own system
# profiles, the way Bambu Studio does when it saves a project: resolve each profile's `inherits`/`include` chain, keep
# the entries of the nozzle variant in use, repeat the filament settings once per filament, and lay all of it over a
# project that Bambu Studio itself saved (project_settings_A1_8xPLA.json), which brings the project-level keys.
# Idea from bambox (estampo/bambox), which builds the same file from a machine base plus filament profiles.
#   python3 bbl/make_configs.py <BambuStudio>/resources/profiles/BBL   -> bbl/project_settings_{A1,P2S}.json
import json, glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
META = {'inherits', 'include', 'name', 'from', 'type', 'instantiation', 'setting_id', 'filament_id', 'description',
        'renamed_from', 'compatible_printers', 'compatible_printers_condition', 'compatible_prints', 'compatible_prints_condition'}
VARIANT = 'Direct Drive Standard'
N_FIL = 8

def index(root):
    idx = {}
    for f in glob.glob(os.path.join(root, '**', '*.json'), recursive=True):
        try: d = json.load(open(f))
        except Exception: continue
        if isinstance(d, dict) and 'name' in d: idx[d['name']] = d
    return idx

def resolve(idx, name):
    d = idx[name]; out = {}
    if d.get('inherits'): out.update(resolve(idx, d['inherits']))
    inc = d.get('include', [])
    for i in (inc if isinstance(inc, list) else []):
        if i in idx: out.update(resolve(idx, i))
    out.update({k: v for k, v in d.items() if k not in ('inherits', 'include')})
    return out

def pick(r, vkey):
    vs = r.get(vkey)
    if not isinstance(vs, list) or len(vs) <= 1: return r
    i = vs.index(VARIANT); n = len(vs); out = {}
    for k, v in r.items():
        if isinstance(v, list) and k not in META and len(v) >= n and len(v) % n == 0:
            per = len(v) // n                              # e.g. machine limits: (normal, silent) per variant
            out[k] = v[i * per:(i + 1) * per]
        else:
            out[k] = v
    return out

def build(idx, printer):
    machine, process, filament = f'Bambu Lab {printer} 0.4 nozzle', f'0.20mm Standard @BBL {printer}', f'Bambu PLA Basic @BBL {printer}'
    cfg = json.load(open(os.path.join(HERE, 'project_settings_A1_8xPLA.json')))
    m = pick(resolve(idx, machine), 'printer_extruder_variant')
    p = pick(resolve(idx, process), 'print_extruder_variant')
    f = pick(resolve(idx, filament), 'filament_extruder_variant')
    for src in (m, p):
        for k, v in src.items():
            if k not in META: cfg[k] = v
    for k, v in f.items():
        if k not in META: cfg[k] = v * N_FIL if isinstance(v, list) else v
    cfg.update(printer_settings_id=machine, print_settings_id=process, filament_settings_id=[filament] * N_FIL,
               print_compatible_printers=[machine], inherits='', name='project_settings', **{'from': 'project'})
    cfg['different_settings_to_system'] = [''] * (N_FIL + 2)
    return cfg

if __name__ == '__main__':
    idx = index(sys.argv[1])
    for pr in ('A1', 'P2S'):
        c = build(idx, pr)
        json.dump(c, open(os.path.join(HERE, f'project_settings_{pr}.json'), 'w'), indent=4)
        print(pr, len(c), 'keys;', c['printer_model'], c['printable_area'], c['nozzle_temperature'][:1], len(c['filament_colour']))
