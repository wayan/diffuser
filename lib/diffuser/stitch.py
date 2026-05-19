import FreeCAD, Part, math
import diffuser.util as du
import diffuser.tabs as dt

from dataclasses import dataclass
from collections import namedtuple

@dataclass
class Params:
    numTabs: int = 3
    tabIndent: float = 20
    shift: float = 8
    tabHeight: float = 10
    thickness: float = 0.8
    stopperHeight: float = 2
    tabOverlay: float = 0.8
    dir: int = 1

def Stitch(e, sfc, P): 
    def at_dist(l):
        return e.Curve.parameterAtDistance(l, e.FirstParameter) 

    tab_width = (e.Length-2*P.tabIndent)/(2*P.numTabs-1)
    # tabs and spaces are equal width
    minlen = 3

    def tab_start(t):
        return P.tabIndent + t * 2 * tab_width

    def pt2d(l, depth):
        u = at_dist(l)
        uv = sfc.parameter(e.valueAt(u))
        if depth == 0:
            return uv
        vec_n = e.tangentAt(u).cross(sfc.normal(*uv)).normalize()
        k = -1 if P.dir < 0 else 1
        return sfc.parameter(sfc.value(*uv)+k*depth*vec_n)

    def slot(t):
        # first and last pt of the slot 
        l_from  = tab_start(t) - P.shift
        l_to    = tab_start(t) + tab_width
        ee = Part.Edge(e.Curve, at_dist(l_from), at_dist(l_to))
        return dt.slotFace(ee, sfc, P.thickness)

    def tab(t):
        l_from = tab_start(t)
        l_m    = l_from + tab_width
        l_to   = l_m + P.shift

        # straight edge - along the stitch
        segs = [
            du.bez2d([ pt2d(l,-P.tabOverlay) for l in du.linspace_minlen(l_from,l_m,minlen) ]),
            # dent
            *du.poly2d([ pt2d(*p) for p in [(l_m, -P.tabOverlay), (l_m,P.thickness), (l_m+0.7*P.shift,P.thickness) ]]),
            # top curve
            du.bez2d([pt2d(*p) for p in [
                (l_m+0.7*P.shift, P.thickness),
                (l_to, P.thickness),
                (l_to, P.thickness + 0.3*P.tabHeight),
                (l_to, P.tabHeight),
                *[ (l, P.tabHeight) for l in du.linspace_minlen(l_to - 1.5*P.shift,l_from + 1.5 *P.shift,minlen)  ],
                (l_from, P.tabHeight), (l_from, 0.3*P.tabHeight), (l_from, -P.tabOverlay),
            ]])
        ]
        wire = Part.Wire([ seg.toShape(sfc) for seg in segs ])
        return Part.Face(sfc, wire)

    def stopper_tab(t):
        l_from  = tab_start(t) - P.shift
        l_to    = tab_start(t) - 0.1 

        # stopper is plain rectangle 
        h = P.stopperHeight
        pts = [ pt2d(*p) for p in [(l_from, -P.tabOverlay), (l_from,h), (l_to,h), (l_to,-P.tabOverlay), (l_from,-P.tabOverlay) ]]
        segs = du.poly2d(pts)
        wire = Part.Wire([ seg.toShape(sfc) for seg in segs ])
        return Part.Face(sfc, wire)

    def slots():
        return [ slot(t) for t in range(P.numTabs) ]

    def tabs():
        return [ tab(t) for t in range(P.numTabs) ]

    def stopper_tabs():
        return [ stopper_tab(t) for t in range(P.numTabs) ]

    Stitch = namedtuple('Stitch', ['slots', 'tabs', 'stopper_tabs'])

    return Stitch(slots, tabs, stopper_tabs)

