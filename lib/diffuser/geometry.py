import math

import diffuser.util as du
from diffuser.util import Z


def rotate_until(shp, angles):
    c = shp.CenterOfGravity
    minAngle = None
    minDiag  = None
    currAngle = 0
    for angle in angles:
        if angle != currAngle:
            shp.rotate(c, Z, angle-currAngle)
        bb = shp.BoundBox
        diag = bb.DiagonalLength
        if minDiag is None or (diag < minDiag and bb.XLength >= bb.YLength):
            minAngle = angle
            minDiag  = diag
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
