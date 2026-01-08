@echo off
REM Build script for creating standalone Windows executable
REM Database will be created automatically on first run (no bundled data)
REM
REM Usage: build_windows.bat

echo ============================================================
echo Dienstplan - Windows Executable Builder
echo Building production-ready standalone executable
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

REM Check Python version is 3.9 or higher
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.9 or higher is required
    echo Current version:
    python --version
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Dienstplan.exe del /q Dienstplan.exe

echo.
echo [3/3] Building executable with PyInstaller...
echo Note: Database will be created dynamically at runtime (no bundled data)
python -m PyInstaller Dienstplan.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo Finalizing...
if exist dist\Dienstplan.exe (
    move dist\Dienstplan.exe .
    echo.
    echo ============================================================
    echo BUILD SUCCESSFUL!
    echo ============================================================
    echo.
    echo Executable created: Dienstplan.exe
    echo.
    echo Database will be created automatically on first run.
    echo Location: data\dienstplan.db (next to executable)
    echo.
    echo The executable is standalone and production-ready.
    echo Uses Waitress production WSGI server (no dev warnings).
    echo No Python installation or dependencies required.
    echo.
    echo To test: Double-click Dienstplan.exe
    echo ============================================================
) else (
    echo ERROR: Executable not found in dist folder
    pause
    exit /b 1
)

pause
