#!/usr/bin/python3
# -*- coding: utf-8 -*-

# TODO
# ---------------
# CHANGE keep labels always uptodate
# CHANGE components from Data to labels,loff
# CHANGE use filters cleverly somewhere near workareas (multiple rgb2loc)

import ogr, gdal, osr
import itertools

import sys
from os.path import basename,abspath,normpath,exists,dirname,join
from os import rename
from time import sleep
from math import ceil,floor,hypot,atan2,pi,sqrt
from random import randint as ri
from pickle import dump as pdump
from pickle import load as pload
from datetime import datetime as dt
from random import choice
from functools import partial
from collections import Counter

from shapely.geometry import Polygon,Point
from shapely.validation import explain_validity

import numpy as np
try:
    import matplotlib.mlab as mlab
    import matplotlib.pyplot as plt
except:
    print("SORRY NO MATPLOTLIB")

from scipy.spatial.distance import euclidean
from scipy.ndimage.morphology import binary_fill_holes
from skimage.measure import label
from skimage.morphology import binary_erosion as erosion
from skimage.morphology import binary_dilation as dilation
from skimage.morphology import binary_opening as opening
from skimage.morphology import binary_closing as closing
from skimage.morphology import remove_small_holes,remove_small_objects
from skimage.filters import gaussian
from skimage.draw import polygon

from skimage.filters.rank import modal
from skimage.morphology import disk


from skimage.segmentation import find_boundaries
import shapefile

from PIL import Image

from PyQt5.QtWidgets import QMainWindow, QAction, QApplication,QMessageBox,\
    QLabel,QTableView,QGridLayout,QWidget,QSpinBox,QLineEdit,QComboBox,\
    QFileDialog,QPushButton,QFormLayout,QListWidget,QColorDialog,\
    QListWidgetItem,qApp,QInputDialog,QRadioButton,QCheckBox,QButtonGroup,\
    QToolBar,QActionGroup
from PyQt5.QtGui import QIcon,QKeySequence,QImage,QPixmap,QBitmap,QColor,\
    QPen,QBrush,QPolygonF
from PyQt5.QtCore import pyqtSignal,Qt,QPointF,QPoint,QRectF,QRect,QObject,pyqtSlot
from data import Data,CData,make_box,get_bnd
from viewer import ImageViewer
from gtif import geotrans,rgeotrans


from iset import PSet,ISet,IBox,Box,Boxes
from wa import WorkArea as WA
from log import Log,sbar,logret,logarg
from att import AttData as AD
from att import BITPAD,BITSHIFT,BITOFF
from cnt import Contour,outline,bnd2outer
from ig import ItemGroup

from edit import EditW
from para import ParameterW,SelectionW,PolyW
from info import InfoW
from button import ButtonW
from collision import CollisionW
from contour import ContourW
from workarea import WorkAreaW
from attribute import AttGenW,AttEditW

from color import color_label,color_button,Color,\
    closer_color,get_color_parameters

from rdp import rdp


PICKLE_VERSION = 1

# Data
# color clusters
# pixel sets, component, filled component, dist convex_hull

last = None

def ndil(bmap,n,c=None):
    r1 = 2*[0] + 5*[1] + 11*[0] + 5*[1] + 2*[0]
    r2 = 2*[0] + 21 * [1] + 2*[0]
    r3 = 2*[0] + 5*[1] + 11*[0] + 5*[0] + 2*[0]    
    r4 = 2*[0] + 5*[1] + 5*[0] + 11*[1] + 2*[0]    
    if c == "H":
        selem = np.array(10*[r1] + 5*[r2] + 10*[r1], dtype=np.uint8)
    elif c == "G":
        selem = np.array(4*[r2] + 8*[r3] + 3*[r4] + 8*[r1] + 4*[r2], dtype=np.uint8)
    elif c == "B":
        selem = np.array(2*[r2] + 8*[r1] + 5*[r2] + 8*[r1] + 2*[r2], dtype=np.uint8)
    else:
        selem=disk(n)

    selem=disk(n)
    return dilation(bmap,selem)

    
def tset(xylist):
    #print("XY",xylist)
    xs = [xy[0] for xy in xylist]
    ys = [xy[1] for xy in xylist]
    return polygon(xs,ys)

def backup(p):
    if exists(p):
        a = p[:-4]
        b = p[-3:]
        assert p[-4] == "."
        n = 1
        while True:
            sn = str(n).zfill((len(str(n))//3)*3+3)
            tmp = a + "_" + sn + "." + b
            if not exists(tmp):
                rename(p,tmp)
                break
            n += 1

def ask(title,msg):
    cont = QMessageBox(QMessageBox.Information,
                       title,
                       msg,
                       QMessageBox.Yes|QMessageBox.No).exec()
    return cont == QMessageBox.Yes

def dmsg(title,msg):
    QMessageBox(QMessageBox.Information,
                       title,
                       msg,
                       QMessageBox.Ok).exec()


MODES = {
    "view" :(QColor(85,85,255),"move/zoom map"),
    "paint":(QColor(255,255,85),"paint boxes, components"),
    "get"  :(QColor(255,85,255),"get attribute pixel sets by color"),
    "info" :(QColor(255,128,128),"display information"),
    "work" :(QColor(255,255,255),"modify working area"),
    #"tlab"  :(QColor(255,255,0),"label areas, components"),
    #"bnd"  :(QColor(255,0,255),"fix boundaries between regions"),
    "mor"  :(QColor(255,0,255),"morphology"),
    #"edit" :(QColor(255,85,85),"edit pixel deltas"),
    #"cnt"  :(QColor(85,255,85),"add/del contours"),
    "fix"  :(QColor(255,0,255),"fix"),
}

class HMap(QMainWindow):
    newImage = pyqtSignal(str,int,int)

    def __init__(self,path=None,load=False,work=False,
                 size=0,showall=False,mode=""):
        super(HMap,self).__init__()
        self.history = []
        self.setWindowTitle('HazardMap')
        self.toolbar = self.addToolBar("Modes")

        # IMAGE DATA
        self.qimage = None
        self.imgdata = [] # raw image data [(r1,g1,b1),(r2,...
        self.width = -1
        self.height = -1

        # SET UP
        self.create_actions()
        self.create_widgets()
        self.layout_widgets()
        self.create_connections()
        self.pplists = []
        self.pplist = []
        self.ppidx = 0
        self.ppig = ItemGroup(self.viewer,fillcolor=QColor(255,0,0,128))

        # LOAD FILE
        if path is None:
            self.file_open(nocancel=True)
        else:
            self.file_open(path = path)

        if load:
            pck = abspath(normpath(path[:-3] + "pck"))
            print("pck",pck)

            try:
                self.file_load(path=pck)
            except:
                dmsg("WARNING","No File "+pck)
                raise
        if work:
            self.wa.full(self.width,self.height,self.col.bands)
        if size == 1:
            self.att0.gen1()
        if size == 5:
            self.att0.gen5()
        if size == 6:
            self.att0.gen6()
        if size == 7:
            self.att0.gen7()
        elif size == 8:
            self.att0.gen8()
        if showall:
            self.att0.show_all()
        if mode:
            self.set_mode(mode)

        self.create_gitems()

        self.buttons.edit.setChecked(True)
        self.buttons.warn.setChecked(True)
        self.buttons.work.setChecked(True)
        self.buttons.slct.setChecked(True)
        self.work.toggle_visibility(hide=True)
        self.edit.toggle_visibility(hide=True)
        self.selpara.toggle_visibility(hide=True)
        self.warnings.toggle_visibility(hide=True)

    def keyPressEvent(self,event):
        QMainWindow.keyPressEvent(self, event)
        if event.key() == Qt.Key_P:
            self.exec_key("p")
        elif event.key() == Qt.Key_Escape:
            self.exec_key("esc")
        elif event.key() == Qt.Key_1:
            self.exec_key("1")
        elif event.key() == Qt.Key_2:
            self.exec_key("2")
        elif event.key() == Qt.Key_3:
            self.exec_key("3")
        elif event.key() == Qt.Key_4:
            self.exec_key("4")
        elif event.key() == Qt.Key_5:
            self.exec_key("5")
        elif event.key() == Qt.Key_6:
            self.exec_key("6")
        elif event.key() == Qt.Key_7:
            self.exec_key("7")
        elif event.key() == Qt.Key_N:
            self.exec_key("n")
        elif event.key() == Qt.Key_M:
            self.exec_key("m")
        elif event.key() == Qt.Key_A:
            self.exec_key("a")
        elif event.key() == Qt.Key_O:
            self.exec_key("o")
        elif event.key() == Qt.Key_E:
            self.exec_key("e")
        elif event.key() == Qt.Key_F:
            self.exec_key("f")
        elif event.key() == Qt.Key_J:
            self.exec_key("j")
        elif event.key() == Qt.Key_K:
            self.exec_key("k")
        elif event.key() == Qt.Key_U:
            self.exec_key("u")
        elif event.key() == Qt.Key_X:
            self.exec_key("x")
        elif event.key() == Qt.Key_Y:
            self.exec_key("y")            
        elif event.key() == Qt.Key_Z:
            self.exec_key("z")
        elif event.key() == Qt.Key_C:
            self.exec_key("c")
        elif event.key() == Qt.Key_S:
            self.exec_key("s")
        elif event.key() == Qt.Key_B:
            self.exec_key("b")
        elif event.key() == Qt.Key_G:
            self.exec_key("g")
        elif event.key() == Qt.Key_H:
            self.exec_key("h")
        elif event.key() == Qt.Key_R:
            self.exec_key("r")


    def __str__(self):
        return "HMAP"

    def selected_loc(self,mode):
        HMap.__dict__["loc_"+mode](self)

    def selected_box(self,mode):
        HMap.__dict__["box_"+mode](self)

    def exec_key(self,key):
        print("KEY",key)
        if key == "n":
            self.pp_go(1)
        elif key == "e":
            self.polys.pp_update()
        elif key == "esc":
            if self.pplist:
                self.pplist.pop()
            self.pp_update()
        elif key == "v":
            self.pp_vis()
        elif key == "y":
            self.gomi_show()
            self.hole_show()
            self.bnds_show_all()
        elif key == "p":
            self.pp_go(-1)
        elif key == "m":
            #elf.parameters.ocde_update()
            self.magic()
        elif key == "o":
            #self.parameters.protect_update()
            self.att0.show_selected()
        elif key == "a":
            #self.parameters.add_update()
            self.att0.show_all()
        elif key == "u":
            self.pp_use()
        elif key == "f":
            self.cont.fatB.setChecked(not self.bnds.fat.isChecked())
            self.bnds_fat()
        elif key == "x":
            self.pp_use(1)
        elif key == "z":
            self.pp_use(-1)
        elif key == "c":
            self.pp_clear()
        elif key == "b":
            self.bnds_fix()
        elif key == "k":
            self.kill()
        elif key == "g":
            self.cont_fixGA()
        elif key == "h":
            self.cont_fixHU()
        elif key == "r":
            self.parameters.add_update()
        elif key == "s":
            self.polys.ppshow.setChecked(not self.polys.ppshow.isChecked())
        elif key in "1234567":
            i = int(key)
            print("IAR",i,self.att0.newrow)
            if i <= self.att0.newrow:
                print("ATT",self.att0.table[(i-1,"idx")])
                self.att0.select(self.att0.table[(i-1,"idx")])

    def get_codes(self,use_99=True,descending=True):
        keys = [x for x in self.att.keys() if use_99 or x != 99]
        if descending:
            return sorted(keys,key=lambda x:-x)
        else:
            return sorted(keys)

    def level_mask(self,box,use_99=True):
        "True = outside of all levels"
        pl = self.get_prelabel(box,use_99)
        return ~(pl.astype(np.bool))

    def get_prelabel(self,box,use_99=True,descending=False):
        prelabel = np.zeros(box.shape,dtype=np.uint8)
        for code in self.get_codes(use_99,descending):
            att = self.att[code]
            x = att.pix.curr.extract_ibox(box).iset.astype(np.uint8)
            prelabel = np.where(x,code,prelabel)
        return prelabel


    def hlog(self,x):
        self.history.append(x)
        with open("hmap.clg","a+") as f:
            f.write(str(dt.now())+": "+str(x)+"\n")

    def create_widgets(self):
        self.statusBar().showMessage("READY")

        # Image
        self.viewer = ImageViewer()

        # RHS
        self.warnings = EditW("*** WARNINGS ***",3)
        self.edit = EditW("* recent history *",6)
        self.glog = Log(sbar=self.statusBar().showMessage,
                      mbox=QMessageBox,
                      edit=self.edit.add,
                      warn=self.warnings.add,
                      dump=self.hlog)
        self.log = self.glog.log

        self.wa = WA(self.viewer,self.glog)
        self.att = {}

        self.info = InfoW(self.viewer)
        self.buttons = ButtonW()
        self.att0 = AttGenW()
        self.att1 = AttEditW()
        self.work = WorkAreaW()
        self.coll = CollisionW()
        self.cont = ContourW()
        self.selpara = SelectionW(self)
        self.parameters = ParameterW(self)
        self.polys = PolyW(self)

    def create_gitems(self):
        w,h = self.width,self.height
        w += (BITPAD-BITSHIFT)-((w+(BITPAD-BITSHIFT))%BITPAD) + BITOFF

        self.wh = (w,h)
        self.cov_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.col_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.cnt_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.bnd_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.col2_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.cnt2_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.bnd2_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.gomi_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.gomi2_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.hole_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.hole2_item = self.viewer.scene.addPixmap(QBitmap(w,h))

        self.col_item.setZValue(-1)
        self.cnt_item.setZValue(-1)
        self.bnd_item.setZValue(-1)
        self.cov_item.setZValue(-1)
        self.cnt2_item.setZValue(-1)
        self.bnd2_item.setZValue(-1)
        self.col2_item.setZValue(-1)
        self.gomi_item.setZValue(-1)
        self.gomi2_item.setZValue(-1)
        self.hole_item.setZValue(-1)
        self.hole2_item.setZValue(-1)

    def layout_widgets(self):
        grid = QGridLayout()
        grid.addWidget(self.viewer, 0, 0, 20, 1)

        grid.addLayout(self.info, 0, 1)
        grid.addLayout(self.buttons, 1, 1)
        grid.addLayout(self.work, 2, 1)
        grid.addLayout(self.att0, 3, 1)
        grid.addLayout(self.selpara, 4, 1)
        grid.addLayout(self.att1, 5, 1)

        grid.addLayout(self.coll, 6, 1)
        grid.addLayout(self.cont, 7, 1)


        grid.addLayout(self.parameters, 9, 1)
        grid.addLayout(self.polys, 10, 1)
        grid.addLayout(self.warnings, 11, 1)
        grid.addLayout(self.edit, 12, 1)

        grid.setColumnStretch(0,3)
        widget = QWidget(self)
        widget.setLayout(grid)
        self.setCentralWidget(widget)

    def create_connections(self):
        self.buttons.edit.clicked.connect(self.edit.toggle_visibility)
        self.buttons.warn.clicked.connect(self.warnings.toggle_visibility)
        self.buttons.para.clicked.connect(self.parameters.toggle_visibility)
        self.buttons.ccb.clicked.connect(self.ccb_toggle_visibility)
        self.buttons.poly.clicked.connect(self.polys.toggle_visibility)
        self.buttons.slct.clicked.connect(self.selpara.toggle_visibility)
        self.buttons.work.clicked.connect(self.work.toggle_visibility)
        self.buttons.attr.clicked.connect(self.att1.toggle_visibility)

        # VIEWER
        self.viewer.selLoc.connect(self.selected_loc)
        self.viewer.selBox.connect(self.selected_box)
        self.viewer.genKeyX.connect(self.exec_key)

        # WORK AREA
        self.work.clr.clicked.connect(self.wa.clear)
        self.work.full.clicked.connect(lambda : self.wa.full(self.width,self.height,self.col.bands))
        self.work.gen.clicked.connect(lambda: self.wa.generate(self.col.bands))
        self.work.addV.clicked.connect(lambda : self.wa.add(self.get_visible()))
        self.work.clrV.clicked.connect(self.wa.clr_visible)
        self.work.show.clicked.connect(lambda: self.wa.set_visibility(self.work.show.isChecked()))
        self.wa.generated.connect(self.wa.hide)
        self.wa.generated.connect(lambda : self.work.show.setChecked(False))
        self.wa.generated.connect(lambda : self.set_mode("view"))
        self.wa.generated.connect(self.wa2view)

        # ATT0 GEN
        self.att0.tableUpdate.connect(self.att0_reset)
        self.att0.useUpdate.connect(self.att0_use_update)
        self.att0.selUpdate.connect(self.att0_sel_update)
        self.att0.colUpdate.connect(self.att0_col_update)

        # ATT1 EDIT
        #self.att1.clrlab.clicked.connect(self.att1_lab_clear)
        #self.att1.vislab.clicked.connect(self.att1_lab_visible)
        #self.att1.visclr.clicked.connect(self.att1_clr_visible)
        #self.att1.shwgomi.clicked.connect(self.gomi_show)
        #self.att1.clrgomi.clicked.connect(self.gomi_clear)
        #self.att1.fatgomi.clicked.connect(self.gomi_fat)
        self.cont.shwG.clicked.connect(self.gomi_show)
        self.cont.hidG.clicked.connect(self.gomi_hide)
        self.cont.fatG.clicked.connect(self.gomi_fat)

        self.cont.shwH.clicked.connect(self.hole_show)
        self.cont.hidH.clicked.connect(self.hole_hide)
        self.cont.fatH.clicked.connect(self.hole_fat)

        self.cont.labG.clicked.connect(self.gomi_toggle)
        self.cont.labH.clicked.connect(self.hole_toggle)
        self.cont.labB.clicked.connect(self.bnds_toggle)


        #self.att1.visrst.clicked.connect(self.att1_rst_visible)
        self.att1.undo.clicked.connect(self.att1_undo)
        self.att1.redo.clicked.connect(self.att1_redo)
        self.att1.simp.clicked.connect(self.att1_simplify)

        self.att1.gauss.clicked.connect(self.gauss)
        self.att1.wa_gauss.clicked.connect(self.wa_gauss)
        self.att1.unfilter.clicked.connect(self.unfilter)

        self.att1.cla1.clicked.connect(lambda : self.att1_closecomp(True))
        self.att1.clu1.clicked.connect(lambda : self.att1_closecomp(False))

        self.att1.opa1.clicked.connect(lambda : self.att1_opencomp(True))
        self.att1.opu1.clicked.connect(lambda : self.att1_opencomp(False))

        # COLL
        self.coll.shwA.clicked.connect(self.coll_show_all)
        self.coll.shwU.clicked.connect(self.coll_show_use)
        self.coll.shwN.clicked.connect(self.coll_show_none)

        self.coll.fat.clicked.connect(self.coll_fat)
        self.coll.fix.clicked.connect(self.coll_fix)

        self.coll.fixO.clicked.connect(self.coll_fixO)        

        # CONT
        self.cont.shwA.clicked.connect(self.cont_show_all)
        self.cont.shwU.clicked.connect(self.cont_show_use)
        self.cont.shwN.clicked.connect(self.cont_show_none)

        self.cont.fat.clicked.connect(self.cont_fat)
        self.cont.fixGA.clicked.connect(self.cont_fixGA)
        self.cont.fixHA.clicked.connect(self.cont_fixHA)
        self.cont.fixGU.clicked.connect(self.cont_fixGU)
        self.cont.fixHU.clicked.connect(self.cont_fixHU)

        self.cont.fixB.clicked.connect(self.bnds_fix)
        self.att1.modA.clicked.connect(lambda : self.mod_fix(cb=False,who="all"))
        self.att1.modcbA.clicked.connect(lambda : self.mod_fix(cb=True,who="all"))
        self.att1.modU.clicked.connect(lambda : self.mod_fix(cb=False,who="use"))
        self.att1.modcbU.clicked.connect(lambda : self.mod_fix(cb=True,who="use"))
        self.cont.fatB.clicked.connect(self.bnds_fat)
        self.cont.shwB.clicked.connect(self.bnds_show_all)
        self.cont.hidB.clicked.connect(self.bnds_show_none)

        #self.att.changed.connect(self.update_image)
        #self.att.selAtt.connect(self.change_att)
        #self.att.undoPix.connect(self.record_undo)
        #self.att.statusMsg.connect(self.update_status_bar)
        #self.att.setH.clicked.connect(self.set_home)
        #self.att.getH.clicked.connect(self.get_home)
#        self.att.colC.clicked.connect(self.dump_collisions)
#        self.att.colF.clicked.connect(self.fix_collisions)


#        self.att.collUpdate.connect(self.info.update_collisions)
#        self.att.cntUpdate.connect(self.info.update_contours)

        #self.att.shwB.clicked.connect(self.update_image)
        #self.att.shwC.clicked.connect(self.update_image)
        #self.att.cntC.clicked.connect(self.update_image)
        #self.att.shwW.clicked.connect(self.wa)

        self.selpara.paraChanged.connect(self.change_selpara)
        self.selpara.selScheme.connect(self.change_scheme)

        self.newImage.connect(self.info.update_image)

        # CONTOURS
        #self.cont.gen.clicked.connect(self.att.generate_contours)
        #self.cont.clr.clicked.connect(self.att.remove_contours)
        #self.cont.fix.clicked.connect(self.att.fix_contours)
        #self.cont.merge.clicked.connect(self.att.merge_contours)
        #self.cont.cover.clicked.connect(self.att.update_covers)

        self.polys.ppuse.clicked.connect(lambda : self.pp_use(0))
        self.polys.ppprev.clicked.connect(lambda : self.pp_go(-1))
        self.polys.ppnext.clicked.connect(lambda : self.pp_go(1))
        self.polys.ppclear.clicked.connect(self.pp_clear)
        self.polys.ppClear.connect(self.pp_clear)
        self.polys.ppshow.clicked.connect(self.pp_update)
        self.polys.ppvis.clicked.connect(self.pp_vis)

    @sbar
    def gomi_show(self,dummy=None):
        codes = self.get_codes(use_99=False)

        w,h = self.wh
        box = Box(0,0,w,h)
        bmap = np.zeros(self.wh,dtype=np.bool)
        maxG = self.cont.maxG.value()
        for code in codes:
            bmap |= self.get_gomi(box,maxG,code)
        self.cont.labG.setText(str(sum(sum(bmap))) + " pix")
        bmap2 = ndil(bmap,20,"G")
        pixmap = IBox(box,iset=bmap).bitmap(QColor("yellow"))
        pixmap2 = IBox(box,iset=bmap2).bitmap(QColor("black"))
        self.gomi_item.setPixmap(pixmap)
        self.gomi2_item.setPixmap(pixmap2)
        self.gomi_item.setZValue(6)
        self.gomi_fat()

    def gomi_hide(self):
        self.gomi_item.setZValue(-1)
        self.gomi2_item.setZValue(-1)

    def gomi_toggle(self):
        self.gomi_item.setZValue(6)
        self.gomi_fat()

    def hole_toggle(self):
        self.hole_item.setZValue(6)
        self.hole_fat()

    def bnds_toggle(self):
        self.bnd_item.setZValue(6)
        self.bnds_fat()

    def gomi_fat(self):
        if self.cont.fatG.isChecked():
            self.gomi2_item.setZValue(5)
        else:
            self.gomi2_item.setZValue(-1)

    @sbar
    def hole_show(self,dummy=None):
        codes = self.get_codes(use_99=False)

        w,h = self.wh
        box = Box(0,0,w,h)
        bmap = np.zeros(self.wh,dtype=np.bool)
        maxH = self.cont.maxH.value()
        for code in codes:
            bmap |= self.get_holes(box,maxH,code)
        self.cont.labH.setText(str(sum(sum(bmap))) + " pix")
        bmap2 = ndil(bmap,20,"H")
        pixmap = IBox(box,iset=bmap).bitmap(QColor("red"))
        pixmap2 = IBox(box,iset=bmap2).bitmap(QColor("black"))
        self.hole_item.setPixmap(pixmap)
        self.hole2_item.setPixmap(pixmap2)
        self.hole_item.setZValue(6)
        self.hole_fat()

    def hole_hide(self):
        self.hole_item.setZValue(-1)
        self.hole2_item.setZValue(-1)

    def hole_fat(self):
        if self.cont.fatH.isChecked():
            self.hole2_item.setZValue(5)
        else:
            self.hole2_item.setZValue(-1)


    @sbar
    @logarg
    def mod_fix(self,cb=False,who="all"):
        V = self.get_visible()
        d = self.cont.maxB.value()
        box = V.grow(d) # avoid spurious growth at edges
        rep = self.att1.modR.value()
        shape = self.att1.shape.text()
        sel = self.att0.selected()
        PARA = self.parameters.get_all()
        po = PARA["protect_overwrite"]
        prelabel = self.get_prelabel(box,use_99=True)
        checkers = np.zeros(box.shape,dtype=np.uint8)

        if cb:
            for i in range(box.shape[0]):
                if i%2:
                    checkers[i,:] += 1
            for j in range(box.shape[1]):
                if j%2:
                    checkers[:,j] += 1
            checkers = np.where(checkers == 1, 100, 0).astype(np.uint8)

        if po == "overwrite" and who == "use":
            print("OU")
            pl = np.where(prelabel == sel, sel, 0)
        else:
            pl = prelabel

        pl = np.where(pl != 0, pl, checkers)

        label = np.array(pl)
        if shape == "disk":
            dd = disk(d) | 1
        else:
            dd = disk(d)
        for i in range(rep):
            self.log("sbar","modal filter "+str(i))
            label = modal(label,dd)

        for code in self.get_codes(use_99=False,descending=True):
            self.log("sbar","modal code " + str(code))            
            if who == "use" and code != sel:
                continue
            att = self.att[code]
            a = np.where(label == code,1,0).astype(np.bool) # growth
            if po == "overwrite" and who == "use":
                print("OU2")
                b = np.where(pl == code,0,1).astype(np.bool) # prelabel != code
            else:
                b = ~(prelabel.astype(np.bool)) # prelabel != 0
            x = np.where(a & b,1,0).astype(np.bool)
            xv = x[d:-d,d:-d]
            if xv.any():
                self.att[code].add_pixs(ISet([IBox(V,xv)]))

    @sbar
    def bnds_show_all(self,summy=None):
        w,h = self.wh
        B = Box(0,0,w,h)

        x = np.zeros(self.wh,dtype=np.bool)
        for i in self.att:
            if i == 99: continue
            x |= self.att[i].pix.curr.extract_ibox(B).iset.astype(np.bool)
        bmap = remove_small_objects(~x,min_size=self.cont.maxBB.value()).astype(np.bool)
        y = ~(bmap | x)
        self.cont.labB.setText(str(sum(sum(y))) + " pix")
        #y = find_boundaries(x,mode="inner",connectivity=2)
        z = ndil(y,20,"B")
        pixmap = IBox(B,iset=y).bitmap(QColor("cyan"))
        pixmap2 = IBox(B,iset=z).bitmap(QColor("black"))
        self.bnd_item.setPixmap(pixmap)
        self.bnd2_item.setPixmap(pixmap2)
        self.bnd_item.setZValue(3)
        self.bnds_fat()

    def bnds_show_none(self):
        self.bnd_item.setZValue(-1)
        self.bnd2_item.setZValue(-1)

    def bnds_fat(self):
        if self.cont.fatB.isChecked():
            self.bnd2_item.setZValue(2)
        else:
            self.bnd2_item.setZValue(-1)




    def bnds_fix(self):
        box = self.get_visible()
        self.bnds_fix_box(box,w=self.cont.maxB.value())

    @sbar
    def bnds_fix_box(self,box,w=0,zone=None):
        if w == 0:
            w = self.cont.maxB.value()
        w = max(w,1)
        
        dils = {}
        add = {}

        if 99 in self.att:
            rm = self.att[99].pix.curr.extract_ibox(box).iset.astype(np.bool)
        else:
            rm = np.zeros(box.shape,dtype=np.bool)

        pts = np.zeros(box.shape,dtype=np.int32)
        codes = sorted([y for y in self.att.keys()],key=lambda x:-x)

        for code in codes:
            att = self.att[code]
            dils[code] = {0:att.pix.curr.extract_ibox(box).iset.astype(bool)}
            rm |= dils[code][0]
            for i in range(w):
                dils[code][i+1] = dilation(dils[code][i])

        if zone is None:
            zone = np.zeros(box.shape,dtype=np.bool)
            for c1 in codes:
                a1 = self.att[c1]
                for c2 in codes:
                    if c1 < c2:
                        a2 = self.att[c2]
                        x = a1.pix.curr.extract_ibox(box).iset.astype(bool)|a2.pix.curr.extract_ibox(box).iset.astype(bool)
                        for i in range(w):
                            x = dilation(x)
                        for i in range(w):
                            x = erosion(x)
                        zone |= x

        for code in codes:
            pts += dils[code][w-1].astype(np.int32)
            add[code] = np.zeros(box.shape,dtype=np.bool)
        pts = np.where(zone,1,0).astype(np.bool) & ~rm

        for i in range(w):
            for code in codes:
                x = dils[code][i] & pts
                add[code] |= x
                pts &= ~x
        for code in codes:
            if add[code].any():
                self.att[code].add_pixs(ISet([IBox(box,add[code])]))

    def ccb_toggle_visibility(self):
        self.cont.toggle_visibility()
        self.coll.toggle_visibility()

    def pp_vis(self):
        l,r,t,b=self.viewer.getVisible()
        self.pplist = [(l,b),(l,t),(r,t),(r,b)]
        self.pp_update()
        self.viewer.scaleCheck(0.5)

    def pp_go(self,off):
        if self.pplists:
            self.ppidx += off
            self.ppidx = min(self.ppidx,len(self.pplists) - 1)
            self.ppidx = max(self.ppidx,0)
            print(self.ppidx,len(self.pplists))
            self.pplist = self.pplists[self.ppidx][:]
            self.pp_update()

    def pp_use(self,flag=0):
        if self.viewer.mode != "paint":
            dmsg("WARNING","wrong mode")
            return
        n = len(self.pplist)
        if n <= 1:
            dmsg("WARNING","not enough points")
            return
        else:
            if n == 2:
                a,b = self.pplist
                self.pplist = [a,(a[0],b[1]),b,(b[0],a[1])]

            self.poly_paint(self.pplist,flag)
            self.pplists.append(self.pplist)
            self.ppidx = len(self.pplists)-1
            self.pplist = []
            self.pp_update()

    def pp_clear(self):
        self.pplist = []
        self.pp_update()

    def pp_update(self):
        ch = self.polys.ppshow.isChecked()
        self.ppig.clear()
        if ch:
            if len(self.pplist) >= 3:
                self.ppig.add_polygon(self.pplist)
                self.ppig.vis_set()
            elif len(self.pplist) == 2:
                self.ppig.add_line(self.pplist)
                self.ppig.add_bbox(self.pplist)
                self.ppig.vis_set()
            elif len(self.pplist) == 1:
                self.ppig.add_point(self.pplist)
                self.ppig.vis_set()

    def wa2view(self):
        self.viewer.wabbox = self.wa.bbox

    def col_get(self,i,j,scheme=None):
        scheme = self.selpara.get_color_scheme() if scheme is None else scheme
        try:
            return tuple([self.col.bands[x][i,j] for x in scheme])
        except:
            return tuple()

    def col_select_region(self):
        x = ISet
        pass

    def att0_reset(self,n):
        for ad in self.att.values():
            ad.rm_item()

        print("ATT_RESET",n)
        if n == 0:
            self.att = {}
        elif n == 1:
            self.att = {i:AD(self.viewer,self.width,self.height,i,self.att0._color[i])
                   for i in range(1,2)}
        elif n == 5:
            self.att = {i:AD(self.viewer,self.width,self.height,i,self.att0._color[i])
                   for i in range(11,16)}
        elif n == 6:
            self.att = {i:AD(self.viewer,self.width,self.height,i,self.att0._color[i])
                   for i in range(31,37)}
        elif n == 7:
            self.att = {i:AD(self.viewer,self.width,self.height,i,self.att0._color[i])
                   for i in range(21,28)}
        elif n == 8:
            self.att = {i:AD(self.viewer,self.width,self.height,i,self.att0._color[i])
                   for i in range(41,49)}
        else:
            raise ValueError("att_reset " + str(n))
        if self.att:
            self.att[99] = AD(self.viewer,self.width,self.height,99,self.att0._color[99])
            self.att0_use_update()


    def att0_use_update(self,idxs=None):
        att = self.att0.selected()
        if att == -1:
            if not self.att0.table:
                return
            self.att0.table[(0,"sel")].setChecked(True)

        ad = self.att[att]
        pix = ad.pix
        txt = "selected: " + str(att) +\
              " idx: " + str(pix.idx) + " of " + str(len(pix.hist))
        if pix.idx >= 1:
            left = pix.idx - 1
        else:
            left = 0
        right = min(pix.idx+2,len(pix.hist))
        while left and right -left < 3:
            left -= 1

        for i,x in enumerate(pix.hist[left:right]):
            txt += " " + str(i) + ": "+x[0]+str(len(x[1]))
        self.info.sel.setText(txt)

    def check_collisions(self):
        self.colls = {}
        coll = set()
        b = {}
        B = Box(0,0,self.width,self.height)
        codes = sorted(list(self.att.keys()),key=lambda x:-x)
        for i in codes:
            b[i] = self.att[i].pix.curr.extract_ibox(B)
        for i in codes:
            for j in codes:
                if i < j:
                    iset = b[i].iset.astype(np.bool) & b[j].iset.astype(np.bool)
                    n = sum(sum((iset)))
                    if n>0:
                        coll.add((i,j,n))
                        self.colls[(i,j)] = iset
        return coll

    def att0_sel_update(self,idxs=None):
        if not idxs:
            idxs = sorted(self.att.keys())
        print("INDEXES",idxs)
        for i in idxs:
            att = self.att[i]
            if i > 0 and i < 99:
                j = (i%10)-1
            elif i == 0:
                j = 0
            else:
                j = len(self.att.keys()) - 1

            if self.att0.table[(j,"act")].isChecked():
                att.show()
            else:
                att.hide()
            self.att0.table[(j,"pix")].setText(str(len(att.pix)))

        coll = self.check_collisions()
        self.info.coll.setText(str(sorted(coll)))
        self.att0_use_update()

    def att0_col_update(self,idx):
        self.att[self.att0.table[(idx,"idx")]].col_update(self.att0.table[(idx,"col")])

    def att0_set_old_col(self,col):
        print(self,self.att0,self.att0.bg,self.att0.bg.buttons(),self.att0.selected)
        sel = self.att0.selected()
        for i in range(len(self.att)):
            if self.att0.table[i,"pix"].text() == "0" and\
               self.att0.table[i,"idx"] == sel:
                self.att0.set_old_col(i,col)
                break

    def att_add_pixs(self,pixs,update=True):
        i = self.att0.selected()
        if i == -1:
            dmsg("WARNING","nothing selected")
            return
        att = self.att[i]
        pset = att.pix
        for (b,idx) in self.wa.items:
            print(b,end=": ")
            if not pset.add_box(b): print("not",end=" ")
            print("added")
        att.add_pixs(pixs)
        if update:
            self.att0_sel_update([i])

    def att_sub_pixs(self,pixs,i=None,update=True):
        if i is None:
            i = self.att0.selected()
        att = self.att[i]
        pset = att.pix
        for (b,idx) in self.wa.items:
            print(b,end=": ")
            if not pset.add_box(b): print("not",end=" ")
            print("added")
        att.sub_pixs(pixs)
        if update:
            self.att0_sel_update([i])

    @logarg
    def att1_lab_clear(self):
        try:
            self.viewer.scene.removeItem(self.lab_item)
            self.lab_item.destroy()
        except:
            pass

    @logarg
    def att1_lab_visible(self,att=0,clabel=True):
        B = self.get_visible(pad=True)
        self.labels(B,att,clabel)
        return B
        #i = self.att0.selected()
        #att = self.att[i]
        #att.sub_box(B)
        #self.att0_sel_update([i])

    @logarg
    def att1_clr_visible(self,dummy=None):
        B = self.get_visible()
        i = self.att0.selected()
        att = self.att[i]
        att.sub_box(B)
        self.att0_sel_update([i])

    @logarg
    def att1_rst_visible(self,dummy=None):
        B = self.get_visible()
        i = self.att0.selected()
        att = self.att[i]
        att.restrict_box(B)
        self.att0_sel_update([i])

    @logarg
    def att1_undo(self,dummy=None):
        print("ATT1 UNDO")
        i = self.att0.selected()
        self.att[i].undo()
        self.att0_sel_update([i])

    @logarg
    def att1_redo(self,dummy=None):
        print("ATT1 REDO")
        i = self.att0.selected()
        self.att[i].redo()
        self.att0_sel_update([i])

    def att1_simplify(self):
        for pix in self.att.values():
            pix.simplify()

    @sbar
    @logarg
    def att1_closecomp(self,full):

        box = self.att1_lab_visible(clabel=False)
        self.log("sbar","label done")
        PARA = self.parameters.get_all()
        PO = PARA["protect_overwrite"]
        n = self.att1.close.value()
        if PO == "overwrite":
            rm = np.zeros(box.shape,dtype=np.bool)
        else:
            rm = self.lab_att.astype(np.bool)

        atts = [x for x in self.att.keys() if x < 99] if full else [self.att0.selected()]
        atts = list(reversed(sorted(atts)))
        print("ATTS",atts)
        for att in atts:
            cs1 = np.where(self.lab_att == att,1,0)
            #cs2 = set(cs1.reshape(-1))
            #self.log("sbar","close comp: "+str(att)+":"+str(len(cs2)))

            if True:
                c = cs1.astype(np.bool)
                d = np.array(c,dtype=np.bool)
                for i in range(n):
                    d = dilation(d)
                for i in range(n):
                    d = erosion(d)
                diff = d & ~c & ~rm
                if sum(sum(diff)):
                    self.att[att].add_pixs(ISet([IBox(box,diff)]))
            self.att0_sel_update([att])

    @sbar
    @logarg
    def att1_opencomp(self,full):
        box = self.att1_lab_visible(clabel=False)
        self.log("sbar","label done")
        PARA = self.parameters.get_all()
        n = self.att1.close.value()

        atts = [x for x in self.att.keys() if x < 99] if full else [self.att0.selected()]
        print("ATTS",atts)
        for att in atts:
            cs1 = np.where(self.lab_att == att,1,0)
            if True:
                c = cs1.astype(np.bool)
                d = np.array(c,dtype=np.bool)
                for i in range(n):
                    d = erosion(d)
                for i in range(n):
                    d = dilation(d)
                diff = c & ~d
                if sum(sum(diff)):
                    self.att[att].sub_pixs(ISet([IBox(box,diff)]))
            self.att0_sel_update([att])


    def threshold(self):
        PARA = self.parameters.get_all()
        sigma = self.att1.sigma.value()
        B = self.get_visible(pad=True)
        img = self.col.threshold(sigma,3,B) #scheme,B)
        self.image = img.toqimage()
        self.qimage = QImage(self.image)
        self.viewer.setImage(self.qimage)

    @logarg
    def wa_gauss(self,dummy=None):
        if self.wa.bbox is not None:
            self.gauss_box(self.wa.bbox)
        else:
            dmsg("WARNING","no workarea defined yet")

    @logarg
    def gauss(self,dummy=None):
        B = self.get_visible()
        self.gauss_box(B)

    @sbar
    def gauss_box(self,box):
        PARA = self.parameters.get_all()
        xy = PARA["xy"]
        xsigma = self.att1.sigma.value() if "x" in xy else 0
        ysigma = self.att1.sigma.value() if "y" in xy else 0

        sigma = (xsigma,ysigma)
        scheme = self.selpara.get_color_scheme()

        img = self.col.gauss(sigma,"rgb",box) #scheme,B)
        self.image = img.toqimage()
        self.qimage = QImage(self.image)
        self.viewer.setImage(self.qimage)

    def sobel(self):
        B = self.get_visible(pad=True)
        img = self.col.sobel(B) #scheme,B)
        self.image = img.toqimage()
        self.qimage = QImage(self.image)
        self.viewer.setImage(self.qimage)

    @logarg
    def unfilter(self,dummy=None):
        img = self.col.unfilter()
        self.image = img.toqimage()
        self.qimage = QImage(self.image)
        self.viewer.setImage(self.qimage)

    def get_visible(self,pad=False):
        l,r,t,b = self.viewer.getVisible()
        l = max(0,l)
        t = max(0,t)
        if pad:
            r += (BITPAD-BITSHIFT)-((r+(BITPAD-BITSHIFT))%BITPAD) + BITOFF
            r = min(r,self.width-(self.width%BITPAD))
        else:
            r = min(r,self.width)
        b = min(b,self.height)
        return Box(l,t,r,b)

    @sbar
    @logarg
    def coll_fixO(self,dummy=None):
        B = self.get_visible()
        b = {}
        selected = []
        for k,t in self.att0.table:
            if t == "act" and self.att0.table[(k,t)].isChecked():
                selected.append(self.att0.table[(k,"idx")])
            
        for i in selected:
            b[i] = self.att[i].pix.curr.extract_ibox(B).iset.astype(np.bool)

        selected = sorted(selected)            
        if self.coll.updown.text() == "down":
            selected = list(reversed(selected))

        for i,idx0 in enumerate(selected):
            for idx1 in selected[i+1:]:
                rm = b[idx1] & b[idx0]
                if sum(sum(rm)):
                    self.att[idx1].sub_pixs(ISet([IBox(B,iset=rm)]))
                
    @sbar
    @logarg
    def coll_fix(self,dummy=None):
        self.check_collisions()
        if self.colls == {}:
            return
        B = self.get_visible()

        b = {}
        #B = Box(0,0,self.width,self.height)
        for i in self.att:
            b[i] = self.att[i].pix.curr.extract_ibox(B).iset.astype(np.bool)
        for (i,j),coll in self.colls.items():
            assert i < j
            if j < 99:
                nc = sum(sum(coll))
                ni = sum(sum(b[i]))
                nj = sum(sum(b[j]))
                c = coll[B.x0:B.x1,B.y0:B.y1]
                x = c & ~erosion(b[i])
                y = c & ~erosion(b[j])
                x &= ~y
                nx = sum(sum(x))
                ny = sum(sum(y))
                print("NXYCIJ",nx,ny,nc,ni,nj)
                if nx:
                    b[i] &= ~x
                    print("NEWBI",sum(sum(b[i])))
                    self.att_sub_pixs(ISet([IBox(B,x)]),i)
                if ny:
                    b[j] &= ~y
                    print("NEWBI",sum(sum(b[j])))
                    self.att_sub_pixs(ISet([IBox(B,y)]),j)
            else:
                d = b[i] & b[j]
                b[i] &= ~d
                print("XXXNEWBI",sum(sum(b[i])))
                self.att_sub_pixs(ISet([IBox(B,d)]),i)
        self.coll_show_all()

    def coll_fat(self):
        if self.coll.fat.isChecked():
            self.col2_item.setZValue(2)
        else:
            self.col2_item.setZValue(-1)

    def coll_show_all(self):
        bmap = np.zeros(self.wh,dtype=np.bool)
        for bm in self.colls.values():
            bmap[:bm.shape[0],:] |= bm

        bmap2 = ndil(bmap,10)
        w,h = self.wh
        B = Box(0,0,w,h)
        pixmap = IBox(B,iset=bmap).bitmap(QColor("red"))
        pixmap2 = IBox(B,iset=bmap2).bitmap(QColor("blue"))
        self.col_item.setPixmap(pixmap)
        self.col2_item.setPixmap(pixmap2)
        self.col_item.setZValue(3)
        self.coll_fat()

    def coll_show_use(self):
        bmap = np.zeros(self.wh,dtype=np.bool)
        att = self.att0.selected()
        for k in self.colls:
            if att in k:
                bmap[:self.colls[k].shape[0],:] |= self.colls[k]
        bmap2 = ndil(bmap,10)
        w,h = self.wh
        B = Box(0,0,w,h)
        pixmap = IBox(B,iset=bmap).bitmap(QColor("red"))
        pixmap2 = IBox(B,iset=bmap2).bitmap(QColor("blue"))
        self.col_item.setPixmap(pixmap)
        self.col2_item.setPixmap(pixmap2)
        self.col_item.setZValue(3)
        self.coll_fat()

    def coll_show_none(self):
        self.col_item.setZValue(-1)
        self.col2_item.setZValue(-1)

    @sbar
    @logarg
    def cont_fixGA(self,dummy=None):
        PARA = self.parameters.get_all()
        box = self.get_visible()
        self.cont_fixGA_hole(box,self.cont.maxG.value())

    def get_gomi(self,box,maxsize,code):
        iset = self.att[code].pix.curr.extract_ibox(box).iset
        c1 = label(iset,connectivity=1)
        c2 = remove_small_objects(c1,min_size=maxsize).astype(np.bool)
        return iset.astype(np.bool) & ~c2

    def get_holes(self,box,maxsize,code):
        iset = self.att[code].pix.curr.extract_ibox(box).iset
        c1 = label(iset,connectivity=1)
        c2 = remove_small_holes(c1,min_size=maxsize).astype(np.bool)
        return c2 & ~iset.astype(np.bool)

    def cont_fixGA_hole(self,box,hole):
        codes = self.get_codes(use_99=False)
        for code in codes:
            diff = self.get_gomi(box,hole,code)
            n=sum(sum(diff))
            if n:
                self.att[code].sub_pixs(ISet([IBox(box,diff)]))

        self.att0_sel_update(codes)
        #self.cont_show_all()

    @sbar
    @logarg
    def cont_fixHA(self,dummy=None):
        box = self.get_visible()
        PARA = self.parameters.get_all()
        self.cont_fixHA_hole(box,self.cont.maxH.value(),PARA["protect_overwrite"])

    def cont_fixHA_hole(self,box,maxsize,po="protect"):
        prelabel = self.get_prelabel(box)

        if po == "overwrite":
            rm = np.zeros(box.shape,dtype=np.bool)
        else:
            rm = prelabel.astype(np.bool)

        codes = self.get_codes(use_99=False)
        for code in codes:
            diff = self.get_holes(box,maxsize,code) & ~rm
            n=sum(sum(diff))
            if n:
                self.att[code].add_pixs(ISet([IBox(box,diff)]))

        self.att0_sel_update(codes)
        #self.cont_show_all()

    @sbar
    @logarg
    def cont_fixGU(self,dummy=None):
        PARA = self.parameters.get_all()
        maxsize = self.cont.maxG.value()
        box = self.get_visible()
        code = self.att0.selected()

        diff = self.get_gomi(box,maxsize,code)
        n=sum(sum(diff))
        if n:
            self.att[code].sub_pixs(ISet([IBox(box,diff)]))

        self.att0_sel_update([code])
        self.cont_show_use()

    @sbar
    @logarg
    def cont_fixHU(self,dummy=None):
        PARA = self.parameters.get_all()
        maxsize = self.cont.maxH.value()
        PO = PARA["protect_overwrite"]
        box = self.get_visible()
        prelabel = self.get_prelabel(box)

        code = self.att0.selected()
        if PO == "overwrite":
            rm = np.zeros(box.shape,dtype=np.bool)
        else:
            rm = prelabel.astype(np.bool)

        diff = self.get_holes(box,maxsize,code) & ~rm
        n=sum(sum(diff))
        if n:
            self.att[code].add_pixs(ISet([IBox(box,diff)]))

        self.att0_sel_update([code])
        self.cont_show_use()

    def cont_fat(self):
        if self.cont.fat.isChecked():
            self.cnt2_item.setZValue(2)
        else:
            self.cnt2_item.setZValue(-1)

    def cont_show_all(self):
        b = {}
        c = {}
        B = Box(0,0,self.width,self.height)
        for i in self.att:
            if i == 99: continue
            b[i] = self.att[i].pix.curr.extract_ibox(B).iset.astype(np.bool)
            c[i] = find_boundaries(b[i],mode="inner",connectivity=2)

        bmap = np.zeros(self.wh,dtype=np.bool)
        for i in self.att:
            if i == 99: continue
            bmap[:c[i].shape[0],:] |= c[i]

        bmap2 = ndil(bmap,10)
        w,h = self.wh
        B = Box(0,0,w,h)
        pixmap = IBox(B,iset=bmap).bitmap(QColor("red"))
        pixmap2 = IBox(B,iset=bmap2).bitmap(QColor("blue"))
        self.cnt_item.setPixmap(pixmap)
        self.cnt2_item.setPixmap(pixmap2)
        self.cnt_item.setZValue(3)
        self.cont_fat()

    def cont_show_use(self):
        B = Box(0,0,self.width,self.height)
        att = self.att0.selected()

        b = self.att[att].pix.curr.extract_ibox(B).iset.astype(np.bool)
        c = find_boundaries(b,mode="inner",connectivity=2)

        bmap = np.zeros(self.wh,dtype=np.bool)
        bmap[:c.shape[0],:] |= c

        bmap2 = ndil(bmap,10)
        w,h = self.wh
        B = Box(0,0,w,h)
        pixmap = IBox(B,iset=bmap).bitmap(QColor("red"))
        pixmap2 = IBox(B,iset=bmap2).bitmap(QColor("blue"))
        self.cnt_item.setPixmap(pixmap)
        self.cnt2_item.setPixmap(pixmap2)
        self.cnt_item.setZValue(3)
        self.cont_fat()

    def cont_show_none(self):
        self.cnt_item.setZValue(-1)
        self.cnt2_item.setZValue(-1)

    def get_home(self):
        self.hlog(["get_home"])
        self.viewer.fitWindow(self.home)

    def set_home(self):
        try:
            home = self.viewer.boxf
        except:
            home = self.viewer.sceneRect()
        self._set_home(home)

    def _set_home(self,home):
        self.hlog(["_set_home",home])
        self.home = home

    def update_status_bar(self,msg):
        self.hlog(["update_status_bar",msg])
        self.statusBar().showMessage(msg)

#    def fix_collisions(self):
#        for k in list(self.att.a2coll.keys()):
#            a1,a2 = k #XXX
#            region = self.att.a2pix[a1].curr | self.att.a2pix[a2].curr
#            self.bnd_region(region,atts=(a1,a2),ar="remove")

#    def dump_collisions(self):
#        for k,val in self.att.a2coll.items():
#            n = str(len(val))
#            msg = "COLLISION! ATT: " + str(k) + " " +\
#                  "NPIX: " + n + " " +\
#                  "VAL: " + (str(list(val)[0]) if len(val) else "---")
#            self.edit.add(msg)
#            self.warnings.add(msg)
#        if len(self.att.a2coll) == 0:
#            self.edit.add("no collisions")

    def display_pixsets(self,atts,img):
        for att in atts:
            col = self.att.a2c[att].rgba()
            pix = self.att.get_pixs(att) #XXX
            c = self.att.a2c[att].getRgb()[:3]
            for (i,j) in pix:
                img.setPixel(i,j,col)

    def display_boundaries(self,atts,img):
        for att in atts:
            print("DB",att)
            col = self.att.a2c[att].rgba()
            c = self.att.a2c[att].getRgb()[:3]
            nc = QColor((128+c[0])%256,(128+c[1])%256,(128+c[2])%256)
            nd = QColor((128+c[0])%256,c[1],c[2])
            for lab in self.att.a2cset.get(att,[]):
                cnt = self.att.a2cset[att][lab]
                print("LAB",lab,len(cnt.pout),[len(x) for x in cnt.phls])
                for (i,j) in cnt.pout:
                    img.setPixelColor(i,j,nc)
                for h in cnt.phls:
                    for (i,j) in h:
                        img.setPixelColor(i,j,nd)

    @sbar
    @logarg
    def update_image(self):
        print("UI")
        self.hlog(["update_image"])
        img = self.qimage.convertToFormat(QImage.Format_ARGB32)
        atts = sorted(self.att.show())

        self.display_pixsets(atts,img)
        self.update_status_bar("UPDATE IMAGE 3")
        self.viewer.setImage(img)
        self.update_status_bar("READY")


    #XXX
    def change_att(self,att):
        global last
        if last != att:
            self.hlog(["change_att",att])
            self.edit.add("ATT changed: " + att)
            self.change_scheme()
        last = att

    @logarg
    def change_scheme(self,scheme):
        att = self.att0.selected()
        self.att[att].scm = scheme
        para = self.att[att].prm[scheme]
        self.selpara.set_dpara(para)

    def change_selpara(self):
        att = self.att0.selected()
        d = self.selpara.get_dpara()
        scheme = self.att[att].scm
        self.att[att].prm[scheme] = d

    @logret
    def get_loc(self,msg,attcheck=True):
        if attcheck:
            if not self.att:
                self.statusBar().showMessage(msg + ": no att")
                return None,None,None

        self.statusBar().showMessage(msg)
        loc = self.viewer.loc
        x,y = loc.x(),loc.y()
        return loc,x,y

#
# BOX-XXX, LOC-XXX
#

    @logret
    @sbar
    def get_box(self,msg,attcheck=True):
        if attcheck:
            if not self.att:
                self.statusBar().showMessage(msg + ": no att")
                return None,None,None,None,None

        self.statusBar().showMessage(msg)
        box = self.viewer.box
        xmin = box.x()
        xmax = xmin + box.width()
        ymin = box.y()
        ymax = ymin + box.height()
        return box,xmin,xmax,ymin,ymax

    @sbar
    def loc_work(self):
        "remove work boxes containing pt"
        msg = "work area location"
        loc,x,y = self.get_loc(msg,attcheck=False)
        if loc is None: return
        self.wa.clr_point(x,y)

    @sbar
    def box_work(self):
        "add work box"
        msg = "box workarea"
        box,xmin,xmax,ymin,ymax = self.get_box(msg,attcheck=False)
        box = Box(xmin,ymin,x1=xmax,y1=ymax)
        if box is None: return
        self.wa.add(box)

    @sbar
    def loc_info(self):
        # get loc
        msg = "location info"
        loc,x,y = self.get_loc(msg,attcheck=False)
        cols = self.col_get(x,y,"rgbhsv")
        if not cols:
            return
        self.log("sbar","LI1")
        # mask = points with identical RGB
        mask = np.where(self.col.bands["r"] == cols[0],True,False)
        mask = np.where(self.col.bands["g"] == cols[1],mask,False)
        mask = np.where(self.col.bands["b"] == cols[2],mask,False)
        nr,nc = mask.shape
        self.log("sbar","LI2")
        # size(mask)
        n = sum(sum(mask)) #.reshape(-1))
        LEN = "NUM: " + str(n)
        self.log("sbar","LI3")
        # bbox(mask)
        if n:
            xs = [(i,np.sum(mask[:,i])) for i in range(nc)]
            xx = [x for x in xs if x[1] > 0]
            x0,x1 = xx[0][0],xx[-1][0]

            ys = [(i,np.sum(mask[i,:])) for i in range(nr)]
            yy = [y for y in ys if y[1] > 0]
            y0,y1 = yy[0][0],yy[-1][0]
            BOX = "BOX: (" + str(x0) + "-" + str(x1) +\
                  ") x (" + str(y0) + "-" + str(y1)+")"
        else:
            BOX = "BOX: ---"
        self.log("sbar","LI4")
        # display
        RGB = "RGB: " + str(cols[:3])
        HSV = "HSV: " + str(cols[3:])
        self.edit.add(" ".join((RGB,HSV,LEN,BOX)))
        cont = QMessageBox(QMessageBox.Information,
                           "base colors","\n".join((RGB,HSV,LEN,BOX)),
                           QMessageBox.Ok)
        cont.addButton(QMessageBox.Cancel)
        c = QColor(*(list(cols[:3])+[255]))
        color_button(cont.buttons()[0],c)
        if cont.exec() == QMessageBox.Ok:
            self.loc_get_loc(x,y)
        self.statusBar().showMessage("READY")

    @sbar
    def box_info(self):
        # init
        msg = "box info"
        box,xmin,xmax,ymin,ymax = self.get_box(msg,attcheck=False)

        # box color vals
        cs = {x:self.col.bands[x][xmin:xmax,ymin:ymax] for x in "rgbhsv"}

        RGBMIN = "RGBMIN: " + str(tuple(min(cs[x].reshape(-1)) for x in "rgb"))
        RGBMAX = "RGBMAX: " + str(tuple(max(cs[x].reshape(-1)) for x in "rgb"))
        HSVMIN = "HSVMIN: " + str(tuple(min(cs[x].reshape(-1)) for x in "hsv"))
        HSVMAX = "HSVMAX: " + str(tuple(max(cs[x].reshape(-1)) for x in "hsv"))

        # display 1
        cont = QMessageBox(QMessageBox.Information,
                           "base colors",
                           "\n".join((RGBMIN,RGBMAX,HSVMIN,HSVMAX)),
                           QMessageBox.Ok).exec()

        # plot histogram
        try:
            fig = plt.figure()
            fig.clf()

            for i in range(6):
                x = "rgbhsv"[i]
                fig.add_subplot(2,3,i+1)
                data = cs[x].reshape(-1)
                plt.hist(data, facecolor='green',bins=max(data)-min(data) + 1)
                plt.title(["RED","GREEN","BLUE",
                           "HSV-HUE","HSV-SATURATION","HSV-VALUE"][i])
                plt.grid(True)
            plt.show()
        except:
            pass
        self.statusBar().showMessage("READY")

    @sbar
    def loc_get(self):
        # init
        msg = "get location"
        loc,x,y = self.get_loc(msg)
        if loc is None: return
        self.loc_get_loc(x,y)

    def loc_get_loc(self,x,y):
        msg = "get location"
        scheme = self.selpara.get_color_scheme()
        try:
            col = self.col_get(x,y,scheme=scheme)
        except:
            dmsg("Warning","loc out of range")
            return
        c = QColor(*self.col_get(x,y,scheme="rgb"))
        self.att0_set_old_col(c)

        # get paras
        pars = [self.selpara.get_para(i) for i in range(1,len(col)+1)]
        PO = self.parameters.get_all()["protect_overwrite"]
        self.log("edit","loc_get+"+str(x)+str(y)+str(col))
        self.log("dump",["loc_get",x,y,col,pars])

        # get box
        mins = [max(pars[i][0],col[i] - pars[i][1]) for i in range(len(col))]
        maxs = [min(pars[i][2],col[i] + pars[i][1]) for i in range(len(col))]

        if not mins:
            return
        
        iset = self.col.bands[scheme[0]]
        mask = np.where(iset >= mins[0],True,False)
        mask = np.where(iset <= maxs[0],mask,False)
        for i in range(1,len(col)):
            iset = self.col.bands[scheme[i]]
            mask = np.where(iset >= mins[i],mask,False)
            mask = np.where(iset <= maxs[i],mask,False)
        if self.parameters.vonly.isChecked():
            B = self.get_visible()
            mask = mask[B.x0:B.x1,B.y0:B.y1]
        else:
            B = Box(0,0,self.width,self.height)


        if PO == "overwrite":
            for code in self.get_codes():
                sub = ISet([IBox(B,np.array(mask))])
                self.att[code].sub_pixs(sub)
        else:
            for code in self.get_codes():
                att = self.att[code]
                rm = att.pix.curr.extract_ibox(B).iset.astype(np.bool)
                mask &= ~rm
        imask = ISet([IBox(B,mask)])                
        self.att_add_pixs(imask)

        # msg
        npix = str(len(imask)) + " pixels"
        self.edit.add(msg + ":" + str((x,y)) + " " + npix)
        self.statusBar().showMessage("READY")

    def box_get(self,check=True):
        msg = "get box"
        box,xmin,xmax,ymin,ymax = self.get_box(msg)
        if box is None: return
        self.log("edit",
                 "get box " + \
                 str([xmin,xmax,ymin,ymax]))

        # COLORS RGB colors of box (except those for highlighting)
        rgbset = {self.col_get(x,y)
                  for x in range(xmin,xmax)
                  for y in range(ymin,ymax)}

        # CHANGE: remove contour boundaries as well
        n = len(rgbset)
        tmp = "Box contains " + str(n) + " colors: Continue?"
        if check and not ask("colors",tmp):
            return

        # CLUSTERS
        clusters = Data(rgbset).cluster(size=self.parameters.get_cls())
        n = len(clusters.keys())
        tmp = "Box contains " + str(n) + " clusters: Continue?"
        if check and not ask("colors",tmp):
            return
        tmp = "box convex closure"
        self.statusBar().showMessage(tmp)

        # CONVEX HULL OF CLUSTERS
        colors = set()
        for i in range(n):
            colors |= Data(clusters[i]).convex_hull()
        n = len(colors)
        if n == 0:
            return
        tmp = "Convex hull contains " + str(n) + " colors: Continue?"
        if check and not ask("colors",tmp):
            return

        # gen mask
        for box,item in self.wa.items:
            B = box
            mask = np.zeros((B.dx,B.dy),dtype=np.bool)
            colmasks = [self.col.bands[x][B.x0:B.x1,B.y0:B.y1]
                        for x in self.selpara.get_color_scheme()]
            for col in colors:
                for x,m in zip(col,colmasks):
                    mask = np.where(m == x, True, mask)

            imask = ISet([IBox(B,mask)])
            self.att_add_pixs(imask)
        #for a,vs in self.att.items():
        #    print(a,len(vs))

        # MSG
        tmp = msg + \
              " X:" + str((xmin,xmax)) + \
              " Y:" + str((ymin,ymax)) + \
              " NC: " + str(n)
        self.edit.add(tmp)
        self.statusBar().showMessage("READY")



    @sbar
    def labels(self,box,att_last=0,zlabels=False,cclabel=True,use_99=True):
        prelabel = np.zeros(box.shape,dtype=np.uint32)
        xlast=None
        for code,att in self.att.items():
            if not use_99 and code == 99:
                continue
            if att != att_last:
                x = att.pix.curr.extract_ibox(box).iset.astype(np.uint32)
                prelabel = np.where(x,code,prelabel)
            else:
                xlast = code*x
        if xlast is not None:
            prelabel = np.where(xlast!=0,xlast,prelabel)
        if cclabel:
            clabel = label(prelabel,connectivity=1)
        else:
            clabel = None
        if zlabels:
            zlabel = label(prelabel,connectivity=1,background=-1)-1
            assert zlabel[0,0] == 0
        siz = {}
        for x in clabel.reshape(-1):
            siz[x] = siz.get(x,0) + 1
        self.lab_att = prelabel
        self.lab_siz = siz
        self.lab_box = box
        self.lab_cmp = clabel
        if zlabels:
            return zlabel
        else:
            return None

    @sbar
    def component(self,i,j,filled=False,protect=True):
        x0,x1,y0,y1 = self.lab_box.xy()
        if i < x0 or i >= x1 or j < y0 or j >= y1:
            return None
        i -= x0
        j -= y0
        lab = self.lab_cmp[i,j]
        comp = ~((self.lab_cmp-lab).astype(np.bool))
        if not filled:
            return comp
        fcomp = binary_fill_holes(comp) + 0
        fill = fcomp & (~comp)
        if protect:
            fill &= ~(self.lab_att.astype(np.bool))
        return fill

    @sbar
    def loc_paint(self):
        msg = "paint location"
        loc,x,y = self.get_loc(msg,attcheck=True)
        if loc is None:
            self.statusBar().showMessage("READY")
            return

        PARA = self.parameters.get_all()
        AR = PARA["add_remove"]
        POLY = self.polys.get_all()
        PP = POLY["pp"]

        att = self.att0.selected()
        tr = None
        if PP == "poly":
            self.pplist.append((x,y))
            self.pp_update()
            return
        elif PP == "edit":
            if self.pplist:
                ds = [hypot(x-z[0],y-z[1]) for z in self.pplist]
                n = len(ds)
                d = min(ds)
                i = ds.index(d)
                if AR == "add":
                    xl = self.pplist[i]
                    p = self.pplist[(i+1) % n]
                    m = self.pplist[(i+n-1) % n]
                    an = atan2(xl[1] - p[1], xl[0] - p[0])
                    ap = atan2(xl[1] - m[1], xl[0] - m[0])
                    a = atan2(xl[1] - y, xl[0] - x)
                    dn = min(abs(a-an),2*pi-abs(a-an))
                    dp = min(abs(a-ap),2*pi-abs(a-ap))
                    if dn < dp:
                        self.pplist = self.pplist[i+1:] +\
                                      self.pplist[:i+1]
                    else:
                        self.pplist = list(reversed(self.pplist[:i])) +\
                                      list(reversed(self.pplist[i:]))
                    self.polys.pp_update()
                    self.polys.pp_update()
                else:
                    self.pplist[i:i+1] = []
            elif AR == "add":
                self.pplist = [(x,y)]
            self.pp_update()
        else:
            self.comp_paint(x,y)

    def level_contains(self,level,x,y):
        b = self.att[level].pix.curr.extract_ibox(Box(x,y,dx=1,dy=1))
        print ("LEVEL",level,x,y,b.iset[0])
        return b.iset[0]


    def comp_paint(self,x,y):
        PARA = self.parameters.get_all()
        AR = PARA["add_remove"]
        PO = PARA["protect_overwrite"]
        self.att1_lab_visible()

        sel = self.att0.selected()
        if not self.level_contains(sel,x,y):
            return

        if AR == "remove":
            c1 = self.component(x,y)
            if c1 is not None:
                ib = ISet([IBox(self.lab_box,iset=c1)])
                self.att_sub_pixs(ib,update=False)
        else:
            c1 = self.component(x,y,filled=True,protect=(PO=="protect"))
            if c1 is not None:
                ib = ISet([IBox(self.lab_box,iset=c1)])
                self.att_add_pixs(ib,update=False)

    def poly_paint(self,tr,delflag=0):
        PARA = self.parameters.get_all()
        AR = PARA["add_remove"]
        PO = PARA["protect_overwrite"]
        rr,cc = tset(tr)

        if len(rr):
            x0,y0 = min(rr),min(cc)
            x1,y1 = max(rr)+1,max(cc)+1
            rr -= x0
            cc -= y0
            c1 = np.zeros((x1-x0,y1-y0),dtype=np.bool)
            c1[rr,cc] = 1
            box = Box(x0,y0,x1,y1)
            rm = np.zeros(box.shape,dtype=np.uint8)
            if delflag == 0 and AR == "remove" or delflag == -1:
                ib = ISet([IBox(box,iset=c1)])
                self.att_sub_pixs(ib,update=False)
            else: # need to add PO
                if PO == "protect":
                    for code,att in self.att.items():
                        x = att.pix.curr.extract_ibox(box).iset.astype(np.uint8)
                        rm += x
                    rm = np.where(rm>0,1,0).astype(np.bool)
                else:
                    code = self.att0.selected()
                    att = self.att[code]
                    rm = att.pix.curr.extract_ibox(box).iset.astype(np.uint8)
                ib = ISet([IBox(box,iset=c1&~rm)])
                self.att_add_pixs(ib,update=False)


    def box_paint(self):
        return
        msg = "paint box"
        box,xmin,xmax,ymin,ymax = self.get_box(msg,attcheck=True)
        if box is None:
            self.statusBar().showMessage("READY")
            return
        try:
            box = Box(xmin,ymin,xmax,ymax)
        except:
            dmsg("Warning","illegal box " + str((xmin,ymin,xmax,ymax)))
            return
        # PARAMETERS
        PARA = self.parameters.get_all()
        AR = PARA["add_remove"]
        PO = PARA["protect_overwrite"]
        att = self.att0.selected()

        self.hlog(["_box_paint",att,xmin,ymin,xmax,ymax,AR,PO])

        paintset = ISet([IBox(box,ones=True)])
        print("DTYPE",len(paintset.boxes),paintset.boxes[0].iset.dtype)
        print("PT1",len(paintset))
        if AR == "add":
            if PO == "protect":
                for a,ad in self.att.items():
                    if a != att:
                        paintset -= ad.pix.curr
                        print("PT2",len(paintset))
            else:
                for a,ad in self.att.items():
                    ad.pix.curr -= paintset
            print("PT3",att,len(paintset))
            self.att_add_pixs(paintset)
        else:
            print("PT4",att,len(paintset))
            self.att_sub_pixs(paintset)

        # MSG
        msg = "paint box"
        self.edit.add(msg + "(" + AR + PO + ")" +\
                      " X:"+ str((xmin,xmax)) +\
                      " Y:" + str((ymin,ymax)))
        self.statusBar().showMessage("READY")

    @sbar
    def loc_fix(self):
        msg = "boundary location"
        loc,x,y = self.get_loc(msg,attcheck=True)
        if loc is None:
            self.statusBar().showMessage("READY")
            return

        PARA = self.parameters.get_all()
        HOLE = self.cont.maxH.value()
        PO = PARA["protect_overwrite"]

        box = self.att1_lab_visible()
        c1 = self.component(x,y)
        if c1 is None:
            return
        
        if PO == "overwrite":
            rm = np.zeros(box.shape,dtype=np.bool)
        else:
            rm = self.lab_att.astype(np.bool)
        c2 = remove_small_holes(c1,HOLE).astype(np.bool)
        diff = c2 & ~c1 & ~rm
        if sum(sum(diff)):
            self.att_add_pixs(ISet([IBox(box,diff)]))

    @sbar
    def box_fix(self):
        msg = "paint box"
        box,xmin,xmax,ymin,ymax = self.get_box(msg,attcheck=True)
        if box is None:
            self.statusBar().showMessage("READY")
            return

        B = Box(xmin,ymin,xmax,ymax)
        Z = ~np.zeros(B.shape,dtype=np.bool)
        self.bnds_fix_box(B,w=self.cont.maxB.value(),zone=Z)

    def magic(self):
        if self.viewer.mode == "paint":
            pl = self.pplist
            app = True
            if len(pl) < 2:
                if not self.pplists:
                    return
                else:
                    pl = self.pplists[-1]
                    if len(pl) < 2:
                        return
                    app = False
            if len(pl) == 2:
                a,b = pl
                pl = [a,(a[0],b[1]),b,(b[0],a[1])]
            if app:
                self.pplists.append(pl)
                self.ppidx = len(self.pplists)-1
            self.pplist = []
            self.pp_update()
            rr,cc = tset(pl)
            if len(rr) == 0:
                return
            x0,y0 = min(rr),min(cc)
            x1,y1 = max(rr)+1,max(cc)+1
            B = Box(x0,y0,x1,y1)
            rr -= x0
            cc -= y0
            Z = np.zeros((x1-x0,y1-y0),dtype=np.uint8)
            Z[rr,cc] = 1
            Z = Z.astype(np.uint8)
            W = self.cont.maxB.value()
            self.bnds_fix_box(B,w=W,zone=Z)


    def kill(self):
        if self.viewer.mode == "paint":
            pl = self.pplist
            app = True
            if len(pl) < 2:
                if not self.pplists:
                    return
                else:
                    pl = self.pplists[-1]
                    if len(pl) < 2:
                        return
                    app = False
            if len(pl) == 2:
                a,b = pl
                pl = [a,(a[0],b[1]),b,(b[0],a[1])]
            if app:
                self.pplists.append(pl)
                self.ppidx = len(self.pplists)-1
            self.pplist = []
            self.pp_update()
            rr,cc = tset(pl)
            if len(rr) == 0:
                return
            x0,y0 = min(rr),min(cc)
            x1,y1 = max(rr)+1,max(cc)+1
            B = Box(x0,y0,x1,y1)
            rr -= x0
            cc -= y0
            Z = np.zeros((x1-x0,y1-y0),dtype=np.uint8)
            Z[rr,cc] = 1
            Z = Z.astype(np.uint8)
            self.rm_zone(B,zone=Z)

    def rm_zone(self,box,zone):
        print("rm zone",box)
        codes = sorted([y for y in self.att.keys() if y != 99],key=lambda x:-x)

        for code in codes:
            att = self.att[code]
            for (b,idx) in self.wa.items:
                att.pix.add_box(b)

            pix = att.pix.curr.extract_ibox(box).iset.astype(bool)
            rm = pix & zone
            if sum(sum(rm)):
                att.sub_pixs(ISet([IBox(box,rm)]))
                self.att0_sel_update([code])

    @sbar
    def loc_tlab(self):
        msg = "label location"
        loc,x,y = self.get_loc(msg,attcheck=True)
        if loc is None:
            self.statusBar().showMessage("READY")
            return

        try:
            x0,x1,y0,y1 = self.lab_box.xy()
            assert not(x < x0 or x >= x1 or y < y0 or y >= y1)
        except:
            self.att1_lab_visible()
        comp = self.component(x,y)
        pixmap = IBox(self.lab_box,iset=comp).bitmap(QColor("red"))
        w,h = self.lab_box.shape
        self.att1_lab_clear()
        w += (BITPAD-BITSHIFT)-((w+(BITPAD-BITSHIFT))%BITPAD) + BITOFF
        self.lab_item = self.viewer.scene.addPixmap(QBitmap(w,h))
        self.lab_item.setOffset(self.lab_box.x0,self.lab_box.y0)
        try:
            self.lab_item.setPixmap(pixmap)
        except:
            self.lab_item = self.viewer.scene.addPixmap(QBitmap(w,h))
            self.lab_item.setPixmap(pixmap)
        self.lab_item.setZValue(3)

    @sbar
    def box_tlab(self):
        msg = "paint box"
        box,xmin,xmax,ymin,ymax = self.get_box(msg,attcheck=True)
        if box is None:
            self.statusBar().showMessage("READY")
            return

        w = xmax - xmin
        w += (BITPAD-BITSHIFT)-((w+(BITPAD-BITSHIFT))%BITPAD) + BITOFF

        box = Box(xmin,ymin,xmin+w,ymax)
        self.labels(box)

    @sbar
    def loc_edit(self):
        msg = "edit location"
        loc,x,y = self.get_loc(msg)
        if loc is None:
            self.statusBar().showMessage("READY")
            return

        ibox = IBox(Box(x,y,x+1,y+1),ones=True)
        self.edit_region(ibox)

        # MSG
        self.edit.add(msg + ": " + str((x,y)))
        self.statusBar().showMessage("READY")

    def box_edit(self):
        msg = "edit box"
        box,xmin,xmax,ymin,ymax = self.get_box(msg)
        if box is None:
            self.statusBar().showMessage("READY")
            return
        ibox = IBox(Box(xmin,ymin,xmax,ymax),ones=True)
        self.edit_region(ibox)

        # MSG
        msg = "edit box: X:"+str((xmin,xmax))+" Y:"+ str((ymin,ymax))
        self.edit.add(msg)
        self.statusBar().showMessage("READY")

    def edit_region(self,ibox):
        print("REGION",ibox.box)
        a = self.att0.selected()
        att = self.att[a]

        for sign,pixs in reversed(att.pix.hist):
            print("HIST",sign)
            if sign == "-":
                break
            sub = False
            for b in pixs.boxes:
                print ("TEST",b.box)
                if ibox.meets(b):
                    print ("TRUE")
                    sub=True
                    break
            if sub:
                att.sub_pixs(pixs)
                return

    def loc_cnt(self):
        pass

    def box_cnt(self):
        pass

    def loc_mor(self):
        msg = "morph location"
        loc,x,y = self.get_loc(msg,attcheck=True)
        if loc is None:
            self.statusBar().showMessage("READY")
            return

        PARA = self.parameters.get_all()
        OCDE = PARA["ocde"]
        PO = PARA["protect_overwrite"]

        att = self.att0.selected()
        box = self.att1_lab_visible(att)

        if PO == "overwrite":
            rm = np.zeros(box.shape,dtype=np.bool)
        else:
            rm = self.lab_att.astype(np.bool)

        c = self.component(x,y)
        if OCDE == "close":
            d = closing(c)
            diff = d & ~c & ~rm
            if sum(sum(diff)):
                self.att_add_pixs(ISet([IBox(box,diff)]))
        elif OCDE == "close2":
            d = erosion(erosion(dilation(dilation(c))))
            diff = d & ~c & ~rm
            if sum(sum(diff)):
                self.att_add_pixs(ISet([IBox(box,diff)]))
        elif OCDE == "dilate":
            d = dilation(c)
            diff = d & ~c & ~rm
            if sum(sum(diff)):
                self.att_add_pixs(ISet([IBox(box,diff)]))
        elif OCDE == "erode":
            d = erosion(c)
            diff = c & ~d
            if sum(sum(diff)):
                self.att_sub_pixs(ISet([IBox(box,diff)]))
        elif OCDE == "open":
            d = opening(c)
            diff = c & ~d
            if sum(sum(diff)):
                self.att_sub_pixs(ISet([IBox(box,diff)]))
        elif OCDE == "open2":
            d = dilation(dilation(erosion(erosion(opening(c)))))
            diff = c & ~d
            if sum(sum(diff)):
                self.att_sub_pixs(ISet([IBox(box,diff)]))



    def box_mor(self):
        msg = "paint box"
        box,xmin,xmax,ymin,ymax = self.get_box(msg,attcheck=True)
        if box is None:
            self.statusBar().showMessage("READY")
            return
        xybox = Box(xmin,ymin,xmax,ymax)

        # PARAMETERS
        PARA = self.parameters.get_all()
        OCDE = PARA["ocde"]
        PO = PARA["protect_overwrite"]

        box = self.att1_lab_visible()

        if PO == "overwrite":
            rm = np.zeros(box.shape,dtype=np.bool)
        else:
            rm = self.lab_att.astype(np.bool)

        att = self.att0.selected()

        cs1 = np.where(self.lab_att == att,self.lab_cmp,0)
        cs2 = cs1[xybox.x0-box.x0:xybox.x1-box.x0,xybox.y0-box.y0:xybox.y1-box.y0]
        cs3 = set(cs2.reshape(-1))

        for cs in cs3:
            c = ~((self.lab_cmp - cs).astype(np.bool))
            #c = np.where(self.lab_cmp == cs,self.lab_cmp,0)
            if OCDE == "close":
                d = closing(c)
                diff = d & ~c & ~rm
                if sum(sum(diff)):
                    self.att[att].add_pixs(ISet([IBox(box,diff)]))
            elif OCDE == "close2":
                d = erosion(erosion(dilation(dilation(c))))
                diff = d & ~c & ~rm
                if sum(sum(diff)):
                    self.att[att].add_pixs(ISet([IBox(box,diff)]))
            elif OCDE == "dilate":
                d = dilation(c)
                diff = d & ~c & ~rm
                if sum(sum(diff)):
                    self.att[att].add_pixs(ISet([IBox(box,diff)]))
            elif OCDE == "erode":
                d = erosion(c)
                diff = c & ~d
                if sum(sum(diff)):
                    self.att[att].sub_pixs(ISet([IBox(box,diff)]))
            elif OCDE == "open":
                d = opening(c)
                diff = c & ~d
                if sum(sum(diff)):
                    self.att[att].sub_pixs(ISet([IBox(box,diff)]))
            elif OCDE == "open2":
                d = dilation(dilation(erosion(erosion(opening(c)))))
                diff = c & ~d
                if sum(sum(diff)):
                    self.att[att].sub_pixs(ISet([IBox(box,diff)]))

        self.att0_sel_update([att])

# MENU
#

# FILES

    def save_exit(self):
        shp = self.path[:-3] + "shp"
        pck = self.path[:-3] + "pck"
        self.file_dump(path=pck)
        if self.file_save(path=shp) == 2:
            return
        self.close()

    @logarg
    def file_read(self,path=False):
        self.hlog(["file_read",path])
        start = dt.now()
        if not path:
            qget = QFileDialog.getOpenFileName
            path = qget(self, 'Load file', 'shp', "HMap (*.shp)")[0]
        if path:
            R = shapefile.Reader(path)
            rs = R.records()
            if len(rs):
                try:
                    lv = int(rs[0][0])
                except:
                    lv = 1
                if self.att:
                    mk = min(self.att.keys())
                else:
                    mk = None
                print("LM",lv,mk,rs[0],type(rs[0]))
                if lv == 1:
                    if mk is None:
                        self.att0.gen1()
                    else:
                        assert mk == 1
                elif lv in range(10,20):
                    if mk is None:
                        self.att0.gen5()
                    else:
                        assert mk in range(10,20)
                elif lv in range(20,30):
                    if mk is None:
                        self.att0.gen7()
                    else:
                        assert mk in range(20,30)
                elif lv in range(30,40):
                    if mk is None:
                        self.att0.gen6()
                    else:
                        assert mk in range(30,40)
                elif lv in range(40,50):
                    if mk is None:
                        self.att0.gen8()
                    else:
                        assert mk in range(40,50)

            x0 = 100000
            y0 = 100000
            x1 = 0
            y1 = 0

            for ir,sr in enumerate(R.shapeRecords()):
                pts = [self.rr(x,y) for x,y in sr.shape.points]
                xs = [x[0] for x in pts]
                ys = [x[1] for x in pts]
                x0 = min(x0,min(xs))
                x1 = max(x1,max(xs))
                y0 = min(y0,min(ys))
                y1 = max(y1,max(ys))
            x0 = int(floor(x0))
            y0 = int(floor(y0))
            x1 = int(ceil(x1))
            y1 = int(ceil(y1))
            B = Box(x0,y0,x1,y1)
            print("BOX",B)
            keys = sorted([x for x in self.att.keys() if x != 99])
            add = {i:np.zeros((x1-x0,y1-y0),dtype=np.bool) for i in keys}
            sub = {i:np.zeros((x1-x0,y1-y0),dtype=np.bool) for i in keys}

            if not self.wa.items:
                self.wa.clear()
                self.wa.add(B)
                self.wa.generate(self.col.bands)

            for i in self.att:
                pix = self.att[i].pix
                for (b,idx) in self.wa.items:
                    pix.add_box(b)


            for ir,sr in enumerate(R.shapeRecords()):
                rec = int(sr.record[0])
                pts = [self.rr(x,y) for x,y in sr.shape.points]
                sep = sr.shape.parts
                print ("Reading",ir,rec,sep,len(pts),dt.now()-start)
                if len(sep) == 1:
                    out = pts
                    ins = []
                else:
                    out = pts[:sep[1]]
                    ins = [pts[sep[i]:sep[i+1]] for i in range(1,len(sep)-1)]
                    ins.append(pts[sep[-1]:])
                try:
                    tmp = [list(x) for x in out]
                    out = rdp(tmp,epsilon=0.1)
                except:
                    print("OUT",out)
                    raise
                rr,cc = tset(out)
                if len(rr):
                    rr -= x0
                    cc -= y0
                    add[rec][rr,cc] = 1
                    for h in ins:
                        try:
                            tmp = [list(x) for x in h]
                            h = rdp(tmp,epsilon=1.0)
                        except:
                            print("OUT",h)
                            raise
                        rr,cc = tset(h)
                        rr -= x0
                        cc -= y0
                        sub[rec][rr,cc] = 1



            for i in keys:
                print("KEY",i,dt.now()-start)
                ib = ISet([IBox(B,iset=add[i])])
                self.att[i].add_pixs(ib)
                ib = ISet([IBox(B,iset=sub[i])])
                self.att[i].sub_pixs(ib)
            print("UP",dt.now()-start)
            self.att0_sel_update()
            print("UP DONE",dt.now()-start)


    def check_holes(self):
        w,h = self.wh
        B = Box(0,0,w,h)
        HOLE = 5
        n = 0
        for att in self.att:
            if att == 99: continue
            x = self.att[att].pix.curr.extract_ibox(B).iset.astype(np.bool)
            c1 = label(x,connectivity=1)
            c2 = remove_small_objects(c1,min_size=HOLE)
            diff = c2 & ~x
            n += sum(sum(diff))
        return n

    def check_gomi(self):
        w,h = self.wh
        B = Box(0,0,w,h)
        HOLE = 5
        n = 0
        for att in self.att:
            if att == 99: continue
            x = self.att[att].pix.curr.extract_ibox(B).iset.astype(np.bool)
            c1 = label(x,connectivity=1)
            c2 = remove_small_objects(c1,min_size=HOLE).astype(np.bool)
            diff = x & ~c2
            n += sum(sum(diff))
        return n

    @logarg
    def file_save(self,path=False):
        if not self.att:
            dmsg("Warning","no atts")
            return 1

        if self.check_collisions():
            dmsg("Warning","unresolved collisions")
            return 2

        n= self.check_holes()
        if n:
            if not ask("WARNING",str(n)+" small hole pixels found. Continue?"):
                return 2

        n= self.check_gomi()
        if n:
            if not ask("WARNING",str(n)+" gomi pixels found. Continue?"):
                return 2

        def extract_holes(cnt):
            holes = []
            while True:
                #print(cnt)
                count = {}
                for ii,x in enumerate(cnt[:-1]):
                    count.setdefault(x,[]).append(ii)
                xs = [x for x in count if len(count[x]) > 1]
                if not xs:
                    break
                n = len(cnt) - 1
                diff = None
                for x in xs:
                    a,b = count[x]
                    d = min(b-a,a+n-b)
                    if d < n:
                        n = d
                        da,db = a,b
                g1 = cnt[da:db+1]
                g2 = cnt[db:] + cnt[1:da+1]
                xs1 = [x[0] for x in g1]
                ys1 = [x[1] for x in g1]
                xs2 = [x[0] for x in g2]
                ys2 = [x[1] for x in g2]
                if min(xs1) < min(xs2) or min(ys1) < min(ys2) or max(xs1) > max(xs2) or max(ys1) > max(ys2):
                    cnt = g1
                    hol = g2
                elif min(xs2) < min(xs1) or min(ys2) < min(ys1) or max(xs2) > max(xs1) or max(ys2) > max(ys1):                    
                    cnt = g2
                    hol = g1
                else:
                    l1 = [x for x in g1 if x[0] == min(xs1)]
                    l2 = [x for x in g2 if x[0] == min(xs2)]
                    ll1 = min([x[1] for x in l1])
                    ll2 = min([x[1] for x in l2])
                    rl1 = max([x[1] for x in l1])
                    rl2 = max([x[1] for x in l2])
                    if ll1 < ll2 or rl1 > rl2:
                        cnt = g1
                        hol = g2
                    elif ll2 < ll1 or rl2 > rl1:
                        cnt = g2
                        hol = g1
                    else:
                        print("G1",g1)
                        print("G2",g2)
                        raise ValueError("BUG")
                if hol:
                    holes.append(reversed(hol))
            return cnt,holes



        B = self.wa.bbox.grow(2)
        B2 = self.wa.bbox.grow(4)
        self.log("sbar","fs labels0")
        codes = self.get_codes(use_99=False)
        prelabel = self.get_prelabel(B,use_99=False)
        labs = {}
        for c in codes:
            cprelabel = ~((prelabel-c).astype(np.bool))

            clabel = label(cprelabel,connectivity=1)
            cbnds = find_boundaries(clabel,mode="inner",connectivity=2)*clabel
            assert(not clabel[0,0])
            self.log("sbar","fs labels1 done " + str(c))    
            #clabs = set(list(clabel.reshape(-1)))

            nlabel = label(~cprelabel,connectivity=1)
            nlabel[0,:] = 0
            nlabel[-1,:] = 0
            nlabel[:,0] = 0
            nlabel[:,-1] = 0
            nbnds = find_boundaries(nlabel,mode="inner",connectivity=2)*nlabel    
            self.log("sbar","fs labels2 done " + str(c))


            habs = {}
            for i in range(B.dx):
                for j in range(B.dy):
                    lab = nlabel[i,j]
                    #print("NIJ",i,j,nlabel[i,j])
                    #if i == 0 and j == 0:
                    #    habs[lab] = None
                    if lab and lab not in habs:
                        out = outline(nbnds,(i,j))
                        cnt = [(x+B.x0,y+B.y0) for (x,y) in bnd2outer(out)]
                        #print("CC",cnt,"OUT",out,"LAB",lab,habs)
                        cnt2,holes = extract_holes(cnt)
                        #print("CC2",cnt2)
                        habs[lab] = Contour(cnt2)
                          
            x0,x1,y0,y1 = B.xy()
            HV = [x for x in habs.values() if x is not None]
            for i in range(B.dx):
                for j in range(B.dy):
                    lab = clabel[i,j]
                    if lab and (c,lab) not in labs:
                        out = outline(cbnds,(i,j))
                        cnt = [(x+B.x0,y+B.y0) for (x,y) in bnd2outer(out)]
                        cnt,holes = extract_holes(cnt)
                        C = Contour(cnt,att=c)
                        labs[c,lab] = C
                        holes=[]
                        for H in holes:
                            if H:
                                try:
                                    C = Contour(H)
                                    holes.append(C)
                                except:
                                    print("BUG",H)
                        for H in holes:
                            C.add_hole(H)
                        for hole in HV:
                            if C.contains(hole):
                                for H in holes:
                                    if H.contains(hole):
                                        break
                                else:
                                    C.add_hole(hole)




        pl = self.get_prelabel(B,use_99=False).astype(np.bool)
        mask = np.zeros(B2.shape,dtype=np.uint8)
        mask[2:-2,2:-2] = (~pl).astype(np.uint8)
        mask[1,:] = 0
        mask[-2,:] = 0
        mask[:,1] = 0
        mask[:,-2] = 0
        mask[0,:] = 1
        mask[-1,:] = 1
        mask[:,0] = 1
        mask[:,-1] = 1

        print("MASK",sum(sum(mask)))
        clabel2 = label(mask,connectivity=1)
        zlabel2 = label(mask,connectivity=1,background=-1)-1
        bnds2 = find_boundaries(clabel2,mode="inner",connectivity=2)*clabel2
        zbnds2 = find_boundaries(zlabel2,mode="inner",connectivity=2)*zlabel2
        nz11 = np.where(bnds2,zbnds2,0)
        nz22 = nz11.reshape(-1)
        nz2 = set(list(nz22))

        print("NZ2",len(nz2))
        labs2 = {}
        pixs = np.zeros(B2.shape,dtype=np.bool)
        for i in range(B2.dx):
            for j in range(B2.dy):
                if zlabel2[i,j] and not pixs[i,j]:
                    pixs[i,j] = True
                    lab = zlabel2[i,j]
                    if lab not in labs2:
                        out = outline(zbnds2,(i,j))
                        cnt = [(x+B2.x0,y+B2.y0) for (x,y) in bnd2outer(out)]
                        labs2[lab] = Contour(cnt,att=99)
                        self.log("sbar","outer contour: " + str(len(labs)))

        zlabs2 = labs2
        labs2 = {k:zlabs2[k] for k in zlabs2 if k in nz2}

        for lab,C in labs2.items():
            for t in zlabs2:
                if t != lab:
                    T = zlabs2[t]
                    if C.contains(T):
                        C.add_hole(T)


        self.log("sbar","fs save")

        self.edit.add("FILE: save")
        w = shapefile.Writer()
        w.shapeType = shapefile.POLYGON
        w.autoBalance = 1
        w2 = shapefile.Writer()
        w2.shapeType = shapefile.POLYGON
        w2.autoBalance = 1
        w.field("level")
        w2.field("level")
        n=0
        for cnt in labs.values():
            n += 1
            self.log("sbar","fs save: "+str(n))
            cnt.shp_write(w,self.ll)
        qget = QFileDialog.getSaveFileName
        if not path:
            path = self.path.split(".")[0]+'.shp'
            path = qget(self, 'Save file', path, "HMap (*.shp)")[0]
        self.hlog(["file_save",path])
        if path:
            shp = path[:-3] + "shp"
            shx = path[:-3] + "shx"
            dbf = path[:-3] + "dbf"
            backup(shp)
            backup(shx)
            backup(dbf)
            try:
                w.save(path)
            except:
                dmsg("FAILURE","couldn't save shapefile: dump - fix program - try again")

        for lab,cnt in labs2.items():
            if lab in nz2:
                n += 1
                self.log("sbar","fs save2: "+str(n))
                cnt.shp_write(w2,self.ll)

        d,p = dirname(path),basename(path)
        path2 = join(d,"_"+p[:-4]+"_hh.shp")
        w2.save(path2)

    @logarg
    def file_load(self,path=False):
        self.hlog(["file_load",path])
        if not path:
            qget = QFileDialog.getOpenFileName
            path = qget(self, 'Load file', 'pck', "HMap (*.pck)")[0]
        if path:
            with open(path,"rb") as f:
                if not self.unpack(pload(f)):
                    return
            if self.att:
                print(sorted(self.att0.table.keys()))
                self.att0.table[0,"sel"].setChecked(True)
        self.att0_sel_update()

    @logarg
    def file_dump(self,path=False):
        qget = QFileDialog.getSaveFileName
        if not path:
            path = qget(self, 'Dump file', self.path.split(".")[0]+'.pck', "HMap (*.pck)")[0]
        self.hlog(["file_dump",path])
        if path:
            backup(path)
            with open(path,"wb") as f:
                data = self.pack()
                pdump(data,f)

    def pack(self):
        data = {}
        #data["home"] = self.home
        data["version"] = PICKLE_VERSION
        data["path"] = self.path
        data["att"] = {att : self.att[att].pack() for att in self.att}
        data["workarea"] = [box for box,item in self.wa.items]
        return data

    def unpack(self,data):
        if "version" not in data or data["version"] != PICKLE_VERSION:
            dmsg("WARNING","old dump file, not loaded")
            return False
        andpath = abspath(normpath(data["path"]))
        anspath = abspath(normpath(self.path))
        if andpath != anspath:
            if not ask("Warning","path mismatch!\n" + \
                       "curr:" + str(anspath) + "\n" + \
                       "load:" + str(andpath) + "\n" + \
                       "use anyway?"):
                return False
        self.wa.clear()
        for box in data["workarea"]:
            self.wa.add(box)
        self.wa.generate(self.col.bands)

        #self.home = data["home"]
        att = data["att"]
        self.att0.clr_table
        for a in sorted(list(att.keys())):
            self.att0.add_att(a)
        self.att = {a : AD.unpack(a,att[a],self.viewer,data["workarea"]) for a in att}
        if 99 not in att:
            self.att0.add_att(99)
            self.att[99] = AD(self.viewer,self.width,self.height,99,self.att0._color[99])
        return True

    @logarg
    def file_open(self,path=False,nocancel=False):
        # PATH
        if not path:
            qget = QFileDialog.getOpenFileName
            if nocancel:
                path = ""
                while not path:
                    path = qget(self, 'Open file', '81', "GeoTIFF files (*.tif)")[0]
            else:
                path = qget(self, 'Open file', '81', "GeoTIFF files (*.tif)")[0]
                if not path:
                    return
        self.path = path
        self.hlog(["file_open",path])

        # GEO
        self.ll = geotrans(path)
        self.rr = rgeotrans(path)

        # IMAGE
        image = Image.open(path)
        self.col = Color(image)
        self.width,self.height = image.size
        self.image = image.toqimage()
        self.qimage = QImage(self.image)

        # GUI
        self.att = {}
        self.info.reset()
        self.newImage.emit(path,self.width,self.height)
        self.viewer.setImage(self.qimage)

        self.edit.add("FILE: open " + path)
        self.home = self.viewer.sceneRect()
        self.wa.clear()
        self.set_mode("view")

    # MODES
    def set_mode(self,mode):
        assert type(mode) == str
        old = self.viewer.mode
        if self.viewer.mode != mode:
            self.viewer.mode = mode
            Mode = mode[:1].upper()+mode[1:]
            getattr(self,"mode" + Mode + "Action").setChecked(True)
            self.info.mode.setText(self.viewer.mode)
            color_label(self.info.mode,MODES[self.viewer.mode][0])
            if mode == "work":
                self.work.show.setChecked(True)
                self.wa.set_visibility(True)
            if old == "work":
                self.work.show.setChecked(False)
                self.wa.set_visibility(False)

    def create_actions(self):
        def ca(text,slot=None,short=None,tip=None,check=False):
            action = QAction(text, self)
            if short is not None:
                action.setShortcut(short)
            if tip is not None:
                action.setToolTip(tip)
                action.setStatusTip(tip)
            if slot is not None:
                action.triggered.connect(slot)
            if check:
                action.setCheckable(True)
            return action

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        modeMenu = menubar.addMenu('&Mode')

        # FILE ACTIONS
        fileMenu.addAction(ca("E&xit", self.save_exit,"Ctrl+X","exit program"))
        fileMenu.addAction(ca("&Quit", self.close,"Ctrl+Q","quit program"))
        fileMenu.addAction(ca("&Open", self.file_open,"Ctrl+O","geotiff open"))
        fileMenu.addAction(ca("&Load", self.file_load, "Ctrl+L","load psets"))
        fileMenu.addAction(ca("&Dump", self.file_dump, "Ctrl+D","dump psets"))
        fileMenu.addAction(ca("&Save", self.file_save, "Ctrl+S","shp save"))
        fileMenu.addAction(ca("&Read", self.file_read, "Ctrl+R","shp read"))

        #act = {}
        self.ag = QActionGroup(self)
        for mode in sorted(MODES.keys()):
            c,tip = MODES[mode]
            name = mode[:1].upper()+mode[1:]
            M = "Ctrl+"+(name[0] if name[0] != "P" else "T")
            action = ca("&"+name,partial(self.set_mode,mode),M,tip,True)
            setattr(self,"mode"+name+"Action",action)
            self.ag.addAction(action)
            self.toolbar.addAction(action)
            modeMenu.addAction(action)
        self.ag.setExclusive(True)


if __name__ == '__main__':
    argv = sys.argv
    app = QApplication(argv)
    print("SYS.ARGV",argv)
    if len(sys.argv) >= 2:
        hmap = HMap(path=argv[1],
                    load="-l" in argv,
                    work="-w" in argv,
                    size=5 if "-5" in argv else \
                    (7 if "-7" in argv else 0))
    else:
        hmap = HMap()
    hmap.show()
    app.exec_()
