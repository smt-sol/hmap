import sys
from math import ceil,floor

from PyQt5.QtWidgets import QGraphicsView,QGraphicsScene
from PyQt5.QtGui import QImage,QPixmap
from PyQt5.QtCore import Qt,QRectF,QRect,pyqtSignal

from iset import Box

class ImageViewer(QGraphicsView):
    selLoc = pyqtSignal(str)
    selBox = pyqtSignal(str)

    zoomChanged = pyqtSignal()
    viewChanged = pyqtSignal()
    mouseMoveLoc = pyqtSignal(int,int)
    mousePressLoc = pyqtSignal(int,int)
    mouseReleaseLoc = pyqtSignal(int,int)
    genKeyX = pyqtSignal(str)

    def __init__(self):
        QGraphicsView.__init__(self)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.color = None
        self.loc = None
        self._pixmapHandle = None
        self.aspectRatioMode = Qt.KeepAspectRatio
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        self.mode = ""
        self.wabbox = None

    def hasImage(self):
        return self._pixmapHandle is not None

    def clearImage(self):
        if self.hasImage():
            self.scene.removeItem(self._pixmapHandle)
            self._pixmapHandle = None

    def pixmap(self):
        if self.hasImage():
            return self._pixmapHandle.pixmap()
        return None

    def image(self):
        if self.hasImage():
            return self._pixmapHandle.pixmap().toImage()
        return None

    def setImage(self, image):
        if type(image) is QPixmap:
            pixmap = image
        elif type(image) is QImage:
            pixmap = QPixmap.fromImage(image)
        else:
            raise RuntimeError("ImageViewer.setImage: Argument must be a QImage or QPixmap.")
        if self.hasImage():
            self._pixmapHandle.setPixmap(pixmap)
        else:
            self._pixmapHandle = self.scene.addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))  # Set scene size to image size.
        self.zoomChanged.emit()

    def fitWindow(self,r=None):
        print("FW",r)
        self.resetTransform()
        if r is None:
            r = self.sceneRect()
        self.fitInView(r, self.aspectRatioMode)
        self.fixWindow()
        self.zoomChanged.emit()

    def getBoxRgb(self,img):
        r = img.copy(self.box)
        colors = set()
        for i in range(r.width()):
            for j in range(r.height()):
                c = r.pixelColor(i,j)
                colors.add((c.getRgb()[:3]))
        return colors

    def fixWindow(self):
        q = self.maxFactor()
        if q < 1.0:
            self.scale(q,q)
            self.zoomChanged.emit()

    def maxFactor(self):
        t = self.transform()
        s = self.image().size()
        m = max(t.m11(),t.m12())
        if t.m12() != 0.0:
            m *= 1.5
        m1 = max(1,m * s.width())
        m2 = max(1,m * s.height())
        return 65534.8/(max(m1,m2))

    def scaleCheck(self,factor):
        if factor == 0:
            self.fitWindow()
        elif factor != 1.0:
            q = self.maxFactor()
            if factor > q:
                factor = q
            self.scale(factor,factor)
            self.zoomChanged.emit()



    def getVisible(self):
        V = self.viewport().rect()
        R = self.mapToScene(V).boundingRect()
        return tuple(int(round(x)) for x in (R.left(),R.right(),R.top(),R.bottom()))

    def getVBox(self):
        x0,x1,y0,y1 = self.getVisible()
        return Box(x0,y0,x1=x1,y1=y1)

           
    def keyPressEvent(self,event):
        QGraphicsView.keyPressEvent(self, event)
        if event.key() == Qt.Key_Home or\
           event.key() == Qt.Key_H:
            self.fitWindow()
        elif event.key() == Qt.Key_W or\
             event.key() == Qt.Key_Space:
            if self.wabbox is None:
                self.fitWindow()
            else:
                b = self.wabbox
                self.fitWindow(QRectF(b.x0,b.y0,b.dx,b.dy))
        elif event.key() == Qt.Key_Plus:
            self.scaleCheck(1.25)
        elif event.key() == Qt.Key_Minus:
            self.scaleCheck(0.8)
        elif event.key() == Qt.Key_Slash:
            self.rotate(22.5)
            self.fixWindow()
        elif event.key() == Qt.Key_Backslash:
            self.rotate(-22.5)
            self.fixWindow()

    def wheelEvent(self,event):
        if event.modifiers() & Qt.ShiftModifier:
            pt = event.angleDelta()
            q = 1.25 ** (pt.y()/360)
            self.scaleCheck(q)
        else:
            QGraphicsView.wheelEvent(self, event)

    def mouseMoveEvent(self, event):
        QGraphicsView.mouseMoveEvent(self, event)
        scenePos = self.mapToScene(event.pos())
        self.mouseMoveLoc.emit(scenePos.x(), scenePos.y())

    def mousePressEvent(self, event):
        scenePos = self.mapToScene(event.pos())
        self.mousePressLoc.emit(scenePos.x(), scenePos.y())
        self.press = scenePos.toPoint()
        if event.button() == Qt.LeftButton:
            self.loc = scenePos.toPoint()
            if self.mode == "view":
                self.setDragMode(QGraphicsView.ScrollHandDrag)
            else:
                self.selLoc.emit(self.mode)
        elif event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        QGraphicsView.mouseReleaseEvent(self, event)
        scenePos = self.mapToScene(event.pos())
        self.mouseReleaseLoc.emit(scenePos.x(), scenePos.y())
        self.release = scenePos.toPoint()
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
        elif event.button() == Qt.RightButton:
            r = self.sceneRect()
            a = self.scene.selectionArea()
            box = a.boundingRect().intersected(r)
            rl = int(floor(box.left()))
            rr = int(ceil(box.right()))
            rt = int(floor(box.top()))
            rb = int(ceil(box.bottom()))
            self.box = QRect(rl,rt,rr-rl,rb-rt)
            self.boxf = box

            if self.mode == "view":
                self.fitWindow(self.boxf)
            else:
                self.selBox.emit(self.mode)
            self.setDragMode(QGraphicsView.NoDrag)

    def mouseDoubleClickEvent(self, event):
        QGraphicsView.mouseDoubleClickEvent(self, event)
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            self.centerOn(scenePos.x(), scenePos.y())
        if event.button() == Qt.RightButton:
            self.fitWindow()
