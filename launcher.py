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

try:
    from waitress import serve
except ImportError:
    serve = None

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
    if getattr(sys, 'frozen', False):
        # Running in a bundle (PyInstaller)
        # Data directory should be next to the executable for persistence
        exe_dir = Path(sys.executable).parent
        data_dir = exe_dir / "data"
    else:
        # Running in normal Python environment
        application_path = Path(__file__).parent
        data_dir = application_path / "data"
    
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)
    
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
    
    # Check if database exists, if not initialize it
    if not os.path.exists(db_path):
        print("[i] No database found. Initializing new database...")
        print()
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
    
    # Start browser opener in background thread
    url = f"http://{host}:{port}"
    browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    browser_thread.start()
    
    # Import and start Flask app with waitress (production WSGI server)
    try:
        from web_api import create_app
        
        if serve is None:
            raise ImportError("waitress module not found")
        
        print(f"[OK] Server will be available at: {url}")
        print("[i] Using Waitress production WSGI server")
        print()
        print("[i] Tip: Close this window or press Ctrl+C to stop the server")
        print("=" * 60)
        print()
        
        app = create_app(db_path)
        # Use waitress production server instead of Flask development server
        serve(app, host=host, port=port, threads=4)
        
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
