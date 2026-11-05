# SPDX-License-Identifier: GPL-3.0-or-later
"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

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


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setPalette(dark_palette())
    app.setApplicationName("Time Overlay")
    app.setApplicationDisplayName("Time Overlay")
    app.setOrganizationName("Time Overlay")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(True)

    icon_path = _icon_path()
    if icon_path is not None:
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            app.setWindowIcon(icon)

    window = TimeOverlayWindow()
    window.show()
    return app.exec()
