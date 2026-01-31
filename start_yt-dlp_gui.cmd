@echo off
setlocal
set SCRIPT_DIR=%~dp0

REM Run the PowerShell launcher. ExecutionPolicy Bypass is used for convenience.
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start_yt-dlp_gui.ps1"
if errorlevel 1 pause

endlocal
