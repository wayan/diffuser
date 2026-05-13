"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
import Mesh
import Lines
from Diffutil import vec, X, Y, Z, O, ortoRecFace, symX

doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

r1 = 20
r2 = 5
t  = 1.3

def arm(angle):
    def arm():
        c1, c2 = [ Part.Face(Part.Wire([Part.makeCircle(r2)])).translate(p) for p in [O, X*r1] ]
        of = ortoRecFace(-r2*Y, r1*X+r2*Y)
        of = of.fuse(c1).fuse(c2)
        of = of.cut(ortoRecFace(r2*X-Y*t/2, r1*X+Y*t/2))
        return of

    a = arm().fuse(arm().rotate(O,Z,angle))
    return a

a = arm(90).translate(100*X)
a = a.removeSplitter()
Part.show(a,"a")

b = arm(135) 
b = b.removeInternalWires()
Part.show(b, "b")

