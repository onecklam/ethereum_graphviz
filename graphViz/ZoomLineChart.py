import random
import math
from PyQt5.QtChart import (
    QAreaSeries,
    QBarSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QPieSeries,
    QScatterSeries,
    QSplineSeries,
    QBarSeries,
    QValueAxis,
    QStackedBarSeries,
    QHorizontalBarSeries,
    QBarCategoryAxis,
    QCategoryAxis,
    QAbstractBarSeries,
)
from PyQt5.QtCore import (
    pyqtSlot,
    pyqtSignal,
    QMargins,
    QPointF,
    Qt,
    QEvent,
    QRectF,
    QPoint,
    QRect,
    QObject,
    QDateTime,
)
from PyQt5.QtGui import (
    QColor,
    QPainter,
    QPalette,
    QCursor,
    QPen,
    QBrush,
    QPainterPath,
    QPalette,
    QLinearGradient,
)
from PyQt5.QtWidgets import (
    QCheckBox,
    QStyle,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QGridLayout,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
    QToolTip,
    QScrollArea,
    QFrame,
    QGraphicsRectItem,
    QGraphicsItem,
)
from LDateEdit import CheckDataEdit
import cgitb

# Avoid error and crash in qt5
cgitb.enable(format="text")


def index_number(li, defaultnumber):
    select = defaultnumber - li[0]
    index = 0
    for i in range(1, len(li) - 1):
        select2 = defaultnumber - li[i]
        if abs(select) > abs(select2):
            select = select2
            index = i
    return li[index], index


# Send signal in QGraphicsRectItem
class SelectedChange(QObject):
    selectedChange = pyqtSignal(list)

    def __init__(self):
        super(SelectedChange, self).__init__()


class RectRangeItem(QGraphicsRectItem):

    handleMiddleLeft = 1
    handleMiddleRight = 2
    handleMiddleCenter = 3

    handleSize = +8.0
    handleSpace = -4.0

    handleCursors = {
        handleMiddleLeft: Qt.SizeHorCursor,
        handleMiddleRight: Qt.SizeHorCursor,
        handleMiddleCenter: Qt.SizeAllCursor,
    }

    def __init__(self, parent=None):
        super(RectRangeItem, self).__init__(parent)
        self.chart = parent
        self.handles = {}
        self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        # Define border color of rectangular body
        self.handleColor = QColor("#00aa55")
        self._selectedChange = SelectedChange()

        self.rangePoints = []
        self.updateHandlesPos()

    # Send messages
    def selectedChange():
        def fget(self):
            return self._selectedChange.selectedChange

        return locals()

    selectedChange = property(**selectedChange())

    def setRangeColor(self, color):
        self.handleColor = QColor(color)

    def handleAt(self, point):
        """
        Returns the resize handle below the given point.
        """
        for k, v, in self.handles.items():
            if v.contains(point):
                return k
        return None

    def hoverMoveEvent(self, moveEvent):
        """
        Executed when the mouse moves over the shape (NOT PRESSED).
        """
        if self.isSelected():
            handle = self.handleAt(moveEvent.pos())
            cursor = Qt.ArrowCursor if handle is None else self.handleCursors[handle]
            self.setCursor(cursor)
        super().hoverMoveEvent(moveEvent)

    def hoverLeaveEvent(self, moveEvent):
        """
        Executed when the mouse leaves the shape (NOT PRESSED).
        """
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(moveEvent)

    def mousePressEvent(self, mouseEvent):
        """
        Executed when the mouse is pressed on the item.
        """

        self.handleSelected = self.handleAt(mouseEvent.pos())
        if self.handleSelected:
            self.mousePressPos = mouseEvent.pos()
            self.mousePressRect = self.boundingRect()
        else:
            if mouseEvent.buttons() == Qt.LeftButton:
                self.lastMousePos = mouseEvent.scenePos()
        super().mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        """
        Executed when the mouse is being moved over the item while being pressed.
        """
        if self.handleSelected is not None:
            self.interactiveResize(mouseEvent)
        else:
            if mouseEvent.buttons() != Qt.LeftButton:
                return
            super().mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        """
        Executed when the mouse is released from the item.
        """
        super().mouseReleaseEvent(mouseEvent)
        if self.handleSelected is not None:
            self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None
        self.update()

    def wheelEvent(self, event):
        event.accept()
        factor = event.delta()
        s = self.handleSize
        rect = self.rect()
        prect = self.chart.rect()
        # Zoom in or out by mouse's wheel
        # Trigger zooming by mouse's wheel
        if factor > 0:
            new_left, left_index = index_number(self.rangePoints, rect.left())
            new_right, right_index = index_number(self.rangePoints, rect.right())

            left_index = max(0, left_index - 1)
            right_index = min(len(self.rangePoints) - 2, right_index + 1)
            new_left = self.rangePoints[left_index]
            new_right = self.rangePoints[right_index]
            rect.setLeft(new_left)
            rect.setRight(new_right)
            self.setRect(rect)
            self.updateHandlesPos()
            self.selectedChange.emit([left_index, right_index])
        if factor < 0:
            new_left, left_index = index_number(self.rangePoints, rect.left())
            new_right, right_index = index_number(self.rangePoints, rect.right())

            left_index = max(0, left_index + 1)
            right_index = min(len(self.rangePoints) - 2, right_index - 1)
            new_left = self.rangePoints[left_index]
            new_right = self.rangePoints[right_index]
            if right_index >= left_index:
                rect.setLeft(new_left)
                rect.setRight(new_right)
                self.setRect(rect)
                self.updateHandlesPos()
                self.selectedChange.emit([left_index, right_index])
            else:
                rect.setLeft(new_left)
                rect.setRight(new_left)
                self.setRect(rect)
                self.updateHandlesPos()
                self.selectedChange.emit([left_index, left_index])
        super().wheelEvent(event)

    def boundingRect(self):
        """
        Returns the bounding rect of the shape (including the resize handles).
        """
        o = self.handleSize + self.handleSpace
        return self.rect().adjusted(-o, -o, o, o)

    def updateHandlesPos(self):
        """
        Update current resize handles according to the shape size and position.
        """
        s = self.handleSize
        b = self.boundingRect()
        self.handles[self.handleMiddleLeft] = QRectF(
            b.left(), b.center().y() - s / 2, s, s
        )
        self.handles[self.handleMiddleRight] = QRectF(
            b.right() - s, b.center().y() - s / 2, s, s
        )
        self.handles[self.handleMiddleCenter] = QRectF(
            b.left() + s, b.top(), b.width() - 2 * s, b.height()
        )

    def interactiveResize(self, mouseEvent):
        """
        Perform shape interactive resize.
        """
        s = self.handleSize
        mousePos = mouseEvent.pos()
        offset = self.handleSize + self.handleSpace
        boundingRect = self.boundingRect()
        rect = self.rect()
        diff = QPointF(0, 0)

        self.prepareGeometryChange()

        if self.handleSelected == self.handleMiddleLeft:
            fromX = self.mousePressRect.left()
            toX = fromX + mousePos.x() - self.mousePressPos.x()
            diff.setX(toX - fromX)

            stateL = toX + offset >= self.chart.rect().left()
            stateR = toX + offset < self.rect().right()
            # Between leftmost and rightmost sides
            if stateL and stateR:
                boundingRect.setLeft(toX)
                rect.setLeft(boundingRect.left() + offset)
                self.setRect(rect)
            else:
                # Less than leftmost side
                if not stateL:
                    toX = self.chart.rect().left() - offset
                    boundingRect.setLeft(toX)
                    rect.setLeft(boundingRect.left() + offset)
                    self.setRect(rect)
                # Greater than rightmost side
                if not stateR:
                    boundingRect.setLeft(self.rect().right())
                    boundingRect.setRight(toX)
                    rect.setLeft(self.rect().right())
                    rect.setRight(boundingRect.right() + offset)
                    self.setRect(rect)
                    self.handleSelected = self.handleMiddleRight
                    self.mousePressPos = mousePos
                    self.mousePressRect = self.boundingRect()

        elif self.handleSelected == self.handleMiddleCenter:
            fromX = self.mousePressRect.left()
            toX = fromX + mousePos.x() - self.mousePressPos.x()

            fromXR = self.mousePressRect.right()
            toXR = fromXR + mousePos.x() - self.mousePressPos.x()

            diff.setX(toX - fromX)
            width = rect.width()
            statel = toX + offset >= self.chart.rect().left()
            stater = toX + offset + width <= self.chart.rect().right()
            if statel and stater:
                boundingRect.setLeft(toX)
                rect.setLeft(boundingRect.left() + offset)
                rect.setWidth(width)
                self.setRect(rect)
            else:
                if not statel:
                    toX = self.chart.rect().left() - offset
                    boundingRect.setLeft(toX)
                    rect.setLeft(boundingRect.left() + offset)
                    rect.setWidth(width)
                    self.setRect(rect)
                if not stater:
                    toXR = self.chart.rect().right() + offset
                    boundingRect.setRight(toXR)
                    rect.setRight(boundingRect.right() - offset)
                    self.setRect(rect)

        elif self.handleSelected == self.handleMiddleRight:
            fromX = self.mousePressRect.right()
            toX = fromX + mousePos.x() - self.mousePressPos.x()
            diff.setX(toX - fromX)

            stateL = toX - offset > self.rect().left()  # +3*s
            stateR = toX - offset <= self.chart.rect().right()
            if stateR and stateL:
                boundingRect.setRight(toX)
                rect.setRight(boundingRect.right() - offset)
                self.setRect(rect)
            else:
                if not stateR:
                    toX = self.chart.rect().right() + offset
                    boundingRect.setRight(toX)
                    rect.setRight(boundingRect.right() - offset)
                    self.setRect(rect)
                # Less than leftmost side
                if not stateL:
                    boundingRect.setLeft(toX)
                    boundingRect.setRight(self.rect().left())
                    rect.setLeft(boundingRect.right() - offset)
                    rect.setRight(self.rect().left())
                    self.setRect(rect)
                    self.handleSelected = self.handleMiddleLeft
                    self.mousePressPos = mousePos
                    self.mousePressRect = self.boundingRect()

        left = self.rect().left()
        right = self.rect().right()
        new_left, left_index = index_number(self.rangePoints, left)
        new_right, right_index = index_number(self.rangePoints, right)
        # Restrict area of movements
        if self.handleSelected == self.handleMiddleLeft:
            rect.setLeft(new_left)
            self.setRect(rect)
        elif self.handleSelected == self.handleMiddleRight:
            rect.setRight(new_right)
            self.setRect(rect)
        elif self.handleSelected == self.handleMiddleCenter:
            rect.setLeft(new_left)
            rect.setRight(new_right)
            self.setRect(rect)

        self.updateHandlesPos()
        self.selectedChange.emit([left_index, right_index])

    def shape(self):
        """
        Returns the shape of this item as a QPainterPath in local coordinates.
        """
        path = QPainterPath()
        path.addRect(self.rect())
        if self.isSelected():
            for handle, shape in self.handles.items():
                if handle != self.handleMiddleCenter:
                    path.addEllipse(shape)
                else:
                    path.addRect(shape)

        return path

    def paint(self, painter, option, widget=None):
        """
        Paint the node in the graphic view.
        """
        opaColor = self.handleColor
        opaColor.setAlphaF(0.2)
        painter.setBrush(QBrush(opaColor))

        rectColor = self.handleColor
        rectColor.setAlphaF(1)
        painter.setPen(QPen(rectColor, 2.0, Qt.SolidLine))
        painter.drawRect(self.rect())

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(rectColor))
        painter.setPen(QPen(rectColor, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        for handle, rect in self.handles.items():
            if self.handleSelected is None or handle == self.handleSelected:
                if handle != self.handleMiddleCenter:
                    painter.drawEllipse(rect)


class ViewButtonsWidget(QWidget):
    RelationSig = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(ViewButtonsWidget, self).__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.dateRangeEdit = CheckDataEdit(mysname=u"From:", myename=u" To:")
        self.dateRangeEdit.sdataedit.setFixedHeight(20)
        self.dateRangeEdit.edataedit.setFixedHeight(20)
        self.refreshBtn = QPushButton("Reset", self)
        openPicture = self.style().standardIcon(QStyle.SP_BrowserReload)
        self.refreshBtn.setIcon(openPicture)
        self.refreshBtn.setStyleSheet("border:none;")  # Remove border
        pal = self.refreshBtn.palette()
        pal.setColor(QPalette.ButtonText, QColor("#FF6347"))
        self.refreshBtn.setPalette(pal)
        self.refreshBtn.setStyleSheet("QPushButton{background:transparent;border:0px;}")
        layout.addWidget(self.dateRangeEdit)
        layout.addWidget(self.refreshBtn)

    def setPalActive(self):
        pal = self.refreshBtn.palette()
        pal.setColor(QPalette.ButtonText, QColor("#FF6347"))
        self.refreshBtn.setPalette(pal)

    def setPalDisActive(self):
        pal = self.refreshBtn.palette()
        pal.setColor(QPalette.ButtonText, QColor("#D3D3D3"))
        self.refreshBtn.setPalette(pal)


class RectZoomMoveView(QChartView):
    """
    Filter data to be displayed in rectangular body
    """

    rangeSig = pyqtSignal(list)

    def __init__(self, parent=None):
        super(RectZoomMoveView, self).__init__(parent)
        self.setChart(QChart())
        self.chart().setMargins(QMargins(5, 5, 5, 5))
        self.chart().setContentsMargins(-10, -10, -10, -10)
        self.chart().setTitle(" ")
        self.relationState = True

        # Define two rectangles for background and drawing respectively
        self.parentRect = QGraphicsRectItem(self.chart())

        self.parentRect.setFlag(QGraphicsItem.ItemClipsChildrenToShape, True)
        self.parentRect.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.RangeItem = RectRangeItem(parent=self.parentRect)
        self.RangeItem.setZValue(998)
        pen = QPen(Qt.gray)
        pen.setWidth(1)
        self.parentRect.setPen(pen)
        self.parentRect.setZValue(997)

        self.scene().addItem(self.parentRect)
        self.scene().addItem(self.RangeItem)

        self.RangeItem.hide()
        self.m_chartRectF = QRectF()
        self.m_rubberBandOrigin = QPointF(0, 0)
        self.dataLength = 0

        self.RangeItem.selectedChange.connect(self.changeFromRectItem)

        self.BtnsWidget = ViewButtonsWidget(self)
        self.BtnsWidget.refreshBtn.clicked.connect(self.updateView)
        self.BtnsWidget.RelationSig.connect(self.setRelationState)
        self.BtnsWidget.dateRangeEdit.dateRangeSig.connect(self.changDateRect)

    def changDateRect(self, daterange):
        if self.chartTypes == "Bar":
            v = 3
        else:
            v = 2
        l = len(self.RangeItem.rangePoints)
        if l > 2:
            try:
                num = self.mintimeData.date().daysTo(daterange[0])
                left = self.RangeItem.rangePoints[num]
                num = self.mintimeData.date().daysTo(daterange[1])
                right = self.RangeItem.rangePoints[num]
                rect = self.chart().plotArea()
                rect.setLeft(left)
                rect.setRight(right)
            except:
                rect = self.chart().plotArea()
            self.RangeItem.setRect(rect)
            self.RangeItem.updateHandlesPos()
        else:
            try:
                num = self.mintimeData.date().daysTo(daterange[0])
                left = self.RangeItem.rangePoints[num]
                num = self.mintimeData.date().daysTo(daterange[0])
                right = self.RangeItem.rangePoints[num]
                rect = self.chart().plotArea()
                rect.setLeft(left)
                rect.setRight(right)
            except:
                rect = self.chart().plotArea()
            self.RangeItem.setRect(rect)
            self.RangeItem.updateHandlesPos()

    def lineSpace(self, start, end, num):
        res = []
        if self.chartTypes == "Bar":
            step = (end - start) / (num)
            for i in range(num + 2):
                res.append(start + i * step)
        else:
            step = (end - start) / (num - 1)
            for i in range(num + 1):
                res.append(start + i * step)
        return res

    def getRangePoints(self):
        count = self.zoomSeries.count()
        rect = self.chart().plotArea()
        left = rect.left()
        right = rect.right()
        if count == 0:
            self.RangeItem.rangePoints = [left, right]
        else:
            # Get coordinate position for each node
            self.RangeItem.rangePoints = self.lineSpace(left, right, count)

    def setRangeColor(self, color):
        self.RangeItem.setRangeColor(color)

    def setRelationState(self, state):
        self.relationState = state

    def initSeries(self, chartTypes="Bar"):
        self.chartTypes = chartTypes
        axisX = QDateTimeAxis()
        axisX.setFormat("yyyy-MM-dd")
        self.zoomSeries = QLineSeries(self.chart())
        self.chart().addSeries(self.zoomSeries)
        self.chart().setAxisY(QValueAxis(), self.zoomSeries)
        self.chart().setAxisX(axisX, self.zoomSeries)
        self.initView()

    def clearAll(self):
        # Clear all series and axes
        self.chart().removeAllSeries()
        axess = self.chart().axes()
        for axes in axess:
            self.chart().removeAxis(axes)

    def setData(self, timeData, valueData, chartTypes="Bar"):
        axisX = QDateTimeAxis()
        axisX.setFormat("yyyy-MM-dd")

        if self.chartTypes == "Bar":
            # Clear all series
            self.clearAll()
            self.zoomSeries = QLineSeries(self.chart())
            barSeries = QBarSeries(self.chart())
            barset = QBarSet("data")
            barSeries.setBarWidth(0.8)
            barSeries.append(barset)
            for td, vd in zip(timeData, valueData):
                self.zoomSeries.append(td.toMSecsSinceEpoch(), vd)
            barset.append(valueData)
            self.zoomSeries.hide()
            self.chart().addSeries(self.zoomSeries)
            self.chart().addSeries(barSeries)
            self.chart().setAxisY(QValueAxis(), self.zoomSeries)
            axisX.setRange(min(timeData), max(timeData))
            self.chart().setAxisX(axisX, self.zoomSeries)
        elif self.chartTypes == "Scatter":
            # Clear all series
            self.clearAll()
            self.zoomSeries = QLineSeries(self.chart())
            scattSeries = QScatterSeries(self.chart())
            scattSeries.setMarkerSize(8)

            for td, vd in zip(timeData, valueData):
                self.zoomSeries.append(td.toMSecsSinceEpoch(), vd)
                scattSeries.append(td.toMSecsSinceEpoch(), vd)
            self.zoomSeries.hide()
            self.chart().addSeries(self.zoomSeries)
            self.chart().addSeries(scattSeries)
            self.chart().setAxisY(QValueAxis(), self.zoomSeries)
            axisX.setRange(min(timeData), max(timeData))
            self.chart().setAxisX(axisX, self.zoomSeries)
        elif self.chartTypes in ["Line", "PLine"]:
            self.clearAll()
            if self.chartTypes == "Line":
                self.zoomSeries = QLineSeries(self.chart())
            else:
                self.zoomSeries = QSplineSeries(self.chart())
            for td, vd in zip(timeData, valueData):
                self.zoomSeries.append(td.toMSecsSinceEpoch(), vd)
            self.chart().addSeries(self.zoomSeries)

            self.chart().setAxisY(QValueAxis(), self.zoomSeries)
            axisX.setRange(min(timeData), max(timeData))
            self.chart().setAxisX(axisX, self.zoomSeries)
        elif self.chartTypes == "Area":

            self.clearAll()
            self.zoomSeries = QLineSeries()
            self.zoomSeries.setColor(QColor("#666666"))
            for td, vd in zip(timeData, valueData):
                self.zoomSeries.append(td.toMSecsSinceEpoch(), vd)

            areaSeries = QAreaSeries(self.zoomSeries, None)

            self.chart().addSeries(self.zoomSeries)
            self.chart().addSeries(areaSeries)
            self.chart().setAxisY(QValueAxis(), areaSeries)
            axisX.setRange(min(timeData), max(timeData))
            self.chart().setAxisX(axisX, areaSeries)
            self.zoomSeries.hide()
        self.mintimeData = min(timeData)
        self.maxtimeData = max(timeData)
        self.BtnsWidget.dateRangeEdit.setDateRange(
            [
                self.mintimeData.toString("yyyy-MM-dd"),
                self.maxtimeData.toString("yyyy-MM-dd"),
            ]
        )
        self.updateView()

    def resetView(self):

        rect = self.chart().plotArea()
        self.parentRect.setRect(rect)
        topRight = self.chart().plotArea().topRight()
        x = int(topRight.x())
        y = int(topRight.y())
        self.BtnsWidget.setGeometry(QRect(x - 420, 0, 420, 23))
        self.RangeItem.setRect(rect)
        self.RangeItem.show()
        self.save_current_rubber_band()
        self.RangeItem.updateHandlesPos()
        self.apply_nice_numbers()
        self.getRangePoints()
        self.sendRang()

    def initView(self):
        self.RangeItem.hide()
        # Hide y-axis
        if self.chart().axisY():
            self.chart().axisY().setVisible(False)
        if self.chart().axisX():
            self.chart().axisX().setGridLineVisible(False)
        self.m_chartRectF = QRectF()
        self.m_rubberBandOrigin = QPointF(0, 0)
        self.getRangePoints()

    def updateView(self):
        self.RangeItem.hide()
        # Hide y-axis
        if self.chart().axisY():
            self.chart().axisY().setVisible(False)
        if self.chart().axisX():
            self.chart().axisX().setGridLineVisible(False)
        self.m_chartRectF = QRectF()
        self.m_rubberBandOrigin = QPointF(0, 0)
        self.resetView()

    # Map points to chart
    def point_to_chart(self, pnt):
        scene_point = self.mapToScene(pnt)
        chart_point = self.chart().mapToValue(scene_point)
        return chart_point

    # Map chart to points
    def chart_to_view_point(self, char_coord):
        scene_point = self.chart().mapToPosition(char_coord)
        view_point = self.mapFromScene(scene_point)
        return view_point

    # Save positions of rectangles
    def save_current_rubber_band(self):
        rect = self.RangeItem.rect()

        chart_top_left = self.point_to_chart(rect.topLeft().toPoint())
        self.m_chartRectF.setTopLeft(chart_top_left)

        chart_bottom_right = self.point_to_chart(rect.bottomRight().toPoint())
        self.m_chartRectF.setBottomRight(chart_bottom_right)

    # Respond to change in positions of rectangles
    def changeFromRectItem(self, rectIndex):
        self.save_current_rubber_band()
        self.sendRang(rectIndex)

    def sendRang(self, rectIndex=[]):

        if self.RangeItem.rect() != self.parentRect.rect():
            self.BtnsWidget.setPalActive()
        else:
            self.BtnsWidget.setPalDisActive()
        if self.chartTypes == "Bar":
            v = 3
        else:
            v = 2
        if rectIndex == []:
            maxData = QDateTime.fromMSecsSinceEpoch(
                self.zoomSeries.at(len(self.RangeItem.rangePoints) - v).x()
            )
            minData = QDateTime.fromMSecsSinceEpoch(self.zoomSeries.at(0).x())
        else:
            minData = max(rectIndex[0], 0)
            maxData = min(rectIndex[1], len(self.RangeItem.rangePoints) - v)
            minData = QDateTime.fromMSecsSinceEpoch(self.zoomSeries.at(minData).x())
            maxData = QDateTime.fromMSecsSinceEpoch(self.zoomSeries.at(maxData).x())

        if minData > maxData:
            if self.RangeItem.handleSelected is None:
                self.resetView()
        else:
            self.BtnsWidget.dateRangeEdit.setDate(
                [minData.toString("yyyy-MM-dd"), maxData.toString("yyyy-MM-dd")]
            )
            if self.relationState:
                self.rangeSig.emit(
                    [
                        minData.toString("yyyy-MM-dd HH:mm:ss"),
                        maxData.toString("yyyy-MM-dd HH:mm:ss"),
                    ]
                )

    # Change positions of rectangles in scaling
    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.chart().plotArea()
        self.parentRect.setRect(rect)
        self.getRangePoints()
        topRight = self.chart().plotArea().topRight()
        x = int(topRight.x())
        y = int(topRight.y())
        self.BtnsWidget.setGeometry(QRect(x - 420, 0, 420, 23))
        if self.RangeItem.isVisible():
            self.restore_rubber_band()
            self.save_current_rubber_band()
            self.RangeItem.updateHandlesPos()
        else:
            self.RangeItem.setRect(self.parentRect.rect())
            self.RangeItem.show()
            self.RangeItem.setRect(self.parentRect.rect())
            self.save_current_rubber_band()
            self.RangeItem.updateHandlesPos()
        self.apply_nice_numbers()

    # Restore to original positions of rectangles
    def restore_rubber_band(self):
        view_top_left = self.chart_to_view_point(self.m_chartRectF.topLeft())
        view_bottom_right = self.chart_to_view_point(self.m_chartRectF.bottomRight())

        self.m_rubberBandOrigin = view_top_left
        height = self.chart().plotArea().height()
        rect = QRectF()
        rect.setTopLeft(view_top_left)
        rect.setBottomRight(view_bottom_right)
        rect.setHeight(height)
        self.RangeItem.setRect(rect)

    # Adjust display coordinates of axes automatically
    def apply_nice_numbers(self):
        axes_list = self.chart().axes()
        for value_axis in axes_list:
            if value_axis:
                pass


class MouseZoomMoveView(QChartView):
    """
    Zoom or move graph with mouse
    """

    def __init__(self, chart, parent=None):
        super(MouseZoomMoveView, self).__init__(parent)
        self.setChart(chart)
        self.zoomState = 1

    def setZoomState(self, state=0):
        self.zoomState = state

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.chart():
            self.m_lastMousePos = self.mapToScene(event.pos())
        QChartView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.chart():
            newValue = self.mapToScene(event.pos())
            delta = newValue - self.m_lastMousePos

            self.chart().scroll(-delta.x(), 0)

            self.m_lastMousePos = newValue

        QChartView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QChartView.mouseReleaseEvent(self, event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Plus:
            self.zoomFun(1)
        elif key == Qt.Key_Minus:
            self.zoomFun(-1)
        elif key == Qt.Key_Left:
            self.chart().scroll(10, 0)
        elif key == Qt.Key_Right:
            self.chart().scroll(-10, 0)
        elif key == Qt.Key_Up:
            if self.zoomState == 2:
                self.chart().scroll(0, -10)
        elif key == Qt.Key_Down:
            if self.zoomState == 2:
                self.chart().scroll(0, 10)
        elif key == Qt.Key_R:
            self.chart().zoomReset()
        else:
            QChartView.keyPressEvent(self, event)

    def wheelEvent(self, event):
        event.accept()
        factor = event.angleDelta().y()
        self.zoomFun(factor)
        QChartView.wheelEvent(self, event)

    def zoomFun(self, factor):
        if self.zoomState == 0:
            if factor > 0:
                self.chart().zoomIn()
            else:
                self.chart().zoomOut()
        elif self.zoomState == 1:
            rect = self.chart().plotArea()
            center = rect.center()

            mFactor = 0.5 if factor > 0 else 2
            rect.setWidth(mFactor * rect.width())
            mousePos = self.mapFromGlobal(QCursor.pos())
            mousePos.setY(center.y())
            rect.moveCenter(mousePos)
            self.chart().zoomIn(rect)
            delta = center - mousePos
            self.chart().scroll(delta.x(), 0)


class QtDataRangeChart(QWidget):
    def __init__(self, parent=None):
        super(QtDataRangeChart, self).__init__(parent)
        vbox = QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)

        self.ZoomChartView = RectZoomMoveView()
        self.ZoomChartView.setRenderHint(QPainter.Antialiasing)

        self.ZoomChartView.rangeSig.connect(self.test)
        self.ZoomChartView.setRangeColor("#4169E1")

        self.zoomChart = self.ZoomChartView.chart()
        self.zoomChart.setTheme(QChart.ChartThemeBlueCerulean)

        self.zoomChart.setAnimationOptions(QChart.SeriesAnimations)
        self.zoomChart.legend().hide()

        self.ZoomChartView.initSeries(chartTypes="Bar")

        btn = QPushButton("sss")
        btn.clicked.connect(self.setData)
        vbox.addWidget(btn)
        vbox.addWidget(self.ZoomChartView)
        self.setFixedHeight(120)

    def test(self, values):
        pass

    def setData(self):
        data, value = self.getRandomData()
        self.ZoomChartView.setData(data, value)
