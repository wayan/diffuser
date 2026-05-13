import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan
from copy import copy


def tangentPoint(p, c, r, top=1):
    d = (p - c).Length
    a = math.sqrt(d ** 2 - r ** 2)

    v = (c - p).normalize()
    p = c - v * (r * r / d) + v.cross(FreeCAD.Vector(0,0,top)) * (a * r / d )
    return p

def vec(x=0,y=0,z=0):
    return FreeCAD.Vector(x,y,z)

def translation(v):
    return FreeCAD.Placement(v, FreeCAD.Rotation())

def perpendicular(p):
    # perpendicular vector
    return p.cross(vec(0,0,1)).normalize()


# returns flattening translation
def compFlat(vec1, vec2):
    vec_in  = vec1.cross(vec2).normalize()
    vec_out = vec(0,0,1)

    # Calculate the rotation axis (cross product of normalized vector and unit X vector)
    rotation_axis = vec_in.cross(vec_out)

    # Calculate the rotation angle (acosine of the dot product)
    rotation_angle = math.acos(vec_in.dot(vec_out))

    pl = FreeCAD.Placement()
    pl.rotate( vec(), rotation_axis, rotation_angle * 180 / math.pi )
    return pl

def compFlatFromPts(pts, reversed=False):
    lst = [2,1,0] if reversed else [0,1,2] 
    p1,p2,p3 = [ pts[i] for i in lst ]
    placement = compFlat(p1-p2,p3-p2)

    diff = p1 - placement.toMatrix().multVec(p1)
    return translation(p1 - placement.toMatrix().multVec(p1)) * placement


class FlatDiff:

    def __init__(self):
        self.LensDia      = 60.7
        self.WidthTop     = 250
        self.WidthFlash   = 98
        self.Length       = 320
        self.WidthBottom  = 220
        self.FrontAngle   = 48 
        self.LensDiaLarge = self.LensDia + 16
        self.FlashHeadWidth = 68
        self.FlashHeadDepth =  15 
        self.FlashThickness = 35

        z1, z2 = [2568, 1523]
        k = self.LensDia/ (z2 - z1) 
        zs = -k * (z1 + z2) / 2
        xzPixel = lambda x,z: vec(x*k,0,z*k+zs)




        p1 = xzPixel(1550, (z1+z2)/2)
        angle = math.pi * self.FrontAngle / 180

        p2 = p1 + self.Length * vec(math.cos(angle), 0, math.sin(angle))
        # self.p3 = xzPixel(2840,107)

        self.fc = xzPixel(2680, 358)

        tp = tangentPoint(vec(p2.x, p2.z), vec(self.fc.x, self.fc.z), self.FlashThickness/2, True) 

        # shifted 2.5 cm to the p2 
        p3 = vec(tp.x,0,tp.y)
        p3 = p3 + 25 * (p2 - p3).normalize()

        self.P1 = lambda k: p1 + k*vec(y=self.WidthBottom / 2) 
        self.P2 = lambda k: p2 + k*vec(y=self.WidthTop / 2) 
        self.P3 = lambda k: p3 + k*vec(y=self.WidthFlash / 2) 

        self.PS = lambda k: self.P1(k) + (self.P3(k) - self.P1(k)).normalize() * 15


    def frontPoints(self):
        return [ self.P1(-1), self.P1(1), self.P2(1), self.P2(-1), self.P1(-1) ]

    def topPoints(self):
        return [ self.P3(-1), self.P3(1), self.P2(1), self.P2(-1), self.P3(-1)]

    def sidePoints(self, k):
        p1 = self.PS(k)
        return [ p1, self.P3(k), self.P2(k), p1]

    def getFront(self):
        poly = Part.makePolygon(self.frontPoints())
        f = Part.Face(Part.Wire([poly])).cut(self.lensCut())
        return f

    def lensCut(self):
        cyl = Part.makeCylinder(self.LensDiaLarge / 2, 500)
        cyl.rotate(vec(),vec(0,1,0),90)

        lensDiff = self.LensDia - self.LensDiaLarge
        cyl.translate(vec(0,0, lensDiff))
        box = Part.makeBox(500, self.LensDiaLarge, self.LensDiaLarge)
        box.translate(vec(0, -self.LensDiaLarge/2, lensDiff - self.LensDiaLarge))
        cyl = cyl.fuse(box)
        cyl.translate(vec(-250,0,0))
        return cyl

    def flashCut(self):
        vy = vec(0,self.FlashHeadWidth/2)
        p3 = self.P3(0) - 3 * (self.P2(0) - self.P3(0)).normalize()
        pts = [ p3 - vy, p3+vy, self.P2(0)+vy, self.P3(0)-vy, p3 - vy ]
        poly = Part.makePolygon(pts)
        f = Part.Face(Part.Wire([poly]))
        # normal vector
        e = self.FlashThickness * (self.P2(0) - self.P3(0)).cross(vec(0,-1,0)).normalize()
        return f.extrude(e)

    def getTop(self):
        poly = Part.makePolygon(self.topPoints())
        return Part.Face(Part.Wire([poly]))

    # shapeof the diffusion
    def getBottom(self):
        p31 = self.P1(1) - self.P3(1)

        p11 = self.P3(1) + (1+ 0.5*self.LensDia/abs(p31.z)) * p31
        p11m = vec(p11.x, -p11.y, p11.z)

        pts = [ p11m, p11, self.P3(1), self.P3(-1), p11m]
        poly = Part.makePolygon(pts)
        f = Part.Face(Part.Wire([poly]))
        f = f.cut(self.lensCut())
        f = f.cut(self.flashCut())
        return f

    def getSide(self, koef=1):
        poly = Part.makePolygon(self.sidePoints(koef))
        f = Part.Face(Part.Wire([poly]))
        return f

    def flap(self, P1, P2, w2, w1=0):
        d = perpendicular(P1-P2)
        return Part.Face(Part.Wire([Part.makePolygon([P1 + w1*d, P1+w2*d, P2+w2*d, P2+w1*d, P1 + w1*d])]))

    def flapHoles(self, P1, P2, w, step, start = None):
        pos = step if start == None else start
        holes = []
        orig = Part.makeCylinder(0.5,5)

        perp = w * perpendicular(P2-P1)
        while abs(pos) < (P2 - P1).Length:
            cyl = orig.copy()
            cyl.translate( P1 + perp + pos * (P2-P1).normalize() + vec(0,0,-1))
            holes.append(cyl)
            pos = pos + step
        return holes


    def topPlacement(self):
        return compFlatFromPts([ self.P3(0), self.P3(1), self.P2(1) ])

    def sidePlacement(self, k):
        pl = self.topPlacement()
        plm = pl.toMatrix()
        p1,p3,p2 = [ plm.multVec(p) for p in diff.sidePoints(k)[0:3] ]
        return compFlatFromPts([p3,p1,p2], k == -1) * pl

    def unwrapped(self):
        # top rotated
        top = self.getTop()
        top.Placement = self.topPlacement()
        plm = top.Placement.toMatrix()

        fw = 20
        hdist = 10 

        holes = []

        for inFront in [True, False]: 
            if inFront:
                P2 = plm.multVec(self.P2(-1))
                P1 = plm.multVec(self.P2(1))
            else:
                P2 = plm.multVec(self.P3(1))
                P1 = plm.multVec(self.P3(-1))

            ps = 0.5*(P2+P1)
            for i in [0,1,2]:
                top = top.fuse(self.flap(P1, P2, (i+1)*fw, i*fw))
                holes.append( self.flapHoles(ps, P1, i*fw + fw / 2, hdist, 0))
                holes.append( self.flapHoles(ps,P2, -i*fw -fw / 2, hdist, hdist))
        
        # side rotated
        for k in [-1,1]:
            side = diff.getSide(k)
            side.Placement = self.sidePlacement(k)
            sm = side.Placement.toMatrix()
            top = top.fuse(side)

            p1,p2,p3 = [ sm.multVec(fn(k)) for fn in [self.PS, self.P2, self.P3] ]

            for i in [0,1,2]:
                top = top.fuse( self.flap(p1,p2, (i+1)*k*fw, i*k*fw) )
                top = top.fuse( self.flap(p1,p3, -(i+1)*k*fw, -i*k*fw) )
                holes.append( self.flapHoles(p2,p1,  (i+0.5) *k*fw,hdist) )
                holes.append( self.flapHoles(p3,p1, -(i+0.5) *k*fw,hdist) )

            # cut
            p3,p2,p3r,p2r = [ plm.multVec(p) for p in [self.P3(-k),self.P2(-k),self.P3(k),self.P2(k)] ]
            plac = FreeCAD.Placement()
            plac.rotate(p3r,p2r-p3r,180)
            placm = plac.toMatrix()
            p3f,p2f = [ placm.multVec(p) for p in [p3,p2] ];

            q = p3f - 1 * (p2f-p3f) 
            r = p3f + 2 * (p2f-p3f)

            cutFlap = self.flap(q,r, k*60)
            top = top.cut(cutFlap)


        for hole in holes:
            top = top.cut(hole)
        return top


    def unwrappedBottom(self):
        bottom = self.getBottom()
        pl = compFlatFromPts([ self.P3(0), self.P1(1), self.P3(1) ])
        pl.translate( vec(-100, 0, 0) )
        bottom.Placement = pl
        plm = pl.toMatrix()

        holes = []
        fw = 10
        hdist = 10
        for k in [-1,1]:
            p1,p3 = [ plm.multVec(fn(k)) for fn in [self.P1, self.P3 ] ]
            holes.append( self.flapHoles(p3,p1,-0.5*k*fw,hdist) )

        for hole in holes:
            bottom = bottom.cut(hole)
        return bottom


NAME = "bracket"
doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

diff = FlatDiff()
Part.show( diff.unwrapped(), "complete")
Part.show( diff.unwrappedBottom(), "completeBottom")



#normalizeFlat(left)
#normalizeFlat(top)
#normalizeFlat(bottom)
#normalizeFlat(front)
#Part.show(top, "top")
#Part.show(left, "left") 
#Part.show(right, "right") 
#Part.show(bottom, "bottom")
#Part.show(front, "front")
#Part.show(diff.flashCut(), "ccc")



#cyl = Part.makeCylinder(diff.FlashThickness/2, 120)
#cyl.translate(vec(z=-60))
#cyl.rotate(vec(), vec(1), 90)
#cyl.translate(diff.fc)
#Part.show(cyl,"cyl")

doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

