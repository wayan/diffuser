from dataclasses import dataclass


@dataclass
class Params:
    """Data-only class to hold cross trap parameters."""
    width: float = 350
    straightHeight: float = 350   # vane outer edge from the funnel rim up to the top edge
    innerWidth: float = 65
    thickness: float = 1          # vane sheet thickness
    slotClearance: float = 0.0    # extra slot width so the vanes slide together
    vaneCornerRadius: float = 5  # how far each edge is cut back at the vanes' rounded outer corners
    snapperHoleDia: float = 1
    funnelAngle: float = 50       # from the vertical
    funnelOverlap: float = 30
    funnelSnapperIndent: float = 20       # top snapper holes, from the funnel's outer rim along the slope
    funnelBottomSnapperIndent: float = 30 # bottom snapper holes, from the funnel's inner rim along the slope
    funnelTabLength: float = 40   # along the funnel line, also the funnel slot length
    funnelTabInset: float = 20    # horizontally in from the vane's outer edge to where the tab starts
    funnelTabCutLength: float = 6   # rope/rubber notch in the funnel tab, down along the funnel line
    funnelTabCutWidth: float = 2    # clear width for the rope, the cut is wider by the funnel's thickness
    funnelTabCutGap: float = 0      # between the funnel line and the cut
    topOverlap: float = 10
    topSlotHeight: float = 20
    connectorWidth: float = 60
    connectorSnapperIndent: float = 10
    topTabHeight: float = 20      # center and mid tabs
    topOuterTabHeight: float = 15 # tabs flush with the vanes' outer edge
    topOuterTabInnerRadius: float = 10  # rounding of the outer tabs' inner top corner
    topTabWidth: float = 30
    topTabHoleDia: float = 5      # pin hole in vaneYZ's center tab
    topCenterTabWidth: float = 50  # tab centered on the top edge of vaneYZ
    topMidTabWidth: float = 25     # tabs on each half of vaneXZ's top edge
    topMidTabGap: float = 30       # gap between the Z axis and the mid tabs' inner edge
    topMidTabHoleDia: float = 3
    topTabCutWidth: float = 10  # horizontal cut at the tab's base, from its inner edge outwards
    bottomTabHoleDia: float = 4
    bottomTabHoleIndent: float = 10  # hole center from the funnel line and the funnel tab's bottom edge
