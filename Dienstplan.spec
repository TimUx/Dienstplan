# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for creating a standalone Windows executable
for the Dienstplan shift planning system.
"""

import os
import sys
from pathlib import Path

# Get the application directory
app_dir = Path(SPECPATH)
wwwroot_dir = app_dir / 'wwwroot'

# Collect all wwwroot files
wwwroot_files = []
if wwwroot_dir.exists():
    for root, dirs, files in os.walk(wwwroot_dir):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(app_dir)
            wwwroot_files.append((str(file_path), str(rel_path.parent)))

# DO NOT bundle the data directory or database
# The database will be created dynamically at runtime next to the executable
# This ensures a clean, empty production database for each installation

# Collect OR-Tools binary files
# This is critical for Windows builds where PyInstaller doesn't automatically
# detect the native binary dependencies (.pyd and .dll files)
ortools_binaries = []
try:
    import ortools
    ortools_dir = Path(ortools.__file__).parent
    
    # Collect all .pyd files (Python extension modules on Windows)
    # and .so files (on Linux, for cross-platform compatibility)
    for root, dirs, files in os.walk(ortools_dir):
        for file in files:
            if file.endswith(('.pyd', '.so', '.dll')):
                file_path = Path(root) / file
                rel_path = file_path.relative_to(ortools_dir.parent)
                ortools_binaries.append((str(file_path), str(rel_path.parent)))
    
    print(f"Found {len(ortools_binaries)} OR-Tools binary files")
except ImportError:
    print("Warning: OR-Tools not found. Binary collection skipped.")

# Only include wwwroot files, not data directory
all_data_files = wwwroot_files

# Include the migrations folder so Alembic can find scripts at runtime
migrations_dir = app_dir / 'migrations'
if migrations_dir.exists():
    for root, dirs, files in os.walk(migrations_dir):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(app_dir)
            all_data_files.append((str(file_path), str(rel_path.parent)))

block_cipher = None

is_windows = sys.platform.startswith('win')
exe_name = 'Dienstplan.exe' if is_windows else 'Dienstplan'
collect_name = 'Dienstplan' if is_windows else 'Dienstplan_bundle'

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=ortools_binaries,  # Include OR-Tools binary dependencies
    datas=all_data_files,
    hiddenimports=[
        'fastapi',
        'starlette',
        'uvicorn',
        'ortools',
        'ortools.sat',
        'ortools.sat.python',
        'ortools.sat.python.cp_model',
        'ortools.init',
        'ortools.init.python',
        'ortools.init.python.init',
        'sqlite3',
        'dateutil',
        'google',
        'google.protobuf',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-Dir build: only scripts are bundled into the EXE itself.
# All binaries, data files and Python modules are placed as loose files
# in the output folder next to Dienstplan.exe.  This eliminates the
# per-launch extraction to %TEMP% that makes the one-file build slow.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,           # required by PyInstaller 6.x for onedir+COLLECT builds
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                       # UPX on individual DLLs gives no real benefit
    console=True,                    # Keep console window to show server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                       # Add an .ico path here if an icon is available
)

# COLLECT assembles the full application folder (dist/Dienstplan/).
# The user distributes this folder (as a ZIP or via the Inno Setup installer).
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=collect_name,               # -> dist/Dienstplan/ on Windows, dist/Dienstplan_bundle/ on Linux
)
