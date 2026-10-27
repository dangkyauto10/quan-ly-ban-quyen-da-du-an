"""Admin-only, one-way safe report upserts. Manual research rows are never removed."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from .core import units, users, accounts, licenses, devices, jobs, audit, DomainError
from .guidance import ROLE_NAMES, ACTION_NAMES

SHEET_ID = '1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U'
HEADERS = json.loads(Path(__file__).with_name('sheet_schema.json').read_text())
SYNC_TAB = '15_DONG_BO_APP'
STATUS_HEADERS = ['Mã lần đồng bộ','Thời điểm','Loại dữ liệu','Nguồn dữ liệu','Số bản ghi nguồn','Kết quả','Ghi chú']

def ident(kind, value): return 'APP-' + kind + '-' + str(value)
def scrub(value):
    # Strings are sent as literal stringValue, never as formulas.
    return re.sub(r'(?i)\b(?:[a-z0-9]{5}-){4}([a-z0-9]{5})\b', r'…\1', str(value or ''))

def make_snapshot(ledger, actor, demo=False):
    # Read related tables from a single consistent database snapshot.
    with ledger.engine.connect() as c:
        if ledger.engine.dialect.name == 'postgresql':
            c = c.execution_options(isolation_level='REPEATABLE READ')
        with c.begin():
            if ledger.engine.dialect.name == 'sqlite': c.exec_driver_sql('BEGIN')
            ledger._auth(c, actor, {'ADMIN'})
            data = {}
            for name, tab in [('units',units),('users',users),('accounts',accounts),
                              ('licenses',licenses),('devices',devices),('jobs',jobs),('audit',audit)]:
                safe = [x for x in tab.c if x.name not in {'cipher','fingerprint'}]
                data[name] = [dict(r) for r in c.execute(select(*safe)).mappings()]
    out = {name: [] for name in HEADERS}
    marker = 'DỮ LIỆU GIẢ — từ app chạy thử' if demo else 'Từ ứng dụng quản lý bản quyền'
    def row(tab, **values): out[tab].append([scrub(values.get(h,'')) for h in HEADERS[tab]])
    def product_id(r):
        raw=json.dumps([r['product'],r['sku'],r['channel'],r['route']],ensure_ascii=False)
        return ident('SP',hashlib.sha256(raw.encode()).hexdigest()[:16])
    for r in data['units']:
        row('01_DU_AN_DON_VI', **{'Mã đơn vị':ident('DV',r['id']),'Mã dự án':r['project'],
            'Tên đơn vị':r['name'],'Trạng thái':'Đang dùng','Ghi chú':marker})
    for r in data['users']:
        row('02_NGUOI_DUNG', **{'Mã người dùng':ident('ND',r['email']),'Email đăng nhập':r['email'],
            'Tên hiển thị':r['email'],'Vai trò':ROLE_NAMES[r['role']].replace('Người quản lý redeem (quy đổi key)','Quản lý redeem (quy đổi key)'),
            'Phạm vi được giao':'Theo vai trò bản app thử','Trạng thái':'Đang dùng' if r['active'] else 'Tạm dừng','Ghi chú':marker})
    seen=set()
    for r in data['licenses']:
        sp=product_id(r)
        if sp not in seen:
            row('03_SAN_PHAM', **{'Mã sản phẩm':sp,'Nhóm phần mềm': 'Antivirus (diệt virus)' if r['product']=='Antivirus' else r['product'],
                'Tên phần mềm':r['product'],'Phiên bản và SKU':r['sku'],
                'Kênh cấp phép':{'Retail':'Retail (bán lẻ)','OEM':'OEM (đi kèm máy)','Volume':'Volume (số lượng lớn)','Vendor':'Theo nhà cung cấp'}[r['channel']],
                'Luồng dự kiến':'Redeem vào Microsoft' if r['route']=='ACCOUNT_REDEEM' else 'Theo nhà cung cấp',
                'Số máy được phép':1,'Căn cứ sử dụng và chuyển máy':'Bản thử quản lý 1 license/1 máy; xác minh theo SKU trước dùng thật','Ghi chú':marker})
            seen.add(sp)
        key_state='Đã redeem' if r['account_id'] else {'RECEIVED':'Mới nhận','VERIFIED':'Đã kiểm tra'}.get(r['state'],'Đã kiểm tra')
        batch=ident('LO',hashlib.sha256((r['batch']+sp).encode()).hexdigest()[:16])
        row('05_KHO_KEY', **{'Mã key':ident('KEY',r['id']),'Mã lô':batch,'Mã sản phẩm':sp,
            'Key đã che':'…'+r['tail'],'Trạng thái key':key_state,'Căn cứ kiểm tra':r['reference'],'Ghi chú':marker})
    grouped={}
    for r in data['licenses']:
        key=(r['batch'],product_id(r));grouped[key]=grouped.get(key,0)+1
    for (batch,sp),qty in grouped.items():
        row('04_LO_BAN_GIAO', **{'Mã lô':ident('LO',hashlib.sha256((batch+sp).encode()).hexdigest()[:16]),
            'Mã sản phẩm':sp,'Số key bàn giao':qty,'Trạng thái đối chiếu':'Chưa đối chiếu',
            'Ghi chú':marker+'; mã lô app: '+batch+'; số lượng là key đang lưu, chưa thay biên nhận công ty'})
    for r in data['accounts']:
        row('06_TK_MICROSOFT', **{'Mã tài khoản':ident('TK',r['id']),'Mã đơn vị':ident('DV',r['unit_id']),
            'Email Microsoft':r['email'],'Người sở hữu/quản lý':r['owner'],'Tình trạng xác thực':'Chưa xác minh',
            'MFA (xác thực nhiều bước)':'Chưa xác minh','Trạng thái tài khoản':'Chờ xác minh','Ghi chú':marker})
    for r in data['devices']:
        row('08_THIET_BI', **{'Mã máy':ident('MAY',r['id']),'Mã đơn vị':ident('DV',r['unit_id']),
            'Mã tem tài sản':r['asset_tag'],'Hãng / model':r['model'],'Serial máy':r['serial'],
            'Serial mainboard hiện tại':r['board_serial'],'Nguồn lấy serial':'',
            'Trạng thái thiết bị':'','Ghi chú':marker+'; app chưa lưu nguồn serial/trạng thái thiết bị riêng'})
    by_lic={r['id']:r for r in data['licenses']}
    by_job={r['id']:r for r in data['jobs']}
    for r in data['jobs']:
        lic=by_lic[r['license_id']]
        row('09_PHAN_BO', **{'Mã phân bổ':ident('PB',r['id']),
            'Mã license':ident('LIC',lic['id']) if lic['account_id'] else '',
            'Mã key':ident('KEY',lic['id']),'Mã máy':ident('MAY',r['device_id']),
            'KTV được giao':ident('ND',r['ktv']),
            'Trạng thái phân bổ':{'SUCCESS':'Đã hoàn thành','FAILED':'Chờ xử lý','WARRANTY_REVIEW':'Chờ xử lý'}.get(r['state'],'Đang giao'),
            'Ghi chú':marker})
    for r in data['audit']:
        details=json.loads(r['details'])
        day=r['at'][:10]
        if r['action']=='REDEEM_CONFIRMED':
            lic=by_lic[r['entity']]
            row('07_REDEEM_LICENSE', **{'Mã lần redeem':ident('RD',r['id']),'Mã key':ident('KEY',lic['id']),
                'Mã tài khoản':ident('TK',details['account_id']),'Ngày thao tác':day,'Người thao tác':ident('ND',r['actor']),
                'Kết quả redeem':'Thành công','Mã license':ident('LIC',lic['id']),
                'Sản phẩm Microsoft xác nhận':lic['sku'],'Mã lỗi / tham chiếu':details.get('reference',''),'Ghi chú':marker+'; kết quả do người thao tác xác nhận'})
        elif r['action'] in {'ACTIVATION_SUCCESS','ACTIVATION_FAILED'}:
            job=by_job[r['entity']]
            row('10_KICH_HOAT', **{'Mã báo cáo':ident('BC',r['id']),'Mã phân bổ':ident('PB',job['id']),
                'Mã máy':ident('MAY',job['device_id']),'Người báo cáo':ident('ND',r['actor']),'Ngày báo cáo':day,
                'Kết quả kích hoạt':'Thành công' if r['action']=='ACTIVATION_SUCCESS' else 'Thất bại',
                'Mã lỗi':details.get('error_code',''),'Cách xác minh / nội dung lỗi':details.get('note',''),
                'Ghi chú':marker+'; link minh chứng không đưa vào bản đồng bộ này'})
        elif r['action']=='BOARD_REPLACED':
            row('11_BAO_HANH', **{'Mã hồ sơ':ident('BH',r['id']),'Mã máy':ident('MAY',r['entity']),
                'Ngày tiếp nhận':day,'Nội dung yêu cầu':details.get('reason',''),
                'Serial mainboard cũ':details.get('old_board',''),'Serial mainboard mới':details.get('new_board',''),
                'Trạng thái hồ sơ':'Chờ xác minh','Ghi chú':marker+'; trạng thái tại lúc ghi sự kiện thay mainboard'})
        row('12_NHAT_KY', **{'Mã sự kiện':ident('NK',r['id']),'Thời điểm':r['at'],
            'Người thao tác':ident('ND',r['actor']),'Loại thao tác':ACTION_NAMES.get(r['action'],r['action']),
            'Mã hồ sơ liên quan':r['entity'],'Sau thay đổi':r['action'],'Ghi chú':marker})
    # Human-entered free text is scrubbed too; raw key bytes/cipher/password fields never enter snapshot.
    return {'created_at':datetime.now(timezone.utc).isoformat(),'demo':demo,'tables':out}

def plan_sync(snapshot, properties, live_values, tables):
    """Upsert APP- rows only. Keep human/template rows and all guide/feedback tabs."""
    props={r['title']:r for r in properties}
    requests=[]
    for name, rows in snapshot['tables'].items():
        if name not in HEADERS or name not in props: raise DomainError('Thiếu tab đồng bộ: '+name)
        headers=HEADERS[name]; current=live_values.get(name,[])
        if not current or current[0] != headers: raise DomainError('Cột đã thay đổi tại '+name+'; cần đối chiếu trước khi ghi.')
        seen={}
        for idx,row in enumerate(current[1:],1):
            key=str(row[0]) if row else ''
            if key and key in seen: raise DomainError('Mã trùng tại '+name)
            if key: seen[key]=idx
        ids=set(); next_row=max(len(current),1)
        for row in rows:
            if len(row)!=len(headers) or not str(row[0]).startswith('APP-') or row[0] in ids:
                raise DomainError('Dữ liệu xuất không hợp lệ tại '+name)
            ids.add(row[0]); idx=seen.get(row[0])
            if idx is None:idx=next_row;next_row+=1
            sheet_id=props[name]['sheetId']
            requests.append({'updateCells':{'range':{'sheetId':sheet_id,'startRowIndex':idx,'endRowIndex':idx+1,
                'startColumnIndex':0,'endColumnIndex':len(headers)},'rows':[{'values':[
                {'userEnteredValue':{'stringValue':str(value)}} for value in row]}],'fields':'userEnteredValue'}})
            requests.append({'repeatCell':{'range':{'sheetId':sheet_id,'startRowIndex':idx,'endRowIndex':idx+1,
                'startColumnIndex':0,'endColumnIndex':len(headers)},'cell':{'userEnteredFormat':{
                'textFormat':{'fontFamily':'Arial','fontSize':11,'bold':False},'wrapStrategy':'WRAP','verticalAlignment':'TOP'}},
                'fields':'userEnteredFormat(textFormat,wrapStrategy,verticalAlignment)'}})
            requests.append({'updateDimensionProperties':{'range':{'sheetId':sheet_id,'dimension':'ROWS',
                'startIndex':idx,'endIndex':idx+1},'properties':{'pixelSize':90},'fields':'pixelSize'}})
        if next_row>props[name]['gridProperties']['rowCount']:
            requests.insert(0,{'appendDimension':{'sheetId':props[name]['sheetId'],'dimension':'ROWS',
                'length':next_row-props[name]['gridProperties']['rowCount']}})
        for table in tables.get(name,[]):
            if table['range'].get('startRowIndex',0)==0 and table['range'].get('endColumnIndex')==len(headers):
                rng=dict(table['range']);rng['endRowIndex']=max(next_row,rng['endRowIndex'])
                requests.append({'updateTable':{'table':{'tableId':table['tableId'],'range':rng},'fields':'range'}})
    return requests

def sync_with_service(service, spreadsheet_id, snapshot):
    api=service.spreadsheets()
    book=api.get(spreadsheetId=spreadsheet_id,fields='spreadsheetId,sheets(properties,tables)').execute()
    props=[s['properties'] for s in book['sheets']]
    tables={s['properties']['title']:s.get('tables',[]) for s in book['sheets']}
    ranges=["'"+n+"'!A1:"+chr(64+len(h))+str(next(p for p in props if p['title']==n)['gridProperties']['rowCount']) for n,h in HEADERS.items()]
    values=api.values().batchGet(spreadsheetId=spreadsheet_id,ranges=ranges,valueRenderOption='UNFORMATTED_VALUE').execute()['valueRanges']
    live={n:v.get('values',[]) for n,v in zip(HEADERS,values)}
    requests=plan_sync(snapshot,props,live,tables)
    status=next((p for p in props if p['title']==SYNC_TAB),None)
    if status:
        header=api.values().get(spreadsheetId=spreadsheet_id,range="'"+SYNC_TAB+"'!A1:G1").execute().get('values',[])
        if header != [STATUS_HEADERS]: raise DomainError('Cột nhật ký đồng bộ đã thay đổi.')
        status_id=status['sheetId']
    else:
        status_id=max(p['sheetId'] for p in props)+1
        requests.append({'addSheet':{'properties':{'sheetId':status_id,'title':SYNC_TAB,'gridProperties':{'rowCount':1000,'columnCount':7,'frozenRowCount':1}}}})
        requests.append({'updateCells':{'start':{'sheetId':status_id,'rowIndex':0,'columnIndex':0},
            'rows':[{'values':[{'userEnteredValue':{'stringValue':x}} for x in STATUS_HEADERS]}],'fields':'userEnteredValue'}})
    requests.append(status_request(snapshot,status_id))
    api.batchUpdate(spreadsheetId=spreadsheet_id,body={'requests':requests}).execute()
    return sum(len(r) for r in snapshot['tables'].values())

def status_request(snapshot, sheet_id):
    count=sum(len(r) for r in snapshot['tables'].values())
    values=['SYNC-'+snapshot['created_at'],snapshot['created_at'],
        'MINH_HỌA' if snapshot['demo'] else 'THỰC_TẾ', 'V2-20261027-C',str(count),'Đã ghi từ app',
        'Một chiều app → Sheet. Các dòng APP- thuộc app; giữ dòng mẫu và góp ý của V.']
    return {'appendCells':{'sheetId':sheet_id,'rows':[{'values':[{'userEnteredValue':{'stringValue':x},
        'userEnteredFormat':{'wrapStrategy':'WRAP','textFormat':{'fontFamily':'Arial','fontSize':11,'bold':False}}}
        for x in values]}],'fields':'userEnteredValue,userEnteredFormat'}}
