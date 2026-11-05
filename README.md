# Time Overlay

A frameless, always-on-top clock, stopwatch and countdown timer for **Windows and Linux**, built with **Python 3 + PyQt6**.

The overlay shows large white time text with a black outline. Hovering reveals the mode and control panels; moving the cursor away leaves only the outlined time floating on screen ("ghost mode").

```
┌──────────────────────────────────────────────────────────────────────┐
│  MODE              ┌────────────────────────────┐      CONTROLS      │
│  [ Clock     ]     │                            │      [ Pause   ]   │
│  [ Stopwatch ]     │        12:34:56            │      [ Reset   ]   │
│  [ Timer     ]     │                            │      [ +1m     ]   │
│  24-hour clock     └────────────────────────────┘      [ Set     ]   │
│  Quit                                                                │
└──────────────────────────────────────────────────────────────────────┘
```

## Features

- **Clock** — live local time, 12/24-hour toggle, updates instantly.
- **Stopwatch** — start, pause, reset, +1 minute and set-value controls; centisecond precision backed by `time.perf_counter()`.
- **Timer** — countdown with quick presets, HH:MM:SS entry, start/pause/reset, +1 minute, and a flashing red/white outline plus a system beep at `00:00:00`.
- **Outlined text** — custom `OutlinedLabel` paints white glyphs with a 3 px black `QPainterPath` stroke for visibility over any content.
- **Responsive type** — the time font is recomputed with a binary search on every resize (and when panels hide/show), so the text fills the available space without clipping.
- **Ghost mode** — controls and the dark rounded background disappear when the cursor leaves the window; the outlined time remains.
- **Drag to move** — left-click and drag anywhere on the overlay (buttons still work normally).
- **Always on top** — frameless tool window with Windows native topmost re-enforcement every 2 seconds and X11 utility hints on Linux.
- **Remembers position** — window geometry and clock format are stored with `QSettings`.

## Requirements

- Python **3.10+**
- PyQt6 6.6+
- Windows 10/11 or a Linux desktop with a compositor (X11 or Wayland)

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

You can also run the package directly:

```bash
python -m time_overlay
```

## Usage

| Mode | Controls |
| --- | --- |
| **Clock** | Left panel: `Clock`, `Stopwatch`, `Timer`, 12/24-hour toggle, `Quit`. Action controls are hidden in clock mode. |
| **Stopwatch** | `Start`/`Pause`, `Reset`, `+1m`, `Set` |
| **Timer** | `Start`/`Pause`, `Reset`, `+1m`, `Set` (HH:MM:SS picker with 1/5/10/15/25/45-minute presets) |

- **Hover** over the window to reveal the panels and the dark rounded background.
- **Move the cursor outside** the window to enter ghost mode: only the outlined time stays visible.
- **Drag** with the left mouse button anywhere on the overlay to reposition it.
- **Resize** with the small grip in the bottom-right corner while the panels are visible.
- **Right-click** anywhere for the context menu: center on screen, switch 12/24-hour clock, or quit.
- The `Quit` button in the left panel also exits the app.

### Timer behavior

- `Set` opens a modal picker. Presets apply instantly; the `Set` button stays disabled for a zero-length timer.
- `+1m` extends a running countdown or adds a minute to a paused/finished one.
- On reaching zero the timer stops, beeps, and flashes the outline red/white. Press `Reset`, `+1m`, `Set`, or `Start` to leave the finished state.

## Platform notes

### Windows

The window uses `FramelessWindowHint | WindowStaysOnTopHint | Tool | WindowDoesNotAcceptFocus`. A `QTimer` calls `user32.SetWindowPos(HWND_TOPMOST, ..., SWP_NOACTIVATE)` every 2 seconds, which keeps the overlay above full-screen presentations and games that try to take the topmost slot.

### Linux

Qt's `Tool`/utility window hint and `WindowStaysOnTopHint` are used. On X11 the app additionally sets `WA_X11NetWmWindowTypeUtility`. Some window managers still place full-screen windows above normal topmost clients. If your X11 WM does this, launch with:

```bash
TIME_OVERLAY_X11_DOCK=1 python main.py
```

which requests an X11 dock-type window instead. Wayland compositors intentionally restrict client-controlled always-on-top; behavior depends on the compositor (KDE and some wlroots compositors generally honor it, GNOME may not). A compositor is required for the transparent background and rounded corners.

## Packaging

### Windows — portable single-file EXE

The app icon source is `packaging/time_overlay_icon.svg`. The build script renders it to PNG/ICO, then runs PyInstaller:

```bat
packaging\build_windows.bat
```

Equivalent manual commands:

```bat
python -m pip install -r requirements-build.txt
python packaging\make_icon.py build\time-overlay.png --ico build\time-overlay.ico --svg packaging\time_overlay_icon.svg
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name TimeOverlay --icon build\time-overlay.ico ^
  --add-data "packaging\time_overlay_icon.svg;packaging" main.py
```

Output: `dist\TimeOverlay.exe` — a portable single-file executable with no installer and no console window.

### Linux — standalone AppImage

```bash
chmod +x packaging/build_linux.sh packaging/AppRun
./packaging/build_linux.sh
```

The script:

1. Runs PyInstaller with `--onefile`.
2. Creates an AppDir with `AppRun`, a `.desktop` file, the scalable SVG app icon, and a generated 256×256 PNG fallback.
3. Downloads `appimagetool` and the type-2 runtime (cached in `build/`) and produces `dist/TimeOverlay-x86_64.AppImage` (or `aarch64`).

Build dependencies: Python 3, `curl`, and the usual Qt runtime libraries. `APPIMAGE_EXTRACT_AND_RUN=1` is used so FUSE is **not** required on the build machine.

Run the result:

```bash
chmod +x dist/TimeOverlay-x86_64.AppImage
./dist/TimeOverlay-x86_64.AppImage
```

If FUSE 2 is not installed on the target machine, use the AppImage's extract-and-run mode:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./dist/TimeOverlay-x86_64.AppImage
```

### Automated releases

The `Release` workflow is triggered manually and creates the tag for you. Choose a bump type (`patch`, `minor`, or `major`); it reads the latest `vX.Y.Z` tag, computes the next version, runs the tests, builds both artifacts, creates the new tag, and publishes a GitHub Release for it.

From the GitHub UI: **Actions → Release → Run workflow**, choose `patch` / `minor` / `major`.

Or with the GitHub CLI:

```bash
gh workflow run release.yml -f release_type=patch
```

The tag is created only after the tests and both builds succeed, and it points at the commit the workflow was dispatched on. If no previous tag exists, the first release starts from `v0.0.0` and increments the chosen part. Concurrent release runs are serialized with a `concurrency` group so the version cannot race.

If publishing fails after the tag has been created, re-run the failed `release` job: the tag is reused when it already points at the same commit, so the version is not bumped twice.

Release assets (example for `v1.2.3`):

- `TimeOverlay-v1.2.3-windows-x64.exe`
- `TimeOverlay-v1.2.3-x86_64.AppImage`

The Linux artifact is built on Ubuntu 22.04 for broad glibc compatibility.

## Tests

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

- `tests/test_core.py` covers the Qt-free stopwatch/countdown state machines and formatting.
- `tests/test_ui.py` is a headless smoke test for window flags, ghost-mode visibility, mode switching, timer controls, clock format, responsive font scaling, and the resize grip.

## Project layout

```
main.py                       PyInstaller/direct entry point
HANDOVER.md                   Maintainer handover, architecture and release context
time_overlay/
  app.py                      QApplication bootstrap
  window.py                   Overlay window, modes, hover, drag, flashing
  outlined_label.py           QPainterPath outlined-text widget
  core.py                     Stopwatch, CountdownTimer, formatters
  dialogs.py                  HH:MM:SS set dialog with presets
  widgets.py                  Custom resize grip
  platform_hints.py           Windows topmost + Linux X11/Wayland hints
  theme.py                    Qt stylesheets
packaging/
  build_windows.bat           PyInstaller one-file build
  build_linux.sh              AppImage build
  make_icon.py                SVG-to-PNG/ICO icon renderer
  time_overlay_icon.svg       Source app icon
  AppRun, time-overlay.desktop
tests/                        unittest suite
.github/workflows/release.yml Manual version-bump Windows + Linux release
```

## Maintainer handover

See [HANDOVER.md](HANDOVER.md) for architecture, invariants, packaging and release-workflow details, known gaps, troubleshooting, and a first-day checklist.

## License

GNU General Public License v3.0 or later. See [LICENSE](LICENSE).
