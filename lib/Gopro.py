import FreeCAD, Part, Mesh, MeshPart, math
from math import pi, sin, cos, tan
from Diffutil import vec, angleVec, between, recPoints, ortoRecFace, X, Y, Z, O, symX, halfSpace
import Locline
import Trans

# holder for flash arms mounted on top of the gopro mount on cold shoe
def Holder():
    m = Locline.Mount()
    thickness = 5
    iwidth  = 15.1
    iheight = 15
    iheight = 7.9 
    idepth  = 12.2
    boltDia    = 5.1
    bottomHeight = 5

    sideWidth   = 1.5
    middleWidth =  3.2
    gapWidth    = 3

    def circle(r):
        return Part.Face(Part.Wire(Part.makeCircle(r)))

    def innerBlock():
        iw2 = iwidth/2
        x = X*iw2
        z = Z*(bottomHeight+iheight)
        y = Y*(idepth + 2.5)

        front = ortoRecFace(-x,x+z).fuse(circle(iw2).rotate(O,X,90).translate(z))
        top   = ortoRecFace(-x,x+y).fuse(circle(iw2).translate(y))
        block = front.extrude(Y*(idepth+20)).common(top.extrude(Z*40))

        for shft in [ sideWidth, sideWidth + gapWidth + middleWidth ]:
            block = block.cut( ortoRecFace(-x,x+Y*gapWidth).translate(Z*bottomHeight+Y*shft).extrude(40*Z) )
        return block

    width = iwidth + 2 *thickness

    # Y center
    xw = X*width/2
    yc = Y*(idepth+3.5)
    r = m.LocLineDia/2
    zc = Z*r

    height = max(m.LocLineDia, iheight+bottomHeight+iwidth/2 + thickness)
    depth  = yc.y + m.LocLineDia/2

    front = ortoRecFace(-xw,xw+zc).fuse(circle(r).rotate(O,X,90).translate(zc))
    top = ortoRecFace(-xw,xw+yc).fuse(circle(r).translate(yc))
    side = ortoRecFace(O, yc+2*zc).fuse(circle(r).rotate(O,Y,90).translate(zc+yc))

    block = ortoRecFace(-xw,xw+yc+r*Y).extrude(Z*height)
    block = block.common(front.extrude(50*Y)).fuse(block.common(top.extrude(50*Z))).fuse(block.common(side.translate(-xw).extrude(2*xw)))

    def cyl(h):
        return Part.makeCylinder(m.LocLineDia/2,h)

    block = Part.makeBox(width, depth, m.LocLineDia/2).translate(-xw)
    block = block.fuse(cyl(height).translate(yc))
    block = block.fuse(cyl(width).rotate(O,Y,90).translate(zc+yc-xw))
    block = block.fuse(cyl(depth).rotate(O,X,-90).translate(zc))

    # hole for the go pro bolt
    hole = Part.makeCylinder(boltDia/2, idepth).rotate(O,X,-90).translate(Z*(iheight+bottomHeight))
    block = block.cut(hole)

    hn = width - 2*3
    nut = m.smallNutPocket(hn).rotate(O,Z,90).translate(-Z*hn/2).rotate(O,Y,90).translate(yc+zc)
    block = block.cut(nut)

    # holes for bolts (side, front, top
    ops = [ Trans.rotate(O,Y,90)+Trans.translate(-50*X+zc+yc), Trans.rotate(O,X,-90)+Trans.translate(Y*idepth+zc),Trans.translate(yc) ]
    for op in ops:
        block = block.cut(op(m.boredHole(100)))


    # protrusion(s) - left, right, front, top 
    ops = [ Trans.rotate(O,Y,90*k) + Trans.translate(k*xw + yc + zc) for k in [-1,1] ]
    ops += [ Trans.rotate(O,X,-90) + Trans.translate(Y*depth + zc) ]
    ops += [ Trans.translate(yc + Z*height) ]
    for op in ops:
        block = block.fuse(op(m.locLineProtrusion()))

    hn = depth-idepth-3
    nut = m.smallNutPocket(hn).rotate(O,X,-90).translate(Y*idepth+zc)
    block = block.cut(nut)

    nut = m.smallNutPocket(height-3)
    block = block.cut(nut.translate(yc))

    # block = block.makeFillet(0.1, block.Edges)
    return block.cut(innerBlock())

