# Puts every part of the walker where it goes, at crank angle th, and writes assembly.stl (plus the motor if its STL
# is given).   python3 sims/strandbeest-print/assemble.py <dir> [deg] [motor.stl]
import json, os, sys, math
import numpy as np, trimesh

D = sys.argv[1]
DEG = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
MOTOR = sys.argv[3] if len(sys.argv) > 3 else None
M = json.load(open(os.path.join(D, 'walker.json')))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from walker_layers import solve, HOLY
S, T, GAP, PITCH, NL = M['S'], M['T'], M['GAP'], M['PITCH'], M['NL']
J0 = solve(0, S)
JS = dict(M['joints']); JS['web'] = ['O', 'A']
load = lambda n: trimesh.load(os.path.join(D, n + '.stl'))
cache = {}
def part(n):
    if n not in cache: cache[n] = load(n)
    return cache[n].copy()

def rigid(n, J, mirror=False):
    js = JS['crank' if n == 'web' else n]
    o0, p0, o, p = J0[js[0]], J0[js[1]], J[js[0]], J[js[1]]
    rot = math.atan2(p[1]-o[1], p[0]-o[0]) - math.atan2(p0[1]-o0[1], p0[0]-o0[0])
    m = part(n)
    Tm = trimesh.transformations.translation_matrix([o[0], o[1], 0]) @ trimesh.transformations.rotation_matrix(rot, [0, 0, 1]) @ trimesh.transformations.translation_matrix([-o0[0], -o0[1], 0])
    m.apply_transform(Tm)
    return m

def module(z0, phase, th):
    """one module whose low frame's high face is at z0 (layers start at z0 + GAP)."""
    out = []
    J = solve(th + phase, S)
    zl = lambda l: z0 + GAP + (l - 1) * PITCH
    for key, l in M['layers'].items():
        if key == 'web_a':
            m = rigid('web', J); m.apply_translation([0, 0, zl(l)]); out.append(m)
        elif key == 'web_b':  # same part turned round: flip z about its own mid-plane
            m = rigid('web', J); m.apply_transform(trimesh.transformations.scale_matrix(-1, [0, 0, T / 2], [0, 0, 1]))
            m.invert(); m.apply_translation([0, 0, zl(l)]); out.append(m)
        elif key.startswith('L:'):
            m = rigid(key[2:], J); m.apply_translation([0, 0, zl(l)]); out.append(m)
        elif key.startswith('M:'):
            # the mirrored leg: mirror of the leg at crank angle (pi - th), turned round in z
            Jm = solve(math.pi - (th + phase), S)
            m = rigid(key[2:], Jm)
            m.apply_transform(trimesh.transformations.scale_matrix(-1, [0, 0, 0], [1, 0, 0]))   # mirror x
            m.apply_transform(trimesh.transformations.scale_matrix(-1, [0, 0, T / 2], [0, 0, 1]))  # turn round in z
            m.apply_translation([0, 0, zl(l)]); out.append(m)  # two mirrors = a turn: no winding fix
    return out

def build(th):
    out = []
    ZF = M['ZF']; secs = M['sections']
    phases = {0: 0, 1: 120, 2: 240, 5: 60, 6: 180, 7: 300}
    for i, s in enumerate(secs):
        if s == 'mod': out += module(ZF[i] + T, math.radians(phases[i]), th)
    # frames
    for i, z in enumerate(ZF):
        below = secs[i - 1] if i > 0 else None; above = secs[i] if i < len(secs) else None
        kind = 'motor' if (below == 'gear' and above == 'motor') else ('motor_back' if below == 'motor' else 'plain')
        n = f'frame-{kind}' + ('-Plo' if below == 'mod' else '') + ('-Phi' if above == 'mod' else '')
        m = part(n); m.apply_translation([0, 0, z]); out.append(m)
    # gears
    gi = secs.index('gear'); zg = ZF[gi] + T + GAP
    g = part('gear-48'); g.apply_transform(trimesh.transformations.rotation_matrix(-th / 4 * 0 - th, [0, 0, 1])); g.apply_translation([0, 0, zg]); out.append(g)
    p = part('pinion'); p.apply_transform(trimesh.transformations.rotation_matrix(4 * th, [0, 0, 1])); p.apply_translation([0, M['CD'], zg]); out.append(p)
    # rails
    for x in (-M['rail'][0], M['rail'][0]):
        r = part('rail')  # printed lying along x: stand it back along z
        r.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [0, 1, 0]))
        r.apply_translation(-r.bounds[0]); ext = r.extents
        r.apply_translation([x - ext[0] / 2, M['rail'][1] - ext[1] / 2, -2 - 0.0])
        out.append(r)
    if MOTOR:
        mot = trimesh.load(MOTOR)
        # motor STL: x up from the shaft face (top face at x = 9.4), y along the body (shaft at 11.2), z across
        R = np.eye(4); R[:3, :3] = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]  # shaft (motor +x) -> -z, body along +y
        mot.apply_transform(R); mot.apply_translation([0, -11.2 + M['CD'], 0])
        zt = ZF[secs.index('motor')] + 0.0  # motor plate (frame 4) high face is the motor's top face
        mot.apply_translation([0, 0, zt + T + 9.4])
        out.append(mot)
    return out

if __name__ == '__main__':
    ms = build(math.radians(DEG))
    trimesh.util.concatenate(ms).export(os.path.join(D, 'assembly.stl'))
    a = trimesh.util.concatenate(ms)
    print('assembly', a.extents.round(1), 'mm, parts', len(ms))
