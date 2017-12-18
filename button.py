from os.path import basename #,abspath,normpath,exists

from PyQt5.QtWidgets import QPushButton,QButtonGroup,QRadioButton
from PyQt5.QtWidgets import QSpinBox,QLabel
from PyQt5.QtWidgets import QGridLayout,QFormLayout

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,Qt

from color import color_label,color_button

class ButtonW(QGridLayout):
    def __init__(self):
        super(ButtonW,self).__init__()

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()

    def create_widgets(self):
        self.edit = QPushButton("hist")
        self.warn = QPushButton("warn")
        self.para = QPushButton("para")
        self.ccb = QPushButton("ccb")
        self.poly = QPushButton("poly")
        self.slct = QPushButton("slct")
        self.work = QPushButton("work")
        self.attr = QPushButton("attr")

    def set_widgets(self):
        self.edit.setCheckable(True)
        self.warn.setCheckable(True)
        self.para.setCheckable(True)
        self.ccb.setCheckable(True)
        self.poly.setCheckable(True)
        self.slct.setCheckable(True)
        self.work.setCheckable(True)
        self.attr.setCheckable(True)

        color_button(self.edit,QColor("yellow"))
        color_button(self.warn,QColor("yellow"))
        color_button(self.para,QColor("yellow"))
        color_button(self.ccb,QColor("yellow"))
        color_button(self.poly,QColor("yellow"))
        color_button(self.slct,QColor("yellow"))
        color_button(self.work,QColor("yellow"))
        color_button(self.attr,QColor("yellow"))

    def layout_widgets(self):
        self.addWidget(self.work,0,0)
        self.addWidget(self.slct,0,1)
        self.addWidget(self.attr,0,2)
        self.addWidget(self.ccb,0,3)
        self.addWidget(self.poly,0,4)
        self.addWidget(self.para,0,5)
        self.addWidget(self.warn,0,6)
        self.addWidget(self.edit,0,7)
