# SPDX-License-Identifier: GPL-3.0-or-later
"""A QLabel that paints text with a thick contrasting outline."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QLabel, QSizePolicy


class OutlinedLabel(QLabel):
    """Draws its text as a QPainterPath with a white fill and black stroke.

    The widget never paints its normal QLabel background or text; everything is
    rendered in :meth:`paintEvent` so the outline is always drawn behind the
    glyphs. It is mouse-transparent, which lets the parent window handle
    dragging when the user grabs the time text.
    """

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self._outline_width = 3.0
        self._outline_color = QColor("#000000")
        self._fill_color = QColor("#ffffff")

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(0, 0)
        self.setFont(self._base_font())

    # ------------------------------------------------------------------ API
    @property
    def outline_width(self) -> float:
        return self._outline_width

    def set_outline_width(self, width: float) -> None:
        self._outline_width = max(0.0, float(width))
        self.update()

    def outline_color(self) -> QColor:
        return QColor(self._outline_color)

    def set_outline_color(self, color: QColor | str) -> None:
        self._outline_color = QColor(color)
        self.update()

    def set_fill_color(self, color: QColor | str) -> None:
        self._fill_color = QColor(color)
        self.update()

    # ------------------------------------------------------------- geometry
    def sizeHint(self) -> QSize:
        return QSize(640, 200)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)

    def fit_font(self, max_width: float, max_height: float) -> None:
        """Choose the largest point size whose rendered path fits the box."""
        text = self.text()
        if not text or max_width <= 0 or max_height <= 0:
            return

        # Leave room for the stroke on every side.
        usable_width = max_width - 2.0 * self._outline_width
        usable_height = max_height - 2.0 * self._outline_width
        if usable_width <= 1 or usable_height <= 1:
            return

        font = QFont(self.font())
        low, high = 6, 1000
        best = low
        while low <= high:
            middle = (low + high) // 2
            font.setPointSize(middle)
            bounds = self._text_path(font, text).boundingRect()
            if bounds.width() <= usable_width and bounds.height() <= usable_height:
                best = middle
                low = middle + 1
            else:
                high = middle - 1

        if best != self.font().pointSize():
            font.setPointSize(best)
            self.setFont(font)
        self.update()

    # ---------------------------------------------------------------- paint
    def paintEvent(self, event) -> None:
        text = self.text()
        if not text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        path = self._text_path(self.font(), text)
        bounds = path.boundingRect()

        # Center the visual glyph bounds rather than the font's line box.
        x = (self.width() - bounds.width()) / 2.0 - bounds.left()
        y = (self.height() - bounds.height()) / 2.0 - bounds.top()
        path.translate(x, y)

        pen = QPen(self._outline_color)
        pen.setWidthF(self._outline_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(self._fill_color)
        painter.drawPath(path)
        painter.end()

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _base_font() -> QFont:
        font = QFont()
        font.setFamilies(
            ["DejaVu Sans Mono", "Consolas", "Menlo", "Liberation Mono", "Courier New"]
        )
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setWeight(QFont.Weight.Bold)
        font.setPointSize(72)
        return font

    @staticmethod
    def _text_path(font: QFont, text: str) -> QPainterPath:
        path = QPainterPath()
        path.addText(QPointF(0.0, 0.0), font, text)
        return path
