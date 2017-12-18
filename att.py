from iset import PSet,ISet
from ig import ItemGroup

from PyQt5.QtGui import QPixmap,QBitmap,QColor
from PyQt5.QtCore import Qt

from iset import IBox

DEF_PRM = {
    "hs" : {1:(0,5,360),2:(15,10,256),3:(0,0,0)},
    "rgb" : {1:(0,25,256),2:(0,25,256),3:(0,25,256)},
    "hsv" : {1:(0,5,360),2:(15,10,256),3:(0,40,256)}
}

UPCOLOR = {
    1:QColor(0, 255, 255),
    11:QColor(255, 153, 0),
    12:QColor(0, 255, 85),
    13:QColor(0, 255, 255),
    14:QColor(0, 0, 255),
    15:QColor(102, 0, 255),
    21:QColor(255, 153, 0),
    22:QColor(0, 255, 85),
    23:QColor(0, 255, 255),
    24:QColor(0, 0, 255),
    25:QColor(255, 0, 102),
    26:QColor(255, 0, 255),
    27:QColor(102, 0, 255),
    31:QColor(255, 153, 0),
    32:QColor(0, 255, 85),
    33:QColor(0, 255, 255),
    34:QColor(0, 0, 255),
    35:QColor(255, 0, 102),
    36:QColor(255, 0, 255),
    41:QColor(255, 153, 0),
    42:QColor(0, 255, 85),
    43:QColor(0, 255, 255),
    44:QColor(0, 0, 255),
    45:QColor(255, 0, 102),
    46:QColor(255, 0, 255),
    47:QColor(102, 0, 255),
    48:QColor(102, 102, 255),
    99:QColor(0, 0, 0)
}


BITPAD = 32
BITSHIFT = 1
BITOFF = 0

class AttData:
    def __init__(self,viewer,w,h,att,col):
        self.att = att     # integer 11-15 or 21-27
        self.col = col     # display color
        self.prm = DEF_PRM # parameters
        self.scm = "hs"    # color scheme
        self.old = None    # old color
        self.pix = PSet()  # pixel sets

        self.viewer = viewer
        w += (BITPAD-BITSHIFT)-((w+(BITPAD-BITSHIFT))%BITPAD) + BITOFF
        self.width = w
        self.height = h
        pm = QPixmap(w,h)
        pm.fill(QColor(0,0,0,0))
        self.itm = self.viewer.scene.addPixmap(pm)
        #self.update_pmap()
        self.hide()
        print("WH",w,h)

    def pack(self):
        data = {
            "att":self.att,
            "col":self.col.getRgb()[:3],
            "prm":self.prm,
            "scm":self.scm,
            "old":self.old.getRgb()[:3] if self.old is not None else None,
            "pix":self.pix.curr,
            "wh":(self.width,self.height)
        }
        return data

    @staticmethod
    def unpack(a,data,viewer,boxes):
        w,h = data["wh"]
        AD = AttData(viewer,w,h,data["att"],UPCOLOR[a])
        for b in boxes:
            AD.pix.add_box(b)
        AD.att = data
        AD.old = None if data["old"] is None else QColor(*data["old"])
        AD.prm = data["prm"]
        AD.scm = data["scm"]
        AD.add_pixs(data["pix"])
        return AD

    def col_update(self,col):
        self.col = col
        self.update_pmap()

    def simplify(self):
        self.pix.simplify()

    def update_pmap(self):
        print("UPDATE PMAP")
        pmap = self.pix.bitmap(self.width,self.height,self.col)
        self.itm.setPixmap(pmap)

    def add_pixs(self,pixs):
        assert isinstance(pixs,ISet)
        self.pix.add(pixs)
        self.update_pmap()

    def sub_pixs(self,pixs):
        assert isinstance(pixs,ISet)
        self.pix.sub(pixs)
        self.update_pmap()

    def intersect_pixs(self,pixs):
        assert isinstance(pixs,ISet)
        self.pix.intersect(pixs)
        self.update_pmap()

    def sub_box(self,box):
        print("SUB",box)
        IB = IBox(box,ones=True)
        self.sub_pixs(ISet([IB]))

    def restrict_box(self,box):
        print("KEEPVIS",box)
        self.pix.restrict_box(box)
        self.update_pmap()

    def show(self):
        self.set_vis(True)

    def hide(self):
        self.set_vis(False)

    def set_vis(self,vis):
        print("VIS",vis,len(self.pix))
        self.itm.setZValue(2 if vis else -1)

    def rm_item(self):
        self.viewer.scene.removeItem(self.itm)

    def undo(self):
        self.pix.undo()
        self.update_pmap()

    def redo(self):
        self.pix.redo()
        self.update_pmap()
