import qtpy
from qtpy.QtCore import QObject
import time
from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy.QtWidgets import *
import visQTablePageStatus
import operator
from SearchWidget import SearchWidget
import cgitb

cgitb.enable(format="text")


class TableModel(QAbstractTableModel):
    """
    Table data model in MVC mode
    """

    def __init__(self, data, HEADERS):
        super(TableModel, self).__init__()
        self._data = data
        self.headers = HEADERS

    def updateData(self, data):
        """
        Update table data
        """
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            value = self._data[index.row()][index.column()]
            return value

        if role == Qt.DecorationRole:
            pass

    def rowCount(self, parent=None, *args, **kwargs):
        """
        Number of rows
        """
        return len(self._data)

    def columnCount(self, parent=None, *args, **kwargs):
        """
        Number of columns
        """
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Define title
        """
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headers[section]
        return int(section + 1)

    def sort(self, Ncol, order):
        self.layoutAboutToBeChanged.emit()
        self._data.sort(key=lambda x: str(x[Ncol]))
        if order == Qt.DescendingOrder:
            self._data.reverse()
        self.layoutChanged.emit()


class InfoTableWidget(QWidget):
    dbclickedSig = Signal(str)

    def __init__(self, parent=None, PageRecordList=[100, 200, 500, 1000]):
        super(InfoTableWidget, self).__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.PageRecordList = PageRecordList
        self.PageRecordCount = self.PageRecordList[0]
        self.enabled = False
        self.initUi()

    def initUi(self):
        totalLayout = QVBoxLayout(self)
        totalLayout.setSpacing(0)
        totalLayout.setContentsMargins(0, 0, 0, 0)

        self.searchWidget = SearchWidget()
        self.searchWidget.sendSearchSig.connect(self.serachTable)
        self.tableView = QTableView()
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)  # Select rows
        self.tableView.setEditTriggers(QTableView.NoEditTriggers)  # Not edit
        self.tableView.setSelectionMode(QTableView.SingleSelection)  # Select row
        self.tableView.setAlternatingRowColors(True)
        self.tableView.resizeColumnsToContents()
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableView.setSortingEnabled(True)
        self.pageStatus = visQTablePageStatus.TablePageBottomStatus(
            self, PageRecordList=self.PageRecordList
        )
        totalLayout.addWidget(self.searchWidget)
        totalLayout.addWidget(self.tableView)

        totalLayout.addWidget(self.pageStatus)

        self.pageStatus.RecordQuerySig.connect(self.changePage)
        self.pageStatus.PageRecordCountSig.connect(self.RefreshTable)

        self.tableView.doubleClicked.connect(self.viewClicked)

    def viewClicked(self, clickedIndex):
        row = clickedIndex.row()
        self.dbclickedSig.emit(
            self.data[(self.pageStatus.currentPage - 1) * self.PageRecordCount + row][0]
        )

    def InitTable(self, headerList, data):
        self.data = data
        self.headerList = headerList
        self.data.sort(key=lambda x: str(x[0]))
        self.olddata = self.data.copy()
        self.dataCount = len(data)
        self.pageStatus.setTotalShape(tuple((self.dataCount, len(self.headerList))))
        self.model = TableModel(self.data[: self.PageRecordCount], self.headerList)

        self.tableView.setModel(self.model)

    def serachTable(self, text):
        if text == "":
            self.data = self.olddata
            self.dataCount = len(self.data)
            self.pageStatus.setTotalShape(tuple((self.dataCount, len(self.headerList))))
            self.model = TableModel(self.data[: self.PageRecordCount], self.headerList)

            self.tableView.setModel(self.model)
        else:
            text = text.lower()
            self.data = [d for d in self.olddata if str(d[0]).lower().find(text) >= 0]

            self.dataCount = len(self.data)
            self.pageStatus.setTotalShape(tuple((self.dataCount, len(self.headerList))))
            self.model = TableModel(self.data[: self.PageRecordCount], self.headerList)

            self.tableView.setModel(self.model)

    def RefreshTable(self, PageRecordCount):
        self.PageRecordCount = int(PageRecordCount)
        self.model.updateData(self.data[0 : self.PageRecordCount])

    def changePage(self, begin, limit):
        self.model.updateData(self.data[begin:limit])
