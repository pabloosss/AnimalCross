@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
py -3 -m unittest discover -s tests -v
pause
