# SPDX-License-Identifier: GPL-3.0-or-later
"""The frameless, always-on-top overlay window."""

from __future__ import annotations

from datetime import datetime
from enum import Enum, auto

from PyQt6.QtCore import QEvent, QSettings, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .core import (
    CountdownTimer,
    Stopwatch,
    format_clock,
    format_countdown,
    format_stopwatch,
)
from .dialogs import ask_for_timer
from .outlined_label import OutlinedLabel
from .platform_hints import reassert_topmost, setup_platform_hints
from .theme import (
    ACTIVE_STYLESHEET,
    GHOST_STYLESHEET,
    MENU_STYLESHEET,
)
from .widgets import DragHandle, ResizeGrip


class Mode(Enum):
    CLOCK = auto()
    STOPWATCH = auto()
    TIMER = auto()


class TimeOverlayWindow(QWidget):
    """Horizontal overlay: modes on the left, time in the middle, controls right."""

    DEFAULT_SIZE = QSize(960, 300)
    MINIMUM_SIZE = QSize(720, 220)
    CLOCK_FORMAT_KEY = "clock/use24h"
    GEOMETRY_KEY = "window/geometry"

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()

        self._settings = settings or QSettings("time-overlay", "time-overlay")
        self._use_24h = self._settings.value(self.CLOCK_FORMAT_KEY, True, type=bool)

        self._mode = Mode.CLOCK
        self._hovered = False
        self._style_active: bool | None = None
        self._flash_on = False

        self._stopwatch = Stopwatch()
        self._timer = CountdownTimer(300.0)

        self.setWindowTitle("Time Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # Tool windows default to WA_QuitOnClose=False. Make the overlay the
        # explicit quit-on-close window so closing the timer dialog cannot
        # terminate the application.
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, True)
        self.setMouseTracking(True)
        self.setMinimumSize(self.MINIMUM_SIZE)
        self.resize(self.DEFAULT_SIZE)

        self._build_ui()
        self._build_timers()
        self._restore_geometry()

        self.set_mode(Mode.CLOCK)
        self.set_hovered(False)
        setup_platform_hints(self)

        self._update_clock_text()
        self._update_stopwatch_text()
        self._update_timer_text()
        self._schedule_fit()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.container = QFrame(self)
        self.container.setObjectName("container")
        outer.addWidget(self.container)

        root = QHBoxLayout(self.container)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        # --------------------------------------------------------- left panel
        self.left_panel = QWidget(self.container)
        self.left_panel.setFixedWidth(156)
        left = QVBoxLayout(self.left_panel)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)

        left_title = QLabel("MODE")
        left_title.setObjectName("panelTitle")
        left.addWidget(left_title)

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_buttons: dict[Mode, QPushButton] = {}
        for mode, label in (
            (Mode.CLOCK, "Clock"),
            (Mode.STOPWATCH, "Stopwatch"),
            (Mode.TIMER, "Timer"),
        ):
            button = QPushButton(label)
            button.setObjectName("modeButton")
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(42)
            button.clicked.connect(
                lambda _checked=False, selected=mode: self.set_mode(selected)
            )
            self._mode_group.addButton(button)
            self._mode_buttons[mode] = button
            left.addWidget(button)

        left.addSpacing(4)
        self.format_button = QPushButton()
        self.format_button.setObjectName("subtleButton")
        self.format_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.format_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.format_button.setToolTip("Toggle between 12-hour and 24-hour clock")
        self.format_button.clicked.connect(self._toggle_clock_format)
        left.addWidget(self.format_button)

        left.addStretch(1)

        self.quit_button = QPushButton("Quit")
        self.quit_button.setObjectName("subtleButton")
        self.quit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.quit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_button.clicked.connect(self.close)
        left.addWidget(self.quit_button)

        root.addWidget(self.left_panel)

        # ------------------------------------------------------------ center
        center = QWidget(self.container)
        center.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        self.time_label = OutlinedLabel("00:00:00", center)
        center_layout.addWidget(self.time_label)
        root.addWidget(center, 1)

        # -------------------------------------------------------- right panel
        self.right_panel = QWidget(self.container)
        self.right_panel.setFixedWidth(190)
        right = QVBoxLayout(self.right_panel)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)

        right_title = QLabel("CONTROLS")
        right_title.setObjectName("panelTitle")
        right.addWidget(right_title)

        self.start_button = self._make_action_button("Start", self._toggle_active)
        self.start_button.setObjectName("startButton")
        self.reset_button = self._make_action_button("Reset", self._reset_active)
        self.set_button = self._make_action_button("Set", self._set_active_value)

        right.addWidget(self.start_button)
        right.addWidget(self.reset_button)
        right.addWidget(self.set_button)
        right.addStretch(1)

        root.addWidget(self.right_panel)

        # Keep references to the panel contents so hover/ghost mode can hide
        # them without removing the fixed-width columns from the layout.
        self._left_content_widgets = [
            left_title,
            *self._mode_buttons.values(),
            self.format_button,
            self.quit_button,
        ]
        self._right_content_widgets = [
            right_title,
            self.start_button,
            self.reset_button,
            self.set_button,
        ]

        # ----------------------------------------------------------- grips/events
        self.size_grip = ResizeGrip(self, self.container)
        self.size_grip.hide()
        self.drag_handle = DragHandle(self, self.container)
        self.drag_handle.hide()

        # Only the container needs the resize notification used to reposition
        # the two grips; dragging is handled by the explicit drag handle.
        self.container.installEventFilter(self)

        self._position_handles()

    def _make_action_button(self, text: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(38)
        button.clicked.connect(slot)
        return button

    def _build_timers(self) -> None:
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(33)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start()

        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(350)
        self._flash_timer.timeout.connect(self._on_flash_tick)

        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.setInterval(0)
        self._fit_timer.timeout.connect(self._fit_time_font)

    # --------------------------------------------------------------- geometry
    def _restore_geometry(self) -> None:
        restored = False
        stored = self._settings.value(self.GEOMETRY_KEY)
        if stored is not None:
            try:
                restored = self.restoreGeometry(stored)
            except (TypeError, ValueError):
                restored = False

        if restored:
            frame = self.frameGeometry()
            if not any(
                screen.availableGeometry().intersects(frame)
                for screen in QGuiApplication.screens()
            ):
                restored = False

        if not restored:
            self._place_default()

    def _place_default(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        width = min(
            self.DEFAULT_SIZE.width(),
            max(self.MINIMUM_SIZE.width(), area.width() - 120),
        )
        height = min(
            self.DEFAULT_SIZE.height(),
            max(self.MINIMUM_SIZE.height(), area.height() - 160),
        )
        self.resize(width, height)
        x = area.x() + max(0, (area.width() - width) // 2)
        y = area.y() + max(0, area.height() - height - 60)
        self.move(x, y)

    def _center_on_screen(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.x() + max(0, (area.width() - self.width()) // 2)
        y = area.y() + max(0, (area.height() - self.height()) // 2)
        self.move(x, y)

    def _position_handles(self) -> None:
        if hasattr(self, "size_grip"):
            self.size_grip.move(
                max(0, self.container.width() - 22),
                max(0, self.container.height() - 22),
            )
        if hasattr(self, "drag_handle"):
            self.drag_handle.move(
                max(0, self.container.width() - 48),
                2,
            )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_handles()
        self._schedule_fit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._position_handles()
        self._schedule_fit()
        reassert_topmost(self)
        QTimer.singleShot(0, self._refresh_hover_from_cursor)

    # ------------------------------------------------------------------ modes
    @property
    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode) -> None:
        self._mode = mode
        for candidate, button in self._mode_buttons.items():
            button.setChecked(candidate is mode)

        self._update_format_button()
        self._update_active_text()
        self._update_control_labels()
        self._apply_panel_visibility()
        self._sync_flash_state()
        self._schedule_fit()

    def _update_active_text(self) -> None:
        if self._mode is Mode.CLOCK:
            self._update_clock_text()
        elif self._mode is Mode.STOPWATCH:
            self._update_stopwatch_text()
        else:
            self._update_timer_text()

    def _toggle_clock_format(self) -> None:
        self._use_24h = not self._use_24h
        self._settings.setValue(self.CLOCK_FORMAT_KEY, self._use_24h)
        self._update_format_button()
        # The context menu can toggle this while a stopwatch/timer is shown;
        # refresh the active mode instead of forcing the clock text.
        self._update_active_text()
        self._schedule_fit()

    def _update_format_button(self) -> None:
        label = "24-hour clock" if self._use_24h else "12-hour clock"
        self.format_button.setText(label)

    # -------------------------------------------------------------- hover mode
    def set_hovered(self, hovered: bool) -> None:
        if self._hovered == hovered and self.isVisible():
            return
        self._hovered = hovered
        self._apply_panel_visibility()

    def _apply_panel_visibility(self) -> None:
        # The panels themselves stay in the layout so the three columns keep
        # their fixed widths. Only their contents are hidden, which keeps the
        # center column (and therefore the time font) stable in ghost mode.
        left_visible = self._hovered
        for widget in self._left_content_widgets:
            widget.setVisible(left_visible)
        self.format_button.setVisible(left_visible and self._mode is Mode.CLOCK)

        right_visible = self._hovered and self._mode is not Mode.CLOCK
        for widget in self._right_content_widgets:
            widget.setVisible(right_visible)
        self.set_button.setVisible(right_visible and self._mode is Mode.TIMER)

        style_active = self._hovered
        if style_active != self._style_active:
            self.container.setStyleSheet(
                ACTIVE_STYLESHEET if style_active else GHOST_STYLESHEET
            )
            self._style_active = style_active

        if self._hovered:
            self.size_grip.show()
            self.drag_handle.show()
            self.size_grip.raise_()
            self.drag_handle.raise_()
            self._position_handles()
        else:
            self.size_grip.hide()
            self.drag_handle.hide()

    def enterEvent(self, event) -> None:
        self.set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.set_hovered(False)
        super().leaveEvent(event)

    def _refresh_hover_from_cursor(self) -> None:
        if not self.isVisible():
            return
        inside = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        self.set_hovered(inside)

    # ------------------------------------------------------------------ ticker
    def _on_tick(self) -> None:
        # Advance the countdown even when another mode is displayed so it
        # finishes (and beeps) accurately in the background.
        timer_finished = self._timer.tick()
        if timer_finished:
            QApplication.beep()
            if self._mode is Mode.TIMER:
                self._update_control_labels()

        if self._mode is Mode.CLOCK:
            self._update_clock_text()
        elif self._mode is Mode.STOPWATCH:
            self._update_stopwatch_text()
        else:
            self._update_timer_text()
            self._sync_flash_state()

    def _update_clock_text(self) -> None:
        self._set_time_text(format_clock(datetime.now(), self._use_24h))

    def _update_stopwatch_text(self) -> None:
        self._set_time_text(format_stopwatch(self._stopwatch.elapsed()))

    def _update_timer_text(self) -> None:
        self._set_time_text(format_countdown(self._timer.remaining()))

    def _set_time_text(self, text: str) -> None:
        if text == self.time_label.text():
            return
        old_length = len(self.time_label.text())
        self.time_label.setText(text)
        if len(text) != old_length:
            self._schedule_fit()

    def _schedule_fit(self) -> None:
        if hasattr(self, "_fit_timer"):
            self._fit_timer.start()

    def _fit_time_font(self) -> None:
        width = self.time_label.width()
        height = self.time_label.height()
        if width < 24 or height < 24:
            return
        self.time_label.fit_font(width - 16, height - 16)

    # ---------------------------------------------------------------- controls
    def _toggle_active(self) -> None:
        if self._mode is Mode.STOPWATCH:
            self._stopwatch.toggle()
            self._update_stopwatch_text()
        elif self._mode is Mode.TIMER:
            self._timer.toggle()
            if self._timer.running:
                self._stop_flash()
            self._update_timer_text()
            self._sync_flash_state()
        self._update_control_labels()

    def _reset_active(self) -> None:
        if self._mode is Mode.STOPWATCH:
            # Stopwatch reset keeps the watch running from zero.
            self._stopwatch.reset()
            self._update_stopwatch_text()
        elif self._mode is Mode.TIMER:
            if self._timer.running:
                return
            self._timer.reset()
            self._stop_flash()
            self._update_timer_text()
        self._update_control_labels()

    def _set_active_value(self) -> None:
        if self._mode is not Mode.TIMER:
            return
        initial = self._timer.remaining()
        if initial <= 0:
            initial = self._timer.duration
        seconds = ask_for_timer(self, max(1.0, initial))
        if seconds is not None:
            self._timer.set_duration(float(seconds))
            self._stop_flash()
            self._update_timer_text()
        self._update_control_labels()
        QTimer.singleShot(0, self._refresh_hover_from_cursor)

    def _update_control_labels(self) -> None:
        if self._mode is Mode.STOPWATCH:
            running = self._stopwatch.running
            self.reset_button.setEnabled(True)
        elif self._mode is Mode.TIMER:
            running = self._timer.running
            self.reset_button.setEnabled(not running)
        else:
            running = False
            self.reset_button.setEnabled(True)
        self.start_button.setText("Pause" if running else "Start")

    # ------------------------------------------------------------------ flashing
    def _sync_flash_state(self) -> None:
        finished = (
            self._mode is Mode.TIMER
            and not self._timer.running
            and self._timer.remaining() <= 0.0
        )
        if finished:
            self._start_flash()
        else:
            self._stop_flash()

    def _start_flash(self) -> None:
        if self._flash_timer.isActive():
            return
        self._flash_on = False
        self._flash_timer.start()
        self._on_flash_tick()

    def _on_flash_tick(self) -> None:
        self._flash_on = not self._flash_on
        color = "#ff3b30" if self._flash_on else "#ffffff"
        self.time_label.set_outline_color(QColor(color))

    def _stop_flash(self) -> None:
        if self._flash_timer.isActive():
            self._flash_timer.stop()
        if self._flash_on or self.time_label.outline_color() != QColor("#000000"):
            self._flash_on = False
            self.time_label.set_outline_color(QColor("#000000"))

    # --------------------------------------------------------------- events
    def eventFilter(self, obj, event) -> bool:
        if obj is self.container and event.type() == QEvent.Type.Resize:
            self._position_handles()
            return False
        return super().eventFilter(obj, event)

    # --------------------------------------------------------------- context menu
    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLESHEET)

        version_action = menu.addAction(f"Time Overlay v{__version__}")
        version_action.setEnabled(False)
        menu.addSeparator()

        center_action = menu.addAction("Center on screen")
        format_action = menu.addAction(
            "Use 12-hour clock" if self._use_24h else "Use 24-hour clock"
        )
        menu.addSeparator()
        quit_action = menu.addAction("Quit")

        chosen = menu.exec(event.globalPos())
        if chosen is center_action:
            self._center_on_screen()
        elif chosen is format_action:
            self._toggle_clock_format()
        elif chosen is quit_action:
            self.close()

        QTimer.singleShot(0, self._refresh_hover_from_cursor)

    # -------------------------------------------------------------------- close
    def closeEvent(self, event) -> None:
        self._tick_timer.stop()
        self._flash_timer.stop()
        self._fit_timer.stop()
        self._settings.setValue(self.GEOMETRY_KEY, self.saveGeometry())
        self._settings.sync()
        super().closeEvent(event)
