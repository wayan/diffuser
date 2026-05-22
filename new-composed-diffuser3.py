"""new-composed-diffuser3.py

    Geometric Model Generation for a Camera Flash Diffuser
"""

import os, sys, FreeCAD, Part, math
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))


import diffuser.model as model
import diffuser.util as du

from diffuser.util import vec, X, Y, Z, O
from diffuser.grid import Grid

def do_stuff(doc):

    P = model.Params( coverConnectedByTabs=False, skipMiddleTab=True)
    diff = model.Model(doc, P)
    g = Grid()
    Part.show(diff.bib, "bib")
    Part.show(diff.BibCone, "bib-cone")
    Part.show(diff.back_plate_complete, "bottom")
    Part.show(diff.bib_mount, "bib-mount")
    Part.show(g.add(diff.unwrap(diff.bib)), "bib-u")
    Part.show(g.add(diff.unwrap(diff.bib_mount)), "bib-um")
    return

    Part.show(diff.BottomComplete, "bottom")
    Part.show(diff.BottomUnwrapped, "bu")
    #Part.show(diff.BottomCone, "bc")
    Part.show(diff.BottomEdge, "ee")



    sidePts = Part.makePolygon(diff.sideCurvePts()).translate(250*X)
    Part.show(sidePts, "sidePts")

    sideCurve = diff.sideCurve().translate(250*X)
    Part.show(sideCurve, "sideCurve")

    Part.show(diff.CoverLeft, "lcover")
    Part.show(diff.CoverRight, "rcover")
    Part.show(diff.BottomComplete, "bottom")
#    Part.show(diff.Diffuser, "diffuser")

#    Part.show(diff.Cover, "cover")

    #Part.show(diff.LensCutSmooth(), "cut-smooth")
    #Part.show(diff.LensCut, "cut")
    Part.show(diff.LensCutExperimental(), "cut")

    
    Part.show(g.add(diff.DiffUnwrapped), "du")
    Part.show(g.add(diff.CoverLeftUnwrapped), "cl")
    Part.show(g.add(diff.CoverRightUnwrapped), "cr")
    Part.show(g.add(diff.BibUnwrapped), "bib-u")

    P2 = model.Params(coverConnectedByTabs=False, bottomCutShallow=True)
    diff2 = model.Model(doc, P2)
    Part.show(g.add(diff.BottomUnwrapped), "bu")
    Part.show( g.add(diff2.BottomUnwrapped), "bu-shallow")

    Part.show( diff.Bib, "bib" )

    return


doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

try:
    # Call the main method on the instance
    do_stuff(doc)
except Exception:
    print(traceback.format_exc())
    sys.exit()

# Close the document
print(f"Closing document: {doc.Label}")

# Quit the FreeCAD application
print("Quitting FreeCAD application...")
