@echo off
rem Starts Prize machines by itself - no hub needed. Other Mice apps that are open
rem on this PC are found automatically. Close this window to stop it.
cd /d "%~dp0.."
if exist MiceHub.exe (MiceHub.exe --alone gacha) else (python main.py --alone gacha)
pause
