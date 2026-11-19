import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from license_app.core import Ledger, DomainError, licenses

def op():return str(uuid.uuid4())
@pytest.fixture
def setup(tmp_path):
    l=Ledger(f'sqlite:///{tmp_path}/ledger.db',Fernet.generate_key().decode(),'a'*48)
    l.bootstrap('admin@test.example')
    for email,role in [('vy@test.example','OPERATOR'),('ktv@test.example','KTV'),('other@test.example','KTV')]:l.add_user('admin@test.example',email,role,op())
    u=l.add_unit('admin@test.example','DA1','Unit A',op(),project_name='Project A')
    a=l.add_account('vy@test.example',u,'office@test.example','Owner',op())
    d=l.add_device('admin@test.example',u,'PC1','SN1','BOARD1','Model',op())
    return l,u,a,d

def ready(s):
    l,_,a,_=s
    l.import_keys('admin@test.example','B1','Office','Home Business 2024','Retail','ACCOUNT_REDEEM',['AAAAA-BBBBB-CCCCC-DDDDD-EEEEE'],'',op())
    entity=l.rows('admin@test.example','licenses')[0]['id']
    l.verify('vy@test.example',entity,'Verified document and license terms',op())
    l.redeem('admin@test.example',entity,a,'Confirmed at Microsoft',op())
    l.assign_account_to_ktv('admin@test.example',a,'ktv@test.example',op())
    return entity

def test_complete_flow_and_warranty(setup):
    l,_,_,d=setup;entity=ready(setup)
    job=l.assign('admin@test.example',entity,d,'ktv@test.example',op())
    l.report('ktv@test.example',job,False,'E001','Failure details','',op())
    l.report('ktv@test.example',job,True,'','Activated in Office account view','',op())
    l.warranty('admin@test.example',d,'BOARD2','Mainboard failed',op())
    assert l.rows('admin@test.example','licenses')[0]['state']=='WARRANTY_REVIEW'
    assert any('BOARD1' in x['details'] and 'BOARD2' in x['details'] for x in l.rows('admin@test.example','audit'))
    l.approve_reactivation('admin@test.example',job,'Supplier approved replacement',op())
    l.report('ktv@test.example',job,True,'','Reactivated','',op())
    assert l.rows('admin@test.example','licenses')[0]['state']=='ACTIVATED'

def test_duplicate_import_rolls_back(setup):
    l=setup[0];key='AAAAA-BBBBB-CCCCC-DDDDD-EEEEE'
    with pytest.raises(DomainError):l.import_keys('admin@test.example','B1','Office','2024','Retail','DIRECT',[key,key],'',op())
    assert not l.rows('admin@test.example','licenses')

def test_permissions_and_encryption(setup):
    l,_,_,d=setup;entity=ready(setup)
    with pytest.raises(DomainError):l.reveal('ktv@test.example',entity)
    with pytest.raises(DomainError):l.rows('ktv@test.example','licenses')
    with pytest.raises(DomainError):l.assign('vy@test.example',entity,d,'ktv@test.example',op())
    job=l.assign('admin@test.example',entity,d,'ktv@test.example',op())
    assert not l.rows('other@test.example','jobs')
    with pytest.raises(DomainError):l.report('other@test.example',job,True,'','Fake report','',op())
    with l.engine.connect() as c:assert 'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE' not in c.execute(select(licenses.c.cipher)).scalar_one()
    public=l.rows('admin@test.example','licenses')[0]
    assert 'cipher' not in public and 'fingerprint' not in public
    assert l.rows('ktv@test.example','jobs')[0]['account']=='office@test.example'

def test_idempotency(setup):
    l,_,_,d=setup;entity=ready(setup);token=op()
    job=l.assign('admin@test.example',entity,d,'ktv@test.example',token)
    assert l.assign('admin@test.example',entity,d,'ktv@test.example',token)==job
    assert len(l.rows('admin@test.example','jobs'))==1
    with pytest.raises(DomainError):l.assign('admin@test.example',entity,d,'ktv@test.example',op())

def test_concurrent_assignment(setup):
    l,_,_,d=setup;entity=ready(setup)
    def attempt(_):
        try:l.assign('admin@test.example',entity,d,'ktv@test.example',op());return True
        except DomainError:return False
    with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(attempt,range(2)))
    assert sum(result)==1
    assert len(l.rows('admin@test.example','jobs'))==1

def test_wrong_unit_and_invalid_state(setup):
    l,_,a,_=setup;entity=ready(setup)
    u=l.add_unit('admin@test.example','DA2','Unit B',op())
    d=l.add_device('admin@test.example',u,'PC2','SN2','BOARD2','Model',op())
    with pytest.raises(DomainError):l.assign('admin@test.example',entity,d,'ktv@test.example',op())
    with pytest.raises(DomainError):l.redeem('admin@test.example',entity,a,'Again',op())

def test_unit_keeps_project_name_separate(setup):
    l,_,_,_=setup
    unit=l.rows('admin@test.example','units')[0]
    assert unit['project']=='DA1'
    assert unit['project_name']=='Project A'
    assert unit['name']=='Unit A'

def test_existing_ledger_migrates_project_name_column(tmp_path):
    url=f'sqlite:///{tmp_path}/legacy.db'
    engine=create_engine(url)
    with engine.begin() as c:
        c.exec_driver_sql('CREATE TABLE units (id VARCHAR PRIMARY KEY, project VARCHAR NOT NULL, name VARCHAR NOT NULL)')
        c.exec_driver_sql("INSERT INTO units (id, project, name) VALUES ('old-1', 'OLD-CODE', 'Old unit')")
    l=Ledger(url,Fernet.generate_key().decode(),'a'*48)
    l.bootstrap('admin@test.example')
    old=next(r for r in l.rows('admin@test.example','units') if r['id']=='old-1')
    assert old['project_name']==''
    new=l.add_unit('admin@test.example','NEW-CODE','New unit',op(),project_name='New project')
    created=next(r for r in l.rows('admin@test.example','units') if r['id']==new)
    assert created['project_name']=='New project'

def test_demo_ui(monkeypatch):
    monkeypatch.setenv('APP_MODE','demo')
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'v2_app.py')).run(timeout=20)
    assert not app.exception
    assert app.subheader[0].value=='Tổng quan'
    def navigate(page):
        for group in app.selectbox(key='nav-section').options:
            app.selectbox(key='nav-section').set_value(group).run()
            if page in app.sidebar.radio[0].options:
                app.sidebar.radio[0].set_value(page).run()
                return
        raise AssertionError('Missing navigation: '+page)
    for page in ['Đơn vị & tài khoản','Kho key','Redeem Office','Thiết bị','Phân bổ','Kích hoạt','Bảo hành','Nhật ký','Người dùng','Hướng dẫn theo vai trò','Đồng bộ Google Sheet']:
        navigate(page)
        assert not app.exception
    app.sidebar.selectbox[0].set_value('ktv@example.test').run()
    assert not app.exception
    assert app.subheader[0].value=='Việc của tôi'
    navigate('Hướng dẫn theo vai trò')
    assert not app.exception
    app.sidebar.selectbox[0].set_value('ktv2@example.test').run()
    navigate('Việc của tôi')
    assert not app.exception and not app.dataframe

def test_demo_seed_preserves_user_reports(tmp_path):
    from license_app.demo import seed_demo
    l=Ledger(f'sqlite:///{tmp_path}/demo.db',Fernet.generate_key().decode(),'a'*48)
    seed_demo(l)
    assert len(l.rows('admin@example.test','licenses'))==3
    jobs=l.rows('ktv@example.test','jobs')
    assert {r['state'] for r in jobs}=={'SUCCESS','FAILED'}
    assert len({r['account'] for r in jobs})==1
    failed=next(r for r in jobs if r['state']=='FAILED')
    l.report('ktv@example.test',failed['id'],True,'','Đã xử lý minh họa','',op())
    seed_demo(l)
    assert len(l.rows('admin@example.test','licenses'))==3
    assert all(r['state']=='SUCCESS' for r in l.rows('ktv@example.test','jobs'))

def test_vietnamese_labels_preserve_source():
    from license_app.guidance import display_record
    source={'role':'KTV','route':'ACCOUNT_REDEEM','state':'REDEEMED'}
    result=display_record(source,{'REDEEMED':'Đã redeem'})
    assert result['Vai trò']=='KTV (kỹ thuật viên)'
    assert result['Cách xử lý']=='Redeem vào tài khoản Microsoft'
    assert source['state']=='REDEEMED'



def test_bulk_account_import_and_assignment(setup):
    l,_,_,_=setup
    rows=[{'project':'DA1','project_name':'Project A','unit_name':'Unit A',
        'email':'bulk-office@test.example','owner':'Owner A'}]
    assert l.import_accounts('admin@test.example',rows,op())=={'added':1,'unchanged':0}
    assert l.import_accounts('admin@test.example',rows,op())=={'added':0,'unchanged':1}
    account=next(r for r in l.rows('admin@test.example','accounts') if r['email']=='bulk-office@test.example')
    l.assign_account_to_ktv('admin@test.example',account['id'],'ktv@test.example',op())
    assert next(r for r in l.account_assignment_rows('admin@test.example') if r['id']==account['id'])['ktv']=='ktv@test.example'
    with pytest.raises(DomainError):l.assign_account_to_ktv('admin@test.example',account['id'],'other@test.example',op())
