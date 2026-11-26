@echo off
title MICE - Reset Hub Password
rem Forgot the hub password? Run this ON THE HUB PC. It edits the local login file directly, so it only works on this PC,
rem never over the network. It puts the shipped logins back on the shipped password; the hub asks for a new one at the next login.
set "REPO=%~dp0../.."
echo.
python "%REPO%/tools/hub_reset_password.py"
echo.
pause
