import os
import subprocess
import sys

import streamlit as st

@st.cache_resource
def run_once():
    cache_dir = os.path.expanduser("~/.cache/ms-playwright")
    if not os.path.exists(cache_dir) or not os.listdir(cache_dir):
        print("Playwright browser cache empty. Installing Chromium binaries...")
        try:
            # Using sys.executable ensures it uses Streamlit's active virtual env Python
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"], check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Playwright install failed: {e}")
    return "Initialization complete"

status = run_once()

