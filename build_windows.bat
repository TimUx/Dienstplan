@echo off
REM Build script for creating standalone Windows executable
REM This script uses PyInstaller to bundle the application
REM
REM Usage:
REM   build_windows.bat              - Build with empty database (default)
REM   build_windows.bat --sample-data - Build with sample data included

echo ============================================================
echo Dienstplan - Windows Executable Builder
echo ============================================================
echo.

REM Parse command line arguments
set INCLUDE_SAMPLE_DATA=0
if "%1"=="--sample-data" set INCLUDE_SAMPLE_DATA=1
if "%1"=="--with-sample-data" set INCLUDE_SAMPLE_DATA=1

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from python.org
    pause
    exit /b 1
)

REM Check Python version is 3.9 or higher
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.9 or higher is required
    echo Current version:
    python --version
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
echo [2/5] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Dienstplan.exe del /q Dienstplan.exe
if exist data\dienstplan.db del /q data\dienstplan.db

echo.
echo [3/5] Creating production database...
if not exist data mkdir data
if %INCLUDE_SAMPLE_DATA%==1 (
    echo Creating database WITH sample data...
    python db_init.py data\dienstplan.db --with-sample-data
) else (
    echo Creating empty production database...
    python db_init.py data\dienstplan.db
)
if errorlevel 1 (
    echo ERROR: Failed to create database
    pause
    exit /b 1
)

echo.
echo [4/5] Building executable with PyInstaller...
python -m PyInstaller Dienstplan.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [5/5] Finalizing...
if exist dist\Dienstplan.exe (
    move dist\Dienstplan.exe .
    echo.
    echo ============================================================
    echo BUILD SUCCESSFUL!
    echo ============================================================
    echo.
    echo Executable created: Dienstplan.exe
    if %INCLUDE_SAMPLE_DATA%==1 (
        echo Database: data\dienstplan.db (WITH sample data)
    ) else (
        echo Database: data\dienstplan.db (empty, production-ready)
    )
    echo.
    echo You can now distribute this executable with the data folder.
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
