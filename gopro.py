"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
import Mesh
import Lines
from Diffutil import vec, X, Y, Z, O, ortoRecFace, symX, symY, angleVec, halfSpace
import Gopro

doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)


# Part.show(revolvero())
#Part.show(Gopro.Holder().common(halfSpace(x=1)), "holder")
Part.show(Gopro.Holder(), "holder")


# Part.show(archProfile())
