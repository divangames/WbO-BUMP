@echo off
chcp 65001 >nul
REM Запуск приложения WBO Animation
cd /d "%~dp0"
py main.py
