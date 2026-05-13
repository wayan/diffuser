import FreeCAD, Part, math
from FreeCAD import Base, Vector
from .utils import vec, angleVec, linspace

Vector2d = FreeCAD.Base.Vector2d

def new_polyline(lst):
    n = Polyline()
    n.lst = lst
    return n

class Polyline:
    """A helper class for creating sequences of connected lines (polylines)."""

    def __init__(self, *pts):
        self.lst = []
        if len(pts) > 0:
            self.add(*pts)

    def __iter__(self):
        return iter(self.lst)

    def __add__(self, it):
        return new_polyline(self.lst + [p for p in it])

    def __iadd__(self, other):
        self.lst += [line for line in other]
        return self

    def rev(self, fn=None):
        """Reverses the order of the lines and the points within each line."""
        n = new_polyline([list(reversed(l)) for l in reversed(self.lst)])
        return n if fn is None else n.map(fn)

    def add(self, *pts):
        """Adds a new line segment, starting from the last point of the previous segment."""
        line = ([self.lst[-1][-1]] if len(self.lst) > 0 else []) + list(pts)
        if len(line) < 2:
            raise Exception("Sorry, the line added does not contain two points")
        self.lst.append(line)
        return self

    def add_broken(self, *pts):
        """Adds a sequence of connected line segments."""
        l = list(pts)
        if len(self.lst) == 0:
            self.add(l[0], l[1])
            l = l[2:]

        for p in l:
            self.add(p)
        return self

    def map(self, fn):
        """Applies a function to each point in the polyline."""
        return new_polyline([[fn(p) for p in line] for line in self])

    def to_wire(self):
        """Converts the polyline to a Part.Wire object."""
        return Part.Wire([Part.makeLine(*l) if len(l) == 2 else Part.BSplineCurve(l).toShape() for l in self])

def create_polyline(vertices):
    """Creates a polyline from a list of vertices."""
    poly = []
    p0 = False
    for v in vertices:
        if p0:
            poly.append(Part.LineSegment(p0, v))
        p0 = v
    return poly

def create_bezier(poles):
    """Creates a Bezier curve from a list of poles."""
    curve = Part.BezierCurve()
    curve.setPoles(poles)
    return curve

def create_rect_xz(w, h):
    """Creates a rectangle in the XZ plane."""
    return Part.Face(Part.makePolygon([vec(), vec(w), vec(w, z=h), vec(z=h), vec()]))

def get_ortho_rect_pts(p1, p3):
    """
    Calculates the points of a rectangle in an orthogonal plane
    defined by two corner points.
    """
    p2, p4 = [vec(p.x, p.y, p.z) for p in [p1, p1]]
    if p1.x == p3.x:
        p2.y = p3.y
        p4.z = p3.z
    elif p1.y == p3.y:
        p2.x = p3.x
        p4.z = p3.z
    elif p1.z == p3.z:
        p2.x = p3.x
        p4.y = p3.y
    else:
        raise Exception("Sorry, the points do not lie in X, Y, or Z planes")
    return [p1, p2, p3, p4, p1]

def create_ortho_rect_poly(p1, p3):
    """Creates a rectangular polygon in an orthogonal plane."""
    return Part.makePolygon(get_ortho_rect_pts(p1, p3))

def create_ortho_rect_face(p1, p3):
    """Creates a rectangular face in an orthogonal plane."""
    return Part.Face(create_ortho_rect_poly(p1, p3))

def create_circle_2d(sfc, center, r, n=10):
    """Creates a 2D circle on a surface."""
    uv = sfc.parameter(center)
    x, y = [r * v for v in sfc.tangent(*uv)]

    def pt2(angle):
        pt = center + angleVec(angle, x, y)
        return Vector2d(*sfc.parameter(pt))

    bez = Part.Geom2d.BSplineCurve2d()
    bez.buildFromPoles([pt2(a) for a in linspace(0, 360, n)], True)
    w = Part.Wire([bez.toShape(sfc)])
    return Part.Face(sfc, w)
