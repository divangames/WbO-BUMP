@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Reinstalling dependencies for WBO Animation...
echo.

echo 1. Uninstalling PySide6, numpy...
py -m pip uninstall PySide6 PySide6-Essentials PySide6-Addons shiboken6 numpy -y 2>nul

echo.
echo 2. Installing from requirements.txt...
py -m pip install -r requirements.txt

echo.
echo Done. Run: py main.py
echo If you see ~umpy warning, remove folder ~umpy in site-packages.
pause
