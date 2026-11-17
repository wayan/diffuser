import math

import diffuser.util as du
from diffuser.util import Z


def landscape_diagonal(bb):
    """rotate_until cost: the bounding box diagonal, for landscape boxes only."""
    return bb.DiagonalLength if bb.XLength >= bb.YLength else math.inf

def paper_fit(long_side, short_side):
    """rotate_until cost: the scale the shape needs to fit a sheet of the given size,
    in either orientation; at most 1 means it fits."""
    def cost(bb):
        a, b = sorted((bb.XLength, bb.YLength), reverse=True)
        return max(a/long_side, b/short_side)
    return cost

A4 = paper_fit(297, 210)

def rotate_until(shp, angles, cost=landscape_diagonal):
    """Rotate shp in place about its center of gravity around Z to the angle from
    angles whose bounding box gives the lowest cost(bb); the first one on ties."""
    c = shp.CenterOfGravity
    minAngle = None
    minCost  = None
    currAngle = 0
    for angle in angles:
        if angle != currAngle:
            shp.rotate(c, Z, angle-currAngle)
        val = cost(shp.BoundBox)
        if minCost is None or val < minCost:
            minAngle = angle
            minCost  = val
        currAngle = angle

    if minAngle != currAngle:
        shp.rotate(c, Z, minAngle-currAngle)
    return shp


def find_ellipse_params(ptTop, ptBottom, aspectRatio):
    # closest ratio A/B
    z0 = ptTop.z
    z1 = ptBottom.z
    x = abs(ptBottom.x)

    minDiff  = None
    zCenter  = None
    for z in du.linspace(z1, z0, 300):
        b = z0 - z
        y = z - z1
        if y >= b or y <= 0:
            continue

        a = x/math.sin(math.acos( (z-z1)/(z0-z)))
        diff = abs(a/(z0-z)-aspectRatio)
        if minDiff is None or diff < minDiff:
            minDiff  = diff
            zCenter     = z

    b = z0 - zCenter
    a = x/math.sin(math.acos( (zCenter-z1)/b))
    return zCenter, a, b
