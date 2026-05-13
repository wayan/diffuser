"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys, math
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from Diffutil import vec, angleVec, between, recPoints, unwrapShape, halfSpace, X, Y, Z, ortoRecFace
from Cone import Cone
import importDXF
import copy

def mycone(name):
    cone = Cone(name)
    cone.ReflectionDeskDown = cone.LensDia / 2 + 27
    return cone

def supports(cone):
    t1 = cone.supportTriangle(False)
    t2 = cone.supportTriangle(True)
    width  = max(*[ t.BoundBox.XLength for t in [t1,t2]]) + 3
    height = max(*[ t.BoundBox.YLength for t in [t1,t2]]) + 5

    cone2 = copy.copy(cone)
    cone2.FlapThickness = 1.8
    cone2.FlapWidth += 2

    supports = []
    for col in range(0, 8):
        for row in range (0, 4 ):
            c = cone if row == 0 or row == 1 else cone2
            t = c.supportTriangle(row==1 or row==3)
            supports.append( t.translate(X * (col*width - t.BoundBox.XMin) + Y * (row*height - t.BoundBox.YMin)))

    print( len(supports), width, height)

    return Part.makeCompound(supports)

def dumpDiffuser(doc, name):
    cone = mycone(name)
    udiff = unwrapShape(doc, cone.build())
    exportAsDxf(udiff, "results/diffuser-%s.dxf" % name )

def dumpSupports(doc):
    cone = mycone("30s")
    exportAsDxf(supports(cone), "results/supports.dxf")

# exportAsDxf(supports(cone), "results/supports.dxf")
# exportAsDxf(supports(cone), "results/supports.dxf")


def dumpDesk(doc, name, narrow=False):
    cone = mycone(name)
    if narrow:
        cone.ConeThickness = 1.6
    udesk = unwrapShape(doc, cone.reflectionDesk())
    exportAsDxf(udesk, "results/desk-%s-%s.dxf" % (name, "narrow" if narrow else "normal" ))



def exportAsDxf(shp, path):
    o = Part.show(shp)
    __objs__ = []
    __objs__.append(o)
    if hasattr(importDXF, "exportOptions"):
        options = importDXF.exportOptions(path)
        importDXF.export(__objs__, path, options)
    else:
        importDXF.export(__objs__, path)
    
    del __objs__


doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

for name in ["9_17big", "30s", "9_17small"]:
    dumpDesk(doc, name, False)
    dumpDesk(doc, name, True)
    dumpDiffuser(doc, name)

# cone = Cone("9_17big")
# cone = Cone("30s")
# cone = Cone("9_17small")
# # cone.ConeThickness = 1.5
# cone.ReflectionDeskDown = cone.LensDia / 2 + 27
# 
# 
# 
# 
# diffuser = cone.build()
# desk =  cone.reflectionDesk()
# 
# Part.show(desk, "desk")
# Part.show(diffuser, "diffuser")
# Part.show(cone.supportTrianglesAtPlace(), "tr")
# 
# 
# udesk = unwrapShape(doc, desk)
# print(udesk.BoundBox)
# Part.show(udesk.translate(300*X), "udesk")
# 
# 
# Part.show(cone.supportTriangle(False).translate(200*Y), "t0")
# Part.show(cone.supportTriangle(True).translate(280*Y), "t1")
# 
# udiff = unwrapShape(doc, diffuser).translate(-300*X)
# Part.show(udiff, "udiff")
# 
# # Part.show(supports(cone),"supports")
# 
# exportAsDxf(udiff, "results/udiff.dxf")
# exportAsDxf(supports(cone), "results/supports.dxf")
# 
# # supports (many)
# Part.show(cone.supportTriangle(False).translate(200*Y), "t0")
# Part.show(cone.supportTriangle(True).translate(280*Y), "t1")
# 
# if False:
#     support = cone.reflectionDeskSupport()
#     Part.show(diffuser, "diffuser")
#     Part.show(support, "support")
# 
# 
#     Part.show(unwrapShape(doc, diffuser).translate(400*X), "udiffuser")
#     Part.show(unwrapShape(doc, desk).translate(800*X), "udesk")
#     Part.show(unwrapShape(doc, support).translate(1200*X), "usupport")
# 
# 
#     # doc.recompute()
#     Gui.SendMsgToActiveView("ViewFit")
#     Gui.activeDocument().activeView().viewIsometric()
# 
