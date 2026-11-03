import io
import uuid
import pytest
import qrcode
from cryptography.fernet import Fernet
from license_app.preparation import PreparationLedger
from license_app.core import DomainError
from license_app.demo import seed_demo
from license_app.labels import label_token,compare_labels,decode_photo,print_html

@pytest.fixture
def setup_pc(tmp_path):
    l=PreparationLedger('sqlite:///'+str(tmp_path/'prep.db'),Fernet.generate_key().decode(),'f'*48)
    seed_demo(l)
    ds=l.preparation_rows('admin@example.test')
    d=next(r for r in ds if r['asset_tag']=='PC-MAU-01')
    l.set_plan('admin@example.test',d['unit_id'],2,str(uuid.uuid4()))
    l.number_device('admin@example.test',d['id'],str(uuid.uuid4()))
    return l,l.preparation_rows('admin@example.test')[0]

def test_plan_and_number_are_stable(setup_pc):
    l,d=setup_pc
    l.number_device('admin@example.test',d['id'],'number-again')
    assert l.preparation_rows('admin@example.test')[0]['number']==1
    with pytest.raises(DomainError):l.set_plan('ktv@example.test',d['unit_id'],10,'bad-role')

def test_label_matching_tamper_and_same_kind(setup_pc):
    _,d=setup_pc;k=b'x'*32
    a,b=label_token(d,'PC',k),label_token(d,'BOX',k)
    assert compare_labels(a,b,k)['id']==d['id']
    with pytest.raises(DomainError):compare_labels(a,a,k)
    with pytest.raises(DomainError):compare_labels(a,b[:-1]+'x',k)
    other=dict(d,id='other')
    with pytest.raises(DomainError):compare_labels(a,label_token(other,'BOX',k),k)
    assert 'THÂN MÁY' in print_html(d,k) and 'VỎ HỘP' in print_html(d,k)

def test_real_qr_image_decode(setup_pc):
    _,d=setup_pc;token=label_token(d,'PC',b'x'*32)
    out=io.BytesIO();qrcode.make(token).save(out,format='PNG')
    assert decode_photo(out.getvalue())==token

def test_inspection_gate_and_rework(setup_pc):
    l,d=setup_pc
    with pytest.raises(DomainError):l.close_package('qc@example.test',d['id'],'too-early')
    with pytest.raises(DomainError):l.inspect_device('ktv@example.test',d['id'],True,'OK',d['serial'],'bad-qc')
    with pytest.raises(DomainError):l.inspect_device('qc@example.test',d['id'],True,'OK','wrong','bad-serial')
    l.inspect_device('qc@example.test',d['id'],False,'Lỗi kỹ thuật',d['serial'],'fail')
    job=next(j for j in l.rows('admin@example.test','jobs') if j['device_id']==d['id'])
    assert job['state']=='PENDING'
    with pytest.raises(DomainError):l.close_package('qc@example.test',d['id'],'still-failed')
    l.report('ktv@example.test',job['id'],True,'','Đã sửa và kiểm tra','','rework')
    l.inspect_device('qc@example.test',d['id'],True,'Đã kiểm tra đạt',d['serial'],'pass')
    l.close_package('qc@example.test',d['id'],'pack')
    assert l.preparation_rows('qc@example.test')[0]['inspection_state']=='PACKED'
    l.warranty('admin@example.test',d['id'],'NEW-BOARD','Lỗi mainboard','replace')
    assert l.preparation_rows('qc@example.test')[0]['inspection_state'] is None
