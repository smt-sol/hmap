from iset import Box,Boxes,IBox,ISet
import numpy as np

from skimage.measure import label
from scipy.ndimage.morphology import binary_fill_holes

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,QObject

from log import sbar
from ig import ItemGroup

class WorkArea(QObject):
    generated=pyqtSignal()
    
    def __init__(self,viewer,log):#,width,height):
        super(WorkArea,self).__init__()

        self.viewer = viewer
        self.log = log.log
        fillcolor = QColor(170,255,0,200)
        self.items = ItemGroup(viewer,fillcolor)
        self.clear()

    def clear(self):
        self.items.clear()
        self.bbox = None
        self.shape = None
        self.bands = {}

        self.atts = None
        self.labels = None
        self.size = None

    def add(self,box):
        for x,i in self.items:
            if x.overlap(box) is not None:
                try:
                    box.shrink(x)
                except ValueError:
                    return
        self.items.add_rect(box)

            
    def sub(self,i):
        assert i >= 0 and i < len(self.items)
        box,item = self.items.pop(i)
        self.viewer.scene.removeItem(item)

    def full(self,w,h,bands):
        self.clear()
        self.add(Box(0,0,w,h))
        self.generate(bands)
        self.hide()
        
    def add_visible(self):
        self.items.add_vis()

    def clr_visible(self):
        self.items.clr_vis()

    def clr_point(self,x,y):
        self.items.clr_point(x,y)        
    
    def show(self):
        self.items.vis_set(True)

    def hide(self):
        self.items.vis_set(False)

    def set_visibility(self,vis):
        self.items.vis_set(vis)

    @sbar
    def generate(self,bands):
        # BOXES
        if not self.items:
            self.log("popE","empty workarea")
            return
        boxes = [x[0] for x in self.items]
        self.bbox = Boxes(boxes).bbox()
        self.shape = (self.bbox.dx,self.bbox.dy)

        # BANDS
        for x in "rgbhsv":
            cb = bands[x]
            cboxes = []
            for box,item in self.items:
                iset = cb[box.x0:box.x1,box.y0:box.y1]
                cboxes.append(IBox(box,iset=iset))
            self.bands[x] = ISet(cboxes)
        self.generated.emit()
