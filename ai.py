import FreeCAD
import Part
from FreeCAD import Base

doc = FreeCAD.ActiveDocument


# 1. Create the Target Object (Cylinder)
# This will be the curved surface we project onto.
target_face = Part.Face(Part.Wire(Part.makeCircle(20))).translate(Base.Vector(0,0,40))


# 2. Create the Source Object (Cube)
# This provides the face/profile we want to project.
source_body = Part.makeCylinder(60, 60).rotate(Base.Vector(0,0,0), Base.Vector(1,0,0),-90).translate(Base.Vector(0,-30,0))
Part.show(source_body, "SOURCE")

# Translate it slightly away so the projection is clear
#source_body.translate(Base.Vector(0, -15, 20))
source_face = source_body.Faces[0]  # Get one of the faces (e.g., the face pointing towards the cylinder)
print(source_face.ParameterRange)

# 3. Define the Projection Direction
# We want to project along the Y-axis (from the cube towards the cylinder).
projection_direction = Base.Vector(0, 1, 0)
Part.show(source_face, "SourceFace")
Part.show(target_face, "TargetFace")
projected_shapes = source_face.project([target_face]) #, projection_direction)
print(projected_shapes)
print(projected_shapes.ShapeType)
print(projected_shapes.Content)
print(projected_shapes.__class__)
print(type(projected_shapes))
print(projected_shapes.SubShapes)

res = projected_shapes.SubShapes[0]
print(res.ShapeType)
res = Part.Face(Part.Wire(res))
cut = source_face.cut(res)
Part.show(cut, "cut")



# 4. Execute the Projection
# The project method is called on the source shape (face)
# projected_shapes = source_face.project(target_face) #, projection_direction)
if True:
	
	
	# Iterate through the projected shapes and display them
	for i, shape in enumerate(projected_shapes.SubShapes):
		proj_obj = doc.addObject("Part::Feature", f"ProjectedShape_{i+1}")
		proj_obj.Shape = shape
		# Optionally, set the color to make the projection visible
		proj_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0) # Red color

doc.recompute()


cut = source_face.cut(res)
Part.show(cut, "cut")



# 4. Execute the Projection
# The project method is called on the source shape (face)
# projected_shapes = source_face.project(target_face) #, projection_direction)
if True:
	
	
	# Iterate through the projected shapes and display them
	for i, shape in enumerate(projected_shapes.SubShapes):
		proj_obj = doc.addObject("Part::Feature", f"ProjectedShape_{i+1}")
		proj_obj.Shape = shape
		# Optionally, set the color to make the projection visible
		proj_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0) # Red color

doc.recompute()

