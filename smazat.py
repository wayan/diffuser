import os, sys, FreeCAD, Part, math, copy

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))


import diffuser.model as model
import diffuser.util as du

from diffuser.util import vec, X, Y, Z, O
from diffuser.grid import Grid

def do_stuff(doc):
    pts = [ vec(0,0,0), vec(20,20,0), vec(80, 40, 0), vec(120, 70,0), vec(130,0,0), vec(0, -90) ]
    e = Part.BSplineCurve(pts).toShape()


    Part.show(e, "e")

    ee = e.copy()
    m = FreeCAD.Base.Matrix()
    m.A11 = -1
    ee.transformShape(m)
    Part.show(ee, "ee")

    w = Part.Wire([e, ee])
    #w = Part.Wire([e, du.reverse_edge(ee)])
    Part.show(Part.Face(w), "x")





doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

try:
    # Call the main method on the instance
    do_stuff(doc)
except Exception:
    print(traceback.format_exc())
    sys.exit()

# Close the document
print(f"Closing document: {doc.Label}")

# Quit the FreeCAD application
print("Quitting FreeCAD application...")
