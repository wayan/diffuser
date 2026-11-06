"""make-crosstrap.py

    Geometric Model Generation for a cross vane trap
"""

import os, sys, traceback, FreeCAD, Part, math
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import crosstrap.model as model
import diffuser.util as du
from diffuser.util import vec, X, Y, Z, O
from diffuser.grid import Grid

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

def show_unwrapped(trap):
    """Show every part laid flat in the XY plane, side by side, clear of the assembled model."""
    g = Grid()
    offset = Y*trap.P.width     # past the assembled model's footprint
    sizes = {}
    for name, shp in trap_parts(trap).items():
        flat = trap.unwrap(shp)
        sizes[name] = flat.BoundBox
        Part.show( g.add(flat).translate(offset), f"{name}-u" )

    print("Unwrapped part dimensions (x × y mm):")
    for name, bb in sizes.items():
        print(f"  {name:12} {bb.XLength:7.1f} × {bb.YLength:7.1f}")

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
