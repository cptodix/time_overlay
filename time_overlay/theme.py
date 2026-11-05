# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt stylesheets for the overlay and its dialogs."""

from __future__ import annotations

ACCENT = "#4da3ff"
ACCENT_RGB = "77, 163, 255"

ACTIVE_STYLESHEET = f"""
#container {{
    background-color: rgba(20, 20, 20, 210);
    border: 1px solid rgba(255, 255, 255, 34);
    border-radius: 20px;
}}
QLabel#panelTitle {{
    color: rgba(255, 255, 255, 120);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding-left: 3px;
}}
QPushButton {{
    color: #f4f4f4;
    background-color: rgba(255, 255, 255, 14);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 10px;
    padding: 9px 12px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 30);
    border-color: rgba(255, 255, 255, 60);
}}
QPushButton:pressed {{
    background-color: rgba(255, 255, 255, 46);
}}
QPushButton:checked {{
    background-color: rgba({ACCENT_RGB}, 92);
    border-color: rgba({ACCENT_RGB}, 200);
}}
QPushButton:disabled {{
    color: rgba(255, 255, 255, 70);
    background-color: rgba(255, 255, 255, 6);
    border-color: rgba(255, 255, 255, 12);
}}
QPushButton#modeButton {{
    text-align: left;
    padding: 11px 16px;
}}
QPushButton#startButton {{
    background-color: rgba({ACCENT_RGB}, 92);
    border-color: rgba({ACCENT_RGB}, 190);
}}
QPushButton#startButton:hover {{
    background-color: rgba({ACCENT_RGB}, 135);
}}
QPushButton#subtleButton {{
    color: rgba(255, 255, 255, 150);
    background-color: transparent;
    border: none;
    font-size: 12px;
    font-weight: 500;
    padding: 6px;
}}
QPushButton#subtleButton:hover {{
    color: #ffffff;
    background-color: rgba(255, 255, 255, 18);
}}
"""

GHOST_STYLESHEET = """
#container {
    background-color: rgba(0, 0, 0, 0);
    /* Keep the same 1px border box as the active style so hiding the
       background does not change the layout geometry or the fitted font. */
    border: 1px solid rgba(0, 0, 0, 0);
    border-radius: 20px;
}
"""

MENU_STYLESHEET = f"""
QMenu {{
    background-color: #1c1c1c;
    color: #f0f0f0;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 24px 7px 14px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: #0d0d0d;
}}
QMenu::item:disabled {{
    color: rgba(255, 255, 255, 90);
}}
QMenu::separator {{
    height: 1px;
    background: #3a3a3a;
    margin: 5px 8px;
}}
"""

DIALOG_STYLESHEET = f"""
QDialog {{
    background-color: #181818;
    color: #f0f0f0;
}}
QLabel {{
    color: #cfcfcf;
    font-size: 13px;
}}
QLabel#titleLabel {{
    color: #ffffff;
    font-size: 19px;
    font-weight: 700;
}}
QLabel#hintLabel {{
    color: rgba(255, 255, 255, 120);
    font-size: 11px;
}}
QLabel#fieldLabel {{
    color: rgba(255, 255, 255, 140);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QSpinBox {{
    background-color: #262626;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    padding: 7px 8px;
    min-width: 56px;
    font-size: 18px;
    font-weight: 600;
    selection-background-color: #2f7fd6;
    selection-color: #ffffff;
}}
QSpinBox:focus {{
    border-color: {ACCENT};
}}
QSpinBox QLineEdit {{
    color: #ffffff;
    background-color: transparent;
    selection-background-color: #2f7fd6;
    selection-color: #ffffff;
}}
QPushButton {{
    color: #f4f4f4;
    background-color: rgba(255, 255, 255, 14);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 30);
}}
QPushButton#stepButton {{
    padding: 0;
    font-size: 17px;
    font-weight: 700;
    color: rgba(255, 255, 255, 190);
    background-color: rgba(255, 255, 255, 10);
    border: 1px solid rgba(255, 255, 255, 24);
    border-radius: 7px;
}}
QPushButton#stepButton:hover {{
    background-color: rgba(255, 255, 255, 24);
    color: #ffffff;
}}
QPushButton#presetButton {{
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 500;
    color: rgba(255, 255, 255, 170);
    background-color: rgba(255, 255, 255, 8);
}}
QPushButton#presetButton:hover {{
    background-color: rgba(255, 255, 255, 22);
    color: #ffffff;
}}
QPushButton#primaryButton {{
    background-color: #2f7fd6;
    border-color: #4da3ff;
}}
QPushButton#primaryButton:hover {{
    background-color: #3a91ee;
}}
QPushButton#primaryButton:disabled {{
    background-color: rgba(47, 127, 214, 70);
    border-color: rgba(77, 163, 255, 80);
    color: rgba(255, 255, 255, 90);
}}
"""
