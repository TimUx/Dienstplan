#!/bin/bash
# Build script for creating a standalone Linux executable
# Database will be created automatically on first run (no bundled data)
#
# Usage: ./build_executable_both.sh

echo "============================================================"
echo "Dienstplan - Linux Executable Builder"
echo "Building production-ready standalone executable"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "[1/3] Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "[2/3] Cleaning previous builds..."
rm -rf build dist
rm -f Dienstplan

echo ""
echo "[3/3] Building executable with PyInstaller..."
echo "Note: Database will be created dynamically at runtime (no bundled data)"
python3 -m PyInstaller Dienstplan.spec
if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed"
    exit 1
fi

# Move executable to current directory
if [ -f dist/Dienstplan ]; then
    mv dist/Dienstplan .
    chmod +x Dienstplan
    echo ""
    echo "============================================================"
    echo "BUILD SUCCESSFUL!"
    echo "============================================================"
    echo ""
    echo "Executable created: Dienstplan"
    ls -lh Dienstplan
    echo ""
    echo "Database will be created automatically on first run."
    echo "Location: data/dienstplan.db (next to executable)"
    echo ""
    echo "The executable is standalone and production-ready."
    echo "Uses Waitress production WSGI server (no dev warnings)."
    echo "No Python installation or dependencies required."
    echo ""
    echo "To test: ./Dienstplan"
    echo "============================================================"
else
    echo "ERROR: Executable not found in dist folder"
    exit 1
fi
