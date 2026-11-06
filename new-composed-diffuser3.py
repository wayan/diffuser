"""new-composed-diffuser3.py

    Geometric Model Generation for a Camera Flash diffuser
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
    Part.show(diff.diffuser, "diff")
    Part.show(diff.bib, "bib")
    Part.show(diff.back_plate_complete, "bplate")
    Part.show(diff.sfc_bibroni, "bibroni")
    return

    print(diff.back_plate_point, diff.flash_point)
    print(diff.back_plate_pts[0])
    print("axis", diff.sfc_back_plate.Axis)

    g = Grid()
    Part.show(diff.bib, "bib")

    if False:
        section = diff.cone.section(diff.sfc_bib)

        for i, e in enumerate(section.Edges):
    #        Part.show(e, "E-{i}".format(i=i))
            pts_rim = diff.front_rim.Curve.intersect(e.Curve, 1e-3)
            if len(pts_rim) == 0:
                continue
            pts_bib = diff.bib_edge.Curve.intersect(e.Curve, 1e-3)
            if len(pts_bib) == 0:
                continue

            u_bib, u_rim = ( e.Curve.parameter(vec(pt.X,pt.Y,pt.Z)) for pt in (pts_bib[0], pts_rim[0]))
            ee = e.Curve.toShape(u_bib, u_rim) if u_bib < u_rim else du.reverse_edge(e.Curve.toShape(u_rim, u_bib))

            u_bib0 = ee.Curve.parameterAtDistance(20, ee.FirstParameter)
            u_rim0 = ee.Curve.parameterAtDistance(30, ee.LastParameter)

            ee = ee.Curve.toShape(u_bib0, u_rim0)
            Part.show(ee, "EE-{i}".format(i=i))

    Part.show(diff.front_rim, "front_rim")


    Part.show(diff.bib_cone, "bib-cone")
    Part.show(diff.back_plate_complete, "bottom")
    Part.show(diff.cover_left, "left")
    Part.show(diff.cover_right, "right")
    #Part.show(diff.bib_mount, "bib-mount")
    Part.show(g.add(diff.unwrap(diff.bib)), "bib-u")
    #Part.show(g.add(diff.unwrap(diff.bib_mount)), "bib-um")
    Part.show(g.add(diff.unwrap(diff.back_plate_complete)), "back_plate-un")
    Part.show(g.add(diff.unwrap(diff.diffuser)), "diffuser-un")
    #Part.show(g.add(diff.unwrap(diff.diffuser)), "diff-um")
    #Part.show(g.add(diff.unwrap(diff.cover)), "cover-um")
    return

    Part.show(diff.back_plate_complete, "bottom")
    Part.show(diff.back_plate_unwrapped, "bu")
    #Part.show(diff.Bottomcone, "bc")
    Part.show(diff.back_plate_edge, "ee")



    sidePts = Part.makePolygon(diff.side_curve_pts()).translate(250*X)
    Part.show(sidePts, "sidePts")

    side_curve = diff.side_curve().translate(250*X)
    Part.show(side_curve, "side_curve")

    Part.show(diff.cover_left, "lcover")
    Part.show(diff.cover_right, "rcover")
    Part.show(diff.back_plate_complete, "bottom")
#    Part.show(diff.diffuser, "diffuser")

#    Part.show(diff.cover, "cover")

    #Part.show(diff.lens_cut_smooth(), "cut-smooth")
    #Part.show(diff.lens_cut, "cut")
    Part.show(diff.lens_cut_experimental(), "cut")

    
    Part.show(g.add(diff.diff_unwrapped), "du")
    Part.show(g.add(diff.cover_left_unwrapped), "cl")
    Part.show(g.add(diff.cover_right_unwrapped), "cr")
    Part.show(g.add(diff.bib_unwrapped), "bib-u")

    P2 = model.Params(coverConnectedByTabs=False, backPlateCutShallow=True)
    diff2 = model.Model(doc, P2)
    Part.show(g.add(diff.back_plate_unwrapped), "bu")
    Part.show( g.add(diff2.back_plate_unwrapped), "bu-shallow")

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
