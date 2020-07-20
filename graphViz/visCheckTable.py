import sys
from qtpy.QtWidgets import (
    QApplication,
    QHeaderView,
    QStyle,
    QStyleOptionButton,
    QTableView,
    QWidget,
    QVBoxLayout,
    QAbstractItemView,
)
from qtpy.QtCore import (
    QRegExp,
    Signal,
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QRect,
    QVariant,
    QEvent,
    QSortFilterProxyModel,
)
from SearchWidget import SearchWidget
import cgitb

cgitb.enable(format="text")


class CheckBoxHeader(QHeaderView):
    clicked = Signal(bool)

    _x_offset = 3
    _y_offset = 0
    _width = 20
    _height = 20

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super(CheckBoxHeader, self).__init__(orientation, parent)
        self.isOn = True
        self.setHighlightSections(False)
        self.setMouseTracking(True)
        self.setSectionsClickable(True)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super(CheckBoxHeader, self).paintSection(painter, rect, logicalIndex)
        painter.restore()

        self._y_offset = int((rect.height() - self._width) / 2.0)

        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(
                rect.x() + self._x_offset,
                rect.y() + self._y_offset,
                self._width,
                self._height,
            )
            option.state = QStyle.State_Enabled | QStyle.State_Active
            if self.isOn:
                option.state |= QStyle.State_On
            else:
                option.state |= QStyle.State_Off
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)

    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if 0 == index:
            x = self.sectionPosition(index)
            if (
                x + self._x_offset < event.pos().x() < x + self._x_offset + self._width
                and self._y_offset < event.pos().y() < self._y_offset + self._height
            ):
                if self.isOn:
                    self.isOn = False
                else:
                    self.isOn = True
                self.clicked.emit(self.isOn)
                self.update()
        super(CheckBoxHeader, self).mousePressEvent(event)

    def headerClick(self, state):
        self.isOn = state
        self.updateSection(0)


class MyModel(QAbstractTableModel):
    clicked = Signal(bool)
    sendData = Signal(list)

    def __init__(self, data, HEADERS, parent=None):
        super(MyModel, self).__init__(parent)
        # Keep track of which object are checked
        self._data = data
        self.checkList = [1] * len(self._data)
        self.headers = HEADERS

    def updateData(self, data):
        self.beginResetModel()
        self._data = data
        self.checkList = [1] * len(self._data)
        self.endResetModel()

    def rowCount(self, QModelIndex):
        return len(self._data)

    def columnCount(self, QModelIndex):
        return len(self.headers)

    def data(self, index, role):
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole:
            value = self._data[index.row()][index.column()]
            return value
        elif role == Qt.CheckStateRole:
            if col == 0:
                return Qt.Checked if self.checkList[row] == 1 else Qt.Unchecked
        elif role == Qt.ToolTipRole:
            if col == 0:
                return self.checkList[row]
        return QVariant()

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()
        if role == Qt.CheckStateRole and col == 0:
            self.checkList[row] = 1 if value == Qt.Checked else 0
            if [1] * len(self._data) == self.checkList:
                self.clicked.emit(True)
            else:
                self.clicked.emit(False)
            sdata = [d[0] for d, c in zip(self._data, self.checkList) if c]
            self.sendData.emit(sdata)
        return True

    def flags(self, index):
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        return Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            d = 0
            for i in self.checkList:
                d = d + i
            return self.headers[section] + "[%d Selected]" % d
        return int(section + 1)

    def headerClick(self, isOn):
        self.beginResetModel()
        if isOn:
            self.checkList = [1] * len(self._data)
        else:
            self.checkList = [0] * len(self._data)
        self.endResetModel()
        sdata = [d[0] for d, c in zip(self._data, self.checkList) if c]
        self.sendData.emit(sdata)


class CheckTable(QWidget):
    sendData = Signal(list)

    def __init__(self, parent=None):
        super(CheckTable, self).__init__(parent)
        totalLayout = QVBoxLayout(self)
        totalLayout.setSpacing(0)
        totalLayout.setContentsMargins(0, 0, 0, 0)

        self.searchWidget = SearchWidget()
        self.searchWidget.sendSearchSig.connect(self.serachTable)
        self.tableView = QTableView()
        self.header = CheckBoxHeader()
        self.tableView.setHorizontalHeader(self.header)
        self.tableView.resizeColumnsToContents()
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        totalLayout.addWidget(self.searchWidget)
        totalLayout.addWidget(self.tableView)

    def initData(self, headerList, data):
        self.data = data
        self.data.sort(key=lambda x: str(x[0]))
        self.headerList = headerList
        self.myModel = MyModel(data, headerList)
        self.proxyModelContact = QSortFilterProxyModel(self)
        self.proxyModelContact.setSourceModel(self.myModel)
        self.tableView.setModel(self.proxyModelContact)
        self.header.clicked.connect(self.myModel.headerClick)
        self.myModel.clicked.connect(self.header.headerClick)
        self.myModel.sendData.connect(self.sendData.emit)

    def serachTable(self, text):
        rx = QRegExp(str(text), Qt.CaseInsensitive)
        self.proxyModelContact.setFilterRegExp(rx)
