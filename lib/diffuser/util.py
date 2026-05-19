import FreeCAD, Part, Mesh, MeshPart, math, ImportGui, FreeCADGui

def vec(x=0,y=0,z=0):
    return FreeCAD.Vector(x,y,z)

X = vec(1)
Y = vec(0,1)
Z = vec(0,0,1)
O = vec()

Vector2d = FreeCAD.Base.Vector2d

# poly2d can accept list of tuples or 2d points
def poly2d(pts):
    return [ Part.Geom2d.Line2dSegment(pt2d(p), pt2d(q)) for p,q in zip(pts,pts[1:]) ]

# bez2d can accept list of tuples or 2d points
def bez2d(poles, periodic=False):
    b = Part.Geom2d.BSplineCurve2d()
    b.buildFromPoles([ pt2d(p) for p in poles], periodic)
    return b

def pt2d(p):
    return Vector2d(*p) if isinstance(p,tuple) else p

def circle2d(sfc, center, r, n=10): 
    uv = sfc.parameter(center)
    x, y = [ r * v for v in sfc.tangent(*uv) ]

    def pt2(angle):
        pt = center + angleVec(angle, x, y)
        return Vector2d(*sfc.parameter(pt)) 

    bez = bez2d([ pt2(a) for a in linspace(0,360,n) ], True)
    w = Part.Wire([ bez.toShape(sfc) ])
    return Part.Face(sfc, w)

def thicken(shp, direction):
    return shp.extrude(direction).translate(-direction/2)

# clone vector
def cvec(p,x=None,y=None,z=None):
    return FreeCAD.Vector( p.x if x is None else x, p.y if y is None else y, p.z if z is None else z )

def recXZ(w, h): 
    return Part.Face(  Part.makePolygon([vec(),vec(w),vec(w,z=h), vec(z=h), vec()]) )

def halfSpace(x=0,y=0,z=0,l=300):
    sx,sy,sz = [ (0 if d > 0 else (-l if d < 0 else -l/2)) for d in [x,y,z]]
    box = Part.makeBox(l,l,l).translate(vec(sx,sy,sz))
    return box

def nutPocket(dia, height):
    r = dia / 2
    poly = Part.makePolygon([
        FreeCAD.Rotation( vec(z=1), angle ).multVec(vec(r) )
          for angle in range(30, 400, 60)
    ])

    f = Part.Face( Part.Wire(poly) ).extrude( vec(0, 0, height) ).removeSplitter()
    f.tessellate(0.01)

    edges = [ e for e in f.Edges if e.BoundBox.ZLength >= height - 1 ]
    if len(edges) > 0:
        f = f.makeFillet(0.1, edges)
    return f

# "orthogonal" rectangle
def ortoRecPts(p1, p3):
    p2, p4 = [ vec(p.x, p.y, p.z) for p in [p1,p1]]
    if p1.x == p3.x:
        p2.y = p3.y
        p4.z = p3.z
    elif p1.y == p3.y:
        p2.x = p3.x
        p4.z = p3.z
    elif p1.z == p3.z:
        p2.x = p3.x
        p4.y = p3.y
    else:
        raise Exception("Sorry, the points does not lie in X or Y or Z planes")
    return [p1, p2, p3, p4, p1]

def ortoRecPoly(p1,p3):
    return Part.makePolygon(ortoRecPts(p1,p3))

def ortoRecFace(p1,p3):
    return Part.Face(ortoRecPoly(p1,p3))

def rads(deg):
    return deg*math.pi/180        

def angleVec(deg, xv=None, yv=None):
    r = math.radians(deg)
    return math.cos(r)*( vec(1,0,0) if xv is None else xv) + math.sin(r)*( vec(0,1,0) if yv is None else yv)

def recPoints(left=-1, top=-1, right=1, bottom=1):
    return [[left,top], [left,bottom], [right,bottom], [right,top], [left,top]]

def unwrapShape(doc, shp):
    mesh = MeshPart.meshFromShape(Shape = shp, LinearDeflection=0.03, AngularDeflection=0.174533, Relative=False)
    meshobj = doc.addObject("Mesh::Feature")
    meshobj.Mesh = mesh

    l = len(doc.Objects)
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Selection.addSelection(doc.Name, meshobj.Name)
    FreeCADGui.runCommand('MeshPart_CreateFlatMesh', 0)

    ret = Part.makeCompound([o.Shape for o in doc.Objects[l:]])
    for o in doc.Objects[l:]:
        doc.removeObject(o.Name)
    doc.removeObject(meshobj.Name)
    return ret

def symX(p):
    return vec(-p.x,p.y,p.z)

def symY(p):
    return vec(p.x,-p.y,p.z)

def symZ(p):
    return vec(p.x,p.y,-p.z)

def symBy(v):
    def sym(p):
        return p + 2*vec().projectToLine(p,v)
    return sym

def secant(curve, uMin, uMax):
     return (curve.valueAt(uMax) - curve.valueAt(uMin)).normalize()

def edgeSecant(e):
     return (e.valueAt(e.LastParameter) - e.valueAt(e.FirstParameter)).normalize()

# replace the corner in wire by BSplineCurve
def roundCorner(w, pt, r=2):
    tolerance = 1e-6
    for i, es in enumerate(zip(w.Edges, w.Edges[1:] + w.Edges[0:1])):
        e1,e2 = es
        if not(isinstance(e1.Curve, Part.Line) and isinstance(e2.Curve, Part.Line)):
            continue

        # first and last points on both lines
        p1 = e1.valueAt(e1.LastParameter)
        p2 = e2.valueAt(e2.FirstParameter)
        if not((p1-pt).Length < tolerance and (p2-pt).Length < tolerance and e1.Length > r and e2.Length > r):
            continue

        p0 = e1.valueAt(e1.FirstParameter) 
        p3 = e2.valueAt(e2.LastParameter)
        p1prev = p1 + r*((p0-p1).normalize())
        p2next = p2 + r*((p3-p2).normalize())

        repl = [  Part.makeLine(p0,p1prev), Part.BSplineCurve([p1prev,p2,p2next]).toShape(), Part.makeLine(p2next, p3) ]
        if i < len(w.Edges) - 1:
            return Part.Wire( w.Edges[:i] + repl + w.Edges[i+2:])
        return Part.Wire( w.Edges[1:i] + repl )

    # unchanged
    return w

def circumcenter(A, B, C):
    """Calculates the circumcenter of three points."""
    return Part.ArcOfCircle(A, B, C).Location

def roundCorners(w, pts, r=2):
    for pt in pts:
        w = roundCorner(w,pt,r)
    return w

def sub_edge(e, uns):
    return Part.Edge(e.Curve, *lerp_list(*e.ParameterRange, uns))

def edge_at_dist(e,l,from_end=False):
    if from_end:
        l = e.Length-l
    return e.Curve.parameterAtDistance(l, e.FirstParameter)

def lerp(p1, p2, k):
    """Linear interpolation lerp p1 and p2 by factor k (0 to 1)."""
    return p1 * (1 - k) + p2 * k

def lerp_tuple(t1, t2, k):
    return tuple(lerp(p1,p2,k) for p1,p2 in zip(t1,t2))

def lerp_list(p1, p2, ks):
    """Linear interpolation for a list of factors."""
    return [p1 * (1 - k) + p2 * k for k in ks]

def linspace(f, to, n):
    return [ lerp(f,to, i/n ) for i in range(n+1) ]

def linspace_minlen(f, to, minlen):
    n = math.ceil(abs(to-f) / minlen)
    return linspace(f,to,n)

def line_cut(wire, r=0.01):
    e = wire.Edges[0]
    circle = Part.makeCircle(r, e.valueAt(e.FirstParameter), e.tangentAt(e.FirstParameter))
    profile = Part.Wire([circle])

    # Sweep the circle along the wire to create a solid 'hair'
    return wire.makePipe(Part.Face(profile))

# Step 2 — find the edge that passes through pt1
def point_on_edge(pt, edge, tol=1e-4):
    """Check if a point lies on an edge within tolerance."""
    dist, _, _ = edge.distToShape(Part.Vertex(pt))
    print("DIST", dist)
    return dist < tol
