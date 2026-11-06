from concurrent.futures import ThreadPoolExecutor
import hashlib
import uuid
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import update,select
from license_app.packing import PackingLedger,claims
from license_app.preparation import inspections
from license_app.core import DomainError,audit
from license_app.demo import seed_demo
from license_app.labels import label_token

@pytest.fixture
def ready_pc(tmp_path):
    ledger=PackingLedger('sqlite:///'+str(tmp_path/'team.db'),Fernet.generate_key().decode(),'m'*48)
    seed_demo(ledger)
    d=next(r for r in ledger.preparation_rows('admin@example.test') if r['asset_tag']=='PC-MAU-01')
    ledger.set_plan('admin@example.test',d['unit_id'],2,'plan')
    ledger.number_device('admin@example.test',d['id'],'number')
    d=next(r for r in ledger.preparation_rows('admin@example.test') if r['id']==d['id'])
    batch=ledger.queue_label_batch('ktv@example.test',d['unit_id'],[d['id']],'test-queue')
    ledger.confirm_label_batch_printed('admin@example.test',batch,'test-print')
    ledger.confirm_label_batch_collected('ktv@example.test',batch,'test-collect')
    ledger.confirm_labels_applied('ktv@example.test',d['id'],d['board_serial'],'Đã dán đúng cặp tem và đóng hộp','test-close')
    d=next(r for r in ledger.preparation_rows('admin@example.test') if r['id']==d['id'])
    key=hashlib.sha256(ledger.fingerprint_key+b'paired-label-v1').digest()
    return ledger,d,key,label_token(d,'PC',key),label_token(d,'BOX',key)

def test_six_simultaneous_claims_have_one_winner(ready_pc):
    ledger,d,*_=ready_pc
    actors=['qc@example.test']+[f'qc{i}@example.test' for i in range(2,7)]
    def attempt(actor):
        try:ledger.claim_for_check(actor,d['id'],str(uuid.uuid4()));return actor
        except DomainError:return None
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(attempt,actors))
    winners=[r for r in results if r]
    assert len(winners)==1
    assert ledger.check_claims('admin@example.test')[d['id']]['owner']==winners[0]

def test_atomic_report_pair_validation_and_duplicate(ready_pc):
    ledger,d,key,a,b=ready_pc
    with pytest.raises(DomainError):ledger.submit_packing('qc@example.test',a,b,key,True,'Đạt',d['board_serial'],'without-claim')
    ledger.claim_for_check('qc@example.test',d['id'],'claim')
    with pytest.raises(DomainError):ledger.submit_packing('qc2@example.test',a,b,key,True,'Đạt',d['board_serial'],'wrong-owner')
    with pytest.raises(DomainError):ledger.submit_packing('qc@example.test',a,a,key,True,'Đạt',d['board_serial'],'same-kind')
    with pytest.raises(DomainError):ledger.submit_packing('qc@example.test',a,b,key,True,'Đạt','wrong','wrong-serial')
    ledger.submit_packing('qc@example.test',a,b,key,True,'Đạt',d['board_serial'],'submit')
    ledger.submit_packing('qc@example.test',a,b,key,True,'Đạt',d['board_serial'],'submit')
    with ledger.engine.connect() as c:
        packed=c.execute(select(inspections).where(inspections.c.id==d['id'])).mappings().one()
        events=c.execute(select(audit).where(audit.c.action=='PACK_PC',audit.c.entity==d['id'])).all()
    assert packed['state']=='PACKED' and packed['inspector']=='qc@example.test'
    assert len(events)==1
    with pytest.raises(DomainError):ledger.claim_for_check('qc2@example.test',d['id'],'claim-complete')

def test_expired_claim_can_be_taken_and_old_owner_rejected(ready_pc):
    ledger,d,key,a,b=ready_pc
    ledger.claim_for_check('qc@example.test',d['id'],'claim')
    with ledger.engine.begin() as c:c.execute(update(claims).where(claims.c.id==d['id']).values(until=0))
    ledger.claim_for_check('qc2@example.test',d['id'],'takeover')
    with pytest.raises(DomainError):ledger.submit_packing('qc@example.test',a,b,key,True,'Đạt',d['board_serial'],'expired')
    ledger.submit_packing('qc2@example.test',a,b,key,False,'Phát hiện lỗi',d['board_serial'],'fail')
    assert not ledger.check_claims('admin@example.test')
    assert next(r for r in ledger.rows('admin@example.test','jobs') if r['device_id']==d['id'])['state']=='PENDING'

def test_stale_label_after_plan_change_rejected(ready_pc):
    ledger,d,key,a,b=ready_pc
    ledger.claim_for_check('qc@example.test',d['id'],'claim')
    ledger.set_plan('admin@example.test',d['unit_id'],3,'new-plan')
    with pytest.raises(DomainError):ledger.submit_packing('qc@example.test',a,b,key,True,'Đạt',d['board_serial'],'stale')

