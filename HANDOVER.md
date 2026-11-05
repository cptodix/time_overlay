# Time Overlay — Handover / Maintainer Notes

**Snapshot date:** 2026-11-05  
**License:** GPL-3.0-or-later  
**Runtime stack:** Python 3.10+, PyQt6 6.6+  
**Build stack:** PyInstaller 6.x, Pillow >=10 (icon generation only), appimagetool for Linux  
**Repository:** `time_overlay` — frameless always-on-top clock / stopwatch / timer overlay for Windows and Linux

> User-facing documentation lives in [README.md](README.md). This file is maintainer/handover context.

This document is the fast path for a new maintainer or agent. It explains what exists, why it was built this way, what is known to be fragile, and what should be checked first.

---

## 1. TL;DR

- The app is a single frameless `QWidget` containing a left mode panel, a center outlined-time label, and a right controls panel.
- All timer/stopwatch logic lives in `time_overlay/core.py` and is Qt-free. Keep it that way — it is what makes the tests fast and deterministic.
- The UI runs from `time_overlay/window.py`; the outlined text is `time_overlay/outlined_label.py`.
- Ghost mode is implemented by hiding both panels and swapping the container stylesheet to fully transparent. The top-level window uses `WA_TranslucentBackground`.
- The app has no keyboard focus by design (`WindowDoesNotAcceptFocus`), so every core action must remain mouse-accessible.
- Packaging is script-driven: `packaging/build_windows.bat` and `packaging/build_linux.sh`. There is no `pyproject.toml` / pip-installable package.
- Releases are manual `workflow_dispatch` runs. The workflow calculates the next `vX.Y.Z` tag from the last tag, runs tests/builds, creates the tag, and publishes the release. It no longer triggers on tag pushes.
- Current test suite: **37 tests**, all passing headlessly. `ruff check .` and `ruff format --check .` pass.
- Biggest known gap: the app's `time_overlay/__init__.py` version is still static `1.0.0`; the release workflow creates tags but does not update the source version.

---

## 2. Repository state at handover

At the time this note was written:

- The implementation and this handover document were present in the working tree (`git status` showed new `time_overlay/`, `tests/`, `packaging/`, `main.py`, `requirements*.txt`, `.github/`, and `HANDOVER.md`).
- `.gitignore` and `README.md` were modified.
- The test suite passed headlessly (37 tests), and ruff checks passed.
- The release workflow YAML was validated structurally, and its version-bump/tag logic was exercised locally in temporary git repositories.
- A Linux AppImage was built and run headlessly during development. The generated `build/`, `dist/`, and `.ruff_cache/` outputs were removed afterward.
- Native Windows building and real X11/Wayland compositor behavior were **not** exercised in the development environment; CI/build scripts cover them conceptually but need a real target machine or GitHub runner to confirm.

Before handing over to a release:

1. Commit and push the working tree.
2. Run the full test suite and ruff checks.
3. Decide whether to bump `time_overlay/__init__.py` to match the intended release tag.
4. Verify repository Actions permissions allow `contents: write`.

---

## 3. Quick start

```bash
# Run from source
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py

# Or as a module
python -m time_overlay

# Headless tests
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v

# Optional lint/format checks (ruff is not in requirements)
python -m pip install ruff
ruff check .
ruff format --check .
```

---

## 4. Architecture

### 4.1 Entry points

```
main.py
  └── time_overlay.app.main()
        └── QApplication
              └── TimeOverlayWindow()
                    └── show() → app.exec()
```

- `main.py` — PyInstaller/direct-run entry point.
- `time_overlay/__main__.py` — enables `python -m time_overlay`.
- `time_overlay/app.py` — creates `QApplication`, sets metadata, creates and shows the window.
- `time_overlay/window.py` — everything UI/state-coordination related.

### 4.2 Widget tree

```
TimeOverlayWindow (QWidget, frameless, translucent)
└── QFrame#container (rounded dark background / fully transparent in ghost mode)
    ├── left_panel (QWidget, fixed 120 px)
    │   ├── "MODE" label
    │   ├── Clock / Stopwatch / Timer buttons (QButtonGroup, checkable)
    │   ├── format button (visible only in Clock mode)
    │   └── Quit button
    ├── center (QWidget, expanding)
    │   └── OutlinedLabel (QPainterPath white fill + black stroke)
    ├── right_panel (QWidget, fixed 96 px)
    │   ├── "CONTROLS" label
    │   ├── Start/Pause
    │   ├── Reset
    │   └── Set (Timer only; hidden in Stopwatch/Clock)
    ├── DragHandle (long top-center bar, hidden in ghost mode)
    └── ResizeGrip (custom 16x16 bottom-right grip, hidden in ghost mode)
```

The left and right panel widgets are **always in the layout** so the three columns keep fixed widths. Ghost/Clock modes hide only panel contents, not the panel containers.

### 4.3 State machines

`time_overlay/core.py` is deliberately Qt-free and takes an injected monotonic clock:

- `Stopwatch`
  - State: `_accumulated` seconds + optional `_started_at`.
  - `elapsed()` = accumulated + (now - started_at) when running.
  - `start()`, `pause()`, `toggle()`, `reset()`.
  - `reset()` zeroes elapsed time **without changing the running state**: a running stopwatch keeps running from zero; a paused one stays paused at zero.

- `CountdownTimer`
  - State: `_duration`, `_remaining`, optional `_deadline`.
  - `remaining()` = deadline - now when running, else `_remaining`.
  - `start()`, `pause()`, `toggle()`, `reset()`, `set_duration()`.
  - `tick()` returns `True` exactly once when a running countdown reaches zero and clears the deadline.
  - Pressing Start after finishing restarts from the last set duration.

Formatters:

- `format_clock(value, use_24h)` — deterministic 12/24-hour format; 12-hour output is manually generated so the `AM/PM` suffix is stable across locales.
- `format_stopwatch(seconds)` — `HH:MM:SS.cc`, truncation with a tiny epsilon to avoid float underflow, capped at `99:59:59.99`.
- `format_countdown(seconds)` — `HH:MM:SS`, rounds **up** (minus epsilon), capped at `99:59:59`.

### 4.4 Tick / data flow

`TimeOverlayWindow._build_timers()` creates:

| Timer | Interval | Purpose |
|---|---:|---|
| `_tick_timer` | 33 ms | Update active mode text; always advance countdown |
| `_flash_timer` | 350 ms | Alternate timer outline red/white when finished |
| `_fit_timer` | 0 ms, single-shot | Coalesce font refits after layout changes |
| Windows topmost timer | 2000 ms | Re-assert `HWND_TOPMOST` (`platform_hints.py`) |

`_on_tick()` always calls `self._timer.tick()` first, **even when another mode is displayed**. This is intentional: a timer running in the background must finish and beep at the right time. If the active mode is Timer, the UI also syncs the flash state and control labels.

Active text updates:

- Clock: `datetime.now()` → `format_clock()`.
- Stopwatch: `Stopwatch.elapsed()` → `format_stopwatch()`.
- Timer: `CountdownTimer.remaining()` → `format_countdown()`.

`_set_time_text()` avoids redundant label updates; it schedules a font refit only when the text length changes.

### 4.5 Hover / ghost mode flow

- `WA_Hover` and `setMouseTracking(True)` are enabled.
- `enterEvent` → `set_hovered(True)`.
- `leaveEvent` → `set_hovered(False)`.
- `_apply_panel_visibility()`:
  - Shows the left panel **contents** when hovered.
  - Shows the right panel **contents** when hovered **and** the mode is not Clock.
  - Keeps the left/right panel containers in the layout at all times, so the center column width (and therefore the fitted font) does not change.
  - Hides `Set` in Stopwatch/Clock; Clock leaves the whole right column blank.
  - Swaps `ACTIVE_STYLESHEET` (`rgba(20,20,20,210)`, 20 px radius, 1 px border) vs `GHOST_STYLESHEET` (`rgba(0,0,0,0)`, 20 px radius, transparent 1 px border). The transparent border is intentional: it keeps the layout box identical to active mode.
  - Shows/hides the drag and resize grips.
  - Does **not** schedule a font refit; hover must not change the time size.
- `_refresh_hover_from_cursor()` is scheduled after show, context menus, and dialogs because opening a popup can fire `leaveEvent` even if the cursor returns to the window afterward.

### 4.6 Drag and resize flow

- `DragHandle` is a long, horizontally centered bar across the top of the container. It is the only window-drag mechanism, visible on hover and hidden in ghost mode.
- `ResizeGrip` (custom 16×16 bottom-right grip) resizes the top-level window, clamped to `MINIMUM_SIZE` (720×220).
- Both grips first try `QWindow.startSystemMove()` / `QWindow.startSystemResize()` so the compositor/WM can perform the operation. This is the portable path on Wayland. If either returns `False`, they fall back to manual `move()`/`resize()` geometry, which is the reliable path on X11/Windows.
- Both grips are direct children of the container, not part of a panel, so they are unaffected by panel-content visibility.
- The old drag-anywhere event filters/mouse overrides were removed to avoid Linux input quirks and accidental drags. The container event filter now only repositions the grips on resize.
- Buttons keep their own mouse behavior; nothing else starts a window drag.

### 4.7 Persistence

`TimeOverlayWindow` uses `QSettings("time-overlay", "time-overlay")`:

| Key | Type | Meaning |
|---|---|---|
| `clock/use24h` | bool | Clock format |
| `window/geometry` | `QByteArray` | `saveGeometry()` blob |

Approximate locations:

- Linux: `~/.config/time-overlay/time-overlay.conf`
- Windows: `HKCU\Software\time-overlay\time-overlay`

`_restore_geometry()` also verifies the restored frame intersects an available screen; otherwise it falls back to a bottom-center placement on the primary screen.

Not persisted: mode, timer duration, stopwatch state. The app always starts in Clock mode with a 5-minute timer.

### 4.8 Requirements traceability (original brief)

| Requirement | Implementation |
|---|---|
| Horizontal `[modes][time][controls]` layout | `window.py::_build_ui` |
| Outlined white text with 3 px black stroke | `outlined_label.py::paintEvent` |
| Left Clock/Stopwatch/Timer panel | `window.py::_build_ui` |
| Stopwatch Start/Pause, Reset; Timer Start/Pause, Reset, Set | `window.py::_build_ui`, `_apply_panel_visibility`, `_update_control_labels` |
| Responsive font scaling on resize | `window.py::_fit_time_font`, `outlined_label.py::fit_font` |
| `WA_Hover` + enter/leave ghost mode | `window.py::__init__`, `enterEvent`, `leaveEvent` |
| Ghost background `rgba(0,0,0,0)`; active `rgba(20,20,20,210)` | `theme.py`, `window.py::_apply_panel_visibility` |
| Fixed three-column layout; ghost mode hides contents only | `window.py::_build_ui`, `_apply_panel_visibility` |
| Drag handle to reposition | `widgets.py::DragHandle`, `window.py::_position_handles` |
| Required window flags | `window.py::__init__` |
| Windows `SetWindowPos(HWND_TOPMOST, SWP_NOACTIVATE)` every 2 s | `platform_hints.py::_setup_windows` |
| Linux X11/Wayland dock/utility hints | `platform_hints.py::_setup_linux` |
| Clock, 12/24-hour toggle | `core.py::format_clock`, `window.py::_toggle_clock_format` |
| Stopwatch precision | `core.py::Stopwatch` |
| Timer countdown, set dialog, flash at 00:00 | `core.py::CountdownTimer`, `dialogs.py`, `window.py::_sync_flash_state` |
| App icon from `packaging/time_overlay_icon.svg` | `packaging/make_icon.py`, build scripts, `app.py` |
| Windows one-file `--noconsole` portable EXE | `packaging/build_windows.bat` |
| Linux standalone AppImage | `packaging/build_linux.sh` |
| Manual version-bump release CI | `.github/workflows/release.yml` |

---

## 5. File-by-file map

| Path | Responsibility |
|---|---|
| `main.py` | Direct/PyInstaller entry point |
| `time_overlay/app.py` | `QApplication` bootstrap, dark palette, metadata, and runtime app icon |
| `time_overlay/window.py` | Main window, layout, modes, hover, drag, resize, flash, context menu, settings |
| `time_overlay/outlined_label.py` | `OutlinedLabel`: `QPainterPath` stroke/fill, centering, binary-search font fitting |
| `time_overlay/core.py` | Qt-free `Stopwatch`, `CountdownTimer`, formatters |
| `time_overlay/dialogs.py` | Modal HH:MM:SS picker with presets and explicit −/+ buttons |
| `time_overlay/widgets.py` | `DragHandle`, `ResizeGrip`, and the custom-painted `TimeField` |
| `time_overlay/platform_hints.py` | Windows `SetWindowPos` topmost enforcement; Linux X11 utility/dock attributes |
| `time_overlay/theme.py` | Active/ghost/menu/dialog QSS and the application-wide `dark_palette()` |
| `tests/test_core.py` | Deterministic state-machine and formatter tests |
| `tests/test_ui.py` | Offscreen UI smoke tests |
| `packaging/build_windows.bat` | PyInstaller one-file Windows build |
| `packaging/build_linux.sh` | PyInstaller + AppDir + appimagetool AppImage build |
| `packaging/make_icon.py` | Renders the SVG icon to PNG/ICO via QtSvg + Pillow |
| `packaging/time_overlay_icon.svg` | Canonical app icon (SVG source) |
| `packaging/AppRun` | AppImage launcher |
| `packaging/time-overlay.desktop` | Linux desktop entry |
| `.github/workflows/release.yml` | Manual version-bump release workflow |

---

## 6. Invariants and design decisions to preserve

### 6.1 Keep `core.py` Qt-free

The state machines take an injected `clock` callable so tests use `FakeClock` instead of sleeping. Do not import Qt into `core.py`; it makes the tests slower and less deterministic.

### 6.2 Active mode owns the label

Any global setting change that affects the clock must refresh the **active mode's** text, not blindly the clock text. `_toggle_clock_format()` calls `_update_active_text()` for exactly this reason. An earlier bug replaced the stopwatch display with the clock when the format was toggled from the context menu while in Stopwatch mode. There is a regression test for it.

### 6.3 Timer must tick in every mode

`_on_tick()` always advances the countdown, even when Clock or Stopwatch is displayed. This is required for background timer completion and the beep. The flash is intentionally only started in Timer mode; switching to Timer after a background finish starts the flash via `_sync_flash_state()`.

### 6.4 Timer display uses ceil; stopwatch uses truncation

`format_countdown()` rounds up (with `1e-9` epsilon) so a 5:00 timer displays `00:05:00` until the first full second has elapsed. `format_stopwatch()` truncates to centiseconds with a `1e-6` epsilon to fix floating-point underflow. Do not “simplify” either to plain `round()` without checking the visual behavior.

### 6.5 Font fitting is deferred

`_schedule_fit()` starts a 0 ms single-shot timer. This waits for Qt's layout pass after resize, mode change, panel visibility change, or text-length change. If you call `fit_font()` directly inside `resizeEvent`, you may fit against stale widget geometry.

`OutlinedLabel.fit_font()`:

- Binary-searches point size from 6 to 1000.
- Measures the actual `QPainterPath` bounding rect, not just font metrics.
- Subtracts `2 * outline_width` from the available box.
- Leaves the label size policy `Ignored/Ignored` and minimum size hint `0×0` so the window layout is not forced larger by the font.

### 6.6 Outline width semantics

`OutlinedLabel._outline_width` defaults to `3.0` and is used as the `QPen` width. Because a centered pen puts half the stroke outside the glyph, the visible outer halo is about 1.5 px. If a future requirement means “3 px of visible black outside the glyph,” change the pen width to `2 * outline_width` (or document the change). The current code matches the literal “3 px stroke” interpretation.

### 6.7 Ghost mode is a stylesheet/visibility swap, not a separate window

The top-level widget is `WA_TranslucentBackground`; the `#container` owns the visible background. Ghost mode hides the panel **contents** and both grips, and applies `GHOST_STYLESHEET` with `background-color: rgba(0, 0, 0, 0)`, a 20 px radius, and a transparent **1 px** border. Active mode restores `ACTIVE_STYLESHEET` with `rgba(20, 20, 20, 210)` and a visible 1 px border.

The transparent 1 px border is deliberate: it preserves the exact layout contents rectangle so the center column does not grow and the fitted time font does not change when entering ghost mode. Do not replace it with `border: none`.

The window still captures mouse input over transparent areas. Ghost mode is **not** click-through. Implementing click-through would conflict with hover-to-reveal and would require platform-specific input-shape work.

### 6.8 No keyboard focus is intentional

The window flags are:

```python
FramelessWindowHint | WindowStaysOnTopHint | Tool | WindowDoesNotAcceptFocus
```

plus `WA_ShowWithoutActivating`. This keeps the overlay from stealing focus from the user's active application. Consequences:

- No keyboard shortcuts on the main overlay.
- Every core action must be mouse-accessible: mode buttons, Start/Pause, Reset, Set, Quit, context menu, drag/resize handles.
- The modal set dialog calls `raise_()`/`activateWindow()` in `showEvent`, and it can receive keyboard input; however, if a WM refuses, the −/+ buttons and presets keep it usable with the mouse.

### 6.9 Windows topmost is re-asserted

`platform_hints._setup_windows()` calls `user32.SetWindowPos(HWND_TOPMOST, ..., SWP_NOACTIVATE)` immediately and every 2 seconds via a `QTimer` parented to the window. `reassert_topmost()` is also called from `showEvent`. Do not remove the timer; full-screen presentations can otherwise cover the overlay.

### 6.10 Linux is best-effort

On X11 (`QGuiApplication.platformName() == "xcb"`), the app sets `WA_X11NetWmWindowTypeUtility`. Setting `TIME_OVERLAY_X11_DOCK=1` switches to the dock attribute for stubborn WMs. On Wayland, only Qt's `Tool`/`WindowStaysOnTopHint` hints are available; the compositor decides. This is a platform limitation, not a bug.

A 2-second `QTimer` in `platform_hints._setup_linux()` calls `reassert_topmost()`, which invokes `window.raise_()` on Linux (and native `SetWindowPos` on Windows). It skips raising while `QApplication.activeModalWidget()` or `activePopupWidget()` is set, so the set dialog and context menu are not covered. Wayland compositors may ignore `raise_()` entirely.

### 6.11 The three-column layout is fixed

The left (`120 px`) and right (`96 px`) panel widgets are never removed from the layout. Hover/Clock/Stopwatch/Timer changes only toggle the visibility of their **contents**:

- Clock: left contents visible when hovered; right contents hidden (blank column).
- Stopwatch: left + Start/Pause + Reset; `Set` hidden.
- Timer: left + Start/Pause + Reset + Set.
- Ghost: all panel contents hidden; the columns remain blank.

Do not replace this with `panel.setVisible(False)`. That collapses the column, widens the center, and makes the time font grow—exactly the regression this design fixes.

### 6.12 Stopwatch reset preserves running state

`Stopwatch.reset()` zeroes `_accumulated` and, if running, resets `_started_at` to now. It must **not** stop the watch. A paused stopwatch resets to zero and stays paused. The UI Reset button is always enabled for Stopwatch.

### 6.13 Timer reset is gated

The Timer `Reset` button is disabled while `CountdownTimer.running` is true. `_reset_active()` also guards programmatically and returns without resetting if the timer is running. Users must pause first. On pause/finish, `_update_control_labels()` re-enables Reset.

### 6.14 The set dialog must not quit the app

`Qt.Tool` windows default to `WA_QuitOnClose=False`; `QDialog` defaults to `True`. With `quitOnLastWindowClosed=True`, closing the dialog would be treated as closing the last quit-on-close window and terminate the application.

The fix is explicit:
- `TimeOverlayWindow.__init__` sets `WA_QuitOnClose=True`.
- `TimeSetDialog.__init__` sets `WA_QuitOnClose=False`.

Preserve these attributes if you replace either widget.

### 6.15 The release workflow creates tags **after** builds

The tag should only exist if tests and both builds succeeded. The `prepare` job computes the version but does not tag. The `release` job creates/pushes the tag at `GITHUB_SHA` after the builds. It reuses an existing tag if it points at the same commit, which makes re-running a failed `release` job safe. Do not move tag creation into `prepare` without handling failed builds and reruns.

### 6.16 Use lightweight tags

The release workflow's tag-existence check compares the remote tag SHA directly to `GITHUB_SHA`. That assumes a lightweight tag. If you switch to annotated tags, update the check to peel `^{}` and compare the commit SHA.

### 6.17 The dialog uses a custom-painted `TimeField`, not `QSpinBox`

`QSpinBox` delegates its value to an internal `QLineEdit`. Under some native
styles/platform palettes that editor ignores the stylesheet color, so the
number is invisible even though editing still works (the user can type and the
`Set` button enables, but the field looks empty). Palette and QSS overrides
were not reliable across Breeze/GTK/platform themes.

The dialog therefore uses `widgets.TimeField`, which paints its own rounded
background, white 18 px digits, and caret with `QPainter`. It keeps the
expected behaviour without depending on a native text widget:

- type digits to replace/increment the value,
- Backspace deletes the last digit, Delete resets to zero,
- Up/Down and the mouse wheel step by one,
- Tab/Shift+Tab traverse fields, Enter clears focus,
- `+`/`−` buttons and presets call `setValue()`,
- values are clamped to the field's min/max (for example minutes `0..59`).

`tests/test_ui.py::test_set_dialog_values_are_painted_white` renders the dialog
and asserts white pixels exist inside every field, so this regression cannot
come back silently. Do not replace `TimeField` with `QSpinBox` unless you also
verify digit contrast under the target platform style.

The application-wide `dark_palette()` is still applied in `app.main()` for
labels, buttons, menus, and any future native widgets.

---

## 7. Tests and quality gates

### Commands

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
python -m pip install ruff
ruff check .
ruff format --check .
```

### What is covered

- `tests/test_core.py` (19 tests): stopwatch start/pause/resume/toggle, including reset-while-running and reset-while-paused; countdown start/pause/reset/set/tick/finish/restart; 12/24-hour formatting including midnight/noon; stopwatch/countdown formatting and rounding.
- `tests/test_ui.py` (18 tests): required window flags/attributes and `WA_QuitOnClose`; app icon loading; initial Clock/ghost state; content visibility and background on hover; mode text; clock format toggle and active-mode text preservation; font growth on resize; font/layout stability across ghost mode; background timer completion; stopwatch controls and reset-while-running; timer reset gating; drag handle; resize grip; set-dialog quit behavior; dark palette values; `TimeField` typing/clamping; and a pixel check that every set-dialog value is painted white.

### What is **not** covered automatically

- Native Windows `SetWindowPos`/topmost behavior.
- Real X11/Wayland compositor behavior, full-screen stacking, dock hints.
- Actual AppImage execution and FUSE/no-FUSE paths.
- Native Windows PyInstaller build.
- GitHub Actions runner execution.
- Visual regression/screenshot comparison.

### Test isolation note

The UI tests create a temporary INI `QSettings` file and pass it into `TimeOverlayWindow(settings=...)`, so they do not touch the developer's real config. The window constructor supports this specifically for tests.

### Validated environment

The implementation was exercised with Python 3.13.15, PyQt6 6.11.0 / Qt 6.11.2, and PyInstaller 6.22.3 on Linux. The release workflow uses Python 3.12 on Ubuntu 22.04 and Windows Server (`windows-latest`).

---

## 8. Packaging

### 8.1 Windows — portable single-file EXE

```bat
packaging\build_windows.bat
```

What it does:

1. Installs `requirements-build.txt` (PyQt6, PyInstaller, Pillow).
2. Renders `packaging/time_overlay_icon.svg` to `build\time-overlay.png` and a multi-size `build\time-overlay.ico` via `packaging/make_icon.py`.
3. Runs PyInstaller:

```bat
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name TimeOverlay --icon "%CD%\build\time-overlay.ico" ^
  --add-data "%CD%\packaging\time_overlay_icon.svg;packaging" ^
  --distpath dist --workpath build\pyinstaller --specpath build main.py
```

The `--add-data` and `--icon` sources are absolute (`%CD%`) because `--specpath` makes relative paths resolve relative to the spec directory.

Output: `dist\TimeOverlay.exe`.

### 8.2 Linux — standalone AppImage

```bash
chmod +x packaging/build_linux.sh packaging/AppRun
./packaging/build_linux.sh
```

What it does:

1. Installs build dependencies.
2. Runs PyInstaller `--onefile --name time-overlay` with the SVG bundled as runtime data.
3. Builds `build/AppDir` with:
   - `usr/bin/time-overlay`
   - `AppRun`
   - `time-overlay.desktop` (root + `usr/share/applications`)
   - `time-overlay.svg` (root + hicolor scalable)
   - `time-overlay.png` (root + hicolor 256×256)
   - `.DirIcon`
4. Downloads `appimagetool` and the type-2 runtime into `build/` if not cached.
5. Runs appimagetool with `APPIMAGE_EXTRACT_AND_RUN=1 --no-appstream --runtime-file ...`.

Output: `dist/TimeOverlay-x86_64.AppImage` (or `aarch64`).

Why the runtime is downloaded explicitly: appimagetool's bundled libcurl hung while fetching the type-2 runtime in one development environment. The script uses system `curl` to fetch it and passes `--runtime-file`, which is more robust behind proxies.

### 8.3 Icon pipeline

The canonical icon is `packaging/time_overlay_icon.svg`.

- `packaging/make_icon.py` renders the SVG with `QSvgRenderer` into a 1024×1024 `QImage`, converts it to Pillow, writes a 256×256 PNG, and (when requested) a multi-size Windows ICO.
- QtSvg is used because PyQt6 is already a dependency and it renders the SVG without a display server.
- The Windows build embeds the generated ICO via `--icon` and bundles the SVG as runtime data (`--add-data`) so `QApplication.setWindowIcon()` can load it.
- The Linux AppImage includes the SVG in `usr/share/icons/hicolor/scalable/apps` plus a 256×256 PNG fallback and `.DirIcon`.
- `time_overlay/app.py` locates the SVG at `packaging/time_overlay_icon.svg` relative to the package root; in a PyInstaller one-file build that resolves inside `_MEIPASS`.
- The app imports `PyQt6.QtSvg` so PyInstaller also collects the SVG image-format/icon-engine plugins.

### 8.4 Build outputs and caching

- `build/` — PyInstaller work dir, AppDir, cached `appimagetool`, cached `runtime-*`, generated icons/spec.
- `dist/` — final `.exe` / `.AppImage`.
- `artifacts/` — CI staging only.
- All are gitignored. The Linux script removes `build/pyinstaller`, `build/AppDir`, and `dist/` at the start but intentionally keeps cached downloads.

### 8.5 Size note

The AppImage is roughly 86 MB because it wraps a PyInstaller **onefile** build of PyQt6. A future optimization is to build the AppImage from a PyInstaller **onedir** output, which typically starts faster and may compress better under SquashFS. The Windows artifact must remain onefile per the requirement.

---

## 9. Release workflow

File: `.github/workflows/release.yml`

### Trigger

Manual only:

```yaml
on:
  workflow_dispatch:
    inputs:
      release_type:
        type: choice
        options: [patch, minor, major]
        default: patch
```

There is **no** `push: tags` trigger anymore. Pushing a tag manually will not run this workflow.

### Jobs

1. **`prepare`** — computes the next version.
   - Checks out full history/tags.
   - `git fetch --tags --force`.
   - Takes the latest tag matching strict `^v[0-9]+\.[0-9]+\.[0-9]+$`.
   - Sorts with `sort -V`, so `v1.10.0` beats `v1.9.99`.
   - Ignores pre-release tags such as `v1.2.3-rc1`.
   - No tags → base `v0.0.0`; the first release is `v0.0.1` (patch), `v0.1.0` (minor), or `v1.0.0` (major).
   - Applies `patch`/`minor`/`major`, resets lower components.
   - Outputs `new_tag` (`vX.Y.Z`) and `new_version` (`X.Y.Z`).

2. **`test`** — runs the headless suite on Ubuntu 22.04 / Python 3.12.

3. **`windows` / `linux`** — need `[prepare, test]`, check out `github.sha`, build, and stage artifacts named with `needs.prepare.outputs.new_tag`.

4. **`release`** — needs `[prepare, windows, linux]`.
   - Checks out `github.sha` with full history.
   - Downloads both artifacts.
   - Verifies `HEAD == GITHUB_SHA`.
   - Checks whether `vX.Y.Z` already exists on `origin`:
     - Same SHA → reuse it (safe rerun).
     - Different SHA → fail.
     - Missing → `git tag vX.Y.Z "$GITHUB_SHA"` and `git push origin vX.Y.Z`.
   - Publishes with `softprops/action-gh-release@v2` using `tag_name: needs.prepare.outputs.new_tag`.

### Concurrency

```yaml
concurrency:
  group: release
  cancel-in-progress: false
```

This serializes release runs so two dispatches cannot compute the same next version.

### Rerun semantics

- Re-run the failed **`release` job**: the tag is reused if it still points at the same commit, and the release is created/updated.
- Re-run the **entire workflow**: `prepare` sees the tag created by the failed run and computes the next version, so it will bump again. Prefer re-running failed jobs for a missing release.

### Permissions

The workflow needs `contents: write` for tag push and release creation. The release job uses the checkout token; do not disable `persist-credentials` there.

### Version gap

`time_overlay/__init__.py` still contains `__version__ = "1.0.0"`. The context menu displays that value. The release workflow creates tags independently. Before a release whose tag is not `v1.0.0`, decide whether to bump this file (and commit it) or make the version derive from the tag at build time. This is the most likely first maintenance task.

---

## 10. Platform behavior and caveats

### Windows

- Window flags are applied in `TimeOverlayWindow.__init__`.
- `platform_hints._setup_windows()` uses `ctypes.windll.user32.SetWindowPos`.
- Constants: `HWND_TOPMOST = -1`, `SWP_NOACTIVATE = 0x0010`, plus `SWP_NOMOVE | SWP_NOSIZE`.
- A 2-second timer re-asserts topmost; `showEvent` also re-asserts immediately.
- Exclusive full-screen/anti-cheat applications may still cover the overlay; no user-space app can guarantee topmost over every exclusive fullscreen scenario.
- `WindowDoesNotAcceptFocus` maps to a non-activating window; buttons still receive mouse clicks.

### Linux X11

- `Qt.Tool` plus `WindowStaysOnTopHint`.
- `WA_X11NetWmWindowTypeUtility` is set when the platform plugin is `xcb`.
- `TIME_OVERLAY_X11_DOCK=1` switches to `WA_X11NetWmWindowTypeDock` for WMs that put fullscreen windows above utility windows.
- A 2-second `QTimer` calls `raise_()` (via `reassert_topmost`) to recover if the WM lowers the overlay after focus changes. It is skipped while the set dialog or context menu is open.
- A compositor is required for the transparent background and rounded corners.

### Linux Wayland

- Compositors intentionally restrict client-controlled always-on-top. `Tool` + `WindowStaysOnTopHint` are best-effort.
- KDE and some wlroots-based compositors generally honor it; GNOME may not.
- The periodic `raise_()` may be ignored entirely; Wayland does not provide a portable always-on-top protocol for normal clients.
- The X11 attributes are not applied under Wayland.
- Testing on X11 is the most reliable way to verify stacking behavior.

### Focus

The overlay never takes focus. The context menu, mode buttons, action buttons, and Quit button are the intended controls. The set dialog is a separate modal window and calls `activateWindow()`, but its −/+ buttons and presets are the fallback if keyboard focus is refused.

### Click-through

Ghost mode is visual only. The transparent window area still receives mouse events, which is required for hover-to-reveal and drag-to-move. It is not click-through to underlying applications.

---

## 11. Known gaps / likely next tasks

1. **Version source of truth** — bump `time_overlay/__init__.py` from the release tag, or inject the version at build time.
2. **Persist more state** — mode, timer duration, and perhaps stopwatch state. Currently only clock format and geometry persist.
3. **AppImage size/startup** — consider PyInstaller `--onedir` inside the AppDir.
4. **Click-through ghost mode** — requires platform-specific input shapes and a plan for hover detection; currently intentionally not implemented.
5. **Global shortcuts / keyboard access** — conflicts with `WindowDoesNotAcceptFocus`; would need global shortcuts (platform-specific) or a focusable variant.
6. **Tray icon** — useful if the overlay is ever hidden or moved off-screen.
7. **Accessibility** — screen-reader labels, high-contrast option, configurable outline/font.
8. **Configuration** — outline width, colors, default timer, font family.
9. **PR CI** — the only workflow is the manual release workflow. Add push/PR tests + lint.
10. **Windows-native tests** — mock `ctypes` or run a Windows job that at least imports the module and constructs the window.
11. **Pre-release/channel support** — optional `rc`/`beta` tags and release flags.
12. **Checksums/signing** — add SHA256 checksums and code signing for Windows.
13. **Single-instance guard** — avoid multiple overlays.
14. **Small-window polish** — the resize grip slightly overlaps the right panel edge at minimum width.
15. **Wayland topmost improvements** — track compositor protocols or document per-DE behavior.

---

## 12. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Black or square background on Linux | No compositor, or translucency unsupported. Enable compositing; test on X11. |
| Overlay is not above fullscreen apps | Windows: check the 2 s topmost timer / `SetWindowPos`. X11: try `TIME_OVERLAY_X11_DOCK=1`. Wayland: compositor policy. |
| Cannot type in the Set dialog | Window manager refused focus for a non-activating parent. Use the −/+ buttons or presets. |
| Set dialog numbers are invisible | The dialog should use `widgets.TimeField` (custom-painted digits), not `QSpinBox`. If you see empty fields, confirm `dialogs.py` imports `TimeField`, rebuild, and run `test_set_dialog_values_are_painted_white`. `TimeField.paintEvent` sets an explicit white `QPainter` pen, so native styles cannot hide the value. |
| Closing the Set dialog exits the app | Verify `TimeOverlayWindow` has `WA_QuitOnClose=True` and `TimeSetDialog` has `WA_QuitOnClose=False`. Tool windows default to false; QDialog defaults to true. |
| Timer Reset button is disabled | By design while the timer is running. Pause first; `_update_control_labels()` re-enables it. |
| Window cannot be dragged | Use the long drag bar across the top (five centered dots). It tries the compositor `startSystemMove()` first and falls back to manual `move()`. On Wayland, the compositor may still refuse client-initiated moves. Drag-anywhere was intentionally removed. |
| Time text grows when the cursor leaves | The fixed 3-column layout / transparent 1 px ghost border is not in effect, or something is calling `_fit_time_font()` on hover. |
| Overlay drops below other windows after focus change | Linux: the 2 s `raise_()` timer is best-effort; X11 WMs may need `TIME_OVERLAY_X11_DOCK=1`; Wayland compositors may ignore raise/topmost requests entirely. |
| Keyboard shortcuts do nothing | By design: `WindowDoesNotAcceptFocus`. Use mouse/context menu. |
| AppImage does not start | FUSE missing or incompatible. Run `APPIMAGE_EXTRACT_AND_RUN=1 ./dist/TimeOverlay-*.AppImage`. |
| Linux build hangs downloading | appimagetool/runtime download/network issue. The script caches under `build/`; check proxy/curl. |
| App icon missing | Confirm `packaging/time_overlay_icon.svg` exists and `make_icon.py` rendered it. The runtime icon also needs the `--add-data` SVG and QtSvg plugins in the frozen build. |
| Windows build fails at icon step | PyQt6/Pillow not installed, invalid SVG path, or not running on Windows. Re-run `python -m pip install -r requirements-build.txt`. |
| Tests fail on a real display | Use `QT_QPA_PLATFORM=offscreen` for the headless suite. |
| Wrong release version | The workflow ignores pre-release tags and starts from `v0.0.0` if no strict semver tag exists. Check `git tag --list 'v*'`. |
| Release fails “tag already exists at …” | The intended tag points to a different commit. Inspect the tag; do not force-move tags without a deliberate decision. |
| Reset saved window/format settings | Linux: remove `~/.config/time-overlay/time-overlay.conf`. Windows: delete `HKCU\Software\time-overlay\time-overlay`. |
| AppImage is large | Expected for PyQt6 + onefile. See onedir optimization note. |

---

## 13. First-day handover checklist

- [ ] Read `README.md` and this file.
- [ ] Run `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`.
- [ ] Run `ruff check .` and `ruff format --check .` (install ruff first).
- [ ] Run `python main.py` on the target platform and manually verify:
  - [ ] Clock ticks; 12/24 toggle; right column is blank in Clock mode.
  - [ ] Stopwatch Start/Pause/Reset; Reset while running keeps it running from zero.
  - [ ] Timer Set/presets/start/pause; Reset is disabled while running; reset after pausing; zero flash and beep.
  - [ ] Hover reveals panel contents; leaving enters ghost mode; the time text does not move or grow.
  - [ ] Drag the centered top bar; bottom-right grip resizes.
  - [ ] Closing the Set dialog via Set/Cancel/window close does not quit the app.
  - [ ] Timer field values are clearly visible and editable (type, +/−, presets).
  - [ ] Right-click menu: center, format, quit.
  - [ ] Geometry and 24-hour setting survive restart.
- [ ] Build the Linux AppImage and run it (`APPIMAGE_EXTRACT_AND_RUN=1` if no FUSE).
- [ ] Build `dist\TimeOverlay.exe` on Windows and run it.
- [ ] Verify GitHub Actions has `contents: write`; check tag/branch protection allows the workflow to push tags.
- [ ] Decide whether `time_overlay/__init__.py` needs a version bump.
- [ ] Commit/push the working tree before dispatching a release.
- [ ] Check open issues / discussions / pending PRs.
- [ ] Confirm the release workflow is still manual and no stray `push: tags` trigger was reintroduced.

---

## 14. Useful commands

```bash
# Run
python main.py
python -m time_overlay

# Tests
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v

# Lint/format
python -m pip install ruff
ruff check .
ruff format --check .

# Linux build
./packaging/build_linux.sh

# Inspect/run AppImage without FUSE
./dist/TimeOverlay-x86_64.AppImage --appimage-extract
APPIMAGE_EXTRACT_AND_RUN=1 ./dist/TimeOverlay-x86_64.AppImage

# Release manually
gh workflow run release.yml -f release_type=patch
gh workflow run release.yml -f release_type=minor
gh workflow run release.yml -f release_type=major

# Latest tags
git tag --list 'v*' --sort=-v:refname
```

---

## 15. Ownership / license

- License: GNU General Public License v3.0 or later (`LICENSE`).
- Source files carry `SPDX-License-Identifier: GPL-3.0-or-later`.
- Keep new source files under the same license.
- The project was built around Python + PyQt6; any replacement UI toolkit would be a rewrite, not an incremental change.
