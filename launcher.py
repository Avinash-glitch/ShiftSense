import streamlit.web.cli as stcli
import sys
import os
import importlib.metadata

# Fix PyInstaller streamlit metadata bug
if getattr(sys, 'frozen', False):
    original_version = importlib.metadata.version

    def patched_version(package_name):
        if package_name == "streamlit":
            return "1.0.0"
        return original_version(package_name)

    importlib.metadata.version = patched_version


def main():

    if getattr(sys, "frozen", False):
        script_dir = sys._MEIPASS
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    script_path = os.path.join(script_dir, "task_rot_paste.py")
    print("Looking for Streamlit script at:", script_path)

    if not os.path.exists(script_path):
        print("ERROR: rota_maker.py not found!")
        input("Press Enter to exit...")
        sys.exit(1)

    # 🔥 FIX: disable Streamlit dev mode
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--server.headless=false",
        "--server.port=3000"
    ]

    stcli.main()


if __name__ == "__main__":
    main()
