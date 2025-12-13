@echo off
REM Build script for creating standalone Windows executable
REM This script uses PyInstaller to bundle the application

echo ============================================================
echo Dienstplan - Windows Executable Builder
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from python.org
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Dienstplan.exe del /q Dienstplan.exe

echo.
echo [3/4] Building executable with PyInstaller...
python -m PyInstaller Dienstplan.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Finalizing...
if exist dist\Dienstplan.exe (
    move dist\Dienstplan.exe .
    echo.
    echo ============================================================
    echo BUILD SUCCESSFUL!
    echo ============================================================
    echo.
    echo Executable created: Dienstplan.exe
    echo File size: 
    dir Dienstplan.exe | find "Dienstplan.exe"
    echo.
    echo You can now distribute this executable.
    echo It includes Python and all dependencies.
    echo.
    echo To test: Double-click Dienstplan.exe
    echo ============================================================
) else (
    echo ERROR: Executable not found in dist folder
    pause
    exit /b 1
)

pause
