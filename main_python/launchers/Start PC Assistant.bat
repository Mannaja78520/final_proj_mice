@echo off
title MICE - Start PC Assistant
rem Starts the PC assistant (the Claude remote-control session for this folder) now, and turns on the small
rem automatic check that keeps it running (every 3 minutes, until the PC restarts or shuts down). Safe to open twice.
set "REPO=%~dp0../.."
echo.
echo  Starting the PC assistant...
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%/tools/rc_watchdog_install.ps1" -NoStart >nul 2>&1
if errorlevel 1 (
  echo  Could not turn on the automatic check. The assistant will still be started now,
  echo  but it will not restart by itself if it stops.
) else (
  echo  The automatic check is on: it looks every 3 minutes, until the PC is restarted or shut down.
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%/tools/rc_watchdog.ps1" >nul 2>&1
python "%REPO%/tools/ai_watch.py" start >nul 2>&1
ping -n 9 127.0.0.1 >nul
for /f "delims=" %%S in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%/tools/rc_watchdog.ps1" -Status') do set "STATE=%%S"
echo.
echo  The PC assistant is: %STATE%
echo  If a usage limit is reached, the work is handed on automatically and picked up again after the reset.
echo  After a restart or shutdown, open "Start PC Assistant" again. To turn it off, open "Stop PC Assistant".
echo.
pause
