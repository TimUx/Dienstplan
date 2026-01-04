# Building the Windows Standalone Executable

This guide explains how to build the Dienstplan Windows standalone executable from source.

## Prerequisites

- **Windows OS** (or cross-compilation setup)
- **Python 3.11 or higher** recommended (minimum 3.9)
- **Git** (optional, for cloning the repository)
- **Internet connection** (for downloading dependencies)

## Quick Build (Windows)

### Option 1: Using the Build Script (Recommended)

1. Open Command Prompt or PowerShell in the Dienstplan directory
2. Run the build script:
   ```cmd
   REM Build with empty database (production-ready, default)
   build_windows.bat
   
   REM Build with sample data (for testing/demo)
   build_windows.bat --sample-data
   ```
3. Wait for the build to complete (~2-5 minutes)
4. The executable `Dienstplan.exe` will be created in the current directory
5. The database will be in the `data/` directory

**Output:**
- `Dienstplan.exe` - The standalone executable
- `data/dienstplan.db` - Pre-initialized, persistent database

### Option 2: Manual Build

```cmd
REM Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Create production database (empty)
mkdir data
python db_init.py data\dienstplan.db

REM OR: Create database with sample data
python db_init.py data\dienstplan.db --with-sample-data

REM Clean previous builds
rmdir /s /q build dist
if exist Dienstplan.exe del /q Dienstplan.exe

REM Build with PyInstaller
python -m PyInstaller Dienstplan.spec

REM Move executable to main directory
move dist\Dienstplan.exe .
```

## Quick Build (Linux/macOS)

While primarily for Windows, you can build a Linux/macOS executable:

```bash
chmod +x build_executable.sh

# Build with empty database (production-ready, default)
./build_executable.sh

# Build with sample data (for testing/demo)
./build_executable.sh --sample-data
```

**Output:**
- `Dienstplan` (or `Dienstplan.exe` on Windows with WSL)
- `data/dienstplan.db` - Pre-initialized, persistent database

## Understanding the Build Process

### Step 1: Install Dependencies
The script installs all Python packages from `requirements.txt`:
- **ortools** - Constraint programming solver
- **Flask** - Web framework
- **flask-cors** - CORS support
- **PyInstaller** - Executable builder

### Step 2: Create Production Database
The script creates a pre-initialized SQLite database:
- **Location**: `data/dienstplan.db`
- **Schema**: All tables, indexes, and constraints
- **Default data**: Admin user, roles, shift types
- **Optional**: Sample data (teams, employees) with `--sample-data` flag

### Step 3: PyInstaller Analysis
PyInstaller analyzes the `launcher.py` script and all its dependencies:
- Identifies all imported modules
- Collects binary dependencies
- Bundles the `wwwroot` directory (web UI files)
- Bundles the `data` directory (database)

### Step 4: Bundle Creation
PyInstaller creates a single executable containing:
- Python 3.11 runtime
- All Python packages
- Web UI assets
- Pre-initialized database template
- Application code

### Step 5: Executable Generation
The final `Dienstplan.exe` is created with:
- Size: ~120-150 MB (includes Python runtime and all libraries)
- Format: Windows PE executable
- Console: Visible (shows server logs)
- Database: Persistent in `data/` directory next to executable

## Build Configuration

### PyInstaller Spec File (`Dienstplan.spec`)

Key configuration options:

```python
# Entry point
['launcher.py']

# OR-Tools binary dependencies (critical for Windows builds!)
# Automatically collects all .pyd, .so, and .dll files from OR-Tools
binaries=ortools_binaries

# Data files to include
datas=wwwroot_files + data_files  # All files from wwwroot/ and data/

# Hidden imports (modules not auto-detected)
hiddenimports=[
    'flask',
    'flask_cors',
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
]

# Executable options
name='Dienstplan'       # Output name
console=True            # Show console window
upx=True               # Compress with UPX
```

**Important Note on OR-Tools:** The spec file includes special code to collect OR-Tools native binary files. This is essential for Windows builds where the `cp_model_helper` DLL and other native dependencies must be explicitly included.

### Customization Options

#### Change the Executable Name
Edit `Dienstplan.spec`, line ~59:
```python
name='MyCustomName',
```

#### Hide Console Window
Edit `Dienstplan.spec`, line ~61:
```python
console=False,  # Hide console window
```
**Warning:** This makes debugging harder!

#### Add an Icon
1. Add your `.ico` file to the project
2. Edit `Dienstplan.spec`, line ~69:
```python
icon='path/to/icon.ico',
```

#### Change Default Port
Edit `launcher.py`, line ~45:
```python
port = 8080  # Change from 5000
```

## Troubleshooting Build Issues

### Issue: "DLL load failed while importing cp_model_helper"

**Symptom:** Windows executable starts but fails with error:
```
❌ Missing dependency: DLL load failed while importing cp_model_helper: Das angegebene Modul wurde nicht gefunden.
```

**Cause:** OR-Tools native binary dependencies (.pyd/.dll files) are not included in the executable

**Solution:** This has been fixed in the current version of `Dienstplan.spec`. If you're using an older version:
1. Update `Dienstplan.spec` from the repository
2. Ensure the spec file includes the `ortools_binaries` collection code
3. Rebuild the executable: `python -m PyInstaller Dienstplan.spec`

The spec file automatically collects all OR-Tools binary files during the build process.

### Issue: "ModuleNotFoundError" during build

**Cause:** Missing Python package

**Solution:**
```cmd
pip install --upgrade -r requirements.txt
```

### Issue: "Failed to execute script"

**Cause:** Hidden import not detected by PyInstaller

**Solution:** Add the module to `hiddenimports` in `Dienstplan.spec`

### Issue: Build is very slow

**Cause:** PyInstaller needs to analyze all dependencies

**Solution:** This is normal. First build takes 2-5 minutes. Subsequent builds are faster.

### Issue: Executable is very large

**Cause:** Includes Python runtime and all libraries

**Solution:** This is expected. Size can be reduced by:
- Removing unused dependencies from `requirements.txt`
- Disabling UPX compression (makes it larger but sometimes more compatible)

### Issue: Antivirus blocks the executable

**Cause:** Some antivirus software flags PyInstaller executables

**Solution:**
- Add the build directory to antivirus whitelist
- Submit the executable to antivirus vendors as false positive
- Sign the executable with a code signing certificate (advanced)

## Production Database

### Database Location
The production database is stored in the `data/` directory:
- **Path**: `data/dienstplan.db`
- **Persistence**: The database persists between runs
- **Bundled**: The database is included in the PyInstaller bundle

### Default Database Contents
The pre-initialized database includes:
- ✅ All database tables and indexes
- ✅ Default roles (Admin, Mitarbeiter)
- ✅ Admin user (`admin@fritzwinter.de` / `Admin123!`)
- ✅ Standard shift types (F, S, N, Z, BMT, BSB, K, U, L)
- ❌ No teams (empty by default)
- ❌ No employees (empty by default)

### Building with Sample Data
To include sample data for testing/demo purposes:

**Windows:**
```cmd
build_windows.bat --sample-data
```

**Linux/macOS:**
```bash
./build_executable.sh --sample-data
```

This adds:
- ✅ 3 sample teams (Alpha, Beta, Gamma)
- ✅ 19 sample employees (15 regular + 4 springers)
- ✅ Various roles and qualifications

### Customizing the Database
To create a custom database before building:

1. Create your database:
   ```bash
   python db_init.py data/dienstplan.db
   ```

2. Populate with your data:
   ```bash
   python main.py serve --db data/dienstplan.db
   # Use the web interface to add your teams, employees, etc.
   ```

3. Build the executable:
   ```bash
   build_windows.bat
   ```

The custom database will be bundled with the executable.

### Database Migration
When users first run the executable:
1. The bundled database template is copied to `data/dienstplan.db` next to the executable
2. All subsequent data is stored in this persistent location
3. Users can backup/restore by copying the `data/` folder

## CI/CD Build (GitHub Actions)

The executable is automatically built on GitHub Actions when pushing to `main`:

1. Workflow file: `.github/workflows/build-and-release.yml`
2. Triggered on: Push to `main` branch
3. Build platform: `windows-latest` runner
4. Outputs: ZIP file with executable and documentation
5. Release: Automatically creates GitHub release

### Manual GitHub Release Build

To trigger a release build:

```bash
git checkout main
git tag v2.0.1
git push origin v2.0.1
```

## Distribution

### What to Include in Distribution

**Minimal (Required):**
- `Dienstplan.exe` - The standalone executable
- `data/` - Directory containing the database
  - `data/dienstplan.db` - Pre-initialized database

**Recommended:**
- `Dienstplan.exe` - The standalone executable
- `data/` - Directory with database
- `README.md` - General documentation
- `LICENSE` - License file
- `VERSION.txt` - Version information

**Optional:**
- `docs/WINDOWS_EXECUTABLE.md` - User guide

### Creating a Distribution ZIP

```cmd
REM Create release directory
mkdir release

REM Copy files
copy Dienstplan.exe release\
xcopy /E /I data release\data
copy README.md release\
copy LICENSE release\

REM Create version file
echo Dienstplan v2.0.1 > release\VERSION.txt
echo No Python installation required! >> release\VERSION.txt
echo Database location: data\dienstplan.db >> release\VERSION.txt

REM Create ZIP
powershell Compress-Archive -Path release\* -DestinationPath Dienstplan-Windows-v2.0.1.zip
```

## File Size Optimization

To reduce executable size:

### Remove Unnecessary Dependencies

Edit `requirements.txt` and remove packages you don't need, then rebuild.

### Use --onefile without UPX

Edit `Dienstplan.spec`, line ~62:
```python
upx=False,
```

### Exclude Unused Modules

Add to `Dienstplan.spec`, line ~33:
```python
excludes=['tkinter', 'matplotlib', 'test'],
```

## Testing the Build

### Basic Functionality Test

```cmd
REM Test executable starts
Dienstplan.exe

REM Verify in browser
REM Open http://localhost:5000
REM Check if UI loads
```

### Automated Testing

```python
# test_executable.py
import subprocess
import time
import requests

# Start executable
proc = subprocess.Popen(['Dienstplan.exe'])

# Wait for server to start
time.sleep(5)

# Test endpoint
response = requests.get('http://localhost:5000')
assert response.status_code == 200

# Cleanup
proc.terminate()
```

## Security Considerations

### Code Signing (Recommended for Distribution)

For professional distribution, sign the executable:

1. Obtain a code signing certificate
2. Install SignTool (Windows SDK)
3. Sign the executable:
   ```cmd
   signtool sign /f certificate.pfx /p password Dienstplan.exe
   ```

### Virus Scanning

Before distribution, scan with:
- Windows Defender
- VirusTotal (virustotal.com)
- Multiple antivirus engines

## Support

For build issues:
- **GitHub Issues**: https://github.com/TimUx/Dienstplan/issues
- **PyInstaller Docs**: https://pyinstaller.org/
- **Build Logs**: Check console output for detailed error messages

---

**Remember:** The first build takes longer. Be patient!

Good luck building! 🚀
