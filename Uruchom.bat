@echo off
cd /d "%~dp0"
py -3 src\animalcross.py
if errorlevel 1 (
 echo Nie udalo sie uruchomic. Sprawdz Python 3 z Tcl/Tk.
 pause
)
