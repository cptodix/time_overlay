# Agent rules

These rules apply to every agent (including subagents) working in this repository.

## Image / screenshot budget (hard rule)

The model request fails when a conversation accumulates more than 30 attached
images (`Too many images in request`). Keep a large safety margin.

- **Never attach or read more than 5 images in a single session.** Treat 5 as
  the hard cap, not a target.
- **Never re-read an image that is already in the conversation.** If you need
  to check it again, refer to the earlier observation or inspect the pixels
  numerically.
- **Prefer programmatic verification over screenshots.** Before reading an
  image, try:
  - `QWidget.grab()` + `QImage.pixelColor()` / histogram checks (text contrast,
    colors, glyph presence),
  - `QFontMetrics.horizontalAdvance()` for layout/clipping checks,
  - widget geometry, `isVisible()`, `isEnabled()` assertions,
  - Pillow pixel sampling for PNGs already on disk.
- **One screenshot per validation pass, maximum.** Combine several states into
  a single contact-sheet image with Pillow if a visual check is unavoidable,
  then read only that one file.
- **Do not ask subagents to read screenshots.** Give them textual assertions or
  pixel-analysis scripts instead.
- **Delete old screenshot files** (for example under `/tmp/opencode/...`) as
  soon as they are no longer needed.
- If you have already read 3 images in a session, switch to numeric/pixel
  checks for the rest of the task.

## Code conventions

- Keep `time_overlay/core.py` free of Qt imports.
- Run `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`,
  `ruff check .`, and `ruff format --check .` before handing work back.
- Keep the three-column layout fixed; hide panel contents, never the panels.
