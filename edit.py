from PyQt5.QtWidgets import QLabel,QGridLayout,QPushButton
from PyQt5.QtWidgets import QListWidget,QListWidgetItem
from PyQt5.QtGui import QColor

from color import color_label,color_button
from datetime import datetime as dt

class EditW(QGridLayout):
    def __init__(self,title,n):
        super(EditW,self).__init__()

        self.title = QLabel(title)
        self.title.setMaximumHeight(40)
        if title == title.upper():
            color_label(self.title,QColor("red"),QColor("white"))
        else:
            color_label(self.title,QColor("black"),QColor("white"))
        self.clear = QPushButton("clear")
        self.edits = QListWidget()
        self.edits.setMaximumHeight(24*n)
        self.edits.setAlternatingRowColors(True)
        self.addWidget(self.title,0,0,1,7)
        self.addWidget(self.clear,0,7)
        self.addWidget(self.edits,2,0,1,8)

        self.clear.clicked.connect(self.edits.clear)

    def toggle_visibility(self,hide=False):
        if hide:
            vis = False
        else:
            vis = not self.title.isVisible()
        self.title.setVisible(vis)
        self.clear.setVisible(vis)
        self.edits.setVisible(vis)

    def add(self,msg):
        with open("hmap.elg","a+") as f:
            f.write(str(dt.now()) + ": " + msg+"\n")
        self.edits.insertItem(0,QListWidgetItem(msg))
