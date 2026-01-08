#!/bin/bash
# Build script for creating BOTH Linux executables (empty + sample data)
# This script creates two separate builds in one go
#
# Usage: ./build_executable_both.sh

echo "============================================================"
echo "Dienstplan - Linux Dual Executable Builder"
echo "Building BOTH empty database AND sample data versions"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "[1/2] Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "============================================================"
echo "Building Version 1: Empty Database (Production)"
echo "============================================================"
echo ""

# Clean previous builds
rm -rf build dist release-empty
rm -f data/dienstplan.db

# Create empty database
mkdir -p data
echo "Creating empty production database..."
python3 db_init.py data/dienstplan.db
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create empty database"
    exit 1
fi

# Build executable
echo "Building executable with PyInstaller..."
python3 -m PyInstaller Dienstplan.spec
if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed (empty version)"
    exit 1
fi

# Create release folder for empty version
mkdir -p release-empty
cp dist/Dienstplan release-empty/
cp -r data release-empty/
cp README.md release-empty/
cp LICENSE release-empty/

cat > release-empty/VERSION.txt << EOF
Dienstplan - Production Version (Empty Database)

This version contains an EMPTY database - ready for production use.

To start: ./Dienstplan
Default login: admin@fritzwinter.de / Admin123!
IMPORTANT: Change password after first login!
EOF

chmod +x release-empty/Dienstplan
echo "[OK] Empty version built successfully!"

echo ""
echo "============================================================"
echo "Building Version 2: Sample Data (Demo)"
echo "============================================================"
echo ""

# Clean for second build
rm -rf build dist release-sample
rm -f data/dienstplan.db

# Create database with sample data
echo "Creating database WITH sample data..."
python3 db_init.py data/dienstplan.db --with-sample-data
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create sample database"
    exit 1
fi

# Build executable
echo "Building executable with PyInstaller..."
python3 -m PyInstaller Dienstplan.spec
if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed (sample version)"
    exit 1
fi

# Create release folder for sample version
mkdir -p release-sample
cp dist/Dienstplan release-sample/
cp -r data release-sample/
cp README.md release-sample/
cp LICENSE release-sample/

cat > release-sample/VERSION.txt << EOF
Dienstplan - Demo Version (With Sample Data)

This version contains SAMPLE DATA for testing and demonstration.
Includes: 3 teams, 17 employees, sample absences

To start: ./Dienstplan
Default login: admin@fritzwinter.de / Admin123!
IMPORTANT: Change password after first login!
EOF

chmod +x release-sample/Dienstplan
echo "[OK] Sample data version built successfully!"

echo ""
echo "============================================================"
echo "Creating tar.gz archives..."
echo "============================================================"
echo ""

# Create tar.gz files
tar -czf Dienstplan-Linux-Empty.tar.gz -C release-empty .
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create empty version tar.gz"
    exit 1
fi
echo "[OK] Created Dienstplan-Linux-Empty.tar.gz"

tar -czf Dienstplan-Linux-SampleData.tar.gz -C release-sample .
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create sample version tar.gz"
    exit 1
fi
echo "[OK] Created Dienstplan-Linux-SampleData.tar.gz"

echo ""
echo "============================================================"
echo "BUILD COMPLETE!"
echo "============================================================"
echo ""
echo "Created files:"
echo "  1. Dienstplan-Linux-Empty.tar.gz (Production version)"
echo "  2. Dienstplan-Linux-SampleData.tar.gz (Demo version)"
echo ""
echo "Folders:"
echo "  - release-empty/    (Empty database build)"
echo "  - release-sample/   (Sample data build)"
echo ""
echo "You can now distribute these tar.gz files."
echo "Both include Python and all dependencies."
echo "============================================================"
