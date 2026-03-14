@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PY=python"
python --version >nul 2>&1
if errorlevel 1 (
    set "PY=py"
    py --version >nul 2>&1
    if errorlevel 1 (
        echo Python not found. Install Python and add to PATH.
        pause
        exit /b 1
    )
)

echo [1/3] Pip and deps...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
%PY% -m pip install pyinstaller

echo.
echo Select build type:
echo   [1] With console (debug)
echo   [2] Without console (GUI only)
choice /C 12 /N /M "Choose 1 or 2: "

set "BUILD_MODE=console"
if errorlevel 2 set "BUILD_MODE=window"

if /I "%BUILD_MODE%"=="console" (
    set "PYI_OPTS="
    set "BUILD_LABEL=with console"
) else (
    set "PYI_OPTS=--noconsole"
    set "BUILD_LABEL=without console"
)

echo.
echo [2/3] Icon for exe (faicon.ico)...
if not exist "Assets\images\faicon.ico" if exist "Assets\images\faicon.png" (
    %PY% -c "from PIL import Image; i=Image.open('Assets/images/faicon.png'); i.save('Assets/images/faicon.ico', format='ICO', sizes=[(256,256),(48,48),(32,32),(16,16)])"
    if exist "Assets\images\faicon.ico" echo   Created faicon.ico from faicon.png
)

echo.
echo [3/4] PyInstaller (onedir, %BUILD_LABEL%)...
set "ICON_OPT="
if exist "Assets\images\faicon.ico" set "ICON_OPT=--icon=Assets\images\faicon.ico"
%PY% -m PyInstaller --noconfirm --onedir --name "WboBAMP" %ICON_OPT% --collect-all numpy --hidden-import=numpy._core._exceptions --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets --hidden-import=PySide6.QtMultimedia --hidden-import=PySide6.QtSvg --hidden-import=PIL.Image %PYI_OPTS% main.py

if errorlevel 1 (
    echo BUILD FAILED
    pause
    exit /b 1
)

echo.
echo [4/4] Copy Assets...
set "DEST=dist\WboBAMP\Assets"
if exist "%DEST%" rmdir /S /Q "%DEST%"
xcopy /E /I /Y "Assets" "%DEST%"

echo Creating launcher (run exe with console to see errors)...
set "LAUNCH=dist\WboBAMP\run_here.bat"
echo @echo off > "%LAUNCH%"
echo cd /d "%%~dp0" >> "%LAUNCH%"
echo WboBAMP.exe >> "%LAUNCH%"
echo pause >> "%LAUNCH%"

echo.
echo OK. To run: dist\WboBAMP\run_here.bat (or WboBAMP.exe)
echo If exe does not start, use run_here.bat to see the error in console.
pause
endlocal
