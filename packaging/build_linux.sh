#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Build a portable Linux AppImage:
#   1. PyInstaller one-file executable
#   2. AppDir skeleton (AppRun, .desktop, icon)
#   3. appimagetool wrapper to produce the final .AppImage
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"

echo "[1/4] Installing build dependencies..."
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements-build.txt

echo "[2/4] Building one-file executable..."
rm -rf "$ROOT_DIR/build/pyinstaller" "$ROOT_DIR/build/AppDir" "$ROOT_DIR/dist"
"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name time-overlay \
  --add-data "$ROOT_DIR/packaging/time_overlay_icon.svg:packaging" \
  --distpath "$ROOT_DIR/dist" \
  --workpath "$ROOT_DIR/build/pyinstaller" \
  --specpath "$ROOT_DIR/build" \
  main.py

echo "[3/4] Assembling AppDir..."
APPDIR="$ROOT_DIR/build/AppDir"
mkdir -p \
  "$APPDIR/usr/bin" \
  "$APPDIR/usr/share/applications" \
  "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
  "$APPDIR/usr/share/icons/hicolor/scalable/apps"

install -m 755 "$ROOT_DIR/dist/time-overlay" "$APPDIR/usr/bin/time-overlay"
install -m 755 "$ROOT_DIR/packaging/AppRun" "$APPDIR/AppRun"
install -m 644 "$ROOT_DIR/packaging/time-overlay.desktop" "$APPDIR/time-overlay.desktop"
install -m 644 "$ROOT_DIR/packaging/time-overlay.desktop" \
  "$APPDIR/usr/share/applications/time-overlay.desktop"

"$PYTHON" "$ROOT_DIR/packaging/make_icon.py" \
  "$APPDIR/time-overlay.png" \
  --svg "$ROOT_DIR/packaging/time_overlay_icon.svg"
install -m 644 "$APPDIR/time-overlay.png" "$APPDIR/.DirIcon"
install -m 644 "$APPDIR/time-overlay.png" \
  "$APPDIR/usr/share/icons/hicolor/256x256/apps/time-overlay.png"
install -m 644 "$ROOT_DIR/packaging/time_overlay_icon.svg" "$APPDIR/time-overlay.svg"
install -m 644 "$ROOT_DIR/packaging/time_overlay_icon.svg" \
  "$APPDIR/usr/share/icons/hicolor/scalable/apps/time-overlay.svg"

echo "[4/4] Creating AppImage..."
case "$(uname -m)" in
  x86_64|amd64) APPIMAGE_ARCH="x86_64" ;;
  aarch64|arm64) APPIMAGE_ARCH="aarch64" ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

mkdir -p "$ROOT_DIR/build"

TOOL="$ROOT_DIR/build/appimagetool"
if [ ! -x "$TOOL" ]; then
  URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${APPIMAGE_ARCH}.AppImage"
  echo "Downloading $URL"
  curl -L --fail --retry 3 --output "$TOOL.download" "$URL"
  chmod +x "$TOOL.download"
  mv "$TOOL.download" "$TOOL"
fi

# appimagetool normally downloads the type-2 runtime itself, but its bundled
# libcurl can be unreliable behind proxies. Fetch it with curl and pass it in.
RUNTIME="$ROOT_DIR/build/runtime-${APPIMAGE_ARCH}"
if [ ! -f "$RUNTIME" ]; then
  RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-${APPIMAGE_ARCH}"
  echo "Downloading $RUNTIME_URL"
  curl -L --fail --retry 3 --output "$RUNTIME.download" "$RUNTIME_URL"
  mv "$RUNTIME.download" "$RUNTIME"
fi

OUTPUT="$ROOT_DIR/dist/TimeOverlay-${APPIMAGE_ARCH}.AppImage"
# APPIMAGE_EXTRACT_AND_RUN avoids requiring FUSE on build machines/CI.
ARCH="$APPIMAGE_ARCH" APPIMAGE_EXTRACT_AND_RUN=1 \
  "$TOOL" --no-appstream --runtime-file "$RUNTIME" "$APPDIR" "$OUTPUT"

echo
echo "Built: $OUTPUT"
