"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import math
# from math import pi, sin, cos, tan

# to be later imported from Util
class Util:
    Meshno = 0

    def vec(x=0,y=0,z=0):
        return FreeCAD.Vector(x,y,z)

    def tangentPoint(p, c, r, top=1):
        d = (p - c).Length
        a = math.sqrt(d ** 2 - r ** 2)

        v = (c - p).normalize()
        p = c - v * (r * r / d) + v.cross(FreeCAD.Vector(0,0,top)) * (a * r / d )
        return p

    def place(obj, placement):
        obj.Placement = placement
        return obj

    def writeMesh(shape, filename):
        mesh = MeshPart.meshFromShape(Shape = shape, LinearDeflection=0.03, AngularDeflection=0.174533, Relative=False)
        #Util.Meshno = Util.Meshno + 1
        #meshobj = doc.addObject("Mesh::Feature", ("mesh-%d" % Util.Meshno))
        #meshobj.Mesh = mesh
        mesh.write(os.path.join(os.path.dirname(__file__), filename))


vec = Util.vec


# END OF "IMPORT"

class Holder:

    # types of holder
    STRAIGHT = 1
    BRACKETED_ONE = 2 
    BRACKETED_TWO = 3

    def __init__(self):

        # "circular" mf12 holder
        self.RadiusOut = 60.0
        self.RadiusIn = self.RadiusOut - 4.9 
        self.ThicknessOut = 10
        self.ThicknessIn  = 7.6 
        self.WidthOut     = 34
        self.WidthIn      = 28
        self.MinHeight    = 15 - 3
        self.DentWidth    = 2.8
        self.DentHeight   = 3 
        self.DentDepth    = 3.2



        holeTolerance = 1.007
        self.LocLineDia = 25
        self.LocLineDiaIn = 21.6 * (1 / holeTolerance) 
        self.LocLineDiaInIn = 11.8 * holeTolerance
        self.LocLineSpacer = 1.7 * holeTolerance
        self.LocLineHeight = 3 
        self.LocLineHoleHeight = 6.15


        self.HotShoeWidth = 18.1
        self.HotShoeDepth = 18.1
        self.HotShoeHeight = 1.7
        self.HotShoeInnerWidth = 12.5
        self.HotShoeInnerDepth = 12.5
        self.HotShoeInnerHeight = 2 
        self.ThreadDia     = 22
        self.ThreadHeight  = 8 
        self.ThreadPitch  = 1.5

        self.BigNutDia = self.ThreadDia + 15
        self.BigNutHeight = 7 

        self.TopThickness = 5
        self.ConnectionDia = 12
        self.ConnectionHeight = 2.5 

        # connecting with bolt and nut
        self.BoltHeadDia = 10.2
        self.BoltHeadHeight  = 3.1

        # radius of M4 Nut
        self.NutDia = 7.8 * holeTolerance
        self.NutHeight = 3.4 * holeTolerance 

        # radius of hole
        self.BoltDia  = 4.2

    def boredHole(self, height):
        return Part.makeCylinder(self.BoltDia/2, height)

    def smallNutPocket(self, height = None):
        return self.nutPocket(self.NutDia, height if height != None else self.NutHeight)

    def locLineProtrusion(self):
        cyl = Part.makeCylinder(self.LocLineDiaIn/2, self.LocLineHeight)
        cyl = cyl.cut( Part.makeCylinder( self.LocLineDiaInIn/2, self.LocLineHeight)) 
        for angle in [0,60,120]:
            spacer = Part.makeBox( self.LocLineDia, self.LocLineSpacer, self.LocLineHeight )
            spacer.translate( vec(-self.LocLineDia/2, -self.LocLineSpacer/2) )
            cyl = cyl.cut(spacer.rotate( vec(), vec(z=1), angle ))
        return cyl

    def buildRod(self):
        hsw = self.HotShoeWidth 
        hsd = self.HotShoeDepth
        hsh = self.HotShoeHeight

        mw = self.HotShoeInnerWidth
        md = self.HotShoeInnerDepth
        mh = self.HotShoeInnerHeight

        bottom = Part.makeBox( hsw, hsd, hsh)

        # .translate( vec(-hsw/2, -hsd/2) )
        middle = Part.makeBox( mw, md, mh )
        thread = self.maleThread( self.ThreadDia, self.ThreadPitch, self.ThreadHeight )
        connection = self.connectionPocket(False)

        top = 0
        body = None
        for part in bottom, middle, thread, connection:
            # to recompute BoundBox
            part.tessellate(0.01)
            bb = part.BoundBox
            zlen = bb.ZLength
            part.translate( vec(-bb.Center.x, -bb.Center.y, top - bb.ZMin))
            top = top + zlen
            body = body.fuse(part) if body != None else part

        body = body.cut( self.nutPocket(self.NutDia, self.NutHeight) )
        body.tessellate(0.01)
        body = body.cut( self.boredHole(body.BoundBox.ZLength + 0.5))
        return body

    def buildTop(self):
        width  = 20
        angle  = 30
        height = self.TopThickness 
        depth = self.LocLineDia
        thickness = 5.5
        radius = width / 2 / math.sin( angle/2 * math.pi / 180 )

        cylOut, cylIn = [
            Part.makeCylinder( radius + i * depth / 2, height, vec(), vec(z=1), angle )
                for i in [1,-1]
        ]

        body = cylOut.cut(cylIn).rotate(vec(), vec(z=1), 90 - angle / 2).translate(vec(y=-radius)).cut(self.connectionPocket() )


        top = Part.makeCircle(depth / 2)

        pts = [depth / 2 * v for v in [ vec(0,-1), vec(1,-1), vec(1,1), vec(0,1), vec(0,-1) ]]
        bc, bp = [ Part.Face(Part.Wire( s )) for s in [ top.copy(), Part.makePolygon(pts) ] ]

        bottom = Part.Wire( bc.fuse(bp).removeSplitter().Edges )
        top.translate(vec(z=thickness))

        locline = (
                Part.makeLoft([bottom, top ], True)
                .cut( self.boredHole( thickness) )
                .cut( self.nutPocket(self.NutDia,self.NutHeight) )
                .fuse( self.locLineProtrusion().translate(vec(z=thickness)))
                .rotate(vec(),vec(0,1), 90)
        )

        locline.tessellate(0.01)
        locline.translate(vec(z = -locline.BoundBox.ZMin))

        l = locline.copy().rotate(vec(y=-radius), vec(z=1), - angle/2)
        r = locline.copy().rotate(vec(), vec(z=1), 180).rotate(vec(y=-radius), vec(z=1), angle/2  )
        hole = self.boredHole(thickness)
        return body.fuse(l).fuse(r).cut(hole)

    def nutPocket(self, dia, height):
        r = dia / 2
        poly = Part.makePolygon([
            FreeCAD.Rotation( vec(z=1), angle ).multVec(vec(r) )
              for angle in range(30, 400, 60)
        ])

        f = Part.Face( Part.Wire(poly) ).extrude( vec(0, 0, height) ).removeSplitter()
        f.tessellate(0.01)

        edges = [ e for e in f.Edges if e.BoundBox.ZLength >= self.NutHeight - 1 ]
        if len(edges) > 0:
            f = f.makeFillet(0.1, edges)
        return f


    def mf12Disk(self):
        rin = self.RadiusIn
        rout = self.RadiusOut
        ti = self.ThicknessIn / 2
        to = self.ThicknessOut / 2
        cut = 0.5

        # part of the profile
        pts = [ 
            [0, ti],
            [rin, ti],
            [rin, to - cut],
            [rin + cut, to],
            [rout - cut, to],
            [rout, to - cut]
        ]
        pts = [ vec(x,0,z) for x,z in pts + [ [x,-y] for x,y in pts[::-1] ] + [ pts[0] ] ]
        return Part.Face(Part.Wire( Part.makePolygon(pts))).revolve(vec(),vec(z=1),360)

    def perpHolder(self):
        #    /Part.makeCylinder(self.RadiusOut, self.ThicknessOut).
        ti = self.ThicknessIn / 2
        to = self.ThicknessOut / 2
        lr = self.LocLineDia / 2

        disk = self.mf12Disk()
        for zs in [ to - self.DentDepth, -to]:
            dent = Part.makeBox(self.DentWidth, self.DentHeight, self.DentDepth)
            dent.translate(vec(-self.DentWidth / 2, self.RadiusOut - self.DentHeight, zs))
            disk = disk.cut( dent )

        y1 = lr
        y2 = y1 + self.MinHeight - 4
        big = y2 + 20

        # B - spline
        pts = [ vec(self.WidthOut/2, big) ]
        pts.extend( self.ptsBetween(pts[-1], vec(self.WidthOut/2, y2), 4) )
        pts.extend( self.ptsBetween(pts[-1], vec(ti, y1), 3 ) )
        pts.extend( self.ptsBetween(pts[-1], pts[-1] + vec(0,-3), 3) )
        ptsl = [ vec(-v.x,v.y) for v in pts[::-1] ]

        parts = [
            Part.Shape([ Part.BSplineCurve(pts) ]),
            Part.makeLine( pts[-1], ptsl[0] ),
            Part.Shape([ Part.BSplineCurve(ptsl) ]),
            Part.makeLine( ptsl[-1], pts[0] )
        ]
        shape1 = Part.Face(Part.Wire(parts)).extrude(vec(z=2*to)).translate(vec(z=-to))
        shape1 = shape1.common( disk.translate(vec(y = lr + self.MinHeight + 4 - self.RadiusOut)) )
        shape1 = shape1.rotate(vec(), vec(0,1), 90)

        # loc line
        shape2 = Part.makeCylinder( lr, 2 * ti )
        shape2 = shape2.fuse( self.locLineProtrusion().translate(vec(z=2*ti)))
        shape2 = shape2.cut( self.boredHole(big) )
        shape2 = shape2.cut( self.smallNutPocket() )
        shape2 = shape2.translate( vec(z=-ti) )

        return shape2.fuse(shape1)


    def buildHolder(self, holderType):
        #    /Part.makeCylinder(self.RadiusOut, self.ThicknessOut).
        ti = self.ThicknessIn / 2
        to = self.ThicknessOut / 2
        lr = self.LocLineDia / 2


        rin = self.RadiusIn
        rout = self.RadiusOut

        dent = Part.makeBox(self.DentWidth, self.DentHeight, self.DentDepth)
        dent.translate(vec(-self.DentWidth / 2, self.RadiusOut - self.DentHeight))
        disk = self.mf12Disk()
        disk = disk.cut( dent.copy().translate(vec(z=to -self.DentDepth)) )
        disk = disk.cut( dent.copy().translate(vec(z=-to)) )

        large = 100
        y1 = lr
        y2 = y1 + self.MinHeight - 4

        wbottom = lr
        if holderType == self.BRACKETED_TWO:
            wbottom = ti


        shape1 = (
            Part.Face(Part.Wire(Part.makePolygon([
                vec( - wbottom, y1 ),
                vec( - self.WidthOut  / 2, y2 ),
                vec( - self.WidthOut  / 2, large ),
                vec( self.WidthOut  / 2, large ),
                vec( self.WidthOut  / 2, y2 ),
                vec( wbottom, y1 ),
                vec( - wbottom, y1 )
            ])))
            .extrude(vec(z=2*to)).translate(vec(z=-to))
            .common( disk.translate(vec(y = lr + self.MinHeight + 4 - self.RadiusOut)) )
        )

        if  holderType == self.BRACKETED_ONE:
            top = Part.makeCircle(lr)
            bottom = Part.Wire(
                Part.Face(Part.Wire(top.copy()))
                .fuse(
                    Part.Face(Part.Wire(Part.makePolygon([
                        vec( -lr, lr),
                        vec( -lr, 0),
                        vec( lr, 0),
                        vec( lr, lr),
                        vec( -lr, lr)
                    ])))
                )
                .removeSplitter()
                .Edges
            )
            shape2 = Part.makeLoft([bottom,top.translate(vec(0,0,2*ti))], True)
        elif holderType == self.BRACKETED_TWO:
            shape2 = Part.makeCylinder( lr, 2 * ti ).fuse(
                Part.makeBox( self.LocLineDia / 2, y1, 2 * ti)
                .translate( vec(-self.LocLineDia /2 ) )
            )
        else:
            shape2 = Part.makeCylinder( lr, 2 * ti ).fuse(
               Part.makeBox( self.LocLineDia, y1, 2 * ti)
                .translate( vec(-self.LocLineDia / 2) )
            )

        shape2 = (
            shape2
            .translate( vec(z=-ti) )
            .fuse( self.locLineProtrusion().translate(vec(z=ti)))
            .cut( self.boredHole(large).translate( vec(z=-large/2) ))
            .cut( self.nutPocket(self.NutDia, self.NutHeight) .translate(vec(z=-ti)) )
        ) 
        if holderType == self.BRACKETED_ONE:
            shape2 = shape2.rotate(vec(), vec(1), 90)
            bb2 = shape2.BoundBox
            bb1 = shape1.BoundBox
            shape2 = shape2.translate( vec(y=bb1.YMin-bb2.YMax, z=ti - bb2.XMax))

        if holderType == self.BRACKETED_TWO:
            shape2 = (
                shape2
                    .rotate(vec(), vec(0,1), 90)
                    .rotate(vec(), vec(-1,0), 90)
            )
            shape2 = (
                    shape2.translate(vec(z = -ti - shape2.BoundBox.ZMin))
            )
        return shape1.fuse(shape2)
    
    def bigNut(self):
        freq = 8 
        freq = 12
        rs   = 2.5 
        h = self.BigNutHeight 
        r = self.BigNutDia / 2
        body = Part.makeCylinder(r, h)

        # rounded dent
        dent = Part.makeCylinder(rs, h).translate(vec(r))
        for a in range(0, 360, int(360 / freq)):
            body = body.cut(dent.copy().rotate(vec(),vec(z=1),a))

        edges = [ e for e in body.Edges if e.BoundBox.ZLength < 0.5 ]
        if len(edges) > 0:
            body = body.makeFillet(0.75, edges)

        body = body.cut(self.maleThread(self.ThreadDia, self.ThreadPitch, h ))
        return body

    def maleThread(self, dia, pitch, height):
        h = height 
        outer = dia  / 2
        inner, iinner, oouter = [
            outer + ( k / 8 * pitch * math.sin(math.pi / 3) )
            for k in [ -5, -7, 1 ]
        ]

        # the thread is a bit narrower
        p = 0.99 * pitch

        pts = [ vec(x,0,z) for x,z in [[iinner, 0], [outer,  -p/2 + p/16], [outer,  -p/2 - p/16], [iinner,  -p], [iinner, 0]] ]
        profile = Part.Wire( Part.makePolygon(pts).Edges)
        helix = Part.Wire(Part.makeHelix(pitch, h + pitch, iinner ).Edges)
        pps = helix.makePipeShell( [profile], True, True)
        pps.applyRotation( FreeCAD.Rotation( vec(0,0,1), 30 ))
        pps = pps.common( Part.makeCylinder(dia, h) )
        return pps.fuse( Part.makeCylinder(inner, h))

    def connectionPocket(self, pocket=True):
        return self.nutPocket(
            self.ConnectionDia - (0 if pocket else 0.2), 
            self.ConnectionHeight - (0 if pocket else 0.2)
        )

    def connectorBody(self):
        w1 = 30.4
        w2 = 18
        w3 = 3.8
        h1 = 25.3
        h2 = 19.1

        ww = w1 / 2 + 3 
        pts = [ vec(x,0,z) for x,z in [[-ww, h1/2], [-w2/2, h1/2], [-w3/2, h2/2], [w3/2, h2/2], [w2/2, h1/2], [ww, h1/2], [ww,0], [-ww,0], [-ww,h1/2] ]]
        return Part.Face(Part.Wire(Part.makePolygon(pts))).revolve(vec(), vec(1), 360) 

    def ptsBetween(self,p1,p2,n,firstPoint=False):
        return [ (p1 * (n - i) + p2 * i) * (1 / n) for i in range(0 if firstPoint else 1, n + 1) ]

    def connectionHolder(self, top = True):
        thickness = 6
        r = 36 / 2
        r2 = r + ( 0 if top else 2)
        x = 12
        width = 24 

        p = vec(math.sqrt(r*r - thickness*thickness), thickness)
        depth = x + p.x

        pts = [ vec(-depth, 0) ]
        pts.extend( self.ptsBetween( pts[-1], vec(pts[-1].x, thickness), 1 ) )
        pts.extend( self.ptsBetween( pts[-1], vec(-p.x, pts[-1].y), 3 ) )

        # angle
        pts.extend( [v for v in [  vec(r*math.cos(a), min(r, r2*math.sin(a))) for a in [ deg * math.pi /180 for deg in range(180, 90, -10) ] ] if v.y > thickness ] )
        pts.extend( [ vec(0, r) ] + [ vec(-v.x, v.y) for v in pts[::-1] ] )

        # converts x => y, y => z
        pts = [ vec(0, v.x, v.y) for v in pts ]

        bezs = Part.Shape([ Part.BSplineCurve(pts) ])
        face = Part.Face(Part.Wire(bezs.Edges + Part.makeLine( pts[-1], pts[0] ).Edges ))

        body = face.extrude( vec(width) ).translate(vec(-width / 2)).cut(self.connectorBody())

        innerHeight = 19.1 / 2

        for i in [-1, 1]:
            ys = i * (x + p.x - x / 2 - 3.5) 

            pocket = self.connectionPocket(not(top)).translate( vec(0,ys) )
            if top:
                body = body.cut( pocket )
                # place for nut head (outside) 
                body = body.cut( Part.makeCylinder(self.BoltHeadDia/2, 10).translate(vec(0,ys,thickness - 0.1)) )
            else:
                pocket.translate(vec(z=-self.ConnectionHeight) )
                body = body.fuse( pocket )
                body = body.cut(
                    self.smallNutPocket(30)
                        .rotate(vec(), vec(0,0,1), 90)
                        .translate(vec(0,ys, 1 + thickness - self.NutHeight) )
                )
                body = body.cut( self.connectionPocket().translate( vec(0,0, r - self.ConnectionHeight + 0.1) ))
                body = body.cut( self.boredHole(r + 5) )
                # place for the nut head (inside)
                body = body.cut( Part.makeCylinder(self.BoltHeadDia / 2, innerHeight + self.BoltHeadHeight) )

            body = body.cut( self.boredHole(20).translate( vec(0, ys, -self.ConnectionHeight - 1) ) )
        return body

        #return body

        # rounding from top

        d = depth + 0.2 
        pts = [ vec(0,-d) ]
        pts.extend( self.ptsBetween(pts[-1], vec(width / 2, -d ), 2) )
        pts.extend( self.ptsBetween(pts[-1], vec(width /2 , d), 4) )
        pts.extend( self.ptsBetween(pts[-1], vec(0, d), 2 ))

        edges = []
        for i in [pts, [ v.scale(-1,1,1) for v in pts[::-1] ]]:
            bez = Part.BSplineCurve(i)
            edges.extend( Part.Shape([bez]).Edges )

        # top cut
        topCut = Part.Face(Part.Wire(edges)).extrude( vec(0,0,60) ).translate( vec(0,0,-30) )
        body = body.common(topCut)
        return body


NAME = "diffuserholder"

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)


# tohle ma byt true
if True:
    h = Holder()

    shapes = [
        h.connectionHolder(True),
        h.connectionHolder(False).translate(vec(50) ),
        h.buildRod().translate(vec(120)),
        h.bigNut().translate(vec(160)),
        # h.perpHolder().translate(vec(200)),
        # h.perpHolder().translate(vec(240))
    ]

    p = 0
    shape = None
    for nshape in shapes:
        nshape.tessellate(0.1)
        xl = nshape.BoundBox.XLength
        nshape.translate(vec(p - nshape.BoundBox.XMin) )
        shape = shape.fuse(nshape) if shape != None else nshape
        p = p + xl + 15


Part.show(shape)

#mesh = MeshPart.meshFromShape(Shape = shape, LinearDeflection=0.01, AngularDeflection=3, Relative=False)
#meshobj = doc.addObject("Mesh::Feature")
#meshobj.Mesh = mesh


doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

