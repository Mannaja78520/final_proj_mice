@echo off
title MICE - Stop PC Assistant
rem Turns off the automatic check and stops the PC assistant session (only that one). Safe to open twice.
set "REPO=%~dp0../.."
echo.
echo  Turning off the automatic check...
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%/tools/rc_watchdog_uninstall.ps1" >nul 2>&1
echo  Stopping the PC assistant...
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%/tools/rc_watchdog.ps1" -StopSession >nul 2>&1
echo.
python "%REPO%/tools/ai_watch.py" stop >nul 2>&1
echo  Done. The PC assistant will not start by itself any more.
echo  To start it again, open "Start PC Assistant".
echo.
pause
