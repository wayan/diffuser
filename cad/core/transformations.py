import math
from .utils import vec

class Transformation:
    """A class for composing transformations on shapes."""

    def __init__(self, *fns):
        def apply(shape):
            for fn in fns:
                shape = fn(shape)
            return shape
        self.fn = apply

    def __call__(self, shape):
        return self.fn(shape)

    def __add__(self, other):
        return Transformation(self, other)

def cut(other):
    """Creates a cut transformation."""
    def apply(shape):
        return shape.cut(other)
    return apply

def common(other):
    """Creates a common transformation."""
    def apply(shape):
        return shape.common(other)
    return apply

def translate(vector):
    """Creates a translation transformation."""
    def fn(shape):
        return shape.translate(vector)
    return Transformation(fn)

def rotate(p0, v0, angle):
    """Creates a rotation transformation."""
    def fn(shape):
        return shape.rotate(p0, v0, angle)
    return Transformation(fn)

def _fn_rev(shape):
    shape.reverse()
    return shape

reverse = Transformation(_fn_rev)

def rotate_vec(vf, vt, c=None):
    """
    Creates a rotation transformation that rotates a vector `vf` to `vt`.
    """
    cross = vf.cross(vt)
    if cross.Length < 0.0001:
        raise Exception("Cannot rotate when the cross product is zero")
    dot = vf.dot(vt) / (vf.Length * vt.Length)
    angle = math.acos(dot) * 180 / math.pi
    
    return rotate(vec() if c is None else c, cross, angle)
