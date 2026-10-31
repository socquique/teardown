# Layer search for one half-module of the 12-leg walker (shared by walker.py).
import math, re, itertools, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, '..', 'strandbeest-shared', 'jansen.js')).read()
HOLY = {k: float(v) for k, v in re.findall(r'(\w):\s*([\d.]+)', re.search(r'HOLY = \{([^}]*)\}', src).group(1))}

def cc(p0, r0, p1, r1):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]; d = math.hypot(dx, dy)
    a = (r0*r0 - r1*r1 + d*d)/(2*d); h = math.sqrt(max(0, r0*r0 - a*a))
    mx, my = p0[0]+a*dx/d, p0[1]+a*dy/d
    return (mx + h*dy/d, my - h*dx/d), (mx - h*dy/d, my + h*dx/d)

def solve(th, S):
    H = HOLY
    P = (-H['a'], -H['l']); A = (H['m']*math.cos(th), H['m']*math.sin(th))
    B = max(cc(A, H['j'], P, H['b']), key=lambda q: q[1]); C = min(cc(A, H['k'], P, H['c']), key=lambda q: q[1])
    D = min(cc(B, H['e'], P, H['d']), key=lambda q: q[0]); E = min(cc(D, H['f'], C, H['g']), key=lambda q: q[0])
    F = min(cc(E, H['h'], C, H['i']), key=lambda q: q[1])
    J = dict(O=(0, 0), P=P, A=A, B=B, C=C, D=D, E=E, F=F)
    return {k: (v[0]*S, v[1]*S) for k, v in J.items()}

PARTS = [  # one leg; the crank is shared with the mirrored leg on the other side of it
    dict(name='crank', joints=['O', 'A']),
    dict(name='link-j', joints=['A', 'B']),
    dict(name='link-k', joints=['A', 'C']),
    dict(name='link-c', joints=['P', 'C']),
    dict(name='link-f', joints=['D', 'E']),
    dict(name='tri-upper', joints=['P', 'B', 'D']),
    dict(name='tri-foot', joints=['C', 'E', 'F'], foot='F'),
]

# ---------------------------------------------------------------- geometry helpers (2D, mm)
def circle(c, r, n=20):
    return [(c[0] + r*math.cos(2*math.pi*i/n), c[1] + r*math.sin(2*math.pi*i/n)) for i in range(n)]

def hull(pts):
    p = sorted(set(pts))
    def cr(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cr(up[-2], up[-1], q) <= 0: up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]

def outline(part, J, R, n=20):
    return hull([q for k in part['joints'] for q in circle(J[k], R*1.3 if k == part.get('foot') else R, n)])

def sat(a, b, margin):
    for poly in (a, b):
        for i in range(len(poly)):
            x0, y0 = poly[i]; x1, y1 = poly[(i+1) % len(poly)]
            nx, ny = y1-y0, x0-x1; L = math.hypot(nx, ny)
            pa = [(x*nx + y*ny)/L for x, y in a]; pb = [(x*nx + y*ny)/L for x, y in b]
            if max(pa) + margin < min(pb) or max(pb) + margin < min(pa): return False
    return True

def dist(poly, p):
    inside = True; d = 1e9
    for i in range(len(poly)):
        x0, y0 = poly[i]; x1, y1 = poly[(i+1) % len(poly)]
        if (x1-x0)*(p[1]-y0) - (y1-y0)*(p[0]-x0) < 0: inside = False
        t = max(0, min(1, ((p[0]-x0)*(x1-x0) + (p[1]-y0)*(y1-y0)) / ((x1-x0)**2 + (y1-y0)**2)))
        d = min(d, math.hypot(p[0]-x0-t*(x1-x0), p[1]-y0-t*(y1-y0)))
    return 0 if inside else d

def search(S, R, pinR, axleR, steps=360, margin=0.6, frame_outline=None):
    """Layers for one half-module: frame = 0 (outer), leg parts 1..K, crank = K+1 (centre, shared with the mirror).
    Constraints over a full turn: parts on one layer never overlap; a pin never passes through a part not on it;
    nothing but the crank and frame ever comes near the axle, which runs through every layer."""
    parts = PARTS[1:]
    n = len(parts)
    clash = [[False]*n for _ in range(n)]
    pinhit = {k: set() for k in 'ABCDEP'}
    axle_bad = set(); frame_hit = set()
    for s in range(steps):
        J = solve(2*math.pi*s/steps, S)
        outs = [outline(p, J, R) for p in parts]
        crank = outline(PARTS[0], J, R)
        for a in range(n):
            for b in range(a+1, n):
                if not clash[a][b] and sat(outs[a], outs[b], margin): clash[a][b] = clash[b][a] = True
            for k in pinhit:
                if k not in parts[a]['joints'] and dist(outs[a], J[k]) < pinR + margin: pinhit[k].add(a)
            if dist(outs[a], J['O']) < axleR + margin: axle_bad.add(parts[a]['name'])
    crank_clash = set()
    for s in range(steps):
        J = solve(2*math.pi*s/steps, S); crank = outline(PARTS[0], J, R)
        for a in range(n):
            if 'A' not in parts[a]['joints'] and sat(outline(parts[a], J, R), crank, margin): crank_clash.add(a)
    if axle_bad: return dict(error='axle', parts=axle_bad)
    best = None
    for K in range(2, 7):
        for lay in itertools.product(range(1, K+1), repeat=n):
            ok = True
            for a in range(n):
                for b in range(a+1, n):
                    if clash[a][b] and lay[a] == lay[b]: ok = False; break
                if not ok: break
            if not ok: continue
            L = {parts[i]['name']: lay[i] for i in range(n)}; L['crank'] = K+1; L['frame'] = 0
            allp = PARTS + [dict(name='frame', joints=['O', 'P'])]
            span = 0
            for k in 'ABCDEP':
                mem = [p['name'] for p in allp if k in p['joints']]
                ls = sorted(L[m] for m in mem)
                if len(set(ls)) != len(ls): ok = False; break
                lo, hi = ls[0], ls[-1]
                if any(lo <= lay[i] <= hi for i in pinhit[k]): ok = False; break
                span += hi - lo
            if not ok: continue
            if any(lay[i] == K for i in crank_clash) and False: pass
            if best is None or span < best[0]: best = (span, L, K)
        if best: return dict(layers=best[1], K=best[2], span=best[0], clash=clash, pinhit=pinhit)
    return dict(error='none')

def search_crankshaft(S, R, pinR, steps=360, margin=0.6):
    """Module = frame_a(0) | web_a(1) | leg parts 2..K+1 | (mirrored leg, the same stack turned round) | web_b | frame_b.
    The crank pin A runs through the whole module, so no part except links j and k may ever come near A;
    the webs sweep a disc round O on their own layers. Returns layers for the leg parts."""
    parts = PARTS[1:]
    n = len(parts)
    clash = [[False]*n for _ in range(n)]
    pinhit = {k: set() for k in 'BCDEP'}
    a_bad = set(); web_bad = set()
    webR = HOLY['m']*S + R
    for s in range(steps):
        J = solve(2*math.pi*s/steps, S)
        outs = [outline(p, J, R) for p in parts]
        for a in range(n):
            for b in range(a+1, n):
                if not clash[a][b] and sat(outs[a], outs[b], margin): clash[a][b] = clash[b][a] = True
            for k in pinhit:
                if k not in parts[a]['joints'] and dist(outs[a], J[k]) < pinR + margin: pinhit[k].add(a)
            if 'A' not in parts[a]['joints'] and dist(outs[a], J['A']) < pinR + margin: a_bad.add(parts[a]['name'])
            if dist(outs[a], J['O']) < webR + margin: web_bad.add(parts[a]['name'])
    names = [p['name'] for p in parts]
    for K in range(2, 8):
        best = None
        for lay in itertools.product(range(2, K+2), repeat=n):
            if any(clash[a][b] and lay[a] == lay[b] for a in range(n) for b in range(a+1, n)): continue
            L = dict(zip(names, lay)); L['frame'] = 0
            ok = True; span = 0
            for k in 'BCDEP':
                mem = [p['name'] for p in parts + [dict(name='frame', joints=['P'])] if k in p['joints']]
                ls = sorted(L[m] for m in mem)
                if len(set(ls)) != len(ls): ok = False; break
                if any(ls[0] <= lay[i] <= ls[-1] for i in pinhit[k]): ok = False; break
                span += ls[-1] - ls[0]
            if not ok: continue
            if best is None or span < best[0]: best = (span, L)
        if best: return dict(layers=best[1], K=K, span=best[0], a_bad=a_bad, web_bad=web_bad, pinhit=pinhit)
    return dict(error='none', a_bad=a_bad, web_bad=web_bad)
