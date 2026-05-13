import FreeCAD, Part, Mesh, MeshPart, Draft, math
import ImportGui
from ..core.utils import vec, half_space

def import_step(path):
    """Imports a STEP file and returns the shape."""
    doc = FreeCAD.newDocument()
    ImportGui.insert(path, doc.Name)
    obj = doc.getObject("Part__Feature")
    shp = obj.Shape.copy()
    FreeCAD.closeDocument(doc.Name)
    return shp

def import_stl(path, height=None):
    """Imports an STL file and returns the shape."""
    doc = FreeCAD.newDocument()
    Mesh.insert(path, doc.Name)
    meshobj = doc.Objects[0]

    shpm = Part.Shape()
    shpm.makeShapeFromMesh(meshobj.Mesh.Topology, 0.1, False)
    shp = Part.Solid(Part.Shell(shpm.Faces))

    shp.rotate(vec(), vec(z=1), 30)
    shp.rotate(vec(), vec(y=-1), 90)
    bb = shp.BoundBox
    shp.translate(vec(-0.5 * (bb.XMax + bb.XMin), -0.5 * (bb.YMax + bb.YMin), -bb.ZMin))

    bb = shp.BoundBox

    if height is not None:
        if bb.ZMax > height:
            shp.translate(vec(z=height - bb.ZMax))
            shp = shp.cut(half_space(z=-1))
        else:
            profile = Part.Face(Part.makePolygon([vec(50 * x, 50 * y, 1) for x, y in
                                                  [[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]]))
            profile = profile.common(shp).extrude(vec(0, 0, -(height + 1 - bb.ZMax)))
            shp = shp.fuse(profile)
            shp.translate(vec(z=height - bb.ZMax))

    thickness = 16.5
    for x in [-1, 1]:
        shp = shp.cut(half_space(x=x).translate(vec(x=x * thickness / 2)))

    FreeCAD.closeDocument(doc.Name)
    return shp
