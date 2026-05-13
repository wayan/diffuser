"""filename.py

    Geometric Model Generation for a Camera Flash Diffuser
    This script uses FreeCAD's Python API to generate a 3D model
    of a flash diffuser, focusing on lazy computation of complex geometric
    attributes for efficiency.
"""

import os, sys
# Note: The original script's path modification is kept here,
# assuming 'lib' contains necessary modules like 'Diffutil'.
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import FreeCAD, Part, Mesh, MeshPart, math

import BOPTools.SplitAPI
import traceback

import diffuser.model as model
import diffuser.util as du
import diffuser.tabs as tabs
import diffuser.stitch as stitch

# Importing specific items from Diffutil globally since they seem to be utility constants/functions
from diffuser.util import vec, X, Y, Z, O


Vector2d = FreeCAD.Base.Vector2d


def do_stuff(doc):
    # Create an instance of the class
    spacer = 600

    i = 0

    def translate(o):
        o.translate(-i*spacer*X)

    P = model.Params(
        coverConnectedByTabs=False,
        skipMiddleTab=True
    )
    diff = model.Model(doc, P)

#    Part.show(diff.CoverBackRim, "back-rim")
#    Part.show(Part.makePolygon(diff.coverBackRimPts()), "back-rim-pts")

#    cv = diff.CoverBackRim


#    return


    sidePts = Part.makePolygon(diff.sideCurvePts()).translate(250*X)
    translate(sidePts)
    Part.show(sidePts, "sidePts")

    sideCurve = diff.sideCurve().translate(250*X)
    translate(sideCurve)
    Part.show(sideCurve, "sideCurve")
    #diff.showUnwrapped((i+1)*spacer*X)
    
    Part.show(diff.CoverLeft, "lcover")
    Part.show(diff.CoverRight, "rcover")
    Part.show(diff.BottomComplete, "bottom")
#    Part.show(diff.Diffuser, "diffuser")

#    Part.show(diff.Cover, "cover")

    Part.show(diff.LensCutSmooth(), "cut")

    Part.show(diff.BottomUnwrapped.translate(400*X), "bu")
    Part.show(diff.DiffUnwrapped.translate(400*X+400*Y), "du")
    Part.show(diff.CoverLeftUnwrapped.translate(400*X+800*Y), "cl")
    Part.show(diff.CoverRightUnwrapped.translate(800*X+800*Y), "cr")

    P2 = model.Params(
        coverConnectedByTabs=False,
        bottomCutShallow=True
    )
    diff2 = model.Model(doc, P2)
    Part.show(diff2.BottomUnwrapped.translate(400*X), "bu-shallow")



    return

# --- Execution Block (Kept as is) ---

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
