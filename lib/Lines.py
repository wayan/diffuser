import Part

def newLines(lst):
    n = Lines()
    n.lst = lst
    return n

class Lines:

    # seznam navazujicich lomenych car
    def __init__(self, *pts):
        self.lst = []
        if len(pts) > 0:
            self.add(*pts)

    def __iter__(self):
        return iter(self.lst)

    def __add__(self, it):
        return newLines(  self.lst + [p for p in it ] )

    def __iadd__(self, other):
        self.lst += [ line for line in other ]
        return self

    # reverses each nested list
    def rev(self, fn=None):
        n = newLines([ list(reversed(l))  for l in reversed(self.lst) ])
        return n if fn is None else n.map(fn)

    # adds the new line starting from last point if any
    def add(self, *pts):
        line = ([ self.lst[-1][-1] ] if len(self.lst) > 0 else []) + list(pts)
        if len(line) < 2:
            raise Exception("Sorry, the line added does not contain two points")
        self.lst.append(line)
        return self

    def addBroken(self, *pts):
        l = list(pts)
        if len(self.lst) == 0:
            self.add(l[0], l[1])
            l = l[2:]

        for p in l:
            self.add(p)
        return self

    def map(self, fn):
        return newLines([ [fn(p) for p in line ]  for line in self ])

    def wire(self):
        return Part.Wire([ Part.makeLine(*l) if len(l) == 2 else Part.BSplineCurve(l).toShape() for l in self ])

