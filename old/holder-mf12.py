"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
import Mesh
from Diffutil import vec


# END OF "IMPORT"

NAME = "diffuserholder"

HolderHeight = 35

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)
Mesh.insert(u"/home/danielr/desticka_k_blesku/MF12-BabyMount.stl")

shpm = Part.Shape()
shpm.makeShapeFromMesh(doc.getObject('MF12_BabyMount').Mesh.Topology, 0.1, False)
shp = Part.Solid(Part.Shell(shpm.Faces))

shp.rotate(vec(),vec(0,0,1),30)
shp.rotate(vec(),vec(0,-1),90)
doc.recompute()
bb = shp.BoundBox
print("X",bb.XMin,bb.XMax)
print("Y",bb.YMin,bb.YMax)
print("Z",bb.ZMin,bb.ZMax)

shp.translate( vec( -0.5* (bb.XMax+bb.XMin), -0.5*(bb.YMax+bb.YMin), -bb.ZMin) )
# doc.recompute()
bb = shp.BoundBox
print("X",bb.XMin,bb.XMax)
print("Y",bb.YMin,bb.YMax)
print("Z",bb.ZMin,bb.ZMax)

if bb.ZMax > HolderHeight:
    b = 200
    shp = shp.cut( Part.makeBox(b,b,bb.ZMax - HolderHeight).translate( vec(-b/2,-b/2)))
    shp.translate(vec(0,0,bb.ZMax-HolderHeight))
else:
    profile = Part.Face(Part.makePolygon([ vec(50*x,50*y, 1) for x,y in [ [-1,-1], [1,-1], [1,1], [-1,1], [-1,-1] ]]))
    profile = profile.common(shp).extrude(vec(0,0,-(HolderHeight+1-bb.ZMax)))
    shp = shp.fuse(profile)
    shp.translate(vec(0,0,HolderHeight-bb.ZMax))

#profile = Part.Face(Part.makePolygon([ vec(0,50*x,50*y) for x,y in [ [-1,-1], [1,-1], [1,1], [-1,1], [-1,-1] ]]))
#Part.show(profile, "prof2")
Part.show(shp, "haleluja")

#>>> __shape__.makeShapeFromMesh(FreeCAD.getDocument('Unnamed').getObject('MF12_BabyMount').Mesh.Topology, 0.100000, False)
#>>> FreeCAD.getDocument('Unnamed').getObject('MF12_BabyMount001').Shape = __shape__
#>>> FreeCAD.getDocument('Unnamed').getObject('MF12_BabyMount001').purgeTouched()
#>>> del __shape__
# >>> ### End command Part_ShapeFromMesh
# >>> # Gui.Selection.addSelection('Unnamed','MF12_BabyMount')

doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()



