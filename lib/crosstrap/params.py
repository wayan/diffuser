from dataclasses import dataclass


@dataclass
class Params:
    """Data-only class to hold cross trap parameters."""
    width: float = 350
    height: float = 400
    innerWidth: float = 80
    thickness: float = 1          # vane sheet thickness
    slotClearance: float = 0.0    # extra slot width so the vanes slide together
    vaneCornerRadius: float = 3   # how far each edge is cut back at the vanes' rounded outer corners
    snapperHoleDia: float = 1
    funnelAngle: float = 45
    funnelOverlap: float = 30
    funnelSnapperIndent: float = 20 
    funnelTabWidth: float = 40
    funnelTabHeight: float = 20
    topOverlap: float = 10
    topSlotHeight: float = 20
    connectorWidth: float = 60
    connectorSnapperIndent: float = 10
    topTabHeight: float = 20
    topTabWidth: float = 30
    topTabHoleDia: float = 5
    topTabHoleIndent: float = 10  # hole center from the tab's inner edge
    topCenterTabWidth: float = 50  # tab centered on the top edge of vaneYZ
    topMidTabWidth: float = 25     # tabs on each half of vaneXZ's top edge
    topMidTabGap: float = 30       # gap between the Z axis and the mid tabs' inner edge
    topMidTabHoleDia: float = 3
    topTabCutWidth: float = 10  # horizontal cut at the tab's base, from its inner edge outwards
    bottomTabHoleDia: float = 4
    bottomTabHoleIndent: float = 10  # hole center from the funnel line and the funnel tab's bottom edge
