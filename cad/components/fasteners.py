import FreeCAD, Part
from ..core.utils import vec

def nut_pocket(dia, height):
    """Creates a hexagonal nut pocket."""
    r = dia / 2
    poly = Part.makePolygon(
        [
            FreeCAD.Rotation(vec(z=1), angle).multVec(vec(r))
            for angle in range(30, 400, 60)
        ]
    )

    f = Part.Face(Part.Wire(poly)).extrude(vec(0, 0, height)).removeSplitter()
    f.tessellate(0.01)

    edges = [e for e in f.Edges if e.BoundBox.ZLength >= height - 1]
    if edges:
        f = f.makeFillet(0.1, edges)
    return f

def bored_hole(bolt_dia, height):
    """Creates a simple cylindrical hole."""
    return Part.makeCylinder(bolt_dia / 2, height)

def small_nut_pocket(nut_dia, height):
    """Creates a nut pocket for a small nut."""
    return nut_pocket(nut_dia, height)
