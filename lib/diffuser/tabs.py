import FreeCAD, Part, math
import diffuser.util as du

Vector2d = FreeCAD.Base.Vector2d

def buildTabFace(is_curved):
    def face(e, sfc, depths, minlen=5):
        sec = du.edgeSecant(e)
        cols = []
        num_steps = math.ceil(e.Length / minlen)

        for k in du.linspace(0, 1, num_steps):
            pt = e.valueAt(du.lerp(*e.ParameterRange, k))
            uv = sfc.parameter(pt)
            tan = sec.cross(sfc.normal(*uv))

            # Determine depth profile
            if is_curved:
                # Apply parabolic taper to the second depth value
                taper = du.lerp(0.4, 1, 1 - abs(2*k - 1)**2)
                curr_depths = [depths[0], depths[1] * taper]
            else:
                curr_depths = depths

            # Project 3D offsets into 2D UV points
            col = [ sfc.parameter(pt + d * tan) for d in curr_depths]
            cols.append(col)

        # Construct geometry
        wire = Part.Wire([seg.toShape(sfc) for seg in tab_segments(cols)])
        return Part.Face(sfc, wire)

    return face

# Create the specific function instances
tabFaceCurved = buildTabFace(True)
tabFaceRec    = buildTabFace(False)

# simple - rectangular symmetrical face on a surface
def slotFace(e, sfc, depth):
    return tabFaceRec(e, sfc, [-depth/2, depth/2])

def tabInterFace(curve, sfc, before, after, depths):
    uss = [ du.lerp_list(*curve.ParameterRange, p) for p in [before,after] ]

    # we start with slightly slated secants
    secs = [ du.secant(curve, *us) for us in uss ] 

    (_, u_min), (u_max, _) = uss
    us = [u_min, u_max]

    minlen = 3
    cols = []
    allDepths = list(du.linspace(*depths, math.ceil( (depths[1] - depths[0])/minlen )))
    ks = list(du.linspace(0, 1, math.ceil(curve.Curve.length(*us)/minlen)))
    for i, k in enumerate(ks):
        sec = du.lerp(*secs, du.lerp(0.2,0.8,k)).normalize()
        pt = curve.valueAt( du.lerp(*us, k))
        uv = sfc.parameter(pt) 
        tan = sec.cross(sfc.normal(*uv))

        cols.append([ sfc.parameter(pt + depth*tan) for depth in (allDepths if i==0 or i==len(ks)-1 else depths)])

    w = Part.Wire([ seg.toShape(sfc) for seg in tab_segments(cols) ])
    return Part.Face(sfc, w)

def tab_segments(cols):
    # Unpack the boundary rows
    bottom_row, *_, top_row = cols

    # Extract boundary columns (safe for jagged rows)
    left_edge  = [row[0] for row in cols]
    right_edge = [row[-1] for row in cols]

    return [
        du.bez2d(left_edge),
        *du.poly2d(top_row),
        du.bez2d(right_edge[::-1]),
        *du.poly2d(bottom_row[::-1])
    ]


