# SPDX-License-Identifier: GPL-3.0-or-later
"""Headless UI smoke tests (run with QT_QPA_PLATFORM=offscreen)."""

from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from time_overlay.app import _icon_path
from time_overlay.window import Mode, TimeOverlayWindow


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        settings = QSettings(
            os.path.join(self.temp_dir.name, "settings.ini"),
            QSettings.Format.IniFormat,
        )
        self.window = TimeOverlayWindow(settings=settings)

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp_dir.cleanup()

    def test_window_flags_and_attributes(self) -> None:
        flags = self.window.windowFlags()
        for flag in (
            Qt.WindowType.FramelessWindowHint,
            Qt.WindowType.WindowStaysOnTopHint,
            Qt.WindowType.Tool,
            Qt.WindowType.WindowDoesNotAcceptFocus,
        ):
            self.assertTrue(flags & flag, f"missing window flag: {flag}")
        self.assertTrue(
            self.window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        )
        self.assertTrue(self.window.testAttribute(Qt.WidgetAttribute.WA_Hover))
        self.assertTrue(self.window.hasMouseTracking())

    def test_app_icon_loads(self) -> None:
        path = _icon_path()
        self.assertIsNotNone(path)
        assert path is not None
        self.assertTrue(path.is_file())
        icon = QIcon(str(path))
        self.assertFalse(icon.isNull())

    def test_starts_in_clock_ghost_mode(self) -> None:
        self.assertEqual(self.window.mode, Mode.CLOCK)
        self.assertTrue(self.window.left_panel.isHidden())
        self.assertTrue(self.window.right_panel.isHidden())
        self.assertIn("rgba(0, 0, 0, 0)", self.window.container.styleSheet())

    def test_hover_reveals_panels_and_background(self) -> None:
        self.window.set_hovered(True)
        self.assertFalse(self.window.left_panel.isHidden())
        self.assertTrue(self.window.right_panel.isHidden())  # clock has no controls
        self.assertIn("rgba(20, 20, 20, 210)", self.window.container.styleSheet())

        self.window.set_mode(Mode.STOPWATCH)
        self.assertFalse(self.window.right_panel.isHidden())
        self.window.set_hovered(False)
        self.assertTrue(self.window.left_panel.isHidden())
        self.assertTrue(self.window.right_panel.isHidden())

    def test_mode_text(self) -> None:
        self.window.set_mode(Mode.STOPWATCH)
        self.assertEqual(self.window.time_label.text(), "00:00:00.00")
        self.window.set_mode(Mode.TIMER)
        self.assertEqual(self.window.time_label.text(), "00:05:00")

    def test_timer_add_minute(self) -> None:
        self.window.set_mode(Mode.TIMER)
        self.window._add_minute()
        self.assertAlmostEqual(self.window._timer.remaining(), 360.0)
        self.assertEqual(self.window.time_label.text(), "00:06:00")

    def test_clock_format_toggle(self) -> None:
        self.assertTrue(self.window._use_24h)
        self.window._toggle_clock_format()
        self.assertFalse(self.window._use_24h)
        self.assertTrue(self.window.time_label.text().endswith(("AM", "PM")))

    def test_clock_format_toggle_keeps_active_mode_text(self) -> None:
        self.window.set_mode(Mode.STOPWATCH)
        self.window._toggle_clock_format()
        self.assertEqual(self.window.time_label.text(), "00:00:00.00")

    def test_font_grows_with_window(self) -> None:
        self.window.show()
        self.app.processEvents()

        self.window.resize(700, 220)
        self.app.processEvents()
        self.window._fit_time_font()
        small = self.window.time_label.font().pointSize()

        self.window.resize(1200, 400)
        self.app.processEvents()
        self.window._fit_time_font()
        large = self.window.time_label.font().pointSize()

        self.assertGreater(large, small)

    def test_timer_finishes_in_background(self) -> None:
        self.window.set_mode(Mode.TIMER)
        self.window._timer.set_duration(0.15)
        self.window._update_timer_text()
        self.window._toggle_active()
        self.assertTrue(self.window._timer.running)

        self.window.set_mode(Mode.CLOCK)
        QTest.qWait(400)
        self.app.processEvents()

        self.assertFalse(self.window._timer.running)
        self.assertEqual(self.window._timer.remaining(), 0.0)

        self.window.set_mode(Mode.TIMER)
        self.assertEqual(self.window.time_label.text(), "00:00:00")
        self.assertTrue(self.window._flash_timer.isActive())

    def test_resize_grip_resizes_window(self) -> None:
        self.window.resize(960, 300)
        self.window.show()
        self.window.set_hovered(True)
        self.app.processEvents()

        grip = self.window.size_grip
        QTest.mousePress(grip, Qt.MouseButton.LeftButton, pos=QPoint(8, 8))
        start_global = grip.mapToGlobal(QPoint(8, 8))
        move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(8, 8),
            QPointF(start_global.x() + 80, start_global.y() + 50),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(grip, move)
        QTest.mouseRelease(grip, Qt.MouseButton.LeftButton, pos=QPoint(8, 8))
        self.app.processEvents()

        self.assertGreater(self.window.width(), 960)
        self.assertGreater(self.window.height(), 300)

    def test_ghost_mode_gives_text_more_room(self) -> None:
        self.window.show()
        self.app.processEvents()
        self.window.resize(960, 300)
        self.app.processEvents()

        self.window.set_hovered(True)
        self.app.processEvents()
        self.window._fit_time_font()
        active_size = self.window.time_label.font().pointSize()

        self.window.set_hovered(False)
        self.app.processEvents()
        self.window._fit_time_font()
        ghost_size = self.window.time_label.font().pointSize()

        self.assertGreater(ghost_size, active_size)


if __name__ == "__main__":
    unittest.main()
