"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan

# to be later imported from Util
class Util:
    Meshno = 0

    def writeMesh(shape, filename):
        mesh = MeshPart.meshFromShape(Shape = shape, LinearDeflection=0.03, AngularDeflection=0.174533, Relative=False)
        #Util.Meshno = Util.Meshno + 1
        #meshobj = doc.addObject("Mesh::Feature", ("mesh-%d" % Util.Meshno))
        #meshobj.Mesh = mesh
        mesh.write(os.path.join(os.path.dirname(__file__), filename))

def vec(x=0,y=0,z=0):
    return FreeCAD.Vector(x,y,z)

def leftSpace():
    big = 600
    boxLeft = Part.makeBox(big, big, big)
    boxLeft.translate( vec(0, -big/2, -big/2) )
    return boxLeft

def unwrapShape(doc, shp):
    name = "anymesh"
    mesh = MeshPart.meshFromShape(Shape = shp, LinearDeflection=0.03, AngularDeflection=0.174533, Relative=False)
    meshobj = doc.addObject("Mesh::Feature", name)
    meshobj.Mesh = mesh

    l = len(doc.Objects)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(NAME, name)
    Gui.runCommand('MeshPart_CreateFlatMesh', 0)

    ret = Part.makeCompound([o.Shape for o in doc.Objects[l:]])
    for o in doc.Objects[l:]:
        doc.removeObject(o.Name)
    doc.removeObject(name)
    return ret


# END OF "IMPORT"

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
            self.Angle    = 60 
            self.Depth    = 155
            self.ReflectionDeskDepth = 55
            self.FlashDepth = 17 + 15 

        if type == "9_17":
            self.Depth    = 125
            self.LensDia  = 72 
            self.Angle    = 100 
            self.Depth    = 135

        if type == "9_17e":
            self.LensDia  = 70 
            self.Angle    = 110 
            self.Depth    = 125

        if type == "9_17test":
            self.LensDia  = 70 
            self.Angle    = 95 
            self.Depth    = 125
            # self.Angle    = 90 
            self.AxisAngle = 15
            self.ShiftUp   = -8
            self.HeightRatio = 0.8

        # Laowa having 110 degrees viewing angle
        if type == "laowa":
            self.Angle = 110 
            self.LensDia = 50.5
            self.Depth = 120

        self.ReflectionDeskWidth = 150
        self.ReflectionDeskHeight = 90
        self.ReflectionDeskDepth = 70


        # unused
        self.DentSegmentAngles = [ [-35,0], [65, 115], [180,215] ] 
        #self.DentSegments      = [ [-17,20], [0, 40], [197,20] ]
        self.DentSegments      = [ [0, 50], [100, 45], [-100, 45] ]


        self.DentDepth = 12
        self.ReflectionDeskFoldAngle = 45
        self.ReflectionDeskHeight   = 56

        self.ReflectionDeskDown = self.LensDia / 2 + 40
        self.ReflectionDeskDownFold = self.LensDia / 2 - 15
        self.ReflectionDeskWidth = self.LensDia + 90

    def Width(self):
        return self.LensDia + 2*tan(self.Angle/2 * pi / 180) *self.Depth

    def Height(self):
        return self.Width() * self.HeightRatio

    def frontRim(self,t=0):
        k = 1.5
        e = Part.Ellipse( k*vec(x=self.Width()/2 + t), k*vec(z=self.Height()/2 + t), vec()).toShape()
        e.translate(k*vec(y=self.Depth ))
        return e

    def backRim(self, t=0):
        # around lens
        r = self.LensDia / 2 + self.LensOuter

        # almost small tip of the cone
        rtip = 10
        ro = self.Height() / 2 
        dtip = self.Depth / (ro - r) * (r - rtip)
        e = Part.Ellipse( vec(x=rtip+t), vec(z=rtip+t), vec() ).toShape() 
        e.translate(vec(y=-dtip))
        return e

    def makeCone(self, t=0, solid=False):
        # around lens
        cone = Part.makeLoft([self.backRim(t), self.frontRim(t) ], solid=solid).removeSplitter()
        cone.rotate( vec(0,0,self.LensDia/2+self.LensOuter), vec(1), self.AxisAngle )
        # cone = cone.cut(self.lensCut())
        return cone

    def makeSolidCone(self, thickness=None):
        if thickness == None:
            thickness = self.ConeThickness
        return self.makeCone(thickness/2, True).cut( self.makeCone(-thickness/2, True))

    def buildSpade(self):
        cone = self.makeCone()
        w1 = 30
        h1 = 30
        w2 = 100
        h2 = 80

        x1, x2, y1, y2 =  [ w1 / 2, w2 / 2,  h1, h1 + h2 ]
        form = Part.Face(
                Part.makePolygon( [ vec(x1,0), vec(x1,y1), vec(x2,y1), vec(x2,y2), vec(-x2,y2), vec(-x2,y1), vec(-x1, y1), vec(-x1,0), vec(x1,0) ]
        )).extrude(vec(z=-400))
        return cone.common(form)

    def buildHood(self):
        big = 500
        shp = self.makeCone()

        r = self.LensDia / 2
        w = 4 
        shp = shp.cut(
            Part.makeBox(w, big, big).translate( vec(-w/2, 0, -big) )
        )

        # lomena cara cutting the bottom of the cone
        z1 = -10 
        y1 = 20

        p1 = vec( y=y1, z = -r + z1)
        p2 = vec( y=self.Depth - 0.5, z =-r + z1 + 3 )
        p3 = vec( y=self.Depth - 0.5, z = self.Height() / 2 )

        between = lambda p1,p2,k: p1 * (1 -k ) + p2 * k

        k1, k2, k3, k4 = [ 0.4, 0.33, 0.5, 0.7 ]

        if False:
            poly = Part.makePolygon([
                p1,
                between(p1,p2, k1),
                between( between(p1,p2, k1), between(p2,p3,k2), k4),
                between( p2, p3, k3),
                vec(y = self.Depth + 1, z=-self.Height() ),
                vec(y = y1, z=-self.Height() ),
                vec(y = y1, z=-r + z1) ])
            poly.translate(vec(-big / 2) )
            bottomCut = Part.Face( Part.Wire(poly) ).extrude( vec(big) )

        
        poly = Part.makePolygon([
            vec(y=y1, z=-self.Height()),
            p1,
            between(p1,p2, k1),
            between( between(p1,p2, k1), between(p2,p3,k2), k4),
            between( p2, p3, k3),
            p3 + vec(0,0,10)
         ])

        cutter = Part.Wire(poly).extrude( vec(big) ).translate(vec(-big/2))
        front = cutter.section(shp)
        hood  = front.extrude( vec(0,-300) )
        hood  = hood.common(
            Part.makeBox(big,big,big).translate(vec(-big/2,0,-big/2))
        )
        hood = hood.common(
            Part.makeBox(big,big,big).translate(vec(0,-big/2,-big/2))
        )
        return hood

        cutter.tessellate(0.1)

        shp.tessellate(0.1)

        shp = Part.makeCone(self.LensDia /2 , self.Height()/2, self.Depth )
        shp.rotate(vec(), vec(-1), 90)
        x = shp.common(cutter)
        x.removeSplitter()
        x.tessellate(0.1)
        return x

        return x.extrude(vec(0,50,0))
        edges = [e for e in x.Edges if e.BoundBox.ZLength > 0.01 ]
        return Part.Wire(edges)
    
        
        #return cutter.fuse(shp)

        if False:
            bottomCut = Part.makeBox(big, big, big)
            bottomCut.translate(
                vec(-big / 2, 30, -big - self.LensDia / 2  + 8)
            )

        shp = shp.cut(bottomCut)
        return shp


    def cutStraight(self):
        def between(p1,p2,k): 
            return p1 * (1 -k ) + p2 * k

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
        Part.show(poly,"oly")
        poly.translate(vec(-big / 2) )

        return Part.Face( Part.Wire(poly) ).extrude( vec(big) )

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

    def OLD_dentSegment(self, angleStart, angleEnd):
        # just bigEnough
        h, r = [60,  400 ]
        cyl = Part.makeCylinder(r, h, vec(), vec(0,1), angleEnd - angleStart) 
        cyl.rotate( vec(), vec(0,1), -(angleEnd - 90) )
        cyl.translate( vec(0,-h/2) )
        return cyl

    def dentSegment(self, angle, width ):
        d, h = [60,  400 ]
        box = Part.makeBox(width, d, h).translate(vec(-width/2, -d/2))
        box.rotate( vec(), vec(0,1), angle) 
        return box

    def recPoints(self):
        return [[-1,-1], [-1,1], [1,1], [1,-1], [-1,-1]]

    # half space before reflectionDesk
    def reflectionDeskFrontHs(self):
        # big enough
        w = 400

        a = self.ReflectionDeskFoldAngle * pi / 180 
        ys  = (self.ReflectionDeskDown - self.ReflectionDeskDownFold) * cos(a)/sin(a)

        pts = [ vec(x *w, 0, -self.ReflectionDeskDownFold * (1-z)/2 + w * (z+1)/2) for x,z in self.recPoints() ]
        desk = Part.Face(Part.makePolygon(pts))

        # folded part of the desk at the bottom
        a = self.ReflectionDeskFoldAngle * pi / 180 
        ys  = (self.ReflectionDeskDown - self.ReflectionDeskDownFold) * cos(a)/sin(a)
        pts = [ vec( w * x, ys * (1-z)/2, -self.ReflectionDeskDown * (1-z)/2 - self.ReflectionDeskDownFold * (1+z)/2) for x,z in self.recPoints() ]
        desk2 = Part.Face(Part.makePolygon(pts))

        return desk.fuse(desk2).extrude(vec(0,300))

    def reflectionDesk(self):
        # final width 
        w = self.LensDia + 90

        pts = [ vec( x *self.ReflectionDeskWidth/2, 0, -self.ReflectionDeskDownFold * (1-z)/2 + (self.ReflectionDeskHeight+self.ReflectionDeskDepth+self.FlashDepth) * (z+1)/2) for x,z in self.recPoints() ]
        desk = Part.Face(Part.makePolygon(pts))

        # folded part of the desk at the bottom
        a = self.ReflectionDeskFoldAngle * pi / 180 
        ys  = (self.ReflectionDeskDown - self.ReflectionDeskDownFold) * cos(a)/sin(a)
        pts = [ vec( self.ReflectionDeskWidth * (x/2), ys * (1-z)/2, -self.ReflectionDeskDown * (1-z)/2 - self.ReflectionDeskDownFold * (1+z)/2) for x,z in self.recPoints() ]
        desk2 = Part.Face(Part.makePolygon(pts))
        desk = desk.fuse(desk2)

        # top cut for the flash
        pts = [ vec(x * self.FlashWidth/2, 0, (self.ReflectionDeskHeight + self.ReflectionDeskDepth) * (1-z)/2 + (self.ReflectionDeskHeight + self.ReflectionDeskDepth + self.FlashDepth)*(z+1)/2  ) for x,z in self.recPoints() ]
        desk = desk.cut(Part.Face(Part.makePolygon(pts)))
        
        # lens cut
        hc = 100
        desk = desk.cut(Part.makeCylinder(self.LensDia / 2, hc, vec(0,-hc/2), vec(0,1)))

        # thin cuts marking the folds
        pts = [ vec(x * 30, 0, z * 0.5 + self.ReflectionDeskHeight) for x,z in self.recPoints() ]
        desk = desk.cut(Part.Face(Part.makePolygon(pts)))

        pts = [ vec(x * self.LensDia/2, 0, z * 0.5 + (-self.ReflectionDeskDownFold)) for x,z in self.recPoints() ]
        desk = desk.cut(Part.Face(Part.makePolygon(pts)))

        # cutting the segments
        thickCone = self.makeSolidCone()
        thickCone.translate(vec(0, 0, self.ShiftUp))
        for angle, width in self.DentSegments:
            seg = self.dentSegment(angle,width).translate(vec(0, 0, self.ShiftUp))
            desk = desk.cut(thickCone.common(seg))


        # shape is cut by the front by bspline curve
        x1 = -self.ReflectionDeskWidth / 2
        x2 = -(self.FlashWidth/2 + 15 )
        z1 =  self.ReflectionDeskDepth + self.FlashDepth + self.ReflectionDeskHeight
        z2 = -self.ReflectionDeskDownFold + 30 
        z3 = -self.ReflectionDeskDownFold - 20 
        z4 = -self.ReflectionDeskDown
        pts   = [ [x2, z1], [x2-8, z1], [x1, z2+40], [x1, z2] ]
        pts2  = [ [x1, z3], [x1, z4], [x1+20, z4] ]

        ptsl   = [ vec(x,0,z) for x,z in pts        ] 
        ptsr   = [ vec(-x,0,z) for x,z in pts[::-1] ]
        pts2l  = [ vec(x,0,z) for x,z in pts2        ] 
        pts2r  = [ vec(-x,0,z) for x,z in pts2[::-1] ]

        cutter = Part.Face(Part.Wire([ 
            Part.BSplineCurve(ps).toShape() for ps in [
                ptsl,
                [ ptsl[-1], pts2l[0] ],
                pts2l,
                [ pts2l[-1], pts2r[0] ],
                pts2r,
                [ pts2r[-1], ptsr[0] ],
                ptsr,
                [ ptsr[-1], ptsl[0] ]
            ]
        ]))

        big = 100
        cutter = cutter.extrude(vec(0,big,0)).translate(vec(0,-big/2,0)) 

        desk = desk.common(cutter)

        # flaps holding the folded part
        # no flaps
        if False:
            ys = (-self.ReflectionDeskDownFold - z3) * cos(a)/sin(a)
            for s in [-1,1]:
                x = -s * x1
                pts = [ vec(x, 0, -self.ReflectionDeskDownFold), vec(x, ys, z3),  vec(x, 0, z2) ]
                pts.append(pts[0])

                # changes the orientation
                flap = Part.Face(Part.makePolygon(pts if s == -1 else pts[::-1]))

                pts2 = [ pts[2], pts[2] + vec(-s*15), pts[2] + vec(-s*15,0,-15), pts[0], pts[2] ]
                flap2 = Part.Face(Part.makePolygon(pts2 if s == -1 else pts2[::-1]))
                flap = flap.fuse(flap2)
                
                # marking hole small hole to desk and to flap
                center = pts[2] + 0.5*vec(-s*15,0,-15)
                hole = Part.makeCylinder(1,5,center, vec(0,1)).translate(vec(0,-3))

                flap = flap.cut(hole)

                #Part.show(flap, ("flap%d" % s))
                flap.rotate( pts[0], pts[1] - pts[0], s*90)

                desk = desk.cut(hole)
                desk = desk.fuse(flap)
        return desk

    def lensCut(self):
        r = self.LensDia / 2 - 1
        lens = Part.Face(Part.Wire([Part.Ellipse( vec(x=r), vec(z=r), vec() ).toShape()]))
        pts1 = [ vec(-r,0,0), vec(r,0,0), vec(r, 0, -3*r), vec(-r,0,-3*r), vec(-r,0,0) ]
        lens = lens.fuse(Part.Face(Part.makePolygon(pts1)))


        pts2 = [ vec(-r -3,0,0), vec(r +3, 0, 0), vec(r+3, 0, -3), vec(-r-3,0,-3), vec(-r-3,0,0) ]
        lens = lens.fuse(Part.Face(Part.makePolygon(pts2)))
        lens = lens.translate(vec(0,-100)).extrude(vec(0,200))
        return lens


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

#        shp = shp.cut(self.cutSmooth())

        # holes for bottom reflector
        cyl = Part.makeCylinder(1, self.Depth)
        cyl.rotate( vec(), vec(-1), 90)
        shp = shp.cut(cyl)
        for x in [-50,50]:
            shp = shp.cut(cyl.copy().translate(vec(x,0,-15)))

        # cutting the reflection desk
        shp.translate( vec(0,0,self.ShiftUp) )
        hs = self.reflectionDeskFrontHs()

        a = (90-self.ReflectionDeskFoldAngle )/2 * pi / 180
        hsBack = self.reflectionDeskFrontHs().translate(-self.DentDepth*vec(0, 1, sin(a)/cos(a)))

        for a,w in self.DentSegments:
            seg = self.dentSegment(a,w)
            seg.translate(vec(0, 0, self.ShiftUp) )
            hs = hs.fuse(seg.common(hsBack))
        shp = shp.common(hs)

        hsBack2 = self.reflectionDeskFrontHs().translate(-1*vec(0, 1, sin(a)/cos(a))).cut(
            self.reflectionDeskFrontHs()
        )
        for a,w in self.DentSegments:
            seg = self.dentSegment(a, w - 6)
            seg.translate(vec(0, 0, self.ShiftUp) )
            shp = shp.cut( seg.common(hsBack2) )

        return shp

    def viewDesk(self):
        poly = Part.makePolygon([
            vec(150*x, 140, 110 * z) for x,z in self.recPoints()
         ])
        return Part.Face(poly)


NAME = "bracket"
doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)

#cone = Cone("9_17e")
cone = Cone("9_17test")
# cone = Cone("30s")


# shifting diffuser up and back along the reflection desk
diffuser = cone.build()
ldiff = diffuser.common(leftSpace())
#    Part.show(ldiff, "diff-%d" % angle)
Part.show(ldiff, "diffuser" )
diffu = unwrapShape(doc, ldiff).translate(vec(300))
Part.show(diffu, "diffuser-unwrapped" )
Part.show(cone.viewDesk(), "viewdesk")

desk =  cone.reflectionDesk()
Part.show(desk, "desk")
desku = unwrapShape(doc, desk).translate(vec(-300))
Part.show(desku, "desk-unwrapped")



#mdiff = MeshPart.meshFromShape(Shape = ldiff, LinearDeflection=0.03, AngularDeflection=0.174533, Relative=False)
#meshobj = doc.addObject("Mesh::Feature", "mdiff")
#meshobj.Mesh = mdiff
#
#l = len(doc.Objects)
#Gui.Selection.clearSelection()
#Gui.Selection.addSelection(NAME, "mdiff")
#Gui.runCommand('MeshPart_CreateFlatMesh', 0)
#
## selecting result of unwrap mesh
#diffu = Part.makeCompound([o.Shape for o in doc.Objects[l:]])
#for o in doc.Objects[l:]:
#    doc.removeObject(o.Name)
#diffu.translate(vec(300,0,))

#mdesk = MeshPart.meshFromShape(Shape = desk, LinearDeflection=0.03, AngularDeflection=0.174533, Relative=False)
#meshobj = doc.addObject("Mesh::Feature", "mdesk")
#meshobj.Mesh = mdesk
#
#Gui.Selection.clearSelection()
#Gui.Selection.addSelection(NAME, "mdesk")
#l = len(doc.Objects)
#Gui.runCommand('MeshPart_CreateFlatMesh',0)
#
#desku = Part.makeCompound([o.Shape for o in doc.Objects[l:]])
#for o in doc.Objects[l:]:
#    doc.removeObject(o.Name)
#desku.translate(vec(-300,0,))


doc.recompute()



# Part.show(Part.makePolygon(cone.cutSmoothPts()), 'poly')
#mesh = MeshPart.meshFromShape(Shape = shp, LinearDeflection=1, AngularDeflection=3, Relative=False)
#meshobj = doc.addObject("Mesh::Feature")
#meshobj.Mesh = mesh



doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

