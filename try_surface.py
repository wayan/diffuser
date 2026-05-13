import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan
from Diffutil import vec, recXZ, halfSpace, unwrapShape, symY, X, Y, Z, O
import BOPTools.SplitAPI 
import Diffutil as du
import math
import traceback
from functools import reduce

def project(sf, shape, xs, ys):
    uMin,uMax,vMin,vMax=sf.ParameterRange

    def uv(x,y):
        xn = (x - xs[0])/(xs[1]-xs[0])
        yn = (y - ys[0])/(ys[1]-ys[0])

        return [ du.between(uMin,uMax,xn), du.between(vMin,vMax,yn)

    newEdges = []
    for e in shape.Edges:
        p0 = e.valueAt(e.FirstParameter)
        p1 = e.valueAt(e.LastParameter)

        newEdges.append
         
    


def do_stuff(doc):
    r1 = 20
    r2 = 40
    pts = [vec(0,-1,0), vec(0,-1,1), vec(0,1,1), vec(0,1,0) ]
    bez, bez2 = [ Part.BSplineCurve([ r*p+x*X for p in pts ]).toShape() for r, x in [ [20,-30], [40, 20] ] ]
    sf = Part.makeRuledSurface(bez, bez2)
    Part.show(sf, "sf")

    uMin,uMax,vMin,vMax=sf.ParameterRange

    n = 40

    pts = [
        [
            sf.valueAt(
                du.between(uMin,uMax, du.between(0.3, 0.8, i/n)),
                du.between(vMin,vMax, k)
            )
            for i in range(n)
        ]
        for k in [0.3,1.0]
    ]

    poly = Part.makePolygon(pts[0] + pts[1][::-1] + [ pts[0][0] ])
    Part.show(poly, "poly")

    projected = sf.project([poly])
    w = Part.Wire(projected.SubShapes)
    Part.show(w, "w")
    f = Part.Face(w)
    Part.show(f,"f")
    print(f.isValid())

    pl1 = Part.makePolygon([O, 40*X, 40*X + 20*Y, 20*Y, O])
    pl2 = Part.makePolygon([10*X+10*Y, 30*X+10*Y, 30*X+30*Y,10*X+30*Y, 10*X+10*Y])
    f = Part.Face(pl1).fuse(Part.Face(pl2)).removeSplitter()
    Part.show(f,"ff")
    print(len(f.Edges))

doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

try:
    do_stuff(doc)
except Exception:
    print(traceback.format_exc())
    sys.exit()
    # FreeCAD.quit()

