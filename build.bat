@echo off
REM Kodex Build Script for Windows
REM Requires Python 3.11+ on the system PATH
REM
REM This creates a portable distribution in dist\kodex\
REM with an embedded Python runtime — no system Python required.

echo.
echo ===================================
echo   Kodex Portable Build
echo ===================================
echo.

python build_embedded.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build failed! Make sure Python 3.11+ is installed.
    pause
    exit /b 1
)

echo.
echo Build successful! See dist\kodex\
pause
