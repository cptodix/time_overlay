# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for application bootstrap helpers."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from time_overlay.app import _acquire_lock, _configure_qt_platform


class SingleInstanceTests(unittest.TestCase):
    def test_second_lock_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "time-overlay.lock"
            first = _acquire_lock(path)
            self.assertIsNotNone(first)
            assert first is not None
            try:
                self.assertIsNone(_acquire_lock(path))
            finally:
                first.unlock()


class PlatformSelectionTests(unittest.TestCase):
    def test_wayland_uses_xwayland_when_available(self) -> None:
        env = {"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"}
        with patch.dict(os.environ, env, clear=True):
            _configure_qt_platform()
            self.assertEqual(os.environ.get("QT_QPA_PLATFORM"), "xcb")

    def test_native_wayland_opt_out(self) -> None:
        env = {
            "XDG_SESSION_TYPE": "wayland",
            "DISPLAY": ":0",
            "TIME_OVERLAY_NATIVE_WAYLAND": "1",
        }
        with patch.dict(os.environ, env, clear=True):
            _configure_qt_platform()
            self.assertNotIn("QT_QPA_PLATFORM", os.environ)

    def test_explicit_platform_wins(self) -> None:
        env = {
            "XDG_SESSION_TYPE": "wayland",
            "DISPLAY": ":0",
            "QT_QPA_PLATFORM": "wayland",
        }
        with patch.dict(os.environ, env, clear=True):
            _configure_qt_platform()
            self.assertEqual(os.environ["QT_QPA_PLATFORM"], "wayland")

    def test_wayland_without_xwayland_stays_native(self) -> None:
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=True):
            _configure_qt_platform()
            self.assertNotIn("QT_QPA_PLATFORM", os.environ)


if __name__ == "__main__":
    unittest.main()
