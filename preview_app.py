"""Hosted preview; enable authenticated web only through admin-held secrets."""
import os
import runpy
from pathlib import Path
import streamlit as st
try:
    enabled=st.secrets.get('web_login_enabled',False) is True
except FileNotFoundError:
    enabled=False
# Incomplete web settings stop with a configuration message, never fall back to fake roles.
os.environ['APP_MODE']='production' if enabled else 'team_test'
runpy.run_path(str(Path(__file__).with_name('v2_app.py')),run_name='__main__')
