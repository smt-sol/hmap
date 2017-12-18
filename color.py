from random import randint as ri

import numpy as np
from skimage.filters import gaussian,sobel,threshold_adaptive,threshold_li


from PIL import Image

from PyQt5.QtWidgets import QMessageBox,QColorDialog
from PyQt5.QtGui import QColor

def get_color(forbidden=None,auto=False):
    if forbidden is None: forbidden = set()
    def autocolor():
        a = ri(0,4)
        b = ri(0,4)
        c = ri(0,4)
        x = ri(0,5)
        if x == 0:
            a += 8
            b += 4
        elif x == 1:
            a += 4
            b += 8
        elif x == 2:
            a += 8
            c += 4
        elif x == 3:
            a += 4
            c += 8
        elif x == 4:
            b += 8
            c += 4
        elif x == 5:
            b += 4
            c += 8
        return QColor(20*a+ri(0,15),20*b+ri(0,15),20*c+ri(0,15))

    if auto:
        col = autocolor()
    else:
        col = QColorDialog().getColor()
        if not col.isValid():
            return None

    rgb = col.getRgb()[:3]
    count = 3
    while rgb in forbidden and (auto or count > 0):
        count -= 1
        if auto:
            col = autocolor()
        else:
            QMessageBox.warning(None,"X", "Color exist: try again")
            col = QColorDialog().getColor()
            if not col.isValid():
                return None
        rgb = col.getRgb()[:3]
    return col



def color_label(label,bg,fg=None):
    label.setAutoFillBackground(True)
    bgvalues = "{r}, {g}, {b}, {a}".format(r = bg.red(),g = bg.green(),
                                           b = bg.blue(),a = 255)
    if fg is None:
        styleSheet = "QLabel { background-color: rgba(" + bgvalues + ");padding: 6px;max-width:12em;}"
    else:
        fgvalues = "{r}, {g}, {b}, {a}".format(r = fg.red(),g = fg.green(),
                                               b = fg.blue(),a = 255)
        styleSheet = "QLabel { background-color: rgba(" + bgvalues +\
                     ");color: rgba(" + fgvalues + ");padding: 6px;max-width: 12em;}"

    label.setStyleSheet(styleSheet)

def color_button(button,color):
    button.setAutoFillBackground(True)
    values = "{r}, {g}, {b}, {a}".format(r = color.red(),g = color.green(),
                                         b = color.blue(),a = 255)
    styleSheet = "QPushButton { background-color: rgba(" + values + "); }"
    button.setStyleSheet(styleSheet)

def get_color_parameters(col,scheme):
    if scheme == "hsv":
        ret = col.getHsv()
    elif scheme == "hs":
        ret = col.getHsv()[:2] + (0,)
    elif scheme == "h":
        ret = col.getHsv()[:1] + (0,0)
    elif scheme == "hsl":
        ret = col.getHsl()
    elif scheme == "hs2":
        ret = col.getHsl()[:2] + (0,)
    elif scheme == "rgb":
        ret = col.getRgb()
    else:
        raise ValueError
    return ret

def closer_color(p,p1,p2,scheme):
    if scheme == "s":
        hsv = p.getHsv()
        return 0 if hsv[1] > p1[1]/2 else 1

    if scheme == "hsv":
        hsv = p.getHsv()
        d1 = (p1[0]-hsv[0],p1[1]-hsv[1],p1[2]-hsv[2])
        d2 = (p2[0]-hsv[0],p2[1]-hsv[1],p2[2]-hsv[2])
    elif scheme == "hs":
        hsv = p.getHsv()
        d1 = (p1[0]-hsv[0],p1[1]-hsv[1])
        d2 = (p2[0]-hsv[0],p2[1]-hsv[1])
    elif scheme == "h":
        hsv = p.getHsv()
        d1 = (p1[0]-hsv[0],)
        d2 = (p2[0]-hsv[0],)
    elif scheme == "hsl":
        hsl = p.getHsl()
        d1 = (p1[4]-hsl[0],p1[5]-hsl[1],p1[6]-hsl[2])
        d2 = (p2[4]-hsl[0],p2[5]-hsl[1],p2[6]-hsl[2])
    elif scheme == "hs2":
        hsl = p.getHsl()
        d1 = (p1[4]-hsl[0],p1[5]-hsl[1])
        d2 = (p2[4]-hsl[0],p2[5]-hsl[1])
    elif scheme == "rgb":
        rgb = p.getRgb()
        d1 = (p1[8]-rgb[0],p1[9]-rgb[1],p1[10]-rgb[2])
        d2 = (p2[8]-rgb[0],p2[9]-rgb[1],p2[10]-rgb[2])
    else:
        raise ValueError

    s1 = sum((x*x for x in d1))
    s2 = sum((x*x for x in d2))
    return 0 if s1 <= s2 else 1


class Color:
    def __init__(self,image):
        self.width,self.height = image.size
        self.rgb = np.array(image)
        self.hsv = np.array(image.convert("HSV"))
        print("rgb shape",self.rgb.shape)
        print("hsv shape",self.hsv.shape)
        self.bands = {}
        self.bands["r"] = self.rgb[:,:,0].transpose()
        self.bands["g"] = self.rgb[:,:,1].transpose()
        self.bands["b"] = self.rgb[:,:,2].transpose()
        self.bands["h"] = self.hsv[:,:,0].transpose()
        self.bands["s"] = self.hsv[:,:,1].transpose()
        self.bands["v"] = self.hsv[:,:,2].transpose()
        self.backup = {k:np.array(a) for k,a in self.bands.items()}

    def gauss(self,sigma,scheme,box):
        assert scheme in ("rgb",)
        x0,x1,y0,y1 = box.xy()
        x0 = max(0,x0)
        y0 = max(0,y0)
        x1 = min(self.width,x1)
        y1 = min(self.height,y1)

        for c in scheme:
            self.bands[c][x0:x1,y0:y1] = gaussian(self.bands[c].astype(np.float64)[x0:x1,y0:y1],sigma).astype(np.uint8)
        for x in range(x0,x1):
            for y in range(y0,y1):
                c = QColor(self.bands["r"][x,y],self.bands["g"][x,y],self.bands["b"][x,y])
                self.bands["h"][x,y],self.bands["s"][x,y],self.bands["v"][x,y] = c.hsvHue(),c.hsvSaturation(),c.value()


        ny,nx = self.bands["r"].shape
        s = (nx,ny,3)
        rgb = np.zeros(s,dtype=np.uint8)
        rgb[:,:,0] = self.bands["r"].transpose()
        rgb[:,:,1] = self.bands["g"].transpose()
        rgb[:,:,2] = self.bands["b"].transpose()
        img = Image.fromarray(rgb)
        return img

    def threshold(self,sigma,blocksize,box):
        x0,x1,y0,y1 = box.xy()
        for c in "rgb":
            self.bands[c][x0:x1,y0:y1] = threshold_adaptive(self.bands[c][x0:x1,y0:y1],block_size=blocksize,param=sigma).astype(np.uint8)
        ny,nx = self.bands["r"].shape
        s = (nx,ny,3)
        rgb = np.zeros(s,dtype=np.uint8)
        rgb[:,:,0] = self.bands["r"].transpose()
        rgb[:,:,1] = self.bands["g"].transpose()
        rgb[:,:,2] = self.bands["b"].transpose()
        img = Image.fromarray(rgb)
        return img

    def sobel(self,box):
        x0,x1,y0,y1 = box.xy()
        for c in "rgb":
            self.bands[c][x0:x1,y0:y1] = sobel(self.bands[c].astype(np.float64)[x0:x1,y0:y1]).astype(np.uint8)
        ny,nx = self.bands["r"].shape
        s = (nx,ny,3)
        rgb = np.zeros(s,dtype=np.uint8)
        rgb[:,:,0] = self.bands["r"].transpose()
        rgb[:,:,1] = self.bands["g"].transpose()
        rgb[:,:,2] = self.bands["b"].transpose()
        img = Image.fromarray(rgb)
        return img

    def unfilter(self):
        for k in self.backup:
            self.bands[k] = np.array(self.backup[k])
        ny,nx = self.bands["r"].shape
        s = (nx,ny,3)
        rgb = np.zeros(s,dtype=np.uint8)
        rgb[:,:,0] = self.bands["r"].transpose()
        rgb[:,:,1] = self.bands["g"].transpose()
        rgb[:,:,2] = self.bands["b"].transpose()
        img = Image.fromarray(rgb)
        return img




        old = """
    def convert_color(self,col,scheme=None):
        if scheme is None:
            scheme = self.get_color_scheme()
        if type(col) == set:
            if scheme == "rgb":
                ret = {QColor(*c).getRgb()[:3] for c in col}
            elif scheme == "hsv":
                ret = {QColor(*c).getHsv()[:3] for c in col}
            elif scheme == "hs":
                ret = {QColor(*c).getHsv()[:2] for c in col}
        else:
            if scheme == "rgb":
                ret = col.getRgb()[:3]
            elif scheme == "hsv":
                ret = col.getHsv()[:3]
            elif scheme == "hs":
                ret = col.getHsv()[:2]
        return ret

    def color_keys(self):
        "set of available colors (according to scheme)"
        try:
            scheme = self.get_color_scheme()
            if scheme == "rgb":
                return self.hmap.imgcolors
            elif scheme == "hsv":
                return set(self.hmap.hsv2rgb.keys())
            elif scheme == "hs":
                return set(self.hmap.hs2rgb.keys())
        except AttributeError:
            return set()

    def revert_colors(self,cols,scheme = None):
        #CHANGE: make sure only necessary colors are returned
        if scheme is None:
            scheme = self.get_color_scheme()
        new = set()
        keys = self.color_keys()
        if scheme == "rgb":
            new = cols & self.hmap.imgcolors
        elif scheme == "hsv":
            cols &= set(self.hmap.hsv2rgb.keys())
            for x in cols:
                new |= self.hmap.hsv2rgb[x]
        elif scheme == "hs":
            cols &= set(self.hmap.hs2rgb.keys())
            for x in cols:
                new |= self.hmap.hs2rgb[x]
        return new
"""
