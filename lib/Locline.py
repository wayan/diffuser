
import FreeCAD, Part, Mesh, MeshPart, math, ImportGui, FreeCADGui
from Diffutil import vec, halfSpace, nutPocket

def loadLocLineElement():
    doc = FreeCAD.newDocument()
    ImportGui.insert("./51801, 59859, 59860, 59861, 56801, 57860, 57859, 57861 1-2 Element.STEP", doc.Name)
    obj = doc.getObject("Part__Feature")
    shp = obj.Shape.copy()
    FreeCAD.closeDocument(doc.Name)
    return shp

def loclinePart(elem, outer, shift=0, cuts=0):
    shp = elem.copy()
    if outer:
        #hOut = 16.47
        hOut = 16.30
        shp = shp.rotate( vec(), vec(0,1,0), 90).translate(vec(0,0,-hOut))
        shp = shp.cut(halfSpace(z=1))
    else:
        total = 29.90
        part = 11.581 + 2
        shp = shp.rotate( vec(), vec(0,1,0), -90).translate(vec(0,0,total-part))
        shp = shp.cut(halfSpace(z=1))

    if shift != 0:
        pts = [ vec(x*100,0,z*100-50) for x,z in [ [0,0],[1,0],[1,1],[0,1],[0,0]] ]
        face = Part.Face(Part.makePolygon(pts))
        shp = shp.common(face).translate(vec(x=shift)).revolve(vec(),vec(0,0,1),360)

    if cuts > 0:
        # width of the cut
        cw = 2 
        ch = 30
        hs = 5
        pts = [ vec(x - cw/2, 0, z - hs - ch) for x,z in [ [0,0], [cw,0], [cw,ch/5], [cw,ch*4/5], [cw,ch], [0,ch], [0,ch*4/5], [0,ch*1/5], [0,0] ] ]
        dent = Part.Face(Part.Wire(Part.Shape([Part.BSplineCurve(pts, periodic=True)]))).extrude(vec(0,30,0))
        for a in [i * 360/cuts  for i in range(0, cuts) ]:
            shp = shp.cut( dent.copy().rotate(vec(),vec(0,0,1), a) )

    return shp

class Mount:

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
        return nutPocket(self.NutDia, height if height != None else self.NutHeight)

    def locLineProtrusion(self):
        cyl = Part.makeCylinder(self.LocLineDiaIn/2, self.LocLineHeight)
        cyl = cyl.cut( Part.makeCylinder( self.LocLineDiaInIn/2, self.LocLineHeight)) 
        for angle in [0,60,120]:
            spacer = Part.makeBox( self.LocLineDia, self.LocLineSpacer, self.LocLineHeight )
            spacer.translate( vec(-self.LocLineDia/2, -self.LocLineSpacer/2) )
            cyl = cyl.cut(spacer.rotate( vec(), vec(z=1), angle ))

        edges = [ e for e in cyl.Edges if e.BoundBox.ZLength > 0.05 or e.BoundBox.ZMin > 0.05 ]

        if len(edges)>0:
            cyl = cyl.makeFillet( 0.33, edges)
        return cyl

