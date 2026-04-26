"""
Launcher script for standalone Windows executable.
Starts the web server and automatically opens the browser.
"""

import sys
import os
import webbrowser
import threading
import time
from pathlib import Path


def _parse_bootstrap_env(file_path: Path) -> dict:
    """Parse simple KEY=VALUE lines from bootstrap env file."""
    values = {}
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _apply_one_time_bootstrap_credentials(data_dir: Path) -> Path | None:
    """
    Load one-time bootstrap credentials from a file in data directory.

    The file is consumed only for first database initialization and removed
    afterwards to avoid keeping plaintext passwords on disk.
    """
    bootstrap_file = data_dir / "bootstrap.env"
    if not bootstrap_file.exists():
        return None

    try:
        bootstrap_values = _parse_bootstrap_env(bootstrap_file)
    except Exception as exc:
        print(f"[!] Could not read bootstrap credentials: {exc}")
        return None

    admin_email = bootstrap_values.get("DIENSTPLAN_INITIAL_ADMIN_EMAIL")
    admin_password = bootstrap_values.get("DIENSTPLAN_INITIAL_ADMIN_PASSWORD")
    if admin_email:
        os.environ["DIENSTPLAN_INITIAL_ADMIN_EMAIL"] = admin_email
    if admin_password:
        os.environ["DIENSTPLAN_INITIAL_ADMIN_PASSWORD"] = admin_password
    if admin_email or admin_password:
        print("[i] One-time bootstrap credentials loaded for initial setup.")
    return bootstrap_file


def open_browser(url, delay=2):
    """Open browser after a short delay to let server start"""
    time.sleep(delay)
    print(f"\n[>] Opening browser at {url}...")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[!] Could not automatically open browser: {e}")
        print(f"Please manually open your browser and navigate to: {url}")

def main():
    """Main launcher function"""
    # Determine application and data paths
    configured_data_dir = os.environ.get("DIENSTPLAN_DATA_DIR", "").strip()
    if configured_data_dir:
        data_dir = Path(configured_data_dir).expanduser()
    elif getattr(sys, 'frozen', False):
        # Running in a bundle (PyInstaller). Store data in a per-user writable path
        # so the app can run without administrator privileges.
        if os.name == "nt":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                data_dir = Path(local_appdata) / "Dienstplan" / "data"
            else:
                data_dir = Path.home() / "AppData" / "Local" / "Dienstplan" / "data"
        else:
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if xdg_data_home:
                data_dir = Path(xdg_data_home) / "Dienstplan" / "data"
            else:
                data_dir = Path.home() / ".local" / "share" / "Dienstplan" / "data"
    else:
        # Running in normal Python environment
        application_path = Path(__file__).parent
        data_dir = application_path / "data"
    
    # Ensure data directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("DIENSTPLAN - Schichtverwaltungssystem")
    print("Version 2.1 - Python Edition")
    print("=" * 60)
    print()
    print("[*] Starting production web server...")
    print()
    
    # Configuration
    host = "127.0.0.1"  # localhost only for security
    port = 5000
    db_path = str(data_dir / "dienstplan.db")
    
    # Check if database exists, if not initialize it; otherwise run migrations
    bootstrap_file_to_delete = None
    if not os.path.exists(db_path):
        print("[i] No database found. Initializing new database...")
        print()
        bootstrap_file_to_delete = _apply_one_time_bootstrap_credentials(data_dir)
        try:
            from db_init import initialize_database
            # Initialize without sample data (production-ready empty database)
            initialize_database(db_path, with_sample_data=False)
            print()
        except ImportError as e:
            print(f"[!] Could not import database initialization module: {e}")
            print("   The application may be corrupted.")
            print()
        except Exception as e:
            print(f"[!] Error initializing database: {e}")
            print("   The application may not work correctly.")
            print()
        finally:
            if bootstrap_file_to_delete and bootstrap_file_to_delete.exists():
                try:
                    bootstrap_file_to_delete.unlink()
                    print("[i] Removed one-time bootstrap credential file.")
                except Exception as exc:
                    print(f"[!] Could not remove bootstrap credential file: {exc}")
    else:
        # Existing database – apply any outstanding migrations automatically
        try:
            from db_init import run_migrations
            run_migrations(db_path)
        except ImportError as e:
            print(f"[!] Could not import migration module: {e}")
        except Exception as e:
            print(f"[!] Error running migrations: {e}")
            print("   The application may not work correctly.")
    
    # Start browser opener in background thread
    url = f"http://{host}:{port}"
    browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    browser_thread.start()
    
    # Import and start FastAPI app with Uvicorn (production ASGI server)
    try:
        from web_api import create_app
        try:
            import uvicorn
        except ImportError as e:
            raise ImportError("uvicorn module not found. Please install it with: pip install uvicorn[standard]") from e
        
        print(f"[OK] Server will be available at: {url}")
        print("[i] Using Uvicorn production ASGI server")
        print()
        print("[i] Tip: Close this window or press Ctrl+C to stop the server")
        print("=" * 60)
        print()
        
        app = create_app(db_path)
        # Use uvicorn production server
        uvicorn.run(app, host=host, port=port, log_level="info")
        
    except KeyboardInterrupt:
        print("\n\n[*] Shutting down server...")
        print("Thank you for using Dienstplan!")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e) or "WinError 10048" in str(e):
            print(f"\n[X] Error: Port {port} is already in use!")
            print("   Another application is using this port.")
            print("   Please close the other application or use a different port.")
        else:
            print(f"\n[X] Network error: {e}")
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)
    except ImportError as e:
        print(f"\n[X] Missing dependency: {e}")
        print("   The application may be corrupted.")
        print("   Please download a fresh copy from GitHub.")
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] Unexpected error starting server: {e}")
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    main()
