from dataclasses import dataclass


@dataclass
class Params:
    """Data-only class to hold three vane trap parameters."""
    width: float = 350            # diameter over the vanes' outer edges
    straightHeight: float = 280   # vane outer edge from the funnel rim up to the top edge
    innerWidth: float = 65        # funnel's lower opening
    thickness: float = 1          # sheet thickness
    slotClearance: float = 0.0    # extra slot width so the parts slide together
    triangleSide: float = 40      # side of the central triangle the vanes' planes enclose
    vaneInnerGap: float = 0       # extra gap between a vane's inner end and the face of the vane it meets
    vaneCornerRadius: float = 5   # how far each edge is cut back at the vanes' rounded corners
    joinTabCount: int = 2         # tabs on a vane's inner edge, through slits in the vane it butts against
    joinTabWidth: float = 60      # along the edge
    joinTabHeight: float = 15     # out from the vane's inner edge, through the vane it butts against
    joinTabCutLength: float = 8   # cuts along the vane's edge into both ends of each tab
    joinSlitCurveOffset: float = 3    # the slit's ends bend this far to the vane's outer side
    joinSlitEndClearance: float = 0.5 # and reach this far past the tab's ends
    joinTabCornerCutTip: float = 16  # tip corners: how far the rounding starts back along the tip; along the sides it takes all of joinTabHeight
    funnelAngle: float = 50       # from the vertical
    funnelOverlap: float = 20     # neighboring funnel segments overlap by a strip this wide along the seam
    funnelTongueRimDist: float = 28   # tongue joining the segments: its middle up the slope from the inner rim
    funnelTongueWidth: float = 18     # along the slope
    funnelTongueLength: float = 12    # out past the segment's edge
    funnelTongueCornerRadius: float = 3
    funnelSlitGap: float = 3          # the slit for it: past the edge of the segment lying on top
    funnelSlitWidth: float = 1.5      # room for the tongue bending through, about 1.5 sheet thicknesses
    funnelTabLength: float = 40   # along the funnel, also the funnel slot length
    funnelTabInset: float = 20    # along the vane in from its outer edge to where the tab starts
    topOverlap: float = 10        # top disc past the vanes' outer edges
    topCenterDia: float = 120    # central disc of the top, under the pie slices' inner ends
    topSliceReach: float = 15     # pie slices inward past the central tab's base cut, along the vane; slit as long
    topSideOverlap: float = 10    # pie slices over each other at their sides, a strip of this width
    topCenterTabRimGap: float = 12   # tab through the central disc: its outer end in from the disc's rim
    topCenterTabLength: float = 30   # along the vane, toward the center
    topCenterTabHeight: float = 20
    topCenterTabCutWidth: float = 10     # cut at its base, in from its outer edge, 2 sheets high
    hangHoleDia: float = 4        # hole in the middle of that tab, for the cord hanging the trap
    hangHoleGap: float = 1        # its bottom edge above the central disc and pie slice
    topTabWidth: float = 30
    topTabHeight: float = 15      # tabs flush with the vanes' outer edge, through the top disc
    topTabCornerRadius: float = 5   # top tabs' rounded corners, outer and central tab alike
    topTabCornerCutTop: float = 15  # the corners facing the other tab: cut back this far along the top
    topTabCornerCutSide: float = 10 # and this far down the side
    topTabCutWidth: float = 10    # cut at their base, from their inner edge outwards, 1 sheet high
