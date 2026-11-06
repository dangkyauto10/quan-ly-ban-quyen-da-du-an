"""Local, fake-data-only multi-user test entry point."""
import os
import runpy
from pathlib import Path
os.environ['APP_MODE']='shared_test'
runpy.run_path(str(Path(__file__).with_name('v2_app.py')),run_name='__main__')
