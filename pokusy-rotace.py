import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan
from copy import copy

def plac():
    return FreeCAD.Placement(vec(), FreeCAD.Rotation())

def vec(x=0,y=0,z=0):
    return FreeCAD.Vector(x,y,z)

# returns flattening translation
def compFlat(vec1, vec2):
    vec_in  = vec1.cross(vec2).normalize()
    vec_out = vec(0,0,1)

    # Calculate the rotation axis (cross product of normalized vector and unit X vector)
    rotation_axis = vec_in.cross(vec_out)

    # Calculate the rotation angle (acosine of the dot product)
    rotation_angle = math.acos(vec_in.dot(vec_out))

    pl = FreeCAD.Placement()
    pl.rotate( vec(), rotation_axis, rotation_angle * 180 / math.pi )
    return pl 

# perpendicular vector
def perp(p):
    return p.cross(vec(0,0,1)).normalize()



NAME = "jambalaya"
doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

P1 = vec(0,-50,40)
P2 = vec(0,50,40)
P3 = vec(200, 70,  100)
P4 = vec(200, -70, 100)

x = Part.makePolygon([P1,P2,P3,P4,P1])
Part.show(x,"x")

pl = FreeCAD.Placement()
pl.translate(vec(0,0,-40))
pl = compFlat(P4-P1,P2-P1) * pl

plm = pl.toMatrix()

y = x.copy()
y.Placement = pl
fc = Part.Face(Part.Wire([y]))
Part.show(fc,"y")


P2f = plm.multVec(P2)
P3f = plm.multVec(P3)

# flaps
d10,d20,d30,d40 = [ d * perp(P2f - P3f) for d in [10,20,30,40]]
flap1 = Part.Face(Part.Wire([Part.makePolygon([P2f,P2f+d20,P3f+d20,P3f,P2f])]))
flap2 = Part.Face(Part.Wire([Part.makePolygon([P2f+d20,P2f+d40,P3f+d40,P3f+d20,P2f+d20])]))
# holes
i = 10
while i < (P2f - P3f).Length:
    cyl1  = Part.makeCylinder(1,5)
    cyl1.translate(P2f + d10 +  i * (P3f - P2f).normalize())
    cyl2 = cyl1.copy()
    cyl2.translate(d30 - d10)
    flap1 = flap1.cut(cyl1)
    flap2 = flap2.cut(cyl2)
    i = i + 10

Part.show(flap1,"flap1")
Part.show(flap2,"flap2")



doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

