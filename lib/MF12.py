
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
import Mesh
import Diffutil as df
from Diffutil import vec, cvec, halfSpace, ortoRecFace, ortoRecPts, symX, symY, XAxis, YAxis, ZAxis, O, X,Y,Z
import Locline
import Lines

def loadMF12(height=None):
    doc = FreeCAD.newDocument()
    Mesh.insert("./MF12-BabyMount.stl", doc.Name)
    meshobj = doc.Objects[0] 

    shpm = Part.Shape()
    shpm.makeShapeFromMesh(meshobj.Mesh.Topology, 0.1, False)
    shp = Part.Solid(Part.Shell(shpm.Faces))

    shp.rotate(O, Z, 30)
    shp.rotate(O,-Y,90)
    bb = shp.BoundBox
    shp.translate( vec( -0.5* (bb.XMax+bb.XMin), -0.5*(bb.YMax+bb.YMin), -bb.ZMin) )

    bb = shp.BoundBox

    if height != None:
        if bb.ZMax > height:
            shp.translate(Z*(height-bb.ZMax))
            shp = shp.cut(halfSpace(z=-1))
        else:
            profile = Part.Face(Part.makePolygon([ vec(50*x,50*y, 1) for x,y in [ [-1,-1], [1,-1], [1,1], [-1,1], [-1,-1] ]]))
            profile = profile.common(shp).extrude(vec(0,0,-(height+1-bb.ZMax)))
            shp = shp.fuse(profile)
            shp.translate(Z*(height-bb.ZMax))

    thickness = 16.5
    for x in [-1,1]:
        shp = shp.cut(halfSpace(x=x).translate(vec(x*thickness/2)))

    FreeCAD.closeDocument(doc.Name)
    return shp

def holderLocLine(bigger=0):
    el = Locline.loadLocLineElement()
    outer = Locline.loclinePart(el, True, bigger)

    # 36 mmm is too much 26 seems to ok
    mf12 = loadMF12(26)
    # inner cylinder
    mf12 = mf12.fuse(Part.makeCylinder(8,8.2))
    mf12 = mf12.fuse(outer)

    if False:

        # cut to insert nut
        hole = Part.Face(Part.Wire(Part.makeCircle(5))).rotate(vec(),vec(0,1),90).translate(vec(-20,0,10)).extrude(vec(40))
        mf12 = mf12.cut(hole)
        # mf12 = mf12.common(halfSpace(x=1))
        holeTolerance = 1.007
        # radius of M4 Nut
        nutDia = 7.8 * holeTolerance
        mf12 = mf12.cut( df.nutPocket(nutDia, 6).translate(vec(0,0,4)))
        # radius of hole (m4)
        boltDia  = 4.2
        mf12 = mf12.cut( Part.makeCylinder(boltDia/2, 10) )

    return mf12

class TriggerHolder:

    def __init__(self):
        self.Width = 50 
        self.Thickness = 8 
        self.SideThickness = 8
        self.HoleDia = 9.3
        self.CenterHeight = 15
        self.ColumnDia = self.HoleDia+6
        return

    def shape(self):
        m = Locline.Mount()

        p0,p1,p2,p3,p4 = ortoRecPts(*[ k*vec(self.Width,m.LocLineDia) for k in [-0.5,0.5]])
        ps  = self.SideThickness*X

        arcs = Lines.Lines()
        arcs.add(0.5*(p3+p0),p0)
        arcs.add(p0+ps)
        arcs.add(p0+ps+vec(3), vec(-8,-self.ColumnDia/2), vec(0,-self.ColumnDia/2))
        arcs += arcs.rev(symX)
        arcs += arcs.rev(symY)


        base = Part.Face(Part.Wire([ Part.BSplineCurve(arc).toShape() for arc in arcs ]))
        base = base.extrude(self.Thickness*Z)

        base = base.fuse(Part.makeCylinder(self.ColumnDia/2,16))
        cut  = ortoRecFace(*[ k*vec(21.5,m.LocLineDia) for k in [-0.5,0.5]])
        cut  = cut.extrude( 2*Z)
        base = base.cut(cut)
        hole = Part.makeCylinder(self.HoleDia/2, 30)
        base = base.cut(hole)

        for side in [-1,1]:
            # side
            pz = self.CenterHeight*Z
            py = vec(m.LocLineDia/2)

            box = ortoRecFace( -py + vec(0,-self.CenterHeight), py )
            box = box.fuse(Part.Face(Part.Wire(Part.makeCircle(m.LocLineDia/2))))
            box = box.extrude(-self.SideThickness*Z)
            box = box.fuse( m.locLineProtrusion() )
            box = box.cut( m.boredHole(40).translate(-20*Z))
            box = box.cut( m.smallNutPocket().translate(-self.SideThickness*Z))
            box = box.rotate(vec(),Z,side*90).rotate(vec(), Y, side*90).translate(vec(side*self.Width/2,0,self.CenterHeight))
            base = base.fuse(box)

        
        return base

