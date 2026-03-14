@echo off
setlocal
cd /d "%~dp0"

set "OUTDIR=%~dp0installer_output"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo ============================================
echo   Wbo BAMP - build installer
echo ============================================
echo.
echo Script folder: %~dp0
echo Output folder: %OUTDIR%
echo.

set "EXE=%~dp0dist\WboBAMP\WboBAMP.exe"
if not exist "%EXE%" (
    echo [ERROR] Not found: dist\WboBAMP\WboBAMP.exe
    echo First run build.bat to build the program.
    pause
    exit /b 1
)

set "INSTALL_IMG=%~dp0dist\INSTALL"
set "BANNER=%INSTALL_IMG%\installer_banner.png"
set "SMALL=%INSTALL_IMG%\installer_small.png"
if not exist "%INSTALL_IMG%" (
    echo [ERROR] Not found: dist\INSTALL
    echo Put installer images there: installer_banner.png, installer_small.png
    pause
    exit /b 1
)
if not exist "%BANNER%" (
    echo [ERROR] Not found: dist\INSTALL\installer_banner.png
    pause
    exit /b 1
)
if not exist "%SMALL%" (
    echo [ERROR] Not found: dist\INSTALL\installer_small.png
    pause
    exit /b 1
)
echo [1/2] Images: dist\INSTALL\*.png

set PY=python
where python >nul 2>&1
if errorlevel 1 set PY=py
if not exist "%~dp0Assets\images\faicon.ico" (
    if exist "%~dp0Assets\images\faicon.png" (
        echo Creating faicon.ico from faicon.png...
        "%PY%" -c "from PIL import Image; i=Image.open(r'%~dp0Assets/images/faicon.png'); i.save(r'%~dp0Assets/images/faicon.ico', format='ICO', sizes=[(256,256),(48,48),(32,32),(16,16)])"
    )
)

echo [2/2] Looking for Inno Setup...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    where iscc >nul 2>&1
    if not errorlevel 1 set "ISCC=iscc"
)
if not defined ISCC (
    echo Inno Setup 6 not found.
    echo.
    echo Install it from: https://jrsoftware.org/isdl.php
    echo After install, run this script again.
    echo.
    start https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

echo Building installer...
"%ISCC%" /DMyOutputDir="%OUTDIR%" "%~dp0installer.iss"
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Done. Installer: %OUTDIR%\WboBAMP_Setup_*.exe
explorer "%OUTDIR%"
pause
endlocal
