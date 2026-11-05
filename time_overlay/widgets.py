# SPDX-License-Identifier: GPL-3.0-or-later
"""Small custom widgets used by the overlay."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class ResizeGrip(QWidget):
    """A visible bottom-right grip that resizes the frameless parent window."""

    def __init__(self, window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._resizing = False
        self._start_global = QPoint()
        self._start_size = QSize()
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Drag to resize")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 18))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 5, 5)

        painter.setPen(QPen(QColor(255, 255, 255, 135), 1.3))
        width, height = self.width(), self.height()
        for offset in (4, 8, 12):
            painter.drawLine(width - offset, height - 2, width - 2, height - offset)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._resizing = True
            self._start_global = event.globalPosition().toPoint()
            self._start_size = self._window.size()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self._start_global
            minimum = self._window.minimumSize()
            width = max(minimum.width(), self._start_size.width() + delta.x())
            height = max(minimum.height(), self._start_size.height() + delta.y())
            self._window.resize(width, height)
            event.accept()
        else:
            self._resizing = False
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)
