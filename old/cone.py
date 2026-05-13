"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from Diffutil import vec, angleVec, between, recPoints, unwrapShape, halfSpace, X, Y, Z
from Cone import Cone

doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

#cone = Cone("9_17e")
# cone = Cone("9_17test")
cone = Cone("30s")

diffuser = cone.build()
ldiff = diffuser.common(halfSpace(x=1))
#    Part.show(ldiff, "diff-%d" % angle)
Part.show(ldiff, "diffuser" )
diffu = unwrapShape(doc, ldiff).translate(300*X)
Part.show(diffu, "diffuser-unwrapped" )
Part.show(cone.viewDesk(), "viewdesk")

desk =  cone.reflectionDesk()
Part.show(desk, "desk")

desku = unwrapShape(doc, desk).translate(-300*X)
Part.show(desku, "desk-unwrapped")

solid = cone.reflectionDeskSolid().translate(300*Y)
Part.show(solid, "desk-solid")

#Part.show(cone.reflectionDeskProfileFront().translate(vec(300)),"front")
#Part.show(cone.reflectionDeskProfile().translate(vec(-300)),"complete")
#Part.show(cone.reflectionDeskSolid(), "ooo")



doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

