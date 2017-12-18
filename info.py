from os.path import basename #,abspath,normpath,exists

from PyQt5.QtWidgets import QPushButton,QButtonGroup,QRadioButton
from PyQt5.QtWidgets import QSpinBox,QLabel
from PyQt5.QtWidgets import QGridLayout,QFormLayout

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,Qt

from color import color_label,color_button

class InfoW(QFormLayout):
    def __init__(self,viewer):
        super(InfoW,self).__init__()

        self.viewer = viewer
        self.width = None
        self.height = None
        self.mousepos = None
        self.mousebox1 = None
        self.mousebox2 = None
        self.zm = 0.0

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()
        self.create_connections()

    def create_widgets(self):
        self.mode = QLabel()
        self.path = QLabel()
        self.image = QLabel()
        self.mouse = QLabel()
        self.cnt = QLabel()
        self.coll = QLabel()
        self.sel = QLabel()

    def set_widgets(self):
        pass

    def layout_widgets(self):
        self.addRow("Mode:",self.mode)
        self.addRow("File:",self.path)
        self.addRow("Image:",self.image)
        self.addRow("Mouse:",self.mouse)
        self.addRow("Collisions:",self.coll)
        self.addRow("Contours:",self.cnt)
        self.addRow("Selection:",self.sel)

    def create_connections(self):
        self.viewer.zoomChanged.connect(self.update_zoom)
        self.viewer.mouseMoveLoc.connect(self.update_mouse_move_pos)
        self.viewer.mousePressLoc.connect(self.update_mouse_press_pos)
        self.viewer.mouseReleaseLoc.connect(self.update_mouse_release_pos)

    def reset(self):
        print("INFO RESET")
        self.mode.setText("view")
        self.path.setText("")
        self.image.setText("")
        self.mouse.setText("")

    def update_zoom(self):
        trn = self.viewer.transform()
        self.zm = max(trn.m11(),trn.m22())
        self.update_image()

    def update_image(self,path=None,w=None,h=None):
        if path is not None:
            base = basename(str(path))
            self.path.setText(base)
        if w is not None:
            self.width = w
        if h is not None:
            self.height = h

        l,r,t,b = self.viewer.getVisible()
        v = str(l) + "-" + str(r) + " x " + str(t) + "-" + str(b)

        zm = '{:.2f}'.format(self.zm)
        txt = str(self.width) + "x" + str(self.height) + " pixs *** " +\
              v + " vis *** " + \
              zm + " mag *** "
        self.image.setText(txt)

    def update_mouse_move_pos(self,x,y):
        self.mousepos = (x,y)
        self.update_mouse()

    def update_mouse_press_pos(self,x,y):
        self.mousebox1 = (x,y)
        self.update_mouse()
        self.update_image()

    def update_mouse_release_pos(self,x,y):
        self.mousebox2 = (x,y)
        self.update_mouse()
        self.update_image()

    def update_mouse(self):
        pt = str(self.mousepos) if self.mousepos is not None else "---"
        b1 = str(self.mousebox1) if self.mousebox1 is not None else "---"
        b2 = str(self.mousebox2) if self.mousebox2 is not None else "---"
        txt = "POS: " + pt + " BOX: " + b1 + "~" + b2
        self.mouse.setText(txt)


    #def update_contours(self):
    #    txt = []
    #    for a in self.hmap.att.a2cset:
    #        txt.append(a+":"+str(len(self.hmap.att.a2cset[a].keys())))
    #    self.cnt.setText("---".join(txt))

    #def update_collisions(self):
    #    txt = []
    #    for x in self.hmap.att.a2coll:
    #        if self.hmap.att.a2coll[x]:
    #            txt.append(str(x)+":"+str(len(self.hmap.att.a2coll[x])))
    #    self.coll.setText("---".join(txt))
