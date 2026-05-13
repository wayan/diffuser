import math
from Diffutil import vec

# transformations on shape and their composition 

class Trans:
    def __init__(self,*fns):
        def apply(shape):
            for fn in fns:
                shape = fn(shape)
            return shape
        self.fn = apply

    def __call__(self, shape):
        return self.fn(shape)

    def __add__(self, other):
        return Trans(self, other)

def cut(other):
    def apply(shape):
        return shape.cut(other)
    return apply

def common(other):
    def apply(shape):
        return shape.common(other)
    return apply

def translate(vec):
    def fn(shape):
        return shape.translate(vec)
    return Trans(fn)

def rot(p0,v0,angle):
    def fn(shape):
        return shape.rotate(p0,v0,angle)
    return Trans(fn)

def fnRev(shape):
    shape.reverse()
    return shape

reverse = Trans(fnRev)

rotate = rot

def rotVec(vf,vt,c=None,vtt=None):
    cross=vf.cross(vt)
    if cross.Length < 0.0001:
        raise Exception("cannot rotate when cross product is zero")
    dot=vf.dot(vt)/(vf.Length*vt.Length)
    angle=math.acos(dot)*180/math.pi
    
    return rot(vec() if c is None else c, cross, angle)

