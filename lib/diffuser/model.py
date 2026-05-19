import FreeCAD, Part, Mesh, MeshPart, math

import BOPTools.SplitAPI

from dataclasses import dataclass, field
from functools import cached_property

import diffuser.util as du
import diffuser.tabs as dt
from diffuser.util import vec, X, Y, Z, O
import diffuser.stitch as st 

import typing

class BibData(typing.NamedTuple):
    Bib: typing.Any
    Mount: typing.Any

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
    diffuserConeAngle: float = 32

    lensDepth: float = 37
    ellipseRatio: float = 4/3
    lensDia: float = 70.5
    flashHeadHeight: float = 33
    flashHeadWidth: float = 64
    flashHeadDepth: float = 40
    flashHeadSpaceLeft: float = 0
    flashHeadSpaceUp: float = 8
    focalPlaneShift: float = 10
    diffThickness: float = 0.7
    SensorWidth: float = 17.3
    SensorHeight: float = 13.0
    lensFocal: float = 14
    coverFrontMargin: float = 8
    coverFoldWidth: float = 14
    snapThickness: float = 5

    snapHoleDia: float = 1

    coneTipShift: float = 290
    bottomTabWidth: float = 25
    bottomTabStart: float = 59
    tabCutWidth: float = 2.5
    coverSplitAt: float = 0.5415
    preventTearRadius: float = 0.3

    # tabs
    diffuserFrontTabDepth: float = 16
    diffuserBottomTabDepth: float = 20
    diffuserInnerTabDepth: float = 15

    coverConnectedByTabs: bool = False

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

    bibConeAngle: float = 35
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
        self.doc = doc
        self.P = P

    @cached_property
    def bottomPoint(self):
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

    def _buildConeParams(self):
        """Builds the conical shape and caches Cone, coneTip, and coneAxis together."""
        pt0 = self.PtDiffuserTop
        pt1 = self.PtDiffuserBottom

        ptTip = pt0 + self.P.coneTipShift * du.angleVec(self.P.diffuserConeAngle, -Y, -Z)
        axis  = du.circumcenter(*[(p - ptTip).normalize() for p in [pt0, pt1, du.symX(pt1)]])

        A     = pt0 - ptTip
        B     = axis
        vDown = 2 * (A.dot(B) / B.dot(B)) * B - A
        cone  = Part.makeLine(ptTip, ptTip + vDown.normalize() * 600).revolve(ptTip, axis, 360)

        self.__dict__['Cone']     = cone
        self.__dict__['coneTip']  = ptTip
        self.__dict__['coneAxis'] = axis

    @cached_property
    def Cone(self):
        self._buildConeParams()
        return self.__dict__['Cone']

    @cached_property
    def coneTip(self):
        self._buildConeParams()
        return self.__dict__['coneTip']

    @cached_property
    def coneAxis(self):
        self._buildConeParams()
        return self.__dict__['coneAxis']

    @cached_property
    def BottomCenterPoint(self):
        z = -self.P.lensDia/2 - 25
        points, lines = self.BottomPlane.Surface.intersect( Part.Line(-100*Y+z*Z,100*Y+z*Z)) 
        return vec(points[0].X, points[0].Y, points[0].Z)

    # bottom cone
    def _buildBibConeParams(self):
        """Builds the conical shape and caches Cone, coneTip, and coneAxis together."""
        pt1 = self.BibLeftPoint
        pt0 = self.BibCenterPoint

        bibConeTipShift = 100
        ptTip = pt0 + bibConeTipShift * du.angleVec(self.P.bibConeAngle, -Y, Z)
        axis  = du.circumcenter(*[(p - ptTip).normalize() for p in [pt0, pt1, du.symX(pt1)]])

        A     = pt0 - ptTip
        B     = axis
        vDown = 2 * (A.dot(B) / B.dot(B)) * B - A
        cone  = Part.makeLine(ptTip, ptTip + vDown.normalize() * 600).revolve(ptTip, axis, 360)

        self.__dict__['BibCone']     = cone
        self.__dict__['bibConeTip']  = ptTip
        self.__dict__['bibConeAxis'] = axis

    @cached_property
    def BottomLeftPoint(self):
        ll, _ = self.BottomSideLines
        return ll[1]

    @cached_property
    def BibLeftPoint(self):
        pt = - (10 + self.P.lensDia/2) * X 
        points, lines = self.BottomPlane.Surface.intersect( Part.Line(pt -100*Y, pt + 100*Y)) 
        return vec(points[0].X, points[0].Y, points[0].Z)

        return self.BottomLeftPoint

    @cached_property
    def BibCenterPoint(self):
        pt = -(10 + self.P.lensDia/2) * Z  
        points, lines = self.BottomPlane.Surface.intersect( Part.Line(pt -100*Y, pt + 100*Y)) 
        return vec(points[0].X, points[0].Y, points[0].Z)
        return self.BottomCenterPoint

    @cached_property
    def BottomEdge(self):
        pt0 = self.BottomLeftPoint
        pt2 = du.symX(pt0)
        pt1 = self.BottomCenterPoint

        # Step 1 — intersect the two surfaces at shape level
        # (assuming you have Face objects for both)
        section = self.BibCone.section(self.BottomPlane)
        edges = section.Edges   # list of intersection curve edges

        # Step 2 — find the edge that passes through pt1
        target_edge = next(e for e in edges if du.point_on_edge(pt1, e))

        # Step 3 — trim to [pt0, pt2] along that edge
        curve = target_edge.Curve

        u0 = curve.parameter(pt0)
        u2 = curve.parameter(pt2)

        return Part.Edge(curve, u0, u2)

    @cached_property
    def BibEdge(self):
        pt0 = self.BibLeftPoint
        pt2 = du.symX(pt0)
        pt1 = self.BibCenterPoint

        print("X", pt0, pt1, pt2)

        # Step 1 — intersect the two surfaces at shape level
        # (assuming you have Face objects for both)
        section = self.BibCone.section(self.BottomPlane)
        edges = section.Edges   # list of intersection curve edges

        print("edges", len(edges) )

        # Step 2 — find the edge that passes through pt1
        edges = [ e for e in edges if du.point_on_edge(pt1, e) ]

        print("edges", len(edges) )
        target_edge = edges[0]

        # Step 3 — trim to [pt0, pt2] along that edge
        curve = target_edge.Curve

        u0 = curve.parameter(pt0)
        u2 = curve.parameter(pt2)

        return Part.Edge(curve, u0, u2)

    @cached_property
    def BibCone(self):
        self._buildBibConeParams()
        return self.__dict__['BibCone']

    @cached_property
    def bibConeTip(self):
        self._buildBibConeParams()
        return self.__dict__['bibConeTip']

    @cached_property
    def bibConeAxis(self):
        self._buildBibConeParams()
        return self.__dict__['bibConeAxis']

    @cached_property
    def frontEllipse(self):
        e = Part.Ellipse()
        zCenter, e.MajorRadius, e.MinorRadius = findEllipseParams(self.P.frontHeight*Z, self.PtDiffuserBottom, self.P.ellipseRatio)
        e.Location = zCenter * Z
        e.Axis = Y
        return e

    @cached_property
    def ConeLimiterSideCurve(self):
        sc = self.sideCurve()
        pt0, pt1 = [ sc.valueAt(p) for p in sc.ParameterRange ]
        y   = -300*Y
        f   = Part.Face(Part.Wire([ Part.makeLine(y + pt0.z*Z, pt0), sc, Part.makeLine(pt1, y + pt1.z*Z), Part.makeLine(y + pt1.z*Z, y + pt0.z*Z)  ]))
        ext = 600*X
        return du.thicken(f, ext)


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
        cone_dir = du.angleVec(self.P.diffuserConeAngle, Y, Z)
        ptFront = pt0 + (self.P.frontHeight - pt0.z)/cone_dir.z * cone_dir

        # curve going slightly down
        down = self.P.lensDia / 3
        pt1d = pt1 - down*Z
        ptfd = ptFront.y*Y + pt1d.z*Z
        return [pt1,
                *du.lerp_list(pt1d,ptfd,[0.3,0.7]),
                du.lerp(ptfd,ptFront,0.48),
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
    def Bib(self):
        return self.bib.Bib

    @cached_property
    def BibMount(self):
        return self.bib.Mount

    @cached_property 
    def bib(self):
        e = self.BibEdge
        pl, pr = e.ParameterRange

        pt0, pt1 = [ e.valueAt(p) for p in (pl,pr) ]

        y1, y2 = 80, 120
        x1 = 40
        pts = [pt1, pt1+y1*Y + x1*X, pt1+y2*Y+x1*X, pt0+y2*Y-x1*X, pt0+y1*Y-x1*X, pt0 ]

        vz = 200*Z
        ps = []

        sfcBib = self.BibCone.Surface
        for pt in pts:
            line = Part.makeLine(pt-vz, pt+vz).Curve
            points, _ = sfcBib.intersect(line)
            ptsInt = [ vec(pt.X, pt.Y, pt.Z) for pt in points ]
            ptsInt.sort(key=lambda pt:pt.z)
            ps.append( sfcBib.parameter(ptsInt[0]) )

        seg = du.bez2d(ps)
        w = Part.Wire([e, seg.toShape(sfcBib) ])

        Part.show(w, "w")
        f =  Part.Face(sfcBib, w.reversed())
        f.validate()
        f.check()

        bib = f

        axis = self.BottomPlane.Surface.Axis

        # flap
        fw = 12 
        fh = 20
        ch = 12

        # parameters on edge
        odsazeni = 10
        distances = (odsazeni, fw+odsazeni, (e.Length-fw)/2, (e.Length+fw)/2, e.Length-fw-odsazeni, e.Length-odsazeni)
        p0, p1, p2, p3, p4, pn = ( e.Curve.parameterAtDistance(d, pl) for d in distances)
        pm = (pl+pr)/2

        ptl, ptr, ptm, pt1, pt2, pt3, pt4 = ( e.valueAt(p) for p in (pl, pr, pm, p1, p2, p3, p4) )


        # mount plate
        pt  = ptm + (fh+3)*X.cross(axis)
        pts = [ ptl, ptl-20*X, vec(ptl.x-20, pt.y, pt.z) ]
        pts += map(du.symX, reversed(pts))

        curved_edges = []
        params = (pl,p0,p1,p2,p3,p4,pn,pr)
        for ps in zip(params, params[1:]):
            edge = Part.makeLine(*[ e.valueAt(p) for p in ps]) if len(curved_edges) % 2 == 1 else Part.Edge(e.Curve, *ps) 
            curved_edges.append(edge)

        w = Part.Wire([ *curved_edges, *Part.makePolygon(pts[::-1]).Edges ])
        mount = Part.Face(w)
        Part.show(w, "ww")

        # flaps to connect the bib to mount plate
        for pa, pb in ((p2,p3), (p0,p1), (p4,pn)):
            pm = (pa+pb)/2
            normal = sfcBib.normal(*sfcBib.parameter(e.valueAt(pm)))
            v = normal.cross(-e.tangentAt(pm))

            pta, ptb   = ( e.valueAt(p) for p in (pa, pb) )
            pta2, ptb2 = (pt + fh *v    for pt in (pta, ptb) )

            w = Part.makePolygon([pta, ptb, ptb2, pta2, pta])
            w = du.roundCorners(w, [pta2, ptb2], 3)
            flap = Part.Face(w).cut([ Part.makeSphere(0.5, pt) for pt in (pta, ptb) ])

            center = (pta+ptb)/2 + ch*v
            fc = Part.Face(Part.Wire(Part.makeCircle(self.P.snapHoleDia, center, normal)))
            mount = mount.fuse(flap.cut(fc))
            bib = bib.cut(fc.extrude(8*normal).translate(-4*normal))

        return BibData(Bib=bib, Mount=mount)


    @cached_property
    def BibUnwrapped(self):
        unwrapped = du.unwrapShape(self.doc, self.Bib )
        rotateUntil(unwrapped, du.linspace(0,180,30) )
        return unwrapped

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
        # return self.LensCutSmooth()
        return self.LensCutExperimental()

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

    def LensCutExperimental(self):
        r = self.P.lensDia / 2
        pts = [ r*du.angleVec(a,X,Z) for a in du.linspace(180, 0, 8) ]

        pts = [ pts[0] + 200*du.angleVec(10,-Z,-X) ] + pts + [ pts[-1] + 200 *du.angleVec(10,-Z,X) ]
        bez = Part.BSplineCurve(pts).toShape()

        w = Part.Wire([bez, Part.makeLine(pts[-1], pts[0]) ])
        f = Part.Face(w)
        return f.extrude(200*Y).translate(-100*Y)

    def LensCutExperimental0(self):
        ll, lr = self.BottomSideLines

        # removing y by scale
        l1, l0 = [ (1*pt).scale(1,0,1) for pt in ll ]

        r = self.P.lensDia / 2
        v = (l1-l0).normalize()

        ptsCenter = [ r*du.angleVec(a,X,Z) for a in du.linspace(180, 0, 8) ]

        zBottom = (l0 - 35*v).z

        # bottom round arc

        arcPts = [ l0, Z*(l0.z - 30), (1*l0).scale(-1,1,1) ]
        arc = Part.ArcOfCircle(l0, Z*(l0.z - 30), (1*l0).scale(-1,1,1)).toShape()
        ac = arc.Curve

        ptsPoly = [ l0, l0-50*X, l0-50*X-120*Z ]
        ptsPoly = [ (1*pt).scale(-1,1,1) for pt in ptsPoly ] + ptsPoly[::-1]

        def arcParam(k):
            pt0 = k*r*X 
            e = Part.makeLine(pt0 - 100*Z, pt0 + 100*Z)
            # bottom intersection
            pts = [ vec(pt.X, pt.Y, pt.Z) for pt in ac.intersectCC(e.Curve) ]
            pts.sort(key=lambda pt:pt.z)
            return ac.parameter(pts[0])

        pLeft, pRight = arcParam(-1), arcParam(1)

        w = Part.Wire([
            Part.Edge(ac, arc.FirstParameter, pLeft),
            Part.BSplineCurve( [ ac.value(pLeft)  ] + ptsCenter + [ ac.value(pRight) ]).toShape(),
            Part.Edge(ac, pRight, arc.LastParameter)
        ] + Part.makePolygon(ptsPoly).Edges )

        Part.show(w, "wx")
        Part.show(Part.makePolygon(ptsPoly), "wx0")
         
        f = Part.Face(w)
        return f.extrude(200*Y).translate(-100*Y)


    @cached_property
    def Bottom(self):
        """Creates the shape of the bottom part."""
        ll, lr  = self.BottomSideLines

        pts = lr[::-1] + ll
        w = Part.Wire( Part.makePolygon(pts).Edges + [ self.BottomEdge ])
        f = Part.Face(w)

        f = f.cut(self.LensCutExperimental())

        return f

    def Bottom0(self):
        """Creates the shape of the bottom part."""
        rim = 0 if not(self.P.coverConnectedByTabs) else 15


        zbottom = 15
        zbottom = 45
        z2 = -self.P.lensDia/2 - zbottom 

        pt1 = self.flashPoint - (self.P.flashHeadWidth/2 + self.P.flashHeadSpaceLeft)*X

        orim = self.FrontRim
        # pt0 = next((pt for pt in [orim.valueAt(p) for p in [orim.FirstParameter, orim.LastParameter]] if pt.x < 0))
        pt0 = next((pt for pt in [orim.valueAt(p) for p in orim.ParameterRange] if pt.x < 0))
        # Linearly interpolate to z2, then offset by rim*X
        pt2 = pt1 + (pt0-pt1) * (z2-pt1.z)/(pt0.z-pt1.z) - rim*X

        pt1 -= rim*X
        pts = [pt2, pt1, du.symX(pt1), du.symX(pt2), pt2 ]
        w = Part.makePolygon(pts)
        Part.show(w, "w")
        f = Part.Face(w).cut(self.LensCut)

        if self.P.coverConnectedByTabs:
            slots = []
            for side in [0,1]:
                slots += self.bottomStitch(side).slots() 
            f = f.cut(slots)

        return f

    def coverSideLine(self, i):
        uvs = self.CoverBase.ParameterRange
        return [ self.CoverBase.valueAt(uvs[i], v) for v in uvs[2:] ]

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

    def makeCoverHoles(self, mirror):
        pt0, pt1 = self.PtSideFlash, self.PtDiffuserBottomMargin
        if mirror:
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
        r = self.P.snapHoleDia / 2
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

        # small spheres marking flash head corners
        pt0 = self.flashPoint + self.P.flashHeadWidth/2*X
        pt1 = pt0 + Z*(self.P.flashHeadHeight+2)
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
    def PtDiffuserTop(self):
        pt0 = Z * (self.P.lensDia/2)
        pt = self.BottomPlane.Surface.intersect(Part.Line(pt0, pt0 + 100*Y))[0][0]
        return vec(pt.X, pt.Y, pt.Z)

    @cached_property
    def PtDiffuserBottom(self):
        pt1 = -self.P.lensDia/5 * Z + (45 + self.P.lensDia/2)*X
        pt = self.BottomPlane.Surface.intersect(Part.Line(pt1, pt1 + 100*Y))[0][0]
        return vec(pt.X, pt.Y, pt.Z)

    @cached_property
    def PtDiffuserBottomMargin(self):
        ptUp = self.PtSideFlash
        ptBottom = self.PtDiffuserBottom
        return ptBottom + (ptBottom-ptUp).normalize()*self.P.coverFrontMargin

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
        diff.rotate(O,Z,90)
        bb = diff.BoundBox
        diff.translate(pt0 + 5*Y + 525*X -X*bb.XMin-Y*bb.YMin)
        Part.show(diff, "diff-unwrapped")

        bt = self.BottomUnwrapped
        bb = bt.BoundBox
        bt.translate(pt0 + 285*X + 343*Y -X*bb.XMin-Y*bb.YMin)
        Part.show(bt, "bottom-unwrapped")

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
        r = self.snapHoleDia / 2
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

