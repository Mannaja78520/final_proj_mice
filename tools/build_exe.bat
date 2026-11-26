@echo off
rem Rebuild MiceHub.exe the ONE way (MiceHub.spec), from anywhere.
rem Stops a running MiceHub first: Windows will not overwrite a running exe.
taskkill /F /IM MiceHub.exe 2>nul
echo Terminated running MiceHub.exe (if any).

rem this file is in tools\, the spec is one folder up
cd /d "%~dp0.."
echo Building MiceHub.exe...
rem Polite: a build is background work (user 2026-11-26). MICE_POLITE=0 runs it at normal priority.
if "%MICE_POLITE%"=="0" (
  echo Running at NORMAL priority: MICE_POLITE=0
  python -m PyInstaller --clean --noconfirm MiceHub.spec
) else (
  start "" /belownormal /wait /b python -m PyInstaller --clean --noconfirm MiceHub.spec
)
