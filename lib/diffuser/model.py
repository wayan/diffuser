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
    bib: typing.Any
    mount: typing.Any

class BibCone(typing.NamedTuple):
    cone: typing.Any
    tip: typing.Any
    axis: typing.Any

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
    backPlateTabWidth: float = 25
    backPlateTabStart: float = 59
    tabCutWidth: float = 2.5
    coverSplitAt: float = 0.5415
    preventTearRadius: float = 0.3

    # tabs
    diffuserFrontTabDepth: float = 16
    diffuserBackPlateTabDepth: float = 20
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

    # back plate stitch(es)
    backPlateStitchNumTabs: int = 3
    backPlateStitchTabIndent: float = 20
    backPlateStitchMargin: float = 10 
    backPlateStitchShift: float = 8
    backPlateStitchTabHeight: float = 10
    backPlateCutShallow: bool = False

    bibConeAngle: float = 25 
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
    def backPlatePoint(self):
        return self.P.lensDia/2*Z - 5*Y

    @cached_property
    def flashPoint(self):
        return -self.P.lensDepth*Y + (self.P.topHeight - self.P.flashHeadHeight)*Z

    @cached_property
    def front_tab_params(self):
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
    def back_plate_tab_params(self):
        # Flap angles setup
        n = 1
        width = self.P.backPlateTabWidth
        first = self.P.backPlateTabStart

        rim = self.BackPlateRim
        return [
            ( rim.Curve.parameterAtDistance(l+k*width/2) for k in (-1,1))
                for l in du.linspace(first, rim.Length-first, n)
        ]

    # --- Lazily Computed Properties using @cached_property ---
    @cached_property
    def sfc_bib(self):
        return self._bib_cone.cone.Surface

    @cached_property
    def sfc_back_plate(self):
        """Builds the construction plane for the back plate block."""
        s = 600
        pt0 = self.backPlatePoint
        pt1 = self.flashPoint
        return Part.makePlane(s, s, pt0, X.cross(pt1-pt0)).translate(-s/2*X + (pt1-pt0)).Surface

    def _buildConeParams(self):
        """Builds the conical shape and caches Cone, coneTip, and coneAxis together."""
        pt0 = self.PtDiffuserTop
        pt1 = self.PtDiffuserBottom

        ptTip = pt0 + self.P.coneTipShift * du.angleVec(self.P.diffuserConeAngle, -Y, -Z)
        axis  = du.circumcenter(*[(p - ptTip).normalize() for p in [pt0, pt1, du.flip_x(pt1)]])

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
    def BackPlateCenterPoint(self):
        z = -self.P.lensDia/2 - 25
        points, lines = self.sfc_back_plate.intersect( Part.Line(-100*Y+z*Z,100*Y+z*Z)) 
        return vec(points[0].X, points[0].Y, points[0].Z)

    @cached_property
    def _bib_cone(self):
        """Builds the conical shape and caches Cone, coneTip, and coneAxis together."""
        pt1, pt0, pt2 = self.bib_points

        bibConeTipShift = 100
        ptTip = pt0 + bibConeTipShift * du.angleVec(self.P.bibConeAngle, -Y, Z)
        axis  = du.circumcenter(*[(p - ptTip).normalize() for p in [pt0, pt1, pt2]])

        A     = pt0 - ptTip
        B     = axis
        vDown = 2 * (A.dot(B) / B.dot(B)) * B - A
        cone  = Part.makeLine(ptTip, ptTip + vDown.normalize() * 600).revolve(ptTip, axis, 360)

        return BibCone(cone=cone,tip=ptTip,axis=axis)

    @cached_property
    def BackPlateLeftPoint(self):
        ll, _ = self.BackPlateSideLines
        return ll[1]

    @cached_property
    def bib_points(self):
        # Pair each direction vector with its specific scalar calculation
        axis_offsets = [
            (-(10 + self.P.lensDia) / 2 * X),
            (-(10 + self.P.lensDia) / 2 * Z),  # You can freely change this formula later
            ( (10 + self.P.lensDia) / 2 * X),
        ]

        # Generate the intersection points cleanly
        pts = []
        for pt in axis_offsets:
            intersections, _ = self.sfc_back_plate.intersect(Part.Line(pt - 100 * Y, pt + 100 * Y))
            p = intersections[0]
            pts.append(vec(p.X, p.Y, p.Z))

        return pts

    @cached_property
    def BackPlateEdge(self):
        pt0 = self.BackPlateLeftPoint
        pt2 = du.flip_x(pt0)
        pt1 = self.BackPlateCenterPoint

        # Step 1 — intersect the two surfaces at shape level
        # (assuming you have Face objects for both)
        section = self.BibCone.section(self.sfc_back_plate)
        edges = section.Edges   # list of intersection curve edges

        # Step 2 — find the edge that passes through pt1
        target_edge = next(e for e in edges if du.point_on_edge(pt1, e))

        # Step 3 — trim to [pt0, pt2] along that edge
        curve = target_edge.Curve

        u0 = curve.parameter(pt0)
        u2 = curve.parameter(pt2)

        return Part.Edge(curve, u0, u2)

    @cached_property
    def bib_edge(self):
        pt0, pt1, pt2 = self.bib_points

        # Step 1 — intersect the two surfaces at shape level
        # (assuming you have Face objects for both)
        section = self.BibCone.section(self.sfc_back_plate.toShape())

        # Step 2 — find the edge that passes through pt1
        edges = [ e for e in section.Edges if du.point_on_edge(pt1, e) ]

        print("edges", len(edges) )
        target_edge = edges[0]

        # Step 3 — trim to [pt0, pt2] along that edge
        curve = target_edge.Curve

        u0 = curve.parameter(pt0)
        u2 = curve.parameter(pt2)

        return Part.Edge(curve, u0, u2)

    @cached_property
    def BibCone(self):
        return self._bib_cone.cone

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
    def BackPlateBlock(self):
        """Builds the solid block that cuts the back plate."""
        depth = 600
        shp = self.sfc_back_plate
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
        return self.Cone.common(self.ConeLimiter).cut(self.BackPlateBlock)

    @cached_property
    def BackPlateRim(self):
        s = self.sfc_back_plate.toShape().section(self.Cone)
        e = s.SubShapes[0]
        pt = self.PtDiffuserBottom
        p0 = e.Curve.parameter(pt)
        p1 = e.Curve.parameter(du.flip_x(pt))
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
        pts = du.lerp_list(pt0,pt1,[0,0.3,0.6,0.8,0.8,1,1,1,1]) + du.lerp_list(pt2, du.flip_x(pt2),[0, 0.5]) 

        return pts + [ du.flip_x(p) for p in pts[:-1][::-1]]

    @cached_property
    def cover_back_rim(self):
        """Builds the profile curve for the flash head rim."""
        return Part.BSplineCurve(self.coverBackRimPts()).toShape()

    @cached_property
    def CoverBase(self):
        """Creates the main cover ruled surface, cut by the back plate block."""
        face = Part.makeRuledSurface(self.cover_back_rim, self.FrontRim)
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
    def bib(self):
        return self._bib.bib

    @cached_property
    def bib_mount(self):
        return self._bib.mount

    @cached_property
    def _bib(self):
        # ── 1. Bib face on the bib-cone surface ───────────────────────────────
        edge              = self.bib_edge
        u_left, u_right   = edge.ParameterRange
        pt_left, pt_right = (edge.valueAt(u) for u in (u_left, u_right))


        def bib_xy_uv(pt):
            vz_probe      = 200 * Z
            raw_pts, _ = self.sfc_bib.intersect(Part.makeLine(pt - vz_probe, pt + vz_probe).Curve)
            int_pts    = sorted([vec(p.X, p.Y, p.Z) for p in raw_pts], key=lambda p: p.z)
            return self.sfc_bib.parameter(int_pts[0])

        if False:
            # Control points for the "back" arch of the bib (arching away along +Y)
            y_near, y_far = 100, 120
            x_spread      = 50
            back_ctrl_pts = [
                pt_right,
                pt_right + y_near * Y + x_spread * X,
                pt_right + y_far  * Y + x_spread * X,
                pt_left  + y_far  * Y - x_spread * X,
                pt_left  + y_near * Y - x_spread * X,
                pt_left,
            ]

            # Project each control point onto the bib-cone surface along Z; take lowest hit
            vz_probe      = 200 * Z
            back_ctrl_uvs = [ bib_xy_uv(pt) for pt in back_ctrl_pts ]
        else:
            y_far       = 150
            x_spread    = 50

            uv_left_far = bib_xy_uv(pt_left  + y_far  * Y - x_spread * X)
            uv_center_far = bib_xy_uv( y_far  * Y)
            uv_center     = self.sfc_bib.parameter(edge.valueAt((u_left+u_right)/2))
            uv_left  = self.sfc_bib.parameter(pt_left)

            def get_uv(uvn):
                un,vn = uvn
                return du.lerp_tuple(
                    du.lerp_tuple(uv_center,uv_left,un),
                    du.lerp_tuple(uv_center_far,uv_left_far,un),
                    vn
                )

            # symmetry
            uvs = list(map(get_uv, ((1,0), (1.2,0.2), (1,0.7), (1,1), (0.7,1))))
            # uvs = [ uv_left, *du.lerp_tuple_list(uv_left_far, uv_center_far, (0, 0.2, 0.8)) 
            uvs += [
                self.sfc_bib.parameter(du.flip_x(self.sfc_bib.value(*uv))) for uv in uvs[::-1]
            ]

            back_ctrl_uvs = uvs[::-1]

        w        = Part.Wire([edge, du.bez2d(back_ctrl_uvs).toShape(self.sfc_bib)])
        bib = Part.Face(self.sfc_bib, w.reversed())
        bib.validate()
        bib.check()

        # ── 2. Mount plate with three connecting flaps ────────────────────────
        axis = self.sfc_back_plate.Axis

        flap_width       = 12   # width of each connecting flap along the edge
        flap_height      = 20   # how far each flap extends from the edge
        snap_hole_offset = 12   # distance of the snap hole from the edge along the flap

        # Arc-length distances from the left end marking the three flap boundaries:
        #   indent | left flap | gap | center flap | gap | right flap | indent
        edge_indent      = 10
        flap_bound_dists = (
            edge_indent,
            edge_indent + flap_width,
            (edge.Length - flap_width) / 2,
            (edge.Length + flap_width) / 2,
            edge.Length - flap_width - edge_indent,
            edge.Length - edge_indent,
        )
        u_left_start, u_left_end, u_center_start, u_center_end, u_right_start, u_right_end = (
            edge.Curve.parameterAtDistance(d, u_left) for d in flap_bound_dists
        )
        u_mid  = (u_left + u_right) / 2
        pt_mid = edge.valueAt(u_mid)

        # Mount-plate outline: left-side half mirrored about X = 0
        pt_plate_ref = pt_mid + (flap_height + 3) * X.cross(axis)
        plate_half   = [
            pt_left,
            pt_left - 20 * X,
            vec(pt_left.x - 20, pt_plate_ref.y, pt_plate_ref.z),
        ]
        plate_pts = plate_half + list(map(du.flip_x, reversed(plate_half)))

        # Mount boundary: alternating curved arc / straight chord along the edge
        u_bounds    = (u_left, u_left_start, u_left_end, u_center_start, u_center_end, u_right_start, u_right_end, u_right)
        mount_edges = [
            Part.makeLine(edge.valueAt(u_a), edge.valueAt(u_b)) if i % 2 == 1
            else Part.Edge(edge.Curve, u_a, u_b)
            for i, (u_a, u_b) in enumerate(zip(u_bounds, u_bounds[1:]))
        ]
        w          = Part.Wire([*mount_edges, *Part.makePolygon(plate_pts[::-1]).Edges])
        mount = Part.Face(w)

        # Three connecting flaps: center, left-shoulder, right-shoulder
        for u_a, u_b in ((u_center_start, u_center_end), (u_left_start, u_left_end), (u_right_start, u_right_end)):
            u_flap_mid = (u_a + u_b) / 2
            normal     = self.sfc_bib.normal(*self.sfc_bib.parameter(edge.valueAt(u_flap_mid)))
            v_flap_dir = normal.cross(-edge.tangentAt(u_flap_mid))

            pt_a, pt_b   = (edge.valueAt(u) for u in (u_a, u_b))
            pt_a2, pt_b2 = (pt + flap_height * v_flap_dir for pt in (pt_a, pt_b))

            w    = Part.makePolygon([pt_a, pt_a2, pt_b2, pt_b, pt_a])
            w    = du.roundCorners(w, [pt_a2, pt_b2], 3)
            flap = Part.Face(w).cut([Part.makeSphere(0.5, pt) for pt in (pt_a, pt_b)])

            pt_snap_hole = (pt_a + pt_b) / 2 + snap_hole_offset * v_flap_dir
            fc = Part.Face(Part.Wire(Part.makeCircle(self.P.snapHoleDia, pt_snap_hole, normal)))

            mount = mount.fuse(flap.cut(fc))
            bib   = bib.cut(fc.extrude(8 * normal).translate(-4 * normal))

        return BibData(bib=bib, mount=mount)

    def unwrap(self, shp):
        unwrapped = du.unwrapShape(self.doc, shp )
        rotateUntil(unwrapped, du.linspace(0,180,30) )
        return unwrapped

    @cached_property
    def DiffuserFrontTabs(self):
        return [ self.diffuserFrontTab(ps) for ps in self.front_tab_params ]

    @cached_property
    def DiffuserBackPlateTabs(self):
        return [ self.diffuserBackPlateTab(ps) for ps in self.back_plate_tab_params ]

    def diffuserBackPlateTab(self, ps):
        def tabCut(e, right):
            if right:
                target_dist = e.Length - self.P.tabCutWidth
                u_min = e.Curve.parameterAtDistance(target_dist, e.FirstParameter) 
                u_max = du.lerp(*e.ParameterRange, 1.1)
            else:
                u_min = du.lerp(*e.ParameterRange, -0.1)
                u_max = e.Curve.parameterAtDistance(self.P.tabCutWidth, e.FirstParameter)

            return dt.tabFaceRec(Part.Edge(e.Curve, u_min, u_max), self.Cone.Surface,  [0, -1.1*self.P.diffThickness])

        e = du.sub_edge(self.BackPlateRim, ps)
        depths = [k*self.P.diffuserBackPlateTabDepth for k in [0.2, -1]]
        tab = dt.tabFaceCurved(e, self.Cone.Surface, depths )
        return tab.cut([ tabCut(e,False), tabCut(e,True) ]) 


    @cached_property
    def DiffuserFrontInnerTabs(self):
        ftp = self.front_tab_params
        depths = [k*self.P.diffuserInnerTabDepth for k in [-1,0.3] ]
        return [ dt.tabInterFace(self.FrontRim, self.Cone.Surface, p,q, depths) for p,q in zip(ftp,ftp[1:]) ]

    @cached_property
    def DiffuserPreventTearCuts(self):
        # omit first and last parameter (u)
        us = [u for p in self.front_tab_params for u in p][1:-1]
        return [ du.circle2d(self.Cone.Surface, self.FrontRim.valueAt(u), self.P.preventTearRadius) for u in us]

    @cached_property
    def Diffuser(self):
        return self.DiffuserBase.fuse(self.DiffuserFrontTabs + self.DiffuserBackPlateTabs + self.DiffuserFrontInnerTabs).cut(self.DiffuserPreventTearCuts)

    @cached_property
    def BackPlateSideLines(self):
        # flaps by the base
        ps = self.CoverBase.ParameterRange
        return [ [ self.CoverBase.valueAt(u,v) for v in ps[2:] ] for u in ps[:2] ]

    @cached_property
    def LensCut(self):
        # return self.LensCutSmooth()
        return self.LensCutExperimental()

    def LensCutSmooth(self):
        ll, lr = self.BackPlateSideLines

        l1, l0 = [ (1*pt).scale(1,0,1) for pt in ll ]

        r = self.P.lensDia / 2
        v = (l1-l0).normalize()

        if self.P.backPlateCutShallow:
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
        pts += ptsCenter + [ du.flip_x(pt) for pt in pts[::-1] ]
        bez = Part.BSplineCurve(pts).toShape()

        ptsPoly = [ l0, l0-20*X, l0-20*X-100*Z ]
        ptsPoly = [ du.flip_x(p) for p in ptsPoly ] + ptsPoly[::-1]
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
        ll, lr = self.BackPlateSideLines

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
    def BackPlate(self):
        """Creates the shape of the back plate part."""
        ll, lr  = self.BackPlateSideLines

        pts = [*reversed(lr), *ll, lr[1]]
        w = Part.makePolygon(pts)
        # w = Part.Wire( Part.makePolygon(pts).Edges + [ self.BackPlateEdge ])
        f = Part.Face(w)
        f = f.cut(self.LensCutExperimental())
        return f

    def BackPlate0(self):
        """Creates the shape of the back plate part."""
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
        pts = [pt2, pt1, du.flip_x(pt1), du.flip_x(pt2), pt2 ]
        w = Part.makePolygon(pts)
        Part.show(w, "w")
        f = Part.Face(w).cut(self.LensCut)

        if self.P.coverConnectedByTabs:
            slots = []
            for side in [0,1]:
                slots += self.backPlateStitch(side).slots() 
            f = f.cut(slots)

        return f

    def coverSideLine(self, i):
        uvs = self.CoverBase.ParameterRange
        return [ self.CoverBase.valueAt(uvs[i], v) for v in uvs[2:] ]

    # side 0 is left, side 1 is right
    def cover_fold(self, side):
        pt0, pt1 = self.PtSideFlash, self.PtDiffuserBottomMargin
        if side==0:
            pt0 = du.flip_x(pt0)
            pt1 = du.flip_x(pt1)

        vt = (pt1 - pt0).normalize()
        axis = self.sfc_back_plate.Axis
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
            pt0 = du.flip_x(pt0)
            pt1 = du.flip_x(pt1)
        vt = (pt1 - pt0).normalize()
        axis = self.sfc_back_plate.Axis
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
        for pt in du.linspace(vpt0, vpt1, 2):
            c = Part.makeCircle(self.P.snapHoleDia/2, pt, axis)
            cyls.append(Part.Face(Part.Wire(c)).extrude(-12*axis))
        return cyls

    def back_plate_slot(self, ps):
        sfc = self.sfc_back_plate

        e = du.sub_edge(self.BackPlateRim, ps)
        e_thin = Part.Edge(e.Curve, *[du.edge_at_dist(e, self.P.tabCutWidth, from_end) for from_end in [False,True]]) 

        return Part.makeCompound([
            # thin cut
            dt.slotFace(e, sfc, self.P.diffThickness/3),

            # thick cut
            dt.slotFace(e_thin, sfc, self.P.diffThickness), 

            # small circles
            *[ du.circle2d(sfc, e.valueAt(u), 0.3) for u in e.ParameterRange ]
        ])

    @cached_property
    def back_plate_complete(self):
        """The final back plate shape with cuts for the inner flaps."""

        return self.BackPlate.cut([
            *self.makeCoverHoles(False), 
            *self.makeCoverHoles(True), 
            *map(self.back_plate_slot, self.back_plate_tab_params),
        ])

    def coverFlashFlap(self, side):
        depth = 35
        heightFromBottom =  4
        heightFromTop     = 4
        cv = self.cover_back_rim

        # extrude cover_back_rim backwards and cut from it
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
        flashMarks = [ Part.makeSphere(2.5).translate(pt) for pt in [pt0, pt1, du.flip_x(pt0), du.flip_x(pt1)] ]

        appendages = []
        for side in [0,1]:
            appendages.append( self.coverFlashFlap(side))
            if self.P.coverConnectedByTabs:
                stitch = self.coverBackPlateStitch(side)
                appendages += stitch.tabs() + stitch.stopper_tabs()
            else:
                appendages.append( self.cover_fold(side) )

        return self.CoverBase.fuse(appendages).cut(self.CoverFrontSlots + flashMarks)

    @cached_property
    def CoverFrontSlots(self):
        """Builds the cutting shapes for the cover front flaps."""
        return [ dt.slotFace(du.sub_edge(self.FrontRim, ps), self.CoverBase.Surface, self.P.diffThickness) for ps in self.front_tab_params ]

    @cached_property
    def CoverLeft(self):
        return self.coverPart(0)

    @cached_property
    def CoverRight(self):
        return self.coverPart(1)

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
        pt = self.sfc_back_plate.intersect(Part.Line(pt0, pt0 + 100*Y))[0][0]
        return vec(pt.X, pt.Y, pt.Z)

    @cached_property
    def PtDiffuserBottom(self):
        pt1 = -self.P.lensDia/5 * Z + (45 + self.P.lensDia/2)*X
        pt = self.sfc_back_plate.intersect(Part.Line(pt1, pt1 + 100*Y))[0][0]
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

        bt = self.BackPlateUnwrapped
        bb = bt.BoundBox
        bt.translate(pt0 + 285*X + 343*Y -X*bb.XMin-Y*bb.YMin)
        Part.show(bt, "back-plate-unwrapped")

    def solids(self):
        return [ self.Cover, self.backPlate_complete, self.Diffuser, self.FlashHead]

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
            stitch = self.coverBackPlateStitch(side)
            body = body.fuse( stitch.tabs() + stitch.stopper_tabs() )
        else:
            body = body.fuse( self.cover_fold(side) )

        body = body.fuse( self.coverFlashFlap(side))

        # mount hole
        r = self.snapHoleDia / 2
        f = Part.Face(Part.Wire([Part.makeCircle(r)]))
        cyl = f.rotate(O,Y,90).translate(self.flashPoint + 20*Y + 12*Z ).extrude(100*X).translate(-50*X)
        body = body.cut(cyl)

        return body

    def backPlateStitchParams(self, side):
        return st.Params(
            tabIndent=self.P.backPlateStitchTabIndent, 
            numTabs=self.P.backPlateStitchNumTabs, 
            shift=self.P.backPlateStitchShift,
            thickness=self.P.diffThickness,
            tabHeight=self.P.backPlateStitchTabHeight,
            tabOverlay=0,
            dir=(1 if side == 0 else -1),
        )

    # back plate stitch(es)
    def backPlateStitch(self, side):
        p0,p1 = self.BackPlateSideLines[side]
        e = Part.makeLine(p1,p0)
        return st.Stitch(e, self.sfc_back_plate, self.backPlateStitchParams(side))

    def coverBackPlateStitch(self, side):
        p0,p1 = self.BackPlateSideLines[side]
        e = Part.makeLine(p1,p0)
        sfc = self.sfc_back_plate

        p2 = p1 - (1 if side == 0 else -1) *Y 
        sfc = Part.Face(Part.makePolygon([p0,p1,p2])).Surface

        return st.Stitch(e, sfc, self.backPlateStitchParams(side))

