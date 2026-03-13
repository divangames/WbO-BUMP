@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [1/3] Pip and deps...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m pip install pyinstaller

echo.
echo [2/3] PyInstaller (onedir, with console)...
py -m PyInstaller --noconfirm --onedir --name "WBOAnimation" --collect-all numpy --hidden-import=numpy._core._exceptions --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets --hidden-import=PySide6.QtMultimedia --hidden-import=PySide6.QtSvg --hidden-import=PIL.Image main.py

if errorlevel 1 (
    echo BUILD FAILED
    pause
    exit /b 1
)

echo.
echo [3/3] Copy Assets...
set "DEST=dist\WBOAnimation\Assets"
if exist "%DEST%" rmdir /S /Q "%DEST%"
xcopy /E /I /Y "Assets" "%DEST%"

echo Creating launcher (run exe with console to see errors)...
set "LAUNCH=dist\WBOAnimation\run_here.bat"
echo @echo off > "%LAUNCH%"
echo cd /d "%%~dp0" >> "%LAUNCH%"
echo WBOAnimation.exe >> "%LAUNCH%"
echo pause >> "%LAUNCH%"

echo.
echo OK. To run: dist\WBOAnimation\run_here.bat (or WBOAnimation.exe)
echo If exe does not start, use run_here.bat to see the error in console.
pause
endlocal
