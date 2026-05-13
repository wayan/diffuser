"""filename.py

   Here a short but significant description of what the script do 

"""

import FreeCAD
from FreeCAD import Base, Vector
import Part
from math import pi, sin, cos

def cylinder(doc, rad, alt, ang=360 ):
    name = 'cyl'
    obj = doc.addObject("Part::Cylinder", "cyl")
    obj.Angle =  ang
    obj.Radius = rad
    obj.Height = alt
    return obj

NAME = "desticka"

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

c = cylinder(doc, 10, 40)

c2 = cylinder(doc, 5, 50, 180)
# c2.Placement = FreeCAD.Placement(Vector(0, 0, 0), FreeCAD.Rotation(0, 0, -90), Vector(0, 0, 15))
c2.Placement = FreeCAD.Placement(Vector(0, 0, 40), FreeCAD.Rotation(0,90,0), Vector(0,0,0))
fuse = DOC.addObject("Part::MultiFuse", 'mfuse')
fuse.Shapes = ( c, c2 )
fuse.Refine = True
doc.recompute()
