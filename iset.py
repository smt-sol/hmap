import numpy as np
from collections import defaultdict

import pytest


class Box:
    """[x0,x1] x [y0,y1] or [x0,x0+dx] x [y0,y0+dy] nonempty region"""
    def __init__(self, x0, y0, x1=None, y1=None, dx=None, dy=None):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1 if x1 is not None else x0 + dx
        self.y1 = y1 if y1 is not None else y0 + dy
        assert self.dx > 0 and self.dy > 0

    def __str__(self):
        return "(" + str(self.x0) + " - " + str(self.x1) + ") x (" + str(self.y0) + " - " + str(self.y1) + ")"

    def __repr__(self):
        return "Box" + str(self.xyxy())

    def __hash__(self):
        return hash(self.xy())

    def __eq__(self, other):
        return self.xy() == other.xy()

    def __len__(self):
        return self.dx * self.dy

    @property
    def dx(self):
        return self.x1 - self.x0

    @property
    def dy(self):
        return self.y1 - self.y0

    @property
    def shape(self):
        return self.dx, self.dy

    def copy(self):
        return Box(*self.xyxy())

    def grow(self, n):
        self.x0 -= n
        self.y0 -= n
        self.x1 += n
        self.y1 += n

    def contains(self, x, y):
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1

    def xy(self):
        return (self.x0, self.x1, self.y0, self.y1)

    def xyxy(self):
        return (self.x0, self.y0, self.x1, self.y1)

    def overlap(self, other):
        """compute intersection"""
        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)
        try:
            return Box(x0, y0, x1, y1)
        except AssertionError:
            return None

    def shrink(self, other, dir="auto"):
        """shrink self until it does not overlap with other"""
        o = self.overlap(other)
        x0, x1, y0, y1 = self.xy()
        if o is None:
            return
        if dir == "dx" or dir == "auto":
            d1 = self.x1 - o.x0
            d2 = o.x1 - self.x0
            if d1 < d2:
                x1 = o.x0
            else:
                x0 = o.x1
        if dir == "dy" or dir == "auto":
            d1 = self.y1 - o.y0
            d2 = o.y1 - self.y0
            if d1 < d2:
                y1 = o.y0
            else:
                y0 = o.y1
        if dir == "dx":
            self.x0, self.x1 = x0, x1
        elif dir == "dy":
            self.y0, self.y1 = y0, y1
        elif (x1-x0)*(self.y1-self.y0) > (y1-y0)*(self.x1-self.x0):
            self.x0, self.x1 = x0, x1
        else:
            self.y0, self.y1 = y0, y1

    @staticmethod
    def from_set(s):
        assert s
        xs = [x[0] for x in s]
        ys = [x[1] for x in s]
        x0 = min(xs)
        x1 = max(xs)+1
        y0 = min(ys)
        y1 = max(ys)+1
        return Box(x0, y0, x1, y1)

class Boxes(list):
    def __init__(self, boxes=None):
        if boxes is None:
            boxes = []
        super().__init__(boxes)

    def bbox(self):
        x0 = min([b.x0 for b in self])
        x1 = max([b.x1 for b in self])+1
        y0 = min([b.y0 for b in self])
        y1 = max([b.y1 for b in self])+1
        return Box(x0, y0, x1, y1)

    def size(self):
        return sum([len(x) for x in self])

    def simplify(self, mode="auto"):
        """generate pairwise disjoint representation (can be improved)"""
        def merge(s):
            out = []
            for a, b in sorted(s):
                if not out or a > out[-1][1]:
                    out.append([a, b])
                else:
                    out[-1][1] = max(b, out[-1][1])
            return out

        d = defaultdict(list)
        while self:
            b = self.pop()
            d[b.x0].append((True, b.y0, b.y1))
            d[b.x1].append((False, b.y0, b.y1))

        curr = set()
        xold = None
        bxs = {}
        for xnew in sorted(d.keys()):
            if xold is not None:
                for y0, y1 in merge(curr):
                    if (xold, y0, y1) in bxs:
                        B = bxs[(xold, y0, y1)]
                        B.x1 = xnew
                    else:
                        B = Box(xold, y0, xnew, y1)
                        self.append(B)
                    bxs[(xnew, y0, y1)] = B
            for a, y0, y1 in d[xnew]:
                if a:
                    curr.add((y0, y1))
                else:
                    curr.remove((y0, y1))
            xold = xnew
        assert not curr


class IBox(Box):
    def __init__(self, box, iset=None, ones=False):
        super().__init__(*box.xyxy())
        if iset is None:
            z = np.zeros(self.shape, dtype=np.bool)
            self.iset = ~z if ones else z
        else:
            self.iset = (iset if isinstance(iset, np.ndarray) else np.array(iset)).astype(np.bool)
        assert self.shape == self.iset.shape

    def __str__(self):
        return "BOX:"+Box.__str__(self) + " LEN:" + str(len(self))

    def __len__(self):
        return sum(sum(self.iset))

    def __iand__(self, other):
        """operate on overlap"""
        o = self.overlap(other)
        if o is not None:
            m = np.array(other.extract_array(o), dtype=np.bool)
            x0, x1, y0, y1 = self._local_coord(o)
            self.iset[x0:x1, y0:y1] &= m
        return self

    def __ior__(self, other):
        """operate on overlap"""
        o = self.overlap(other)
        if o is not None:
            m = np.array(other.extract_array(o), dtype=np.bool)
            x0, x1, y0, y1 = self._local_coord(o)
            self.iset[x0:x1, y0:y1] |= m
        return self

    def __isub__(self, other):
        """operate on overlap"""
        o = self.overlap(other)
        if o is not None:
            m = ~np.array(other.extract_array(o), dtype=np.bool)
            x0, x1, y0, y1 = self._local_coord(o)
            self.iset[x0:x1, y0:y1] &= m
        return self

    def restrict(self, box):
        o = self.overlap(box)
        if o is None:
            self.clear()
        else:
            x0, x1, y0, y1 = self._local_coord(o)
            self.iset[:x0, :] = 0
            self.iset[x1:, :] = 0
            self.iset[:, :y0] = 0
            self.iset[:, y1:] = 0
            
    def copy(self):
        return IBox(Box(*self.xyxy()), np.array(self.iset))

    @staticmethod
    def from_set(s):
        return IBox(Box.from_set(s))

    def clear(self):
        self.iset &= False

    def add_point(self, p):
        self._set(p, 1)

    def sub_point(self, p):
        self._set(p, 0)

    def flip_point(self, p):
        i, j = p[0] - self.x0, p[1] - self.y0
        if 0 <= i < self.dx and 0 <= j < self.dy:
            self.iset[i, j] = not self.iset[i, j]

    def _set(self, p, val):
        i, j = p[0] - self.x0, p[1] - self.y0
        if 0 <= i < self.dx and 0 <= j < self.dy:
            self.iset[i, j] = val

    def _local_coord(self, box):
        """self-coords of other (smaller) box"""
        bx0, bx1, by0, by1 = box.xy()
        sx0, sx1, sy0, sy1 = self.xy()

        assert sx0 <= bx0 < bx1 <= sx1
        assert sy0 <= by0 < by1 <= sy1

        x0, x1 = bx0 - sx0, bx1 - sx0
        y0, y1 = by0 - sy0, by1 - sy0
        return x0, x1, y0, y1

    def extract_array(self, box):
        x0, x1, y0, y1 = self._local_coord(box)
        return self.iset[x0:x1, y0:y1]

    def extract_ibox(self, box):
        x0, x1, y0, y1 = self._local_coord(box)
        return IBox(box, iset=self.iset[x0:x1, y0:y1])

    def meets(self, other):
        o = self.overlap(other)
        if o is not None:
            m = np.array(other.extract_array(o), dtype=np.bool)
            x0, x1, y0, y1 = self._local_coord(o)
            x = self.iset[x0:x1, y0:y1]
            if sum(sum(x & m)):
                return True
        return False

    # NO TESTS
    def bitmap(self, col):
        from PyQt5.QtGui import QImage, QPixmap

        vs = self.iset.transpose()
        bits = np.packbits(vs.view(np.uint8))
        img = QImage(bits, self.dx, self.dy, QImage.Format_Mono)
        img.setColorTable([0, col.rgba()])
        bmap = QPixmap.fromImage(img)
        return bmap


class ISet:
    "list of pairwise disjoint IBoxes"
    def __init__(self, boxes=None):
        self.boxes = []
        if boxes is None:
            return
        for b in boxes:
            if isinstance(b, Box) and not isinstance(b, IBox):
                b = IBox(b)
            assert isinstance(b, IBox)
            for c in self.boxes:
                assert b.overlap(c) is None
            self.boxes.append(b)
        self.sig = {b.xy(): b for b in self.boxes}
        self.keys = set(self.sig.keys())

    def copy(self):
        return ISet([x.copy() for x in self.boxes])

    def __len__(self):
        return sum(len(x) for x in self.boxes)

    def __str__(self):
        ret = []
        for b in self.boxes:
            ret.append(str(b))
        return "\n\n".join(ret)

    def pair(self, other):
        jkey = self.keys & other.keys
        skey = self.keys - other.keys
        okey = other.keys - self.keys
        pairs = [(self.sig[xy], other.sig[xy]) for xy in jkey]
        sonly = [self.sig[xy] for xy in skey]
        oonly = [other.sig[xy] for xy in okey]
        return (pairs, sonly, oonly)

    def __ior__(self, other):
        p, s, o = self.pair(other)
        for a, b in p:
            a |= b
        if s and o:
            for a in s:
                for b in o:
                    a |= b
        return self

    def __iand__(self, other):
        p, s, o = self.pair(other)
        for a, b in p:
            a &= b
        if s and o:
            for a in s:
                for b in o:
                    a &= b
        return self

    def __isub__(self, other):
        p, s, o = self.pair(other)
        for a, b in p:
            a -= b
        if s and o:
            for a in s:
                for b in o:
                    a -= b
        return self

    def __and__(self, other):
        assert self.keys == other.keys
        iboxes = []
        for xy in self.keys:
            a, b = self.sig[xy], other.sig[xy]
            iboxes.append(IBox(a, iset=(a.iset & b.iset)))
        return ISet(iboxes)

    def __or__(self, other):
        assert self.keys == other.keys
        iboxes = []
        for xy in self.keys:
            a, b = self.sig[xy], other.sig[xy]
            iboxes.append(IBox(a, iset=a.iset | b.iset))
        return ISet(iboxes)

    def __sub__(self, other):
        assert self.keys == other.keys
        iboxes = []
        for xy in self.keys:
            a, b = self.sig[xy], other.sig[xy]
            iboxes.append(IBox(a, iset=a.iset & ~b.iset))
        return ISet(iboxes)

    def add_box(self, box):
        for b in self.boxes:
            if b.overlap(box) is not None:
                print("OV", b, box)
                return False
        self.boxes.append(IBox(box))
        self.sig = {b.xy(): b for b in self.boxes}
        self.keys = set(self.sig.keys())
        return True

    def extract_ibox(self, box):
        if not self.boxes:
            return IBox(box, np.zeros(box.shape))
        dtype = self.boxes[0].iset.dtype
        assert dtype == np.bool
        a = IBox(box, np.zeros(box.shape, dtype=dtype))
        for b in self.boxes:
            a |= b
        return a

    def bibox(self):
        B = Boxes(self.boxes).bbox()
        IB = IBox(B)
        for ib in self.boxes:
            IB |= ib
        return IB

    def clear(self):
        for b in self.boxes:
            b.clear()

    def copy(self):
        return ISet([x.copy() for x in self.boxes])

    def add_point(self, p):
        for i in self.boxes:
            i.add_point(p)

    def sub_point(self, p):
        for i in self.boxes:
            i.sub_point(p)


class PSet:
    """ISet with history"""
    def __init__(self, iset=None):
        self.curr = ISet() if iset is None else iset
        self.simplify()

    def __len__(self):
        return len(self.curr)

    # BOXES
    def currbox(self, box):
        return self.curr.extract_ibox(box)

    def add_box(self, box):
        return self.curr.add_box(box)

    def restrict(self, box):
        for x in self.curr.boxes:
            x.restrict(box)

    # HISTORY
    def simplify(self):
        self.hist = []
        self.idx = 0

    def recalc(self, idx=None):
        if idx is None:
            idx = self.idx
        self.idx = 0
        self.curr.clear()
        for h in self.hist[:idx]:
            if h[0] == "+":
                self.add(h[1], nohist=True)
            else:
                self.sub(h[1], nohist=True)

    def add(self, pixs, nohist=False):
        pixs -= self.curr
        if len(pixs):
            if not nohist:
                self.hist = self.hist[:self.idx]
            self.idx += 1
            self.curr |= pixs
            if not nohist:
                self.hist.append(("+", pixs))

    def sub(self, pixs, nohist=False):
        pixs &= self.curr
        if len(pixs):
            if not nohist:
                self.hist = self.hist[:self.idx]
            self.idx += 1
            self.curr -= pixs
            if not nohist:
                self.hist.append(("-", pixs))

    def intersect(self, pixs):
        curr = self.curr.copy()
        curr -= pixs
        self.sub(curr)

    def redo(self):
        if self.idx < len(self.hist):
            h = self.hist[self.idx]
            if h[0] == "+":
                self.curr |= h[1]
            else:
                self.curr -= h[1]
            self.idx += 1

    def undo(self):
        if self.idx:
            self.idx -= 1
            if False:
                self.recalc()
                return
            h = self.hist[self.idx]
            if h[0] == "-":
                self.curr |= h[1]
            else:
                self.curr -= h[1]

    def bitmap(self, w, h, c):
        B = Box(0, 0, dx=w, dy=h)
        IB = self.currbox(B)
        return IB.bitmap(c)

########################
#
# TESTS
#
########################

# Box
def test_box_initcheck():
    with pytest.raises(AssertionError):
        Box(1, 2, 3, 2)


def test_box_init():
    assert repr(Box(1, 2, 3, 5)) == "Box(1, 2, 3, 5)"


def test_box_len():
    B = Box(1, 2, 3, 3)
    assert len(B) == 2


def test_box_copy():
    B = Box(1, 2, 3, 3)
    C = B.copy()
    assert B is not C
    assert B == C
    assert repr(B) == repr(C)

def test_box_grow():
    B = Box(1, 2, 3, 3)
    B.grow(3)
    assert B.xyxy() == (-2, -1, 6, 6)


def test_box_shrink():
    B1 = Box(0, 0, 5, 6)
    B2 = Box(0, 0, 5, 6)
    B3 = Box(0, 0, 5, 6)
    C = Box(3, 3, 5, 5)
    B1.shrink(C, dir="dx")
    B2.shrink(C, dir="dy")
    B3.shrink(C)
    assert B1.xyxy() == (0, 0, 3, 6)
    assert B2.xyxy() == (0, 0, 5, 3)
    assert B3.xyxy() == (0, 0, 3, 6)

def test_box_contains():
    B = Box(0, 0, 5, 6)
    assert B.contains(0, 0)
    assert B.contains(1, 2)
    assert not B.contains(5, 5)
    assert not B.contains(4, 6)
    assert B.contains(4.999, 5.999)


def test_box_overlap():
    B = Box(0, 0, 5, 6)
    C = Box(3, 3, 5, 5)
    assert B.overlap(C) == Box(3, 3, 5, 5)


def test_box_from_set():
    B = Box.from_set({(1, 2), (10, 10), (0, 1), (3, 0)})
    assert len(B) == 121

# Boxes
def test_boxes_simplify():
    B = Boxes()
    B.append(Box(x0=1, x1=3, y0=0, y1=4))
    B.append(Box(x0=2, x1=4, y0=5, y1=10))
    B.append(Box(x0=3, x1=5, y0=0, y1=8))

    assert len(B) == 3
    B.simplify()
    assert B.size() == 31
    assert len(B) == 4

    for x in B:
        for y in B:
            if x is not y:
                assert x.overlap(y) is None


# IBox
def test_ibox_init():
    B = Box(0, 0, 3, 4)

    I1 = IBox(B)
    assert len(I1) == 0

    I2 = IBox(B, ones=True)
    assert len(I2) == 12

    I = np.array(range(12), dtype=np.bool).reshape(3, 4)
    I3 = IBox(B, iset=I)
    assert len(I3) == 11

    I4 = I3.copy()
    assert len(I4) == 11

    I4.clear()
    assert len(I4) == 0


def test_ibox_add_sub_point():
    B = Box(0, 0, 3, 4)
    I = IBox(B)
    I.add_point((1, 1))
    assert len(I) == 1
    I.add_point((1, 1))
    assert len(I) == 1
    I.add_point((2, 2))
    assert len(I) == 2
    I.sub_point((1, 1))
    assert len(I) == 1
    I.sub_point((2, 2))
    assert len(I) == 0
    I.add_point((1, 1))
    I.add_point((2, 2))
    assert len(I) == 2


def test_ibox_extract():
    B = Box(0, 0, 3, 4)
    I = IBox(B)
    I.add_point((1, 1))
    I.add_point((2, 2))

    B1 = Box(1, 1, 2, 3)
    I1 = I.extract_array(B1)
    assert len(I1) == 1

    B2 = Box(1, 1, 3, 3)
    I2 = I.extract_array(B2)
    assert len(I2) == 2

    I3 = I.extract_ibox(B2)
    assert len(I3) == 2
    assert I3.xy() == (1, 3, 1, 3)


def test_ibox_bool():
    x = [1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1]
    y = [1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1]
    X = np.array(x, dtype=np.bool).reshape(3, 4)
    Y = np.array(y, dtype=np.bool).reshape(3, 4)
    B = Box(0, 0, 3, 4)
    IX = IBox(B, iset=X)
    IY = IBox(B, iset=Y)
    assert len(IX) == 6
    assert len(IY) == 6
    IX &= IY
    assert len(IX) == 4
    IY -= IX
    assert len(IY) == 2

    X = np.array(x, dtype=np.bool).reshape(3, 4)
    Y = np.array(y, dtype=np.bool).reshape(3, 4)
    IX = IBox(B, iset=X)
    IY = IBox(B, iset=Y)
    IX |= IY
    assert len(IX) == 8

    X = np.array(x, dtype=np.bool).reshape(3, 4)
    Y = np.array(y, dtype=np.bool).reshape(3, 4)
    IX = IBox(B, iset=X)
    IY = IBox(B, iset=Y)
    assert len(IX) == 6
    assert len(IY) == 6
    assert IX.meets(IY)
    assert len(IX) == 6
    assert len(IY) == 6


def test_iset():
    a1 = [1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1]
    a2 = [1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1]
    A1 = np.array(a1, dtype=np.bool).reshape(3, 4)
    A2 = np.array(a2, dtype=np.bool).reshape(3, 4)
    B1 = Box(0, 0, 3, 4)
    B2 = Box(2, 0, 5, 4)
    B3 = Box(3, 0, 6, 4)
    I1 = IBox(B1, iset=A1)
    I2 = IBox(B1, iset=A2)
    I3 = IBox(B2, iset=A1)
    I4 = IBox(B2, iset=A2)
    I5 = IBox(B3, iset=A1)
    I6 = IBox(B3, iset=A2)
    with pytest.raises(AssertionError):
        ISet([I1, I2])
    with pytest.raises(AssertionError):
        ISet([I1, I3])
    with pytest.raises(AssertionError):
        ISet([I4, I6])
    J1 = ISet([I1, I5])
    J2 = ISet([I1, I6])
    J3 = ISet([I2, I5])
    J4 = ISet([I2, I6])
    assert len(I1) == 6
    assert len(J1.boxes[0]) == 6
    assert len(J1) == 12
    assert len(J3) == 12
    assert len(J1 & J3) == 10
    assert len(J1 & J4) == 8
    assert len(J1 | J4) == 16
    assert len(J1 - J4) == 4
    assert J1.sig == J2.sig

def test_pset():
    pass
