@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set PY=python
python --version >nul 2>&1
if errorlevel 1 (
    set PY=py
    py --version >nul 2>&1
    if errorlevel 1 (
        echo Python not found. Install Python and add to PATH.
        pause
        exit /b 1
    )
)

echo [1/2] Installing dependencies...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/2] Starting WBO Animation...
%PY% main.py
if errorlevel 1 (
    echo.
    echo Program exited with error.
    pause
    exit /b 1
)

endlocal
