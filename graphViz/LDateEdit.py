# -*- coding: utf8 -*-
import qtpy
from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *
import re
import sys
import os
import datetime

sys.path.append(os.path.dirname(os.getcwd()))
if qtpy.PYQT5:
    import cgitb

    cgitb.enable(format="text")


class CheckDataEdit(QWidget):
    dateRangeSig = Signal(list)

    def __init__(self, mysname=None, myename=None, parent=None):
        super(CheckDataEdit, self).__init__(parent)
        hbox = QHBoxLayout()
        hbox.setSpacing(2)
        hbox.setContentsMargins(0, 0, 0, 0)
        self.linklist = []

        if mysname != None:
            self.slabel = QLabel()
            self.slabel.setText(mysname)
        if myename != None:
            self.elabel = QLabel()
            self.elabel.setText(myename)

        self.sdataedit = QDateEdit(self)
        self.edataedit = QDateEdit(self)
        self.sdataedit.setFixedWidth(120)
        self.edataedit.setFixedWidth(120)

        # Set date picker widget
        self.sdataedit.setCalendarPopup(True)
        self.sdataedit.cal = self.sdataedit.calendarWidget()
        self.sdataedit.cal.setFirstDayOfWeek(Qt.Monday)
        self.sdataedit.cal.setGridVisible(True)
        self.sdataedit.setDateTime(QDateTime(2015, 7, 29, 0, 0, 0))

        self.edataedit.setCalendarPopup(True)
        self.edataedit.cal = self.edataedit.calendarWidget()
        self.edataedit.cal.setFirstDayOfWeek(Qt.Monday)
        self.edataedit.cal.setGridVisible(True)
        self.edataedit.setDateTime(QDateTime(2019, 11, 26, 0, 0, 0))

        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)

        if mysname != None:
            hbox.addWidget(self.slabel)
        hbox.addWidget(self.sdataedit)
        if myename != None:
            hbox.addWidget(self.elabel)
        hbox.addWidget(self.edataedit)
        self.sdataedit.dateTimeChanged.connect(self.sgetDataS)
        self.edataedit.dateTimeChanged.connect(self.sgetDataE)

        self.setLayout(hbox)

    def setDateRange(self, dateRange):
        minDate = QDate.fromString(dateRange[0], "yyyy-MM-dd")
        maxDate = QDate.fromString(dateRange[1], "yyyy-MM-dd")

        self.sdataedit.setMinimumDate(minDate)
        self.sdataedit.setMaximumDate(maxDate)
        self.edataedit.setMinimumDate(minDate)
        self.edataedit.setMaximumDate(maxDate)
        self.sdataedit.setDate(minDate)
        self.edataedit.setDate(maxDate)

        startDate = self.sdataedit.date()
        endDate = self.edataedit.date()
        self.linklist = [startDate, endDate]

    def sgetDataS(self):
        startDate = self.sdataedit.date()
        endDate = self.edataedit.date()
        days = startDate.daysTo(endDate)
        if days < 0:
            self.sdataedit.setDate(endDate)
        self.startdate = self.sdataedit.dateTime().toPyDateTime()
        self.enddate = self.edataedit.dateTime().toPyDateTime()
        self.dateRangeSig.emit([startDate, endDate])

    def sgetDataE(self):
        startDate = self.sdataedit.date()
        endDate = self.edataedit.date()
        days = endDate.daysTo(startDate)
        if days > 0:
            self.edataedit.setDate(startDate)
        self.dateRangeSig.emit([startDate, endDate])

    def setDate(self, dateRange):
        minDate = QDate.fromString(dateRange[0], "yyyy-MM-dd")
        maxDate = QDate.fromString(dateRange[1], "yyyy-MM-dd")
        self.sdataedit.setDate(minDate)
        self.edataedit.setDate(maxDate)
