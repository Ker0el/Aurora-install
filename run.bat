@echo off
title Aurora Install - 极光入库

echo ========================================
echo   Aurora Install - 极光入库 Version
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.8+
    pause
    exit /b 1
)

echo [INFO] Checking dependencies...
python -c "import qasync" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Missing dependencies, installing automatically...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency installation failed, please run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo [SUCCESS] Dependencies installed
    echo.
)

echo [INFO] Starting Aurora Install...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Program error occurred
    pause
)