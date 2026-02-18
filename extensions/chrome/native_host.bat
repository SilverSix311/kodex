@echo off
REM ============================================================
REM  Kodex Context Bridge — Native Messaging Host Launcher
REM
REM  Called by Chrome when the extension connects to the native host.
REM  Launches the Python native messaging handler via the embedded
REM  Python runtime (if available) or falls back to system Python.
REM
REM  DO NOT run this directly — Chrome launches it automatically.
REM ============================================================

setlocal

set "LAUNCHER_DIR=%~dp0"
REM Remove trailing backslash
if "%LAUNCHER_DIR:~-1%"=="\" set "LAUNCHER_DIR=%LAUNCHER_DIR:~0,-1%"

REM Walk up to find the Kodex root (extensions/chrome/ -> root)
set "KODEX_ROOT=%LAUNCHER_DIR%\..\.."
for %%I in ("%KODEX_ROOT%") do set "KODEX_ROOT=%%~fI"

REM Embedded Python (preferred — ships with dist/kodex build)
set "EMBEDDED_PYTHON=%KODEX_ROOT%\python\python.exe"

REM App source location
set "APP_DIR=%KODEX_ROOT%\app"

REM Native messaging script location (src tree, for development)
set "SRC_DIR=%KODEX_ROOT%\src"

REM ── Choose Python executable ──────────────────────────────────────────────

if exist "%EMBEDDED_PYTHON%" (
    set "PYTHON_EXE=%EMBEDDED_PYTHON%"
    set "PYTHONPATH=%APP_DIR%"
) else (
    REM Fall back to system Python
    set "PYTHON_EXE=python"
    set "PYTHONPATH=%SRC_DIR%"
)

REM ── Launch the native messaging host ─────────────────────────────────────

REM Native messaging requires stdin/stdout to be in binary mode (no BOM, no CR).
REM Python handles this internally via sys.stdin.buffer / sys.stdout.buffer.

"%PYTHON_EXE%" -m kodex_py.native_messaging

endlocal
