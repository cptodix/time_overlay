# SPDX-License-Identifier: GPL-3.0-or-later
"""Small custom widgets used by the overlay."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class DragHandle(QWidget):
    """A visible top-right handle that moves the frameless parent window."""

    def __init__(self, window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._dragging = False
        self._offset = QPoint()
        self.setFixedSize(24, 16)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Drag to move")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 16))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 5, 5)

        painter.setBrush(QColor(255, 255, 255, 150))
        for x in (8, 16):
            for y in (4, 8, 12):
                painter.drawEllipse(QPointF(x, y), 1.4, 1.4)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Prefer the compositor/WM move operation. It is required on
            # Wayland, where clients cannot position their own toplevels.
            window_handle = self._window.windowHandle()
            if window_handle is not None and window_handle.startSystemMove():
                event.accept()
                return
            self._dragging = True
            self._offset = (
                event.globalPosition().toPoint()
                - self._window.frameGeometry().topLeft()
            )
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self._window.move(event.globalPosition().toPoint() - self._offset)
            event.accept()
        else:
            self._dragging = False
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)


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
            # Let the compositor/WM perform the resize when supported. This
            # is the portable path on Wayland; fall back to manual geometry.
            window_handle = self._window.windowHandle()
            if window_handle is not None and window_handle.startSystemResize(
                Qt.Edge.BottomEdge | Qt.Edge.RightEdge
            ):
                event.accept()
                return
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
