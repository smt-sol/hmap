from os.path import basename #,abspath,normpath,exists

from PyQt5.QtWidgets import QPushButton,QButtonGroup,QRadioButton
from PyQt5.QtWidgets import QSpinBox,QLabel
from PyQt5.QtWidgets import QGridLayout,QFormLayout

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,Qt

from color import color_label,color_button


class SelectionW(QGridLayout):
    paraChanged = pyqtSignal()
    selScheme = pyqtSignal(str)

    def __init__(self,hmap):
        super(SelectionW,self).__init__()

        self.hmap = hmap

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()
        self.create_connections()

    def toggle_visibility(self,hide=False):
        vis = not self.title.isVisible()
        if hide:
            vis = False
        self.title.setVisible(vis)
        self.resetButton.setVisible(vis)
        self.bgLabel.setVisible(vis)
        self.rgb.setVisible(vis)
        self.hsv.setVisible(vis)
        self.hsx.setVisible(vis)
        self.para1Label.setVisible(vis)
        self.para2Label.setVisible(vis)
        self.para3Label.setVisible(vis)
        self.min1.setVisible(vis)
        self.del1.setVisible(vis)
        self.max1.setVisible(vis)
        self.min1Label.setVisible(vis)
        self.del1Label.setVisible(vis)
        self.max1Label.setVisible(vis)
        self.min2.setVisible(vis)
        self.del2.setVisible(vis)
        self.max2.setVisible(vis)
        self.min2Label.setVisible(vis)
        self.del2Label.setVisible(vis)
        self.max2Label.setVisible(vis)
        self.min3.setVisible(vis)
        self.del3.setVisible(vis)
        self.max3.setVisible(vis)
        self.min3Label.setVisible(vis)
        self.del3Label.setVisible(vis)
        self.max3Label.setVisible(vis)

    def create_widgets(self):
        self.title = QLabel("* Selection *")
        color_label(self.title,QColor("black"),QColor("white"))
        self.resetButton = QPushButton("Reset")

        self.bgLabel = QLabel("color scheme")
        self.bg = QButtonGroup()
        self.rgb = QRadioButton("rgb")
        self.hsv = QRadioButton("hsv")
        self.hsx = QRadioButton("hs")
        self.bg.addButton(self.rgb)
        self.bg.addButton(self.hsv)
        self.bg.addButton(self.hsx)

        self.para1Label = QLabel("Parameter 1 (Red/Hue)")
        self.min1 = QSpinBox()
        self.del1 = QSpinBox()
        self.max1 = QSpinBox()
        self.min1Label = QLabel("min")
        self.del1Label = QLabel("del")
        self.max1Label = QLabel("max")

        self.para2Label = QLabel("Parameter 2 (Green/Saturation)")
        self.min2 = QSpinBox()
        self.del2 = QSpinBox()
        self.max2 = QSpinBox()
        self.min2Label = QLabel("min")
        self.del2Label = QLabel("del")
        self.max2Label = QLabel("max")

        self.para3Label = QLabel("Parameter 3 (Blue/Value)")
        self.min3 = QSpinBox()
        self.del3 = QSpinBox()
        self.max3 = QSpinBox()
        self.min3Label = QLabel("min")
        self.del3Label = QLabel("del")
        self.max3Label = QLabel("max")

    def set_widgets(self):
        self.min1.setMinimum(-1)
        self.min2.setMinimum(0)
        self.min3.setMinimum(0)
        self.min1.setMaximum(359)
        self.min2.setMaximum(359)
        self.min3.setMaximum(359)

        self.del1.setMinimum(0)
        self.del2.setMinimum(0)
        self.del3.setMinimum(0)
        self.del1.setMaximum(359)
        self.del2.setMaximum(359)
        self.del3.setMaximum(359)

        self.max1.setMinimum(0)
        self.max2.setMinimum(0)
        self.max3.setMinimum(0)
        self.max1.setMaximum(359)
        self.max2.setMaximum(359)
        self.max3.setMaximum(359)

        for w in (self.min1Label,self.del1Label,self.max1Label,
                  self.min2Label,self.del2Label,self.max2Label,
                  self.min3Label,self.del3Label,self.max3Label):
            w.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.reset()

    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,7)
        self.addWidget(self.resetButton,0,7)
        self.addWidget(self.bgLabel,1,0,1,2)

        for x in range(1,4):
            self.addWidget(self.__dict__["para"+str(x)+"Label"],x+1,0)
            self.addWidget(self.__dict__["min"+str(x)+"Label"],x+1,1)
            self.addWidget(self.__dict__["min"+str(x)],x+1,2)
            self.addWidget(self.__dict__["del"+str(x)+"Label"],x+1,3)
            self.addWidget(self.__dict__["del"+str(x)],x+1,4)
            self.addWidget(self.__dict__["max"+str(x)+"Label"],x+1,5)
            self.addWidget(self.__dict__["max"+str(x)],x+1,6)

    def create_connections(self):
        self.rgb.toggled.connect(self.rgbtoggle)
        self.hsv.toggled.connect(self.rgbtoggle)
        self.hsx.toggled.connect(self.rgbtoggle)
        self.resetButton.clicked.connect(self.reset)
        for x in range(1,4):
            for y in ("min","del","max"):
                self.__dict__[y+str(x)].valueChanged.connect(self.paraChanged)


    def reset(self):
        self.min1.setValue(0)
        self.min2.setValue(15)
        self.min3.setValue(0)
        self.del1.setValue(6)
        self.del2.setValue(15)
        self.del3.setValue(0)
        self.max1.setValue(359)
        self.max2.setValue(359)
        self.max3.setValue(359)

        self.hsx.setChecked(True)

        self.addWidget(self.rgb,1,2)
        self.addWidget(self.hsv,1,3)
        self.addWidget(self.hsx,1,4)

    def rgbtoggle(self):
        text = self.get_color_scheme()
        self.selScheme.emit(text)

    def get_color_scheme(self):
        return self.bg.checkedButton().text()

    def get_para(self,n):
        if n == 1:
            return self.min1.value(),self.del1.value(),self.max1.value()
        elif n == 2:
            return self.min2.value(),self.del2.value(),self.max2.value()
        elif n == 3:
            return self.min3.value(),self.del3.value(),self.max3.value()
        else:
            raise ValueError(n)

    def get_dpara(self):
        return {i:self.get_para(i) for i in range(1,4)}

    def set_dpara(self,d):
        for i,val in d.items():
            assert i in range(1,4)
            self.set_para(i,val)

    def set_para(self,i,val):
        s = str(i)
        self.__dict__["min" +s].setValue(val[0])
        self.__dict__["del" +s].setValue(val[1])
        self.__dict__["max" +s].setValue(val[2])


class PolyW(QGridLayout):
    ppUpdate = pyqtSignal()
    ppClear = pyqtSignal()

    def __init__(self,hmap):
        super(PolyW,self).__init__()

        self.hmap = hmap

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()
        self.create_connections()

    def toggle_visibility(self):
        vis = not self.title.isVisible()
        self.title.setVisible(vis)
        self.pp.setVisible(vis)
        self.ppclear.setVisible(vis)
        self.ppshow.setVisible(vis)
        self.ppuse.setVisible(vis)
        self.ppprev.setVisible(vis)
        self.ppnext.setVisible(vis)
        self.ppvis.setVisible(vis)

    def create_widgets(self):
        self.title = QLabel("* Polygons *")
        color_label(self.title,QColor("black"),QColor("white"))

        self.pp = QPushButton("comp")
        self.ppclear = QPushButton("clear")
        self.ppuse = QPushButton("use")
        self.ppprev = QPushButton("prev")
        self.ppnext = QPushButton("next")
        self.ppshow = QPushButton("show")
        self.ppvis = QPushButton("getvis")

    def set_widgets(self):
        self.ppshow.setCheckable(True)

    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,7)
        self.addWidget(self.pp,1,0)
        self.addWidget(self.ppuse,1,1)
        self.addWidget(self.ppclear,1,2)
        self.addWidget(self.ppshow,1,3)
        self.addWidget(self.ppprev,1,4)
        self.addWidget(self.ppnext,1,5)
        self.addWidget(self.ppvis,1,6)

    def create_connections(self):
        self.pp.clicked.connect(self.pp_update)

    def get_all(self):
        return {
            "pp" : self.pp.text(),
            "ppshow" : self.ppshow.isChecked(),
        }

    def pp_update(self):
        txts = "comp,poly,edit".split(",")
        idx = txts.index(self.pp.text())
        self.pp.setText(txts[(idx+1) % len(txts)])

class ParameterW(QGridLayout):
    def __init__(self,hmap):
        super(ParameterW,self).__init__()

        self.hmap = hmap

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()
        self.create_connections()

    def toggle_visibility(self):
        vis = not self.title.isVisible()
        self.title.setVisible(vis)
        self.resetButton.setVisible(vis)
        self.add_remove.setVisible(vis)
        self.protect_overwrite.setVisible(vis)

        self.ocde.setVisible(vis)
        self.xy.setVisible(vis)
        self.vonly.setVisible(vis)

    def create_widgets(self):
        self.title = QLabel("* Parameters *")
        color_label(self.title,QColor("black"),QColor("white"))

        self.resetButton = QPushButton("reset")
        self.add_remove = QPushButton("add")
        self.protect_overwrite = QPushButton("protect")

        self.ocde = QPushButton("open")
        self.xy = QPushButton("xy")

        self.vonly = QPushButton("vis only")


    def set_widgets(self):
        self.vonly.setCheckable(True)
        color_button(self.vonly,QColor(0,255,0))

    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,7)
        self.addWidget(self.add_remove,1,0)
        self.addWidget(self.protect_overwrite,1,1)
        self.addWidget(self.ocde,1,2)
        self.addWidget(self.xy,1,3)
        self.addWidget(self.vonly,1,4)

    def create_connections(self):
        self.add_remove.clicked.connect(self.add_update)
        self.protect_overwrite.clicked.connect(self.protect_update)
        self.ocde.clicked.connect(self.ocde_update)
        self.xy.clicked.connect(self.xy_update)


    def get_all(self):
        return {
            "add_remove" : self.add_remove.text(),
            "protect_overwrite" : self.protect_overwrite.text(),
            "ocde" : self.ocde.text(),
            "xy" : self.xy.text(),
        }

    def add_update(self):
        if self.add_remove.text() == "add":
            self.add_remove.setText("remove")
        else:
            self.add_remove.setText("add")
        self.hmap.log(["add_update",self.add_remove.text()])

    def protect_update(self):
        if self.protect_overwrite.text() == "protect":
            self.protect_overwrite.setText("overwrite")
        else:
            self.protect_overwrite.setText("protect")
        self.hmap.log(["protect_update",self.protect_overwrite.text()])

    def ocde_update(self):
        txts = "open,open2,close,close2,dilate,erode".split(",")
        idx = txts.index(self.ocde.text())
        self.ocde.setText(txts[(idx+1) % 6])

    def xy_update(self):
        txts = "xy,x,y".split(",")
        idx = txts.index(self.xy.text())
        self.xy.setText(txts[(idx+1) % 3])

    def get_cls(self):
        return 20
