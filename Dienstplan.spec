# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for creating a standalone Windows executable
for the Dienstplan shift planning system.
"""

import os
from pathlib import Path

# Get the application directory
app_dir = Path(SPECPATH)
wwwroot_dir = app_dir / 'wwwroot'
data_dir = app_dir / 'data'

# Collect all wwwroot files
wwwroot_files = []
if wwwroot_dir.exists():
    for root, dirs, files in os.walk(wwwroot_dir):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(app_dir)
            wwwroot_files.append((str(file_path), str(rel_path.parent)))

# Collect data directory files (database)
data_files = []
if data_dir.exists():
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(app_dir)
            data_files.append((str(file_path), str(rel_path.parent)))

# Combine all data files
all_data_files = wwwroot_files + data_files

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=all_data_files,
    hiddenimports=[
        'flask',
        'flask_cors',
        'ortools',
        'ortools.sat.python.cp_model',
        'sqlite3',
        'dateutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'PIL',
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Dienstplan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console window to show server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Could add an icon file here if available
)
