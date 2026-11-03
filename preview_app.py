"""Explicit, fake-data-only entry point for the hosted V2 review."""
import os
import runpy
from pathlib import Path

# This entry point never connects to the production ledger or writes to Sheets.
os.environ['APP_MODE'] = 'demo'
runpy.run_path(str(Path(__file__).with_name('v2_app.py')), run_name='__main__')
