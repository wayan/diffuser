import FreeCAD, Part, Mesh, MeshPart, math

import BOPTools.SplitAPI

from functools import cached_property
import diffuser.util as du

from crosstrap.params import Params  # noqa: F401 (re-exported)
from diffuser.util import vec, X, Y, Z, O
from diffuser.geometry import rotate_until, landscape_diagonal

def flip_x(p):
    """du.flip_x for a du.rounded_polygon point, plain or (point, r)."""
    return (du.flip_x(p[0]), p[1]) if isinstance(p, tuple) else du.flip_x(p)

class Model:
    """
    Geometric model of a cross vane trap: two flat vanes joined by a halving
    joint. vaneXZ is slotted down from the top edge and lies in the XZ
    plane, vaneYZ is slotted up from the bottom edge and lies in the
    YZ plane. Both are returned in their assembled position, crossing at the
    Z axis with the bottom edge at vane_bottom_z.
    """

    def __init__(self, doc, P):
        self.doc = doc
        self.P = P

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

    @cached_property
    def funnel_height(self):
        P = self.P
        return (P.width - P.innerWidth)/(2*math.tan(math.radians(P.funnelAngle)))

    @cached_property
    def height(self):
        """Height of the vane's top edge: the funnel plus the straight part above it."""
        return self.funnel_height + self.P.straightHeight

    def _funnel_tab(self):
        """Funnel line points of the vane tab in the XZ plane at +X: the outer end of
        the funnel line, the upper end of the tab and the unit direction down the line."""
        P = self.P
        funnel_top = vec(P.width/2, 0, self.funnel_height)
        down = (vec(P.innerWidth/2) - funnel_top).normalize()

        # funnelTabInset in from the outer edge, measured horizontally
        tab_inner = funnel_top + down * (P.funnelTabInset/math.sin(math.radians(P.funnelAngle)))
        return funnel_top, tab_inner, down

    @cached_property
    def vane_bottom_z(self):
        """Height of the vane's bottom edge, the lower end of the funnel tab."""
        _, tab_inner, down = self._funnel_tab()
        return (tab_inner + down*self.P.funnelTabLength).z

    @cached_property
    def top_tab_x(self):
        """Distance of the top tab centers from the Z axis, the tabs flush with the vane's outer edge."""
        return (self.P.width - self.P.topTabWidth)/2

    def _inner_tabs(self, main_from_top):
        """Center x, width and pin hole diameter of the tabs on the right half of the
        vane's top edge between the axis and the side tab, outermost first: the mid
        tab on vaneXZ, the center tab, at x 0, on vaneYZ."""
        P = self.P
        if main_from_top:
            return [(P.topMidTabGap + P.topMidTabWidth/2, P.topMidTabWidth, P.topMidTabHoleDia)]
        return [(0, P.topCenterTabWidth, P.topTabHoleDia)]

    def _vane_outline(self, main_from_top):
        """Right half of the vane outline in the XZ plane for du.rounded_polygon,
        from the bottom outer corner up the outer edge and along the top edge to
        the inner side of the top tab. The step below the funnel line is the tab
        that goes through the funnel, the tab on the top edge goes through the
        top disc; it is flush with the outer edge, which runs straight up into it.
        The outer corners are rounded; tab_inner and funnel_top stay sharp,
        because the funnel lies on the edge between them and its slot starts at
        tab_inner, and so does the top tab's inner base corner, where the top
        disc sits; its inner top corner gets a larger rounding. The outline then goes on over the inner tabs, their base
        corners sharp as well; a tab centered on the axis only by its right half."""
        P = self.P
        r, x, h = P.vaneCornerRadius, P.width/2, self.height
        funnel_top, tab_inner, _ = self._funnel_tab()
        tx, tw, oth = self.top_tab_x, P.topTabWidth, P.topOuterTabHeight
        th = P.topTabHeight
        pts = [(vec(x, 0, self.vane_bottom_z), r), (vec(x, 0, tab_inner.z), r),
               tab_inner, funnel_top, (vec(x, 0, h + oth), r),
               (vec(tx - tw/2, 0, h + oth), P.topOuterTabInnerRadius), vec(tx - tw/2, 0, h)]
        for c, w, _ in self._inner_tabs(main_from_top):
            pts += [vec(c + w/2, 0, h), (vec(c + w/2, 0, h + th), r)]
            if c > 0:
                pts += [(vec(c - w/2, 0, h + th), r), vec(c - w/2, 0, h)]
        return pts

    def _vane_blank(self, main_from_top):
        """Unslotted vane in the XZ plane, centered on the Z axis."""
        pts = self._vane_outline(main_from_top)
        return Part.Face(du.rounded_polygon(pts + [flip_x(p) for p in pts[::-1]]))

    def _slot(self, z0, h):
        """Slot box h high through a sheet in the XZ plane, centered on the Z axis, starting at z0."""
        P = self.P
        w = P.thickness + P.slotClearance
        return Part.makeBox(w, 2*P.thickness, h).translate(vec(-w/2, -P.thickness, z0))

    def _vane(self, main_from_top):
        """Vane with the half height slot on one edge. The vane slotted from the top
        also gets a short slot on the bottom edge for the connector, the one slotted
        from the bottom gets snapper holes for it. Both get their inner tabs on the
        top edge, which go through the top disc, with pin holes."""
        P = self.P
        bz = self.vane_bottom_z
        h, th = (self.height - bz)/2, P.topSlotHeight

        if main_from_top:
            slots = [self._slot(self.height - h, h), self._slot(bz, th)]
        else:
            slots = [self._slot(bz, h)] + self._connector_holes()
        return self._vane_blank(main_from_top).cut(
            slots + self._inner_tab_holes(main_from_top)
            + self._top_tab_cuts() + self._bottom_tab_holes() + self._funnel_tab_cuts())

    def _funnel_tab_cuts(self):
        """Notches for a rope or rubber band hanging something under the funnel:
        thin cuts through both funnel tabs, parallel to the funnel line and
        funnelTabCutGap out from it, open to the tab's top edge and running
        funnelTabCutLength down along the line, measured on the cut's center line.
        The closed end is a full semicircle, against tearing."""
        P = self.P
        # widened by the funnel's thickness, which lies along the funnel line in the cut
        t, w, g = P.thickness, P.funnelTabCutWidth + P.thickness, P.funnelTabCutGap
        _, tab_inner, down = self._funnel_tab()
        out = down.cross(Y)     # perpendicular to the funnel line, away from the funnel

        def at(o, s): return tab_inner + out*o + down*s

        # how far up the line a point o out from it meets the tab's top edge, level with tab_inner
        def s_edge(o): return -o*out.z/down.z

        # where the straight sides end and the semicircle starts
        s_bot = s_edge(g + w/2) + P.funnelTabCutLength - w/2
        # the open end reaches w past the top edge on both sides, clear of the vane
        s_open = s_edge(g + w) - w
        a, b, c, d = at(g, s_open), at(g, s_bot), at(g + w, s_bot), at(g + w, s_open)
        wire = Part.Wire([Part.makeLine(a, b), Part.Arc(b, at(g + w/2, s_bot + w/2), c).toShape(),
                          Part.makeLine(c, d), Part.makeLine(d, a)])
        cut = Part.Face(wire).translate(vec(y=-t)).extrude(vec(y=2*t))
        return [cut, cut.mirror(O, X)]

    def _bottom_tab_holes(self):
        """Hanger hole cylinders through both funnel tabs, for the wires holding the
        collection cup. They sit as close to the axis as the funnel allows, for
        rigidity: bottomTabHoleIndent from the funnel line and from the tab's bottom edge."""
        P = self.P
        r, t, i = P.bottomTabHoleDia/2, P.thickness, P.bottomTabHoleIndent
        _, tab_inner, down = self._funnel_tab()
        out = down.cross(Y)     # perpendicular to the funnel line, away from the funnel

        # from the tab's bottom corner on the funnel line, go up the line by s,
        # so that i out from the line we end up i above the bottom edge
        corner = tab_inner + down*P.funnelTabLength
        s = i*(1 - out.z)/(-down.z)
        c = corner - down*s + out*i
        return [Part.makeCylinder(r, 2*t, vec(sx*c.x, -t, c.z), Y) for sx in (-1, 1)]

    def _inner_tab_holes(self, main_from_top):
        """Hole cylinders centered in each inner tab, on both sides of the axis, their
        bottom edge level with the top disc's upper face, so a pin through them holds
        the disc down."""
        P = self.P
        t = P.thickness
        holes = {(sx*c, d/2) for c, _, d in self._inner_tabs(main_from_top) for sx in (-1, 1)}
        return [Part.makeCylinder(r, 2*t, vec(x, -t, self.height + t + r), Y) for x, r in holes]

    def _top_tab_cuts(self):
        """Horizontal cut boxes through both top tabs at their base, where the top disc
        sits, a sheet thickness high, running outwards from the tab's inner edge."""
        P = self.P
        w, t, cw = P.thickness + P.slotClearance, P.thickness, P.topTabCutWidth
        x0 = self.top_tab_x - P.topTabWidth/2
        return [Part.makeBox(cw, 2*t, w).translate(vec(x, -t, self.height))
                for x in (x0, -x0 - cw)]

    def _connector_holes(self):
        """Snapper hole cylinders through the connector and its vane, indented from the
        connector's side edges and centered vertically."""
        P = self.P
        r, t, i = P.snapperHoleDia/2, P.thickness, P.connectorSnapperIndent
        z = self.vane_bottom_z + P.topSlotHeight
        xs = (-P.connectorWidth/2 + i, P.connectorWidth/2 - i)
        return [Part.makeCylinder(r, 2*t, vec(x, -t, z), Y) for x in xs]

    def _connector(self):
        """Connector in the XZ plane at the bottom of a vane, slotted on its inner edge."""
        P = self.P
        th = P.topSlotHeight
        z0 = self.vane_bottom_z
        face = du.ortoRecFace(vec(-P.connectorWidth/2, 0, z0), vec(P.connectorWidth/2, 0, z0 + 2*th))
        return face.cut([self._slot(z0 + th, th)] + self._connector_holes())

    @cached_property
    def vaneXZ(self):
        return self._vane(main_from_top=True)

    @cached_property
    def vaneYZ(self):
        return self._vane(main_from_top=False).rotate(O, Z, 90)

    @cached_property
    def connectorYZ(self):
        # on the bottom edge, with vaneYZ's main slot
        return self._connector().rotate(O, Z, 90)

    @cached_property
    def funnelParts(self):
        # two funnel segments on opposite sides, slotted for the vane tabs;
        # each segment covers two vanes, the other two slots miss it
        slots = [self._funnel_slot().rotate(O, Z, ang) for ang in (0, 90, 180, 270)]
        return [self._funnel_segment().rotate(O, Z, ang).cut(slots) for ang in (45, 180 + 45)]

    @cached_property
    def funnelHalfPart(self):
        """One funnel segment cut in half by its vertical symmetry plane, with one vane
        slot; a template that fits A4 unwrapped, printed twice, once mirrored."""
        P = self.P
        # turned back so the segment's symmetry plane is the YZ plane, keep the +X half
        seg = self.funnelParts[0].copy().rotate(O, Z, -45)
        r = P.width
        box = Part.makeBox(r, 2*r, self.funnel_height + 2).translate(vec(0, -r, -1))
        return seg.common(box)

    def _funnel_slot(self):
        """Slab through the funnel where the vane tab crosses it, in the XZ plane at +X."""
        P = self.P
        _, a, down = self._funnel_tab()
        b = a + down*P.funnelTabLength
        n = down.cross(Y) * P.thickness     # reaches past the funnel surface on both sides
        face = Part.Face(Part.makePolygon([a - n, b - n, b + n, a + n, a - n]))
        return du.thicken(face, vec(y=P.thickness + P.slotClearance))

    def _funnel_segment(self):
        # cone segment
        P = self.P
        a1 = math.degrees(math.asin(2*P.funnelOverlap / P.width))
        p1, p2 = vec(P.innerWidth/2), vec(P.width/2, 0, self.funnel_height)
        line = Part.makeLine(p1, p2)
        face = line.rotate(O, Z, -a1/2).revolve(O, Z, 180 + a1)

        # snapper holes, indented from both ends of the generating line,
        # in the middle of each overlap
        d = (p2 - p1).normalize()
        n = d.cross(Y)
        r, h = P.snapperHoleDia/2, 2*P.thickness
        centers = [p1 + d*P.funnelBottomSnapperIndent, p2 - d*P.funnelSnapperIndent]
        holes = [
            Part.makeCylinder(r, h, c - n*h/2, n).rotate(O, Z, ang)
                for ang in (0, 180) for c in centers
        ]
        return face.cut(holes)

    @cached_property
    def topPart(self):
        # disc lying on top of the vanes, slotted for both top tabs of both vanes
        P = self.P
        circle = Part.makeCircle(P.width/2 + P.topOverlap, vec(z=self.height), Z)
        slots = [self._top_slot().rotate(O, Z, ang) for ang in (0, 90, 180, 270)]
        slots += self._inner_tab_slots(main_from_top=True)     # vaneXZ
        slots += [s.rotate(O, Z, 90) for s in self._inner_tab_slots(main_from_top=False)]
        return Part.Face(Part.Wire(circle)).cut(slots)

    def _inner_tab_slots(self, main_from_top):
        """Boxes through the top disc where a vane's inner tabs go through it, for the vane
        in the XZ plane, on both sides of the axis."""
        P = self.P
        w, t = P.thickness + P.slotClearance, P.thickness
        cs = {(sx*c, tw) for c, tw, _ in self._inner_tabs(main_from_top) for sx in (-1, 1)}
        return [Part.makeBox(tw, w, 2*t).translate(vec(c - tw/2, -w/2, self.height - t)) for c, tw in cs]

    def _top_slot(self):
        """Box through the top disc where the vane's top tab at +X goes through it,
        open to the disc's outer edge. It starts past the tab's base cut, so the
        disc between the tab's inner edge and the slot slides into that cut."""
        P = self.P
        w, t = P.thickness + P.slotClearance, P.thickness
        x0 = self.top_tab_x - P.topTabWidth/2 + P.topTabCutWidth
        l = P.width/2 + P.topOverlap - x0 + t     # past the disc's edge
        return Part.makeBox(l, w, 2*t).translate(vec(x0, -w/2, self.height - t))

