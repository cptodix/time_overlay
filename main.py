#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""PyInstaller / direct-run entry point."""

from time_overlay.app import main

if __name__ == "__main__":
    raise SystemExit(main())
