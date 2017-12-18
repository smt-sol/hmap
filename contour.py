from os.path import basename #,abspath,normpath,exists

from PyQt5.QtWidgets import QPushButton,QButtonGroup,QRadioButton
from PyQt5.QtWidgets import QSpinBox,QLabel
from PyQt5.QtWidgets import QGridLayout,QFormLayout

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,Qt

from color import color_label,color_button

class ContourW(QGridLayout):
    def __init__(self):
        super(ContourW,self).__init__()

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()

    def toggle_visibility(self):
        vis = not self.title.isVisible()
        self.title.setVisible(vis)
        self.shwA.setVisible(vis)
        self.shwU.setVisible(vis)
        self.shwN.setVisible(vis)
        self.fat.setVisible(vis)
        self.fixGU.setVisible(vis)
        self.fixHU.setVisible(vis)
        self.fixGA.setVisible(vis)
        self.fixHA.setVisible(vis)
        self.shwG.setVisible(vis)
        self.hidG.setVisible(vis)
        self.fatG.setVisible(vis)
        self.shwH.setVisible(vis)
        self.hidH.setVisible(vis)
        self.fatH.setVisible(vis)
        self.maxH.setVisible(vis)
        self.maxG.setVisible(vis)
        self.labH.setVisible(vis)
        self.labG.setVisible(vis)

        self.fixB.setVisible(vis)
        self.maxB.setVisible(vis)
        self.maxBB.setVisible(vis)
        self.shwB.setVisible(vis)
        self.hidB.setVisible(vis)
        self.fatB.setVisible(vis)


    def create_widgets(self):
        self.title = QLabel("* Cnts/Gomi/Holes/Bnds *")

        self.shwA = QPushButton("show C")
        self.shwU = QPushButton("show use C")
        self.shwN = QPushButton("hide C")

        self.fat = QPushButton("fat C")

        self.shwG = QPushButton("show G")
        self.labG = QPushButton("? pixels")
        self.hidG = QPushButton("hide G")
        self.fatG = QPushButton("fat G")
        self.fixGA = QPushButton("fix G all ")
        self.fixGU = QPushButton("fix G use")

        self.maxG = QSpinBox()

        self.shwH = QPushButton("show H")
        self.labH = QPushButton("? pixels")
        self.hidH = QPushButton("hide H")
        self.fatH = QPushButton("fat H")
        self.fixHA = QPushButton("fix H all")
        self.fixHU = QPushButton("fix H use")
        self.maxH = QSpinBox()

        self.fixB = QPushButton("fix B")
        self.labB = QPushButton("? pixels")
        self.maxB = QSpinBox()
        self.maxBB = QSpinBox()
        self.shwB = QPushButton("show B")
        self.hidB = QPushButton("hide B")
        self.fatB = QPushButton("fat B")


    def set_widgets(self):
        color_label(self.title,QColor("black"),QColor("white"))
        color_button(self.fixGA,QColor(0,255,0))
        color_button(self.fixHA,QColor(0,255,0))
        color_button(self.fixGU,QColor(0,255,0))
        color_button(self.fixHU,QColor(0,255,0))
        color_button(self.fat,QColor(255,255,0))
        color_button(self.shwA,QColor(255,255,0))
        color_button(self.shwU,QColor(255,255,0))
        color_button(self.shwN,QColor(255,255,0))

        color_button(self.shwG,QColor(255,255,0))
        color_button(self.hidG,QColor(255,255,0))
        color_button(self.fatG,QColor(255,255,0))
        color_button(self.shwH,QColor(255,255,0))
        color_button(self.hidH,QColor(255,255,0))
        color_button(self.fatH,QColor(255,255,0))

        color_button(self.fixB,QColor(0,255,0))
        color_button(self.hidB,QColor(255,255,0))
        color_button(self.shwB,QColor(255,255,0))
        color_button(self.fatB,QColor(255,255,0))

        color_button(self.labB,QColor(255,255,0))
        color_button(self.labG,QColor(255,255,0))
        color_button(self.labH,QColor(255,255,0))


        self.fat.setCheckable(True)
        self.fatG.setCheckable(True)
        self.fatH.setCheckable(True)
        self.fatB.setCheckable(True)

        self.maxB.setMinimum(0)
        self.maxB.setValue(4)
        self.maxB.setMaximum(40)

        self.maxBB.setMinimum(10)
        self.maxBB.setValue(1000)
        self.maxBB.setMaximum(1000000000)

        self.maxG.setMinimum(1)
        self.maxG.setMaximum(10000)
        self.maxH.setMinimum(1)
        self.maxH.setMaximum(10000)
        self.maxG.setValue(9)
        self.maxH.setValue(9)

    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,8)
        self.addWidget(self.shwA,1,0)
        self.addWidget(self.shwU,1,1)
        self.addWidget(self.shwN,1,2)
        self.addWidget(self.fat,1,3)

        self.addWidget(self.shwG,2,0)
        self.addWidget(self.labG,2,1)
        self.addWidget(self.hidG,2,2)
        self.addWidget(self.fatG,2,3)
        self.addWidget(self.fixGA,2,4)
        self.addWidget(self.fixGU,2,5)
        self.addWidget(self.maxG,2,6)

        self.addWidget(self.shwH,3,0)
        self.addWidget(self.labH,3,1)
        self.addWidget(self.hidH,3,2)
        self.addWidget(self.fatH,3,3)
        self.addWidget(self.fixHA,3,4)
        self.addWidget(self.fixHU,3,5)
        self.addWidget(self.maxH,3,6)

        self.addWidget(self.shwB,4,0)
        self.addWidget(self.labB,4,1)
        self.addWidget(self.hidB,4,2)
        self.addWidget(self.fatB,4,3)
        self.addWidget(self.fixB,4,4)
        self.addWidget(self.maxB,4,6)
        self.addWidget(self.maxBB,4,7)
