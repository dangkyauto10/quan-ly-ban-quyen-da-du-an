"""Read deploy-time settings without ever returning credential values in errors."""
import os
import re
from cryptography.fernet import Fernet
from sqlalchemy.engine import make_url

class ConfigurationError(ValueError):
    def __init__(self,fields):
        self.fields=fields
        super().__init__('Cần cấu hình: '+', '.join(fields))

def load_web_settings(source=None,environ=None):
    source=source or {};environ=os.environ if environ is None else environ
    app=source.get('app',{})
    names={'DATABASE_URL':'database_url','LICENSE_ENCRYPTION_KEY':'encryption_key',
        'FINGERPRINT_KEY':'fingerprint_key','BOOTSTRAP_ADMIN_EMAIL':'admin_email'}
    values={name:environ.get(name) or app.get(field,'') for name,field in names.items()}
    invalid=[]
    try:
        url=make_url(values['DATABASE_URL'])
        if url.drivername!='postgresql+psycopg' or not url.username or not url.database:
            raise ValueError()
        # Managed external PostgreSQL must use TLS. Cloud SQL socket uses its secured connector.
        if not str(url.query.get('host','')).startswith('/cloudsql/'):
            if not url.host or url.query.get('sslmode') not in {'require','verify-ca','verify-full'}:raise ValueError()
    except Exception:invalid.append('app.database_url (PostgreSQL dùng chung, kết nối bảo mật)')
    try:Fernet(values['LICENSE_ENCRYPTION_KEY'].encode())
    except Exception:invalid.append('app.encryption_key')
    if len(values['FINGERPRINT_KEY'])<32:invalid.append('app.fingerprint_key')
    values['BOOTSTRAP_ADMIN_EMAIL']=values['BOOTSTRAP_ADMIN_EMAIL'].strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',values['BOOTSTRAP_ADMIN_EMAIL']):invalid.append('app.admin_email')
    qr=environ.get('QR_SIGNING_KEY') or source.get('qr_signing_key','')
    if len(qr)<32:invalid.append('qr_signing_key')
    auth=source.get('auth',{})
    for field in ['redirect_uri','cookie_secret','client_id','client_secret','server_metadata_url']:
        if not auth.get(field):invalid.append('auth.'+field)
    if auth.get('redirect_uri') and not re.fullmatch(r'https://[^/]+/oauth2callback',auth['redirect_uri']):invalid.append('auth.redirect_uri (HTTPS)')
    if auth.get('cookie_secret') and len(auth['cookie_secret'])<32:invalid.append('auth.cookie_secret (ít nhất 32 ký tự)')
    if auth.get('server_metadata_url') and auth['server_metadata_url']!='https://accounts.google.com/.well-known/openid-configuration':invalid.append('auth.server_metadata_url (Google)')
    if invalid:raise ConfigurationError(invalid)
    values['QR_SIGNING_KEY']=qr
    return values
