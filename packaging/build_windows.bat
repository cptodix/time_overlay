@echo off
setlocal
cd /d "%~dp0\.."

if "%PYTHON%"=="" set "PYTHON=python"

echo [1/4] Installing build dependencies...
%PYTHON% -m pip install --upgrade pip
if errorlevel 1 goto :error
%PYTHON% -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

echo [2/4] Generating icon...
if not exist build mkdir build
%PYTHON% packaging\make_icon.py build\time-overlay.png --ico build\time-overlay.ico --svg packaging\time_overlay_icon.svg
if errorlevel 1 goto :error

echo [3/4] Building single-file executable...
%PYTHON% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --noconsole ^
  --name TimeOverlay ^
  --icon "%CD%\build\time-overlay.ico" ^
  --add-data "%CD%\packaging\time_overlay_icon.svg;packaging" ^
  --distpath dist ^
  --workpath build\pyinstaller ^
  --specpath build ^
  main.py
if errorlevel 1 goto :error

echo [4/4] Done.
echo.
echo Built: %CD%\dist\TimeOverlay.exe
exit /b 0

:error
echo.
echo Build failed.
exit /b 1
