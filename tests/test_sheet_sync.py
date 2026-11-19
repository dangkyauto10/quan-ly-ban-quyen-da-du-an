import copy
import json
import pytest
from cryptography.fernet import Fernet
from license_app.core import Ledger, DomainError
from license_app.demo import seed_demo
from license_app.sheet_sync import (make_snapshot, plan_sync, HEADERS, scrub,
    SHEET_ID, SUPPLIER_TAB_GID, SUPPLIER_HEADERS, configured_spreadsheet_id, parse_supplier_receipts)

@pytest.fixture
def snapshot(tmp_path):
    l=Ledger(f'sqlite:///{tmp_path}/ledger.db',Fernet.generate_key().decode(),'a'*48)
    seed_demo(l)
    return l,make_snapshot(l,'admin@example.test',demo=True)

def fixture_live(s):
    props=[{'title':name,'sheetId':i,'gridProperties':{'rowCount':1000}} for i,name in enumerate(HEADERS,1)]
    live={n:[list(h), ['MAU-GIU-LAI']+['']*(len(h)-1)] for n,h in HEADERS.items()}
    return props,live

def test_snapshot_masks_and_links(snapshot):
    l,s=snapshot
    body=json.dumps(s,ensure_ascii=False)
    assert 'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE' not in body
    assert 'cipher' not in body and 'fingerprint' not in body
    assert len(s['tables']['05_KHO_KEY'])==3
    assert len(s['tables']['07_REDEEM_LICENSE'])==2
    assert len(s['tables']['10_KICH_HOAT'])==2
    accounts={r[0] for r in s['tables']['06_TK_MICROSOFT']}
    assert all(r[2] in accounts for r in s['tables']['07_REDEEM_LICENSE'])
    with pytest.raises(DomainError):make_snapshot(l,'ktv@example.test')

def test_plan_keeps_manual_rows_and_does_not_delete(snapshot):
    _,s=snapshot;props,live=fixture_live(s);before=copy.deepcopy(live)
    requests=plan_sync(s,props,live,{})
    assert live==before
    writes=[r for r in requests if 'updateCells' in r]
    assert all(r['updateCells']['range']['startRowIndex']>=2 for r in writes)
    assert all(r['updateCells']['fields']=='userEnteredValue' for r in writes)
    # Simulate the first write, then a retry: same rows, no new copies.
    names={p['sheetId']:p['title'] for p in props}
    for req in writes:
        cell=req['updateCells'];name=names[cell['range']['sheetId']];idx=cell['range']['startRowIndex']
        live[name].append([v['userEnteredValue']['stringValue'] for v in cell['rows'][0]['values']])
    again=[r for r in plan_sync(s,props,live,{}) if 'updateCells' in r]
    assert [r['updateCells']['range'] for r in writes]==[r['updateCells']['range'] for r in again]

def test_header_change_blocks_all_writes(snapshot):
    _,s=snapshot;props,live=fixture_live(s)
    live['05_KHO_KEY'][0][0]='Đã đổi tên cột'
    with pytest.raises(DomainError):plan_sync(s,props,live,{})

def test_literal_export_and_key_scrub():
    assert scrub('key AAAAA-BBBBB-CCCCC-DDDDD-EEEEE')=='key …EEEEE'
    assert scrub('=IMPORTXML("x")')=='=IMPORTXML("x")' # Writer uses stringValue; never formulaValue.
def test_app_uses_only_the_approved_workbook_even_if_old_secret_remains():
    assert SHEET_ID == '1Qdftk3jOKZMSbRzX-JCtXm_AJv87CUcwYHu-0EpcyRM'
    assert SUPPLIER_TAB_GID == 906599733
    assert configured_spreadsheet_id({'google_sheets':{'spreadsheet_id':'1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U'}}) == SHEET_ID

def test_supplier_intake_keeps_mismatched_codes_pending_review():
    values=[SUPPLIER_HEADERS,[
        'TEST-FPT-001','FPT','','','','FPT ELEAD T12400i','i5-12400 / 8GB / 256GB',
        'f08100212-i5124','WT0508260303','f08100212-i5124','WT0508260307','CHỜ XÁC MINH'
    ]]
    rows=parse_supplier_receipts(values)
    assert rows[0]['Đối chiếu mã tự động']=='CÓ MÃ CHUNG; CÒN MÃ LỆCH — CHỜ XÁC MINH'
    assert rows[0]['Kết quả đối chiếu tem NCC']=='CHỜ XÁC MINH'

def test_supplier_intake_rejects_formula_and_duplicate_ids():
    row=['TEST-1','FPT','','','','','','A','B','A','C','']
    with pytest.raises(DomainError,match='công thức'):
        parse_supplier_receipts([SUPPLIER_HEADERS,['=IMPORTXML("x")']+row[1:]])
    with pytest.raises(DomainError,match='bị lặp'):
        parse_supplier_receipts([SUPPLIER_HEADERS,row,row])
