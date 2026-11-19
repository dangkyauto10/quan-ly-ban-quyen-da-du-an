import uuid
import pytest
from cryptography.fernet import Fernet
from license_app.web_config import load_web_settings,ConfigurationError
from license_app.packing import PackingLedger
from license_app.core import DomainError

def config():
    return {'app':{'database_url':'postgresql+psycopg://u:p@db.example.test/bq?sslmode=require',
        'encryption_key':Fernet.generate_key().decode(),'fingerprint_key':'f'*48,'admin_email':'VY@EXAMPLE.TEST'},
        'qr_signing_key':'q'*48,
        'auth':{'redirect_uri':'https://example.streamlit.app/oauth2callback','cookie_secret':'c'*48,
                'client_id':'id','client_secret':'secret','server_metadata_url':'https://accounts.google.com/.well-known/openid-configuration'}}

def test_secrets_config_and_secure_database():
    s=config();v=load_web_settings(s,environ={})
    assert v['BOOTSTRAP_ADMIN_EMAIL']=='vy@example.test'
    for bad in ['sqlite:///local.db','postgresql+psycopg://u:p@db/bq?sslmode=disable','postgresql+psycopg://u:p@db/bq']:
        s['app']['database_url']=bad
        with pytest.raises(ConfigurationError) as e:load_web_settings(s,environ={})
        assert ':p@' not in str(e.value)

def test_missing_invalid_secrets_fail_closed():
    with pytest.raises(ConfigurationError):load_web_settings({},environ={})
    for key in ['encryption_key','fingerprint_key','admin_email']:
        s=config();s['app'][key]='bad'
        with pytest.raises(ConfigurationError):load_web_settings(s,environ={})
    s=config();s['auth']['redirect_uri']='http://host/oauth2callback'
    with pytest.raises(ConfigurationError):load_web_settings(s,environ={})

def test_allowlist_disable_and_last_admin(tmp_path):
    l=PackingLedger('sqlite:///'+str(tmp_path/'users.db'),Fernet.generate_key().decode(),'f'*48)
    l.bootstrap('admin@example.test')
    l.add_user('admin@example.test','ktv@example.test','KTV','add')
    with pytest.raises(DomainError):l.update_user('ktv@example.test','ktv@example.test','ADMIN',True,'escalate')
    with pytest.raises(DomainError):l.update_user('admin@example.test','admin@example.test','KTV',True,'last')
    l.update_user('admin@example.test','ktv@example.test','KTV',False,'disable')
    with pytest.raises(DomainError):l.rows('ktv@example.test','jobs')
    l.update_user('admin@example.test','ktv@example.test','QC',True,'enable')
    assert l.role('ktv@example.test')=='QC'
    with pytest.raises(DomainError):l.rows('unknown@example.test','jobs')

def test_operator_cannot_redeem_or_reveal(tmp_path):
    l=PackingLedger('sqlite:///'+str(tmp_path/'redeem.db'),Fernet.generate_key().decode(),'f'*48)
    l.bootstrap('admin@example.test');l.add_user('admin@example.test','operator@example.test','OPERATOR','add')
    u=l.add_unit('admin@example.test','D','U','unit')
    a=l.add_account('admin@example.test',u,'office@example.test','Owner','account')
    l.import_keys('admin@example.test','B','Office','2024','Retail','ACCOUNT_REDEEM',['AAAAA-BBBBB-CCCCC-DDDDD-EEEEE'],'','import')
    lic=l.rows('admin@example.test','licenses')[0]['id']
    l.verify('admin@example.test',lic,'Verified','verify')
    with pytest.raises(DomainError):l.redeem('operator@example.test',lic,a,'Confirmed','bad-redeem')
    with pytest.raises(DomainError):l.reveal('operator@example.test',lic)
    l.redeem('admin@example.test',lic,a,'Confirmed','redeem')
