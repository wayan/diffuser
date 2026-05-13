"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD
from FreeCAD import Base, Vector
import Part
from math import pi, sin, cos

# to be later imported from Util
class Util:
    def vec(x=0,y=0,z=0):
        return FreeCAD.Vector(x,y,z)

    def circlePoint(angle, r = 1):
        rad = Util.rad(angle)
        return Util.vec( cos(rad), sin(rad) ).multiply(r)

    def rad(angle):
        return pi * angle / 180

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

class Objimka:
    "This is a bracket class"

    def lalok(self,angle1, angle2, r1, r2, reverse = False):
        p1 = Util.circlePoint(angle1, r1)
        p2 = Util.circlePoint(angle2, r2)

        p12 = p1.add( Util.circlePoint(angle1 + 90, (r2 - r1) * (-1 if reverse else 1)  ))
        p21 = p2.add( Util.circlePoint(angle2 - 90, (r2 - r1) * (-1 if reverse else 1)))

        #if reverse:
        #    return Part.Shape(Util.polyline([p2,p21,p12,p1]))
        #else:
        #    return Part.Shape(Util.polyline([p1,p12,p21,p2]))

        if reverse:
            return Util.bez([p2,p21,p12,p1])
        else:
            return Util.bez([p1,p12,p21,p2])


    def build(self):
        Radius = 30
        RadiusHandle = 4 
        AngleStart = -45
        AngleEnd  = 225
        HandleAngle = 180 + 40 
        MaterialThickness = 11
        BorderThickness   = 4
        LalokWidth = 15
        LalokThickness = 2.5
        HrotRadius = 1.5 

        c1 = Part.makeCircle(30, vec(), vec(0,0,1,), AngleStart, AngleEnd)
        c2 = Part.makeCircle(
            RadiusHandle,
            vec(cos(Util.rad(AngleStart)), sin(Util.rad(AngleStart)) ).multiply(Radius + RadiusHandle),
            vec(0,0,1),
            180 + AngleStart,
            180 + AngleStart + HandleAngle
        )
        c3 = Part.makeCircle(
            RadiusHandle,
            vec(cos(Util.rad(AngleEnd)), sin(Util.rad(AngleEnd)) ).multiply(Radius + RadiusHandle),
            vec(0,0,1),
            AngleEnd - 180 - HandleAngle,
            AngleEnd - 180
        )

        shape = Util.fuse(
            [
                Part.Face( Part.Wire(c.makeOffset2D(BorderThickness / 2).Edges) ).extrude( vec(0,0,MaterialThickness) ) for c in [c1,c2,c3]
            ]
        )


        Laloks = 5
        r1     = Radius + BorderThickness / 2 
        r2     = r1     +  LalokWidth
        r3 = r1 + 3

        parts = []
        hrots = []
        for i in range(0, Laloks):
            a1 = AngleStart + i * (AngleEnd - AngleStart) / Laloks
            a2 = AngleStart + (i + 1) * (AngleEnd - AngleStart) / Laloks

            parts += [ 
                self.lalok(a1,(a1+a2)/2,(r1 if i == 0 else r3), r2), self.lalok(a2,(a1+a2)/2, (r1 if i + 1 == Laloks else r3),r2, True) 
            ]

            hc = Part.makeCircle(HrotRadius, Util.circlePoint( (a1+a2)/2, (r1+r2)/2), vec(0,0,1))

            hrots += [ Part.Face( Part.Wire(hc.Edges) ).extrude(vec(0,0,MaterialThickness)) ]        

        parts += Util.polyline([ Util.circlePoint(AngleEnd, r1), Util.circlePoint(AngleStart, r1)])


        laloks = Part.Face(Util.wire(parts)).cut(
            Part.Face(Part.Wire(Part.makeCircle(r1).Edges ))
        ).extrude(vec(0,0,LalokThickness))

        Part.show(Util.fuse([shape,laloks] + hrots))
        return





        #f1 = Part.Face( Part.Wire( ).makeOffset2D(3).Edges))
        #Part.show(f1.extrude(vec(0,0,6)))

        #ra = Util.fuse([
        #    ]).extrude(vec(0,0,6))
        
#            Part.makeCircle(
#                RadiusHandle,
#                vec(cos(Util.rad(AngleStart)), sin(Util.rad(AngleStart)) ).multiply(Radius+RadiusHandle),
#                vec(0,0,1),
#                180 + AngleStart,
#                180 + AngleStart + 180
#            ).makeOffset2D(3)
        # raa = ra.makeOffset2D(3)
        #Part.show(Part.Face(Part.Wire(ra.Edges)))
        return


NAME = "desticka"

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

objimka = Objimka()
objimka.build()
doc.recompute()
# doc.saveAs( os.path.join(os.path.dirname(__file__), "desticka.stl"))


