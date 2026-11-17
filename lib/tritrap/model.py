import FreeCAD, Part, math

from functools import cached_property
import diffuser.util as du

from tritrap.params import Params  # noqa: F401 (re-exported)
from diffuser.util import vec, Y, Z, O
from diffuser.geometry import rotate_until, landscape_diagonal

class Model:
    """
    Geometric model of a three vane trap: flat vanes in a pinwheel around the Z
    axis, above a funnel and under a top disc. The vanes' planes are shifted off
    the axis, so that seen from above they enclose an equilateral triangle with
    side triangleSide. Each vane runs along one side of the triangle, from the
    corner where it butts against the face of the previous vane, past the next
    corner, where the next vane butts against it, out to the rim.

    A vane is built in its own frame, the XZ plane with x along the vane and
    x = 0 at the foot of the axis; place() puts it into the assembly. All parts
    are returned in their assembled position.
    """

    angles = (0, 120, 240)

    def __init__(self, doc, P):
        self.doc = doc
        self.P = P

    @cached_property
    def offset(self):
        """Distance of the vanes' planes from the Z axis, the triangle's inradius."""
        return self.P.triangleSide/(2*math.sqrt(3))

    def place(self, shp, ang):
        """Shape built in the vane frame, moved to the vane at angle ang."""
        return shp.copy().translate(vec(y=-self.offset)).rotate(O, Z, ang)

    @cached_property
    def funnel_height(self):
        P = self.P
        return (P.width - P.innerWidth)/(2*math.tan(math.radians(P.funnelAngle)))

    @cached_property
    def height(self):
        """Height of the vanes' top edge: the funnel plus the straight part above it."""
        return self.funnel_height + self.P.straightHeight

    def cone_z(self, x):
        """Height of the funnel surface at x in the vane frame; the vane's plane cuts
        the cone along a hyperbola, since it misses the axis."""
        P = self.P
        r = math.hypot(x, self.offset)
        return (r - P.innerWidth/2)/math.tan(math.radians(P.funnelAngle))

    def cone_point(self, x):
        return vec(x, 0, self.cone_z(x))

    @cached_property
    def x_outer(self):
        """Vane frame x of the vane's outer edge, on the funnel rim."""
        return math.sqrt((self.P.width/2)**2 - self.offset**2)

    @cached_property
    def x_inner(self):
        """Vane frame x of the vane's inner end: the triangle corner, moved along the
        vane until both corners of its end clear the face of the vane it meets at 60°."""
        P = self.P
        return -P.triangleSide/2 + math.sqrt(3)/2*P.thickness + P.vaneInnerGap

    @cached_property
    def funnel_tab(self):
        """Ends of the vane's tab through the funnel, both on the funnel surface: the
        upper one funnelTabInset in from the outer edge, the lower one funnelTabLength
        from it along a straight chord."""
        P = self.P
        top = self.cone_point(self.x_outer - P.funnelTabInset)
        x = top.x - P.funnelTabLength
        for _ in range(20):     # keep the slope, the chord is nearly straight
            d = top - self.cone_point(x)
            x = top.x - P.funnelTabLength*d.x/d.Length
        return top, self.cone_point(x)

    @cached_property
    def vane_bottom_z(self):
        """Height of the vanes' bottom edge, the lower end of the funnel tab."""
        return self.funnel_tab[1].z

    def _vane(self):
        """Vane in the vane frame. Going round its outline from the inner bottom
        corner: the bottom edge, the outer edge with the step of the tab that goes
        through the funnel, the funnel surface up to the rim, the outer edge up into
        the top tab, which goes through a pie slice, and the top edge back to the
        inner end, over the tab through the central disc. The upper end of the
        funnel tab, the funnel rim and the tabs' base corners stay sharp, the
        funnel and the top sit there; the other corners are rounded. Both top
        tabs get a horizontal cut at their base, holding the top parts. Down the
        inner edge are the join tabs, which go through the join slits of the vane
        it butts against."""
        P = self.P
        r, xi, xo, h = P.vaneCornerRadius, self.x_inner, self.x_outer, self.height
        tab_top, _ = self.funnel_tab
        bz = self.vane_bottom_z
        tw, th = P.topTabWidth, P.topTabHeight
        ci, co, cth = *self.center_tab, P.topCenterTabHeight
        # the top tabs' corners facing each other are rounded asymmetrically, cut back
        # further along the top than down the side; the other two symmetrically
        tr, tl, ts = P.topTabCornerRadius, P.topTabCornerCutTop, P.topTabCornerCutSide
        pts = [(vec(xi, 0, bz), r), (vec(xo, 0, bz), r), (vec(xo, 0, tab_top.z), r),
               tab_top, self.cone_point(xo),
               (vec(xo, 0, h + th), tr), (vec(xo - tw, 0, h + th), tl, ts), vec(xo - tw, 0, h),
               vec(co, 0, h), (vec(co, 0, h + cth), ts, tl), (vec(ci, 0, h + cth), tr), vec(ci, 0, h),
               (vec(xi, 0, h), r)]
        # the join tabs' tip corners are rounded all along the sides, from the vane's
        # edge, and much further along the tip
        js, jt, jx = P.joinTabHeight, P.joinTabCornerCutTip, xi - P.joinTabHeight
        for z0, z1 in reversed(self.join_tabs):     # going down the inner edge
            pts += [vec(xi, 0, z1), (vec(jx, 0, z1), js, jt), (vec(jx, 0, z0), jt, js), vec(xi, 0, z0)]
        return Part.Face(du.rounded_polygon(pts)).cut(
            [self._center_tab_cut(), self._top_tab_cut(), self._hang_hole()]
            + self._join_slits() + self._join_tab_cuts())

    def _hang_hole(self):
        """Hole for hanging the trap, in the middle of the central disc's tab, its
        bottom edge hangHoleGap above the central disc and pie slice lying on the vane."""
        P = self.P
        t, r = P.thickness, P.hangHoleDia/2
        ci, co = self.center_tab
        z = self.height + 2*t + P.hangHoleGap + r
        return Part.makeCylinder(r, 2*t, vec((ci + co)/2, -t, z), Y)

    @cached_property
    def join_tabs(self):
        """Bottom and top heights of the join tabs on the vane's inner edge, from the
        bottom up: the edge split into equal shares, a tab centered in each."""
        P = self.P
        bz, w, n = self.vane_bottom_z, P.joinTabWidth, P.joinTabCount
        share = (self.height - bz)/n
        return [(bz + (i + 0.5)*share - w/2, bz + (i + 0.5)*share + w/2) for i in range(n)]

    @cached_property
    def join_slit_width(self):
        """The join tabs cross the vane they go through at 60°, so the slit, and the
        room it takes along the tab, is √3 sheet thicknesses wide."""
        return math.sqrt(3)*self.P.thickness + self.P.slotClearance

    def _join_slits(self):
        """Slits through the vane at the triangle corner where the next vane butts
        against it, for that vane's join tabs, in the vane frame. Each is straight
        along the tab's neck between its cuts; past them, toward both ends of the
        tab, it bends in the vane's plane to the vane's outer side, toward its
        outer edge, so the tab's barbs bend aside on their way through and spring
        back behind the vane."""
        P = self.P
        t, w, c = P.thickness, self.join_slit_width, P.joinTabCutLength
        x0, d = P.triangleSide/2, P.joinSlitCurveOffset
        l = c + P.joinSlitEndClearance     # how far each arc reaches up or down
        r = (l*l + d*d)/(2*d)              # arc tangent to the straight part, d outward after l

        def arc(z, sz):
            """Arc from the straight part's end at height z, up (sz 1) or down (sz -1),
            bending outward, to +x."""
            a = math.asin(l/r)
            def at(u): return vec(x0 + r - r*math.cos(u), 0, z + sz*r*math.sin(u))
            return Part.Arc(at(0), at(a/2), at(a)).toShape()

        slits = []
        for z0, z1 in self.join_tabs:
            path = Part.Wire([arc(z0 + c, -1).reversed(), Part.makeLine(vec(x0, 0, z0 + c), vec(x0, 0, z1 - c)),
                              arc(z1 - c, 1)])
            face = Part.Face(path.makeOffset2D(w/2, openResult=False))
            slits.append(face.translate(vec(y=-t)).extrude(vec(y=2*t)))
        return slits

    def _join_tab_cuts(self):
        """Cuts along the vane's inner edge into both ends of each join tab, joinTabCutLength
        long, as wide as the room the vane it goes through takes along it."""
        P = self.P
        t, w, l = P.thickness, self.join_slit_width, P.joinTabCutLength
        x0 = self.x_inner - w
        cuts = []
        for z0, z1 in self.join_tabs:
            cuts += [Part.makeBox(w, 2*t, l + t).translate(vec(x0, -t, z0 - t)),
                     Part.makeBox(w, 2*t, l + t).translate(vec(x0, -t, z1 - l))]
        return cuts

    def _top_tab_cut(self):
        """Horizontal cut at the base of the outer top tab, a sheet thick for the pie
        slice, from its inner edge outwards."""
        P = self.P
        t, x0 = P.thickness, self.x_outer - P.topTabWidth
        return Part.makeBox(P.topTabCutWidth + t, 2*t, t).translate(vec(x0 - t, -t, self.height))

    @cached_property
    def center_tab(self):
        """Vane frame x of the inner and outer end of the tab through the central disc,
        its outer end topCenterTabRimGap in from the disc's rim."""
        P = self.P
        co = math.sqrt((P.topCenterDia/2 - P.topCenterTabRimGap)**2 - self.offset**2)
        return co - P.topCenterTabLength, co

    def _center_tab_cut(self):
        """Horizontal cut at the base of the central disc's tab, in from its outer edge,
        high enough for the central disc and the pie slice lying on it."""
        P = self.P
        t, (_, co) = P.thickness, self.center_tab
        return Part.makeBox(P.topCenterTabCutWidth + t, 2*t, 2*t).translate(
            vec(co - P.topCenterTabCutWidth, -t, self.height))

    def _center_slot(self):
        """Box through the central disc where the vane's tab goes through it, in the vane
        frame. It stops short of the tab's base cut, so the disc slides into it."""
        P = self.P
        w, t = P.thickness + P.slotClearance, P.thickness
        ci, co = self.center_tab
        l = co - P.topCenterTabCutWidth - ci
        return Part.makeBox(l, w, 2*t).translate(vec(ci, -w/2, self.height - t))

    @cached_property
    def vaneParts(self):
        vane = self._vane()
        return [self.place(vane, ang) for ang in self.angles]

    def _funnel_slot(self):
        """Slab through the funnel where the vane's tab crosses it, in the vane frame."""
        P = self.P
        a, b = self.funnel_tab
        n = (b - a).normalize().cross(Y)*P.thickness     # reaches past the funnel surface on both sides
        face = Part.Face(Part.makePolygon([a - n, b - n, b + n, a + n, a - n]))
        return du.thicken(face, vec(y=P.thickness + P.slotClearance))

    @cached_property
    def funnel_tab_angle(self):
        """Angle around the Z axis of the middle of the funnel tab of the vane at angle 0."""
        a, b = self.funnel_tab
        return math.degrees(math.atan2(-self.offset, (a.x + b.x)/2))

    @cached_property
    def funnelParts(self):
        """Three cone segments, each a third of the way round between two vanes'
        funnel tabs, so the seams lie on the tabs: the tab goes through both
        overlapping layers and pins them together. Neighbors overlap by a strip
        funnelOverlap wide along the seam. Near the inner rim, each segment has a
        tongue past its counterclockwise edge, which lies on the next segment and
        tucks through a slit in it; the segments are alike, each with one tongue
        and one slit, near its clockwise edge."""
        P = self.P
        line = Part.makeLine(vec(P.innerWidth/2), vec(P.width/2, 0, self.funnel_height))
        cone = line.revolve(O, Z, 360)
        slots = [self.place(self._funnel_slot(), ang) for ang in self.angles]
        parts = []
        for ang in self.angles:
            center = self.funnel_tab_angle + 60 + ang
            outline = self._wedge(center, P.funnelOverlap/2, -1, self.funnel_height + 1)
            tongue = self._seam_prism(self._funnel_tongue(), center + 60)
            slit = self._seam_prism(self._funnel_slit(), center - 60)
            parts.append(cone.common(outline.fuse(tongue)).cut(slots + [slit]))
        return parts

    def _seam_prism(self, face, seam):
        """Vertical prism through the funnel of a plan face drawn in the seam frame:
        x along the seam's radial line, y across it, counterclockwise."""
        return face.copy().rotate(O, Z, seam).extrude(vec(z=self.funnel_height + 2))

    def _seam_span(self):
        """Seam frame x of the ends of the tongue, and the slit, along the seam:
        funnelTongueRimDist up the slope from the inner rim, funnelTongueWidth wide
        along the slope."""
        P = self.P
        s = math.sin(math.radians(P.funnelAngle))   # slope to plan
        c = P.innerWidth/2 + P.funnelTongueRimDist*s
        return c - P.funnelTongueWidth/2*s, c + P.funnelTongueWidth/2*s

    def _funnel_tongue(self):
        """Plan face of the tongue in the seam frame, from inside the segment out past
        its edge by funnelTongueLength, the outer corners rounded."""
        P = self.P
        x0, x1 = self._seam_span()
        e, r = P.funnelOverlap/2, P.funnelTongueCornerRadius
        y1 = e + P.funnelTongueLength
        pts = [vec(x0, e - 1, -1), (vec(x0, y1, -1), r), (vec(x1, y1, -1), r), vec(x1, e - 1, -1)]
        return Part.Face(du.rounded_polygon(pts))

    def _funnel_slit(self):
        """Plan face of the slit in the seam frame, for the previous segment's tongue,
        funnelSlitGap past that segment's edge, along the seam, its ends rounded."""
        P = self.P
        x0, x1 = self._seam_span()
        w = P.funnelSlitWidth
        y, r = P.funnelOverlap/2 + P.funnelSlitGap + w/2, w/2
        def at(x, dy): return vec(x, y + dy, -1)
        # a straight line alone has no plane for makeOffset2D, so the stadium is drawn
        return Part.Face(Part.Wire([
            Part.makeLine(at(x0, -r), at(x1, -r)),
            Part.Arc(at(x1, -r), at(x1 + r, 0), at(x1, r)).toShape(),
            Part.makeLine(at(x1, r), at(x0, r)),
            Part.Arc(at(x0, r), at(x0 - r, 0), at(x0, -r)).toShape()]))

    def _top_slot(self):
        """Box through the pie slice where the vane's outer top tab goes through it, in
        the vane frame, open to the rim. It starts past the tab's base cut, so the
        slice slid in from outside holds in that cut with the strip before the slot."""
        P = self.P
        w, t = P.thickness + P.slotClearance, P.thickness
        x0 = self.x_outer - P.topTabWidth + P.topTabCutWidth
        l = P.width/2 + P.topOverlap - x0 + t     # past the rim
        return Part.makeBox(l, w, 2*t).translate(vec(x0, -w/2, self.height - t))

    def _disc(self, r):
        return Part.Face(Part.Wire(Part.makeCircle(r, vec(z=self.height), Z)))

    def _wedge(self, center, half_width, z0=None, z1=None):
        """Prism from z0 to z1, through the top by default, around the angle center,
        between two lines parallel to the radial seams at center ± 60°, each
        half_width out past its seam."""
        P = self.P
        u = vec(math.cos(math.radians(center)), math.sin(math.radians(center)))
        def ray(ang): return vec(math.cos(math.radians(ang)), math.sin(math.radians(ang)))
        apex = -u*(half_width/math.sin(math.radians(60)))   # where the two lines meet
        L = 2*P.width
        pts = [apex, apex + ray(center - 60)*L, apex + u*2*L, apex + ray(center + 60)*L]
        if z0 is None:
            z0, z1 = self.height - P.thickness, self.height + P.thickness
        face = Part.Face(Part.makePolygon([p + vec(z=z0) for p in pts + pts[:1]]))
        return face.extrude(vec(z=z1 - z0))

    @cached_property
    def topParts(self):
        """The top lying on the vanes: a central disc and three pie slices over it,
        each centered on a vane's outer top tab and slotted for it. The slices
        overlap each other by a strip topSideOverlap wide along the seams halfway
        between the tabs. Inward each slice reaches over the central disc to
        topSliceReach past the start of the central tab's base cut, measured along
        the vane, with a slit from there out to the cut, embracing the tab. All
        lie in one plane here; in reality they're stacked."""
        P = self.P
        center = self._disc(P.topCenterDia/2).cut(
            [self.place(self._center_slot(), ang) for ang in self.angles])
        ring = self._disc(P.width/2 + P.topOverlap).cut(self._disc(self.slice_inner_radius))
        tab_angle = math.degrees(math.atan2(-self.offset, self.x_outer - P.topTabWidth/2))
        cuts = [self._top_slot(), self._slice_slit()]
        slices = [ring.common(self._wedge(tab_angle + ang, P.topSideOverlap/2))
                      .cut([self.place(c, ang) for c in cuts])
                  for ang in self.angles]
        return [center] + slices

    @cached_property
    def slice_inner_x(self):
        """Vane frame x where the pie slice's inner arc crosses the vane: topSliceReach
        in from the start of the central tab's base cut."""
        _, co = self.center_tab
        return co - self.P.topCenterTabCutWidth - self.P.topSliceReach

    @cached_property
    def slice_inner_radius(self):
        return math.hypot(self.slice_inner_x, self.offset)

    def _slice_slit(self):
        """Box through the pie slice along the vane, from its inner arc out to the
        central tab's base cut, in the vane frame; the tab goes through it."""
        P = self.P
        w, t = P.thickness + P.slotClearance, P.thickness
        x0 = self.slice_inner_x - t     # from past the arc
        return Part.makeBox(P.topSliceReach + t, w, 2*t).translate(vec(x0, -w/2, self.height - t))

    def unwrap(self, shp, cost=landscape_diagonal):
        """Part laid flat in the XY plane at z=0. Flat parts are just turned into
        the plane, keeping their exact edges; curved ones (the funnel) are
        flattened through a mesh and turned to the angle with the lowest cost of
        their bounding box, see rotate_until."""
        if all(isinstance(f.Surface, Part.Plane) for f in shp.Faces):
            flat = shp.copy()
            rot = FreeCAD.Rotation(shp.Faces[0].normalAt(0, 0), Z)
            flat.Placement = FreeCAD.Placement(O, rot).multiply(flat.Placement)
        else:
            flat = rotate_until(du.unwrapShape(self.doc, shp), du.linspace(0, 180, 360), cost)
        return flat.translate(vec(z=-flat.BoundBox.ZMin))
