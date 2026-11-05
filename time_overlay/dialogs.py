# SPDX-License-Identifier: GPL-3.0-or-later
"""Modal dialog used to set timer durations."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .theme import DIALOG_STYLESHEET
from .widgets import TimeField

_MAX_SECONDS = 99 * 3600 + 59 * 60 + 59

_TIMER_PRESETS = (
    ("1 min", 60),
    ("5 min", 300),
    ("10 min", 600),
    ("15 min", 900),
    ("25 min", 1500),
    ("45 min", 2700),
)


class TimeSetDialog(QDialog):
    """A small dark-themed HH:MM:SS picker with quick presets."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title: str = "Set Timer",
        initial_seconds: float = 300,
        presets: tuple[tuple[str, int], ...] | None = None,
    ) -> None:
        super().__init__(parent)
        self._presets = presets if presets is not None else _TIMER_PRESETS

        # Closing a QDialog is otherwise treated as closing a quit-on-close
        # window. The overlay is a Tool window whose WA_QuitOnClose is set
        # explicitly, so the dialog must never quit the application.
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        self.setWindowTitle(title)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_STYLESHEET)

        initial = max(0, min(_MAX_SECONDS, round(initial_seconds)))
        hours, remainder = divmod(initial, 3600)
        minutes, seconds = divmod(remainder, 60)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        root.addWidget(title_label)

        hint = QLabel("Choose a duration. Presets apply instantly.")
        hint.setObjectName("hintLabel")
        root.addWidget(hint)

        fields = QHBoxLayout()
        fields.setSpacing(12)
        self._hours = self._make_value_field("Hours", hours, 0, 99)
        self._minutes = self._make_value_field("Minutes", minutes, 0, 59)
        self._seconds = self._make_value_field("Seconds", seconds, 0, 59)
        fields.addWidget(self._make_field("HOURS", self._hours))
        fields.addWidget(self._make_field("MINUTES", self._minutes))
        fields.addWidget(self._make_field("SECONDS", self._seconds))
        root.addLayout(fields)

        presets_label = QLabel("QUICK SET")
        presets_label.setObjectName("fieldLabel")
        root.addWidget(presets_label)

        preset_grid = QGridLayout()
        preset_grid.setHorizontalSpacing(8)
        preset_grid.setVerticalSpacing(8)
        for index, (label, seconds_value) in enumerate(self._presets):
            button = QPushButton(label)
            button.setObjectName("presetButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(
                lambda _checked=False, value=seconds_value: self._apply_preset(value)
            )
            preset_grid.addWidget(button, index // 3, index % 3)
        root.addLayout(preset_grid)

        root.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        self._ok_button = QPushButton("Set")
        self._ok_button.setObjectName("primaryButton")
        self._ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ok_button.setDefault(True)
        self._ok_button.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(self._ok_button)
        root.addLayout(buttons)

        for field in (self._hours, self._minutes, self._seconds):
            field.valueChanged.connect(self._update_ok_button)
        self._update_ok_button()

        self.adjustSize()
        self._center_on_parent(parent)
        self._hours.setFocus()

    # ------------------------------------------------------------------ API
    def showEvent(self, event) -> None:
        super().showEvent(event)
        # The overlay itself is a non-activating tool window; make sure the
        # modal picker still comes to the front and can receive keyboard input.
        self.raise_()
        self.activateWindow()

    def seconds(self) -> int:
        return self._total_seconds()

    @classmethod
    def ask(
        cls,
        parent: QWidget | None,
        *,
        title: str,
        initial_seconds: float,
        presets: tuple[tuple[str, int], ...] | None = None,
    ) -> int | None:
        dialog = cls(
            parent,
            title=title,
            initial_seconds=initial_seconds,
            presets=presets,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.seconds()
        return None

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _make_value_field(
        label: str, value: int, minimum: int, maximum: int
    ) -> TimeField:
        field = TimeField(value, minimum, maximum)
        field.setAccessibleName(label)
        field.setToolTip(f"{label}: type a number, use the arrows or +/−")
        return field

    @staticmethod
    def _make_field(label: str, field: TimeField) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        caption = QLabel(label)
        caption.setObjectName("fieldLabel")
        layout.addWidget(caption)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        minus = QPushButton("\u2212")
        plus = QPushButton("+")
        for button in (minus, plus):
            button.setObjectName("stepButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedWidth(26)
            button.setMinimumHeight(36)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(300)
            button.setAutoRepeatInterval(80)

        minus.clicked.connect(lambda: field.setValue(field.value() - 1))
        plus.clicked.connect(lambda: field.setValue(field.value() + 1))

        row.addWidget(minus)
        row.addWidget(field, 1)
        row.addWidget(plus)
        layout.addLayout(row)
        return container

    def _total_seconds(self) -> int:
        return (
            self._hours.value() * 3600
            + self._minutes.value() * 60
            + self._seconds.value()
        )

    def _apply_preset(self, total_seconds: int) -> None:
        total_seconds = max(0, min(_MAX_SECONDS, total_seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self._hours.setValue(hours)
        self._minutes.setValue(minutes)
        self._seconds.setValue(seconds)

    def _update_ok_button(self) -> None:
        self._ok_button.setEnabled(self._total_seconds() > 0)

    def _center_on_parent(self, parent: QWidget | None) -> None:
        if parent is None:
            return
        parent_rect = parent.frameGeometry()
        self.move(parent_rect.center() - self.rect().center())


def ask_for_timer(parent: QWidget | None, initial_seconds: float) -> int | None:
    return TimeSetDialog.ask(
        parent,
        title="Set Timer",
        initial_seconds=initial_seconds,
        presets=_TIMER_PRESETS,
    )
