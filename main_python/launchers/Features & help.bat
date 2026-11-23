@echo off
rem Starts Features & help by itself - no hub needed. Other Mice apps that are open
rem on this PC are found automatically. Close this window to stop it.
cd /d "%~dp0.."
if exist ..\dist\MiceHub.exe (..\dist\MiceHub.exe --alone help) else (python main.py --alone help)
pause
