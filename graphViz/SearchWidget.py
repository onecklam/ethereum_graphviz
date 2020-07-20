# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QStringListModel
from PyQt5.QtWidgets import (
    QLineEdit,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStyle,
    QPushButton,
    QCompleter,
)
from PyQt5.QtGui import QIcon
import qtawesome as qta


class SearchWidget2(QWidget):
    def __init__(self, parent=None):
        super(SearchWidget2, self).__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "QWidget{min-height: 36px;max-height: 36px;border-radius: 15px;}"
        )

        self._initView()

    def _initView(self):
        """Initialize graph layout"""

        layout = QHBoxLayout(self)

        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        searchstyle = """
                QLineEdit#searchEdit {
            width: 220px;
            min-height: 32px;max-height: 32px;
            border: 1px;
            color: #666;
            background: #fff;
            outline: none;
            padding-left: 10px;
            
            padding-right: 5px;
            border-top-left-radius: 15px;
            border-bottom-left-radius: 15px;
        }
        """
        self._searchEdit = QLineEdit(self, objectName="searchEdit")
        self._searchEdit.setStyleSheet(searchstyle)
        self._searchBtn = RubberBandButton(parent=self)
        skinpic = QIcon("Google-Custom-Search.ico")
        self._searchBtn.setpng(skinpic)

        layout.addWidget(self._searchEdit)
        layout.addWidget(self._searchBtn)


class SearchWidget(QLineEdit):
    sendSearchSig = pyqtSignal(str)

    def __init__(
        self,
        bgcolor="#201F1F",
        icon_file="fa.search",
        iconSize=QSize(24, 24),
        parent=None,
    ):
        super(SearchWidget, self).__init__(parent)

        skinpic = qta.icon(icon_file)
        self._searchBtn = QPushButton(skinpic, "", parent=self)
        self._searchBtn.setObjectName("searchbtn")
        self._searchBtn.setStyleSheet(
            "QPushButton#searchbtn{background:transparent;border: 0px;}"
        )  # Transparent display
        self.username = ""

        self._searchBtn.setFixedSize(24, 24)
        self._searchBtn.setCursor(Qt.ArrowCursor)

        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        buttonSize = self._searchBtn.sizeHint()
        self.setObjectName("searchEdit")

        self.setStyleSheet(
            "QLineEdit#searchEdit{min-height: 26px;max-height: 26px;padding-right: %dpx; border-radius: 13px;background: #666666;border: 1px;}"
            % (buttonSize.width() + frameWidth + 1)
        )
        self.setMinimumSize(
            max(
                self.minimumSizeHint().width(), buttonSize.width() + frameWidth * 2 + 2
            ),
            max(
                self.minimumSizeHint().height(),
                buttonSize.height() + frameWidth * 2 + 2,
            ),
        )
        self._searchBtn.clicked.connect(self.sendSearch)

    def resizeEvent(self, event):
        buttonSize = self._searchBtn.sizeHint()
        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self._searchBtn.move(
            self.rect().right() - frameWidth - buttonSize.width() - 3,
            (self.rect().bottom() - buttonSize.height() + 5) / 2,
        )
        super(SearchWidget, self).resizeEvent(event)

    def sendSearch(self):
        text = self.text()
        self.sendSearchSig.emit(text)

    def setUsername(self, username):
        self.username = username
