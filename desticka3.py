"""filename.py

   Here a short but significant description of what the script do 

"""

import FreeCAD
import sys
from FreeCAD import Base, Vector
import Part
from math import pi, sin, cos

class Bracket:
    "This is a bracket class"

    i_name = 0

    def oName(self, name = None):
        if name is None:
            self.i_name = self.i_name + 1
            return "o" + str(self.i_name)
        else:
            return name 

    def cylinder(self, rad, alt, ang=360 ):
        obj = self.doc.addObject("Part::Cylinder", self.oName())
        obj.Angle =  ang
        obj.Radius = rad
        obj.Height = alt
        return obj

    def cube(self, l, w, h):
        obj = self.doc.addObject("Part::Box", self.oName())
        obj.Length = l 
        obj.Width  = w
        obj.Height = h
        return obj

    def cut(self, base, tool):
        obj = self.doc.addObject("Part::Cut", self.oName())
        obj.Base = base
        obj.Tool = tool
        obj.Refine = True
        return obj

    def fuse(self, shapes):
        obj = self.doc.addObject("Part::MultiFuse", self.oName())
        obj.Shapes = shapes
        obj.Refine = True
        return obj

    def shiftPlacement(self, x = 0.0, y = 0.0, z = 0.0) :
        return FreeCAD.Placement( Vector(x,y,z), FreeCAD.Rotation(0, 0, 0), Vector(0, 0, 0) )

    def move(self, obj, x=0, y=0, z=0):
        obj.Placement = FreeCAD.Placement( Vector(x,y,z), FreeCAD.Rotation(0, 0, 0), Vector(0, 0, 0) )
        return obj

    def withPlacement(self, obj, placement):
        obj.Placement = placement
        return obj

    def Xpriruba(self):
        ro   = self.PrirubaWOut / 2
        ri   = self.PrirubaWIn / 2
        ws   = self.PrirubaSpace2 / 2
        h    = self.PrirubaHeight

        spacer = lambda angle: self.withPlacement( self.cube( 2 * ro, 2 * ws, h ), FreeCAD.Placement( Vector( -ro, - ws, 0), FreeCAD.Rotation(angle,0,0), Vector(ro,ws,0) ))

        cout = self.cylinder( ro, h)
        cin  = self.cylinder( ri, h)
        return self.cut(cout, self.fuse( (cin, spacer(60), spacer(120), spacer(0) ) ))

    def armEnd(self, far):
        obj = self.cut( 
            self.cylinder(self.W / 2, self.H ),
            self.cylinder(self.Hole, self.H )
        )
        if not far:
            return obj

        p = self.move( self.priruba(), 0, 0, self.H )
        return self.fuse((obj, p))


    def arm(self):
        hole   = lambda : self.cylinder(self.Hole, self.H )
        cyl    = lambda : self.cylinder(self.W / 2, self.H )

        b = self.move( self.cube(self.L, self.W, self.H), y = - self.W / 2)
        return self.cut(
            self.fuse(
                ( cyl(), self.move(cyl(), x = self.L ), b, self.move(self.priruba(), x = self.L, z = self.H) )
            ),
            self.fuse(
                ( hole(), self.move( hole(), x = self.L ) )
            )
        )

    def build(self):
        angle   = 30
        placement = lambda left: FreeCAD.Placement( Vector(0, left * self.BaseWidth / 2, 0), FreeCAD.Rotation(left * angle, 0, 0), Vector(0, 0, 0) )

        return self.fuse(
            (   self.withPlacement(self.arm(), placement(1)),
                self.withPlacement(self.arm(), placement(-1))
            )
        )

    def polyline(self, vertices):
        poly = []
        p0 = False
        for v in vertices:
            if p0:
                poly.append(Part.LineSegment(p0, v)) 
            p0 = v
        return poly

    def priruba(self, r1, r2, ws, h):
        spacer = lambda angle: self.withPlacement( Part.makeBox( 2 * r1, 2 * ws, h ), FreeCAD.Placement( Vector( -r1, - ws, 0), FreeCAD.Rotation(angle,0,0), Vector(r1,ws,0) ))

        cout = Part.makeCylinder( r1, h)
        cin  = Part.makeCylinder( r2, h)
            
        return cout.cut(cin.multiFuse([spacer(60), spacer(120), spacer(0) ]))

    def bez(self, poles):
        geomCurve = Part.BezierCurve()
        geomCurve.setPoles(poles)
        return geomCurve

# building the arm
    def build3(self):
        wire = lambda shapes: Part.Wire(Part.Shape(shapes).Edges)

        # center of the hole
        CenterX  = 35
        CenterY  = - 35
        AdapterWidth = 12.5
        AdapterLength = 50
        AdapterHeight = 8 
        Thickness1 = 6
        Thickness2 = 3 
        Thickness3 = 3
        ThicknessBottom = 3 
        ThicknessFront =  4 
        Radius  = 12.5
        Length  = 15
        Width  = 50
        Angle1 = pi / 4 
        Angle2 = pi + pi / 6
        # radius of
        Hole1  = 3 

        vec2 = lambda x, y: Vector(x, y, 0)
        # point at radius
        pr = lambda ang: vec2( CenterX + Radius * cos(ang), CenterY + Radius * sin(ang))

        pta1 = pr(Angle1)
        pta2 = pr(Angle2)

        height = AdapterHeight + ThicknessBottom

        p0 = vec2(0, -ThicknessFront)

        elems = [
            self.bez([ p0,  p0.add(vec2(1,0).multiply(5)), 
                pta2.add(vec2(sin(Angle2), -cos(Angle2)).multiply(10)), 
                pta2
            ]),
            Part.Arc( pta2, pr( (Angle1 + Angle2) / 2 - pi ), pta1),
            self.bez([
                pta1,
                pta1.add( vec2(-sin(Angle1), cos(Angle1)).multiply(10) ), 
                vec2(0, AdapterLength /2),  
                vec2(0, AdapterLength)
            ])
        ]

        w = wire(
            elems + self.polyline([
                vec2( 0, AdapterLength),
                vec2(-(2*Thickness2+AdapterWidth), AdapterLength),
                vec2(-(2*Thickness2+AdapterWidth), -ThicknessFront),
                p0
            ]))

        w_cut = wire(
            elems + self.polyline([
                vec2( 0, AdapterLength),
                vec2(-Thickness2, AdapterLength),
                vec2(-Thickness2, -ThicknessFront),
                p0
            ])
        ).makeOffset2D(-Thickness1)

        vol_radius = self.move(
            Part.makeCylinder(Radius, height).cut( Part.makeCylinder(Hole1, height)),
            x=CenterX, y=CenterY, z=-height)

        vol_adapter = self.move(
            Part.makeBox(AdapterWidth, AdapterLength, AdapterHeight),
            x=-(Thickness2 + AdapterWidth),
            z=-AdapterHeight
        )

        hole_adapter1 = self.move(
            Part.makeCylinder(Hole1,height),
            x=-(Thickness2 + AdapterWidth/2), y=AdapterLength/2, z=-height
        )

        hole_adapter2 = Part.Face(Part.Wire( Part.makeCircle( Hole1, Vector(-Thickness2 - AdapterWidth / 2, 0, -AdapterHeight + 1 + Hole1), Vector(0,1,0)).Edges )).extrude(
            Vector(0, -ThicknessFront, 0 )
        )

        vol1 = Part.Face(w).cut(Part.Face(w_cut)).extrude(Vector(0, 0, - height)).fuse(vol_radius).cut(vol_adapter).cut(hole_adapter1).cut(hole_adapter2)

        priruba = self.move(self.priruba(10, 5, 2, 3), x=CenterX, y=CenterY)

        total = vol1.fuse(priruba)

        p1 = Vector(0, 0, height - Thickness3)
        p2 = Vector(Radius - Thickness3, 0, height - Thickness3)
        p3 = Vector(Radius - Thickness3, 0, 0) 
        p0 = Vector(0, 0)

        hole_last = self.move(
            Part.Face(wire([self.bez([p1, p2, p3])] + self.polyline([p3,p0,p1]))).revolve(
                Vector(0,0,0),
                Vector(0,0,1),
                360),
            x=CenterX, y=CenterY, z=-height
        )
        total = total.cut( hole_last )

        Part.show(total)

        return


        # w1 = Part.Wire(S1.Edges)
        w2 = w1.makeOffset2D( -Thickness1)
        vol1 = Part.Face(w1).cut(Part.Face(w2)).extrude(App.Vector(0, 0, - (AdapterHeight + ThicknessBottom)))
        Part.show(vol1 )

        # adapter holder
        w_total = AdapterWidth + Thickness2
        vol_b = self.move(Part.makeBox(w_total, AdapterLength, ThicknessBottom), x = -w_total, z = -AdapterHeight - ThicknessBottom )
        vol_l = self.move(Part.makeBox(Thickness2, AdapterLength, AdapterHeight), x = -(AdapterWidth + Thickness2), z = -AdapterHeight)
        vol_f = self.move(Part.makeBox(AdapterWidth + 2 * Thickness2, ThicknessFront, AdapterHeight + ThicknessBottom), 
                x=-(AdapterWidth+Thickness2), y=-ThicknessFront, z=-(AdapterHeight + ThicknessBottom))
        # Part.show(vol_b)
        # /Part.show(vol_l)

        # place under loc-lite
        vol_radius = self.move( Part.makeCylinder(Radius, 5), x=CenterX, y=CenterY, z=-5)
        # Part.show(vol_radius)

        vol_hole = self.move( Part.makeCylinder(Hole1, 20), x=CenterX, y=CenterY, z=-10)
        vol_hole2 = self.move( Part.makeCylinder(Hole1, 20), x=-(Thickness2 + AdapterWidth)/2, y=AdapterLength/2, z=-10)

        total = vol1.multiFuse([ vol_b, vol_l, vol_radius, vol_f]).cut(vol_hole).cut(vol_hole2)
        Part.show(total)


        return
        # PP = self.move( Part.makeCylinder(Radius, 5), x = CenterX, y = CenterY, z = 5 )
        #Part.show(P.fuse(PP))





    def build2(self):
        c1 = Vector(0, 0, 0)
        c2 = Vector(50, 0, 0)
        c23 = Vector(50,25,0)
        c3 = Vector(25, 50, 0) 
        c12 = Vector(25, -25, 0)
        b = self.bez3(c1,c12,c2)
#        return Part.Wire([
#            b, 
#            Part.LineSegment(c2, c3),
#            Part.LineSegment(c3, c1)
#        ])

        S1 = Part.Shape([
            self.bez3(c1,c12,c2),
            # Part.LineSegment(c2, c3),
            Part.Arc( c2, c23, c3 ),
            Part.LineSegment(c3, c1)
        ])
        W = Part.Face(Part.Wire(S1.Edges))
        P = W.extrude(App.Vector(0, 0, 10))
        Part.show(P)




NAME = "desticka"

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

bracket = Bracket()
bracket.doc = doc
bracket.W = 25 
bracket.Hole = 5
bracket.L = 100
bracket.H = 10

# parametry priruby
bracket.PrirubaWOut = 21
bracket.PrirubaWIn = 12
bracket.PrirubaHeight = 3
bracket.PrirubaSpace2 = 2 

bracket.BaseWidth = 40
bracket.build3()
doc.recompute()


