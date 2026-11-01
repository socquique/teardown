# Fit test for the living picture (living.py): every press fit, snap and bearing of the real thing, in the same print
# orientation, in a few minutes of plastic. Print it, try each joint, and report which size fits best.
#   python3 sims/strandbeest-print/probeta.py   -> teardown-out/print/living-wave/probeta.3mf (+ probeta-*.stl)
#   A  arm pegs (2.5 mm, printed lying like the arms) into blind holes 2.30 / 2.40 (design) / 2.50
#   B  caps on an M3 screw: bores 2.6 / 2.7 (design) / 2.8;  a carrier strip with the 3.5 pivot hole
#   C  snap: a slice of the box wall with its groove, and a slice of the lid with its bead
#   D  D-shaft: shaft stub (lying on its flat), washer with the D bore, bearing plate with the 6.7 hole
#   E  TT motor: a slice of the motor plate, standing like the real one (boss, pin and bump holes), and the pinion
import os, sys, math
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv; sys.argv = [sys.argv[0]]
import living as L
import export_3mf as E
from fidgets import cyl, ext, to_tm
from objects import box, d_hole, text_poly
from manifold3d import Manifold
sys.argv = _argv

def label(s, x, y, z, size=3.2, depth=0.5):
    """text cut into a top face at height z."""
    return ext(text_poly(s, size, (x, y)), depth + 0.01, z - depth)

pieces = []   # (name, manifold) in print orientation, z = 0 on the bed

# A: a leg block 2.4 thick (back face on the bed, as the waves print) with three pairs of blind holes from below,
#    and three arms with the real pegs, printed lying on their side like the real arms
leg = box(0, 36, 0, 14, 0, L.PT)
for i, d in enumerate((2.30, 2.40, 2.50)):
    x = 6 + 12 * i
    for yy in (5.5 - 1.5, 5.5 + 1.5):          # the real pair, 3.0 apart
        leg = leg - cyl(d / 2, 1.9, x, yy, -0.01)
    leg = leg - label(f'{d:.1f}' if i != 1 else '2.4*', x, 11.3, L.PT, 2.6, 0.4)
pieces.append(('A-pata-agujeros', leg))
arm = box(-1.5, 1.5, 0, 6, -30, -0.1)                   # a stub of the real arm, built as assembled (pegs along +z) ...
for py in L.ARM_PEGS:
    arm = arm + L.peg(0, py, -0.6)                       # ... with the real pegs (flat on the bed side, chamfered tip)
arm = arm.rotate([0, -90, 0])                            # ... and laid on its −x face like the real arms
pieces += [(f'A-brazo-{i + 1}', arm) for i in range(3)]

# B: caps with three bores (the screw is a real M3), and a strip of carrier with the 3.5 pivot hole
for i, d in enumerate((2.6, 2.7, 2.8)):
    cap = cyl(2.6, 1.2) - cyl(d / 2, 3, 0, 0, -1)
    pieces.append((f'B-tapon-{d:.1f}', cap))
strip = box(0, 30, 0, 10, 0, L.PT) - cyl(1.75, 5, 6, 5, -1) - cyl(1.65, 5, 18, 5, -1) - cyl(L.CSK_R, L.CSK_R - 1.65, 18, 5, -0.01, r2=1.65)
strip = strip - label('3.5', 26, 5, L.PT, 2.4, 0.4)
pieces.append(('B-pivote-y-avellanado', strip))            # 3.5 pivot hole; countersunk M3 hole as in the sky panel

# C: the box's snap: a wall slice (printed standing like the box) with the groove, and a lid slice with its bead
H = 14.0; W_ = 30.0
wall = box(0, W_, 0, 4, 0, H)                            # wall, inner face at y = 4
zc = H - L.LIP / 2                                       # groove where the lid's bead lands (lid lip enters from the top)
wall = wall - Manifold.cylinder(W_ + 2, 0.6, 0.6, 32).rotate([0, 90, 0]).translate([-1, 4, zc])
wall = wall + box(0, W_, -6, 4, 0, 2)                    # a foot so it stands
lid = box(0, W_, 0, 12, 0, 3)                            # lid plate (on the bed) ...
lip0 = 12 - 4 - 0.15                                     # ... with its lip, outer face 0.15 inside the wall face
lid = lid + box(0, W_, lip0 - 2, lip0, 3 - 0.01, 3 + L.LIP)
lid = lid + Manifold.cylinder(W_, 0.45, 0.45, 32).rotate([0, 90, 0]).translate([0, lip0, 3 + L.LIP / 2])
pieces += [('C-pared-ranura', wall), ('C-tapa-cordon', lid)]

# D: D-shaft stub, washer, bearing plate
shaft = (cyl(L.SH_R, 25, 0, 0, 0) ^ box(-5, L.SH_FLAT, -5, 5, -1, 40))
shaft_flat = shaft.rotate([0, 90, 0])                    # lies on its flat (as in the real print)
pieces.append(('D-eje', shaft_flat))
washer = cyl(6, 1.6) - d_hole(L.SH_R + 0.2, L.SH_FLAT + 0.2, 0, 4, -1)
pieces.append(('D-arandela', washer))
# bearings stand up like the real ones (box wall, gearbox), so their holes are horizontal: Ø6.4 / 6.6 (design) / 6.8
for d in (6.4, 6.6, 6.8):
    bear = box(-8, 8, 0, 3, 0, 18) - Manifold.cylinder(5, d / 2, d / 2, 64).rotate([-90, 0, 0]).translate([0, -1, 10])
    bear = bear + box(-8, 8, -6, 9, 0, 2)                # foot
    pieces.append((f'D-cojinete-{d:.1f}', bear))

# E: the motor plate around the TT's boss, locating pin and bump, standing up as in the real gearbox
mp = box(0, 3, -16, 37, 0, 22)                           # x thin, y up, z across: shaft at (y, z) = (0, 11); reaches below the motor body (−11.2)
mp = mp - Manifold.cylinder(5, 4.5, 4.5, 64).rotate([0, 90, 0]).translate([-1, 0, 11]) \
        - Manifold.cylinder(5, 2.05, 2.05, 64).rotate([0, 90, 0]).translate([-1, 11.15, 11]) \
        - box(-1, 4, 30.7 - 2.8, 30.7 + 2.8, 11 - 2.3, 11 + 2.3)
mp = mp.rotate([90, 0, 0])                               # y -> z: plate stands (like the real gearbox)
mp = mp + box(-8, 11, -22, 0, -16, -14)                  # a foot, below the motor (the first one hit the motor body)
pieces.append(('E-placa-motor', mp))
F = L.fixed()
pieces.append(('E-pinon-motor', F['g_pin']))

if __name__ == '__main__':
    objs = []
    for n, m in pieces:
        tm = to_tm(m)
        tm.vertices -= tm.bounds[0]
        objs.append((n, [tm]))
    beds = E.pack([(n, ms) for n, ms in objs])
    assert len(beds) == 1, 'does not fit one plate'
    bed = beds[0]
    plates = [('probeta', [(n, [(ms[0], 'gris')], (x, y)) for n, ms, x, y in bed])]
    for pr in ('P2S', 'A1'):
        E.write_bbl_3mf(os.path.join(L.OUT, f'probeta-{pr}.3mf'), plates, 'Cuadro vivo · probeta de ajustes', pr)
    for n, ms, x, y in bed:
        ms[0].export(os.path.join(L.OUT, f'probeta-{n}.stl'))
    for n, ms, x, y in bed: print(f'{n:24s} {ms[0].extents.round(1)} watertight={ms[0].is_watertight}')
