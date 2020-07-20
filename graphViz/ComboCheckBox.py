# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QComboBox,
    QLineEdit,
    QListWidget,
    QCheckBox,
    QListWidgetItem,
)
import copy
from SearchWidget import SearchWidget


class ComboCheckBox(QComboBox):
    def __init__(self):
        super(ComboCheckBox, self).__init__()
        self.setObjectName("QComboWidget")
        self.setStyleSheet("QComboBox#QComboWidget{min-width: 120px;}")

    def addItems(self, items):
        self.items = copy.deepcopy(items)
        self.items.insert(0, "Selected All")
        self.row_num = len(self.items)

        self.Selectedrow_num = 0
        self.qCheckBox = []
        self.qLineEdit = QLineEdit()
        self.qLineEdit.setStyleSheet("QLineEdit{border:0px;}")
        self.qLineEdit.setReadOnly(True)
        self.setFixedWidth(300)

        self.qListWidget = QListWidget(self)

        self.searchWidget = SearchWidget()
        self.searchWidget.sendSearchSig.connect(self.on_textChanged)
        qItem = QListWidgetItem(self.qListWidget)
        qItem.setSizeHint(QSize(280, 30))
        self.qListWidget.setItemWidget(qItem, self.searchWidget)

        self.addQCheckBox(0)
        self.qCheckBox[0].stateChanged.connect(self.All)
        for i in range(1, self.row_num):
            self.addQCheckBox(i)
            self.qCheckBox[i].stateChanged.connect(self.show)

        self.setLineEdit(self.qLineEdit)
        self.setModel(self.qListWidget.model())
        self.setView(self.qListWidget)
        self.setFixedHeight(30)
        self.qCheckBox[0].setCheckState(1)

    def addQCheckBox(self, i):
        self.qCheckBox.append(QCheckBox())
        qItem = QListWidgetItem(self.qListWidget)
        qItem.setSizeHint(QSize(190, 20))
        self.qCheckBox[i].setText(self.items[i])
        self.qListWidget.setItemWidget(qItem, self.qCheckBox[i])

    def Selectlist(self):
        Outputlist = []
        for i in range(1, self.row_num):
            if self.qCheckBox[i].isChecked() == True:
                Outputlist.append(self.qCheckBox[i].text())

        self.Selectedrow_num = len(Outputlist)
        return Outputlist

    def hidePopup(self):
        self.qListWidget.scrollToTop()
        super().hidePopup()

    def showPopup(self):
        super().showPopup()
        self.qListWidget.scrollToTop()

    def show(self):
        show = ""
        self.Outputlist = self.Selectlist()

        self.qLineEdit.setReadOnly(False)
        self.qLineEdit.clear()
        for i in self.Outputlist:
            show += i + ";"
        if self.Selectedrow_num == 0:
            self.qCheckBox[0].setCheckState(0)
        elif self.Selectedrow_num == self.row_num - 1:
            self.qCheckBox[0].setCheckState(2)
        else:
            self.qCheckBox[0].setCheckState(1)

        self.qLineEdit.setText("%d Items Selected" % (len(self.Outputlist)))
        self.qLineEdit.setReadOnly(True)

    def All(self, status):
        if status == 2:
            for i in range(1, self.row_num):
                self.qCheckBox[i].setChecked(True)
        elif status == 1:
            if self.Selectedrow_num == 0:
                self.qCheckBox[0].setCheckState(2)
        elif status == 0:
            self.clear()
        self.Outputlist = self.Selectlist()

    def clear(self):
        for i in range(self.row_num):
            self.qCheckBox[i].setChecked(False)

    def on_textChanged(self, text):
        for row in range(2, self.qListWidget.count()):
            it = self.qListWidget.item(row)
            widget = self.qListWidget.itemWidget(it)
            if text:
                it.setHidden(not self.filter(text.lower(), widget.text().lower()))
            else:
                it.setHidden(False)

    def filter(self, text, keywords):
        return text in keywords
