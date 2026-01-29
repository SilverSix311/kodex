@echo off
REM Kodex Build Script for AutoHotkey v2
REM This script compiles kodex.ahk to kodex.exe using Ahk2Exe compiler

setlocal enabledelayedexpansion

REM Find AutoHotkey v2 installation
set AHK2EXE=
for %%i in (
    "C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe"
    "C:\Program Files (x86)\AutoHotkey\Compiler\Ahk2Exe.exe"
    "%USERPROFILE%\AppData\Local\AutoHotkey\Compiler\Ahk2Exe.exe"
) do (
    if exist %%i (
        set AHK2EXE=%%i
        goto found
    )
)

:found
if "%AHK2EXE%"=="" (
    echo Error: AutoHotkey v2 Compiler not found!
    echo Please install AutoHotkey v2 from https://www.autohotkey.com/
    pause
    exit /b 1
)

echo Found Ahk2Exe: %AHK2EXE%
echo.

REM Create output directory
if not exist "dist" mkdir dist

REM Compile main script
echo Compiling kodex.ahk to dist\kodex.exe...
"%AHK2EXE%" /in kodex.ahk /out dist\kodex.exe /icon kodex.ico

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build successful!
    echo Executable: dist\kodex.exe
    echo.
    echo You can now:
    echo 1. Test the executable: dist\kodex.exe
    echo 2. Upload to GitHub releases
) else (
    echo.
    echo Build failed! Check AutoHotkey installation.
    pause
    exit /b 1
)

pause
