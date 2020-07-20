# -*- coding: utf-8 -*-
import sys
import os
import qtpy
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
import qtawesome as qta
import math

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:

    def _fromUtf8(s):
        return s


# Avoid error and crash in qt5
if qtpy.PYQT5:
    import cgitb

    cgitb.enable(format="text")


class TablePageBottomStatus(QtWidgets.QWidget):
    # Set page widget for table
    RecordQuerySig = QtCore.Signal(int, int)
    # Number of data per page
    PageRecordCountSig = QtCore.Signal(int)
    # Change mode of selecting data
    SelectedModelSig = QtCore.Signal(str)
    # Change font sizes
    fontSizeSig = QtCore.Signal(str)
    # Adjust width automatically
    columnsWidthSig = QtCore.Signal()
    # Adjust height automatically
    rowsWidthSig = QtCore.Signal()

    def __init__(
        self,
        parent=None,
        PageRecordList=[100, 200, 500, 1000, 5000],
        datashape=(0, 0),
        iconcolor="#87CEFA",
        iconSize=QtCore.QSize(24, 24),
    ):
        super(TablePageBottomStatus, self).__init__(parent)
        # Current page with default 0
        self.currentPage = 1
        # Data per page with default 10000
        self.PageRecordCount = PageRecordList[0]

        self.totalRecrodRows = datashape[0]
        self.totalRecrodCols = datashape[1]

        self.buttonstyle = "QPushButton#page_btn{background:transparent;border:0px;}"
        self.buttonstyle2 = """QPushButton#page_btn{color: silver;
    background-color: QLinearGradient( x1: 0, y1: 1, x2: 0, y2: 0,
    stop: 0 #231e1f, stop: 1 #484846);
    border-width: 0px;}"""
        # Number of pages with default 0
        self.totalPageCount = max(
            math.ceil(float(self.totalRecrodRows) / self.PageRecordCount), 1
        )

        self.setFixedHeight(iconSize.height())

        totalLayout = QtWidgets.QVBoxLayout(self)
        totalLayout.setSpacing(2)
        totalLayout.setContentsMargins(5, 0, 5, 0)

        statusWidget2 = QtWidgets.QWidget()
        statusWidget2.setFixedHeight(iconSize.height())

        # Set status layout
        statusLayout2 = QtWidgets.QHBoxLayout(statusWidget2)
        statusLayout2.setSpacing(2)
        statusLayout2.setContentsMargins(0, 0, 0, 0)

        label = QtWidgets.QLabel("")
        self.pageNumcombo = QtWidgets.QComboBox()
        self.pageNumcombo.insertItems(0, [str(p) for p in PageRecordList])
        self.totalRecrodLabel = QtWidgets.QLabel()

        self.currentPageLabel = QtWidgets.QLabel()

        backward = qta.icon("fa.backward", color=iconcolor, color_active=iconcolor)

        self.firstButton = QtWidgets.QPushButton(backward, "")
        self.firstButton.setFixedSize(iconSize)
        self.firstButton.setObjectName("page_btn")
        self.firstButton.setStyleSheet(self.buttonstyle)
        self.firstButton.setToolTip("backward")
        self.firstButton.setCursor(QtCore.Qt.ArrowCursor)

        step_backward = qta.icon(
            "fa.step-backward", color=iconcolor, color_active=iconcolor
        )

        self.prevButton = QtWidgets.QPushButton(step_backward, "")
        self.prevButton.setFixedSize(iconSize)
        self.prevButton.setObjectName("page_btn")
        self.prevButton.setStyleSheet(self.buttonstyle)
        self.prevButton.setToolTip("step-backward")
        self.prevButton.setCursor(QtCore.Qt.ArrowCursor)

        step_forward = qta.icon(
            "fa.step-forward", color=iconcolor, color_active=iconcolor
        )

        self.nextButton = QtWidgets.QPushButton(step_forward, "")
        self.nextButton.setFixedSize(iconSize)
        self.nextButton.setObjectName("page_btn")
        self.nextButton.setStyleSheet(self.buttonstyle)
        self.nextButton.setToolTip("step-forward")
        self.nextButton.setCursor(QtCore.Qt.ArrowCursor)

        forward = qta.icon("fa.forward", color=iconcolor, color_active=iconcolor)

        self.lastButton = QtWidgets.QPushButton(forward, "")
        self.lastButton.setFixedSize(iconSize)
        self.lastButton.setObjectName("page_btn")
        self.lastButton.setStyleSheet(self.buttonstyle)
        self.lastButton.setToolTip("forward")
        self.lastButton.setCursor(QtCore.Qt.ArrowCursor)

        step_to = qta.icon("fa.paper-plane", color=iconcolor, color_active=iconcolor)

        self.switchPageButton = QtWidgets.QPushButton(step_to, "")
        self.switchPageButton.setFixedSize(iconSize)
        self.switchPageButton.setObjectName("page_btn")
        self.switchPageButton.setStyleSheet(self.buttonstyle)
        self.switchPageLineEdit = QtWidgets.QLineEdit()
        self.switchPageLineEdit.setFixedWidth(40)
        self.switchPage = QtWidgets.QLabel(u" to")
        self.page = QtWidgets.QLabel(u"")

        statusLayout2.addWidget(label)
        statusLayout2.addWidget(self.pageNumcombo)
        statusLayout2.addWidget(self.totalRecrodLabel)

        statusLayout2.addWidget(self.currentPageLabel)
        statusLayout2.addWidget(QtWidgets.QSplitter())
        statusLayout2.addSpacerItem(
            QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
            )
        )
        statusLayout2.addWidget(self.firstButton)
        statusLayout2.addWidget(self.prevButton)
        statusLayout2.addWidget(self.nextButton)
        statusLayout2.addWidget(self.lastButton)
        statusLayout2.addWidget(self.switchPage)
        statusLayout2.addWidget(self.switchPageLineEdit)
        statusLayout2.addWidget(self.page)
        statusLayout2.addWidget(self.switchPageButton)

        totalLayout.addWidget(statusWidget2)

        self.prevButton.clicked.connect(self.OnPrevButtonClick)
        self.nextButton.clicked.connect(self.OnNextButtonClick)
        self.firstButton.clicked.connect(self.OnFirstButtonClick)
        self.lastButton.clicked.connect(self.OnLastButtonClick)
        self.switchPageButton.clicked.connect(self.OnSwitchPageButtonClick)
        self.pageNumcombo.currentIndexChanged.connect(self.setLimitPerPage)

        self.SetTotalPageLabel()
        self.UpdateStatus()

    def btnGroupState(self, num):
        buttons = self.GroupBtn.buttons()
        for btn in buttons:
            if btn != num:
                btn.setStyleSheet(self.buttonstyle)
                btn.setChecked(False)
            else:
                btn.setStyleSheet(self.buttonstyle2)
                btn.setChecked(True)

    # Set data per page
    def setLimitPerPage(self, index):
        self.PageRecordCount = int(self.pageNumcombo.currentText())
        # Number of pages with default 0
        self.totalPageCount = max(
            math.ceil(float(self.totalRecrodRows) / self.PageRecordCount), 1
        )
        self.PageRecordCountSig.emit(self.PageRecordCount)
        self.SetTotalPageLabel()
        self.UpdateStatus()
        self.OnSwitchPage(1)

    # Set number of pages
    def setTotalShape(self, totalShape):
        self.currentPage = 1
        self.totalRecrodRows = totalShape[0]
        self.totalRecrodCols = totalShape[1]
        # Number of pages with default 0
        self.totalPageCount = max(
            math.ceil(float(self.totalRecrodRows) / self.PageRecordCount), 1
        )
        self.SetTotalPageLabel()
        self.UpdateStatus()

    # Go to first page
    def OnFirstButtonClick(self):
        self.OnSwitchPage(1)

    # Go to last page
    def OnLastButtonClick(self):
        self.OnSwitchPage(self.totalPageCount)

    # Go to previous page
    def OnPrevButtonClick(self):
        limitIndex = (self.currentPage - 2) * self.PageRecordCount
        self.RecordQuerySig.emit(limitIndex, limitIndex + self.PageRecordCount)
        self.currentPage = self.currentPage - 1
        self.UpdateStatus()

    # Go to next page
    def OnNextButtonClick(self):
        limitIndex = self.currentPage * self.PageRecordCount
        self.RecordQuerySig.emit(limitIndex, limitIndex + self.PageRecordCount)
        self.currentPage = self.currentPage + 1
        self.UpdateStatus()

    # Go to specific page
    def OnSwitchPageButtonClick(self):

        # Input page number
        szText = self.switchPageLineEdit.text()
        if szText != "":
            # Pattern of a number
            regExp = QtCore.QRegExp(u"-?[0-9]*")
            # Validate a number
            if not regExp.exactMatch(szText):
                QtWidgets.QMessageBox.information(self, u"Info", u"input number")
                return
        else:
            QtWidgets.QMessageBox.information(self, u"info", u"input page number")
            return
        # Get page number
        pageIndex = int(szText)
        # Validate existence of page
        if pageIndex > self.totalPageCount or pageIndex < 1:
            QMessageBox.information(self, u"info", u"page error")
            self.switchPageLineEdit.setText("")
            return
        self.OnSwitchPage(pageIndex)

    def OnSwitchPage(self, pageIndex):
        # Get initial page number
        limitIndex = (pageIndex - 1) * self.PageRecordCount
        # Check records
        self.RecordQuerySig.emit(limitIndex, limitIndex + self.PageRecordCount)
        # Set current page
        self.currentPage = pageIndex
        # Update status
        self.UpdateStatus()

    def SetTotalPageLabel(self):
        self.totalRecrodLabel.setText(
            u" %s*%s " % (int(self.totalRecrodRows), int(self.totalRecrodCols))
        )

    def UpdateStatus(self):
        # Set current text
        self.currentPageLabel.setText(
            u"%s/%s" % (int(self.currentPage), int(self.totalPageCount))
        )
        # Validate applicable button
        if self.totalPageCount == 0 or self.totalPageCount == 1:
            self.firstButton.setEnabled(False)
            self.lastButton.setEnabled(False)
            self.nextButton.setEnabled(False)
            self.prevButton.setEnabled(False)
            self.switchPageLineEdit.setEnabled(False)
            self.switchPageButton.setEnabled(False)
        else:
            self.switchPageLineEdit.setEnabled(True)
            self.switchPageButton.setEnabled(True)

        if self.currentPage == self.totalPageCount:
            self.nextButton.setEnabled(False)
            self.firstButton.setEnabled(True)
            self.lastButton.setEnabled(False)
            if self.currentPage == 1 or self.currentPage == 0:
                self.prevButton.setEnabled(False)
                self.firstButton.setEnabled(False)
            else:
                self.prevButton.setEnabled(True)
        elif self.currentPage < self.totalPageCount:
            self.nextButton.setEnabled(True)
            self.firstButton.setEnabled(True)
            self.lastButton.setEnabled(True)
            if self.currentPage == 1 or self.currentPage == 0:
                self.prevButton.setEnabled(False)
                self.firstButton.setEnabled(False)
            else:
                self.prevButton.setEnabled(True)
