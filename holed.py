"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import FreeCAD, Part, Mesh, MeshPart
from FreeCAD import Base, Vector
from math import pi, sin, cos

# to be later imported from Util
class Util:
    def vec(x=0,y=0,z=0):
        return FreeCAD.Vector(x,y,z)

    def polyline(vertices):
        poly = []
        p0 = False
        for v in vertices:
            if p0:
                poly.append(Part.LineSegment(p0, v)) 
            p0 = v
        return poly

    def bez(poles):
        curve = Part.BezierCurve()
        curve.setPoles(poles)
        return curve

    def wire(shapes):
        return Part.Wire(Part.Shape(shapes).Edges)

    def fuse(shapes):
        if len(shapes) > 1:
            return shapes[0].multiFuse(shapes[1:])
        else:
            return shapes[0]

    def move(obj, x=0, y=0, z=0):
        obj.Placement = FreeCAD.Placement( vec(x,y,z), FreeCAD.Rotation(0, 0, 0), vec(0, 0, 0) )
        return obj

    def place(obj, placement):
        obj.Placement = placement
        return obj


vec = Util.vec


# END OF "IMPORT"

class Holed:
    "This is a bracket class"

    def build(self):
        doc = FreeCAD.ActiveDocument

        Radius = 7 
        Height = 20
        Pitch  = 1.5
        Width  = 1.5

        pitch = Pitch * 0.99
        profile = Part.Face(Part.Wire(Part.Shape( Util.polyline([ vec(Radius, 0, 0), vec(Radius + Width, 0, -pitch/2), vec(Radius, 0, -pitch), vec(Radius, 0, 0)] )).Edges))
        sprofile = Part.show(profile)

        #ls = Util.bez([vec(), vec(0,0,30), vec(0,30,40), vec(0,40,40)]).toShape()

        shelix      = Part.show( Part.makeHelix(Pitch, Height + 4, Radius))
        sw          = doc.addObject('PartDesign::Sweep','Sweep')
        sw.Sections = [ sprofile ]
        sw.Spine    = shelix
        sw.Solid    = True
        sw.Frenet   = True
        sw.Placement = FreeCAD.Placement( vec(0,0,-2), FreeCAD.Rotation(30, 0, 0), vec(0, 0, 0) )


        cyl  = Part.makeCylinder(Radius * 1.005, Height + 4) 
        Util.move(cyl, 0, 0, -2 )

        hole = Util.fuse([ cyl, sw.Shape ])
        return hole

        #hole = doc.addObject("Part::Fuse", "Hole")
        #hole.Base = scyl
        #hole.Tool = sw
        #return


        scyl2 = Part.show(Part.makeCylinder( 2 * Radius, Height ))

        cut = doc.addObject("Part::Cut", "xCut")
        cut.Base  = scyl2
        cut.Tool  = hole


        return

        cyl = Part.makeCylinder(Radius, Height)
        thread = Part.makeThread(1, 3,  Height, Radius)

        newshape = Util.fuse([cyl,thread])

        Part.show(newshape)

        return

    def build0(self):
        doc = FreeCAD.ActiveDocument

        Radius = 7 
        Height = 20
        Pitch  = 1.5
        Width  = 1.5

        pitch = Pitch * 0.99
        profile = Part.Face(Part.Wire(Part.Shape( Util.polyline([ vec(Radius, 0, 0), vec(Radius + Width, 0, -pitch/2), vec(Radius, 0, -pitch), vec(Radius, 0, 0)] )).Edges))
        sprofile = Part.show(profile)

        #ls = Util.bez([vec(), vec(0,0,30), vec(0,30,40), vec(0,40,40)]).toShape()

        shelix      = Part.show( Part.makeHelix(Pitch, Height + 4, Radius))
        sw          = doc.addObject('Part::Sweep','Sweep')
        sw.Sections = [ sprofile ]
        sw.Spine    = shelix
        sw.Solid    = True
        sw.Frenet   = True
        sw.Placement = FreeCAD.Placement( vec(0,0,-2), FreeCAD.Rotation(30, 0, 0), vec(0, 0, 0) )


        scyl  = Part.show( Part.makeCylinder(Radius * 1.005, Height + 4) )
        Util.move(scyl, 0, 0, -2 )

        hole = doc.addObject("Part::MultiFuse","Hole")
        hole.Shapes = [scyl, sw ]


        #hole = doc.addObject("Part::Fuse", "Hole")
        #hole.Base = scyl
        #hole.Tool = sw
        #return


        scyl2 = Part.show(Part.makeCylinder( 2 * Radius, Height ))

        cut = doc.addObject("Part::Cut", "xCut")
        cut.Base  = scyl2
        cut.Tool  = hole


        return

        cyl = Part.makeCylinder(Radius, Height)
        thread = Part.makeThread(1, 3,  Height, Radius)

        newshape = Util.fuse([cyl,thread])

        Part.show(newshape)

        return


NAME = "desticka"

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

holed = Holed()
shape = holed.build()
doc.recompute()
### End command Mesh_FromPartShape
mesh = doc.addObject("Mesh::Feature", "Pridavek")
mesh.Mesh = MeshPart.meshFromShape(Shape = shape, LinearDeflection=0.06, AngularDeflection=0.174533, Relative=False)
mesh.Label = "xCut_meshed"
doc.recompute()

Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()
# doc.saveAs( os.path.join(os.path.dirname(__file__), "desticka.stl"))


