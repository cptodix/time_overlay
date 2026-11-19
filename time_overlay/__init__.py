# SPDX-License-Identifier: GPL-3.0-or-later
"""Time Overlay - an always-on-top clock, stopwatch and countdown timer."""

try:
    from ._version import __version__
except ImportError:  # source checkout without a release stamp
    __version__ = "1.0.0"

__all__ = ["__version__"]
