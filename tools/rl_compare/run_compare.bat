@echo off
rem RL vs planner comparison: one double-click (A50-1). Settings: config\rl_compare.json
rem Add --fresh after the command to retrain after changing settings.
cd /d "%~dp0\..\.."
python -m tools.rl_compare.run %*
if exist ".local\rl_compare\index.html" start "" ".local\rl_compare\index.html"
pause
