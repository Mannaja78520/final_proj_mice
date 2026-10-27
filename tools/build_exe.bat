@echo off
rem Rebuild MiceHub.exe the ONE way (MiceHub.spec), from anywhere.
rem Stops a running MiceHub first: Windows will not overwrite a running exe.
taskkill /F /IM MiceHub.exe 2>nul
echo Terminated running MiceHub.exe (if any).

rem this file is in tools\, the spec is one folder up
cd /d "%~dp0.."
echo Building MiceHub.exe...
python -m PyInstaller --clean --noconfirm MiceHub.spec
