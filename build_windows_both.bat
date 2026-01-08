@echo off
REM Build script for creating BOTH Windows executables (empty + sample data)
REM This script creates two separate builds in one go

echo ============================================================
echo Dienstplan - Windows Dual Executable Builder
echo Building BOTH empty database AND sample data versions
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

echo [1/2] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Building Version 1: Empty Database (Production)
echo ============================================================
echo.

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release-empty rmdir /s /q release-empty
if exist data\dienstplan.db del /q data\dienstplan.db

REM Create empty database
if not exist data mkdir data
echo Creating empty production database...
python db_init.py data\dienstplan.db
if errorlevel 1 (
    echo ERROR: Failed to create empty database
    pause
    exit /b 1
)

REM Build executable
echo Building executable with PyInstaller...
python -m PyInstaller Dienstplan.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed (empty version)
    pause
    exit /b 1
)

REM Create release folder for empty version
mkdir release-empty
copy dist\Dienstplan.exe release-empty\
xcopy /E /I data release-empty\data
copy README.md release-empty\
copy LICENSE release-empty\

echo Dienstplan - Production Version (Empty Database) > release-empty\VERSION.txt
echo. >> release-empty\VERSION.txt
echo This version contains an EMPTY database - ready for production use. >> release-empty\VERSION.txt
echo. >> release-empty\VERSION.txt
echo To start: Double-click Dienstplan.exe >> release-empty\VERSION.txt
echo Default login: admin@fritzwinter.de / Admin123! >> release-empty\VERSION.txt
echo IMPORTANT: Change password after first login! >> release-empty\VERSION.txt

echo [OK] Empty version built successfully!

echo.
echo ============================================================
echo Building Version 2: Sample Data (Demo)
echo ============================================================
echo.

REM Clean for second build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release-sample rmdir /s /q release-sample
if exist data\dienstplan.db del /q data\dienstplan.db

REM Create database with sample data
echo Creating database WITH sample data...
python db_init.py data\dienstplan.db --with-sample-data
if errorlevel 1 (
    echo ERROR: Failed to create sample database
    pause
    exit /b 1
)

REM Build executable
echo Building executable with PyInstaller...
python -m PyInstaller Dienstplan.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed (sample version)
    pause
    exit /b 1
)

REM Create release folder for sample version
mkdir release-sample
copy dist\Dienstplan.exe release-sample\
xcopy /E /I data release-sample\data
copy README.md release-sample\
copy LICENSE release-sample\

echo Dienstplan - Demo Version (With Sample Data) > release-sample\VERSION.txt
echo. >> release-sample\VERSION.txt
echo This version contains SAMPLE DATA for testing and demonstration. >> release-sample\VERSION.txt
echo Includes: 3 teams, 17 employees, sample absences >> release-sample\VERSION.txt
echo. >> release-sample\VERSION.txt
echo To start: Double-click Dienstplan.exe >> release-sample\VERSION.txt
echo Default login: admin@fritzwinter.de / Admin123! >> release-sample\VERSION.txt
echo IMPORTANT: Change password after first login! >> release-sample\VERSION.txt

echo [OK] Sample data version built successfully!

echo.
echo ============================================================
echo Creating ZIP archives...
echo ============================================================
echo.

REM Create ZIP files
powershell -Command "Compress-Archive -Path release-empty\* -DestinationPath Dienstplan-Windows-Empty.zip -Force"
if errorlevel 1 (
    echo ERROR: Failed to create empty version ZIP
    pause
    exit /b 1
)
echo [OK] Created Dienstplan-Windows-Empty.zip

powershell -Command "Compress-Archive -Path release-sample\* -DestinationPath Dienstplan-Windows-SampleData.zip -Force"
if errorlevel 1 (
    echo ERROR: Failed to create sample version ZIP
    pause
    exit /b 1
)
echo [OK] Created Dienstplan-Windows-SampleData.zip

echo.
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Created files:
echo   1. Dienstplan-Windows-Empty.zip (Production version)
echo   2. Dienstplan-Windows-SampleData.zip (Demo version)
echo.
echo Folders:
echo   - release-empty\    (Empty database build)
echo   - release-sample\   (Sample data build)
echo.
echo You can now distribute these ZIP files.
echo Both include Python and all dependencies.
echo ============================================================

pause
