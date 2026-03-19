@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

rem build_fix.bat
rem Creates update_vX.zip (delta update) for GitHub Releases.
rem Usage:
rem   build_fix.bat "D:\path\to\OLD\WboBAMP" [NEW_DIR]

set "OLD_DIR=%~1"
set "NEW_DIR=%~2"

if "%OLD_DIR%"=="" (
  echo [ERROR] Missing OLD_DIR argument.
  echo.
  echo Usage:
  echo   build_fix.bat "D:\path\to\OLD\WboBAMP" [NEW_DIR]
  echo.
  echo Example:
  echo   build_fix.bat "D:\releases\v0.1.2.2.3\WboBAMP"
  exit /b 2
)

if "%NEW_DIR%"=="" set "NEW_DIR=%~dp0dist\WboBAMP"

if not exist "%OLD_DIR%" (
  echo [ERROR] OLD_DIR not found: "%OLD_DIR%"
  exit /b 2
)

if not exist "%NEW_DIR%" (
  echo [ERROR] NEW_DIR not found: "%NEW_DIR%"
  echo        (Usually dist\WboBAMP. Run build.bat first.)
  exit /b 2
)

where powershell >nul 2>&1
if errorlevel 1 (
  echo [ERROR] PowerShell not found in PATH.
  exit /b 2
)

set "OUT_ROOT=%~dp0fix_output"
if not exist "%OUT_ROOT%" mkdir "%OUT_ROOT%" >nul 2>&1

set "PS1=%~dp0build_fix.ps1"
if not exist "%PS1%" (
  echo [ERROR] Not found: "%PS1%"
  exit /b 2
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -OldDir "%OLD_DIR%" -NewDir "%NEW_DIR%" -OutRoot "%OUT_ROOT%"
set "RC=%ERRORLEVEL%"
echo [DEBUG] powershell exit code: %RC%

if %RC% NEQ 0 (
  echo [ERROR] Fix build failed.
  exit /b 1
)

echo.
echo [OK] Done. Output folder: "%OUT_ROOT%"
echo.
echo Tips:
echo - Upload update_vX.zip to GitHub Release assets.
echo - If you need to replace WboBAMP.exe or delete files, ship installer instead.
echo.
exit /b 0
endlocal

