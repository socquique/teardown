# Gear checks for the living picture: (1) our tooth profile against cq_gears' reference involute (meadiode/cq_gears):
# tooth thickness at several radii — ours should be the reference minus half the backlash; (2) each meshing pair swept
# in fine steps over two tooth periods (the 3D sweep in living.py steps the crank too coarsely for teeth).
#   python3 sims/strandbeest-print/check_gears.py   (needs: pip install cadquery git+https://github.com/meadiode/cq_gears)
import os, sys, math, numpy as np
sys.argv=[sys.argv[0]]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cadquery as cq, trimesh
from cq_gears import SpurGear
import living as L
from shapely.geometry import Polygon, Point, LineString
def ref_poly(z):
    g=SpurGear(module=1.0, teeth_number=z, width=2.0)
    wp=cq.Workplane('XY').gear(g)
    cq.exporters.export(wp, '/tmp/g.stl')
    tm=trimesh.load('/tmp/g.stl'); sec=tm.section(plane_origin=[0,0,1.0], plane_normal=[0,0,1])
    p2,_=sec.to_planar(); polys=p2.polygons_full
    P=max(polys,key=lambda p:p.area)
    # to_planar may shift; recentre on the centroid
    from shapely import affinity
    return affinity.translate(P, -P.centroid.x, -P.centroid.y)
def thick(P, r, z):
    """mean angular tooth thickness (as arc length) at radius r."""
    c=Point(0,0).buffer(r,512).exterior
    inter=P.intersection(LineString(c.coords))
    segs=list(getattr(inter,'geoms',[inter]))
    L_=[s.length for s in segs if s.length>0.05]
    return np.median(L_) if L_ else 0
for z in (10,14,26,40):
    R=ref_poly(z); O=L.gp(z)
    rp=z/2
    ra_r=max(np.hypot(*np.array(R.exterior.coords).T)); ra_o=max(np.hypot(*np.array(O.exterior.coords).T))
    rows=[]
    for r in (rp-0.6, rp-0.3, rp, rp+0.3, rp+0.6):
        rows.append((round(r,2), round(thick(R,r,z),3), round(thick(O,r,z),3)))
    print(f'z={z}: tip r ref {ra_r:.2f} ours {ra_o:.2f} |', ' '.join(f'r{r}: ref {a} ours {b} d={a-b:+.2f}' for r,a,b in rows))

# --- meshing pairs, fine sweep
from shapely import affinity
def g2d(z,c,a): return affinity.translate(affinity.rotate(L.gp(z),a,origin=(0,0)),c[0],c[1])
def sweep(z1,c1,z2,c2,ph2):
    worst=9
    for a in np.linspace(0, 2*360/z1, 400):
        d=g2d(z1,c1,a).distance(g2d(z2,c2,ph2 - a*z1/z2))
        worst=min(worst,d)
    return worst
# shaft gear (26) at shaft, compound small (14) at CPD: ratio; compound big (40) vs pinion (10)
s=(L.SH_Y,L.SH_Z)
print('26/14 min gap', round(sweep(L.ZS,s,L.ZC,L.CPD,L.PC),3))
print('40/10 min gap', round(sweep(L.ZB,L.CPD,L.ZP,L.MOT,L.PM + L.PC*L.ZB/L.ZP),3))
