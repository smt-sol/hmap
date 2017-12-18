#from PyQt5.QtGui import QImage,QPixmap,QBitmap,QColor,QPen,QBrush,QPolygonF
from PyQt5.QtGui import QColor,QPen,QBrush,QPolygonF
from PyQt5.QtCore import pyqtSignal,Qt,QPointF

#from ibox import Box

class ItemGroup(list):
    def __init__(self,viewer,fillcolor=QColor("black")):
        super(ItemGroup,self).__init__()
        self.viewer = viewer
        self.fillcolor = fillcolor

    def clear(self):
        while self:
            b,i = self.pop()
            self.viewer.scene.removeItem(i)

    def add_rect(self,box,fillcolor=None):
        if fillcolor is None:
            fillcolor = self.fillcolor
        P = QPen(fillcolor)
        B = QBrush(fillcolor,Qt.SolidPattern)
        x0,x1,y0,y1 = box.x0,box.x1,box.y0,box.y1
        item = self.viewer.scene.addRect(x0,y0,x1-x0,y1-y0,P,B)
        item.setZValue(100)
        self.append((box,item))

    def add_line(self,line,fillcolor=None):
        if fillcolor is None:
            fillcolor = self.fillcolor
        P = QPen(fillcolor)
        P.setWidth(5)

        (x0,y0),(x1,y1) = line

        item = self.viewer.scene.addLine(x0,y0,x1,y1,P)
        item.setZValue(100)
        self.append((line,item))

    def add_bbox(self,line,fillcolor=None):
        if fillcolor is None:
            fillcolor = self.fillcolor
        P = QPen(fillcolor)
        B = QBrush(fillcolor,Qt.SolidPattern)
        (x0,y0),(x1,y1) = line
        item = self.viewer.scene.addRect(x0,y0,x1-x0,y1-y0,P,B)
        item.setZValue(100)
        self.append((line,item))

    def add_point(self,point,fillcolor=None):
        if fillcolor is None:
            fillcolor = self.fillcolor
        P = QPen(fillcolor)
        B = QBrush(fillcolor,Qt.SolidPattern)

        (x0,y0) = point[0]

        item = self.viewer.scene.addRect(x0-5,y0-5,11,11,P,B)
        item.setZValue(100)
        self.append((point,item))

    def add_polygon(self,polygon,fillcolor=None):
        if fillcolor is None:
            fillcolor = self.fillcolor
        P = QPen(fillcolor)
        B = QBrush(fillcolor,Qt.SolidPattern)
        poly = QPolygonF([QPointF(*x)  for x in polygon])
        item = self.viewer.scene.addPolygon(poly,P,B)
        item.setZValue(100)
        self.append((poly,item))

    def add_bitmap(self,box):
        pass

    def add_vis(self):
        vis = self.viewer.getVBox()
        self.add_rect(vis)

    def clr_vis(self):
        vis = self.viewer.getVBox()
        rem = self.search_box(vis)
        self.rm_items(rem)

    def clr_point(self,x,y):
        rem = self.search_point(x,y)
        self.rm_items(rem)

    def search_point(self,x,y):
        ret = []
        for (idx,(b,i)) in enumerate(self):
            if b.contains(x,y):
                ret.append(idx)
        return ret

    def search_box(self,box):
        ret = []
        for idx,(b,i) in enumerate(self):
            if box.overlap(b) is not None:
                ret.append(idx)
        return ret
        self.rm_items(rem)

    def rm_items(self,idxs):
        for idx in sorted(idxs,key=lambda x : -x):
            b,i = self.pop(idx)
            self.viewer.scene.removeItem(i)

    def vis_set(self,vis=True):
        if vis:
            for (b,i) in self:
                i.setZValue(100)
        else:
            for (b,i) in self:
                i.setZValue(-1)

    def vis_toggle(self):
        for (b,i) in self:
            i.setZValue(-i.zValue())
