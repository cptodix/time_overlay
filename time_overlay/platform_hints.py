# SPDX-License-Identifier: GPL-3.0-or-later
"""Platform-specific always-on-top reinforcement.

Qt's ``WindowStaysOnTopHint`` is enough for ordinary windows, but full-screen
applications on Windows can still cover a topmost overlay. Windows therefore
gets a periodic native ``SetWindowPos`` call. On Linux we rely on Qt/X11/
Wayland window hints plus a periodic ``raise_()`` restack attempt, with an
optional X11 dock hint for stubborn window managers.
"""

from __future__ import annotations

import logging
import os
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# Windows constants
_HWND_TOPMOST = -1
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010


def setup_platform_hints(window) -> None:
    """Apply platform-specific window hints and start enforcement timers."""
    if sys.platform == "win32":
        _setup_windows(window)
    elif sys.platform.startswith("linux"):
        _setup_linux(window)


def reassert_topmost(window) -> None:
    """Re-apply the topmost state immediately (called after the window shows)."""
    if sys.platform == "win32":
        _windows_set_topmost(window)
    elif sys.platform.startswith("linux"):
        # Best-effort restack for X11 and compositors that honor raise
        # requests. Never raise over our own modal dialog or context menu.
        if window.isVisible() and not _popup_is_active():
            window.raise_()


def _popup_is_active() -> bool:
    return (
        QApplication.activeModalWidget() is not None
        or QApplication.activePopupWidget() is not None
    )


# --------------------------------------------------------------------- Windows
def _setup_windows(window) -> None:
    try:
        import ctypes  # noqa: F401  (availability check)
    except Exception:  # pragma: no cover - only on Windows
        logger.exception("ctypes is unavailable; cannot enforce topmost state")
        return

    _windows_set_topmost(window)

    timer = QTimer(window)
    timer.setInterval(2000)
    timer.timeout.connect(lambda: _windows_set_topmost(window))
    timer.start()
    # Keep a strong reference so the timer is not collected with the closure.
    window._topmost_timer = timer  # type: ignore[attr-defined]


def _windows_set_topmost(window) -> None:
    if sys.platform != "win32":
        return
    if _popup_is_active():
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        hwnd = wintypes.HWND(int(window.winId()))
        user32.SetWindowPos(
            hwnd,
            wintypes.HWND(_HWND_TOPMOST),
            0,
            0,
            0,
            0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE,
        )
    except Exception:
        logger.exception("Failed to enforce the Windows topmost state")


# ----------------------------------------------------------------------- Linux
def _setup_linux(window) -> None:
    platform = QGuiApplication.platformName().lower()
    logger.debug("Linux platform plugin: %s", platform)

    if platform == "xcb":
        try:
            if os.environ.get("TIME_OVERLAY_X11_DOCK") == "1":
                window.setAttribute(Qt.WidgetAttribute.WA_X11NetWmWindowTypeDock, True)
            else:
                window.setAttribute(
                    Qt.WidgetAttribute.WA_X11NetWmWindowTypeUtility, True
                )
        except Exception:
            logger.exception("Failed to apply X11 window-type hints")
    else:
        # Wayland compositors decide whether a client may stay above others.
        # Qt.Tool + WindowStaysOnTopHint are the best portable hints available.
        logger.debug("Non-X11 Linux session; relying on Qt topmost hints")

    # On X11, raise() is the most portable way to recover from a WM lowering
    # the overlay when it loses focus. Some Wayland compositors ignore it.
    timer = QTimer(window)
    timer.setInterval(2000)
    timer.timeout.connect(lambda: reassert_topmost(window))
    timer.start()
    window._linux_topmost_timer = timer  # type: ignore[attr-defined]
