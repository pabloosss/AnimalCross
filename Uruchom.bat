@echo off
cd /d "%~dp0"
py -3 animalcross.py
if errorlevel 1 (
 echo Nie udalo sie uruchomic. Sprawdz instalacje Python 3 z Tcl/Tk.
 pause
)
