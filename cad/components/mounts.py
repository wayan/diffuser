import FreeCAD, Part, Mesh, MeshPart, math
from ..core.utils import vec, angle_vec
from ..core.geometry import create_ortho_rect_face
from ..core.transformations import Transformation, rotate, translate
from .fasteners import small_nut_pocket, bored_hole

class LoclineMount:
    """
    A class to create Loc-Line compatible mounts.
    """

    def __init__(self, hole_tolerance=1.007):
        self.hole_tolerance = hole_tolerance

        # Loc-Line dimensions
        self.locline_dia = 25
        self.locline_dia_in = 21.6 * (1 / self.hole_tolerance)
        self.locline_dia_in_in = 11.8 * self.hole_tolerance
        self.locline_spacer = 1.7 * self.hole_tolerance
        self.locline_height = 3
        self.locline_hole_height = 6.15

        # Hot shoe dimensions
        self.hot_shoe_width = 18.1
        self.hot_shoe_depth = 18.1
        self.hot_shoe_height = 1.7
        self.hot_shoe_inner_width = 12.5
        self.hot_shoe_inner_depth = 12.5
        self.hot_shoe_inner_height = 2

        # Thread dimensions
        self.thread_dia = 22
        self.thread_height = 8
        self.thread_pitch = 1.5

        # Nut and bolt dimensions
        self.big_nut_dia = self.thread_dia + 15
        self.big_nut_height = 7
        self.bolt_head_dia = 10.2
        self.bolt_head_height = 3.1
        self.nut_dia = 7.8 * self.hole_tolerance
        self.nut_height = 3.4 * self.hole_tolerance
        self.bolt_dia = 4.2

    def create_locline_protrusion(self):
        """Creates the protrusion for a Loc-Line connection."""
        cyl = Part.makeCylinder(self.locline_dia_in / 2, self.locline_height)
        cyl = cyl.cut(Part.makeCylinder(self.locline_dia_in_in / 2, self.locline_height))
        for angle in [0, 60, 120]:
            spacer = Part.makeBox(self.locline_dia, self.locline_spacer, self.locline_height)
            spacer.translate(vec(-self.locline_dia / 2, -self.locline_spacer / 2))
            cyl = cyl.cut(spacer.rotate(vec(), vec(z=1), angle))

        edges = [e for e in cyl.Edges if e.BoundBox.ZLength > 0.05 or e.BoundBox.ZMin > 0.05]

        if edges:
            cyl = cyl.makeFillet(0.33, edges)
        return cyl


class GoproMount:
    """
    A class to create a GoPro compatible mount.
    """

    def __init__(self, thickness=5, iwidth=15.1, iheight=7.9, idepth=12.2, bolt_dia=5.1, bottom_height=5):
        self.thickness = thickness
        self.iwidth = iwidth
        self.iheight = iheight
        self.idepth = idepth
        self.bolt_dia = bolt_dia
        self.bottom_height = bottom_height
        self.side_width = 1.5
        self.middle_width = 3.2
        self.gap_width = 3
        self.locline_mount = LoclineMount()

    def build(self):
        """Builds the GoPro mount."""
        m = self.locline_mount
        thickness = self.thickness
        iwidth = self.iwidth
        iheight = self.iheight
        idepth = self.idepth
        boltDia = self.bolt_dia
        bottomHeight = self.bottom_height
        sideWidth = self.side_width
        middleWidth = self.middle_width
        gapWidth = self.gap_width

        def circle(r):
            return Part.Face(Part.Wire(Part.makeCircle(r)))

        def inner_block():
            iw2 = iwidth / 2
            x = vec(x=iw2)
            z = vec(z=(bottomHeight + iheight))
            y = vec(y=(idepth + 2.5))

            front = create_ortho_rect_face(-x, x + z).fuse(circle(iw2).rotate(vec(), vec(x=1), 90).translate(z))
            top = create_ortho_rect_face(-x, x + y).fuse(circle(iw2).translate(y))
            block = front.extrude(vec(y=(idepth + 20))).common(top.extrude(vec(z=40)))

            for shft in [sideWidth, sideWidth + gapWidth + middleWidth]:
                block = block.cut(
                    create_ortho_rect_face(-x, x + vec(y=gapWidth))
                    .translate(vec(z=bottomHeight, y=shft))
                    .extrude(vec(z=40))
                )
            return block

        width = iwidth + 2 * thickness

        xw = vec(x=width / 2)
        yc = vec(y=(idepth + 3.5))
        r = m.locline_dia / 2
        zc = vec(z=r)

        height = max(m.locline_dia, iheight + bottomHeight + iwidth / 2 + thickness)
        depth = yc.y + m.locline_dia / 2

        front = create_ortho_rect_face(-xw, xw + zc).fuse(circle(r).rotate(vec(), vec(x=1), 90).translate(zc))
        top = create_ortho_rect_face(-xw, xw + yc).fuse(circle(r).translate(yc))
        side = create_ortho_rect_face(vec(), yc + 2 * zc).fuse(
            circle(r).rotate(vec(), vec(y=1), 90).translate(zc + yc)
        )

        block = create_ortho_rect_face(-xw, xw + yc + vec(y=r)).extrude(vec(z=height))
        block = (
            block.common(front.extrude(vec(y=50)))
            .fuse(block.common(top.extrude(vec(z=50))))
            .fuse(block.common(side.translate(-xw).extrude(2 * xw)))
        )

        def cyl(h):
            return Part.makeCylinder(m.locline_dia / 2, h)

        block = Part.makeBox(width, depth, m.locline_dia / 2).translate(-xw)
        block = block.fuse(cyl(height).translate(yc))
        block = block.fuse(cyl(width).rotate(vec(), vec(y=1), 90).translate(zc + yc - xw))
        block = block.fuse(cyl(depth).rotate(vec(), vec(x=1), -90).translate(zc))

        hole = Part.makeCylinder(boltDia / 2, idepth).rotate(vec(), vec(x=1), -90).translate(vec(z=(iheight + bottomHeight)))
        block = block.cut(hole)

        hn = width - 2 * 3
        nut = small_nut_pocket(m.nut_dia, hn).rotate(vec(), vec(z=1), 90).translate(vec(z=-hn / 2)).rotate(vec(), vec(y=1), 90).translate(yc + zc)
        block = block.cut(nut)

        ops = [
            rotate(vec(), vec(y=1), 90) + translate(vec(x=-50) + zc + yc),
            rotate(vec(), vec(x=1), -90) + translate(vec(y=idepth) + zc),
            translate(yc),
        ]
        for op in ops:
            block = block.cut(op(bored_hole(m.bolt_dia, 100)))

        ops = [rotate(vec(), vec(y=1), 90 * k) + translate(vec(x=k) * xw + yc + zc) for k in [-1, 1]]
        ops += [rotate(vec(), vec(x=1), -90) + translate(vec(y=depth) + zc)]
        ops += [translate(yc + vec(z=height))]
        for op in ops:
            block = block.fuse(op(m.create_locline_protrusion()))

        hn = depth - idepth - 3
        nut = small_nut_pocket(m.nut_dia, hn).rotate(vec(), vec(x=1), -90).translate(vec(y=idepth) + zc)
        block = block.cut(nut)

        nut = small_nut_pocket(m.nut_dia, height - 3)
        block = block.cut(nut.translate(yc))

        return block.cut(inner_block())
