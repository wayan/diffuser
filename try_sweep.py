"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
import Mesh
import Lines
from Diffutil import vec, X, Y, Z, O, ortoRecFace, symX, angleVec

doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

r = 50
path = Part.makeCircle(r, O, Z, 0, 90)

line = Part.makeLine(r*Y,-r*X+r*Y)
Part.show(line,"line")

d = 50
h = 15 

def arch():
    arcs = Lines.Lines()
    arcs.add(O, 0.6*h*Z, Y*(d/2-0.6*h)+h*Z, d/2*Y+h*Z)
    arcs += arcs.rev(lambda p: p+Y*(d-2*p.y))
    return arcs.wire()

def archLine():
    return Part.makeLine(O, d*Y)

def archProfile():
    arcs = Lines.Lines()
    arcs.add(O, 0.6*h*Z, Y*(d/2-0.6*h)+h*Z, d/2*Y+h*Z)
    arcs += arcs.rev(lambda p: p+Y*(d-2*p.y))
    arcs.addBroken(d*Y-30*Z, -30*Z, O)
    return Part.Face(arcs.wire())


def spine(angle):
    w = 20
    avec = angleVec(angle)
    arcs = Lines.Lines()
    arcs.add(w*X, 3*X)
    arcs.add(O, avec*3)
    arcs.add(w*avec)
    return arcs.wire()
    

w1 = 1.15
w2 = 1.3
w3 = 1.4
w4 = 10 

def prof():
    ar = Lines.Lines()
    ar.add(O, w1/2 *X) 
    ar.add(w1/2*X+h/3*Z, w2/2*X+2*h/3*Z, (h-2)*Z+w2/2*X, w3/2*X+Z*h, w4/2*X+Z*h)
    ar.addBroken(w4/2*X, w4/2*X-3.5*Z,-3.5*Z)
    ar += ar.rev(symX)
    return ar.wire()



def profile():
    lines = Lines.Lines()
    x1, x2, x3 = [ X*x for x in [-2,-7,-10]]
    z1, z2 = [Z*z for z in [5,15]]
    lines.addBroken(O,x3,x3+z1,x2+z1,x2+z2,x1+z2,x1+z1,z1)
    lines += lines.rev(symX)
    return lines.wire()



if False:
    path = Part.Wire([path,line])
    p1 = profile().translate(r*X)
    p2 = profile().rotate(O,Z,90).translate(r*Y)

    sweep = doc.addObject("Part::Sweep")
    sweep.Sections = [ Part.show(prof()), Part.show(prof().reversed().translate(d*Y)) ]
    sweep.Spine =  Part.show(archLine()) 
    sweep.Solid = True
    sweep.recompute()

    Part.show(archProfile())

    koko = sweep.Shape.common(archProfile().translate(-100*X).extrude(200*X))
    Part.show(koko, "koko")

angle = 135 
s = spine(angle)
sweep = doc.addObject("Part::Sweep")
w = 20
avec = angleVec(angle)
p1 = prof().rotate(O,Z,-90).translate(X*w)
p2 = prof().rotate(O,Z,-90+angle).translate(w*avec)
sweep.Sections = [ Part.show(p1), Part.show(p2) ]
sweep.Spine =  Part.show(s) 
sweep.Solid = True
sweep.recompute()

shp = sweep.Shape.cut(Part.makeCylinder(2, 50))
Part.show(shp, "finally")

# Part.show(archProfile())
