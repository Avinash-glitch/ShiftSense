import sys
import os
import importlib.metadata

# ⚠️ CRITICAL: Apply metadata patch BEFORE importing streamlit
if getattr(sys, 'frozen', False):
    original_version = importlib.metadata.version

    def patched_version(package_name):
        if package_name == "streamlit":
            return "1.0.0"
        return original_version(package_name)

    importlib.metadata.version = patched_version

# NOW it's safe to import streamlit
import streamlit.web.cli as stcli
import webbrowser
import time
from threading import Timer


def open_browser():
    """Open browser after a short delay"""
    time.sleep(3)
    webbrowser.open('http://localhost:3000')


def main():
    if getattr(sys, "frozen", False):
        script_dir = sys._MEIPASS
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    script_path = os.path.join(script_dir, "streamlit_new.py")
    print("=" * 60)
    print("🚀 Daily Assignment Generator")
    print("=" * 60)
    print("Looking for Streamlit script at:", script_path)

    if not os.path.exists(script_path):
        print("ERROR: streamlit_new.py not found!")
        input("Press Enter to exit...")
        sys.exit(1)

    # Disable Streamlit dev mode
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    # Launch browser in background thread
    Timer(3.0, open_browser).start()

    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--server.headless=true",
        "--server.port=3000",
        "--browser.gatherUsageStats=false"
    ]

    print("Starting Streamlit server...")
    stcli.main()


if __name__ == "__main__":
    main()
