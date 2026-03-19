@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pack_github_update.ps1" %*
if errorlevel 1 exit /b 1
