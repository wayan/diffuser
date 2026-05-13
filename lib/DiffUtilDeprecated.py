import FreeCAD, Part, Mesh, MeshPart, math
# Importing specific items from Diffutil globally since they seem to be utility constants/functions
from Diffutil import vec, X, Y, Z, O
import BOPTools.SplitAPI
import Diffutil as du
import math
import traceback
from functools import reduce, cached_property # <<< ADDED cached_property
import itertools

# unMin, unMax are parameters on the curve normalized to 0..1
def tabBlock(curve, sfc, unMin, unMax, depthMin, depthMax, n=10, rectangular=False):
    """Projects a section of a B-spline curve onto a surface to create a flap face."""
    uMin, uMax = du.betweenList(*curve.ParameterRange, [unMin, unMax])

    # secant is a vector of direction between first and last points on the curve
    secant = (curve.valueAt(uMax) - curve.valueAt(uMin)).normalize()
    uv = sfc.parameter(curve.valueAt((uMin+uMax)/2))
    v1 = sfc.normal(*uv).cross(secant)
    v2 = sfc.tangent(*uv)[1]  # in direction of v

    # 2 rows of points, offset from the surface in the direction normal to the curve on the surface
    ptsMin, ptsMax = [], []

    for outer, pts in [[False, ptsMin],[True, ptsMax]]:
        for k in du.linear_space(0,1,n):
            u = du.between(uMin,uMax,k)
            uv = sfc.parameter(curve.valueAt(u)) 
            depth = depthMin
            if outer:
                depth = depthMax * (1 if rectangular else du.between(0.4, 1, 1 - abs(2*k-1)**2))

            uvp = sfc.parameter(sfc.value(*uv) + depth * secant.cross(sfc.normal(*uv)))
            pts.append( sfc.value( *uvp ) )


    w = Part.Wire([
        # bottom (straight) part
         Part.BSplineCurve(ptsMin).toShape(),
 
         # side part
         Part.makeLine(ptsMin[-1], ptsMax[-1]),
 
         # round part
         Part.BSplineCurve( ptsMax[::-1] ).toShape(),
 
         # side part
         Part.makeLine(ptsMax[0], ptsMin[0] )
    ])


    uv = sfc.parameter(curve.valueAt((uMin+uMax)/2))
    # tangent plane at the middle of the curve
    axis = sfc.normal(*uv)
    pln  = Part.Plane(sfc.value(*uv), axis)
    proj = pln.toShape().project([w])
    f = Part.Face(Part.Wire(proj.SubShapes))
    return du.thicken(f, 10*axis)

# unMin, unMax are parameters on the curve normalized to 0..1
def projectionBlock(curve, sfc, unMin, unMax, depthMin, depthMax, n=10):
    """Projects a section of a B-spline curve onto a surface to create a flap face."""
    us = [ du.between(*curve.ParameterRange, un) for un in du.linear_space(unMin,unMax, n) ]
    uvs  = [ sfc.parameter(curve.valueAt(u)) for u in us ]

    # axis is a vector along the projected curve on the surface
    axis = (sfc.value(*uvs[-1]) - sfc.value(*uvs[0])).normalize()

    # 2 rows of points, offset from the surface in the direction normal to the curve on the surface
    ptsMin, ptsMax = [], []
    for pts, depth in [[ptsMin,depthMin], [ptsMax, depthMax]]:
        for uv in uvs:
            p0 = sfc.value(*uv) + depth * sfc.normal(*uv).cross(axis)
            uvp = sfc.parameter(p0)
            pts.append( sfc.value( *uvp ) )

    poly = Part.Wire([
        Part.BSplineCurve(ptsMin).toShape(),
        Part.makeLine(ptsMin[-1], ptsMax[-1]),
        Part.BSplineCurve(ptsMax[::-1]).toShape(),
        Part.makeLine(ptsMax[0], ptsMin[0])
    ])

    u  = du.between(*curve.ParameterRange, du.between(unMin, unMax, 0.5))
    uv = sfc.parameter(curve.valueAt(u))
    n = sfc.normal(*uv)
    # tangent plane
    pln = Part.Plane(sfc.value(*uv), n)
    proj = pln.toShape().project([poly])
    f = Part.Face(Part.Wire(proj.SubShapes))
    return du.thicken(f, 10*n)


