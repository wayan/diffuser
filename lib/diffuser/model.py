import FreeCAD, Part, Mesh, MeshPart, math

import BOPTools.SplitAPI
import itertools

# Importing specific items from Diffutil globally since they seem to be utility constants/functions
from dataclasses import dataclass, field
from functools import cached_property # <<< ADDED cached_property
from collections import namedtuple

import diffuser.util as du
import diffuser.tabs as dt
from diffuser.util import vec, X, Y, Z, O
import diffuser.stitch as st 

Vector2d = FreeCAD.Base.Vector2d

# constants
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



@dataclass
class Params:
    """Data-only class to hold diffuser parameters."""
    # diffuserConeAngle: float = 30
    diffuserConeAngle: float = 32

    lensDepth: float = 37
    ellipseRatio: float = 4/3
    #lensDia: float = 69
    lensDia: float = 70.5 
    flashHeadHeight: float = 33
    flashHeadWidth: float = 64
    flashHeadDepth: float = 40
    flashHeadSpaceLeft: float = 0
    flashHeadSpaceUp: float = 8
    focalPlaneShift: float = 10
    diffThickness: float = 0.7
    coverThickness: float = 1
    SensorWidth: float = 17.3
    SensorHeight: float = 13.0
    lensFocal: float = 14
    coverFrontMargin: float = 8
    coverFoldWidth: float = 14
    snapThickness: float = 5
    coneTipShift: float = 290
    bottomTabWidth: float = 25
    bottomTabStart: float = 59
    tabCutWidth: float = 2.5
   # coverSplitAt: float = 0.55
    coverSplitAt: float = 0.5415
    preventTearRadius: float = 0.3

    # tabs
    diffuserFrontTabDepth: float = 16
    diffuserBottomTabDepth: float = 20
    diffuserInnerTabDepth: float = 15

    coverConnectedByTabs: bool = False
    coverNumTabs: int = 3

    # calculated fields
    topHeight: float = field(init=False)
    frontHeight: float = field(init=False)

    # cover stitch
    coverStitchNumTabs: int = 3
    coverStitchTabIndent: float = 20
    coverStitchMargin: float = 10 
    coverStitchShift: float = 8
    coverStitchTabHeight: float = 10

    # bottom stitch(es)
    bottomStitchNumTabs: int = 3
    bottomStitchTabIndent: float = 20
    bottomStitchMargin: float = 10 
    bottomStitchShift: float = 8
    bottomStitchTabHeight: float = 10
    bottomCutShallow: bool = False
    skipMiddleTab: bool = False

    def __post_init__(self):
        # Godox flash
        lensCenterHeight = 46.5
        self.topHeight = 195 - lensCenterHeight
        # Meike flash   
        # self.topHeight = 155 - self.lensCenterHeight
        # self.flashHeadHeight = 36

        # top is flat
        self.frontHeight = self.topHeight + self.flashHeadSpaceUp # - 20

class Model:
    """
    Class to encapsulate the geometric model generation for a diffuser,
    converting global variables to class properties and functions to methods.
    Uses @cached_property for lazy, single-computation attribute access.
    """

    def __init__(self, doc, P):
        """Initializes the model by creating a parameter object."""
        self.doc = doc
        self.P = P

    @cached_property
    def bottomPoint(self):
        # Point definitions
        return self.P.lensDia/2*Z - 5*Y

    @cached_property
    def flashPoint(self):
        return -self.P.lensDepth*Y + (self.P.topHeight - self.P.flashHeadHeight)*Z

    @cached_property
    def frontTabParams(self):
        n = 5
        width = 20
        first = 80

        rim = self.FrontRim
        ps = []
        #for l in du.linspace(first, rim.Length-first, n):
        #    flapParams.append([ rim.Curve.parameterAtDistance(l+k*width/2) for k in [-1,1]])
        s = [0.12, 0.23, 0.37, 0.5]
        for l in du.lerp_list(0, rim.Length, s + [1-i for i in s[:-1][::-1]]):
            ps.append([ rim.Curve.parameterAtDistance(l+k*width/2, rim.FirstParameter) for k in [-1,1]])

        if self.P.skipMiddleTab:
            ps.pop(len(ps)-3)
            ps.pop( 2)

        return ps

    @cached_property
    def bottomTabParams(self):
        # Flap angles setup
        n = 1
        width = self.P.bottomTabWidth
        first = self.P.bottomTabStart

        rim = self.BottomRim
        flapParams = []
        for l in du.linspace(first, rim.Length-first, n):
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
        ptTip = pt0 + self.P.coneTipShift * du.angleVec(self.P.diffuserConeAngle, -Y, -Z)

        # Uses the circumcenter method
        axis = du.circumcenter(*[ (p-ptTip).normalize() for p in [pt0, pt1, du.symX(pt1) ]])

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
        zCenter, e.MajorRadius, e.MinorRadius = findEllipseParams(self.P.frontHeight*Z, self.PtDiffuserBottom, self.P.ellipseRatio)
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
        p1 = e.parameter(du.symX(pt))
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
        return shp.extrude(depth * shp.normalAt(du.lerp(uMin, uMax, 0.5), du.lerp(vMin, vMax, 0.5)))

    def sideCurve(self):
        return Part.BSplineCurve(self.sideCurvePts()).toShape()

    def sideCurvePts(self):
        pt0 = self.PtDiffuserTop
        pt1 = (1*self.PtDiffuserBottom).scale(0,1,1)
        # top front of the diffuser
        vec = du.angleVec(self.P.diffuserConeAngle, Y, Z)
        ptFront = pt0 + (self.P.frontHeight - pt0.z)/vec.z * vec

        # simple curve
        if False:
            pts = [pt1, pt1.z * Z + ptFront.y * Y , ptFront, ptFront + 200 *Z ]

        # curve going slightly down
        down = self.P.lensDia / 3
        pt1d = pt1 - down*Z
        ptfd = ptFront.y*Y + pt1d.z*Z
        # pts = [pt1, *du.lerp_list(pt1d,ptfd,[0.3,0.7]), du.lerp(ptfd,ptFront,0.6), ptFront, ptFront + 200 *Z ]
        return [pt1, 
                *du.lerp_list(pt1d,ptfd,[0.3,0.7]), 
                du.lerp(ptfd,ptFront,0.48), 
                #          du.lerp(ptfd,ptFront,0.55), 
                du.lerp(ptfd, ptFront, 0.72)-50*Y, 
                du.lerp(ptfd,ptFront,0.9), 
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
        p1 = e.Curve.parameter(du.symX(pt))
        pts = [ e.valueAt(p) for p in du.linspace(p0,p1,40) ]
        if pts[0].x < pts[-1].x:
            pts.reverse()
        return Part.BSplineCurve(pts).toShape()

    @cached_property
    def PtSideFlash(self):
        # Flash head profile points
        return self.flashPoint + X*(self.P.flashHeadWidth/2 + self.P.flashHeadSpaceLeft)

    def coverBackRimPts(self):
        w  = self.P.flashHeadWidth

        # Flash head profile points
        pt0 = self.flashPoint - w/2*X - self.P.flashHeadSpaceLeft*X
        pt1 = pt0 + self.P.flashHeadHeight*Z 
        pt2 = pt1 + self.P.flashHeadSpaceUp*Z 
        pts = du.lerp_list(pt0,pt1,[0,0.3,0.6,0.8,0.8,1,1,1,1]) + du.lerp_list(pt2, du.symX(pt2),[0, 0.5]) 

        return pts + [ du.symX(p) for p in pts[:-1][::-1]]

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
            params = du.linspace(u_min, u_max, n)
            pts = []
            for u in params:
                pt = face.valueAt(u, v)
                if with_margin:
                    # Offset point by the front margin along the V-tangent
                    pt += self.P.coverFrontMargin * face.tangentAt(u, v)[1]
                pts.append(pt)

            return Part.BSplineCurve(pts).toShape()

        # Rule lerp the clean back edge and the offset front edge
        return Part.makeRuledSurface(
            get_boundary_curve(v_min, False),
            get_boundary_curve(v_max, True)
        )

    def diffuserFrontTab(self, ps):
        e = du.sub_edge(self.FrontRim, ps)
        depths = [k*self.P.diffuserFrontTabDepth for k in [0.3,-1]]
        return dt.tabFaceCurved(e, self.Cone.Surface, depths)

    @cached_property
    def DiffuserFrontTabs(self):
        return [ self.diffuserFrontTab(ps) for ps in self.frontTabParams ]

    def diffuserBottomTab(self, ps):
        def tabCut(e, right):
            if right:
                target_dist = e.Length - self.P.tabCutWidth
                u_min = e.Curve.parameterAtDistance(target_dist, e.FirstParameter) 
                u_max = du.lerp(*e.ParameterRange, 1.1)
            else:
                u_min = du.lerp(*e.ParameterRange, -0.1)
                u_max = e.Curve.parameterAtDistance(self.P.tabCutWidth, e.FirstParameter)

            return dt.tabFaceRec(Part.Edge(e.Curve, u_min, u_max), self.Cone.Surface,  [0, -1.1*self.P.diffThickness])

        e = du.sub_edge(self.BottomRim, ps)
        depths = [k*self.P.diffuserBottomTabDepth for k in [0.2, -1]]
        tab = dt.tabFaceCurved(e, self.Cone.Surface, depths )
        return tab.cut([ tabCut(e,False), tabCut(e,True) ]) 

    @cached_property
    def DiffuserBottomTabs(self):
        return [ self.diffuserBottomTab(ps) for ps in self.bottomTabParams ]

    @cached_property
    def DiffuserFrontInnerTabs(self):
        ftp = self.frontTabParams
        depths = [k*self.P.diffuserInnerTabDepth for k in [-1,0.3] ]
        return [ dt.tabInterFace(self.FrontRim, self.Cone.Surface, p,q, depths) for p,q in zip(ftp,ftp[1:]) ]

    @cached_property
    def DiffuserPreventTearCuts(self):
        # omit first and last parameter (u)
        us = [u for p in self.frontTabParams for u in p][1:-1]
        return [ du.circle2d(self.Cone.Surface, self.FrontRim.valueAt(u), self.P.preventTearRadius) for u in us]

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
        return self.LensCutSmooth()

    def LensCutRectangle(self):
        """Builds the shape used to cut the lens."""
        r = self.P.lensDia / 2
        h = 400
        down = 200

        shp = Part.Face(Part.makePolygon([-r*X, r*X, r*X-down*Z, -r*X-down*Z, -r*X]))
        # Calls the lens method
        return shp.translate(-h/2*Y).extrude(h*Y).fuse(self.lens)

    def LensCutSmooth(self):
        ll, lr = self.BottomSideLines

        l1, l0 = [ (1*pt).scale(1,0,1) for pt in ll ]

        r = self.P.lensDia / 2
        v = (l1-l0).normalize()

        if self.P.bottomCutShallow:
            pts = [
                l0, 
                l0 - 25*v,
                l0 - 25*v  + 36*X,
                l0 - 15*v  + 45*X,
            ]
            ptsCenter = [ r*du.angleVec(a,X,0.4*Z) for a in du.linspace(170, 10, 8) ]
        else:
            pts = [
                l0, 
                l0 - 25*v,
                l0 - 25*v  + 30*X,
                l0 - 25*v  + 40*X,
            ]
            ptsCenter = [ r*du.angleVec(a,X,0.8*Z) for a in du.linspace(170, 10, 8) ]
        pts += ptsCenter + [ du.symX(pt) for pt in pts[::-1] ]
        bez = Part.BSplineCurve(pts).toShape()

        ptsPoly = [ l0, l0-20*X, l0-20*X-100*Z ]
        ptsPoly = [ du.symX(p) for p in ptsPoly ] + ptsPoly[::-1]
        poly = Part.makePolygon(ptsPoly)
        f = Part.Face( Part.Wire([bez] + poly.Edges) )
        return f.extrude(200*Y).translate(-100*Y)


    @cached_property
    def Bottom(self):
        """Creates the shape of the bottom part."""
        # rim = 15
        rim = 0
        if self.P.coverConnectedByTabs:
            rim = 15
        z2 = -self.P.lensDia/2 - 15
        w = self.P.flashHeadWidth + 2*self.P.flashHeadSpaceLeft

        pt1 = self.flashPoint - w/2*X

        orim = self.FrontRim
        pt0 = next((pt for pt in [orim.valueAt(p) for p in [orim.FirstParameter, orim.LastParameter]] if pt.x < 0))
        # Linearly interpolate to z2, then offset by rim*X
        pt2 = pt1 + (pt0-pt1) * (z2-pt1.z)/(pt0.z-pt1.z) - rim*X

        pt1 -= rim*X
        # du.symX is assumed to be available
        pts = [pt2, pt1, du.symX(pt1), du.symX(pt2), pt2 ]
        w = Part.makePolygon(pts)
        w = du.roundCorners(w, [pt2, du.symX(pt2)], 8)
        f = Part.Face(w).cut(self.LensCut)

        if self.P.coverConnectedByTabs:
            slots = []
            for side in [0,1]:
                slots += self.bottomStitch(side).slots() 
            f = f.cut(slots)

        return f

    def bottomSideLine(self, i):
        p0, p1 = [ c.valueAt(c.ParameterRange[i]) for c in [self.CoverBackRim, self.FrontRim] ]
        return [ p0, p1 + (p1-p0).normalize() * self.P.coverFrontMargin ]

    def coverSideLine(self, i):
        uvs = self.CoverBase.ParameterRange
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

    def makeBottomFlap2(self, symX):
        pt0, pt1, axis = self.PtSideFlash, self.PtDiffuserBottom, self.bottomFoldAxis

        if symX:
            pt0 = du.symX(pt0)
            pt1 = du.symX(pt1)
            axis = du.symX(axis)

        vt = (pt1-pt0).normalize()

        pln = Part.Plane(pt0, axis)
        v = self.P.bottomTabWidth * axis.cross(vt)
        if v.y > 0:
            v = -v

        w = Part.makePolygon([pt0,pt0+v,pt1+v, pt1, pt0])
        w = du.roundCorners(w, [pt0+v,pt1+v], 8)
        f = Part.Face(pln, w)

        # holes to connect bottom with the cover
        vn = (1*v).normalize()*self.P.bottomTabWidth / 2
        r = 0.5
        for pt in du.linspace(pt0 + vt*15 + vn, pt1 - vt*15 + vn, 2):
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

    def makeBottomFlapOrig(self, symX, reverseNormal):
        pt0, pt1 = self.coverSideLine(0)
        axis = self.bottomFoldAxis
        if symX:
            pt0 = du.symX(pt0)
            pt1 = du.symX(pt1)
            axis = du.symX(axis)

        vt = (pt1-pt0).normalize()

        # plane of the flap
        pln = Part.Plane(pt0, axis)
        v = self.P.bottomTabWidth * (axis.cross(vt))
        if v.y > 0:
            v = -v

        w = Part.makePolygon([pt0,pt0+v,pt1+v, pt1, pt0])
        w = du.roundCorners(w,[pt0+v,pt1+v], 8)
        f = Part.Face(pln, w)

        # holes to connect bottom with the cover
        vn = (1*v).normalize()*self.P.bottomTabWidth / 2
        pt00 = pt0 + vt*15 + vn
        pt11 = pt1 - vt*15 + vn
        r = 0.5
        for pt in du.linspace(pt00, pt11, 2):
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

    # side 0 is left, side 1 is right
    def makeCoverFold(self, side):
        pt0, pt1 = self.PtSideFlash, self.PtDiffuserBottomMargin
        if side==0:
            pt0 = du.symX(pt0)
            pt1 = du.symX(pt1)

        vt = (pt1 - pt0).normalize()
        axis = self.BottomPlane.Surface.Axis
        if axis.z > 0:
            axis = - axis

        v = axis * self.P.snapThickness

        # flap going slightly down
        pts = [pt0,pt0+v,pt1+v, pt1, pt0]
        if side==0:
            pts.reverse()
        f1 = Part.Face(Part.makePolygon(pts))

        # folded flap at the bottom (going to the center)
        v2 = axis.cross(vt) * self.P.coverFoldWidth
        if abs(pt0.x+v2.x) > abs(pt0.x-v2.x):
            v2 = -v2

        fromSide = 12

        pts = [p + v for p in [pt0, pt0+v2, pt1+v2, pt1, pt0]]
        pc  = pts[1:3]
        if side==0:
            pts.reverse()

        w = du.roundCorners(Part.makePolygon(pts), pc, 6)
        f2 = Part.Face(w)

        f = Part.makeCompound([f1, f2])

        vpt0 = pt0 + v + v2/2 + fromSide*vt
        vpt1 = pt1 + v + v2/2 - fromSide*vt


        # holes to connect bottom with the cover
        r = 0.5
        for pt in du.linspace(vpt0, vpt1, 2):
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

    def makeCoverHoles(self, symX):
        pt0, pt1 = self.PtSideFlash, self.PtDiffuserBottomMargin
        if symX:
            pt0 = du.symX(pt0)
            pt1 = du.symX(pt1)
        vt = (pt1 - pt0).normalize()
        axis = self.BottomPlane.Surface.Axis
        if axis.z > 0:
            axis = - axis

        v = axis * self.P.snapThickness
        v2 = axis.cross(vt) * self.P.coverFoldWidth 
        if abs(pt0.x+v2.x) > abs(pt0.x-v2.x):
            v2 = -v2

        vpt0 = pt0 + v + v2/2 + 12*vt
        vpt1 = pt1 + v + v2/2 - 12*vt

        # holes to connect bottom with the cover
        cyls = []
        r = 0.5
        for pt in du.linspace(vpt0, vpt1, 2):
            c = Part.Circle()
            c.Axis = axis
            c.Location = pt
            c.Radius = r
            cyls.append(Part.Face(Part.Wire(c.toShape())).extrude(-12*axis))

        return cyls

    @cached_property
    def BottomSlots(self):
        slots = []
        sfc = self.BottomPlane.Surface
        for ps in self.bottomTabParams:
            e = du.sub_edge(self.BottomRim, ps)
            e_thin = Part.Edge(e.Curve, *[du.edge_at_dist(e, self.P.tabCutWidth, from_end) for from_end in [False,True]]) 
            slots += [
                # thin cut
                dt.slotFace(e, sfc, self.P.diffThickness/3),

                # thick cut
                dt.slotFace(e_thin, sfc, self.P.diffThickness),

                # small circles
                *[ du.circle2d(sfc, e.valueAt(u), 0.3) for u in e.ParameterRange ]
            ]
        return slots

    @cached_property
    def BottomComplete(self):
        """The final bottom shape with cuts for the inner flaps."""

        return self.Bottom.cut(self.makeCoverHoles(False)+self.makeCoverHoles(True)+self.BottomSlots)

    @cached_property
    def CoverStrapCut(self):
        # rectangular cut for the strap
        ptc = self.flashPoint + Z*self.P.flashHeadHeight*0.1 + 12*Y
        w, h = 3, 18
        pts = [ptc + w*y/2*Y+h*z/2*Z for y,z in [ [-1,-1], [1,-1], [1,1], [-1,1], [-1,-1] ] ]

        f = Part.Face(Part.makePolygon(pts))
        for pt in [ pts[0], pts[3] ]:
            c = Part.Circle()
            c.Radius = w
            c.Location = pt
            c.Axis = X
            f = f.fuse(Part.Face(Part.Wire(c.toShape())))

        return du.thicken(f, X*(self.P.flashHeadWidth+40))

    def coverFlashFlap(self, side):
        depth = 35
        heightFromBottom =  4
        heightFromTop     = 4
        cv = self.CoverBackRim

        # extrude CoverBackRim backwards and cut from it
        p1, p2 = [ cv.Curve.parameterAtDistance(d) for d in [heightFromBottom,self.P.flashHeadHeight-heightFromTop]]
        pts = [ cv.valueAt(p1), cv.valueAt(p2) ]
        pts += [pts[1]-depth*Y,pts[0]-depth*Y,pts[0]]

        # "moving" to center (eliminate X)
        pts = [ (1*pt).scale(0,1,1) for pt in pts ]
        w = du.roundCorners(Part.makePolygon(pts), pts[2:4], 5)

        sidevec = X * (100 if side == 1 else -100)
        cutter = Part.Face(w).extrude(sidevec)

        # cutting holes for the tightening strap
        strapWidth     = 20
        strapThickness = 2
        strapMargin    = 5
        scutters = []
        for pt in du.lerp_list(pts[0], pts[1], [0.35, 0.65]):
            spts = [ pt + j*strapThickness/2*Z - (strapMargin+i*strapWidth)*Y for i,j in [ [0,-1],[1,-1],[1,1], [0,1],[0,-1]]]
            w = du.roundCorners(Part.makePolygon(spts), spts, 0.5)
            scutters.append(Part.Face(w).extrude(sidevec))

        return cv.extrude(-(depth+10)*Y).common(cutter).cut(scutters)

    @cached_property
    def Cover(self):
        """Builds the cover with cuts for the flaps and other features."""

        # Flash head profile points
        # small round cuts to see where the flash is
        pt0 = self.flashPoint + self.P.flashHeadWidth/2*X
        pt1 = pt0 + Z*(self.P.flashHeadHeight+2) # + self.P.flashHeadDepth*Y
        # small round cuts to see where the flash is
        flashMarks = [ Part.makeSphere(2.5).translate(pt) for pt in [pt0, pt1, du.symX(pt0), du.symX(pt1)] ]

        appendages = []
        for side in [0,1]:
            appendages.append( self.coverFlashFlap(side))
            if self.P.coverConnectedByTabs:
                stitch = self.coverBottomStitch(side)
                appendages += stitch.tabs() + stitch.stopper_tabs()
            else:
                appendages.append( self.makeCoverFold(side) )

        return self.CoverBase.fuse(appendages).cut(self.CoverFrontSlots + flashMarks)

    @cached_property
    def SensorCone(self):
        """Builds the sensor cone shape."""
        depth = 300
        vv = self.P.lensFocal*Y + self.P.SensorWidth/2*X + self.P.SensorHeight/2*Z
        vv = vv / vv.y

        # tip of the cone (pyramid)
        yTip = -self.P.lensDepth - self.P.focalPlaneShift + self.P.lensFocal

        shp = Part.makeLoft([
            Part.makePolygon([ v, (1*v).scale(-1,1,1), (1*v).scale(-1,1,-1), (1*v).scale(1,1,-1), v ])
            for v in [ yTip * Y + vv * (y - yTip) for y  in [0, depth]]
            ])
        return shp

    @cached_property
    def CoverFrontSlots(self):
        """Builds the cutting shapes for the cover front flaps."""
        return [ dt.slotFace(du.sub_edge(self.FrontRim, ps), self.CoverBase.Surface, self.P.diffThickness) for ps in self.frontTabParams ]

    @cached_property
    def CoverLeft(self):
        return self.coverPart(0)

    @cached_property
    def CoverRight(self):
        return self.coverPart(1)

    @cached_property
    def CoverLeftUnwrapped(self):
        """Builds the flattened (unwrapped) cover shape."""
        unwrapped = du.unwrapShape(self.doc, self.CoverLeft)
        rotateUntil(unwrapped, du.linspace(0,180,30) )
        return unwrapped
        
    @cached_property
    def CoverRightUnwrapped(self):
        """Builds the flattened (unwrapped) cover shape."""
        unwrapped = du.unwrapShape(self.doc, self.CoverRight)
        rotateUntil(unwrapped, du.linspace(0,180,30) )
        return unwrapped

    @cached_property
    def CoverUnwrapped(self):
        """Builds the flattened (unwrapped) cover shape."""
        unwrapped = du.unwrapShape(self.doc, self.Cover)
        rotateUntil(unwrapped, du.linspace(0,180,30) )
        return unwrapped


    @cached_property
    def DiffUnwrapped(self):
        """Builds the flattened (unwrapped) diffuser shape."""
        unwrapped = du.unwrapShape(self.doc, self.Diffuser)
        rotateUntil(unwrapped, du.linspace(0,180,30) )
        return unwrapped

    @cached_property
    def BottomUnwrapped(self):
        """Builds the flattened (unwrapped) bottom shape."""
        unwrapped = du.unwrapShape(self.doc, self.BottomComplete)
        rotateUntil(unwrapped, du.linspace(0,180,30) )
        return unwrapped

    @cached_property
    def FlashHead(self):
        """Builds the box representing the flash head."""
        w = self.P.flashHeadWidth
        d = self.P.flashHeadDepth
        h = self.P.flashHeadHeight
        box = Part.makeBox(w, d, h)
        box.translate(-w/2*X + (self.P.topHeight - self.P.flashHeadHeight)*Z - Y*self.P.lensDepth)
        return box

    @cached_property
    def Lens(self):
        """Generates the lens shape (a cylinder)."""
        c = Part.Circle()
        c.Radius = self.P.lensDia / 2
        c.Location = -self.P.lensDepth * Y
        c.Axis = Y
        return Part.Face(Part.Wire(c.toShape())).extrude(self.P.lensDepth*Y)

    @cached_property
    def lens(self):
        """Generates the lens shape (a cylinder)."""
        r = self.P.lensDia / 2
        h = 400

        n = 60
        pts = [ r * du.angleVec(angle, X, Z) for angle in du.linspace(-90, 270, n) ]

        bez = Part.BSplineCurve(pts, periodic=True).toShape()
        shp = Part.Face(Part.Wire(bez))
        return du.thicken(shp, h*Y)

    @cached_property
    def PtDiffuserTop(self):
        """Calculates a point on the cone's base plane for diffuser_cone2."""
        pt0 = Z*(10 + self.P.lensDia/2) + 0*Y
        pt0 = Z*( self.P.lensDia/2) + 0*Y
        # Accesses self.BottomPlane (a cached property)
        pt = self.BottomPlane.Surface.intersect(Part.Line(pt0, pt0 + 100*Y))[0][0]
        return vec(pt.X, pt.Y, pt.Z)

    @cached_property 
    def PtDiffuserBottom(self):
        """Calculates a second point on the cone's base plane for diffuser_cone2."""
        pt1 = -self.P.lensDia / 5 * Z + (50 + self.P.lensDia/2)*X
        pt1 = -self.P.lensDia / 5 * Z + (45 + self.P.lensDia/2)*X

        # Accesses self.BottomPlane (a cached property)
        pt = self.BottomPlane.Surface.intersect(Part.Line(pt1, pt1 + 100*Y))[0][0]
        return vec(pt.X, pt.Y, pt.Z)

    @cached_property
    def PtDiffuserBottomMargin(self):
        ptUp = self.PtSideFlash
        ptBottom = self.PtDiffuserBottom
        return ptBottom + (ptBottom-ptUp).normalize()*self.P.coverFrontMargin

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

    @cached_property
    def coverStitch(self):
        params = st.Params(
            tabIndent=self.P.coverStitchTabIndent, 
            numTabs=self.P.coverStitchNumTabs, 
            shift=self.P.coverStitchShift,
            thickness=self.P.diffThickness,
            tabHeight=self.P.coverStitchTabHeight,
            dir=-1,
        )

        u_min, u_max, v_min, v_max = self.CoverBase.ParameterRange
        u = du.lerp(u_min, u_max, self.P.coverSplitAt)
        segs = du.poly2d([ (u,v_min), (u,v_max) ])

        sfc = self.CoverBase.Surface
        [e] = [ seg.toShape(sfc) for seg in segs ]
        return st.Stitch(e, sfc, params)

    def coverStitchEdge(self, side):
        sfc = self.CoverBase.Surface
        u_min, u_max, v_min, v_max = self.CoverBase.ParameterRange
        u = du.lerp(u_min, u_max, self.P.coverSplitAt)

        # for left, the edge is shifted
        if side == 0:
            u_vec, _ = sfc.tangent(u, (v_min+v_max)/2)
            pts = [ 
                sfc.parameter(sfc.value(u,v) + self.P.coverStitchMargin*u_vec) for v in du.linspace(v_min,v_max, 10)
            ]
            seg = du.bez2d(pts)
        else:
            [seg] = du.poly2d([(u,v_min), (u,v_max)])

        return seg.toShape(sfc) 

    def coverPart(self, side):
        e = self.coverStitchEdge(side)
        body = BOPTools.SplitAPI.slice(self.CoverBase, [e], mode="Standard", tolerance=0.01).SubShapes[side]
        body = body.cut(self.CoverFrontSlots)

        stitch = self.coverStitch
        if side == 0:
            body = body.cut(stitch.slots())
        else:
            body = body.fuse(stitch.tabs() + stitch.stopper_tabs())

        if self.P.coverConnectedByTabs:
            stitch = self.coverBottomStitch(side)
            body = body.fuse( stitch.tabs() + stitch.stopper_tabs() )
        else:
            body = body.fuse( self.makeCoverFold(side) )

        body = body.fuse( self.coverFlashFlap(side))

        # mount hole
        r = 0.5
        f = Part.Face(Part.Wire([Part.makeCircle(r)]))
        cyl = f.rotate(O,Y,90).translate(self.flashPoint + 20*Y + 12*Z ).extrude(100*X).translate(-50*X)
        body = body.cut(cyl)

        return body


    def bottomStitchParams(self, side):
        return st.Params(
            tabIndent=self.P.bottomStitchTabIndent, 
            numTabs=self.P.bottomStitchNumTabs, 
            shift=self.P.bottomStitchShift,
            thickness=self.P.diffThickness,
            tabHeight=self.P.bottomStitchTabHeight,
            tabOverlay=0,
            dir=(1 if side == 0 else -1),
        )

    # bottom stitch(es)
    def bottomStitch(self, side):
        p0,p1 = self.BottomSideLines[side]
        e = Part.makeLine(p1,p0)
        sfc = self.BottomPlane.Surface
        return st.Stitch(e, sfc, self.bottomStitchParams(side))

    def coverBottomStitch(self, side):
        p0,p1 = self.BottomSideLines[side]
        e = Part.makeLine(p1,p0)
        sfc = self.BottomPlane.Surface

        p2 = p1 - (1 if side == 0 else -1) *Y 
        sfc = Part.Face(Part.makePolygon([p0,p1,p2])).Surface

        return st.Stitch(e, sfc, self.bottomStitchParams(side))

