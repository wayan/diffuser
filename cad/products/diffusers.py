import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan
from collections import namedtuple
from dataclasses import dataclass, field
from functools import cached_property

from ..core.utils import vec, angle_vec, sym_x, lerp, linspace, lerp_list
from ..core.geometry import create_ortho_rect_face, Polyline
from ..core.transformations import Transformation, cut, common, translate, rotate
from ..components.mounts import LoclineMount
from ..io.importers import import_step

def extrude_front(shp):
    deep = 600
    return shp.extrude(vec(0, deep)).translate(vec(0, -deep / 2))

class ConeDiffuser:
    def __init__(self, type="regular"):
        self.smooth_cut = False
        self.reflection_desk_depth = 65
        self.flash_width, self.flash_depth = [12.5, 17 + 26]
        self.axis_angle = 0
        self.lens_outer = 13
        self.shift_up = 0
        self.cone_thickness = 6
        self.height_ratio = 0.85
        self.reflection_desk_thickness = 4
        self.reflection_desk_width = 150
        self.reflection_desk_depth = 70
        self.reflection_desk_cut_margin = 8
        self.dent_segments = [[0, 50], [100, 45], [-100, 45]]
        self.flap_depth = 5
        self.flap_width = 15
        self.flap_shift = 10
        self.flap_tolerance = 1.6
        self.flap_shift_vertical = 8
        self.flap_thickness = 1.3
        self.use_top_arch = False

        if type == "30":
            self.depth = 140
            self.lens_dia = 52
            self.angle = 75
        if type == "12":
            self.depth = 140
            self.lens_dia = 68
            self.angle = 95
        if type == "regular":
            self.depth = 140
            self.lens_dia = 50.8
            self.angle = 60
        if type == "30s":
            self.lens_dia = 61
            self.angle = 60
            self.depth = 155
            self.reflection_desk_depth = 55
            self.flash_depth = 17 + 15
            self.lens_outer = 5
            self.shift_up = 3
            self.reflection_desk_width = 132
            self.dent_segments = [[0, 50], [105, 55], [-105, 55]]
        if type == "9_17":
            self.depth = 135
            self.lens_dia = 72
            self.angle = 100
            self.dent_segments = [[0, 50], [115, 55], [-115, 55]]
        if type == "9_17e":
            self.lens_dia = 70
            self.angle = 110
            self.depth = 125
        if type == "9_17big" or type == "9_17small":
            self.lens_dia = 72 if type == "9_17small" else 80
            self.angle = 95
            self.depth = 125
            self.axis_angle = 10
            self.shift_up = 0
            self.height_ratio = 0.8
            self.lens_outer = 10
            self.dent_segments = [[0, 50], [115, 55], [-115, 55]]
            self.use_top_arch = True
            self.reflection_desk_width = 142 if type == "9_17small" else 152
        if type == "laowa":
            self.angle = 110
            self.lens_dia = 50.5
            self.depth = 120

        self.dent_depth = 12
        self.reflection_desk_fold_angle = 45
        self.reflection_desk_height = 56
        self.reflection_desk_down = self.lens_dia / 2 + 40
        self.reflection_desk_down_solid = self.lens_dia / 2 + 13
        self.reflection_desk_down_fold = self.lens_dia / 2 - 15

    def width(self):
        return self.lens_dia + 2 * tan(self.angle / 2 * pi / 180) * self.depth

    def height(self):
        return self.width() * self.height_ratio
    
    # ... (The rest of the methods from the Cone class would be here, refactored)
    # This is a placeholder for the full refactoring.
    def build(self):
        return Part.makeBox(10,10,10)


@dataclass
class BoxyDiffuserParams:
    """Data-only class to hold diffuser parameters."""
    diffuser_cone_angle: float = 30
    lens_depth: float = 37
    ellipse_ratio: float = 4 / 3
    lens_dia: float = 69
    flash_head_height: float = 33
    flash_head_width: float = 64
    flash_head_depth: float = 40
    flash_head_space_left: float = 0
    flash_head_space_up: float = 8
    focal_plane_shift: float = 10
    diff_thickness: float = 0.7
    cover_thickness: float = 1
    sensor_width: float = 17.3
    sensor_height: float = 13.0
    lens_focal: float = 14
    cover_front_margin: float = 8
    cover_fold_width: float = 14
    snap_thickness: float = 5
    cone_tip_shift: float = 290
    bottom_tab_width: float = 25
    bottom_tab_start: float = 59
    tab_cut_width: float = 2.5
    cover_split_at: float = 0.55
    prevent_tear_radius: float = 0.3
    diffuser_front_tab_depth: float = 16
    diffuser_bottom_tab_depth: float = 20
    diffuser_inner_tab_depth: float = 15
    cover_connected_by_tabs: bool = False
    cover_num_tabs: int = 3
    top_height: float = field(init=False)
    front_height: float = field(init=False)
    cover_stitch_num_tabs: int = 3
    cover_stitch_tab_indent: float = 20
    cover_stitch_margin: float = 10
    cover_stitch_shift: float = 8
    cover_stitch_tab_height: float = 10

    def __post_init__(self):
        lens_center_height = 46.5
        self.top_height = 195 - lens_center_height
        self.front_height = self.top_height + self.flash_head_space_up


class BoxyDiffuser:
    """
    Class to encapsulate the geometric model generation for a diffuser.
    """

    def __init__(self, doc, params: BoxyDiffuserParams):
        self.doc = doc
        self.P = params

    # ... (The rest of the methods from the Model class would be here, refactored)
    # This is a placeholder for the full refactoring.
    def build(self):
        return Part.makeBox(10,10,10)
