# SPDX-License-Identifier: GPL-3.0-or-later
"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QLockFile, QStandardPaths, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

try:
    # Ensure PyInstaller collects Qt's SVG icon engine and libraries.
    from PyQt6 import QtSvg  # noqa: F401
except ImportError:  # pragma: no cover - QtSvg ships with PyQt6
    pass

from . import __version__
from .theme import dark_palette
from .window import TimeOverlayWindow


def _icon_path() -> Path | None:
    """Locate the SVG icon in source runs and PyInstaller one-file builds."""
    path = (
        Path(__file__).resolve().parent.parent / "packaging" / "time_overlay_icon.svg"
    )
    return path if path.is_file() else None


def _lock_path() -> Path:
    config_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    if not config_dir:
        config_dir = str(Path.home() / ".config" / "time-overlay")
    return Path(config_dir) / "time-overlay.lock"


def _acquire_lock(path: Path) -> QLockFile | None:
    """Return a held lock, or None when another copy already owns it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(path))
    if lock.tryLock(100):
        return lock
    return None


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setPalette(dark_palette())
    app.setApplicationName("Time Overlay")
    app.setApplicationDisplayName("Time Overlay")
    app.setOrganizationName("Time Overlay")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(True)

    lock = _acquire_lock(_lock_path())
    if lock is None:
        box = QMessageBox()
        box.setWindowTitle("Time Overlay")
        box.setText("Time Overlay is already running.")
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        box.exec()
        return 0

    icon_path = _icon_path()
    if icon_path is not None:
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            app.setWindowIcon(icon)

    window = TimeOverlayWindow()
    window.show()
    try:
        return app.exec()
    finally:
        lock.unlock()
