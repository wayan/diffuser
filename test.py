"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys, math
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from Diffutil import vec, angleVec, between, recPoints, unwrapShape, halfSpace, X, Y, Z, ortoRecFace
from Cone import Cone


doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

cone = Cone("9_17test")
cone.ReflectionDeskDown = cone.LensDia / 2 + 27

diffuser = cone.build()
desk =  cone.reflectionDesk()

Part.show(desk, "desk")


Part.show(unwrapShape(doc, desk).translate(300*X), "udesk")

v = FreeCAD.Vector

r = 50
c = Part.makeCircle(r)
c = c.fuse(Part.makeCircle(r, v(r/2)))
c = c.removeSplitter()
print(len(c.Edges))
Part.show(c, "circle")

