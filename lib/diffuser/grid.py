# compose shapes
import math
from diffuser.util import vec, X, Y, Z, O

class Grid:
    def __init__(self, width=800, space=100):
        self.width = width 
        self.space = space
        self.x = 0
        self.y = 0
        self.rowHeight = 0

    def add(self, shp):
        xNew = self.x + shp.BoundBox.XLength + self.space
        if self.x > 0:
            if xNew > self.width:
                self.x = 0
                self.y += self.space + self.rowHeight
                self.rowHeight = 0
                return self.add(shp)

        shp.translate(X*(self.x - shp.BoundBox.XMin) + Y*(self.y-shp.BoundBox.YMin))

        if self.rowHeight < shp.BoundBox.YLength:
            self.rowHeight = shp.BoundBox.YLength

        self.x = xNew

        return shp
