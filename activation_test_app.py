"""Shared, fake-data-only activation exercise entry point."""
import os
import runpy
from pathlib import Path

os.environ['APP_MODE'] = 'activation_demo'
runpy.run_path(str(Path(__file__).with_name('v2_app.py')), run_name='__main__')
