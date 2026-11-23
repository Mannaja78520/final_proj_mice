@echo off
title MICE
rem Starts Nong Studio by itself - no hub needed. Other MICE apps that are open
rem on this PC are found automatically. Close this window to stop it.
cd /d "%~dp0.."
if exist ..\dist\MiceHub.exe (..\dist\MiceHub.exe --alone studio) else (python main.py --alone studio)
pause
