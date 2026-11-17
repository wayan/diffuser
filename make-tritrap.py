"""make-tritrap.py

    Geometric Model Generation for a three vane trap
"""

import os, sys, traceback, FreeCAD, Part
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import tritrap.model as model
from diffuser.util import Y
from diffuser.grid import Grid

def trap_parts(trap):
    """All parts of the trap by name, in their assembled position."""
    parts = {}
    for i, vane in enumerate(trap.vaneParts, 1):
        parts[f"vane{i}"] = vane
    for i, funnel in enumerate(trap.funnelParts, 1):
        parts[f"funnel{i}"] = funnel
    center, *slices = trap.topParts
    parts["topCenter"] = center
    for i, s in enumerate(slices, 1):
        parts[f"top{i}"] = s
    return parts

def show_unwrapped(trap):
    """Show every part laid flat in the XY plane, side by side, clear of the
    assembled model, and print the size of each."""
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


doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)

try:
    do_stuff(doc)
except Exception:
    print(traceback.format_exc())
    sys.exit()

print(f"Closing document: {doc.Label}")
print("Quitting FreeCAD application...")
