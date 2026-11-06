import FreeCAD, Part, Mesh, MeshPart, math

import BOPTools.SplitAPI

from functools import cached_property

import diffuser.util as du
import diffuser.tabs as dt
from diffuser.util import vec, X, Y, Z, O
import diffuser.stitch as st

from diffuser.params import BibData, BibCone, DiffuserCone, Params  # noqa: F401 (re-exported)
from diffuser.geometry import rotate_until, find_ellipse_params

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
    def back_plate_point(self):
        z = 70.5/2
        return vec(0,-5,z)

    @cached_property
    def flash_point(self):
        return vec(0, -self.P.lensDepth, self.P.topHeight - self.P.flashHeadHeight)

    @cached_property
    def front_tab_params(self):
        n = 5
        width = 20
        first = 80

        rim = self.front_rim
        ps = []
        #for l in du.linspace(first, rim.Length-first, n):
        #    flapParams.append([ rim.Curve.parameterAtDistance(l+k*width/2) for k in [-1,1]])
        s = [0.12, 0.23, 0.37, 0.5]
        for l in du.lerp_list(0, rim.Length, s + [1-i for i in s[:-1][::-1]]):
            ps.append(tuple(rim.Curve.parameterAtDistance(l+k*width/2, rim.FirstParameter) for k in (-1,1)))

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

        rim = self.back_plate_rim
        u_left = rim.FirstParameter

        return [
            tuple( rim.Curve.parameterAtDistance(l+k*width/2, u_left) for k in (-1,1))
                for l in du.linspace(first, rim.Length-first, n)
        ]

    # --- Lazily Computed Properties using @cached_property ---
    @cached_property
    def sfc_bib(self):
        return self._bib_cone.cone.Surface

    @cached_property
    def sfc_back_plate(self):
        """Builds the construction plane for the back plate block."""
        pt0 = self.back_plate_point
        pt1 = self.flash_point
        return Part.Plane(pt0, (pt0-pt1).cross(X))

    @cached_property
    def _diffuser_cone(self):
        """Builds the conical shape and caches cone, cone_tip, and cone_axis together."""
        pt0 = self.pt_diffuser_top
        pt1 = self.pt_diffuser_bottom

        pt_tip = pt0 + self.P.cone_tipShift * du.angle_vec(self.P.diffuserconeAngle, -Y, -Z)
        axis  = du.circumcenter(*[(p - pt_tip).normalize() for p in [pt0, pt1, du.flip_x(pt1)]])

        A     = pt0 - pt_tip
        B     = axis
        vDown = 2 * (A.dot(B) / B.dot(B)) * B - A
        cone  = Part.makeLine(pt_tip, pt_tip + vDown.normalize() * 600).revolve(pt_tip, axis, 360)

        return DiffuserCone(cone=cone, tip=pt_tip, axis=axis)

    @cached_property
    def sfc_diff(self):
        return self.cone.Surface

    @cached_property
    def cone(self):
        return self._diffuser_cone.cone

    @cached_property
    def back_plate_center_point(self):
        z = -self.P.lensDia/2 - 25
        points, lines = self.sfc_back_plate.intersect( Part.Line(-100*Y+z*Z,100*Y+z*Z)) 
        return vec(points[0].X, points[0].Y, points[0].Z)

    @cached_property
    def _bib_cone(self):
        """Builds the conical shape and caches cone, cone_tip, and cone_axis together."""
        pt1, pt0, pt2 = self.bib_pts

        bib_cone_tip_shift = 60
        pt_tip = pt0 + bib_cone_tip_shift * du.angle_vec(self.P.bibconeAngle, -Y, Z)
        axis  = du.circumcenter(*[(p - pt_tip).normalize() for p in [pt0, pt1, pt2]])

        A     = pt0 - pt_tip
        B     = axis
        vDown = 2 * (A.dot(B) / B.dot(B)) * B - A
        cone  = Part.makeLine(pt_tip, pt_tip + vDown.normalize() * 600).revolve(pt_tip, axis, 360)

        return BibCone(cone=cone,tip=pt_tip,axis=axis)

    def _back_plate_y(self, z):
        intersections, _ = self.sfc_back_plate.intersect(Part.Line(vec(0, -100, z), vec(0, 100, z)))
        p = intersections[0]
        return p.Y

    @cached_property
    def bib_pts(self):
        # points in x,z
        r = self.P.lensDia/2
        pts2d = [ (-(r+15), 0),  (0, -(r+15)) ]
        pts = [ vec(x, self._back_plate_y(z),z) for x, z in pts2d ]
        return [ *pts, du.flip_x(pts[0]) ]

    @cached_property
    def back_plate_edge(self):
        pt0 = self.back_plate_left_point
        pt2 = du.flip_x(pt0)
        pt1 = self.back_plate_center_point

        # Step 1 — intersect the two surfaces at shape level
        # (assuming you have Face objects for both)
        section = self.bib_cone.section(self.sfc_back_plate)
        edges = section.Edges   # list of intersection curve edges

        # Step 2 — find the edge that passes through pt1
        target_edge = next(e for e in edges if du.point_on_edge(pt1, e))

        # Step 3 — trim to [pt0, pt2] along that edge
        curve = target_edge.Curve
        return Part.Edge(curve, curve.parameter(pt0), curve.parameter(pt2))

    @cached_property
    def bib_edge(self):
        pt0, pt1, pt2 = self.bib_pts

        # Step 1 — intersect the two surfaces at shape level
        # (assuming you have Face objects for both)
        section = self.bib_cone.section(self.sfc_back_plate.toShape())

        # Step 2 — find the edge that passes through pt1
        edges = [ e for e in section.Edges if du.point_on_edge(pt1, e) ]

        # Step 3 — trim to [pt0, pt2] along that edge
        curve = edges[0].Curve
        return Part.Edge(curve, curve.parameter(pt0), curve.parameter(pt2))

    @cached_property
    def sfc_bibroni(self):
        """Face on sfc_bib bounded by:
        - back edge : bib_cone ∩ sfc_back_plate  (trimmed to where the side edges start)
        - left/right: bib_cone ∩ diffuser_base
        - front edge: bezier on sfc_bib joining the two open front endpoints
        All edges are expressed as 2-D curves on sfc_bib so the wire is guaranteed connected.
        """
        section   = self.bib_cone.section(self.diffuser_base)
        all_edges = section.Edges

        left_edge  = next(e for e in all_edges if e.CenterOfMass.x < 0)
        right_edge = next(e for e in all_edges if e.CenterOfMass.x > 0)

        # Orient each side edge so its first point is the back (closer to the back plate)
        axis = self.sfc_back_plate.Axis
        pos  = self.sfc_back_plate.Position
        def dist_bp(pt): return abs(axis.dot(pt - pos))
        def orient_back_first(e):
            fp, lp = e.valueAt(e.FirstParameter), e.valueAt(e.LastParameter)
            return e if dist_bp(fp) < dist_bp(lp) else du.reverse_edge(e)

        left_edge  = orient_back_first(left_edge)
        right_edge = orient_back_first(right_edge)

        pt_bl = left_edge.valueAt(left_edge.FirstParameter)   # back-left
        pt_br = right_edge.valueAt(right_edge.FirstParameter) # back-right
        pt_fl = left_edge.valueAt(left_edge.LastParameter)    # front-left
        pt_fr = right_edge.valueAt(right_edge.LastParameter)  # front-right

        uv = self.sfc_bib.parameter  # 3-D point → (u, v) on sfc_bib

        # Back edge: trim bib_edge to [pt_bl, pt_br], sample in UV to stay on sfc_bib
        bib_e  = self.bib_edge
        p_bl_u = bib_e.Curve.parameter(pt_bl)
        p_br_u = bib_e.Curve.parameter(pt_br)
        lo, hi = sorted([p_bl_u, p_br_u])
        back_uvs = (
            [uv(pt_bl)]
            + [uv(bib_e.Curve.value(t)) for t in du.linspace(lo, hi, 8)[1:-1]]
            + [uv(pt_br)]
        )

        # Side edge UV lists (first point = back, last point = front)
        def edge_uvs(e, n=12): return [uv(pt) for pt in e.discretize(n)]

        uv_fr  = uv(pt_fr)
        uv_fl  = uv(pt_fl)
        uv_mid = tuple((a + b) / 2 for a, b in zip(uv_fr, uv_fl))

        # All four edges as 2-D beziers on sfc_bib → endpoints guaranteed to match
        wire = Part.Wire([
            du.bez2d(back_uvs).toShape(self.sfc_bib),                            # back  L→R
            du.bez2d(edge_uvs(right_edge)).toShape(self.sfc_bib),                # right B→F
            du.bez2d([uv_fr, uv_mid, uv_fl]).toShape(self.sfc_bib),             # front R→L
            du.bez2d(list(reversed(edge_uvs(left_edge)))).toShape(self.sfc_bib), # left  F→B
        ])
        face = Part.Face(self.sfc_bib, wire)
        face.validate()
        face.check()
        return face

    @cached_property
    def bib_cone(self):
        return self._bib_cone.cone

    @cached_property
    def front_ellipse(self):
        e = Part.Ellipse()
        zCenter, e.MajorRadius, e.MinorRadius = find_ellipse_params(self.P.frontHeight*Z, self.pt_diffuser_bottom, self.P.ellipseRatio)
        e.Location = zCenter * Z
        e.Axis = Y
        return e

    @cached_property
    def cone_limiter_side_curve(self):
        sc = self.side_curve()
        pt0, pt1 = map(sc.valueAt, sc.ParameterRange)
        y   = -300*Y
        f   = Part.Face(Part.Wire([ Part.makeLine(y + pt0.z*Z, pt0), sc, Part.makeLine(pt1, y + pt1.z*Z), Part.makeLine(y + pt1.z*Z, y + pt0.z*Z)  ]))
        ext = 600*X
        return du.thicken(f, ext)

    @cached_property
    def front_rim(self):
        return self.front_rim_side_curve

    @cached_property
    def cone_limiter(self):
        return self.cone_limiter_side_curve

    @cached_property
    def front_rim_side_curve(self):
        sc = self.side_curve()
        sc.translate(300*X)
        proj = self.cone.makeParallelProjection(sc, -X)
        e = proj.SubShapes[0].Edges[0]

        fpt, lpt = map(e.valueAt, e.ParameterRange)
        if fpt.x > lpt.x:
            return du.reverse_edge(e)
        return e

    @cached_property
    def back_plate_block(self):
        """Builds the solid block that cuts the back plate."""
        depth = 600
        shp = self.sfc_back_plate.toShape()
        u_min, u_max, v_min, v_max = shp.ParameterRange
        return shp.extrude(depth * shp.normalAt(du.lerp(u_min, u_max, 0.5), du.lerp(v_min, v_max, 0.5)))

    def side_curve(self):
        return Part.BSplineCurve(self.side_curve_pts()).toShape()

    def side_curve_pts(self):
        pt0 = self.pt_diffuser_top
        pt1 = (1*self.pt_diffuser_bottom).scale(0,1,1)
        # top front of the diffuser
        cone_dir = du.angle_vec(self.P.diffuserconeAngle, Y, Z)
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
    def diffuser_base(self):
        """The main diffuser shape, cut by the ellipse and bottom block."""
        return self.cone.common(self.cone_limiter).cut(self.back_plate_block)

    @cached_property
    def back_plate_rim(self):
        s = self.sfc_back_plate.toShape().section(self.cone)
        e = s.SubShapes[0]
        pt = self.pt_diffuser_bottom
        p0 = e.Curve.parameter(pt)
        p1 = e.Curve.parameter(du.flip_x(pt))
        pts = [ e.valueAt(p) for p in du.linspace(p0,p1,40) ]
        if pts[0].x < pts[-1].x:
            pts.reverse()
        return Part.BSplineCurve(pts).toShape()

    @cached_property
    def pt_side_flash(self):
        # Flash head profile points
        return self.flash_point + X*(self.P.flashHeadWidth/2 + self.P.flashHeadSpaceLeft)

    def cover_back_rim_pts(self):
        w  = self.P.flashHeadWidth

        # Flash head profile points
        pt0 = self.flash_point - w/2*X - self.P.flashHeadSpaceLeft*X
        pt1 = pt0 + self.P.flashHeadHeight*Z 
        pt2 = pt1 + self.P.flashHeadSpaceUp*Z 
        # pts = du.lerp_list(pt0,pt1,[0,0.3,0.6,0.8,0.8,1,1,1,1]) + du.lerp_list(pt2, du.flip_x(pt2),[0, 0.5]) 
        pts = [ *map(du.lerp_fn(pt0,pt1),[0,0.3,0.6,0.8,0.8,1,1,1,1]),  *map(du.lerp_fn(pt2, du.flip_x(pt2)),[0, 0.5]) ]

        return [*pts, *map(du.flip_x, pts[:-1][::-1]) ]

    @cached_property
    def cover_back_rim(self):
        """Builds the profile curve for the flash head rim."""
        return Part.BSplineCurve(self.cover_back_rim_pts()).toShape()

    @cached_property
    def cover_base(self):
        """Creates the main cover ruled surface, cut by the back plate block."""
        face = Part.makeRuledSurface(self.cover_back_rim, self.front_rim)
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
        return Part.makeRuledSurface(get_boundary_curve(v_min, False), get_boundary_curve(v_max, True))

    def diffuser_front_tab(self, ps):
        e = du.sub_edge(self.front_rim, ps)
        depths = ( k*self.P.diffuser_front_tabDepth for k in (0.3,-1))
        return dt.tabFaceCurved(e, self.cone.Surface, depths)

    @cached_property
    def bib(self):
        return self._bib.bib

    @cached_property
    def bib_mount(self):
        return self._bib.mount

    def bib_xy_pt(self, x, y):
        vz_probe      = 200 
        raw_pts, _ = self.sfc_bib.intersect(Part.makeLine( vec(x,y, - vz_probe), vec(x,y,vz_probe)).Curve)
        int_pts    = sorted([vec(p.X, p.Y, p.Z) for p in raw_pts], key=lambda p: p.z)
        return int_pts[0]


    @cached_property
    def _bib(self):
        # ── 1. Bib face on the bib-cone surface ───────────────────────────────
        edge            = self.bib_edge
        u_left, u_right = edge.ParameterRange
        pt_left         = edge.valueAt(edge.FirstParameter) 

        y_far    = 150
        x_spread = 50

        uv_left_far, uv_center_far, uv_center, uv_left = map(
            self.sfc_bib.parameter,
            (
                self.bib_xy_pt(pt_left.x - x_spread, y_far),
                self.bib_xy_pt(0, y_far),
                edge.valueAt((u_left + u_right) / 2), 
                pt_left
            )
        )

        def get_uv(uvn):
            un, vn = uvn
            return du.lerp_tuple(
                du.lerp_tuple(uv_center, uv_left, un),
                du.lerp_tuple(uv_center_far, uv_left_far, un),
                vn
            )

        # left edge
        uvs      = [get_uv(pt) for pt in ((1, 0), (0.8, 0.35), (1, 0.7), (1, 1), (0.7, 1))]
        mirrored = [self.sfc_bib.parameter(du.flip_x(self.sfc_bib.value(*uv))) for uv in uvs]
        uvs      = [*uvs, *reversed(mirrored)]

        front_edge = du.bez2d(uvs[::-1]).toShape(self.sfc_bib)

        wire       = Part.Wire([edge, front_edge ]).reversed()

        face  = Part.Face(self.sfc_bib, wire)
        face.validate()
        face.check()

        # ── 2. Mount plate with shoulder flaps ────────────────────────────────
        mount_axis = self.sfc_back_plate.Axis

        flap_width       = 18   # width of each shoulder flap along the edge
        flap_height      = 18   # how far each flap extends inward from the edge
        snap_hole_offset = 10   # distance of the snap hole centre from the edge

        # Mount edge: intersection of bib_face with a plane shifted inward by snapThickness
        mount_plane = Part.Plane(
            self.sfc_back_plate.Position - self.P.snapThickness * mount_axis,
            mount_axis
        )
        mount_edge = mount_plane.toShape().section(face).Edges[0]


        # Parameters on `edge` spanning the inner (non-flap) section
        fw = flap_width + 5
        fw2 = flap_width + 12


        # Parameters on `mount_edge` bounding the two shoulder flaps
        edge_at_dist = du.param_at_dist(edge)
        mount_edge_at_dist = du.param_at_dist(mount_edge)

        # new wire
        def on_bib(*pts):
            return du.bez2d(map(self.sfc_bib.parameter, pts)).toShape(self.sfc_bib)

        u_ml  = mount_edge.FirstParameter
        u_ml1 = mount_edge_at_dist(flap_width)
        u_mr1 = mount_edge_at_dist(flap_width, True)
        u_mr  = mount_edge.LastParameter
        u_el  = edge_at_dist(fw2)
        u_er  = edge_at_dist(fw2, True)

        me, e, fe = mount_edge, edge, front_edge

        wire = Part.Wire([
            Part.Edge(me.Curve, u_ml,  u_ml1),
            on_bib(me.valueAt(u_ml1), e.valueAt(edge_at_dist(fw)),       e.valueAt(u_el)),
            Part.Edge(e.Curve,  u_el,  u_er),
            on_bib(e.valueAt(u_er),   e.valueAt(edge_at_dist(fw, True)), me.valueAt(u_mr1)),
            Part.Edge(me.Curve, u_mr1, u_mr),
            Part.Edge(fe.Curve, fe.Curve.parameter(me.valueAt(u_mr)),
            fe.Curve.parameter(me.valueAt(u_ml))),
        ])

        # new face
        face = Part.Face(self.sfc_bib, wire.reversed())
        face.validate()
        face.check()

        # Two shoulder flaps: left and right, folded inward
        snap_holes = []
        shoulder_spans = [ (0, flap_width, False), (flap_width, 0, True), ]
        flaps = []
        for dist_a, dist_b, from_end in shoulder_spans:
            u_a = mount_edge_at_dist(dist_a, from_end)
            u_b = mount_edge_at_dist(dist_b, from_end)
            
            pt_a, pt_b = map(mount_edge.valueAt, (u_a, u_b))

            v_flap_dir = mount_axis.cross(pt_b - pt_a).normalize()  # inward

            pt_a2, pt_b2 = (pt + flap_height * v_flap_dir for pt in (pt_a, pt_b))

            flap_wire = Part.makePolygon([pt_b, pt_b2, pt_a2, pt_a])
            flap_wire = du.round_corners(flap_wire, [pt_a2, pt_b2], 8)
            flap_wire = Part.Wire([Part.Edge(mount_edge.Curve, u_a, u_b), *flap_wire.Edges])
            flap      = Part.Face(flap_wire)

            pt_hole = du.lerp(pt_a, pt_b, 0.5) + snap_hole_offset * v_flap_dir
            r       = self.P.snapHoleDia / 2
            hole    = Part.Face(Part.Wire(Part.makeCircle(r, pt_hole, mount_axis)))
            hole    = hole.extrude(10 * mount_axis).translate(-5 * mount_axis)

            flaps.append(flap.cut([hole, *(Part.makeSphere(0.5, pt) for pt in (pt_a, pt_b))]))
            snap_holes.append(hole)

        return BibData(bib=Part.Compound([face, *flaps]), snap_holes=snap_holes, face=face)

    @cached_property
    def _smazat_bib(self):
        # ── 1. Bib face on the bib-cone surface ───────────────────────────────
        edge            = self.bib_edge
        u_left, u_right = edge.ParameterRange
        pt_left, _      = (edge.valueAt(u) for u in (u_left, u_right))

        y_far    = 150
        x_spread = 50

        uv_left_far   = self.bib_xy_uv(pt_left + y_far * Y - x_spread * X)
        uv_center_far = self.bib_xy_uv(y_far * Y)
        uv_center     = self.sfc_bib.parameter(edge.valueAt((u_left + u_right) / 2))
        uv_left       = self.sfc_bib.parameter(pt_left)

        def get_uv(uvn):
            un, vn = uvn
            return du.lerp_tuple(
                du.lerp_tuple(uv_center, uv_left, un),
                du.lerp_tuple(uv_center_far, uv_left_far, un),
                vn
            )

        # symmetry
        uvs = list(map(get_uv, ((1, 0), (0.8, 0.35), (1, 0.7), (1, 1), (0.7, 1))))
        uvs = [
            *uvs,
            *reversed([self.sfc_bib.parameter(du.flip_x(self.sfc_bib.value(*uv))) for uv in uvs])
        ]

        bib_front_edge = du.bez2d(uvs[::-1]).toShape(self.sfc_bib)
        bib_wire       = Part.Wire([edge, bib_front_edge])
        bib_face       = Part.Face(self.sfc_bib, bib_wire.reversed())
        bib_face.validate()
        bib_face.check()

        # ── 2. Mount plate with shoulder flaps ────────────────────────────────
        mount_axis = self.sfc_back_plate.Axis

        flap_width       = 18   # width of each shoulder flap along the edge
        flap_height      = 18   # how far each flap extends inward from the edge
        snap_hole_offset = 10   # distance of the snap hole centre from the edge

        # Mount edge: intersection of bib_face with a plane shifted inward by snapThickness
        mount_plane = Part.Plane(
            self.sfc_back_plate.Position - self.P.snapThickness * mount_axis,
            mount_axis
        )
        mount_edge = mount_plane.toShape().section(bib_face).Edges[0]


        edge_at_dist = du.param_at_dist(edge)

        # Parameters on `edge` spanning the inner (non-flap) section
        fw = flap_width + 5
        fw2 = flap_width + 12


        # Parameters on `mount_edge` bounding the two shoulder flaps
        u_mount_left, u_mount_right = mount_edge.ParameterRange
        u_left_shoulder_end    = mount_edge.Curve.parameterAtDistance(flap_width, u_mount_left)
        u_right_shoulder_start = mount_edge.Curve.parameterAtDistance(
            mount_edge.Length - flap_width, u_mount_left
        )

        mount_wire = Part.Wire([
            Part.Edge(mount_edge.Curve, u_mount_left, u_left_shoulder_end),
            du.bez2d(map(self.sfc_bib.parameter, 
                (
                    mount_edge.valueAt(u_left_shoulder_end), 
                    edge.valueAt( edge_at_dist(fw) ),
                    edge.valueAt( edge_at_dist(fw2) ),
                ))).toShape(self.sfc_bib),
            Part.Edge(edge.Curve, edge_at_dist(fw2), edge_at_dist(fw2, True)),
            du.bez2d(map(self.sfc_bib.parameter, (
                edge.valueAt( edge_at_dist(fw2, True) ),
                edge.valueAt( edge_at_dist(fw, True) ),
                mount_edge.valueAt(u_right_shoulder_start)
            ))).toShape(self.sfc_bib),
            Part.Edge(mount_edge.Curve, u_right_shoulder_start, u_mount_right),
            Part.Edge(
                bib_front_edge.Curve,
                bib_front_edge.Curve.parameter(mount_edge.valueAt(u_mount_right)),
                bib_front_edge.Curve.parameter(mount_edge.valueAt(u_mount_left))
            )
        ])
        mount_face = Part.Face(self.sfc_bib, mount_wire.reversed())
        mount_face.validate()
        mount_face.check()

        # Two shoulder flaps: left and right, folded inward
        snap_holes = []
        shoulder_spans = [
            (u_mount_left, u_left_shoulder_end),
            (u_right_shoulder_start, u_mount_right),
        ]
        for u_a, u_b in shoulder_spans:
            pt_a, pt_b = map(mount_edge.valueAt, (u_a, u_b))

            v_flap_dir = mount_axis.cross(pt_b - pt_a).normalize()  # inward

            pt_a2, pt_b2 = (pt + flap_height * v_flap_dir for pt in (pt_a, pt_b))

            flap_wire = Part.makePolygon([pt_b, pt_b2, pt_a2, pt_a])
            flap_wire = du.round_corners(flap_wire, [pt_a2, pt_b2], 8)
            flap_wire = Part.Wire([Part.Edge(mount_edge.Curve, u_a, u_b), *flap_wire.Edges])
            flap      = Part.Face(flap_wire).cut([Part.makeSphere(0.5, pt) for pt in (pt_a, pt_b)])

            pt_hole = du.lerp(pt_a, pt_b, 0.5) + snap_hole_offset * v_flap_dir
            r       = self.P.snapHoleDia / 2
            hole    = Part.Face(Part.Wire(Part.makeCircle(r, pt_hole, mount_axis)))
            hole    = hole.extrude(10 * mount_axis).translate(-5 * mount_axis)

            mount_face = mount_face.fuse(flap.cut(hole))
            snap_holes.append(hole)

        return BibData(bib=mount_face, mount=mount_face, snap_holes=snap_holes, face=bib_face)

    def unwrap(self, shp):
        unwrapped = du.unwrapShape(self.doc, shp )
        rotate_until(unwrapped, du.linspace(0,180,30) )
        return unwrapped

    def diffuser_back_plate_tab(self, ps):
        def tabCut(e, right):
            if right:
                target_dist = e.Length - self.P.tabCutWidth
                u_min = e.Curve.parameterAtDistance(target_dist, e.FirstParameter) 
                u_max = du.lerp(*e.ParameterRange, 1.1)
            else:
                u_min = du.lerp(*e.ParameterRange, -0.1)
                u_max = e.Curve.parameterAtDistance(self.P.tabCutWidth, e.FirstParameter)

            return dt.tabFaceRec(Part.Edge(e.Curve, u_min, u_max), self.cone.Surface,  [0, -1.1*self.P.diffThickness])

        e = du.sub_edge(self.back_plate_rim, ps)
        depths = [k*self.P.diffuserback_plateTabDepth for k in [0.2, -1]]
        tab = dt.tabFaceCurved(e, self.cone.Surface, depths )
        return tab.cut([ tabCut(e,False), tabCut(e,True) ]) 

    @cached_property
    def diffuser_front_inner_tabs(self):
        ftp = self.front_tab_params
        depths = [k*self.P.diffuserInnerTabDepth for k in [-1,0.3] ]
        return [ dt.tabInterFace(self.front_rim, self.cone.Surface, p,q, depths) for p,q in zip(ftp,ftp[1:]) ]

    @cached_property
    def diffuser_prevent_tear_cuts(self):
        # omit first and last parameter (u)
        us = [u for p in self.front_tab_params for u in p][1:-1]
        return [ du.circle2d(self.cone.Surface, self.front_rim.valueAt(u), self.P.preventTearRadius) for u in us]

    @cached_property
    def diffuser(self):
        return self.diffuser_base.fuse([
            *map(self.diffuser_front_tab, self.front_tab_params), 
            *map(self.diffuser_back_plate_tab, self.back_plate_tab_params), 
            *self.diffuser_front_inner_tabs,
            ]).cut(self.diffuser_prevent_tear_cuts)

    @cached_property
    def back_plate_pts(self):
        # flaps by the base
        u_min, u_max, v_min, v_max = self.cover_base.ParameterRange
        return tuple( tuple( self.cover_base.valueAt(u,v) for v in (v_min, v_max) ) for u in (u_min, u_max) )

    @cached_property
    def lens_cut(self):
        # return self.lens_cut_smooth()
        return self.lens_cut_experimental()

    def lens_cut_smooth(self):
        ll, lr = self.back_plate_pts

        l1, l0 = [ (1*pt).scale(1,0,1) for pt in ll ]

        r = self.P.lensDia / 2
        v = (l1-l0).normalize()

        if self.P.backPlateCutShallow:
            pts = [ l0, l0 - 25*v, l0 - 25*v  + 36*X, l0 - 15*v  + 45*X, ]
            ptsCenter = [ r*du.angle_vec(a,X,0.4*Z) for a in du.linspace(170, 10, 8) ]
        else:
            pts = [ l0, l0 - 25*v, l0 - 25*v  + 30*X, l0 - 25*v  + 40*X, ]
            ptsCenter = [ r*du.angle_vec(a,X,0.8*Z) for a in du.linspace(170, 10, 8) ]
        pts += ptsCenter + [ du.flip_x(pt) for pt in pts[::-1] ]
        bez = Part.BSplineCurve(pts).toShape()

        ptsPoly = [ l0, l0-20*X, l0-20*X-100*Z ]
        ptsPoly = [ du.flip_x(p) for p in ptsPoly ] + ptsPoly[::-1]
        poly = Part.makePolygon(ptsPoly)
        f = Part.Face( Part.Wire([bez] + poly.Edges) )
        return f.extrude(200*Y).translate(-100*Y)

    def lens_cut_experimental(self):
        r = self.P.lensDia / 2
        pts = [ r*du.angle_vec(a,X,Z) for a in du.linspace(180, 0, 8) ]

        pts = [ pts[0] + 200*du.angle_vec(10,-Z,-X) ] + pts + [ pts[-1] + 200 *du.angle_vec(10,-Z,X) ]
        bez = Part.BSplineCurve(pts).toShape()

        w = Part.Wire([bez, Part.makeLine(pts[-1], pts[0]) ])
        f = Part.Face(w)
        return f.extrude(200*Y).translate(-100*Y)

    def lens_cut_experimental0(self):
        ll, lr = self.back_plate_pts

        # removing y by scale
        l1, l0 = [ (1*pt).scale(1,0,1) for pt in ll ]

        r = self.P.lensDia / 2
        v = (l1-l0).normalize()

        ptsCenter = [ r*du.angle_vec(a,X,Z) for a in du.linspace(180, 0, 8) ]

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
    def back_plate(self):
        """Creates the shape of the back plate part."""
        pt0, pt1 = self.back_plate_pts[0]
        v_down = (vec(0, pt1.y, pt1.z) - vec(0, pt0.y, pt0.z)).normalize()

        down1 = 8
        down2 = 15 
   
        c = vec(0, self._back_plate_y(0), 0)
        r = self.P.lensDia/2
        # around the lens
        pts_round = [ c + r* du.angle_vec(a, -X, -v_down) for a in du.linspace(0, 180, 20) ]
        pts_round = [ pts_round[0]+10*v_down, *pts_round, pts_round[-1]+10*v_down ] 

        pt2 = pt1 + down1*(pt1-pt0).normalize()
        pt3 = pt2 + down2*v_down 
        pt4 = vec(-r, pt3.y, pt3.z)

        # pts_left = [pt0, pt1, pt2, pt3, pt4, pt4 + 5*(pt5-pt4).normalize() ]
        pts_up = [pt0+5*X, pt0, pt0+5*(pt1-pt0).normalize()]
        pts_left = [pt1, pt2, pt3, pt3+10*X]
        pts_middle = [pt4-10*X,pt4, pt4-10*v_down]

        w = Part.Wire(
            du.connect_edges_with_lines([
                Part.BSplineCurve(pts_up).toShape(), 
                Part.BSplineCurve(pts_left).toShape(),
                Part.BSplineCurve(pts_middle).toShape(),
                Part.BSplineCurve(pts_round).toShape(),
                Part.BSplineCurve(list(map(du.flip_x, reversed(pts_middle)))).toShape(),
                Part.BSplineCurve(list(map(du.flip_x, reversed(pts_left)))).toShape(),
                Part.BSplineCurve(list(map(du.flip_x, reversed(pts_up)))).toShape(),
            ], True))
        f = Part.Face(w)
        return f

    def cover_side_line(self, i):
      u_min, u_max, v_min, v_max = self.cover_base.ParameterRange
      u = (u_min, u_max)[i]
      return [self.cover_base.valueAt(u, v) for v in (v_min, v_max)]

    # side 0 is left, side 1 is right
    def cover_fold(self, side):
        pt0, pt1 = self.pt_side_flash, self.pt_diffuser_bottom_margin
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

        w = du.round_corners(Part.makePolygon(pts), pc, 6)
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

    def make_cover_holes(self, mirror):
        pt0, pt1 = self.pt_side_flash, self.pt_diffuser_bottom_margin
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
        return [
            Part.Face(Part.Wire(Part.makeCircle(self.P.snapHoleDia/2, pt, axis))).extrude(-12*axis)
            for pt in du.linspace(vpt0, vpt1, 2)
        ]

    def UNUSED_back_plate_slot(self, ps):
        sfc = self.sfc_back_plate

        e = du.sub_edge(self.back_plate_rim, ps)
        e_thin = Part.Edge(e.Curve, *[du.edge_at_dist(e, self.P.tabCutWidth, from_end) for from_end in [False,True]]) 

        return Part.makeCompound([
            # thin cut
            dt.slotFace(e, sfc, self.P.diffThickness/3),

            # thick cut
            dt.slotFace(e_thin, sfc, self.P.diffThickness), 

            # small circles
            *[ du.circle2d(sfc, e.valueAt(u), 0.3) for u in e.ParameterRange ]
        ])

    def back_plate_slot(self, us):
        sfc        = self.sfc_back_plate
        plate_axis = sfc.Axis

        slot_edge = Part.Edge(
            self.back_plate_rim.Curve,
            *map(du.lerp_fn(*self.back_plate_rim.ParameterRange), us)
        )

        tab_cut_width = 8
        curve_radius  = 5
        curve_steps   = 10
        curve_angle   = math.degrees(tab_cut_width / curve_radius)

        u_inner_start, u_inner_end = (
            du.edge_at_dist(slot_edge, tab_cut_width, from_end)
            for from_end in (False, True)
        )

        # Tangent step vectors for building the rounded ends
        step_vec_start, step_vec_end = (
            slot_edge.tangentAt(u).normalize() * tab_cut_width / curve_steps
            for u in (u_inner_start, u_inner_end)
        )

        pts = Part.Edge(slot_edge.Curve, u_inner_start, u_inner_end).discretize(12)
        for angle_step in du.linspace(0, curve_angle, curve_steps):
            rot_end   = FreeCAD.Base.Rotation(plate_axis,  angle_step)
            rot_start = FreeCAD.Base.Rotation(plate_axis, -angle_step)
            pts.append(pts[-1] + rot_end.multVec(step_vec_end))
            pts.insert(0, pts[0] - rot_start.multVec(step_vec_start))

        curved_slot = Part.BSplineCurve(pts).toShape()

        return Part.makeCompound([
            #dt.slotFace(curved_slot, sfc, self.P.diffThickness),
            dt.tabFaceRecTan(curved_slot, sfc, [-self.P.diffThickness/2, self.P.diffThickness/2]),
            *[du.circle2d(sfc, curved_slot.valueAt(u), 0.3) for u in curved_slot.ParameterRange],
        ])

    @cached_property
    def back_plate_complete(self):
        """The final back plate shape with cuts for the inner flaps."""

        return self.back_plate.cut([
            *self.make_cover_holes(False), 
            *self.make_cover_holes(True), 
            *map(self.back_plate_slot, self.back_plate_tab_params),
            *self._bib.snap_holes,
        ])

    def cover_flash_flap(self, side):
        depth = 35
        heightFromBottom =  4
        heightFromTop     = 4
        cv = self.cover_back_rim

        # extrude cover_back_rim backwards and cut from it
        p1, p2 = [ cv.Curve.parameterAtDistance(d) for d in [heightFromBottom,self.P.flashHeadHeight-heightFromTop]]
        pts = [ cv.valueAt(p1), cv.valueAt(p2) ]
        pts += [pts[1]-depth*Y,pts[0]-depth*Y,pts[0]]

        # "moving" to center (eliminate X)
        pts = [ vec(0,pt.y,pt.z) for pt in pts ]
        w = du.round_corners(Part.makePolygon(pts), pts[2:4], 5)

        sidevec = X * (100 if side == 1 else -100)
        cutter = Part.Face(w).extrude(sidevec)

        # cutting holes for the tightening strap
        strapWidth     = 20
        strapThickness = 2
        strapMargin    = 5
        scutters = []
        for pt in du.lerp_list(pts[0], pts[1], [0.35, 0.65]):
            spts = [ pt + j*strapThickness/2*Z - (strapMargin+i*strapWidth)*Y for i,j in [ (0,-1), (1,-1), (1,1), (0,1) , (0,-1) ]]
            w = du.round_corners(Part.makePolygon(spts), spts, 0.5)
            scutters.append(Part.Face(w).extrude(sidevec))

        return cv.extrude(-(depth+10)*Y).common(cutter).cut(scutters)

    @cached_property
    def cover(self):
        """Builds the cover with cuts for the flaps and other features."""

        # small spheres marking flash head corners
        pt0 = self.flash_point + self.P.flashHeadWidth/2*X
        pt1 = pt0 + Z*(self.P.flashHeadHeight+2)
        flashMarks = [ Part.makeSphere(2.5).translate(pt) for pt in [pt0, pt1, du.flip_x(pt0), du.flip_x(pt1)] ]

        appendages = []
        for side in (0, 1):
            appendages.append( self.cover_flash_flap(side))
            if self.P.coverConnectedByTabs:
                stitch = self.cover_back_plate_stitch(side)
                appendages += stitch.tabs() + stitch.stopper_tabs()
            else:
                appendages.append( self.cover_fold(side) )

        return self.cover_base.fuse(appendages).cut(self.cover_front_slots + flashMarks)

    @cached_property
    def cover_front_slots(self):
        """Builds the cutting shapes for the cover front flaps."""
        return [ dt.slotFace(du.sub_edge(self.front_rim, ps), self.cover_base.Surface, self.P.diffThickness) for ps in self.front_tab_params ]

    @cached_property
    def cover_left(self):
        return self.cover_part(0)

    @cached_property
    def cover_right(self):
        return self.cover_part(1)

    @cached_property
    def flash_head(self):
        """Builds the box representing the flash head."""
        w = self.P.flashHeadWidth
        d = self.P.flashHeadDepth
        h = self.P.flashHeadHeight
        box = Part.makeBox(w, d, h)
        box.translate(-w/2*X + (self.P.topHeight - self.P.flashHeadHeight)*Z - Y*self.P.lensDepth)
        return box

    @cached_property
    def pt_diffuser_top(self):
        z = self.P.lensDia/2
        return vec(0, self._back_plate_y(z), z)

    @cached_property
    def pt_diffuser_bottom(self):
        x = 45 + self.P.lensDia/2
        z = -self.P.lensDia/5 
        return vec(x, self._back_plate_y(z), z)

    @cached_property
    def pt_diffuser_bottom_margin(self):
        ptUp = self.pt_side_flash
        ptBottom = self.pt_diffuser_bottom
        return ptBottom + (ptBottom-ptUp).normalize()*self.P.coverFrontMargin

    def show_unwrapped(self, pt0):
        W,H = 400,300
        pt1 = pt0+W*X  
        pt2 = pt1+H*Y
        pt3 = pt0+H*Y
        Part.show(Part.makePolygon([pt0,pt1,pt2,pt3,pt0]))

        # self.cover_unwrapped.rotate(O,Z,90)

        bb = self.cover_unwrapped.BoundBox
        self.cover_unwrapped.translate(pt0 +5 *X + 5*Y -X*bb.XMin-Y*bb.YMin)
        Part.show(self.cover_unwrapped, "cover-unwrapped")

        diff = self.diff_unwrapped
        diff.rotate(O,Z,90)
        bb = diff.BoundBox
        diff.translate(pt0 + 5*Y + 525*X -X*bb.XMin-Y*bb.YMin)
        Part.show(diff, "diff-unwrapped")

        bt = self.back_plate_unwrapped
        bb = bt.BoundBox
        bt.translate(pt0 + 285*X + 343*Y -X*bb.XMin-Y*bb.YMin)
        Part.show(bt, "back-plate-unwrapped")

    def solids(self):
        return [ self.cover, self.back_plate_complete, self.diffuser, self.flash_head]

    @cached_property
    def cover_stitch(self):
        params = st.Params(
            tabIndent=self.P.cover_stitchTabIndent, 
            numTabs=self.P.cover_stitchNumTabs, 
            shift=self.P.cover_stitchShift,
            thickness=self.P.diffThickness,
            tabHeight=self.P.cover_stitchTabHeight,
            dir=-1,
        )

        u_min, u_max, v_min, v_max = self.cover_base.ParameterRange
        u = du.lerp(u_min, u_max, self.P.coverSplitAt)
        segs = du.poly2d([ (u,v_min), (u,v_max) ])

        sfc = self.cover_base.Surface
        [e] = [ seg.toShape(sfc) for seg in segs ]
        return st.Stitch(e, sfc, params)

    def cover_stitch_edge(self, side):
        sfc = self.cover_base.Surface
        u_min, u_max, v_min, v_max = self.cover_base.ParameterRange
        u = du.lerp(u_min, u_max, self.P.coverSplitAt)

        # for left, the edge is shifted
        if side == 0:
            u_vec, _ = sfc.tangent(u, (v_min+v_max)/2)
            pts = [ 
                sfc.parameter(sfc.value(u,v) + self.P.cover_stitchMargin*u_vec) for v in du.linspace(v_min,v_max, 10)
            ]
            seg = du.bez2d(pts)
        else:
            [seg] = du.poly2d([(u,v_min), (u,v_max)])

        return seg.toShape(sfc) 

    def cover_part(self, side):
        e = self.cover_stitch_edge(side)
        body = BOPTools.SplitAPI.slice(self.cover_base, [e], mode="Standard", tolerance=0.01).SubShapes[side]
        body = body.cut(self.cover_front_slots)

        stitch = self.cover_stitch
        if side == 0:
            body = body.cut(stitch.slots())
        else:
            body = body.fuse(stitch.tabs() + stitch.stopper_tabs())

        if self.P.coverConnectedByTabs:
            stitch = self.cover_back_plate_stitch(side)
            body = body.fuse( stitch.tabs() + stitch.stopper_tabs() )
        else:
            body = body.fuse( self.cover_fold(side) )

        body = body.fuse( self.cover_flash_flap(side))

        # mount hole
        r = self.P.snapHoleDia / 2
        f = Part.Face(Part.Wire([Part.makeCircle(r)]))
        cyl = f.rotate(O,Y,90).translate(self.flash_point + 20*Y + 12*Z ).extrude(100*X).translate(-50*X)
        body = body.cut(cyl)

        return body

    def back_plate_stitch_params(self, side):
        return st.Params(
            tabIndent=self.P.back_plate_stitchTabIndent, 
            numTabs=self.P.back_plate_stitchNumTabs, 
            shift=self.P.back_plate_stitchShift,
            thickness=self.P.diffThickness,
            tabHeight=self.P.back_plate_stitchTabHeight,
            tabOverlay=0,
            dir=(1 if side == 0 else -1),
        )

    # back plate stitch(es)
    def back_plate_stitch(self, side):
        p0,p1 = self.back_plate_pts[side]
        e = Part.makeLine(p1,p0)
        return st.Stitch(e, self.sfc_back_plate, self.back_plate_stitch_params(side))

    def cover_back_plate_stitch(self, side):
        p0,p1 = self.back_plate_pts[side]
        e = Part.makeLine(p1,p0)
        sfc = self.sfc_back_plate

        p2 = p1 - (1 if side == 0 else -1) *Y 
        sfc = Part.Face(Part.makePolygon([p0,p1,p2])).Surface

        return st.Stitch(e, sfc, self.back_plate_stitch_params(side))

