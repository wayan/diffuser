"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos

# to be later imported from Util
class Util:
    Meshno = 0

    def vec(x=0,y=0,z=0):
        return FreeCAD.Vector(x,y,z)

    def bez(poles):
        curve = Part.BezierCurve()
        curve.setPoles(poles)
        return curve

    def tangentPoint(p, c, r, top=1):
        d = (p - c).Length
        a = math.sqrt(d ** 2 - r ** 2)

        v = (c - p).normalize()
        p = c - v * (r * r / d) + v.cross(FreeCAD.Vector(0,0,top)) * (a * r / d )
        return p

    def wire(shapes):
        return Part.Wire(Part.Shape(shapes).Edges)

    def fuse(shapes):
        if len(shapes) > 1:
            return shapes[0].multiFuse(shapes[1:])
        else:
            return shapes[0]

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

class UmbrellHolder:
    def __init__(self):
        # center of the hole
        holeTolerance = 1.007
        self.Thickness   = 2.0
        self.ShaftDia    = 10.2 * holeTolerance
        self.Height      = 80
        self.BottomDia   = 25
        self.BottomHeight = 10


    # 3/8 thread
    def innerThread(self, h):
        inch = 25.4
        n  = 16
        outer = 3 / 8  * inch
        pitch = inch / n

        inner, iinner, oouter = [
            outer + 2 * ( k / 8 * pitch * sin(pi / 3) )
            for k in [ -5, -7, 1 ]
        ]
        helix = Part.Wire(Part.makeHelix(pitch, h, iinner / 2).Edges)

        print([outer, inner, iinner, oouter, sin(pi/3) ])
        profile = Part.Wire( Part.makePolygon([ 
            vec(iinner / 2, 0, 0), 
            vec(oouter / 2 , 0, -pitch/2), 
            vec(iinner / 2, 0, -pitch), 
            vec(iinner / 2, 0, 0)
            ] ).Edges)
        # return profile
        pps = helix.makePipeShell( [profile], True, True)
        pps.applyRotation( FreeCAD.Rotation( vec(0,0,1), 30 ))
        return pps.fuse( Part.makeCylinder(inner / 2, h))

    def build(self):
        rin = self.ShaftDia / 2
        rout = rin + self.Thickness
        h = self.Height

        sh = Part.makeCylinder(rout, self.Height).cut(
            Part.makeCylinder(rin, self.Height))


        # .translate( vec(0,0,-self.BottomHeight - 1) )

        rcut = h * 0.27 
        hcut = 1.5 * self.ShaftDia
        cylcut = Part.makeCylinder(rcut, hcut)

        if False:
            cylcut.translate( vec(- rcut - self.ShaftDia / 2  + 1 * self.Thickness, 0, 2*h/3) )
            sh = sh.cut(cylcut)

        cylcut.translate(vec(0,0,-hcut / 2))
        cylcut.applyRotation( FreeCAD.Rotation(vec(1,0,0), 90) )
        cylcut.translate( vec(- rcut - self.ShaftDia / 2  + 1 * self.Thickness, 0, 2*h/3) )

        sh = sh.cut(cylcut)
        sh = sh.removeSplitter()
        sh = sh.makeFillet(0.5, [ e for e in sh.Edges if e.BoundBox.ZMax > 0.5 ] )


        bottom = Part.makeCylinder(self.BottomDia / 2, self.BottomHeight)
        sh = sh.fuse(
            bottom.makeFillet(2, [ e for e in bottom.Edges if e.BoundBox.ZMax > 0.5 ])
        )
        thread = self.innerThread(15)
        sh = sh.cut(thread)

        return sh

class FilterThread:
    def __init__(self):
        # center of the hole
        self.dia = 46
        self.pitch = 0.75

    def innerThread(self, h):
        r = self.dia / 2
        pitch = self.pitch
        hpitch =  pitch * sin(pi / 3)
        inner = r - 5 * hpitch / 8
        iinner = r - 7 * hpitch / 8

        helix = Part.Wire(Part.makeHelix(pitch, h, iinner).Edges)

        profile = Part.Wire( Part.makePolygon([ 
            vec(iinner, 0, 0), 
            vec(r , 0, -pitch/2), 
            vec(iinner, 0, -pitch), 
            vec(iinner, 0, 0)
            ] ).Edges)
        # return profile
        pps = helix.makePipeShell( [profile], True, True)
        pps.applyRotation( FreeCAD.Rotation( vec(0,0,1), 30 ))
        return pps.fuse( Part.makeCylinder(inner, h))

    def build(self):
        return self.innerThread(20)



class Bracket:
    "This is a bracket class"

    def __init__(self):
        # center of the hole
        self.CenterX     = 35
        self.CenterY     = - 35

        # radius of hole
        self.HoleRadius  = 3 

        # radius of the support
        self.Radius  = 12.5
        # priruba 21.6 (trosku mensi)
        self.PrirubaRadius1 = 21 / 2
        # priruba 11.6 (trosku vetsi)
        self.PrirubaRadius2 = 12.2 / 2
        # priuba 1.6 mm (trosku vetsi)
        self.PrirubaSpacer = 2
        self.PrirubaHeight = 2

        self.FrontHoleHeight = 1.5

        # width 11.8 (trosku vetsi)
        self.AdapterWidth = 12.1
        self.AdapterLength = 48.7 
        self.AdapterFrontHeight = 12.5

        self.Thickness1 = 6
        self.AdapterThicknessSide = 4 
        self.ThicknessUnderBolt = 3
        self.AdapterThicknessBottom = 4 
        self.AdapterThicknessFront =  5.5

        ###### dimensions #######
        holeTolerance = 1.007

        # bolt
        self.BoltDia = 6.5 * holeTolerance 

        # radius of M6 Nut
        self.NutDia = 11.25 * holeTolerance

        # ordinary nut
        self.NutHeight = 5 * holeTolerance
        # low profile nut
        # self.NutHeight = 3.2 * holeTolerance


        self.AdapterCenterY = 26

        self.BraceWidth = 5
        self.SupportDia = 25.4

        self.AdapterHeight = 7.5 
        self.AdapterHolderThickness = 3.5 
        self.BracketThickness = 20 - 9.7 
        self.AdapterCenterX = -15

        # position  
        self.RightCenterX = 35
        self.RightCenterY = -35
        self.LeftCenterX = -90
        self.LeftCenterY = 70



        # 
        self.LocLineDia = 25
        self.LocLineDiaIn = 21.6 * (1 / holeTolerance) 
        self.LocLineDiaInIn = 11.8 * holeTolerance
        self.LocLineSpacer = 1.7 * holeTolerance
        self.LocLineHeight = 3 
        self.LocLineHoleHeight = 6.15


        # hotshoe - outer dimensions
        self.HotShoeWidth      = 25
        self.HotShoeLength     = 25

        self.HotShoeBaseHeight   =  20 - 10.7 

        self.HotShoeSpaceHeight = 1

        self.HotShoePlateWidth = 18.8
        self.HotShoePlateLength = 20.1
        self.HotShoePlateHeight = 2.1

        self.HotShoePlateHeightAbove = 1.6
        self.HotShoeInnerWidth = 12.9

        ######### compute ########
        self.LeftCenter  = vec(self.LeftCenterX, self.LeftCenterY)
        self.RightCenter = vec(self.RightCenterX, self.RightCenterY)

    def hotShoe(self):
        w = self.HotShoeWidth
        l = self.HotShoeLength
        h = self.HotShoeBaseHeight + self.HotShoeSpaceHeight + self.HotShoePlateHeight + self.HotShoePlateHeightAbove

        cube = Part.makeBox( w, l, h).translate( vec(-w / 2, -l / 2) )

        ww = self.HotShoeInnerWidth 
        ll = self.HotShoePlateLength
        hh = self.HotShoeSpaceHeight + self.HotShoePlateHeight + self.HotShoePlateHeightAbove 

        cube2 = Part.makeBox( ww, ll, hh).translate( vec(-ww  / 2, - l / 2, h - hh))
        cube = cube.cut(cube2).removeSplitter()

        edges = cube.Edges


        www = self.HotShoePlateWidth
        lll = self.HotShoePlateLength
        hhh = self.HotShoePlateHeight
        cube3 = Part.makeBox( www, lll, hhh).translate( vec( -www  / 2, - l / 2, h - self.HotShoePlateHeight - self.HotShoePlateHeightAbove))

        locLine = self.locLineProtrusion()
        locLine.applyRotation( FreeCAD.Rotation( vec(1,0,0), 180 ))

        cube = cube.makeFillet(
            2, [ e for e in edges if e.BoundBox.ZLength >= h ]).makeFillet(
            0.5, [ e for e in edges if e.BoundBox.ZLength < h ]).fuse(locLine).cut(cube3).cut( Part.makeCylinder(self.BoltDia / 2, h) ).cut( 
            self.nutPocket(h).translate( vec( 0, 0, self.HotShoeBaseHeight - self.NutHeight) )
        )
        return cube

    def locLineProtrusion(self):
        cyl = Part.makeCylinder(self.LocLineDiaIn / 2 , self.LocLineHeight).cut(
            Part.makeCylinder( self.LocLineDiaInIn / 2 , self.LocLineHeight)
        )
        for angle in range(0, 180, 60):
            cyl = cyl.cut(
                Util.place(
                    Part.makeBox( self.LocLineDia, self.LocLineSpacer, self.LocLineHeight ),
                    FreeCAD.Placement( 
                        vec( - self.LocLineDia / 2, - self.LocLineSpacer / 2, 0), 
                        FreeCAD.Rotation(angle,0,0), 
                        vec(  self.LocLineDia / 2, self.LocLineSpacer / 2, 0)
                    )
                )
            )
        return cyl

    def nutPocket(self, height = 0):
        if height == 0:
            height = self.NutHeight
        poly = Part.makePolygon([
            FreeCAD.Rotation(vec(0,0,1), angle + 90).multVec( vec(self.NutDia / 2 ) )
              for angle in range(0, 370, 60)
        ])
        f = Part.Face( Part.Wire(poly) ).extrude( vec(0,0, height) ).removeSplitter()
        f = f.makeFillet(
            0.1,
            [ e for e in f.Edges if e.BoundBox.ZLength >= self.NutHeight ]
        )
        return f

    def adapterHolder(self):
        w = self.AdapterWidth + self.AdapterHolderThickness * 2
        holder = Part.makeBox(w, self.AdapterLength, self.BracketThickness ).translate( vec( self.AdapterCenterX - w / 2, 0, -self.BracketThickness ))
        return holder

    def adapterHolderPocket(self):
        ww = self.AdapterWidth

        pocket = Part.makeBox( ww, self.AdapterLength, self.AdapterHeight).translate( 
                vec( self.AdapterCenterX - ww/2, 0, - self.AdapterHeight ) )
        return pocket



    def umbrellaHolder(self):
        MinThickness = 2.5
        BottomThickness = 5 
        Height       = 80
        ShaftDiameter = 11
        outer = Part.makeCylinder(ShaftDiameter / 2 + MinThickness, Height)
        inner = Util.move( Part.makeCylinder(ShaftDiameter / 2, Height), z=BottomThickness)
        total = outer.cut(inner)
        newshape = total.makeFillet(0.5, total.Edges)

        Part.show(newshape, "Koko")

        i = 0
        for edge in total.Edges:
            Part.show(edge, "koko-%02d" % i)
            i = i + 1

        return newshape


    def xpriruba(self, r1, r2, ws, h):
        spacer = lambda angle: Util.place( Part.makeBox( 2 * r1, 2 * ws, h ), FreeCAD.Placement( vec( -r1, - ws, 0), FreeCAD.Rotation(angle,0,0), vec(r1,ws,0) ))
        cout = Part.makeCylinder( r1, h)
        cin  = Part.makeCylinder( r2, h)
        return cout.cut(cin.multiFuse([spacer(60), spacer(120), spacer(0) ]))

    def curvePoint(self, c, n):
        fp = c.FirstParameter
        lp = c.LastParameter
        step  = (lp - fp) / n
        return lambda i : c.value(fp + i * step )

    def circleArcs(self, c1, c2, r, R1, R2):
        vc        = c2 - c1
        pc        = (c2 + c1) * 0.5
        vcp       = vec(vc.y, -vc.x).normalize()
        d         = vc.Length / 2
        yR1, yR2 = [ math.sqrt(  (R - r)**2 - d**2 ) for R in [R1,R2] ]
        C1       = pc.add( vcp * yR1 )
        C2       = pc.add( vcp * (-yR2) )

        circlePoint = lambda c,p,r: c.add(c.sub(p).normalize().multiply(r))

        pts = [
         circlePoint(c1, C1, r),
         circlePoint(C1, pc, -R1),
         circlePoint(c2, C1, r),
         circlePoint(c2, pc, r),
         circlePoint(c2, C2, r),
         circlePoint(C2, pc, -R2),
         circlePoint(c1,C2,r),
         circlePoint(c1, pc, r)
        ] 
        pts.append(pts[0])

        return [ Part.ArcOfCircle(pts[i],pts[i+1],pts[i+2]) for i in range(0, 8, 2) ]

    def pestik3(self):
        p0 = vec(0,-17)
        c  = vec(40)
        r  = 8
        p1 = Util.tangentPoint(p0, c, r, 1)
        p2 = Util.tangentPoint(p0, c, r, -1)

        #Part.show( Part.makeLine(p0, p1) )
        #Part.show( Part.makeLine(p2, p0) )
        Part.show(Util.move(
            Part.makeCircle(r),
            c.x, c.y
        ))
        return Part.Shape([
            Part.LineSegment(p0, p1),
            Part.ArcOfCircle(
                p1,
                c + ( (c - p0).normalize() * r ),
                p2
            ),
            Part.LineSegment(p2, p0)
        ])

    def thickLine(self, p1, p2, width):
        nv = (p2 - p1).normalize().cross( vec(z = 1) ) * (width / 2 )
        print("NV: ", nv )
        poly = Part.makePolygon( [ p1 + nv, p2 + nv, p2 - nv, p1 - nv, p1 + nv ] )
        return Part.Face( Part.Wire(poly) )


    def build(self):
        r = self.SupportDia / 2
        h = self.BracketThickness

        xr, xl = [ self.AdapterCenterX + i * (self.AdapterWidth / 2 + self.AdapterHolderThickness) for i in [1, -1] ]
        R1, R2 = [ vec(xr, y) for y in [-self.AdapterThicknessFront,self.AdapterLength] ]
        L1, L2 = [ vec(xl, y) for y in [-self.AdapterThicknessFront,self.AdapterLength] ]

        pts = [
            R1,
            Util.tangentPoint(R1, self.RightCenter, r, 1),
            Util.tangentPoint(R2, self.RightCenter, r, -1),
            R2,
            L2,
            Util.tangentPoint(L2, self.LeftCenter, r, 1),
            Util.tangentPoint(L1, self.LeftCenter, r, -1),
            L1,
            R1
        ]

        face = Part.Face(Part.Wire(Part.makePolygon(pts))) 

        for bpts in [ pts[0:4] + pts[0:1], pts[7:3:-1] + pts[7:8] ]:
            n = 4 
            cp1 = self.curvePoint( Part.LineSegment( bpts[0], bpts[1] ), n )
            cp2 = self.curvePoint( Part.LineSegment( bpts[3], bpts[2] ), n )
        # zigzag = Part.Face(Part.Wire(Part.makePolygon([ (cp2 if i % 2 == 0 else cp1)(i) for i in range(1, n) ]).makeOffset2D(self.BraceWidth / 2) ))
            zigzag = self.thickLine( cp1(2), cp2(2), self.BraceWidth )
            facecut = Part.Face(Part.Wire(Part.makePolygon(bpts))).makeOffset2D(-self.BraceWidth).cut(zigzag)
            face = face.cut( facecut)

        # cut the inner parts of the arms
        # face = face.cut(faceLeft.makeOffset2D(-self.BraceWidth).cut(zigzag) ).cut(faceRight.makeOffset2D(-self.BraceWidth))

        body = face.extrude(vec(z=-h)).removeSplitter()

        edges = []
        for e in body.Edges:
            bb = e.BoundBox
            if bb.ZLength >= h / 2 and not([ p for p in [ pts[i] for i in [1,2,5,6] ] if bb.isInside( p ) ]):
                edges.append( e )
            # [ e for e in body.Edges if e.BoundBox.ZLength >= h / 2 and e.BoundBox.YMax >= -self.AdapterThicknessFront and e.BoundBox.YMax <= self.AdapterLength 

        body = body.makeFillet( 3,  edges )

        # horizontal edges
        body = body.makeFillet(
            2,
            [  e for e in body.Edges if e.BoundBox.ZLength < 0.5 ]
        )

        pocket = Part.makeBox(self.AdapterWidth, self.AdapterLength, self.AdapterHeight).translate( 
            vec(self.AdapterCenterX - self.AdapterWidth /2, 0, -self.AdapterHeight ) 
        )

        hole = Part.makeCylinder(self.BoltDia / 2, h ).translate( vec( self.AdapterCenterX, self.AdapterCenterY, -h))

        body = self.addBracketHolders( body.cut(pocket).cut(hole))
        return body 


    def addBracketHolders(self,body):
        r  = self.SupportDia / 2
        h    = self.BracketThickness
        for p in [ self.RightCenter, self.LeftCenter ]:
            body = body.fuse( 
                Part.makeCylinder(r, h).translate( p.add(vec(z=-h)))
            ).fuse(
                self.locLineProtrusion().translate(p)
            ).cut(
                self.nutPocket().translate( p.add(vec(z=-h)))
            ).cut(
                Part.makeCylinder(self.BoltDia / 2, h).translate(p.add(vec(z=-h)))
            )
        return body
        

    def OLD_build(self):

        # center of the hole
        CenterX     = 35
        CenterY     = - 35

        # radius of hole
        HoleRadius  = 3 

        # radius of the support
        Radius  = 12.5
        # priruba 21.6 (trosku mensi)
        PrirubaRadius1 = 21 / 2
        # priruba 11.6 (trosku vetsi)
        PrirubaRadius2 = 12.2 / 2
        # priuba 1.6 mm (trosku vetsi)
        PrirubaSpacer = 2
        PrirubaHeight = 2

        AdapterHeight = 7.5 
        FrontHoleHeight = 1.5

        # width 11.8 (trosku vetsi)
        AdapterWidth = 12.1
        AdapterLength = 48.7 
        AdapterFrontHeight = 12.5
        AdapterCenterY = 25

        Thickness1 = 6
        AdapterThicknessSide = 4 
        ThicknessUnderBolt = 3
        AdapterThicknessBottom = 4 
        AdapterThicknessFront =  4 
        Angle1 = pi / 4 
        Angle2 = pi + pi / 6

        # point at radius
        pr = lambda ang: vec( CenterX + Radius * cos(ang), CenterY + Radius * sin(ang))

        pta1 = pr(Angle1)
        pta2 = pr(Angle2)

        height = AdapterHeight + AdapterThicknessBottom

        # 
        x_center = - (AdapterThicknessSide + AdapterWidth / 2)

        p0 = vec(0, -AdapterThicknessFront)

        elems = [
            Util.bez([ p0,  p0.add(vec(1,0).multiply(5)), 
                pta2.add(vec(sin(Angle2), -cos(Angle2)).multiply(10)), 
                pta2
            ]),
            Part.Arc( pta2, pr( (Angle1 + Angle2) / 2 - pi ), pta1),
            Util.bez([
                pta1,
                pta1.add( vec(-sin(Angle1), cos(Angle1)).multiply(10) ), 
                vec(0, AdapterLength /2),  
                vec(0, AdapterLength)
            ])
        ]

        w = Util.wire(
            elems + Util.polyline([
                vec( 0, AdapterLength),
                vec(-(2*AdapterThicknessSide+AdapterWidth), AdapterLength),
                vec(-(2*AdapterThicknessSide+AdapterWidth), -AdapterThicknessFront),
                p0
            ]))

        w_cut = Util.wire(
            elems + Util.polyline([
                vec( 0, AdapterLength),
                vec(-AdapterThicknessSide, AdapterLength),
                vec(-AdapterThicknessSide, -AdapterThicknessFront),
                p0
            ])
        ).makeOffset2D(-Thickness1)

        # horizontal (along y axis) hole in the adapter
        #hole_adapter2 = Part.Face(Part.Wire( Part.makeCircle( HoleRadius, vec(x_center, 0, -AdapterHeight + FrontHoleHeight + HoleRadius), vec(0,1,0)).Edges )).extrude(
        #    vec(0, -AdapterThicknessFront )
        #)

        p1 = vec(0, 0, height - ThicknessUnderBolt)
        p2 = vec(Radius - ThicknessUnderBolt, 0, height - ThicknessUnderBolt)
        p3 = vec(Radius - ThicknessUnderBolt, 0, 0) 
        p0 = vec(0, 0)

        bracket_depression = Util.move(
            Part.Face(Util.wire([Util.bez([p1, p2, p3])] + Util.polyline([p3,p0,p1]))).revolve(
                vec(0,0,0),
                vec(0,0,1),
                360),
            x=CenterX, y=CenterY, z=-height
        )

        total = Util.fuse(
            [
                Part.Face(w).cut(Part.Face(w_cut)).extrude(vec(0, 0, -height)),
                Util.move(
                    Part.makeCylinder(Radius, height),
                    x=CenterX, y=CenterY, z=-height
                ),
                Util.move(self.priruba(PrirubaRadius1, PrirubaRadius2, PrirubaSpacer, PrirubaHeight), x=CenterX, y=CenterY),
                Util.move(
                    Part.makeBox(AdapterWidth + 2*AdapterThicknessSide, AdapterThicknessFront, AdapterFrontHeight - AdapterHeight),
                    x = -AdapterWidth - 2*AdapterThicknessSide, y=-AdapterThicknessFront
                )
            ]
        ).cut(Util.fuse(
            [ 
                Util.move(
                    Part.makeBox(AdapterWidth, AdapterLength, AdapterHeight),
                    x=-(AdapterThicknessSide + AdapterWidth),
                    z=-AdapterHeight
                ),
                # hole in the adapter bottom
                Util.move(
                    Part.makeCylinder(HoleRadius,height),
                    x=x_center, y=AdapterCenterY, z=-height
                ),
                # hole_adapter2, 
                Util.place(
                    Part.makeCylinder(HoleRadius,height),
                    FreeCAD.Placement(
                        vec(x_center, 0, -AdapterHeight+FrontHoleHeight+HoleRadius),
                        FreeCAD.Rotation(0,0,90),
                        vec()
                    )
                ),
                bracket_depression,
                # hole in the handle
                Util.move( Part.makeCylinder(HoleRadius, height), x=CenterX, y=CenterY, z=-height)
            ])
            )

        return total
        newshape = total.makeFillet(0.5, total.Edges)
        return newshape
        # o = Part.show(newshape)
        return o


NAME = "bracket"

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

if True:
    bracket = Bracket()
    hs = bracket.hotShoe()
    bkt = bracket.build()

    Part.show( hs.copy().translate(vec(-50, 0, 50)) )
    Part.show( bkt )
    Part.show( hs.copy().translate(vec(50, 0, 50)) )

    bktLow = Bracket()
    bktLow.NutHeight = 3
    bktLow.HotShoeBaseHeight = 15 - 9.7
    hsLow = bktLow.hotShoe()

    Part.show( hsLow.copy().translate(vec(-100, 0, 50)) )
    Part.show( hsLow.copy().translate(vec(100, 0, 50)) )

    Util.writeMesh(bkt, "bracket-1ks.stl")
    Util.writeMesh(hs,  "hotshoe-2ks.stl")
    Util.writeMesh(hsLow,  "hotshoe-low-2ks.stl")

if False:
    uholder = UmbrellHolder()
    uh = uholder.build()
    Part.show(uh)
    Util.writeMesh(uh, "umbrella-holder-1ks.stl")

if False:
    fltr = FilterThread()
    shp = fltr.build()
    Part.show(shp)
    # Util.writeMesh(uh, "umbrella-holder-1ks.stl")




doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

# doc.saveAs( os.path.join(os.path.dirname(__file__), "bracket.FCStd")) 
doc.FileName = os.path.join(os.path.dirname(__file__), "bracket.FCStd")
Gui.SendMsgToActiveView("Save")
doc.save()




#### shape = bracket.build()
###shape = bracket.umbrellaHolder()
###
###mesh = MeshPart.meshFromShape(Shape = shape, LinearDeflection=0.03, AngularDeflection=0.174533, Relative=False)
###meshobj = doc.addObject("Mesh::Feature")
###meshobj.Mesh = mesh
###doc.recompute()
###
###Gui.SendMsgToActiveView("ViewFit")
###Gui.activeDocument().activeView().viewIsometric()
###doc.recompute()
###mesh.write(os.path.join(os.path.dirname(__file__), "fff.stl"))
# doc.saveAs( os.path.join(os.path.dirname(__file__), "desticka.stl"))


