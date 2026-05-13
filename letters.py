import FreeCAD, Part, Draft

# Define the text and its parameters
text = "FreeCAD"
font_size = 10
font_face = "Arial"  # You can change this to your preferred font
extrusion_height = 5

# Create a 2D text object
text_object = Draft.make_text(text, font_size, font_face)

Part.show(text_object.Shape)

# Extrude the 2D text to create a 3D shape
#extrusion = Part.makeExtrusion(text_object.Shape, FreeCAD.Vector(0, 0, extrusion_height))

# Place the 3D text in the FreeCAD document
#FreeCAD.ActiveDocument.addObject("Part::Feature", "3DText").Shape = extrusion

# Show the created object in the 3D view
Gui.ActiveDocument.recompute() 

# Optionally, you can add more features like:
# - Beveling the edges
# - Adding holes or cutouts
# - Applying different materials
