@echo off
rem Mice control hub launcher (Windows) - double-click to start.
rem The hub opens at http://127.0.0.1:8642/ and finds all modules by itself;
rem Nong Studio is at /studio/.
cd /d "%~dp0"
if exist MiceHub.exe (MiceHub.exe) else (python main.py)
pause
