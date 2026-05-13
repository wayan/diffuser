"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
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
def recXZ( w, h): 
        return Part.Face(  Part.makePolygon([vec(),vec(w),vec(w,z=h), vec(z=h), vec()]) )

def halfSpace(x=0,y=0,z=0,l=300):
    sx,sy,sz = [ (0 if d > 0 else (-l if d < 0 else -l/2)) for d in [x,y,z]]
    box = Part.makeBox(l,l,l).translate(vec(sx,sy,sz))
    return box

# END OF "IMPORT"

class Holder:

    def __init__(self, type="regular"):
        self.FlangeThickness = 1.6
        self.FlangeAngle   = 45 
        self.FlangeLength  = 12
        self.BodyThickness = 3.5
        self.BodyOuterDia  = 49
        self.BodyHeight    = 10
        self.WingThickness = 2
        self.WingLength    = 8 
        self.FilterDia = 46
        self.HoleDia      = 3
        self.ThreadHeight = 3 
        self.UpperThreadHeight = 2 
        self.FilterPitch = 0.75
        self.TipHeight   = 1.6
        self.TipDia      = 1.6
        self.CutInHalf   = True
        self.CutInHalf   = False


        #self.FilterDia = 62
        #self.BodyHeight = 3 
        #self.WingLength = 4 
        #self.FlangeAngle = 40 

        self.BodyOuterDia = self.FilterDia + 3

    def maleThread(self, dia, pitch, height):
        h = height 
        outer = dia  / 2
        inner, iinner, oouter = [
            outer + ( k / 8 * pitch * sin(pi / 3) )
            for k in [ -5, -7, 1 ]
        ]
        helix = Part.Wire(Part.makeHelix(pitch, h, iinner ).Edges)

        # the thread is a bit narrower
        p = 0.99 * pitch

#        profile = Part.Wire( Part.makePolygon([ 
#            vec(iinner, 0, 0), 
#            vec(outer, 0, -p / 2 + p / 16),
#            vec(outer, 0, -p / 2 - p / 16),
#            vec(iinner, 0, -p), 
#            vec(iinner, 0, 0)
#            ] ).Edges)
        profile = Part.makePolygon([ 
            vec(iinner, 0, 0), 
            vec(outer, 0, -p / 2 + p / 16),
            vec(outer, 0, -p / 2 - p / 16),
            vec(iinner, 0, -p), 
            vec(iinner, 0, 0)
            ] )
        # return profile
        pps = helix.makePipeShell( [profile], True, True)
        pps.applyRotation( FreeCAD.Rotation( vec(0,0,1), 30 ))
        return pps.fuse( Part.makeCylinder(inner, h))



    def build(self):

        angle = self.FlangeAngle

        body = ( 
            recXZ(self.BodyThickness, self.BodyHeight + self.ThreadHeight)
            .translate( vec(self.BodyOuterDia/2 - self.BodyThickness) )
            .revolve(vec(), vec(z=1), 360)
        )

        # negative thread
        thread = (
            Part.makeBox( 200, 200, self.ThreadHeight)
            .translate(vec(-100,-100))
            .cut(
                self.maleThread(self.FilterDia, self.FilterPitch, 2 + self.ThreadHeight)
                .translate( vec(z=-1) )
            )
        )


        upperThread = ( 
            Part.makeBox( 200, 200, self.UpperThreadHeight)
            .translate(vec(-100,-100))
            .common(
                self.maleThread(self.FilterDia, self.FilterPitch, 2 + self.UpperThreadHeight)
                .translate( vec(z=-1) )
            )
            .translate(
                vec(z=self.BodyHeight + self.ThreadHeight - self.UpperThreadHeight)
            )
        )

        l = 14 
        flange = (
            recXZ(self.FlangeLength + l, self.FlangeThickness)
            .translate( vec(-l, 0, -self.FlangeThickness) )
            .fuse(
                recXZ(self.WingThickness, self.WingLength)
                .translate(vec(z=-self.WingLength - self.FlangeThickness))
            )
            .rotate( vec(), vec(y=-1), self.FlangeAngle )
            .cut( recXZ(200, 200).translate(vec(-200, z=-100)))
            .translate( vec(self.BodyOuterDia / 2, 0, z=self.BodyHeight+self.ThreadHeight))
            .revolve( vec(), vec(z=1), 360 )
        )

        tip = (
            Part.makeCone(self.TipDia / 2, 0.1, self.TipHeight)
            .rotate( vec(), vec(y=-1), 180 )
            .translate( vec(self.FlangeLength * 0.6, 0, -self.FlangeThickness ) )
            .rotate( vec(), vec(y=-1), self.FlangeAngle )
            .translate( vec(self.BodyOuterDia / 2, 0, z=self.BodyHeight+self.ThreadHeight))
        )

        body = body.cut(thread).cut(upperThread).fuse(flange)
        if False:
            for a in range(0, 340, 30):
                body = body.fuse( tip.copy().rotate(vec(), vec(z=1), a ))

        if self.CutInHalf:
            body= body.common( Part.makeBox(200, 200, 200).translate(vec(-100,0,-100)))


        # adding cuts (holders of the white sheet reflecting the lights forward)
        w, d, h = [150,0.1,40]
        plate = Part.makeBox(w,d,h)
        plate.translate(vec(-w/2))
        plate.rotate(vec(),vec(1),45)
        plate.translate(vec(0,-2/3*self.FilterDia/2, 12))
        # body = body.fuse(plate)
        #return body
        #body = body.cut(plate)

        plate = plate.cut(body)
        plate.rotate(vec(),vec(1),-45)
        return plate

        return body

NAME = "diffuserholder"

doc = FreeCAD.newDocument(NAME)
FreeCAD.setActiveDocument(NAME)


holder = Holder("12")
shape = holder.build()
Part.show(shape)



doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

