@echo off
setlocal
set "KODEX_DIR=%~dp0"
set "PYTHONPATH=%KODEX_DIR%app"
set "KODEX_DB=%KODEX_DIR%data\kodex.db"

REM Run Kodex engine with tray icon
"%KODEX_DIR%python\pythonw.exe" -m kodex_py.cli --db "%KODEX_DB%" run
