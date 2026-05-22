"""filename.py

    Geometric Model Generation for a Camera Flash Diffuser
    This script uses FreeCAD's Python API to generate a 3D model
    of a flash diffuser, focusing on lazy computation of complex geometric
    attributes for efficiency.
"""

import os, sys
# Note: The original script's path modification is kept here,
# assuming 'lib' contains necessary modules like 'Diffutil'.
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import FreeCAD, Part, Mesh, MeshPart, math
# Importing specific items from Diffutil globally since they seem to be utility constants/functions
from Diffutil import vec, X, Y, Z, O
import BOPTools.SplitAPI
import math
import traceback
from functools import reduce, cached_property # <<< ADDED cached_property
import itertools

import Diffutil as du
import DiffTabs as tabs

Vector2d = FreeCAD.Base.Vector2d

# constants
LEFT  = "left"
RIGHT = "right" 

def subEdge(e, uns):
    return Part.Edge(e.Curve, *du.betweenList(*e.ParameterRange, uns))

def rotateUntil(shp, angles):
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


# --- Utility Functions (Kept as is) ---
def findEllipseParams(ptTop, ptBottom, aspectRatio):
    # closest ratio A/B
    z0 = ptTop.z 
    z1 = ptBottom.z
    x = abs(ptBottom.x)

    minDiff  = None
    zCenter  = None
    for z in du.linear_space(z1, z0, 300):
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


def circumcenter(A, B, C):
    """Calculates the circumcenter of three points."""
    return Part.ArcOfCircle(A, B, C).Location

class DiffuserModel:
    """
    Class to encapsulate the geometric model generation for a diffuser,
    converting global variables to class properties and functions to methods.
    Uses @cached_property for lazy, single-computation attribute access.
    """

    def __init__(self):
        # Global variables from the original script are now instance properties (attributes)
        self.diffuserConeAngle = 35
        self.diffuserConeAngle = 40
        self.diffuserConeAngle = 33 
        self.diffuserConeAngle = 30 

        self.lensDepth = 67
        self.lensDepth = 37

        self.ellipseRatio = 7/6
        self.ellipseRatio = 4/3
        self.lensCenterHeight = 46.5

        # 30mm
        # self.lensDia = 58
        # 12-40
        self.lensDia = 69

        # Godox flash
        self.topHeight = 195 - self.lensCenterHeight
        self.flashHeadHeight = 33
        self.flashHeadWidth  = 64
        self.flashHeadDepth = 40

        # Meike flash   
        # self.topHeight = 155 - self.lensCenterHeight
        # self.flashHeadHeight = 36


        self.flashHeadSpaceLeft = 0 
        self.flashHeadSpaceUp = 8
        self.frontHeight = self.topHeight + self.flashHeadSpaceUp # - 20


        self.focalPlaneShift = 10
        self.diffThickness   = 0.7
        self.coverThickness  = 1

        self.SensorWidth  = 17.3
        self.SensorHeight = 13.0
        #self.lensFocal    = 30
        self.lensFocal = 14


        self.coverFrontMargin = 8 
        self.coverFoldWidth = 14

        self.snapThickness = 5

        # self.coneTipShift = 270
        # diff.coneTipShift = 140
        self.coneTipShift = 290

        #self.bottomTabWidth = 25 
        self.bottomTabWidth = 25 
        #self.bottomTabStart = 55 
        self.bottomTabStart = 59 

        self.tabCutWidth = 2.5

        # parameter (u) of the part where to cut the cover
        self.coverSplitAt = 0.55

        self.preventTearRadius = 0.3

        self.diffuserFrontTabDepth  = 16
        self.diffuserBottomTabDepth = 20 
        self.diffuserInnerTabDepth  = 15

    @cached_property
    def bottomPoint(self):
        # Point definitions
        return self.lensDia/2*Z - 5*Y
        return O 

    @cached_property
    def flashPoint(self):
        return -self.lensDepth*Y + (self.topHeight - self.flashHeadHeight)*Z

    @cached_property
    def frontTabParams(self):
        n = 5
        width = 20
        first = 80

        rim = self.FrontRim
        fp,lp = rim.FirstParameter, rim.LastParameter

        flapParams = []
        #for l in du.linear_space(first, rim.Length-first, n):
        #    flapParams.append([ rim.Curve.parameterAtDistance(l+k*width/2) for k in [-1,1]])
        s = [0.12, 0.23, 0.37, 0.5]
        for l in du.betweenList(0, rim.Length, s + [1-i for i in s[:-1][::-1]]):
            flapParams.append([ rim.Curve.parameterAtDistance(l+k*width/2) for k in [-1,1]])

        return flapParams

    @cached_property
    def bottomTabParams(self):
        # Flap angles setup
        n = 1
        width = self.bottomTabWidth
        first = self.bottomTabStart

        rim = self.BottomRim
        flapParams = []
        for l in du.linear_space(first, rim.Length-first, n):
            flapParams.append([ rim.Curve.parameterAtDistance(l+k*width/2) for k in [-1,1]])
        return flapParams

    # --- Lazily Computed Properties using @cached_property ---
    @cached_property
    def BottomPlane(self):
        """Builds the construction plane for the bottom block."""
        s = 600
        pt0 = self.bottomPoint
        pt1 = self.flashPoint
        return Part.makePlane(s, s, pt0, X.cross(pt1-pt0)).translate(-s/2*X + (pt1-pt0))

    @cached_property
    def _coneParams(self):
        """Builds the conical shape."""
        pt0 = self.PtDiffuserTop
        pt1 = self.PtDiffuserBottom

        # du.angleVec, -Y, -Z are assumed to be available
        ptTip = pt0 + self.coneTipShift * du.angleVec(self.diffuserConeAngle, -Y, -Z)

        # Uses the circumcenter method
        axis = circumcenter(*[ (p-ptTip).normalize() for p in [pt0, pt1, du.flip_x(pt1) ]])

        A = (pt0-ptTip)
        B = axis
        vDown = 2 * (A.dot(B)/B.dot(B)) * B - A

        depth = 600
        cone = Part.makeLine(ptTip, ptTip + vDown.normalize() * depth).revolve(ptTip, axis, 360)

        return cone, ptTip, axis

    @cached_property
    def Cone(self):
        return self._coneParams[0]

    @cached_property
    def coneTip(self):
        return self._coneParams[1]

    @cached_property
    def coneAxis(self): 
        return self._coneParams[2]

    @cached_property
    def frontEllipse(self):
        e = Part.Ellipse()
        zCenter, e.MajorRadius, e.MinorRadius = findEllipseParams(self.frontHeight*Z, self.PtDiffuserBottom, self.ellipseRatio)
        e.Location = zCenter * Z
        e.Axis = Y
        return e

    @cached_property
    def ConeLimiterEllipse(self):
        """Builds the elliptical cut volume."""
        d = 500
        return Part.Face(Part.Wire(self.frontEllipse.toShape())).translate(-100*Y).extrude(d*Y)

    @cached_property
    def ConeLimiterSideCurve(self):
        sc = self.sideCurve()
        pt0 = sc.valueAt(sc.FirstParameter)
        pt1 = sc.valueAt(sc.LastParameter)
        y   = -300*Y
        f   = Part.Face(Part.Wire([ Part.makeLine(y + pt0.z*Z, pt0), sc, Part.makeLine(pt1, y + pt1.z*Z), Part.makeLine(y + pt1.z*Z, y + pt0.z*Z)  ]))
        ext = 600*X
        return du.thicken(f, ext)

    @cached_property
    def FrontRimEllipse(self):
        e = self.frontEllipse
        pt = (1*self.PtDiffuserBottom).scale(1,0,1)
        p0 = e.parameter(pt)
        p1 = e.parameter(du.flip_x(pt))
        arc =  Part.ArcOfEllipse(e, p1, p0)

        shp = arc.toShape()
        shp.reverse()
        shp.translate(300*Y)
        proj = self.Cone.makeParallelProjection(shp, -Y)
        e = proj.SubShapes[0].Edges[0]
        e.reverse()
        pts = e.discretize(50)
        return Part.BSplineCurve(pts[::-1]).toShape()

    @cached_property
    def FrontRim(self):
        return self.FrontRimSideCurve

    @cached_property
    def ConeLimiter(self):
        return self.ConeLimiterSideCurve

    @cached_property
    def FrontRimSideCurve(self):
        sc = self.sideCurve()
        sc.translate(300*X)
        proj = self.Cone.makeParallelProjection(sc, -X)
        e = proj.SubShapes[0].Edges[0]
        pts = e.discretize(50)

        # points are from -x to x
        if pts[0].x > pts[-1].x:
            pts.reverse()
        return Part.BSplineCurve(pts).toShape()


    @cached_property
    def BottomBlock(self):
        """Builds the solid block that cuts the bottom."""
        depth = 600
        shp = self.BottomPlane
        uMin, uMax, vMin, vMax = shp.ParameterRange
        return shp.extrude(depth * shp.normalAt(du.between(uMin, uMax, 0.5), du.between(vMin, vMax, 0.5)))

    def sideCurve(self):
        return Part.BSplineCurve(self.sideCurvePts()).toShape()

    def sideCurvePts(self):
        pt0 = self.PtDiffuserTop
        pt1 = (1*self.PtDiffuserBottom).scale(0,1,1)
        # top front of the diffuser
        vec = du.angleVec(self.diffuserConeAngle, Y, Z)
        ptFront = pt0 + (self.frontHeight - pt0.z)/vec.z * vec

        # simple curve
        if False:
            pts = [pt1, pt1.z * Z + ptFront.y * Y , ptFront, ptFront + 200 *Z ]

        # curve going slightly down
        down = self.lensDia / 3
        pt1d = pt1 - down*Z
        ptfd = ptFront.y*Y + pt1d.z*Z
        # pts = [pt1, *du.betweenList(pt1d,ptfd,[0.3,0.7]), du.between(ptfd,ptFront,0.6), ptFront, ptFront + 200 *Z ]
        return [pt1, 
                *du.betweenList(pt1d,ptfd,[0.3,0.7]), 
                du.between(ptfd,ptFront,0.55), 
                du.between(ptfd, ptFront, 0.72)-50*Y, 
                du.between(ptfd,ptFront,0.9), 
                ptFront, ptFront + 200 *Z ]

    @cached_property
    def DiffuserBase(self):
        """The main diffuser shape, cut by the ellipse and bottom block."""
        return self.Cone.common(self.ConeLimiter).cut(self.BottomBlock)

    @cached_property
    def BottomRim(self):
        s = self.BottomPlane.section(self.Cone)
        e = s.SubShapes[0]
        pt = self.PtDiffuserBottom
        p0 = e.Curve.parameter(pt)
        p1 = e.Curve.parameter(du.flip_x(pt))
        pts = [ e.valueAt(p) for p in du.linear_space(p0,p1,40) ]
        if pts[0].x < pts[-1].x:
            pts.reverse()
        return Part.BSplineCurve(pts).toShape()

    @cached_property
    def PtSideFlash(self):
        # Flash head profile points
        return self.flashPoint + X*(self.flashHeadWidth/2 + self.flashHeadSpaceLeft)

    def coverBackRimPts(self):
        w  = self.flashHeadWidth

        # Flash head profile points
        pt0 = self.flashPoint - w/2*X - self.flashHeadSpaceLeft*X
        pt1 = pt0 + self.flashHeadHeight*Z 
        pt2 = pt1 + self.flashHeadSpaceUp*Z 
        pts = du.betweenList(pt0,pt1,[0,0.3,0.6,0.8,0.8,1,1,1,1]) + du.betweenList(pt2, du.flip_x(pt2),[0, 0.5]) 

        return pts + [ du.flip_x(p) for p in pts[:-1][::-1]]

    @cached_property
    def CoverBackRim(self):
        """Builds the profile curve for the flash head rim."""
        return Part.BSplineCurve(self.coverBackRimPts()).toShape()

    @cached_property
    def CoverBase(self):
        """Creates the main cover ruled surface, cut by the bottom block."""
        face = Part.makeRuledSurface(self.CoverBackRim, self.FrontRim)
        u_min, u_max, v_min, v_max = face.ParameterRange
        n = 50

        def get_boundary_curve(v, with_margin=False):
            params = du.linear_space(u_min, u_max, n)
            pts = []
            for u in params:
                pt = face.valueAt(u, v)
                if with_margin:
                    # Offset point by the front margin along the V-tangent
                    pt += self.coverFrontMargin * face.tangentAt(u, v)[1]
                pts.append(pt)

            return Part.BSplineCurve(pts).toShape()

        # Rule between the clean back edge and the offset front edge
        return Part.makeRuledSurface(
            get_boundary_curve(v_min, with_margin=False),
            get_boundary_curve(v_max, with_margin=True)
        )

    def diffuserFrontTab(self, ps):
        e = subEdge(self.FrontRim, ps)
        depths = [k*self.diffuserFrontTabDepth for k in [0.3,-1]]
        return tabs.tabFaceCurved(e, self.Cone.Surface, depths)

    @cached_property
    def DiffuserFrontTabs(self):
        return [ self.diffuserFrontTab(ps) for ps in self.frontTabParams ]

    def diffuserBottomTab(self, ps):
        def tabCut(e, right):
            if right:
                target_dist = e.Length - self.tabCutWidth
                u_min = e.Curve.parameterAtDistance(target_dist, e.FirstParameter) 
                u_max = du.between(*e.ParameterRange, 1.1)
            else:
                u_min = du.between(*e.ParameterRange, -0.1)
                u_max = e.Curve.parameterAtDistance(self.tabCutWidth, e.FirstParameter)

            return tabs.tabFaceRec(Part.Edge(e.Curve, u_min, u_max), self.Cone.Surface,  [0, -1.1*self.diffThickness])

        e = subEdge(self.BottomRim, ps)
        depths = [k*self.diffuserBottomTabDepth for k in [0.2, -1]]
        tab = tabs.tabFaceCurved(e, self.Cone.Surface, depths )
        return tab.cut([ tabCut(e,False), tabCut(e,True) ]) 

    @cached_property
    def DiffuserBottomTabs(self):
        return [ self.diffuserBottomTab(ps) for ps in self.bottomTabParams ]

    @cached_property
    def DiffuserFrontInnerTabs(self):
        ftp = self.frontTabParams
        depths = [k*self.diffuserInnerTabDepth for k in [-1,0.3] ]
        return [ tabs.tabInterFace(self.FrontRim, self.Cone.Surface, p,q, depths) for p,q in zip(ftp,ftp[1:]) ]

    @cached_property
    def DiffuserPreventTearCuts(self):
        # omit first and last parameter (u)
        us = [u for p in self.frontTabParams for u in p][1:-1]
        return [ du.circle2d(self.Cone.Surface, self.FrontRim.valueAt(u), self.preventTearRadius) for u in us]

    @cached_property
    def Diffuser(self):
        return self.DiffuserBase.fuse(self.DiffuserFrontTabs + self.DiffuserBottomTabs + self.DiffuserFrontInnerTabs).cut(self.DiffuserPreventTearCuts)

    @cached_property
    def BottomSideLines(self):
        # flaps by the base
        ps = self.CoverBase.ParameterRange
        return [ [ self.CoverBase.valueAt(u,v) for v in ps[2:] ] for u in ps[:2] ]

    @cached_property
    def LensCut(self):
        """Builds the shape used to cut the lens."""
        r = self.lensDia / 2
        h = 400
        down = 200

        shp = Part.Face(Part.makePolygon([-r*X, r*X, r*X-down*Z, -r*X-down*Z, -r*X]))
        # Calls the lens method
        return shp.translate(-h/2*Y).extrude(h*Y).fuse(self.lens)

    @cached_property
    def Bottom(self):
        """Creates the shape of the bottom part."""
        # rim = 15
        rim = 0
        z2 = -self.lensDia/2 - 15
        w = self.flashHeadWidth + 2*self.flashHeadSpaceLeft

        pt1 = self.flashPoint - w/2*X

        orim = self.FrontRim
        pt0 = next((pt for pt in [orim.valueAt(p) for p in [orim.FirstParameter, orim.LastParameter]] if pt.x < 0))
        # Linearly interpolate to z2, then offset by rim*X
        pt2 = pt1 + (pt0-pt1) * (z2-pt1.z)/(pt0.z-pt1.z) - rim*X

        pt1 -= rim*X
        # du.flip_x is assumed to be available
        w = Part.makePolygon([pt2, pt1, du.flip_x(pt1), du.flip_x(pt2), pt2 ])
        w = du.roundCorners(w, [pt2, du.flip_x(pt2)], 8)
        shp = Part.Face(w)
        shp = shp.cut(self.LensCut)
        return shp

    def bottomSideLine(self, i):
        p0, p1 = [ c.valueAt(c.ParameterRange[i]) for c in [self.CoverBackRim, self.FrontRim] ]
        return [ p0, p1 + (p1-p0).normalize() * self.coverFrontMargin ]

    def coverSideLine(self, i):
        uvs = shp.CoverBase.ParameterRange
        return [ self.CoverBase.valueAt(uvs[i], v) for v in uvs[2:] ]

    @cached_property
    def bottomFoldAxis(self):
        pt0, pt1 = self.PtSideFlash, self.PtDiffuserBottom 

        vt = (pt1-pt0).normalize()

        # normal vector is perpendicular to line and to axis of the bottom plane 
        axis = -1*vt.cross(self.BottomPlane.Surface.Axis)

        # axis is rotatated by an angle of 45 back
        rot = FreeCAD.Rotation()
        rot.Angle = math.radians(45)
        rot.Axis  = -vt
        axis      = rot * axis
        return axis

    def makeBottomFlap2(self, flip_x):
        pt0, pt1, axis = self.PtSideFlash, self.PtDiffuserBottom, self.bottomFoldAxis

        if flip_x:
            pt0 = du.flip_x(pt0)
            pt1 = du.flip_x(pt1)
            axis = du.flip_x(axis)

        vt = (pt1-pt0).normalize()

        pln = Part.Plane(pt0, axis)
        v = self.bottomTabWidth * axis.cross(vt)
        if v.y > 0:
            v = -v

        w = Part.makePolygon([pt0,pt0+v,pt1+v, pt1, pt0])
        w = du.roundCorners(w, [pt0+v,pt1+v], 8)
        f = Part.Face(pln, w)

        # holes to connect bottom with the cover
        vn = (1*v).normalize()*self.bottomTabWidth / 2
        r = 0.5
        for pt in du.linear_space(pt0 + vt*15 + vn, pt1 - vt*15 + vn, 2):
            c = Part.Circle()
            c.Axis = axis
            c.Location = pt
            c.Radius = r
            f = f.cut( Part.Face(Part.Wire(c.toShape())) )

        # holes marking the corners
        r = 0.5
        for pt in [pt0, pt1]:
            c = Part.Circle()
            c.Axis = axis 
            c.Location = pt
            c.Radius = r
            f = f.cut( Part.Face(Part.Wire(c.toShape())) )
        return f

    def makeBottomFlapOrig(self, flip_x, reverseNormal):
        pt0, pt1 = self.coverSideLine(0)
        axis = self.bottomFoldAxis
        if flip_x:
            pt0 = du.flip_x(pt0)
            pt1 = du.flip_x(pt1)
            axis = du.flip_x(axis)

        vt = (pt1-pt0).normalize()

        # plane of the flap
        pln = Part.Plane(pt0, axis)
        v = self.bottomTabWidth * (axis.cross(vt))
        if v.y > 0:
            v = -v

        w = Part.makePolygon([pt0,pt0+v,pt1+v, pt1, pt0])
        w = du.roundCorners(w,[pt0+v,pt1+v], 8)
        f = Part.Face(pln, w)

        # holes to connect bottom with the cover
        vn = (1*v).normalize()*self.bottomTabWidth / 2
        pt00 = pt0 + vt*15 + vn
        pt11 = pt1 - vt*15 + vn
        r = 0.5
        for pt in du.linear_space(pt00, pt11, 2):
            c = Part.Circle()
            c.Axis = axis
            c.Location = pt
            c.Radius = r
            f = f.cut( Part.Face(Part.Wire(c.toShape())) )

        # holes marking the corners
        r = 0.5
        for pt in [pt0, pt1]:
            c = Part.Circle()
            c.Axis = axis 
            c.Location = pt
            c.Radius = r
            f = f.cut( Part.Face(Part.Wire(c.toShape())) )
        return f

    def makeCoverFold(self, side):
        self.singleCoverFlap = True

        pt0, pt1 = self.PtSideFlash, self.PtDiffuserBottomMargin
        if side==LEFT:
            pt0 = du.flip_x(pt0)
            pt1 = du.flip_x(pt1)

        vt = (pt1 - pt0).normalize()
        axis = self.BottomPlane.Surface.Axis
        if axis.z > 0:
            axis = - axis

        v = axis * self.snapThickness

        # flap going slightly down
        pts = [pt0,pt0+v,pt1+v, pt1, pt0]
        if side==LEFT:
            pts.reverse()
        f1 = Part.Face(Part.makePolygon(pts))

        # 2 folded flaps at the bottom (is goint to the center)
        v2 = axis.cross(vt) * self.coverFoldWidth 
        if abs(pt0.x+v2.x) > abs(pt0.x-v2.x):
            v2 = -v2

        fromSide = 12

        if self.singleCoverFlap:
            # single flap
            pts = [p + v for p in [pt0, pt0+v2, pt1+v2, pt1, pt0]]
            pc  = pts[1:3]
            if side==LEFT:
                pts.reverse()

            w = du.roundCorners(Part.makePolygon(pts), pc, 6)
            f2 = Part.Face(w)

            f = Part.makeCompound([f1, f2])
        else:
            # two flaps
            ptm  = (pt1+pt0)/2 + fromSide*vt
            pts = [p + v for p in [pt0, pt0+v2, ptm+v2, ptm, pt0]]
            pc  = pts[1:3]
            if side==LEFT:
                pts.reverse()

            w = du.roundCorners(Part.makePolygon(pts), pc, 6)
            f2 = Part.Face(w)

            ptm = pt1 - 2*fromSide*vt
            pts = [p + v for p in [ptm, ptm+v2, pt1+v2, pt1, ptm]]
            pc  = pts[1:3]
            if side==LEFT:
                pts.reverse()

            w = du.roundCorners(Part.makePolygon(pts), pc, 6)
            f3 = Part.Face(w)

            f = Part.makeCompound([f1, f2, f3])

        vpt0 = pt0 + v + v2/2 + fromSide*vt
        vpt1 = pt1 + v + v2/2 - fromSide*vt


        # holes to connect bottom with the cover
        r = 0.5
        for pt in du.linear_space(vpt0, vpt1, 2):
            c = Part.Circle()
            c.Axis = axis
            c.Location = pt
            c.Radius = r
            f = f.cut( Part.Face(Part.Wire(c.toShape())) )

        # holes marking the corners
        r = 0.5
        for pt in [pt0 + v, pt1 + v]:
            c = Part.Sphere()
            c.Center = pt
            c.Radius = r
            f = f.cut( Part.Solid(Part.Shell([c.toShape()])) )
        return f

    def makeCoverHoles(self, flip_x):
        pt0, pt1 = self.PtSideFlash, self.PtDiffuserBottomMargin
        if flip_x:
            pt0 = du.flip_x(pt0)
            pt1 = du.flip_x(pt1)
        vt = (pt1 - pt0).normalize()
        axis = self.BottomPlane.Surface.Axis
        if axis.z > 0:
            axis = - axis

        v = axis * self.snapThickness
        v2 = axis.cross(vt) * self.coverFoldWidth 
        if abs(pt0.x+v2.x) > abs(pt0.x-v2.x):
            v2 = -v2

        vpt0 = pt0 + v + v2/2 + 12*vt
        vpt1 = pt1 + v + v2/2 - 12*vt

        # holes to connect bottom with the cover
        cyls = []
        r = 0.5
        for pt in du.linear_space(vpt0, vpt1, 2):
            c = Part.Circle()
            c.Axis = axis
            c.Location = pt
            c.Radius = r
            cyls.append(Part.Face(Part.Wire(c.toShape())).extrude(-12*axis))

        return cyls

    @cached_property
    def BottomComplete(self):
        """The final bottom shape with cuts for the inner flaps."""
             
        slots = []
        for ps in self.bottomTabParams:
            e = subEdge(self.BottomRim, ps)

            ips = [ e.Curve.parameterAtDistance(l, e.FirstParameter) for l in [self.tabCutWidth, e.Length-self.tabCutWidth] ]

            slots += [
                # thin cut
                tabs.slotFace(e, self.BottomPlane.Surface, self.diffThickness/3),
                # thick cut
                tabs.slotFace( subEdge(e, ips), self.BottomPlane.Surface, self.diffThickness),
            ]

        return self.Bottom.cut(self.makeCoverHoles(False)+self.makeCoverHoles(True)+slots)

    @cached_property
    def CoverStrapCut(self):
        # rectangular cut for the strap
        ptc = self.flashPoint + Z*self.flashHeadHeight*0.1 + 12*Y
        w, h = 3, 18
        pts = [ptc + w*y/2*Y+h*z/2*Z for y,z in [ [-1,-1], [1,-1], [1,1], [-1,1], [-1,-1] ] ]

        f = Part.Face(Part.makePolygon(pts))
        for pt in [ pts[0], pts[3] ]:
            c = Part.Circle()
            c.Radius = w
            c.Location = pt
            c.Axis = X
            f = f.fuse(Part.Face(Part.Wire(c.toShape())))

        return du.thicken(f, X*(self.flashHeadWidth+40))

    def coverFlashFlap(self, side):
        depth = 35
        heightFromBottom =  4
        heightFromTop     = 4
        cv = self.CoverBackRim

        # extrude CoverBackRim backwards and cut from it
        p1, p2 = [ cv.Curve.parameterAtDistance(d) for d in [heightFromBottom,self.flashHeadHeight-heightFromTop]]
        pts = [ cv.valueAt(p1), cv.valueAt(p2) ]
        pts += [pts[1]-depth*Y,pts[0]-depth*Y,pts[0]]

        # "moving" to center (eliminate X)
        pts = [ (1*pt).scale(0,1,1) for pt in pts ]
        w = du.roundCorners(Part.makePolygon(pts), pts[2:4], 5)

        sidevec = X * (100 if side == RIGHT else -100)
        cutter = Part.Face(w).extrude(sidevec)

        # cutting holes for the tightening strap
        strapWidth     = 20
        strapThickness = 2
        strapMargin    = 5
        scutters = []
        for pt in du.betweenList(pts[0], pts[1], [0.35, 0.65]):
            spts = [ pt + j*strapThickness/2*Z - (strapMargin+i*strapWidth)*Y for i,j in [ [0,-1],[1,-1],[1,1], [0,1],[0,-1]]]
            w = du.roundCorners(Part.makePolygon(spts), spts, 0.5)
            scutters.append(Part.Face(w).extrude(sidevec))

        return cv.extrude(-(depth+10)*Y).common(cutter).cut(scutters)

    @cached_property
    def Cover(self):
        """Builds the cover with cuts for the flaps and other features."""

        # Flash head profile points
        # small round cuts to see where the flash is
        pt0 = self.flashPoint + self.flashHeadWidth/2*X
        pt1 = pt0 + Z*(self.flashHeadHeight+2) # + self.flashHeadDepth*Y
        # small round cuts to see where the flash is
        flashMarks = [ Part.makeSphere(2.5).translate(pt) for pt in [pt0, pt1, du.flip_x(pt0), du.flip_x(pt1)] ]

        # rectangular cut for the strap
        # cover = cover.cut( self.CoverStrapCut )
        return self.CoverBase.cut(self.CoverFrontSlots )

        return self.CoverBase.fuse(self.coverFlashFlaps() + [ self.makeCoverFold(side) for side in [LEFT,RIGHT] ]).cut(self.CoverFrontCuts + flashMarks)

    @cached_property
    def SensorCone(self):
        """Builds the sensor cone shape."""
        depth = 300
        vv = self.lensFocal*Y + self.SensorWidth/2*X + self.SensorHeight/2*Z
        vv = vv / vv.y

        # tip of the cone (pyramid)
        yTip = -self.lensDepth - self.focalPlaneShift + self.lensFocal

        shp = Part.makeLoft([
            Part.makePolygon([ v, (1*v).scale(-1,1,1), (1*v).scale(-1,1,-1), (1*v).scale(1,1,-1), v ])
            for v in [ yTip * Y + vv * (y - yTip) for y  in [0, depth]]
            ])
        return shp


    @cached_property
    def CoverFrontSlots(self):
        """Builds the cutting shapes for the cover front flaps."""
        return [ tabs.slotFace(subEdge(self.FrontRim, ps), self.CoverBase.Surface, self.diffThickness) for ps in self.frontTabParams ]

    @cached_property
    def CoverLeft(self):
        return self.coverPart(LEFT)

    @cached_property
    def CoverRight(self):
        return self.coverPart(RIGHT)

    @cached_property
    def CoverLeftUnwrapped(self):
        """Builds the flattened (unwrapped) cover shape."""
        unwrapped = du.unwrapShape(doc, self.CoverLeft)
        rotateUntil(unwrapped, du.linear_space(0,180,30) )
        return unwrapped
        
    @cached_property
    def CoverRightUnwrapped(self):
        """Builds the flattened (unwrapped) cover shape."""
        unwrapped = du.unwrapShape(doc, self.CoverRight)
        rotateUntil(unwrapped, du.linear_space(0,180,30) )
        return unwrapped

    @cached_property
    def CoverUnwrapped(self):
        """Builds the flattened (unwrapped) cover shape."""
        unwrapped = du.unwrapShape(doc, self.Cover)
        rotateUntil(unwrapped, du.linear_space(0,180,30) )
        return unwrapped


    @cached_property
    def DiffUnwrapped(self):
        """Builds the flattened (unwrapped) diffuser shape."""
        unwrapped = du.unwrapShape(doc, self.Diffuser)
        rotateUntil(unwrapped, du.linear_space(0,180,30) )
        return unwrapped

    @cached_property
    def BottomUnwrapped(self):
        """Builds the flattened (unwrapped) bottom shape."""
        unwrapped = du.unwrapShape(doc, self.BottomComplete)
        rotateUntil(unwrapped, du.linear_space(0,180,30) )
        return unwrapped

        # Accesses self.BottomComplete and self.BottomPlane (cached properties)
        b = self.BottomComplete.copy()

        vFrom = self.BottomPlane.Surface.Axis
        vTo   = Z
        b.rotate(b.CenterOfGravity, vFrom.cross(vTo), math.degrees(vFrom.getAngle(vTo)))
        return b

    @cached_property
    def FlashHead(self):
        """Builds the box representing the flash head."""
        w = self.flashHeadWidth
        d = self.flashHeadDepth
        h = self.flashHeadHeight
        box = Part.makeBox(w, d, h)
        box.translate(-w/2*X + (self.topHeight - self.flashHeadHeight)*Z - Y*self.lensDepth)
        return box

    @cached_property
    def Lens(self):
        """Generates the lens shape (a cylinder)."""
        c = Part.Circle()
        c.Radius = self.lensDia / 2
        c.Location = -self.lensDepth * Y
        c.Axis = Y
        return Part.Face(Part.Wire(c.toShape())).extrude(self.lensDepth*Y)

    @cached_property
    def lens(self):
        """Generates the lens shape (a cylinder)."""
        r = self.lensDia / 2
        h = 400

        n = 60
        pts = [ r * du.angleVec(angle, X, Z) for angle in du.linear_space(-90, 270, n) ]

        bez = Part.BSplineCurve(pts, periodic=True).toShape()
        shp = Part.Face(Part.Wire(bez))
        return du.thicken(shp, h*Y)

    @cached_property
    def PtDiffuserTop(self):
        """Calculates a point on the cone's base plane for diffuser_cone2."""
        pt0 = Z*(10 + self.lensDia/2) + 0*Y
        pt0 = Z*( self.lensDia/2) + 0*Y
        # Accesses self.BottomPlane (a cached property)
        pt = self.BottomPlane.Surface.intersect(Part.Line(pt0, pt0 + 100*Y))[0][0]
        return vec(pt.X, pt.Y, pt.Z)

    @cached_property 
    def PtDiffuserBottom(self):
        """Calculates a second point on the cone's base plane for diffuser_cone2."""
        pt1 = -self.lensDia / 5 * Z + (50 + self.lensDia/2)*X
        pt1 = -self.lensDia / 5 * Z + (45 + self.lensDia/2)*X

        # Accesses self.BottomPlane (a cached property)
        pt = self.BottomPlane.Surface.intersect(Part.Line(pt1, pt1 + 100*Y))[0][0]
        return vec(pt.X, pt.Y, pt.Z)

    @cached_property
    def PtDiffuserBottomMargin(self):
        ptUp = self.PtSideFlash
        ptBottom = self.PtDiffuserBottom
        return ptBottom + (ptBottom-ptUp).normalize()*self.coverFrontMargin

    # --- Main Execution Method ---
    def showUnwrapped(self, pt0):
        W,H = 400,300
        pt1 = pt0+W*X  
        pt2 = pt1+H*Y
        pt3 = pt0+H*Y
        Part.show(Part.makePolygon([pt0,pt1,pt2,pt3,pt0]))

        # self.CoverUnwrapped.rotate(O,Z,90)

        bb = self.CoverUnwrapped.BoundBox
        self.CoverUnwrapped.translate(pt0 +5 *X + 5*Y -X*bb.XMin-Y*bb.YMin)
        Part.show(self.CoverUnwrapped, "cover-unwrapped")

        diff = self.DiffUnwrapped
        # diff.rotate(O,Z,110)
        diff.rotate(O,Z,90)
        bb = diff.BoundBox
        self.DiffUnwrapped.translate(pt0 + 5*Y + 525*X -X*bb.XMin-Y*bb.YMin)
        Part.show(self.DiffUnwrapped, "diff-unwrapped")

        bt = self.BottomUnwrapped
        #bt.rotate(O,Z,180)
        #bt.rotate(O,Z,90)
        bb = self.BottomUnwrapped.BoundBox
        self.BottomUnwrapped.translate(pt0 + 285*X + 343*Y -X*bb.XMin-Y*bb.YMin)
        Part.show(self.BottomUnwrapped, "bottom-unwrapped")

    def solids(self):
        return [ self.Cover, self.BottomComplete, self.Diffuser, self.FlashHead]

    def coverPart(self, side):
        return self.coverPartStitchLongitude(side)

    def coverPartStitchLongitude(self, side):
        # parameters
        tabCount = 3
        tabIndent = 20
        margin = 10 
        dentWidth = 8 

        uvs = self.CoverBase.ParameterRange
        u = du.between(*uvs[:2], self.coverSplitAt)
        axis = self.CoverBase.normalAt(u, du.between(*uvs[2:],0.5))
        pMin, pMax = [self.CoverBase.valueAt(u,v) for v in uvs[2:]]

        # Matrix defines the split plane: X along the split, Y perpendicular to it
        mx = FreeCAD.Matrix()
        xv = (pMax-pMin).normalize()
        mx.setCol(0, xv)
        mx.setCol(1, axis.cross(xv))
        mx.move(pMin+tabIndent*xv)

        xl = (pMax-pMin).Length - 2*tabIndent
        tabWidth = xl/(2*tabCount-1)
        spaceWidth = tabWidth

        def baseByCommon():
            y = margin if side==RIGHT else 0
            # creating halfspace bigenough
            big = 600
            l0, l1 = [ mx*vec(x,y) - big/2*Z  for x in [-big,big]] 
            pts = [l0,l1,l1+big*Z,l0+big*Z,l0]
            hs = Part.Face(Part.makePolygon(pts)).extrude(big*(1 if side==RIGHT else -1)*X)
            return self.Cover.common(hs)

        base = baseByCommon


        corners = [[-1,0],[1,0],[1,1],[-1,1],[-1,0]]
        sfc = self.CoverBase.Surface

        if side == LEFT:

            faces = []
            for t in range(0, tabCount):
                # center of the tab
                xc = t*(tabWidth + spaceWidth) + tabWidth/2 

                # left part is the single long slot 
                pts = []
                for i,j in corners:
                    pt = mx*vec(xc+i*tabWidth/2 -dentWidth*(1 if i < 0 else 0), margin + j*self.diffThickness) 
                    pts.append( Vector2d( *sfc.parameter(pt) ))

                # cutting the edges
                segs = [ Part.Geom2d.Line2dSegment(p,q) for p,q in zip(pts,pts[1:]) ]
                w = Part.Wire([ seg.toShape(sfc) for seg in segs ])
                faces.append( Part.Face(sfc, w) )
            return base().fuse([self.makeCoverFold(side), self.coverFlashFlap(side)]).cut(faces)

        # right
        faces = []
        faceCuts = []
        dentXXX = 10
        for t in range(0, tabCount):
            # right part - tab
            xc = t*(tabWidth + spaceWidth) + tabWidth/2

            pts = []
            for i,j in corners:
                pt = mx*vec(xc + i*tabWidth/2 + dentWidth*(1 if i > 0 else 0), margin + j*dentXXX + (0 if j>0 else -0.3*dentXXX)) 
                pts.append( Vector2d( *sfc.parameter(pt) ))

            # cutting the edges
            segs = [
                *du.poly2d(pts[:2]),
                du.bez2d(du.betweenList(*pts[1:3], [0, 0.3,1 ]) + du.betweenList(*pts[2:4], [0.3,0.7]) + du.betweenList(*pts[3:5], [0,0.7,1]))
            ]
            #segs = [ Part.Geom2d.Line2dSegment(p,q) for p,q in zip(pt2s,pt2s[1:]) ]
            w = Part.Wire([ seg.toShape(sfc) for seg in segs ])
            faces.append( Part.Face(sfc, w) )

            pts = []
            cutWidth = 1.2*self.diffThickness
            for i,j in corners:
                pt = mx*vec(xc + tabWidth/2 + dentWidth*(1.1 if i > 0 else 0), margin + j*cutWidth) 
                pts.append( Vector2d( *sfc.parameter(pt) ))

            w = Part.Wire([ seg.toShape(sfc) for seg in du.poly2d(pts) ])
            faceCuts.append( Part.Face(sfc, w) )

        return base().fuse([self.makeCoverFold(side), self.coverFlashFlap(side)] + faces).cut(faceCuts)

    def coverPartStitchLatitude(self, side):
        # parameters
        tabCount = 2
        tabIndent = 20
        margin = 15 
        dentWidth = 4 
        dentHeight = 3 
        tabHeight = 15
        # how much the parts overlap
        overlap = 5
        tolerance = 0.001
        stemTolerance = 1

        uvs = self.CoverBase.ParameterRange
        u = du.between(*uvs[:2], self.coverSplitAt)
        axis = self.CoverBase.normalAt(u, du.between(*uvs[2:],0.5))
        pMin, pMax = [self.CoverBase.valueAt(u,v) for v in uvs[2:]]

        # Matrix defines the split plane: X along the split, Y perpendicular to it
        mx = FreeCAD.Matrix()
        xv = (pMax-pMin).normalize()
        mx.setCol(0, xv)
        mx.setCol(1, axis.cross(xv))
        mx.move(pMin+tabIndent*xv)

        xl = (pMax-pMin).Length - 2*tabIndent
        tabWidth = xl/(tabCount+1)
        spaceWidth = tabWidth

        def thicken(shp):
            h = 20
            return du.thicken(shp, h*axis)

        tabStemHeight = margin - overlap - dentHeight + stemTolerance

        def baseBySplit():
            # build part
            y = overlap if side==RIGHT else 0
            cutter = thicken(Part.makeLine(*[ mx*vec(x,y) for x in [-tabIndent-15,xl+tabIndent+15]])) 
            shapes = BOPTools.SplitAPI.slice(self.Cover, [cutter], mode="Standard", tolerance=tolerance).SubShapes
            return Part.makeCompound([shp for shp in shapes if (side==RIGHT)==(shp.CenterOfGravity.x >= 0)])

        def baseByCommon():
            y = overlap if side==RIGHT else 0
            # creating halfspace bigenough
            big = 600
            l0, l1 = [ mx*vec(x,y) - big/2*Z  for x in [-big,big]] 
            pts = [l0,l1,l1+big*Z,l0+big*Z,l0]
            hs = Part.Face(Part.makePolygon(pts)).extrude(big*(1 if side==RIGHT else -1)*X)
            return self.Cover.common(hs)

        base = baseByCommon

        wires = []

        for t in range(0, tabCount):
            w2 = 0.5*tabWidth
            corners = [[-1,0],[1,0],[1,1],[-1,1],[-1,0]]
            # center of the tab
            xc = t*(tabWidth + spaceWidth) + w2

            if side==RIGHT:
                # right part - tab

                # the stem (it is made quite thicker)
                tolerance = 0.05
                stemCorners = [[-1,-tolerance],[1,-tolerance],[1,1+tolerance],[-1,1+tolerance],[-1,-tolerance]]
                pts = [ mx*vec(xc+i*(w2-dentWidth), overlap+j*tabStemHeight) for i,j in stemCorners ]
                wires.append(Part.makePolygon(pts)) 

                pts = [ mx*vec(xc+i*w2, overlap+tabStemHeight+j*tabHeight) for i,j in corners ]
                poly = Part.makePolygon(pts)
                wires.append(du.roundCorners(poly, pts[2:4], 0.7*tabHeight)) 
            else:
                # left part - slot

                # cuts on the left side
                pts = [ mx*vec(xc+i*w2, margin + j*self.diffThickness) for i,j in corners ]
                # cut to insert the other part
                wires.append(Part.makePolygon(pts)) 

                # narrower cut
                pts = [ mx*vec(xc+i*(w2-dentWidth), margin - j*dentHeight) for i,j in corners ]
                wires.append(Part.makePolygon(pts)) 

        shapes = [ thicken(Part.Face(w)) for w in wires]

        b = base().fuse([self.makeCoverFold(side), self.coverFlashFlap(side)])

        if side==RIGHT:
            return b.fuse([ self.CoverBase.common(shp) for shp in shapes])
        else:
            return b.cut(shapes)

def coneTriangle(self):
    pt0 = diff.coneTip + diff.coneAxis*550 - 250*X
    f = Part.Face(Part.makePolygon([diff.coneTip, pt0, du.flip_x(pt0), diff.coneTip]))
    return f

def do_stuff(doc):
    # Create an instance of the class
    spacer = 600

    i = 0

    def translate(o):
        o.translate(-i*spacer*X)

    diff = DiffuserModel()

#    Part.show(diff.CoverBackRim, "back-rim")
#    Part.show(Part.makePolygon(diff.coverBackRimPts()), "back-rim-pts")

#    cv = diff.CoverBackRim


#    return


    #sidePts = Part.makePolygon(diff.sideCurvePts()).translate(250*X)
    #translate(sidePts)
    #Part.show(sidePts, "sidePts")
    #diff.showUnwrapped((i+1)*spacer*X)
    
    Part.show(diff.CoverLeft, "lcover")
    Part.show(diff.CoverRight, "rcover")
#    Part.show(diff.BottomComplete, "bottom")
#    Part.show(diff.Diffuser, "diffuser")


    Part.show(diff.BottomUnwrapped.translate(400*X), "bu")
    Part.show(diff.DiffUnwrapped.translate(400*X+400*Y), "du")
    Part.show(diff.CoverLeftUnwrapped.translate(400*X+800*Y), "cl")
    Part.show(diff.CoverRightUnwrapped.translate(800*X+800*Y), "cr")


    return

# --- Execution Block (Kept as is) ---

doc = FreeCAD.newDocument()
FreeCAD.setActiveDocument(doc.Name)


try:
    # Call the main method on the instance
    do_stuff(doc)
except Exception:
    print(traceback.format_exc())
    sys.exit()

# Close the document
print(f"Closing document: {doc.Label}")

# Quit the FreeCAD application
print("Quitting FreeCAD application...")
