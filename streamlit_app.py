"""Entry point for Streamlit Community Cloud: runs the real dashboard in app/dashboard.py."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "app" / "dashboard.py"), run_name="__main__")
