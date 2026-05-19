import FreeCAD
from FreeCAD import Base, Vector
import Part
from math import pi, sin, cos

def vec(x=0,y=0,z=0):
    return FreeCAD.Vector(x,y,z)

def polyline(vertices):
    poly = []
    p0 = False
    for v in vertices:
        if p0:
            poly.append(Part.LineSegment(p0, v)) 
        p0 = v
    return poly

def bez(poles):
    curve = Part.BezierCurve()
    curve.setPoles(poles)
    return curve


