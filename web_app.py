"""Web sign-in entry point. Never seeds fake identities or local test data."""
import os
import runpy
from pathlib import Path
os.environ['APP_MODE']='production'
runpy.run_path(str(Path(__file__).with_name('v2_app.py')),run_name='__main__')
