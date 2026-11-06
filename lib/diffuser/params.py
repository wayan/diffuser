import typing
from dataclasses import dataclass, field


class BibData(typing.NamedTuple):
    face: typing.Any
    bib: typing.Any
    snap_holes: typing.Any

class BibCone(typing.NamedTuple):
    cone: typing.Any
    tip: typing.Any
    axis: typing.Any

class DiffuserCone(typing.NamedTuple):
    cone: typing.Any
    tip: typing.Any
    axis: typing.Any

@dataclass 
class Params:
    """Data-only class to hold diffuser parameters."""
    diffuserconeAngle: float = 32

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

    cone_tipShift: float = 290
    backPlateTabWidth: float = 25
    backPlateTabStart: float = 59
    tabCutWidth: float = 2.5
    coverSplitAt: float = 0.5415
    preventTearRadius: float = 0.3

    # tabs
    diffuser_front_tabDepth: float = 16
    diffuserback_plateTabDepth: float = 20
    diffuserInnerTabDepth: float = 15

    coverConnectedByTabs: bool = False

    # calculated fields
    topHeight: float = field(init=False)
    frontHeight: float = field(init=False)

    # cover stitch
    cover_stitchNumTabs: int = 3
    cover_stitchTabIndent: float = 20
    cover_stitchMargin: float = 10
    cover_stitchShift: float = 8
    cover_stitchTabHeight: float = 10

    # back plate stitch(es)
    back_plate_stitchNumTabs: int = 3
    back_plate_stitchTabIndent: float = 20
    back_plate_stitchMargin: float = 10
    back_plate_stitchShift: float = 8
    back_plate_stitchTabHeight: float = 10
    backPlateCutShallow: bool = False

    bibconeAngle: float = 25
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
