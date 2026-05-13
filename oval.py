"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan
from Diffutil import vec, recXZ, halfSpace, unwrapShape, X, Y, Z, O, ortoRecPoly, symX, symY
import Diffutil as df
from Lines import Lines


doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

ww = 500
hh = 250

w = 200 * X / 2
h = 230 * Y / 2
oo = 10*(X+Y)
Part.show( ortoRecPoly(O, ww*X+hh*Y), "plexi")

arcs = Lines()
arcs.add(-h, -h+w-25*X)
arcs.add(-h+w, -h+w+25*Y)
arcs.add(w)
arcs = arcs + arcs.rev(symY)
arcs = arcs + arcs.rev(symX)
arcs = arcs.map(lambda p: p+w+h+oo)

oval = Part.Wire([ Part.BSplineCurve(arc).toShape() for arc in arcs ])
Part.show(oval, "oval")


