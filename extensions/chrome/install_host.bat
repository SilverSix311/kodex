@echo off
REM ============================================================
REM  Kodex Context Bridge — Native Messaging Host Installer
REM  Registers com.kodex.context with Chrome on Windows.
REM
REM  Usage:
REM    install_host.bat [EXTENSION_ID]
REM
REM  If EXTENSION_ID is not provided, you'll be prompted to enter
REM  it.  Find your extension ID at chrome://extensions after
REM  loading the extension in developer mode.
REM ============================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "HOST_MANIFEST=%SCRIPT_DIR%\com.kodex.context.json"
set "HOST_LAUNCHER=%SCRIPT_DIR%\native_host.bat"
set "REG_KEY=HKCU\Software\Google\Chrome\NativeMessagingHosts\com.kodex.context"

REM -- Get extension ID --
if "%~1"=="" (
    echo.
    echo  Kodex Context Bridge - Native Messaging Host Installer
    echo  -------------------------------------------------------
    echo.
    echo  To find your extension ID:
    echo    1. Open Chrome and go to chrome://extensions
    echo    2. Enable "Developer mode" (top right)
    echo    3. Load the extension from: %SCRIPT_DIR%
    echo    4. Copy the ID shown below the extension name
    echo.
    set /p EXT_ID="  Enter your Chrome extension ID: "
) else (
    set "EXT_ID=%~1"
)

if "%EXT_ID%"=="" (
    echo ERROR: No extension ID provided. Aborting.
    exit /b 1
)

echo.
echo  Extension ID : %EXT_ID%
echo  Host manifest: %HOST_MANIFEST%
echo  Launcher     : %HOST_LAUNCHER%
echo.

REM -- Update the allowed_origins in the host manifest --
REM  We use PowerShell to do the JSON update cleanly.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$manifest = Get-Content '%HOST_MANIFEST%' -Raw | ConvertFrom-Json; " ^
  "$manifest.allowed_origins = @('chrome-extension://%EXT_ID%/'); " ^
  "$manifest.path = '%HOST_LAUNCHER:\=\\%'; " ^
  "$manifest | ConvertTo-Json -Depth 4 | Set-Content '%HOST_MANIFEST%' -Encoding UTF8"

if errorlevel 1 (
    echo ERROR: Failed to update host manifest. Is PowerShell available?
    exit /b 1
)

echo  Updated host manifest with extension ID and launcher path.

REM -- Register in Windows Registry --
reg add "%REG_KEY%" /ve /t REG_SZ /d "%HOST_MANIFEST%" /f

if errorlevel 1 (
    echo ERROR: Failed to write registry key. Try running as Administrator.
    exit /b 1
)

echo.
echo  Registry key registered:
echo    %REG_KEY%
echo    = "%HOST_MANIFEST%"
echo.
echo  ============================================================
echo   Installation complete!
echo.
echo   Restart Chrome and open a Freshdesk/CSR/GT3 page.
echo   The Kodex Context Bridge icon should appear in your toolbar.
echo  ============================================================
echo.

endlocal
