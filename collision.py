from os.path import basename #,abspath,normpath,exists

from PyQt5.QtWidgets import QPushButton,QButtonGroup,QRadioButton
from PyQt5.QtWidgets import QSpinBox,QLabel
from PyQt5.QtWidgets import QGridLayout,QFormLayout

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,Qt

from color import color_label,color_button

class CollisionW(QGridLayout):
    def __init__(self):
        super(CollisionW,self).__init__()

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()
        self.create_connections()

    def toggle_visibility(self):
        vis = not self.title.isVisible()
        self.title.setVisible(vis)
        self.shwA.setVisible(vis)
        self.shwU.setVisible(vis)
        self.shwN.setVisible(vis)
        self.fat.setVisible(vis)
        self.fix.setVisible(vis)


    def create_widgets(self):
        self.title = QLabel("* Collisions *")

        self.shwA = QPushButton("show all")
        self.shwU = QPushButton("show use")
        self.shwN = QPushButton("show none")

        self.fat = QPushButton("fat")
        self.fat.setCheckable(True)

        self.fix = QPushButton("fix")
        self.fixO = QPushButton("fix order")
        self.updown = QPushButton("down")

    def create_connections(self):
        self.updown.clicked.connect(self.updown_update)

    def set_widgets(self):
        color_label(self.title,QColor("black"),QColor("white"))
        color_button(self.fix,QColor(0,255,0))
        color_button(self.fixO,QColor(0,255,0))
        color_button(self.updown,QColor(0,255,0))
        color_button(self.fat,QColor(255,255,0))
        color_button(self.shwA,QColor(255,255,0))
        color_button(self.shwU,QColor(255,255,0))
        color_button(self.shwN,QColor(255,255,0))


    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,8)
        self.addWidget(self.shwA,1,0)
        self.addWidget(self.shwU,1,1)
        self.addWidget(self.shwN,1,2)
        self.addWidget(self.fat,1,3)

        self.addWidget(self.fix,1,4)
        self.addWidget(self.fixO,1,5)
        self.addWidget(self.updown,1,6)

    def updown_update(self):
        txts = "up,down".split(",")
        idx = txts.index(self.xy.text())
        self.xy.setText(txts[(idx+1) % 2])
