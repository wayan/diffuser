import FreeCAD, Part, Mesh, MeshPart, Draft, math
from ..core.utils import vec, sym_x, sym_y
from ..core.geometry import create_ortho_rect_face, Polyline, get_ortho_rect_pts
from ..components.mounts import LoclineMount
from ..io.importers import import_stl, import_step

class MF12Holder:
    def __init__(self, bigger=0):
        self.bigger = bigger

    def build(self):
        el = import_step("./51801, 59859, 59860, 59861, 56801, 57860, 57859, 57861 1-2 Element.STEP")
        outer = self._locline_part(el, True, self.bigger)

        mf12 = import_stl("./MF12-BabyMount.stl", 26)
        mf12 = mf12.fuse(Part.makeCylinder(8, 8.2))
        mf12 = mf12.fuse(outer)

        return mf12

    def _locline_part(self, elem, outer, shift=0, cuts=0):
        shp = elem.copy()
        if outer:
            h_out = 16.30
            shp = shp.rotate(vec(), vec(0, 1, 0), 90).translate(vec(0, 0, -h_out))
            shp = shp.cut(half_space(z=1))
        else:
            total = 29.90
            part = 11.581 + 2
            shp = shp.rotate(vec(), vec(0, 1, 0), -90).translate(vec(0, 0, total - part))
            shp = shp.cut(half_space(z=1))

        if shift != 0:
            pts = [vec(x * 100, 0, z * 100 - 50) for x, z in [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            face = Part.Face(Part.makePolygon(pts))
            shp = shp.common(face).translate(vec(x=shift)).revolve(vec(), vec(0, 0, 1), 360)

        if cuts > 0:
            cw = 2
            ch = 30
            hs = 5
            pts = [vec(x - cw / 2, 0, z - hs - ch) for x, z in
                   [[0, 0], [cw, 0], [cw, ch / 5], [cw, ch * 4 / 5], [cw, ch], [0, ch], [0, ch * 4 / 5], [0, ch * 1 / 5], [0, 0]]]
            dent = Part.Face(Part.Wire(Part.Shape([Part.BSplineCurve(pts, periodic=True)]))).extrude(vec(0, 30, 0))
            for a in [i * 360 / cuts for i in range(0, cuts)]:
                shp = shp.cut(dent.copy().rotate(vec(), vec(0, 0, 1), a))

        return shp


class TriggerHolder:
    def __init__(self):
        self.width = 50
        self.thickness = 8
        self.side_thickness = 8
        self.hole_dia = 9.3
        self.center_height = 15
        self.column_dia = self.hole_dia + 6

    def build(self):
        m = LoclineMount()

        p0, p1, p2, p3, p4 = get_ortho_rect_pts(*[k * vec(self.width, m.locline_dia) for k in [-0.5, 0.5]])
        ps = self.side_thickness * vec(x=1)

        arcs = Polyline()
        arcs.add(0.5 * (p3 + p0), p0)
        arcs.add(p0 + ps)
        arcs.add(p0 + ps + vec(3), vec(-8, -self.column_dia / 2), vec(0, -self.column_dia / 2))
        arcs += arcs.rev(sym_x)
        arcs += arcs.rev(sym_y)

        base = Part.Face(Part.Wire([Part.BSplineCurve(arc).toShape() for arc in arcs]))
        base = base.extrude(vec(z=self.thickness))

        base = base.fuse(Part.makeCylinder(self.column_dia / 2, 16))
        cut = create_ortho_rect_face(*[k * vec(21.5, m.locline_dia) for k in [-0.5, 0.5]])
        cut = cut.extrude(vec(z=2))
        base = base.cut(cut)
        hole = Part.makeCylinder(self.hole_dia / 2, 30)
        base = base.cut(hole)

        for side in [-1, 1]:
            pz = self.center_height * vec(z=1)
            py = vec(y=m.locline_dia / 2)

            box = create_ortho_rect_face(-py + vec(y=-self.center_height), py)
            box = box.fuse(Part.Face(Part.Wire(Part.makeCircle(m.locline_dia / 2))))
            box = box.extrude(vec(z=-self.side_thickness))
            box = box.fuse(m.create_locline_protrusion())
            box = box.cut(m.boredHole(40).translate(vec(z=-20)))
            box = box.cut(m.smallNutPocket().translate(vec(z=-self.side_thickness)))
            box = box.rotate(vec(), vec(z=1), side * 90).rotate(vec(), vec(y=1), side * 90).translate(
                vec(side * self.width / 2, 0, self.center_height))
            base = base.fuse(box)

        return base
