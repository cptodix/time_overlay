#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the application SVG icon to PNG and an optional Windows ICO.

QtSvg renders the vector source directly into a QImage without needing a
window/display server. Pillow handles resizing and the multi-size ICO container.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

DEFAULT_SVG = Path(__file__).with_name("time_overlay_icon.svg")
MASTER_SIZE = 1024
PNG_SIZE = 256

_ICO_SIZES = [
    (16, 16),
    (24, 24),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]


def _render_svg(svg_path: Path, size: int = MASTER_SIZE) -> Image.Image:
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise ValueError(f"Invalid or unreadable SVG icon: {svg_path}")

    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    try:
        renderer.render(painter)
    finally:
        painter.end()

    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = image.width(), image.height()
    pointer = image.bits()
    pointer.setsize(image.sizeInBytes())
    return Image.frombytes("RGBA", (width, height), bytes(pointer))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path, help="Output PNG path (256x256)")
    parser.add_argument("--ico", type=Path, help="Optional Windows ICO path")
    parser.add_argument(
        "--svg",
        type=Path,
        default=DEFAULT_SVG,
        help="Source SVG icon (default: packaging/time_overlay_icon.svg)",
    )
    args = parser.parse_args()

    master = _render_svg(args.svg)

    args.png.parent.mkdir(parents=True, exist_ok=True)
    master.resize((PNG_SIZE, PNG_SIZE), Image.Resampling.LANCZOS).save(args.png)

    if args.ico:
        args.ico.parent.mkdir(parents=True, exist_ok=True)
        master.save(args.ico, format="ICO", sizes=_ICO_SIZES)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
