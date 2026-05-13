import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan
from Diffutil import vec, angleVec, between, recPoints, ortoRecFace, X, Y, Z, O, symX, halfSpace
import Locline 
import traceback
import functools
import Trans
import copy
from Lines import Lines

def extrudeFront(shp):
    deep = 600
    return shp.extrude(vec(0,deep)).translate(vec(0,-deep/2))

class Cone:
    def __init__(self, type="regular"):
        self.SmoothCut   = False
        self.ReflectionDeskDepth = 65  
        self.FlashWidth, self.FlashDepth = [12.5, 17 + 26]
        self.AxisAngle = 0
        self.LensOuter = 13 

        # how much is the diffuser shifted up alongside reflection desk
        self.ShiftUp = 0 
        self.ConeThickness = 6
        self.HeightRatio = 0.85
        self.ReflectionDeskThickness = 4

        self.ReflectionDeskWidth = 150
#         self.ReflectionDeskHeight = 90
        self.ReflectionDeskDepth = 70
        self.ReflectionDeskCutMargin = 8

        # unused
        #self.DentSegments      = [ [-17,20], [0, 40], [197,20] ]
        self.DentSegments      = [ [0, 50], [100, 45], [-100, 45] ]


        # support around reflectionDesk
        self.FlapDepth = 5
        self.FlapWidth = 15
        self.FlapShift = 10
        self.FlapTolerance = 1.6
        self.FlapShiftVerical = 8 
        self.FlapThickness = 1.3

        self.UseTopArch = False

        # regular used for 30mm and 60mm
        if type == "30":
            self.Depth    = 140
            self.LensDia  = 52 
            self.Angle    = 75 
        if type == "12":
            self.Depth    = 140
            self.LensDia  = 65

            # slightly bigger
            self.LensDia = 68

            self.Angle    = 95 
        if type == "regular":
            self.Depth    = 140
            self.LensDia  = 50.8
            self.Angle    = 60

        if type == "30s":
            self.LensDia  = 58 
            self.LensDia  = 61 
            self.Angle    = 60 
            self.Depth    = 155
            self.ReflectionDeskDepth = 55
            self.FlashDepth = 17 + 15 
            self.LensOuter  = 5
            self.ShiftUp = 3
            self.ReflectionDeskWidth = 132
            self.DentSegments      = [ [0, 50], [105, 55], [-105, 55] ]

        if type == "9_17":
            self.Depth    = 125
            self.LensDia  = 72 
            self.Angle    = 100 
            self.Depth    = 135
            self.DentSegments      = [ [0, 50], [115, 55], [-115, 55] ]

        if type == "9_17e":
            self.LensDia  = 70 
            self.Angle    = 110 
            self.Depth    = 125

        if type == "9_17big" or type == "9_17small":
            self.LensDia  = 70 
            self.Angle    = 95 
            self.Depth    = 125
            # self.Angle    = 90 
            self.AxisAngle = 10 
            self.ShiftUp   = 0 
            self.HeightRatio = 0.7
            self.HeightRatio = 0.8
            self.LensOuter = 10 
            self.DentSegments      = [ [0, 50], [115, 55], [-115, 55] ]
            self.UseTopArch = True
            
            self.LensDia = 72 if type == "9_17small" else 80
            self.ReflectionDeskWidth = 142 if type =="9_17small" else 152

        # Laowa having 110 degrees viewing angle
        if type == "laowa":
            self.Angle = 110 
            self.LensDia = 50.5
            self.Depth = 120


        self.DentDepth = 12
        self.DentDepth = 12 
        self.ReflectionDeskFoldAngle = 45
        self.ReflectionDeskHeight   = 56

        self.ReflectionDeskDown = self.LensDia / 2 + 40
        self.ReflectionDeskDownSolid = self.LensDia / 2 + 13
        self.ReflectionDeskDownFold = self.LensDia / 2 - 15
        # self.ReflectionDeskWidth = self.LensDia + 90

    def Width(self):
        return self.LensDia + 2*tan(self.Angle/2 * pi / 180) *self.Depth

    def Height(self):
        return self.Width() * self.HeightRatio

    def frontRim(self, t=0):
        k = 1.5
        e = Part.Ellipse( k*vec(x=self.Width()/2 + t), k*vec(z=self.Height()/2 + t), O).toShape()
        e.translate(k*vec(y=self.Depth ))
        return e

    def backRim(self, t=0):
        # around lens
        r = self.LensDia / 2 + self.LensOuter

        # almost small tip of the cone
        rtip = 10
        ro = self.Height() / 2 
        dtip = self.Depth / (ro - r) * (r - rtip)
        e = Part.Ellipse( vec(x=rtip+t), vec(z=rtip+t), O ).toShape() 
        e.translate(vec(y=-dtip))
        return e

    def makeCone(self, t=0, solid=False):
        # around lens
        cone = Part.makeLoft([self.backRim(t), self.frontRim(t) ], solid=solid).removeSplitter()
        cone.rotate( vec(0,0,self.LensDia/2+self.LensOuter), X, self.AxisAngle )
        return cone

    def makeSolidCone(self, thickness=None):
        if thickness == None:
            thickness = self.ConeThickness
        return self.makeCone(thickness/2, True).cut( self.makeCone(-thickness/2, True))


    def cutStraight(self):
        # lomena cara cutting the bottom of the cone
        z1 = -10 
        y1 = 20

        r = self.LensDia / 2

        p1 = vec(0, y1,  -r + z1)
        p2 = vec(0, self.Depth, -r + z1 + 3 )
        p3 = vec(0, self.Depth, self.Height() / 2 )

        # more cut (not so much one top)
        # k1, k2, k3, k4 = [ 0.25, 0.5, 0.65, 0.5 ]

        # less cut
        k1, k2, k3, k4 = [ 0.4, 0.33, 0.5, 0.7 ]

        poly = Part.makePolygon([
            p1,
            between(p1,p2, k1),
            between( between(p1,p2, k1), between(p2,p3,k2), k4),
            between( p2, p3, k3),
            vec(0, self.Depth + 1, -self.Height() ),
            vec(0, y1, -self.Height() ),
            vec(0,y1,-r + z1) 
        ])

        big = 800
        return Part.Face( poly ).translate(X*-big/2).extrude(X*big)

    def cutSmoothPts(self):
        r = self.LensDia / 2
        d = self.Depth
        h = self.Height() / 2
        return [ vec(0,y,z) for y,z in [ 
            [0, 0], [0, -0.4*r], [0, -0.8*r], [0.6*r, -1.1*r], [0.4*d, -0.7*r], [0.68*d, -0.38*r], [d+1, 0.35*h], [d+1, 0.5*h], [d+1, 0.75*h], [d+1, h + 1] ] 
        ]

    def cutSmooth(self):
        r = self.LensDia / 2
        d = self.Depth
        h = self.Height() / 2

        # bezier spline
        bezPts = self.cutSmoothPts()
        bez = Part.BSplineCurve(bezPts)

        poly = Part.makePolygon([ bezPts[-1], bezPts[-1] + vec(0,5,0), vec(0,d,-h - 1), vec(0,0,-h-1), bezPts[0] ])
        parts = [ Part.Shape([bez]), poly ]
        big = 500
        shp = Part.Face(Part.Wire(parts))
        shp = shp.translate(vec(-big/2)).extrude(vec(big))
        return shp

    def dentSegment(self, angle, width, shft=None ):
        d, h = [60,  400 ]

        if shft is None:
            shft = -width/2

        box = Part.makeBox(width, d, h).translate(shft*X-d/2*Y)
        box.rotate(O,Y,angle) 
        return box

    def makeDentSegments(self):
        return [ self.dentSegment(a,w) for a, w in self.DentSegments ]

    # half space before reflectionDesk
    def reflectionDeskFrontHs(self):
        # flat
        # return halfSpace(y=1)

        # big enough
        w = 400

        a = self.ReflectionDeskFoldAngle * pi / 180 
        ys  = (self.ReflectionDeskDown - self.ReflectionDeskDownFold) * cos(a)/sin(a)

        desk = ortoRecFace( vec(-w, 0, -self.ReflectionDeskDownFold), vec(w,0,w ) )

        # folded part of the desk at the bottom
        pts = [ vec( w * x, ys * (1-z)/2, -self.ReflectionDeskDown * (1-z)/2 - self.ReflectionDeskDownFold * (1+z)/2) for x,z in recPoints() ]
        desk2 = Part.Face(Part.makePolygon(pts))

        return desk.fuse(desk2).extrude(vec(0,300))

    def reflectionDeskTopFold(self, left):
        w = 3 
        t = 1
        p0 = vec((-1 if left else 1) * (self.ReflectionDeskWidth - w)/2, 0, self.ReflectionDeskHeight)
        return ortoRecFace(*[p0-k/2*vec(w,0,t) for k in [-1,1]])

    def reflectionDeskBottomFold(self, left):
        w = 3 
        t = 1
        p0 = vec((-1 if left else 1) * (self.ReflectionDeskWidth - w)/2, 0, -self.ReflectionDeskDownFold)
        return ortoRecFace(*[p0-k/2*vec(w,0,t) for k in [-1,1]])
        # return ortoRecFace(*[ vec(k * self.LensDia/2, 0, k * 0.5 + (-self.ReflectionDeskDownFold)) for k in [-1,1] ])

    def reflectionDeskProfile(self, forSolid=False):
        # shape is cut by the front by bspline curve
        x1 = X * -self.ReflectionDeskWidth/2
        x2 = X*-(self.FlashWidth/2 + 20 )

        z1 = Z*(self.ReflectionDeskDepth + self.FlashDepth + self.ReflectionDeskHeight)
        z2 = Z*(self.ReflectionDeskHeight)
        z22 = z2+25*Z
        z3 = -Z*self.ReflectionDeskDownFold
        z4 = -Z*( self.ReflectionDeskDownSolid if forSolid else self.ReflectionDeskDown)

        arcs = Lines()
        arcs.add(z1, z1+x2+5*X)
        arcs.add(x2+z1, x2+z1-10*Z,x2+between(z1,z22, 0.65), x1+z22+5*Z, x1+z22)
        arcs.add(x1+z2)
        arcs.add(x1+z4+20*Z)
        arcs.add(x1+z4, x1+20*X+z4)
        arcs.add(z4)

        arcs = arcs + arcs.rev(symX)

        profile = Part.Face(Part.Wire([ Part.BSplineCurve(arc).toShape() for arc in arcs]) )
        return profile

    def reflectionDeskProfileTop(self):
        profile = self.reflectionDeskProfile()
        flashCut = ortoRecFace(
           vec(- self.FlashWidth/2, 0, self.ReflectionDeskHeight + self.ReflectionDeskDepth),
           vec(self.FlashWidth/2,   0, self.ReflectionDeskHeight + self.ReflectionDeskDepth + self.FlashDepth))
        profile = profile.cut(flashCut)
        profile = profile.translate(-Z*self.ReflectionDeskHeight).common(halfSpace(z=1))
        profile.rotate(O,X,90)

        w2 = X*self.ReflectionDeskWidth/2
        profile = profile.fuse(ortoRecFace(-w2,w2+100*Y))
        return profile


    def reflectionDeskProfileFront(self):
        b = 800
        box = ortoRecFace( vec(-b,0,-b), vec(b,0,self.ReflectionDeskHeight) )
        profile = self.reflectionDeskProfile(True).common(box)
        # profile is Shell, why? I need a Face
        return profile.Faces[0]

    def reflectionDeskCuts(self):
        # stacking operations to be later applied independently on both desks
        op = Trans.Trans()
        
        hc = 100
        op += Trans.cut( Part.makeCylinder(self.LensDia / 2, hc, Y*(-hc/2), Y))

        # thin cuts marking the folds
        for fold in [ self.reflectionDeskTopFold(True), self.reflectionDeskTopFold(False), self.reflectionDeskBottomFold(True), self.reflectionDeskBottomFold(False) ]:
            op += Trans.cut(fold)

        def addSegment(angle,width,thickness=None,shft=None):
            if thickness is None:
                thickness = self.ConeThickness
            thickCone = self.makeSolidCone(thickness)
            thickCone.translate(vec(0, 0, self.ShiftUp))
            seg = self.dentSegment(angle,width,shft).translate(vec(0, 0, self.ShiftUp))
            return Trans.cut(thickCone.common(seg))

        # cutting the segments
        for segment in self.steppedDentSegments():
            op += addSegment(*segment)

        big = 400
        op += Trans.common(self.reflectionDeskProfile().extrude(Y*big).translate(-big/2*Y))
        return op

    def steppedDentSegments(self):
        top, left, right = self.DentSegments
    
        la, lw = left
        ra, rw = right

        return [ 
            top, 
            [la, 0.6*lw, self.ConeThickness, -0.5*lw], 
            [la, 0.2*lw, 2/3*self.ConeThickness, 0.1*lw], 
            [la, 0.2*lw, 0.4*self.ConeThickness, 0.3*lw], 

            [ra, 0.2*rw, 0.4*self.ConeThickness, -0.5*rw], 
            [ra, 0.2*rw, 2/3*self.ConeThickness, -0.3*rw],
            [ra, 0.6*rw, self.ConeThickness, -0.1*rw]
        ]

    def foldDepth(self):
        return (self.ReflectionDeskDown-self.ReflectionDeskDownFold)*math.tan(self.ReflectionDeskFoldAngle*math.pi/180)

    def reflectionDesk(self):
        h = Z * self.ReflectionDeskHeight
        lines = Lines()
        lines.addBroken(
            h - Y*(self.ReflectionDeskDepth+self.FlashDepth),
            h,
            -Z*self.ReflectionDeskDownFold,
            -Z*self.ReflectionDeskDown + Y*self.foldDepth())
            # -Z*self.ReflectionDeskDown 

        front = lines.wire().translate(-200*X).extrude(400*X)
        front = front.common( self.reflectionDeskProfileTop().translate(-200*Z).extrude(400*Z))
        front = front.common( self.reflectionDeskProfile().translate(-200*Y).extrude(400*Y))
        if self.UseTopArch:
            # adding arch
            front = front.fuse(self.reflectionDeskTopArch())
            front = front.cut(self.reflectionDeskTopArch().rotate(Z*self.ReflectionDeskHeight,X,90))

        op = self.reflectionDeskCuts()
        front = op(front)

        for sup in self.reflectionDeskSupports():
            front = front.fuse(sup)
        return front

    def reflectionDeskTopArch(self):
        h = 20
        s = 8
        x0 = X * (self.ReflectionDeskWidth / 2 - 35)
        arcs = Lines()
        arcs.add(O,x0 + s*X )
        arcs.add(x0, x0+h*Z, h*Z)
        arcs += arcs.rev(symX)
        arcs = arcs.rev()
        return Part.Face(arcs.wire()).translate(Z*self.ReflectionDeskHeight)

    def reflectionDeskSupports(self):
        def flap():
            f = ortoRecFace(O, X*self.FlapDepth + Z*self.FlapWidth).translate(X*self.ReflectionDeskWidth/2)
            f.reverse()
            return f

        left = Trans.rotate(O,Z,180)  + Trans.reverse

        f1 = Trans.translate(Z*(-self.ReflectionDeskDownFold+self.FlapShift))

        f2 = Trans.translate(Z*(self.ReflectionDeskHeight-self.FlapShift-self.FlapWidth))

        f3 = Trans.rotate(O,X, 90) + Trans.translate(Z*self.ReflectionDeskHeight -Y*self.FlapShift)

        f4 = Trans.translate(-Z*(self.FlapShift+self.FlapWidth)) + Trans.rotate(O, X, self.ReflectionDeskFoldAngle) + Trans.translate(Z*-self.ReflectionDeskDownFold)

        return [ op(flap()) 
            for op in [ f1, left+f1, f2, left+f2, f3, left+f3, f4, left+f4 ]
        ]

    def supportTrianglesAtPlace(self):
        op = Trans.rotate(O,-X,90)+Trans.rotate(O,Z,90)
        op += Trans.translate(X*self.ReflectionDeskWidth/2+Z*self.ReflectionDeskHeight)
        # op += Trans.translate((Z+Y)*(self.FlapShiftVerical + self.FlapThickness / 2))
        t = self.supportTriangle(False)
        return op(t)

    def supportTriangle(self, bottom=False):
        angle = self.ReflectionDeskFoldAngle if bottom else 90
        def along(p1,p2,l):
            return p1+l*(p2-p1).normalize()

        def hole(angled):
            c = X * (self.FlapShift + self.FlapWidth/2)
            corner = X*(self.FlapWidth/2 + self.FlapTolerance) + Y*self.FlapThickness / 2
            if not angled:
                c = -c
            f = ortoRecFace(c-corner,c+corner)
            if angled:
                f = f.rotate(O,Z,angle)
            return f

        w = self.FlapWidth + 2 * self.FlapShift + self.FlapShiftVerical

        h = 2 * self.FlapShiftVerical 
        r = 2

        p0 = angleVec(angle/2-90)
        p0 = - p0 * (self.FlapShiftVerical / p0.y)
        p1 = p0+w*angleVec(angle)
        p4 = p0-w*X 
        v = (p1-p0).cross(-Z).normalize()
        p2 = p1 + h * v 
        p3 = p4 + h*Y
        l = Lines()

        l.add( along(p0,p4,r), p0, along(p0,p1,r))
        l.add( along(p1,p0,r) )
        l.add( p1, along(p1,p2,r) )
        l.add( along(p2,p1,r) )
        l.add( p2, along(p2,p3,r) )
        l.add( along(p3,p2,r) )
        l.add( p3, along(p3,p4,r) )
        l.add( along(p4,p3,r) )
        l.add( p4, along(p4,p0,r))
        l.add( along(p0,p4,r) )

        # hole
        f = Part.Face(l.wire())
        f = f.cut(hole(False)).cut(hole(True))
        return f


    def lensProfile(self):
        c = Part.makeCircle(self.LensDia / 2)
        f = Part.Face(Part.Wire([ c ]))
        f.rotate(O,X,90)
        return f

    # front thick part of the reflection desk
    def reflectionDeskSolid(self, t=None):
        if t is None:
            t=self.ReflectionDeskThickness

        big = 400
        desk = Part.makeBox(big, t, big)
        desk2 = Part.makeBox(big, t, big)
        desk2 = desk2.translate(vec(0,0, -big))
        desk2.rotate(O, X, self.ReflectionDeskFoldAngle)
        desk = desk.fuse(desk2)
        desk.translate( vec(-big/2,0,-self.ReflectionDeskDownFold) )

        margin = self.ReflectionDeskCutMargin

        profile = self.reflectionDeskProfileFront()
        cone    = self.makeSolidCone(self.ConeThickness)

        cutter = extrudeFront(profile.makeOffset2D(-margin))
        for seg in self.makeDentSegments():
            cutter = cutter.cut( cone.common(seg).makeOffsetShape(margin, 0.1)  )

        cutter = cutter.cut( extrudeFront(self.lensProfile().makeOffset2D(margin)))

        # traverse
        b = 400
        cutter = cutter.cut( Part.makeBox(b,b,margin).translate( vec(-b/2,-b/2, -self.ReflectionDeskDownFold+margin/2)))
        cutter = cutter.cut( Part.makeBox(margin,b,b).translate( vec(-margin/2,-b/2,-b/2)))
        desk = desk.cut(cutter )

        # cutting the holes
        for seg in self.makeDentSegments():
            desk = desk.cut( cone.common(seg)  )

        desk = desk.cut( extrudeFront(self.lensProfile()) )

        # cutting outer shape
        desk = desk.common( extrudeFront(profile) )

        # locline mount
        mount = Locline.Mount()
        for left in [ True, False ]:
            m = self.locLineMount(mount, left)
            m.translate( vec(
                -self.ReflectionDeskWidth/2 if left else self.ReflectionDeskWidth/2-mount.LocLineDia,
                -(mount.LocLineDia - self.ReflectionDeskThickness),
                self.ReflectionDeskHeight
                ))
            desk = desk.fuse(m)

        return desk

    def locLineMount(self, mount, left=True):
        l = mount.LocLineDia

        k   = 0.2
        kk  = 0.5*k
        kkk = 1.5*k
        arcs = [
            [ O, X ],
            [ X, vec(1, 0, -kk) ],
            [ vec(1,0,-kk), vec(1,0,-k), vec(1-kk,0,-k), vec(kkk,0,-kkk), vec(k,0,kk-1), vec(k,0,-1), vec(kk,0,-1)  ],
            [ vec(kk,0,-1), vec(0,0,-1) ],
            [ vec(0,0,-1), O ]
        ]

        def prof():
            sh = O if left else vec(0.5)
            c = Part.Face(Part.Wire(Part.makeCircle(l*0.5))).translate(l*vec(0.5,0.5))
            c = c.fuse( ortoRecFace(l*vec(0,0.5), l*vec(1,1)))
            # c = c.fuse( ortoRecFace(O, l*vec(1,0.5) ))
            c = c.fuse( ortoRecFace(l*sh,l*(sh+ vec(0.5,1))) )
            return c

        def mirror(p):
            return p if left else vec(l-p.x,p.y,p.z)

        # front profile
        front = Part.Face(Part.Wire([ Part.BSplineCurve([ mirror(l*p) for p in arc]).toShape() for arc in arcs ]))

        # top profile
        top = prof()
        if left:
            side = prof().rotate(O,Y,90)
        else:
            side = prof().translate(vec(-l)).rotate(O,Y,-90)

        box = front.extrude(vec(0,l)).common(top.extrude(vec(0,0,-l))).common(side.extrude(vec(l)))

        for p in [ 
                # top protrusion
                mount.locLineProtrusion().translate(l * vec(0.5,0.5) ), 
                # left / right protrusion
                mount.locLineProtrusion().rotate(O,Y, (-90 if left else 90)).translate(l*vec((0 if left else 1),0.5,-0.5)) 
                ]:
            box = box.fuse(p)

        t = 3
        for p in [
            mount.boredHole(l).translate(l*vec(0.5,0.5,-1)),
            mount.boredHole(l).rotate(O,Y,90).translate(l*vec(0,0.5,-0.5)),
            mount.smallNutPocket(l).translate(l*vec(0.5,0.5,-1) + Z*-t),
            mount.smallNutPocket(l).rotate(O,Y,90).translate(l*vec(0,0.5,-0.5) + X*(t if left else -t)),
            ]:
            box = box.cut(p)

        return box


    # builds the diffuser
    def build(self):
        big = 900

        shp = self.makeCone()

        # cutting the cone at the bottom
        w = 34 
        shp = shp.cut( Part.makeBox(w, big, big).translate( vec(-w/2, 0, -big) ) )
        shp = shp.cut(self.cutStraight())

        # cuts the front (so the cone can be bigger)
        shp = shp.cut( Part.makeBox(big,big,big).translate( vec(-big/2, self.Depth, -big/2) ) )

        # holes for bottom reflector
        cyl = Part.makeCylinder(1, self.Depth)
        cyl.rotate(O,-X,90)
        shp = shp.cut(cyl)
        for x in [-50,50]:
            shp = shp.cut(cyl.copy().translate(Z*-15))

        # cutting the reflection desk
        shp.translate( Z*self.ShiftUp )
        hs = self.reflectionDeskFrontHs()

        if False:
            a = (90-self.ReflectionDeskFoldAngle )/2 * pi / 180
            hsBack = self.reflectionDeskFrontHs().translate(-self.DentDepth*vec(0, 1, sin(a)/cos(a)))
        else:
            # hs Back is halfspace shifted back
            hsBack = halfSpace(y=1).translate(-self.DentDepth*Y)

        for a,w in self.DentSegments:
            seg = self.dentSegment(a,w)
            seg.translate(Z*self.ShiftUp)
            hs = hs.fuse(seg.common(hsBack))
        shp = shp.common(hs)

        hsBack2 = self.reflectionDeskFrontHs().translate(-1*vec(0, 1, sin(a)/cos(a))).cut(
            self.reflectionDeskFrontHs()
        )

        showSegmentMarks = False
        if showSegmentMarks:    
            for a,w in self.DentSegments:
                seg = self.dentSegment(a, w-12)
                seg.translate(Z*self.ShiftUp)
                shp = shp.cut( seg.common(hsBack2) )

        return shp

    def strutHole(self,r=0.8):
        return Part.Face(Part.Wire(Part.makeCircle(r)))

    def cornerHole(self,r=0.5):
        return Part.Face(Part.Wire(Part.makeCircle(r)))

    # podpěra
    def strut(self, angle=135):
        dia = 30
        t = 15
        tt = t/2

        r = dia/2
        rsmall = 0.8
        rr = r/angleVec(angle/2).x 

        p = r*angleVec(angle)
        q = p.cross(-Z).normalize()*t
        arcs = Lines()
        arcs.add(r*X, r*X + 3*Y,r*angleVec(angle/2), p -(1*q).normalize()*3, p)
        arcs.addBroken(p+q, q, O, -t*Y, -t*Y+r*X, -t*Y+2*r*X, -t*Y+3*r*X, 3*r*X, 2*r*X, r*X)
        profile = Part.Face(Part.Wire([ Part.BSplineCurve(arc).toShape() for arc in arcs]) )

        for pos in [O, p, r*X, 2*r*X, r*X-t*Y,2*r*X-t*Y]:
            profile = profile.cut(self.cornerHole().translate( pos))

        for pos in [ p/2 + q/t*tt] + [ r*(i+0.5)*X - Y*tt for i in [0,1,2] ]:
            profile = profile.cut(self.strutHole().translate(pos)) 


        return profile


        print(rr)
        arcs = Lines()
        arcs.add(O, t*Z)
        arcs.add(t*Z+r*X)
        arcs.add(r*X)
        arcs.add(r*(X-Z),-r*Z)
        arcs.add(-r*Z-t*X)
        arcs.add(-t*X)
        arcs.add(O)

        profile = Part.Face(Part.Wire([ Part.BSplineCurve(arc).toShape() for arc in arcs]) )
        return profile

    def viewDesk(self):
        return ortoRecFace( vec(-150, 140, -110), vec(150, 140, 110) )

