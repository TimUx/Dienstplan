#!/bin/bash
# Build script for creating standalone executable
# This script uses PyInstaller to bundle the application
#
# Usage:
#   ./build_executable.sh              - Build with empty database (default)
#   ./build_executable.sh --sample-data - Build with sample data included

echo "============================================================"
echo "Dienstplan - Standalone Executable Builder"
echo "============================================================"
echo ""

# Parse command line arguments
INCLUDE_SAMPLE_DATA=0
if [ "$1" = "--sample-data" ] || [ "$1" = "--with-sample-data" ]; then
    INCLUDE_SAMPLE_DATA=1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "[1/5] Installing dependencies..."
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
echo "Note: Database will be created dynamically at runtime (no bundled data)"
python3 -m PyInstaller Dienstplan.spec
if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed"
    exit 1
fi

echo ""
echo "[4/4] Finalizing..."

# Determine executable name based on OS
case "$OSTYPE" in
    msys*|win32*|cygwin*|mingw*)
        EXECUTABLE="Dienstplan.exe"
        ;;
    *)
        EXECUTABLE="Dienstplan"
        ;;
esac

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
    echo "Database will be created automatically on first run."
    echo "Location: data/dienstplan.db (next to executable)"
    echo ""
    echo "The executable is standalone and production-ready."
    echo "No Python installation or dependencies required."
    echo ""
    echo "To test: ./$EXECUTABLE"
    echo "============================================================"
else
    echo "ERROR: Executable not found in dist folder"
    exit 1
fi
