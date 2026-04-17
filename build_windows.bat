@echo off
REM Build script for creating the Dienstplan Windows distribution.
REM
REM PyInstaller is run in ONE-DIR mode:  all DLLs and Python modules are
REM placed as loose files next to Dienstplan.exe inside dist\Dienstplan\.
REM This avoids the slow per-launch extraction to %TEMP% that the old
REM single-file build required.
REM
REM Outputs
REM   dist\Dienstplan\          - application folder (One-Dir layout)
REM   Dienstplan-Windows.zip    - ready-to-distribute ZIP of that folder
REM
REM Usage: build_windows.bat

echo ============================================================
echo Dienstplan - Windows Executable Builder  (One-Dir)
echo Building production-ready standalone distribution
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
if exist dist  rmdir /s /q dist
if exist Dienstplan-Windows.zip del /q Dienstplan-Windows.zip

echo.
echo [3/4] Building with PyInstaller (One-Dir mode)...
echo Note: Database will be created dynamically at runtime
python -m PyInstaller Dienstplan.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Creating distribution ZIP...
if exist dist\Dienstplan (
    powershell -NoProfile -Command "Compress-Archive -Path 'dist\Dienstplan\*' -DestinationPath 'Dienstplan-Windows.zip' -Force"
    if errorlevel 1 (
        echo ERROR: Failed to create ZIP archive
        pause
        exit /b 1
    )
    echo.
    echo ============================================================
    echo BUILD SUCCESSFUL!
    echo ============================================================
    echo.
    echo Application folder : dist\Dienstplan\
    echo Distribution ZIP   : Dienstplan-Windows.zip
    echo.
    echo Database will be created automatically on first run.
    echo Location: data\dienstplan.db  (next to Dienstplan.exe)
    echo.
    echo To test: run dist\Dienstplan\Dienstplan.exe
    echo ============================================================
) else (
    echo ERROR: dist\Dienstplan folder not found after build
    pause
    exit /b 1
)

pause
