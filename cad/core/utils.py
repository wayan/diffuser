import FreeCAD, Part, math

def vec(x=0, y=0, z=0):
    """Creates a FreeCAD.Vector."""
    return FreeCAD.Vector(x, y, z)

def sym_x(p):
    """Symmetrizes a point by the X axis."""
    return vec(-p.x, p.y, p.z)

def sym_y(p):
    """Symmetrizes a point by the Y axis."""
    return vec(p.x, -p.y, p.z)

def sym_z(p):
    """Symmetrizes a point by the Z axis."""
    return vec(p.x, p.y, -p.z)

def lerp(p1, p2, k):
    """Linear interpolation between two points."""
    return p1 * (1 - k) + p2 * k

def lerp_list(p1, p2, ks):
    """Linear interpolation for a list of factors."""
    return [p1 * (1 - k) + p2 * k for k in ks]

def linspace(f, to, n):
    """Generates a list of n+1 evenly spaced numbers between f and to."""
    return [lerp(f, to, i / n) for i in range(n + 1)]

def linspace_minlen(f, to, minlen):
    """Generates a list of evenly spaced numbers with a minimum step length."""
    n = math.ceil(abs(to - f) / minlen)
    return linspace(f, to, n)

def angle_vec(deg, xv=None, yv=None):
    """
    Creates a 2D vector from an angle in degrees.
    Default axes are X and Y.
    """
    r = math.radians(deg)
    return math.cos(r) * (vec(1, 0, 0) if xv is None else xv) + math.sin(r) * (vec(0, 1, 0) if yv is None else yv)

def half_space(x=0, y=0, z=0, l=300):
    """Creates a half-space solid."""
    sx, sy, sz = [
        (0 if d > 0 else (-l if d < 0 else -l / 2)) for d in [x, y, z]
    ]
    box = Part.makeBox(l, l, l).translate(vec(sx, sy, sz))
    return box

def thicken(shp, vec_):
    """Thickens a shape by extruding it along a vector."""
    return shp.extrude(vec_).translate(-vec_ / 2)

def clone_vec(p, x=None, y=None, z=None):
    """Creates a new vector with some of the coordinates of the original vector."""
    return FreeCAD.Vector(
        p.x if x is None else x, p.y if y is None else y, p.z if z is None else z
    )
