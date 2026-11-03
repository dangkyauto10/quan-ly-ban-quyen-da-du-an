"""Persistent local multi-browser test configuration; never production credentials."""
import json
import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet

def shared_config():
    root=Path(os.getenv('LICENSE_TEST_DATA_DIR',str(Path(__file__).resolve().parent.parent/'test-data'))).resolve()
    root.mkdir(parents=True,exist_ok=True)
    config=root/'test-secrets.json'
    if not config.exists():
        value={'encryption':Fernet.generate_key().decode(),'fingerprint':secrets.token_urlsafe(48)}
        # Startup happens before serving browser sessions in the supplied launcher.
        try:
            with config.open('x',encoding='utf-8') as f:json.dump(value,f)
            config.chmod(0o600)
        except FileExistsError:pass
    value=json.loads(config.read_text(encoding='utf-8'))
    return ('sqlite:///'+(root/'test-ledger.db').as_posix(),value['encryption'],value['fingerprint'])
