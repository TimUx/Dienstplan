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

def open_browser(url, delay=2):
    """Open browser after a short delay to let server start"""
    time.sleep(delay)
    print(f"\n🌐 Opening browser at {url}...")
    webbrowser.open(url)

def main():
    """Main launcher function"""
    # Set up paths for bundled application
    if getattr(sys, 'frozen', False):
        # Running in a bundle (PyInstaller)
        application_path = Path(sys._MEIPASS)
    else:
        # Running in normal Python environment
        application_path = Path(__file__).parent
    
    print("=" * 60)
    print("DIENSTPLAN - Schichtverwaltungssystem")
    print("Version 2.0 - Python Edition")
    print("=" * 60)
    print()
    print("🚀 Starting web server...")
    print()
    
    # Configuration
    host = "127.0.0.1"  # localhost only for security
    port = 5000
    db_path = "dienstplan.db"
    
    # Check if database exists, if not inform user
    if not os.path.exists(db_path):
        print("ℹ️  No database found. A new database will be created.")
        print("   Sample data can be generated via the web interface or CLI.")
        print()
    
    # Start browser opener in background thread
    url = f"http://{host}:{port}"
    browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    browser_thread.start()
    
    # Import and start Flask app
    try:
        from web_api import create_app
        
        print(f"✓ Server will be available at: {url}")
        print()
        print("💡 Tip: Close this window or press Ctrl+C to stop the server")
        print("=" * 60)
        print()
        
        app = create_app(db_path)
        app.run(host=host, port=port, debug=False)
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down server...")
        print("Thank you for using Dienstplan!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    main()
