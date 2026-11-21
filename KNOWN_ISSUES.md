# Known issues and future work

This file lists the issues we know about but have not fully fixed. Each entry explains what happens, why it happens, the current workaround, possible fixes, the risk of those fixes, and the next step.

The short user-facing list is in [README.md](README.md#known-issues).

## Summary

| # | Issue | Affects | Short workaround | Status |
|---|---|---|---|---|
| 1 | Fullscreen presentations cover the overlay | Windows, Linux X11, Wayland | Borderless/windowed fullscreen or a second display; X11 dock hint | Platform limit |
| 2 | Native Wayland always-on-top | Wayland sessions | Default XWayland fallback; compositor rules | Best effort |
| 3 | Windows SmartScreen warning | Windows | More info → Run anyway | Unsigned |
| 4 | AppImage needs FUSE 2 | Linux AppImage | `APPIMAGE_EXTRACT_AND_RUN=1` | Workaround |
| 5 | Timer bell can be silent | All | Enable the system bell | TODO |
| 6 | Mode/timer/stopwatch state is not saved | All | Re-set after restart | TODO |
| 7 | Times cap at `99:59:59` | All | Use shorter durations | TODO |
| 8 | No macOS build | macOS | None | Not planned |
| 9 | No push/PR CI | Contributors | Release test job only | TODO |
| 10 | Pinned AppImage tools need manual updates | Maintainers | Update version + SHA256 | TODO |
| 11 | No global shortcuts, tray, or screen-reader labels | All | Mouse controls | Feature gap |

---

## 1. Fullscreen presentations cover the overlay

**What happens:** The overlay stays above normal windows, but a presentation, video, or game in fullscreen can cover it.

**Why:**

"Always on top" is a request to the window manager or compositor. It is not a hardware guarantee.

- **Windows exclusive fullscreen:** the fullscreen application bypasses the desktop compositor (DWM) and draws directly. A normal topmost window cannot be composed above it.
- **Windows borderless fullscreen:** this is still a normal window. Topmost should work; if it does not, the fullscreen app is probably also topmost and reasserting itself.
- **Linux X11:** a fullscreen window is often in a higher layer than normal topmost windows. Window managers decide.
- **Linux Wayland:** the compositor owns stacking. A native fullscreen surface is above normal clients by design.

**Current behavior:**

- Windows: `SetWindowPos(HWND_TOPMOST)` every 2 seconds.
- X11 and XWayland: `WindowStaysOnTopHint`, an X11 utility hint, and a 2-second `raise_()`. `TIME_OVERLAY_X11_DOCK=1` requests a dock-type window instead.
- Wayland: the app defaults to XWayland when `DISPLAY` is set; native Wayland is best-effort.

**Workarounds:**

1. **Run the presentation in borderless or windowed fullscreen.** This keeps it a normal window, so topmost can work. This is the most reliable fix.
2. **Use a second display.** Put the presentation on one screen and the overlay on the other. This is reliable but needs two screens.
3. **On X11 or XWayland, try the dock hint:**

   ```bash
   TIME_OVERLAY_X11_DOCK=1 python main.py
   ```

   Some window managers keep a dock window above fullscreen; others do not.

**Potential fixes and risks:**

- **Windows foreground hook or faster reassert.** Reassert topmost when the foreground window changes, or every 0.5–1 second. Helps borderless fullscreen; costs CPU wakeups and still cannot beat exclusive fullscreen.
- **X11 dock window by default.** May stay above fullscreen in some window managers. Risk: some WMs treat it like a panel, reserve screen space, or hide it from the taskbar.
- **Wayland layer-shell.** A `zwlr_layer_shell_v1` surface in the `overlay` layer is the only real native Wayland path. Risk: compositor-specific (wlroots-based and some KDE; not GNOME), makes the window a panel surface, and Qt does not expose the protocol. It would need a separate native helper.
- **Exclusive fullscreen.** No supported user-space fix exists. Do not promise one.

**TODO:**

- [ ] Test a platform matrix: Windows 10/11 with PowerPoint, LibreOffice Impress, Chrome, and a fullscreen game; KDE/GNOME on X11, XWayland, and native Wayland.
- [ ] Decide whether the Windows foreground hook is worth the extra code after testing borderless fullscreen.
- [ ] Decide whether an X11 dock-by-default mode is safe enough; keep the env switch until then.
- [ ] Prototype layer-shell only if a target compositor and a concrete use case justify it.
- [ ] Keep the "use borderless fullscreen or a second display" advice prominent.

---

## 2. Native Wayland always-on-top

**What happens:** On native Wayland, the overlay may not stay above other windows, even with `WindowStaysOnTopHint`.

**Why:** Wayland has no standard always-on-top protocol for normal application windows. The compositor decides. KDE and some wlroots-based compositors may honor the hint; GNOME generally does not.

**Current behavior:**

- If `XDG_SESSION_TYPE=wayland` and `DISPLAY` is set, `time_overlay/app.py` sets `QT_QPA_PLATFORM=xcb` before creating `QApplication`. This runs the app through XWayland so the compositor can apply the X11 above hints.
- `TIME_OVERLAY_NATIVE_WAYLAND=1` keeps native Wayland.
- An explicit `QT_QPA_PLATFORM` always wins.
- `QApplication.setDesktopFileName("time-overlay")` sets the app_id/WM_CLASS so compositor window rules can match.

**Workarounds:**

- Use the default XWayland fallback.
- On KDE, add a window rule for `time-overlay` ("Keep above").
- On GNOME, use the "Always on Top" extension or the window menu, if available.
- On wlroots compositors, use a compositor rule or layer-shell-aware tooling.

**Potential fixes and risks:**

- **Layer-shell overlay.** Native and above fullscreen on supporting compositors. Risk: compositor-specific, not exposed by Qt, panel-like window, not GNOME.
- **Force XWayland for all Wayland sessions.** Already the default when `DISPLAY` exists. Risk: XWayland scaling and native-feature trade-offs; does not help against a native Wayland fullscreen surface.
- **Compositor-specific D-Bus/CLI rules.** Fragile and different on every desktop.

**TODO:**

- [ ] Document per-compositor behavior (KDE, GNOME, Sway, Hyprland).
- [ ] Test the auto-XWayland path on KDE and GNOME.
- [ ] Keep the native opt-out and explicit-platform behavior covered by tests.

---

## 3. Windows SmartScreen warning

**What happens:** Windows may show "Windows protected your PC" the first time the EXE runs.

**Why:** The EXE is not code-signed. SmartScreen treats low-reputation, unsigned binaries with suspicion.

**Workaround:** Choose **More info** → **Run anyway**. Verify the download came from the official GitHub release page.

**Potential fix:** Sign the EXE with a Windows code-signing certificate.

**Risk:** Certificates cost money, need renewal, and require signing in CI. Signing improves trust but does not guarantee every SmartScreen prompt disappears immediately.

**TODO:**

- [ ] Decide whether to buy a code-signing certificate.
- [ ] Add signing to the Windows build if the project gets a certificate.
- [ ] Publish SHA256 checksums for the release assets.

---

## 4. AppImage needs FUSE 2

**What happens:** On some Linux systems the AppImage does not start because FUSE 2 is missing or incompatible.

**Why:** The AppImage runtime uses FUSE 2 to mount itself. Many current distributions ship FUSE 3 or no FUSE at all.

**Workaround:**

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./TimeOverlay-x86_64.AppImage
```

The app then extracts to a temporary directory and runs. This needs no FUSE but starts a little slower and writes to temporary storage.

**Potential fix:** Ship a FUSE-3 runtime or a `--onedir` build inside the AppDir. Both add size and packaging work.

**Risk:** A larger AppImage, slower startup, or a second packaging format to maintain.

**TODO:**

- [ ] Evaluate a FUSE-3 AppImage runtime.
- [ ] Consider a `.tar.gz` or distro package as a fallback.

---

## 5. Timer bell can be silent

**What happens:** The timer flashes but the "ding" may not be audible.

**Why:** `QApplication.beep()` asks the platform for the system bell. Some desktops disable the bell, route it nowhere, or mute it.

**Workaround:** Enable the system bell in the desktop sound settings.

**Potential fix:** Bundle a short WAV and play it with `QSoundEffect` (PyQt6.QtMultimedia). This gives a consistent sound independent of the system bell.

**Risk:** Adds a multimedia dependency/plugin to the frozen builds, an audio asset and its license, and a new failure mode when no audio device exists.

**TODO:**

- [ ] Decide whether a bundled sound is worth the extra dependency.
- [ ] If added, keep the system bell as a fallback.
- [ ] Add a "mute" setting if the sound can be disabled.

---

## 6. Mode, timer, and stopwatch state are not saved

**What happens:** After a restart, the app opens in Clock mode with a fresh 5-minute timer. The stopwatch is zero.

**Why:** Only the window geometry and the 12/24-hour choice are stored in `QSettings`. Persisting a running timer would also need a wall-clock deadline and handling for time spent while the app was closed.

**Workaround:** Re-set the timer/stopwatch after restart.

**Potential fix:** Store the mode, timer duration, and a deadline in `QSettings`; restore them on launch.

**Risk:** A restored timer might expire immediately or start beeping on launch. Stopwatch state across restarts is usually not meaningful.

**TODO:**

- [ ] Persist the timer duration and the 12/24-hour choice.
- [ ] Decide whether to restore a running timer; if yes, use an absolute deadline and clamp to zero.
- [ ] Add tests for stale/expired settings.

---

## 7. Times cap at `99:59:59`

**What happens:** The stopwatch display stops at `99:59:59.99` and the timer dialog only accepts up to 99 hours, 59 minutes, 59 seconds.

**Why:** The formatters cap output, and the timer fields use fixed two-digit hours.

**Workaround:** Use shorter durations.

**Potential fix:** Add a days field, or let the hours field grow and fit the font accordingly.

**Risk:** More digits mean a smaller fitted font or a wider window; the fixed three-column layout needs care.

**TODO:**

- [ ] Decide whether long-running stopwatches are a real use case.
- [ ] If so, remove the cap and extend the time fields.

---

## 8. No macOS build

**What happens:** There is no `.app` or `.dmg`; only Windows and Linux are packaged.

**Why:** PyQt6 supports macOS, but packaging, code signing, notarization, and testing need a Mac runner and an Apple developer account.

**Workaround:** None; use Windows or Linux.

**Potential fix:** Add a macOS PyInstaller build and a GitHub Actions macOS job, then sign and notarize.

**Risk:** Signing/notarization cost and maintenance; different always-on-top and fullscreen behavior.

**TODO:**

- [ ] Decide whether macOS is in scope.
- [ ] If yes, add a build job and a small test matrix.

---

## 9. No push/PR CI

**What happens:** The only workflow is the manual release workflow. It runs tests and ruff, but only when a release is dispatched.

**Why:** The project has no push/PR workflow yet.

**Workaround:** Run the tests and ruff locally before opening a PR.

**Potential fix:** Add a small `ci.yml` for push and pull requests on the default branch, reusing the release test steps.

**Risk:** CI minutes and maintenance; low.

**TODO:**

- [ ] Add `push`/`pull_request` CI for tests, ruff, and a Linux build smoke test.
- [ ] Keep the release workflow as the only publisher.

---

## 10. Pinned AppImage tools need manual updates

**What happens:** `packaging/build_linux.sh` pins `appimagetool` 1.9.1 and type2-runtime 20251108 with SHA256 checks. A future release of either tool is not picked up automatically.

**Why:** Pinning and verifying is safer than the old `continuous` URLs, but it is manual.

**Workaround:** Update the version, URL, and SHA256 for both `x86_64` and `aarch64` when bumping.

**Potential fix:** A small update script or a Renovate/Dependabot rule that checks the AppImage releases.

**Risk:** A stale pin may miss fixes; an automatic updater could break the build if an upstream asset changes.

**TODO:**

- [ ] Add an update helper or a scheduled check.
- [ ] Keep the SHA256 checks and test both architectures.

---

## 11. No global shortcuts, tray, or screen-reader labels

**What happens:** The overlay is mouse-driven. It does not take keyboard focus by design (`WindowDoesNotAcceptFocus`), has no tray icon, and its custom time field and time label do not expose rich accessibility metadata.

**Why:** The app is a small always-on overlay; global shortcuts and accessibility need platform-specific work.

**Workaround:** Use the mouse and the context menu.

**Potential fix:** Add an optional focusable mode, global shortcuts, a tray menu, and accessibility names/roles.

**Risk:** Keyboard focus can interfere with the overlay's non-activating behavior; global shortcuts are platform-specific; a tray icon adds another lifecycle.

**TODO:**

- [ ] Add `setAccessibleName`/roles where Qt supports them.
- [ ] Decide whether global shortcuts are in scope.
- [ ] Decide whether a tray icon is useful when the overlay is hidden or off-screen.
