# SPDX-License-Identifier: GPL-3.0-or-later
"""Small custom widgets used by the overlay."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class DragHandle(QWidget):
    """A visible top-right handle that moves the frameless parent window."""

    def __init__(self, window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._dragging = False
        self._offset = QPoint()
        self.setFixedHeight(14)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Drag to move")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 22))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 5, 5)

        painter.setBrush(QColor(255, 255, 255, 170))
        center = self.width() / 2.0
        middle = self.height() / 2.0
        for offset in (-16, -8, 0, 8, 16):
            painter.drawEllipse(QPointF(center + offset, middle), 1.5, 1.5)
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


class TimeField(QWidget):
    """A small integer field whose digits are painted by this widget.

    ``QSpinBox`` delegates its text to an internal ``QLineEdit``. Under some
    native styles/platform palettes that editor ignores the stylesheet color,
    which makes the value invisible even though editing still works. Painting
    the digits directly with ``QPainter`` removes that dependency while keeping
    keyboard, wheel, and focus behaviour.
    """

    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        value: int = 0,
        minimum: int = 0,
        maximum: int = 99,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._minimum = int(minimum)
        self._maximum = int(maximum)
        self._value = self._clamp(value)
        self._replace_on_next_digit = True
        self._caret_visible = True

        self._caret_timer = QTimer(self)
        self._caret_timer.setInterval(530)
        self._caret_timer.timeout.connect(self._blink_caret)

        font = QFont(self.font())
        font.setPixelSize(18)
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setMinimumWidth(64)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # ------------------------------------------------------------------ API
    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:
        value = self._clamp(value)
        if value == self._value:
            return
        self._value = value
        self.update()
        self.valueChanged.emit(value)

    def _clamp(self, value: int) -> int:
        return max(self._minimum, min(self._maximum, int(value)))

    # --------------------------------------------------------------- painting
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        border = QColor("#4da3ff") if self.hasFocus() else QColor("#3a3a3a")
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(QColor("#262626"))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8
        )

        font = QFont(self.font())
        font.setPixelSize(18)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))

        text = str(self._value)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

        if self.hasFocus() and self._caret_visible:
            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(text)
            x = (self.width() + text_width) / 2.0 + 2.0
            top = (self.height() - metrics.height()) / 2.0 + 3.0
            bottom = top + metrics.height() - 6.0
            painter.setPen(QPen(QColor("#ffffff"), 1.5))
            painter.drawLine(QPointF(x, top), QPointF(x, bottom))

        painter.end()

    # ---------------------------------------------------------------- input
    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._replace_on_next_digit = True
        self._caret_visible = True
        self._caret_timer.start()
        self.update()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self._caret_timer.stop()
        self._caret_visible = True
        self._replace_on_next_digit = True
        self.update()

    def _blink_caret(self) -> None:
        self._caret_visible = not self._caret_visible
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._replace_on_next_digit = True
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            event.accept()
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta:
            self.setValue(self._value + (1 if delta > 0 else -1))
            self._replace_on_next_digit = True
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()

        if key == Qt.Key.Key_Tab:
            self.focusNextPrevChild(True)
            event.accept()
            return
        if key == Qt.Key.Key_Backtab:
            self.focusNextPrevChild(False)
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            event.accept()
            return
        if key == Qt.Key.Key_Up:
            self.setValue(self._value + 1)
            self._replace_on_next_digit = True
            event.accept()
            return
        if key == Qt.Key.Key_Down:
            self.setValue(self._value - 1)
            self._replace_on_next_digit = True
            event.accept()
            return
        if key == Qt.Key.Key_Backspace:
            self.setValue(self._value // 10)
            self._replace_on_next_digit = False
            event.accept()
            return
        if key == Qt.Key.Key_Delete:
            self.setValue(0)
            self._replace_on_next_digit = True
            event.accept()
            return

        text = event.text()
        if text.isdigit():
            digit = int(text)
            if self._replace_on_next_digit:
                new_value = digit
            else:
                new_value = min(self._value * 10 + digit, self._maximum)
            self._replace_on_next_digit = False
            self.setValue(new_value)
            event.accept()
            return

        super().keyPressEvent(event)
