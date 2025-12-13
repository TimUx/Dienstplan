#!/bin/bash
# Build script for creating standalone executable
# This script uses PyInstaller to bundle the application

echo "============================================================"
echo "Dienstplan - Standalone Executable Builder"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "[1/4] Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "[2/4] Cleaning previous build..."
rm -rf build dist
rm -f Dienstplan Dienstplan.exe

echo ""
echo "[3/4] Building executable with PyInstaller..."
python3 -m PyInstaller Dienstplan.spec
if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed"
    exit 1
fi

echo ""
echo "[4/4] Finalizing..."

# Determine executable name based on OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    EXECUTABLE="Dienstplan.exe"
else
    EXECUTABLE="Dienstplan"
fi

if [ -f "dist/$EXECUTABLE" ]; then
    mv "dist/$EXECUTABLE" .
    chmod +x "$EXECUTABLE"
    echo ""
    echo "============================================================"
    echo "BUILD SUCCESSFUL!"
    echo "============================================================"
    echo ""
    echo "Executable created: $EXECUTABLE"
    ls -lh "$EXECUTABLE"
    echo ""
    echo "You can now distribute this executable."
    echo "It includes Python and all dependencies."
    echo ""
    echo "To test: ./$EXECUTABLE"
    echo "============================================================"
else
    echo "ERROR: Executable not found in dist folder"
    exit 1
fi
