from os.path import basename #,abspath,normpath,exists

from PyQt5.QtWidgets import QPushButton,QButtonGroup,QRadioButton
from PyQt5.QtWidgets import QSpinBox,QLabel
from PyQt5.QtWidgets import QGridLayout,QFormLayout
from PyQt5.QtWidgets import QCheckBox

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal,Qt

from color import color_label,color_button,get_color

class AttGenW(QGridLayout):
    _code = {
        1:"???",
        11:"0～0.5",
        12:"0.5～1.0",
        13:"1.0～2.0",
        14:"2.0～5.0",
        15:"5.0以",
        21:"0～0.5",
        22:"0.5～1.0",
        23:"1.0～2.0",
        24:"2.0～3.0",
        25:"3.0～4.0",
        26:"4.0～5.0",
        27:"5.0以上",
        31:"0～0.5ｍ未満",
        32:"0.5～3.0",
        33:"3.0～5.0",
        34:"5.0～10.0",
        35:"10.0～20.0",
        36:"20.0以上",
        41:"0～0.3",
        42:"0.3～0.5",
        43:"0.5～1.0",
        44:"1.0～3.0",
        45:"3.0～5.0",
        46:"5.0～10.0",
        47:"10.0～20.0",
        48:"20.0以上",
        99:"XXX"
    }

    _color = {
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

    tableUpdate = pyqtSignal(int)
    selUpdate = pyqtSignal()
    useUpdate = pyqtSignal()
    colUpdate = pyqtSignal(int)

    def __init__(self):
        super(AttGenW,self).__init__()

        self.newrow = 0
        self.table = {}

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()
        self.create_connections()

    def create_widgets(self):
        self.title = QLabel("* Generate Attributes *")
        self.set1 = QPushButton("1段階")
        self.set5 = QPushButton("5段階")
        self.set6 = QPushButton("6段階")
        self.set7 = QPushButton("7段階")
        self.set8 = QPushButton("8段階")
        self.clr = QPushButton("clear")
        self.shwA = QPushButton("all")
        self.shwS = QPushButton("use")
        self.shwN = QPushButton("none")
        self.bg = QButtonGroup()

    def set_widgets(self):
        color_label(self.title,QColor("black"),QColor("white"))
        color_button(self.set1,QColor(255,0,0))
        color_button(self.set5,QColor(255,0,0))
        color_button(self.set6,QColor(255,0,0))
        color_button(self.set7,QColor(255,0,0))
        color_button(self.set8,QColor(255,0,0))
        color_button(self.shwA,QColor(255,255,0))
        color_button(self.shwS,QColor(255,255,0))
        color_button(self.shwN,QColor(255,255,0))
        color_button(self.clr,QColor(255,0,0))

    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,8)
        self.addWidget(self.shwA,1,0)
        self.addWidget(self.shwS,1,1)
        self.addWidget(self.shwN,1,2)

        self.addWidget(self.set1,2,0)
        self.addWidget(self.set5,2,1)
        self.addWidget(self.set6,2,2)
        self.addWidget(self.set7,2,3)
        self.addWidget(self.set8,2,4)
        self.addWidget(self.clr,2,7)
        self.addWidget(QLabel("use"),3,0)
        self.addWidget(QLabel("show"),3,1)
        self.addWidget(QLabel("new"),3,2)
        self.addWidget(QLabel("old"),3,3)
        self.addWidget(QLabel("pixs"),3,4)
        self.addWidget(QLabel("RGB"),3,5)
        self.addWidget(QLabel("HSV"),3,6)

    def create_connections(self):
        self.set1.clicked.connect(self.gen1)
        self.set5.clicked.connect(self.gen5)
        self.set6.clicked.connect(self.gen6)
        self.set7.clicked.connect(self.gen7)
        self.set8.clicked.connect(self.gen8)
        self.clr.clicked.connect(self.clr_table)
        self.shwA.clicked.connect(self.show_all)
        self.shwS.clicked.connect(self.show_selected)
        self.shwN.clicked.connect(self.show_none)

    def clr_table(self):
        if self.table:
            for k,v in self.table.items():
                if k[1] == "act":
                    self.bg.removeButton(v)
                if k[1] not in ("att","col","idx"):
                    v.hide()
                    v.destroy()

            self.table = {}
            self.tableUpdate.emit(0)
            self.newrow = 0

    def gen1(self):
        if self.table != {}:
            return
        for i in range(1,2):
            self.add_att(i)
        self.add_ex()
        self.table[(0,"sel")].setChecked(True)
        self.tableUpdate.emit(1)

    def gen5(self):
        if self.table != {}:
            return
        for i in range(11,16):
            self.add_att(i)
        self.add_ex()
        self.table[(0,"sel")].setChecked(True)
        self.tableUpdate.emit(5)

    def gen6(self):
        if self.table != {}:
            return
        for i in range(31,37):
            self.add_att(i)
        self.add_ex()
        self.table[(0,"sel")].setChecked(True)
        self.tableUpdate.emit(6)

    def gen7(self):
        if self.table != {}:
            return
        for i in range(21,28):
            self.add_att(i)
        self.add_ex()
        self.table[(0,"sel")].setChecked(True)
        self.tableUpdate.emit(7)

    def gen8(self):
        if self.table != {}:
            return
        for i in range(41,49):
            self.add_att(i)
        self.add_ex()
        self.table[(0,"sel")].setChecked(True)
        self.tableUpdate.emit(8)


    def add_ex(self):
        self.add_att(99)

    def add_att(self,i):
        off = 4
        idx = self.newrow
        self.newrow += 1

        att = self._code[i]
        self.table[(idx,"idx")] = i
        self.table[(idx,"att")] = att
        self.table[(idx,"col")] = self._color[i]
        self.table[(idx,"sel")] = QRadioButton()
        self.table[(idx,"act")] = QCheckBox()
        self.table[(idx,"pix")] = QLabel("0")
        self.table[(idx,"new")] = QPushButton(att)
        self.table[(idx,"old")] = QPushButton(att)
        self.table[(idx,"rgb")] = QLabel()
        self.table[(idx,"hsv")] = QLabel()
        self.table[(idx,"hsl")] = QLabel()

        self.bg.addButton(self.table[(idx,"sel")],i)
        color_button(self.table[(idx,"new")],self.table[(idx,"col")])

        self.addWidget(self.table[(idx,"sel")],idx+off,0)
        self.addWidget(self.table[(idx,"act")],idx+off,1)
        self.addWidget(self.table[(idx,"new")],idx+off,2)
        self.addWidget(self.table[(idx,"old")],idx+off,3)
        self.addWidget(self.table[(idx,"pix")],idx+off,4)
        self.addWidget(self.table[(idx,"rgb")],idx+off,5)
        self.addWidget(self.table[(idx,"hsv")],idx+off,6)

        self.table[(idx,"new")].clicked.connect(lambda: self.button_color1(idx))
        self.table[(idx,"old")].clicked.connect(lambda: self.button_color2(idx))
        self.table[(idx,"act")].clicked.connect(self.selUpdate.emit)
        self.table[(idx,"sel")].clicked.connect(self.useUpdate.emit)
        print("ADDATT",i)


    def set_old_col(self,idx,col):
        color_button(self.table[(idx,"old")],col)
        self.table[(idx,"rgb")].setText(str(col.getRgb()[:3]))
        self.table[(idx,"hsv")].setText(str(col.getHsv()[:3]))

    def select_color(self,idx,col=None,auto=False):
        if not col:
            forbidden = {self.table[i,"col"].getRgb()[:3] for i in range(self.newrow)}
            col = get_color(auto=auto,forbidden=forbidden)
            if col is None:
                return
        self.table[(idx,"col")] = col
        color_button(self.table[idx,"new"],col)
        self.colUpdate.emit(idx)

    def button_color1(self,idx):
        self.select_color(idx)

    def button_color2(self,idx):
        self.random_color(idx)

    def random_color(self,idx,col=None):
        self.select_color(idx,auto=True)


    def show_all(self):
        for idx in range(self.newrow):
            if self.table[(idx,"idx")] < 99:
                self.table[(idx,"act")].setChecked(True)
        self.selUpdate.emit()

    def show_selected(self):
        for idx in range(self.newrow):
            self.table[(idx,"act")].setChecked(self.table[(idx,"sel")].isChecked())
        self.selUpdate.emit()

    def show_none(self):
        for idx in range(self.newrow):
            self.table[(idx,"act")].setChecked(False)
        self.selUpdate.emit()

    def selected(self):
        try:
            return self.bg.checkedId()
        except:
            return None

    def select(self,att):
        for idx in range(self.newrow):
            if self.table[(idx,"idx")] == att:
                self.table[(idx,"sel")].setChecked(True)

    def next_att(self):
        for i in range(self.newrow-1):
            if self.table[i,"sel"].isChecked():
                self.table[i+1,"sel"].setChecked(True)
                break
        else:
            if self.table:
                self.table[0,"sel"].setChecked(True)

class AttEditW(QGridLayout):
    def __init__(self):
        super(AttEditW,self).__init__()

        self.create_widgets()
        self.set_widgets()
        self.layout_widgets()
        self.create_connections()

    def toggle_visibility(self):
        vis = not self.title.isVisible()
        self.title.setVisible(vis)
        #self.visclr.setVisible(vis)
        #self.visrst.setVisible(vis)
        self.undo.setVisible(vis)
        self.redo.setVisible(vis)
        self.gauss.setVisible(vis)
        self.wa_gauss.setVisible(vis)
        self.unfilter.setVisible(vis)
        self.simp.setVisible(vis)
        self.cla1.setVisible(vis)
        self.clu1.setVisible(vis)
        self.opa1.setVisible(vis)
        self.opu1.setVisible(vis)

        self.modA.setVisible(vis)
        self.modcbA.setVisible(vis)
        self.modU.setVisible(vis)
        self.modcbU.setVisible(vis)
        self.modR.setVisible(vis)
        self.dist.setVisible(vis)
        self.shape.setVisible(vis)
        self.sigma.setVisible(vis)
        self.close.setVisible(vis)

    def create_widgets(self):
        self.title = QLabel("* Edit Attributes *")

        #self.visclr = QPushButton("del vis")
        #self.visrst = QPushButton("keep vis")
        #self.vislab = QPushButton("label vis")
        #self.clrlab = QPushButton("label clear")
        self.shwgomi = QPushButton("show gomi")
        self.clrgomi = QPushButton("clear gomi")
        self.fatgomi = QPushButton("fat gomi")

        self.undo = QPushButton("undo")
        self.redo = QPushButton("redo")
        self.simp = QPushButton("simplify")

        self.gauss = QPushButton("gauss")
        self.wa_gauss = QPushButton("WA gauss")
        self.unfilter = QPushButton("undo filter")

        self.cla1 = QPushButton("close all")
        self.clu1 = QPushButton("close use")

        self.opa1 = QPushButton("open all")
        self.opu1 = QPushButton("open use")

        self.shape = QPushButton("disk")
        self.modA = QPushButton("mod all")
        self.modcbA = QPushButton("modcb all")
        self.modU = QPushButton("mod use")
        self.modcbU = QPushButton("modcb use")
        self.modR = QSpinBox()
        self.dist = QSpinBox()
        self.sigma = QSpinBox()
        self.close = QSpinBox()



    def set_widgets(self):
        color_label(self.title,QColor("black"),QColor("white"))
        color_button(self.undo,QColor(255,0,0))
        color_button(self.redo,QColor(255,0,0))
        color_button(self.simp,QColor(255,0,0))

        color_button(self.cla1,QColor(0,255,0))
        color_button(self.clu1,QColor(0,255,0))

        color_button(self.opa1,QColor(0,255,0))
        color_button(self.opu1,QColor(0,255,0))

        #color_button(self.shwgomi,QColor(255,255,0))
        #color_button(self.fatgomi,QColor(255,255,0))
        #color_button(self.clrgomi,QColor(255,255,0))

        #color_button(self.visrst,QColor(0,255,0))

        color_button(self.gauss,QColor(0,255,0))
        color_button(self.wa_gauss,QColor(0,0,255))
        color_button(self.unfilter,QColor(255,0,0))

        self.fatgomi.setCheckable(True)
        self.shape.setCheckable(True)

        color_button(self.modA,QColor(0,255,0))
        color_button(self.modU,QColor(0,255,0))
        color_button(self.modcbA,QColor(0,255,0))
        color_button(self.modcbU,QColor(0,255,0))
        self.dist.setMinimum(1)
        self.dist.setValue(2)
        self.dist.setMaximum(15)

        self.sigma.setMinimum(1)
        self.sigma.setMaximum(10000)

        self.close.setMinimum(1)
        self.close.setMaximum(100)
        self.modR.setMinimum(1)
        self.modR.setMaximum(100)

        self.sigma.setValue(5)
        self.modR.setValue(3)
        self.close.setValue(3)

    def layout_widgets(self):
        self.addWidget(self.title,0,0,1,8)
        self.addWidget(self.undo,1,0)
        self.addWidget(self.redo,1,1)
        self.addWidget(self.simp,1,2)
        #self.addWidget(self.visclr,1,5)
        #self.addWidget(self.visrst,1,6)

        self.addWidget(self.gauss,2,0)
        self.addWidget(self.wa_gauss,2,1)
        self.addWidget(self.unfilter,2,2)
        self.addWidget(self.sigma,2,6)


        self.addWidget(self.cla1,3,0)
        self.addWidget(self.clu1,3,1)

        self.addWidget(self.opa1,3,2)
        self.addWidget(self.opu1,3,3)
        self.addWidget(self.close,3,6)




        self.addWidget(self.modA,4,0)
        self.addWidget(self.modU,4,1)
        self.addWidget(self.modcbA,4,2)
        self.addWidget(self.modcbU,4,3)
        self.addWidget(self.shape,4,4)
        self.addWidget(self.dist,4,6)
        self.addWidget(self.modR,4,7)



    def shape_update(self):
        txts = "disk,square".split(",")
        idx = txts.index(self.shape.text())
        self.shape.setText(txts[(idx+1) % len(txts)])

    def create_connections(self):
        self.shape.clicked.connect(self.shape_update)
