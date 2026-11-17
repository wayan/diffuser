"""make-crosstrap.py

    Geometric Model Generation for a cross vane trap
"""

import os, sys, traceback, FreeCAD, Part, math
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import crosstrap.model as model
import diffuser.util as du
from diffuser.util import vec, X, Y, Z, O
from diffuser.grid import Grid
from diffuser.geometry import A4, landscape_diagonal

def trap_parts(trap):
    """All parts of the trap by name, in their assembled position."""
    parts = {
        "vaneXZ": trap.vaneXZ,
        "vaneYZ": trap.vaneYZ,
        "connectorYZ": trap.connectorYZ,
        "top": trap.topPart,
    }
    for i, funnel in enumerate(trap.funnelParts, 1):
        parts[f"funnel{i}"] = funnel
    return parts

def flat_only_parts(trap):
    """Parts shown only laid flat, not in the assembled model."""
    return {"funnelHalf": trap.funnelHalfPart}

# sheets the unwrapped parts are turned to fit, by part name
PAPER = {"funnelHalf": ("A4", A4)}

def x_length(bb):
    """rotate_until cost: the bounding box width along X."""
    return bb.XLength

def unwrap_cost(name):
    """How an unwrapped part is turned: to fit its sheet, the funnel segments to be
    narrowest along X, the rest to a compact box."""
    if name in PAPER:
        return PAPER[name][1]
    if name.startswith("funnel"):
        return x_length
    return landscape_diagonal

def show_unwrapped(trap):
    """Show every part laid flat in the XY plane, side by side, clear of the assembled model."""
    g = Grid()
    offset = Y*trap.P.width     # past the assembled model's footprint
    sizes = {}
    for name, shp in (trap_parts(trap) | flat_only_parts(trap)).items():
        flat = trap.unwrap(shp, unwrap_cost(name))
        sizes[name] = flat.BoundBox
        Part.show( g.add(flat).translate(offset), f"{name}-u" )

    print("Unwrapped part dimensions (x × y mm):")
    for name, bb in sizes.items():
        line = f"  {name:12} {bb.XLength:7.1f} × {bb.YLength:7.1f}"
        if name in PAPER:
            paper, cost = PAPER[name]
            line += f"   {paper} fit {cost(bb):.3f} ({'fits' if cost(bb) <= 1 else 'too big'})"
        print(line)

def do_stuff(doc):
    P = model.Params()
    trap = model.Model(doc, P)

    for name, shp in trap_parts(trap).items():
        Part.show( shp, name )
    show_unwrapped(trap)
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
