from os.path import basename #,abspath,normpath,exists

from PyQt5.QtWidgets import QPushButton,QButtonGroup,QRadioButton
from PyQt5.QtWidgets import QSpinBox,QLabel
from PyQt5.QtWidgets import QGridLayout,QFormLayout

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,Qt

from color import color_label,color_button

class WorkAreaW(QGridLayout):
    def __init__(self):
        super(WorkAreaW,self).__init__()

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()

    def toggle_visibility(self,hide=False):
        if hide:
            vis = False
        else:
            vis = not self.title.isVisible()
        self.title.setVisible(vis)
        self.show.setVisible(vis)
        self.clr.setVisible(vis)
        self.full.setVisible(vis)
        self.gen.setVisible(vis)
        self.addV.setVisible(vis)
        self.clrV.setVisible(vis)

    def create_widgets(self):
        self.title = QLabel("* Work Area *")
        self.show = QPushButton("show")
        self.show.setCheckable(True)
        self.clr = QPushButton("clear")
        self.full = QPushButton("full")
        self.gen = QPushButton("generate")
        self.addV = QPushButton("addVis")
        self.clrV = QPushButton("clrVis")

    def set_widgets(self):
        color_label(self.title,QColor("black"),QColor("white"))
        color_button(self.show,QColor(255,255,0))
        color_button(self.clr,QColor(255,0,0))
        color_button(self.full,QColor(255,0,0))
        color_button(self.gen,QColor(255,0,0))
        color_button(self.addV,QColor(0,255,0))
        color_button(self.clrV,QColor(0,255,0)
        )
    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,8)
        self.addWidget(self.show,1,0)
        self.addWidget(self.clr,1,1)
        self.addWidget(self.full,1,2)
        self.addWidget(self.gen,1,3)
        self.addWidget(self.addV,1,4)
        self.addWidget(self.clrV,1,5)
