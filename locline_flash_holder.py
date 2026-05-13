"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
from Diffutil import vec, halfSpace
import Diffutil as df


# END OF "IMPORT"

class Holder:

    def __init__(self):
        self.Cuts = True
        holeTolerance = 1.007
        # radius of M4 Nut
        self.NutDia = 7.8 * holeTolerance
        self.NutHeight = 3.4 * holeTolerance 

        # radius of hole (m4)
        self.BoltDia  = 4.2
        # radius of hole (m5)
        #self.BoltDia  = 5.5
        return

    def maleThread(self, dia, pitch, height):
        h = height 
        outer = dia  / 2
        inner, iinner, oouter = [
            outer + ( k / 8 * pitch * sin(Math.pi / 3) )
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

    def smallNutPocket(self, height = None):
        return df.nutPocket(self.NutDia, height if height != None else self.NutHeight)

    def coldShoe(self, h1=5):
        # body holding the flash

        # width of the metal part of the flash
        wf = 18.9

        w0 = wf + 2 * 4
        w2 = 12.8

        # dent on the bottom for pins
        wDent = 9
        hDent = 2

        h2 = 2.6
        # thickness of the metal part of the cold shoe
        h3 = 1.5 - 0.2


        # outer width and depth 
        wo = wf + 2 * 5 
        do = wo 

        k = 1/2
        pts = [ [0, -do/2], [-k*wo/2, -do/2], [-wo/2, -do/2 ], [-wo/2, -k*do/2], [-wo/2, k*do/2], [-wo/2,do/2], [-k*wo/2,do/2] ]
        bez = Part.BSplineCurve([ vec(x,y) for x,y in pts + [[0,do/2]]] + [ vec(-x,y) for x,y in  pts[::-1]], periodic=True)

        h = h1 + h2 + h3
        body = Part.Face(Part.Wire(Part.Shape([bez]))).extrude(vec(0,0,h))

        # cut
        wi = w2 
        di = do - 8
        print("di=" , di, ",do=", do)
        pts = [ [-wo/2,-do/2], [-wi/2,-di/2], [-wi/2, -di/3], [-wi/2,0], [-wi/2,di/2] ]
        bez = Part.BSplineCurve([vec(x,y) for x,y in pts + [[0,di/2]]] + [ vec(-x,y) for x,y, in pts[::-1]])

        parts = [ Part.Shape([bez]), Part.makeLine( vec(wo/2, -do/2 ), vec(-wo/2,-do/2)) ]

        cut   = Part.Face(Part.Wire(parts)).extrude(vec(0,0,h)).translate(vec(0,0,h1))
        body = body.cut(cut)

        # dent for the flash
        cut = Part.makeBox(wf, do - 4, h2).translate(vec(-wf/2, -do/2, h1))
        body = body.cut(cut)

        # dent for the pins
        cut = Part.makeBox(wDent, (do + di)/2, hDent).translate(vec(-wDent/2, -do/2, h1-hDent))
        body = body.cut(cut)
        return body


    def build(self, cuts=True, outer=True):
        body = self.coldShoe()

        # locline holder
        # diameter of the small sphere
        diaSphere = 21.5 + (-0.2 if outer else 0.2)
        # diameter of the circle cut from small sphere in bottom
        diaBottom = 20.5 - 0.3
        # diameter of the circle cut from small sphere in top
        diaTop = 15
        thickness = 2 

        hStem = 4 

        hBottom, hTop = [ math.sqrt(diaSphere*diaSphere - dia*dia) / 2 for dia in [diaBottom, diaTop]]

        if outer:
            rIn = diaSphere / 2
            rOut = rIn + thickness
            rc = math.sqrt(rOut*rOut - hTop*hTop)
        else:
            rOut = diaSphere / 2
            rIn  = rOut - thickness
            rc = diaTop / 2
            
        s = Part.makeSphere(rOut ).cut( Part.makeSphere(rIn) )

        l = 100
        s = s.cut(Part.makeBox(l,l,l).translate(vec(-l/2,-l/2,-l - hBottom)))
        s = s.cut(Part.makeBox(l,l,l).translate(vec(-l/2,-l/2,hTop)))
        s = s.fuse(Part.makeCylinder(rc,hStem).translate( vec(0,0,hTop) ))
        s = s.fuse(body.translate(vec(0,0,hTop + hStem)))

        if cuts:
            cw = 3 
            ch = 3 *hTop / 3
            pts = [ vec(x,0,z) for x,z in [ [-cw/2, -rOut/2], [-cw/2, ch], [cw/2, ch],[cw/2,-rOut/2] ]]
            shp = Part.Face(Part.Wire(Part.Shape([Part.BSplineCurve(pts, periodic=True)]))).extrude(vec(0,30,0))
            m = None
            for a in [60,180,300]:
                dent = shp.copy().rotate(vec(),vec(0,0,1),a)
                m = m.fuse(dent) if m != None else dent
            s = s.cut(m)

        # bolt hole
        s = s.cut(Part.makeCylinder(self.BoltDia/2, 40))
        s = s.cut(self.smallNutPocket(40).translate(vec(0,0,hTop + 2)))
        return s

    def withLocline(self, elem, outer, shift=0, cuts=0):
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

        shp = shp.fuse( self.coldShoe(8) )
        # bolt hole
        shp = shp.cut(Part.makeCylinder(self.BoltDia/2, 40))
        t = 2
        shp = shp.cut(self.smallNutPocket(40).translate(vec(0,0,t)))
        return shp



loclineElem = df.loadLocLineElement()


doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

h = Holder()
# for cuts in [False, True]:
#     for outer in [True, False]:
#         shp = h.build(cuts, outer).translate(vec(50 if cuts else 0, 50 if outer else 0))
#         Part.show(shp, "mine_" + ("outer" if outer else "inner") + "_" + ("cutted" if cuts else "plain") )

i = 0
for outer in [True, False]:
    j = 0
    for shift in ( [0.2, 0.4, 0.6, 0.8] if outer else [-0.2, -0.4, -0.6, -0.8]):
        k = 0
        for cuts in [0,3,4]:
            shp = h.withLocline(loclineElem, outer, shift, cuts)
            shp.translate( vec(50 *i + 150*k, 50 * j))
            name = "locline-" + ("outer" if outer else "inner") 
            if shift != 0:
                name = name + "-"+ ("bigger" if shift > 0 else "smaller") + str(abs(shift)) 
            if cuts != 0:
                name = name + "-"+ ( str(cuts) + "cuts") 
            obj = Part.show(shp, name)
            Part.export([obj],"/home/danielr/desticka_k_blesku/"  + name + ".STEP")
            k = k + 1
        j = j + 1
    i = i + 1

doc.recompute()
Gui.SendMsgToActiveView("ViewFit")
Gui.activeDocument().activeView().viewIsometric()

