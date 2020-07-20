# -*- coding: utf8 -*-
import sys
import os
import warnings

warnings.filterwarnings("ignore")
# Add system path to use interactive tools
my_path = os.path.join(os.getcwd(), "bin")
if my_path not in sys.path:
    sys.path.append(my_path)

with open("exchanges.ini", "r") as f:
    exchange_nodes = f.read().split("=")[-1]
    exchange_nodes = [x.strip() for x in exchange_nodes.split(",")]

from visGraphHigh import GraphHigh
from visTableWidget import InfoTableWidget
from LDateEdit import CheckDataEdit
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from PyQt5.QtChart import QChart
from visgraph import GraphWork
from visCheckTable import CheckTable
from ZoomLineChart import RectZoomMoveView
from visDoubleRangeSlider import RangeSlider
from ComboCheckBox import ComboCheckBox
import numpy as np
from datetime import datetime
import VisStyle


def init_config():
    settings = QtCore.QSettings("exchanges.ini", QtCore.QSettings.IniFormat)
    settings.setValue("Exchange-Nodes", exchange_nodes)


def get_config():
    settings = QtCore.QSettings("exchanges.ini", QtCore.QSettings.IniFormat)
    Exchange = settings.value("Exchange-Nodes")
    return Exchange


class WorkerThreadSubGraph(QtCore.QThread):
    SendDataSignal = QtCore.Signal(list)
    processSignal = QtCore.Signal(int, str)

    def __init__(self, parent=None):
        super(WorkerThreadSubGraph, self).__init__(parent)
        self.working = True

    def SetData(self, G, work, filter_dic):
        self.G = G
        self.work = work
        self.filter_dic = filter_dic
        self.working = True
        self.start()

    def run(self):
        self.processSignal.emit(0, "Generating sub graph...")
        self.SubG = self.work.getSubGraphByFilter(self.G, self.filter_dic)
        if self.SubG is not None:
            # Compute centrality measures
            self.work.InDegreeCentrality(self.SubG)
            self.work.OutDegreeCentrality(self.SubG)
            self.work.DegreeCentrality(self.SubG)
            self.processSignal.emit(10, "Computing degree centrality...")
            self.work.BetweenessCentrality(self.SubG)
            self.processSignal.emit(20, "Computing betweeness centrality...")
            self.work.ClosenessCentrality(self.SubG)
            self.processSignal.emit(30, "Computing closeness centrality...")
            self.work.PagerankCentrality(self.SubG)
            self.processSignal.emit(40, "Computing PageRank centrality...")
            # Compute community measures
            self.work.LouvainCommunity(self.SubG)
            self.processSignal.emit(50, "Computing Louvain community...")
            self.work.LabelPropagationCommunity(self.SubG)
            self.processSignal.emit(60, "Computing label propagation community...")
            self.work.UnionFindCommunity(self.SubG)
            self.processSignal.emit(70, "Computing union find community...")

            nodesData = [[data["label"]] for n, data in self.SubG.nodes(data=True)]
            self.SendDataSignal.emit([self.SubG, nodesData])
        else:
            self.SendDataSignal.emit([self.G, []])
        self.working = False


class WorkerThreadGraph(QtCore.QThread):
    SendDataSignal = QtCore.Signal(list)
    processSignal = QtCore.Signal(int, str)

    def __init__(self, parent=None):
        super(WorkerThreadGraph, self).__init__(parent)
        self.working = True

    def SetData(self, G, work):
        self.G = G
        self.work = work
        self.working = True
        self.start()

    def run(self):
        # Compute centrality measures
        self.work.InDegreeCentrality(self.G)
        self.work.OutDegreeCentrality(self.G)
        self.work.DegreeCentrality(self.G)
        self.processSignal.emit(10, "Computing degree centrality...")
        self.work.BetweenessCentrality(self.G)
        self.processSignal.emit(20, "Computing betweeness centrality...")
        self.work.ClosenessCentrality(self.G)
        self.processSignal.emit(30, "Computing closeness centrality...")
        self.work.PagerankCentrality(self.G)
        self.processSignal.emit(40, "Computing PageRank centrality...")
        # Compute community measures
        self.work.LouvainCommunity(self.G)
        self.processSignal.emit(50, "Computing Louvain community...")
        self.work.LabelPropagationCommunity(self.G)
        self.processSignal.emit(60, "Computing label propagation community...")
        self.work.UnionFindCommunity(self.G)
        self.processSignal.emit(70, "Computing union find community...")

        # Compute node sizes
        marksize = self.work.setGNodesSize(self.G)

        # Compute node colors
        colors = self.work.setGNodesColor(self.G)

        labels = self.work.getGNodesAttrList(self.G, "label")

        nodesData = [[data["label"]] for n, data in self.G.nodes(data=True)]

        DateRangeData = self.getDateRangeData()
        valueRangeData = self.work.getGEdgesAttrRange(self.G, "value_in_ether")

        exchange = self.work.getNodesByType(self.G)

        self.processSignal.emit(90, "Generating graph layout...")

        # Compute graph layout
        node_pos, edge_pos = self.work.pygraphviz_layout(
            self.G, prog="sfdp", bundle=False
        )

        self.processSignal.emit(100, "Computing graph layout...")

        self.SendDataSignal.emit(
            [
                marksize,
                colors,
                labels,
                node_pos,
                edge_pos,
                nodesData,
                DateRangeData,
                valueRangeData,
                exchange,
            ]
        )
        self.working = False

    def getDateRangeData(self):
        Attrs = [data["time_stamp"] for source, target, data in self.G.edges(data=True)]
        if len(Attrs) == 1:
            d = QtCore.QDateTime.fromString(str(Attrs[0])[:10], "yyyy-MM-dd")
            return [[d], [1]]
        startDate = QtCore.QDateTime.fromString(str(min(Attrs))[:10], "yyyy-MM-dd")
        endDate = QtCore.QDateTime.fromString(str(max(Attrs))[:10], "yyyy-MM-dd")

        Attrs = np.unique(np.array(Attrs), return_counts=True)
        dataold = [
            QtCore.QDateTime.fromString(str(k)[:10], "yyyy-MM-dd") for k in Attrs[0]
        ]
        valueold = [v for v in Attrs[1]]
        data = []
        value = []
        num = startDate.daysTo(endDate)
        for i in range(num):
            d = startDate.addDays(1 * i)
            data.append(d)
            if d in dataold:
                idx = dataold.index(d)
                value.append(valueold[idx])
            else:
                value.append(0)
        return [data, value]


class GraphProcessBar(QtWidgets.QProgressBar):
    ProcessSignal = QtCore.Signal(int, str)

    def __init__(self, parent=None):
        super(GraphProcessBar, self).__init__(parent)
        # Setup graph layout, add control tools
        self.hbl = QtWidgets.QHBoxLayout(self)
        self.hbl.setSpacing(0)
        self.hbl.setContentsMargins(0, 0, 0, 0)
        self.label = QtWidgets.QLabel()
        self.label.setObjectName("selfPro")
        self.label.setStyleSheet("QLabel#selfPro{background:transparent}")
        self.setValue(0)
        self.setTextVisible(False)
        self.hbl.addSpacerItem(
            QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
            )
        )
        self.hbl.addWidget(self.label)
        self.hbl.addSpacerItem(
            QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
            )
        )
        self.ProcessSignal.connect(self.setProValue)

    def setProValue(self, value, text):
        self.label.setText(text)
        self.setValue(value)


class ToolWidget(QtWidgets.QWidget):
    graphsignal = QtCore.Signal(int, str)
    graphsignal2 = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(ToolWidget, self).__init__(parent)
        self.hbl = QtWidgets.QHBoxLayout(self)
        self.hbl.setSpacing(0)
        self.hbl.setContentsMargins(5, 0, 5, 0)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItem(u"From File")
        self.type_combo.addItem(u"From DataBase")
        self.type_combo.setCurrentIndex(1)
        self.type_combo.currentIndexChanged.connect(self.setType)

        self.stackwidget = QtWidgets.QStackedWidget()

        fileWidget = QtWidgets.QWidget()
        hbl = QtWidgets.QHBoxLayout(fileWidget)
        hbl.setSpacing(0)
        hbl.setContentsMargins(5, 0, 5, 0)
        self.dataFile = QtWidgets.QLineEdit()

        self.file_button = QtWidgets.QPushButton("File")
        self.file_button.setToolTip(u"select gexf File")
        self.file_button.clicked.connect(self.getFile)
        hbl.addWidget(self.dataFile)
        hbl.addWidget(self.file_button)

        databaseWidget = QtWidgets.QWidget()
        hbl2 = QtWidgets.QHBoxLayout(databaseWidget)
        hbl2.setSpacing(0)
        hbl2.setContentsMargins(5, 0, 5, 0)
        self.exchangesWidget = ComboCheckBox()
        self.exchangesWidget.setFixedWidth(300)
        exchanges = get_config()
        exchanges = sorted(exchanges)
        self.exchangesWidget.addItems(exchanges)
        self.dataRangeWidget = CheckDataEdit(mysname=u"From:", myename=u" To:")
        self.database_button = QtWidgets.QPushButton("Search")

        self.typedataCheck = QtWidgets.QComboBox()
        self.typedataCheck.addItems(
            [
                "Money Flow Graph (MFG)",
                "Contract Creation Graph (CCG)",
                "Contract Invocation Graph (CIG)",
            ]
        )
        hbl2.addWidget(self.exchangesWidget)
        hbl2.addWidget(self.dataRangeWidget)
        hbl2.addWidget(self.typedataCheck)

        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.setToolTip(u"Apply")
        self.apply_button.clicked.connect(self.apply)

        self.stackwidget.addWidget(fileWidget)
        self.stackwidget.addWidget(databaseWidget)
        self.stackwidget.setCurrentIndex(1)

        self.hbl.addWidget(self.type_combo)
        self.hbl.addWidget(self.stackwidget)
        self.hbl.addWidget(self.apply_button)

    def setType(self, idx):
        self.stackwidget.setCurrentIndex(idx)

    def getFile(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog

        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            u"Load gexf file",
            self.dataFile.text(),
            u"Gexf Files (*.gexf)",
            options=options,
        )

        if fileName:
            self.dataFile.setText(fileName)

    def apply(self):
        idx = self.stackwidget.currentIndex()
        if idx == 0:
            fileName = self.dataFile.text()
            self.graphsignal.emit(0, fileName)
        else:
            form_data = {}
            minData = self.dataRangeWidget
            startDate = self.dataRangeWidget.sdataedit.date()
            endDate = self.dataRangeWidget.edataedit.date()
            form_data["start_date"] = datetime.strptime(
                startDate.toString("yyyy-MM-dd"), "%Y-%m-%d"
            )
            form_data["end_date"] = datetime.strptime(
                endDate.toString("yyyy-MM-dd"), "%Y-%m-%d"
            )
            form_data["exchange_nodes"] = self.exchangesWidget.Outputlist
            form_data["graph_type"] = self.typedataCheck.currentText()
            self.graphsignal2.emit(form_data)


class Radiodemo(QtWidgets.QWidget):
    selectSig = QtCore.Signal(str)

    def __init__(self, title, keys, parent=None):
        super(Radiodemo, self).__init__(parent)
        hbl = QtWidgets.QHBoxLayout(self)
        hbl.setSpacing(0)
        hbl.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(title)
        hbl.addWidget(label)
        self.cs_group = QtWidgets.QButtonGroup()
        for i, k in enumerate(keys):
            btn = QtWidgets.QRadioButton(k)
            if i == 0:
                btn.setChecked(True)
            hbl.addWidget(btn)
            self.cs_group.addButton(btn)
        self.cs_group.buttonClicked.connect(self.btnstate)

    def btnstate(self, btn):
        if btn.isChecked():
            self.selectSig.emit(btn.text())


class ValueRangeWidget(QtWidgets.QWidget):
    rangeSig = QtCore.Signal(list)

    def __init__(self, valerange=[1.01, 100.999], parent=None):
        super(ValueRangeWidget, self).__init__(parent)
        self.valerange = valerange
        self.vbl = QtWidgets.QVBoxLayout(self)
        self.vbl.setSpacing(0)
        self.vbl.setContentsMargins(0, 0, 0, 0)

        hbl = QtWidgets.QHBoxLayout()
        hbl.setSpacing(0)
        hbl.setContentsMargins(0, 0, 0, 0)

        pDoubleValidator = QtGui.QDoubleValidator()
        pDoubleValidator.setRange(valerange[0], valerange[1])

        pDoubleValidator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        # Set level of accuracy
        pDoubleValidator.setDecimals(8)

        self.minEdit = QtWidgets.QLineEdit()
        self.minEdit.setFixedWidth(120)
        self.minEdit.setValidator(pDoubleValidator)
        self.maxEdit = QtWidgets.QLineEdit()
        self.maxEdit.setFixedWidth(120)
        self.maxEdit.setValidator(pDoubleValidator)
        self.minEdit.setReadOnly(True)
        self.maxEdit.setReadOnly(True)
        self.refreshBtn = QtWidgets.QPushButton("Reset", self)
        openPicture = self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        self.refreshBtn.setIcon(openPicture)
        self.refreshBtn.setStyleSheet("border:none;")  # Remove borders
        pal = self.refreshBtn.palette()
        pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#FF6347"))
        self.refreshBtn.setPalette(pal)
        self.refreshBtn.setStyleSheet("QPushButton{background:transparent;border:0px;}")
        self.refreshBtn.clicked.connect(self.resetRange)
        hbl.addSpacerItem(
            QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
            )
        )
        self.label = QtWidgets.QLabel("")
        hbl.addWidget(self.label)
        label = QtWidgets.QLabel("From")
        label.setStyleSheet("QLabel{background:transparent;border:0px;}")
        hbl.addWidget(label)
        hbl.addWidget(self.minEdit)

        label = QtWidgets.QLabel(" To")
        label.setStyleSheet("QLabel{background:transparent;border:0px;}")
        hbl.addWidget(label)
        hbl.addWidget(self.maxEdit)
        hbl.addWidget(self.refreshBtn)

        self.slider = RangeSlider()
        self.slider.setMinimum(valerange[0])
        self.slider.setMaximum(valerange[1])

        self.slider.setOrientation(QtCore.Qt.Horizontal)

        self.slider.rangeValueChanged.connect(self.sliderChange)
        self.slider.setLowValue(self.valerange[0])
        self.slider.setHighValue(self.valerange[1])
        self.vbl.addLayout(hbl)
        self.vbl.addWidget(self.slider)

    def setRanges(self, valerange):
        self.valerange = valerange
        self.slider.rangeValueChanged.disconnect()
        self.slider.setMinimum(self.valerange[0])
        self.slider.setMaximum(self.valerange[1])
        self.slider.setLowValue(self.valerange[0])
        self.slider.setHighValue(self.valerange[1])
        self.minEdit.setText(str(valerange[0]))
        self.maxEdit.setText(str(valerange[1]))
        self.slider.rangeValueChanged.connect(self.sliderChange)

    def minEditFinish(self):
        value = float(self.minEdit.text())

    def sliderChange(self, value, value2):
        self.minEdit.setText(str(value))
        self.maxEdit.setText(str(value2))
        self.rangeSig.emit([value, value2])

    def resetRange(self):
        self.slider.setLowValue(self.valerange[0])
        self.slider.setHighValue(self.valerange[1])
        self.rangeSig.emit(self.valerange)


class ControlWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ControlWidget, self).__init__(parent)
        self.setFixedHeight(240)
        self.vbl = QtWidgets.QVBoxLayout(self)
        self.vbl.setSpacing(0)
        self.vbl.setContentsMargins(0, 0, 0, 0)

        hbl = QtWidgets.QHBoxLayout()
        hbl.setSpacing(0)
        hbl.setContentsMargins(0, 0, 0, 0)

        self.nodetable1 = CheckTable()
        self.nodetable1.setFixedWidth(300)

        widget = QtWidgets.QWidget()
        vbl = QtWidgets.QVBoxLayout(widget)
        vbl.setSpacing(0)
        vbl.setContentsMargins(5, 5, 5, 5)

        self.ZoomChartView = RectZoomMoveView()
        self.ZoomChartView.setStyleSheet("border:none;")  # Remove borders
        self.ZoomChartView.verticalScrollBar().setDisabled(True)
        self.ZoomChartView.setVerticalScrollBarPolicy(1)
        self.ZoomChartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.ZoomChartView.setRangeColor("#666666")

        self.zoomChart = self.ZoomChartView.chart()
        self.zoomChart.setBackgroundVisible(False)

        self.zoomChart.setAnimationOptions(QChart.SeriesAnimations)
        self.zoomChart.legend().hide()

        self.ZoomChartView.initSeries(chartTypes="Bar")

        self.valueRangeWidget = ValueRangeWidget()
        vbl.addWidget(self.ZoomChartView)
        vbl.addWidget(self.valueRangeWidget)

        hbl.addWidget(self.nodetable1)
        hbl.addWidget(widget)

        self.nodesizeWidget = Radiodemo(
            "Centrality:",
            ["InDegree", "OutDegree", "Degree", "Betweeness", "Closeness", "PageRank"],
        )
        self.nodecolorWidget = Radiodemo(
            "Community:", ["Louvain", "Label propagation", "Union find"]
        )

        hbl2 = QtWidgets.QHBoxLayout()
        hbl2.setSpacing(0)
        hbl2.setContentsMargins(0, 0, 0, 0)
        self.resetBtn = QtWidgets.QPushButton("Reset")
        self.applyBtn = QtWidgets.QPushButton("Apply")
        hbl2.addSpacerItem(
            QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
            )
        )
        hbl2.addWidget(self.resetBtn)
        hbl2.addWidget(self.applyBtn)

        self.vbl.addLayout(hbl)
        self.vbl.addWidget(self.nodesizeWidget)
        self.vbl.addWidget(self.nodecolorWidget)
        self.vbl.addLayout(hbl2)


class MainWidget(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent)
        self.setWindowTitle(self.tr("GraphViz"))
        self.setWindowIcon(QtGui.QIcon("GraphViz.ico"))
        self.toolbar = self.addToolBar("tool")
        self.toolwidget = ToolWidget()
        self.toolwidget.graphsignal.connect(self.startWork)
        self.toolwidget.graphsignal2.connect(self.startWork2)
        self.toolbar.addWidget(self.toolwidget)

        mwidget = QtWidgets.QWidget()
        self.vbl = QtWidgets.QVBoxLayout(mwidget)
        self.vbl.setSpacing(0)
        self.vbl.setContentsMargins(0, 0, 0, 0)
        self.stackwidget = QtWidgets.QStackedWidget()
        self.controlWidget = ControlWidget()
        self.controlWidget.resetBtn.clicked.connect(self.resetFilter)
        self.controlWidget.applyBtn.clicked.connect(self.applyFilter)
        self.process = GraphProcessBar()
        self.process.setVisible(False)
        self.vbl.addWidget(self.stackwidget)
        self.vbl.addWidget(self.controlWidget)
        self.vbl.addWidget(self.process)

        self.centralWidget = GraphHigh()
        self.centralWidget.draw_init()
        self.centralWidget.neighbors_signal.connect(self.setNeighbors)
        self.stackwidget.addWidget(QtWidgets.QWidget())
        self.stackwidget.addWidget(self.centralWidget)
        self.setCentralWidget(mwidget)
        self.stackwidget.setCurrentIndex(0)

        self.dockGraph = QtWidgets.QDockWidget(self.tr("Node attributes"), self)
        self.dockGraph.setFixedWidth(350)
        self.dockGraph.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetMovable
        )
        self.dockGraph.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea
        )

        widget = QtWidgets.QWidget()
        vbl = QtWidgets.QVBoxLayout(widget)
        vbl.setSpacing(0)
        vbl.setContentsMargins(0, 0, 0, 0)
        self.textInfo = QtWidgets.QTextEdit()
        self.textInfo.setReadOnly(True)
        self.graphNodesWidget = InfoTableWidget()
        self.graphNodesWidget.dbclickedSig.connect(
            self.centralWidget.updateMarkerVisible
        )
        vbl.addWidget(self.textInfo)
        vbl.addWidget(self.graphNodesWidget)

        self.dockGraph.setWidget(widget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockGraph)

        self.dockGraph.hide()
        self.controlWidget.hide()

        self.work = GraphWork()
        self.nodesAttrs = [
            "label",
            "node_type",
            "InDegree",
            "OutDegree",
            "Degree",
            "Betweeness",
            "Closeness",
            "PageRank",
            "Louvain",
            "Label propagation",
            "Union find",
        ]

    def setNeighbors(self, info, values):
        if values is None:
            self.graphNodesWidget.InitTable(["All Nodes"], self.nodesData)
        elif values == []:
            self.graphNodesWidget.InitTable(["Sub Nodes"], self.NeighborsnodesData)
        else:
            self.graphNodesWidget.InitTable(["Neighbors"], [[v] for v in values])
        self.textInfo.setText(info)

    def startWork(self, idx, filename):
        if filename:
            self.graphNodesWidget.InitTable([""], [])

            self.dockGraph.hide()
            self.controlWidget.hide()
            self.setDisConnect()
            self.stackwidget.setCurrentIndex(0)
            self.subG = None
            self.G, num = self.work.readFile(filename)
            if num > 0:
                self.process.setVisible(True)
                self.workthread = WorkerThreadGraph(self)
                self.workthread.SendDataSignal.connect(self.InitGraph)
                self.workthread.processSignal.connect(self.changeProcess)
                self.workthread.SetData(self.G, self.work)
            else:
                QtWidgets.QMessageBox.information(self, "Info", ("The Graph is Empty！"))

    def startWork2(self, form_data):
        self.work = GraphWork()
        self.subG = None
        self.G, num = self.work.get_from_db(form_data)

        self.graphNodesWidget.InitTable([""], [])

        self.dockGraph.hide()
        self.controlWidget.hide()
        self.setDisConnect()
        self.stackwidget.setCurrentIndex(0)

        idx = self.toolwidget.typedataCheck.currentIndex()
        if idx == 2:
            self.controlWidget.valueRangeWidget.label.setText(" number_of_calls   ")
        elif idx == 0:
            self.controlWidget.valueRangeWidget.label.setText("  value_in_ether   ")
        if num > 0:
            self.process.setVisible(True)
            self.workthread = WorkerThreadGraph(self)
            self.workthread.SendDataSignal.connect(self.InitGraph)
            self.workthread.processSignal.connect(self.changeProcess)
            self.workthread.SetData(self.G, self.work)
        else:
            QtWidgets.QMessageBox.information(self, "Info", ("The Graph is Empty！"))

    def changeProcess(self, value, text):
        self.process.ProcessSignal.emit(value, text)

    def InitGraph(self, values):
        (
            marksize,
            colors,
            labels,
            node_pos,
            edge_pos,
            self.nodesData,
            DateRangeData,
            valueRangeData,
            exchange,
        ) = values
        # Number of nodes
        npts = self.G.number_of_nodes()
        # Number of edges
        nlinks = self.G.number_of_edges()

        self.valueRangeData = list(valueRangeData)

        if self.valueRangeData == [0, 0]:
            self.controlWidget.valueRangeWidget.hide()
        else:
            self.controlWidget.valueRangeWidget.show()
            self.controlWidget.valueRangeWidget.setRanges(self.valueRangeData)

        self.controlWidget.ZoomChartView.setData(DateRangeData[0], DateRangeData[1])
        self.graphNodesWidget.InitTable(["All Nodes"], self.nodesData)
        self.centralWidget.draw_init()
        self.centralWidget.init_data(
            self.G, marksize, colors, labels, node_pos, edge_pos, npts, nlinks
        )
        self.controlWidget.nodetable1.initData(["exchange"], exchange)

        self.process.setVisible(False)
        self.process.ProcessSignal.emit(0, "")
        self.controlWidget.nodesizeWidget.cs_group.buttons()[0].setChecked(True)
        self.controlWidget.nodecolorWidget.cs_group.buttons()[0].setChecked(True)
        self.dockGraph.show()
        self.controlWidget.show()
        self.stackwidget.setCurrentIndex(1)

        self.controlWidget.ZoomChartView.resetView()
        rect = self.controlWidget.ZoomChartView.chart().plotArea()
        self.controlWidget.ZoomChartView.parentRect.setRect(rect)
        self.setConnect()

        self.filter_dic = {"edges": {}}

    def setDisConnect(self):
        try:
            self.controlWidget.nodesizeWidget.selectSig.disconnect()
        except:
            pass
        try:
            self.controlWidget.nodecolorWidget.selectSig.disconnect()
        except:
            pass
        try:
            self.controlWidget.ZoomChartView.rangeSig.disconnect()
        except:
            pass
        try:
            self.controlWidget.valueRangeWidget.rangeSig.disconnect()
        except:
            pass
        try:
            self.controlWidget.nodetable1.sendData.disconnect()
        except:
            pass

    def setConnect(self):
        self.controlWidget.nodesizeWidget.selectSig.connect(
            self.centralWidget.updateMarkersSize
        )
        self.controlWidget.nodecolorWidget.selectSig.connect(
            self.centralWidget.updateMarkersColor
        )

        self.controlWidget.ZoomChartView.rangeSig.connect(self.setFilterDate)
        self.controlWidget.valueRangeWidget.rangeSig.connect(self.setFilterValue)
        self.controlWidget.nodetable1.sendData.connect(self.setFilterNode)

    def resetFilter(self):
        self.controlWidget.nodetable1.header.headerClick(True)
        self.setDisConnect()
        self.controlWidget.nodesizeWidget.cs_group.buttons()[0].setChecked(True)
        self.controlWidget.nodecolorWidget.cs_group.buttons()[0].setChecked(True)
        self.controlWidget.ZoomChartView.BtnsWidget.refreshBtn.click()
        self.controlWidget.valueRangeWidget.refreshBtn.click()
        self.controlWidget.nodetable1.myModel.headerClick(True)
        self.graphNodesWidget.InitTable(["All Nodes"], self.nodesData)
        self.filter_dic = {"edges": {}}
        self.setConnect()
        self.centralWidget.setSubG(None)
        self.centralWidget.updateSubGVisible()

    def applyFilter(self):
        self.process.setVisible(True)
        self.workthreadsub = WorkerThreadSubGraph(self)
        self.workthreadsub.SendDataSignal.connect(self.subGraph)
        self.workthreadsub.processSignal.connect(self.changeProcess)
        self.workthreadsub.SetData(self.G, self.work, self.filter_dic)

    def subGraph(self, values):
        self.process.setVisible(False)
        self.process.ProcessSignal.emit(0, "")
        SubG, self.NeighborsnodesData = values
        if SubG == self.G:
            self.graphNodesWidget.InitTable(["All Nodes"], self.nodesData)
            self.centralWidget.setSubG(None)
        else:
            self.graphNodesWidget.InitTable(["Sub Nodes"], self.NeighborsnodesData)
            self.centralWidget.setSubG(SubG)
        self.centralWidget.updateSubGVisible()

    def setFilterDate(self, value):
        ranges = [
            self.controlWidget.ZoomChartView.mintimeData.toString(
                "yyyy-MM-dd HH:mm:ss"
            ),
            self.controlWidget.ZoomChartView.maxtimeData.toString(
                "yyyy-MM-dd HH:mm:ss"
            ),
        ]
        if value == ranges:
            if "time_stamp" in self.filter_dic["edges"]:
                self.filter_dic["edges"].pop("time_stamp")
        else:
            self.filter_dic["edges"]["time_stamp"] = {"value": value, "type": "time"}

    def setFilterValue(self, value):
        if value == self.valueRangeData:
            if "value_in_ether" in self.filter_dic["edges"]:
                self.filter_dic["edges"].pop("value_in_ether")
        else:
            self.filter_dic["edges"]["value_in_ether"] = {
                "value": value,
                "type": "float",
            }

    def setFilterNode(self, value):
        if len(value) == len(self.controlWidget.nodetable1.myModel._data):
            if "label" in self.filter_dic["edges"]:
                self.filter_dic["edges"].pop("label")
        else:
            self.filter_dic["edges"]["label"] = {"value": value, "type": "list"}


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    file = QtCore.QFile(":pic/style.qss")
    file.open(QtCore.QFile.ReadOnly)
    styleSheet = file.readAll()
    styleSheet = str(styleSheet, encoding="utf8")
    app.setStyleSheet(styleSheet)

    window = MainWidget()
    window.show()

    sys.exit(app.exec_())
