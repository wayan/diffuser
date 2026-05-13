"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
import Mesh
import Lines
from Diffutil import vec, X, Y, Z, O, ortoRecFace, symX, symY, angleVec

doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

d = 50
h = 15 
w = 20
down = 4

def archLine():
    return Part.makeLine(O, d*Y)

def archProfile():
    arcs = Lines.Lines()
    arcs.add(O, 0.6*h*Z, Y*(d/2-0.6*h)+h*Z, d/2*Y+h*Z)
    arcs += arcs.rev(lambda p: p+Y*(d-2*p.y))
    arcs.addBroken(d*Y-30*Z, -30*Z, O)
    return Part.Face(arcs.wire())


def spine(angle, rnd=3):
    avec = angleVec(angle)
    arcs = Lines.Lines()
    arcs.add(w*X, rnd*X)
    arcs.add(O, avec*rnd)
    arcs.add(w*avec)
    return arcs.wire()

def revolvero():
    ww = 0.99*w
    arcs = Lines.Lines()
    arcs.addBroken(-down*Z, -down*Z+ww*X, 0.4*h*Z+ww*X)
    arcs.add(h*Z+ww*X,h*Z+X*(ww-0.6*h))
    arcs.addBroken(h*Z,-down*Z)
    f = Part.Face(arcs.wire())
    f = f.revolve(O,Z,360)
    return f
    
def profIn():
    w1 = 1.15
    w2 = 1.3
    w3 = 1.4
    w4 = 9 
    ar = Lines.Lines()
    ar.add(O, w1/2*Y) 
    ar.add(w1/2*Y+h/3*Z, w2/2*Y+2*h/3*Z, (h-2)*Z+w2/2*Y, w3/2*Y+Z*h, w4/2*Y+Z*h)
    ar.addBroken(w4/2*Y, w4/2*Y-down*Z,-down*Z)
    ar += ar.rev(symY)
    return ar.wire()

def prof(inner=False):
    w1 = 1.2
    w2 = 1.3
    w3 = 1.4
    w4 = 8
    ar = Lines.Lines()
    if inner:
        ar.add(O, w1/2*Y) 
        ar.add(w1/2*Y+h/3*Z, w2/2*Y+2*h/3*Z, (h-2)*Z+w2/2*Y, w3/2*Y+Z*h)
        ar.add(Z*h)
    else:
        ar.add(Z*h, w3/2*Y+Z*h, w4/2*Y+Z*h)
        ar.addBroken(w4/2*Y, w4/2*Y-down*Z,-down*Z)

    ar += ar.rev(symY)
    return ar.wire()


def create(angle):
    l = len(doc.Objects)
    w = 20
    avec = angleVec(angle)
    p1,p2 = [ prof().translate(X*w) for i in [1,2] ]
    p1.reverse()
    p2 = p2.rotate(O,Z,angle)
    sweep = doc.addObject("Part::Sweep")
    sweep.Sections = [ Part.show(p1), Part.show(p2) ]
    sweep.Spine =  Part.show(spine(angle,7)) 
    sweep.Solid = True
    sweep.recompute()
    shp = sweep.Shape


    p1,p2 = [ prof(True).translate(X*w) for i in [1,2] ]
    p1.reverse()
    p2 = p2.rotate(O,Z,angle)
    sweep = doc.addObject("Part::Sweep")
    sweep.Sections = [ Part.show(p1), Part.show(p2) ]
    sweep.Spine =  Part.show(spine(angle,1.4)) 
    sweep.Solid = True
    sweep.recompute()
    shpIn = sweep.Shape

    for o in doc.Objects[l:]:
        doc.removeObject(o.Name)

    shp = shp.cut(shpIn)
    shp = shp.common(revolvero())
    shp = shp.cut(Part.makeCylinder(1.5,50).translate(X+Y))
    return shp

# Part.show(revolvero())
Part.show(create(135), "xyz135")
Part.show(create(90).translate(X*80), "xyz90")


# Part.show(archProfile())
