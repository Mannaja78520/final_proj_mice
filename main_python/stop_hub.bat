@echo off
rem Stops the Mice hub on this PC and everything it started (voice helper,
rem face watcher, the friends' apps). Double-click; safe when nothing runs.
cd /d "%~dp0"
if exist MiceHub.exe (MiceHub.exe --stop) else (python main.py --stop)
pause
