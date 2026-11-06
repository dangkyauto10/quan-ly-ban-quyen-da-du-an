"""Admin-only, one-way report upserts. Non-app rows are never overwritten or removed."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from .core import units, receiving_points, users, accounts, licenses, devices, jobs, audit, DomainError, meta
from .guidance import ROLE_NAMES, ACTION_NAMES
from .preparation import inspections

SHEET_ID = '1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U'
PLAN_TAB = '16_KE_HOACH_CAP_PC'
PLAN_HEADERS = ['Mã dự án','Tên dự án','Tên đơn vị được cấp','Mã xã/điểm',
    'Tên xã/phường/đơn vị','Số PC tại điểm','Phần mềm','SKU','Số license được cấp']
ACCOUNT_TAB = '17_TAI_KHOAN_MS'
ACCOUNT_HEADERS = ['Mã dự án','Tên dự án','Tên đơn vị được cấp','Email tài khoản Microsoft','Người quản lý tài khoản']
HEADERS = json.loads(Path(__file__).with_name('sheet_schema.json').read_text())
SYNC_TAB = '15_DONG_BO_APP'
STATUS_HEADERS = ['Mã lần đồng bộ','Thời điểm','Loại dữ liệu','Nguồn dữ liệu','Số bản ghi nguồn','Kết quả','Ghi chú']

def configured_spreadsheet_id(settings):
    try:
        return settings.get('google_sheets',{}).get('spreadsheet_id',SHEET_ID)
    except Exception:
        # Streamlit raises when secrets.toml is absent (for example in AppTest/demo).
        return SHEET_ID

def build_sheets_service(settings):
    """Build the runtime Google Sheets client from the configured service identity."""
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    scopes=['https://www.googleapis.com/auth/spreadsheets']
    info=settings.get('google_service_account')
    if info:
        credentials=Credentials.from_service_account_info(dict(info),scopes=scopes)
    else:
        try:credentials=google.auth.default(scopes=scopes)[0]
        except DefaultCredentialsError:
            raise DomainError('Chưa cấu hình danh tính Google Sheets cho app. Thêm [google_service_account] trong Secrets và chia sẻ Sheet quyền Editor cho email service account.') from None
    return build('sheets','v4',credentials=credentials,cache_discovery=False)

def _sheet_integer(value,line,label,minimum):
    if isinstance(value,bool) or value is None or value=='':
        raise DomainError(f'Dòng {line}: {label} phải là số nguyên từ {minimum} trở lên.')
    try:
        number=float(value)
    except (TypeError,ValueError):
        raise DomainError(f'Dòng {line}: {label} phải là số nguyên từ {minimum} trở lên.') from None
    if not number.is_integer() or number<minimum:
        raise DomainError(f'Dòng {line}: {label} phải là số nguyên từ {minimum} trở lên.')
    return int(number)

def read_delivery_plan(service,spreadsheet_id):
    """Read the authoritative unit/point/SKU plan tab without reading any key material."""
    api=service.spreadsheets()
    book=api.get(spreadsheetId=spreadsheet_id,fields='sheets(properties(title))').execute()
    titles={sheet['properties']['title'] for sheet in book.get('sheets',[])}
    if PLAN_TAB not in titles:raise DomainError('Chưa có tab '+PLAN_TAB+' trong Google Sheet.')
    values=api.values().get(spreadsheetId=spreadsheet_id,
        range="'"+PLAN_TAB+"'!A1:I1000",valueRenderOption='FORMULA').execute().get('values',[])
    if not values or values[0][:len(PLAN_HEADERS)]!=PLAN_HEADERS:
        raise DomainError('Tiêu đề tab '+PLAN_TAB+' chưa đúng mẫu. Hãy kiểm tra lại các cột trước khi nạp.')
    records=[]
    for line,row in enumerate(values[1:],2):
        cells=list(row[:len(PLAN_HEADERS)])+['']*max(0,len(PLAN_HEADERS)-len(row))
        if not any(str(value).strip() for value in cells):continue
        if any(isinstance(value,str) and value.startswith('=') for value in cells):
            raise DomainError(f'Dòng {line}: không dùng công thức trong tab kế hoạch; nhập giá trị trực tiếp.')
        project,project_name,unit_name,point_code,point_name=[str(v).strip() for v in cells[:5]]
        pc_quantity=_sheet_integer(cells[5],line,'Số PC tại điểm',1)
        product,sku=str(cells[6]).strip(),str(cells[7]).strip()
        if bool(product)!=bool(sku):raise DomainError(f'Dòng {line}: cần điền đủ Phần mềm và SKU.')
        license_quantity=0
        if product:
            if product not in {'Windows','Office','Antivirus'}:
                raise DomainError(f'Dòng {line}: Phần mềm phải là Windows, Office hoặc Antivirus.')
            license_quantity=_sheet_integer(cells[8],line,'Số license được cấp',0)
            if license_quantity>pc_quantity:
                raise DomainError(f'Dòng {line}: số license của SKU không thể vượt số PC tại điểm.')
        elif str(cells[8]).strip():
            raise DomainError(f'Dòng {line}: để trống Số license nếu chưa điền Phần mềm và SKU.')
        records.append({'project':project,'project_name':project_name,'unit_name':unit_name,
            'point_code':point_code,'point_name':point_name,'pc_quantity':pc_quantity,
            'product':product,'sku':sku,'license_quantity':license_quantity})
    if not records:raise DomainError('Tab '+PLAN_TAB+' chưa có dòng kế hoạch để nạp.')
    return records

def read_account_roster(service,spreadsheet_id):
    """Read account ownership metadata only; passwords and MFA are never accepted."""
    api=service.spreadsheets()
    book=api.get(spreadsheetId=spreadsheet_id,fields='sheets(properties(title))').execute()
    titles={sheet['properties']['title'] for sheet in book.get('sheets',[])}
    if ACCOUNT_TAB not in titles:raise DomainError('Chưa có tab '+ACCOUNT_TAB+' trong Google Sheet.')
    values=api.values().get(spreadsheetId=spreadsheet_id,range="'"+ACCOUNT_TAB+"'!A1:E1000",
        valueRenderOption='FORMULA').execute().get('values',[])
    if not values or values[0][:len(ACCOUNT_HEADERS)]!=ACCOUNT_HEADERS:
        raise DomainError('Tiêu đề tab '+ACCOUNT_TAB+' chưa đúng mẫu.')
    records=[];seen=set()
    for line,row in enumerate(values[1:],2):
        cells=list(row[:len(ACCOUNT_HEADERS)])+['']*max(0,len(ACCOUNT_HEADERS)-len(row))
        if not any(str(value).strip() for value in cells):continue
        if any(isinstance(value,str) and value.startswith('=') for value in cells):
            raise DomainError(f'Dòng {line}: không dùng công thức trong tab tài khoản.')
        project,project_name,unit_name,email,owner=[str(v).strip() for v in cells]
        email=email.lower()
        if not project or not project_name or not unit_name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
            raise DomainError(f'Dòng {line}: cần đủ dự án, đơn vị được cấp và email Microsoft hợp lệ.')
        if email in seen:raise DomainError(f'Dòng {line}: email Microsoft bị lặp trong danh sách.')
        seen.add(email);records.append({'project':project,'project_name':project_name,'unit_name':unit_name,
            'email':email,'owner':owner or 'Chưa ghi người quản lý'})
    if not records:raise DomainError('Tab '+ACCOUNT_TAB+' chưa có dòng tài khoản để nạp.')
    return records

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
            for name, tab in [('units',units),('receiving_points',receiving_points),('users',users),('accounts',accounts),
                              ('licenses',licenses),('devices',devices),('jobs',jobs),('audit',audit),('inspections',inspections)]:
                safe = [x for x in tab.c if x.name not in {'cipher','fingerprint'}]
                data[name] = [dict(r) for r in c.execute(select(*safe)).mappings()]
            assignment_table=meta.tables.get('account_assignments')
            data['account_assignments']=[dict(r) for r in c.execute(select(*assignment_table.c)).mappings()] if assignment_table is not None else []
    out = {name: [] for name in HEADERS}
    marker = 'DỮ LIỆU GIẢ — từ app chạy thử' if demo else 'Từ ứng dụng quản lý bản quyền'
    def row(tab, **values): out[tab].append([scrub(values.get(h,'')) for h in HEADERS[tab]])
    def product_id(r):
        raw=json.dumps([r['product'],r['sku'],r['channel'],r['route']],ensure_ascii=False)
        return ident('SP',hashlib.sha256(raw.encode()).hexdigest()[:16])
    for r in data['units']:
        row('01_DU_AN_DON_VI', **{'Mã đơn vị':ident('DV',r['id']),'Mã dự án':r['project'],
            'Tên dự án':r.get('project_name') or r['project'],
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
    active_handoffs={r['account_id']:r for r in data['account_assignments'] if r.get('released_at') is None}
    for r in data['accounts']:
        handoff=active_handoffs.get(r['id'])
        row('06_TK_MICROSOFT', **{'Mã tài khoản':ident('TK',r['id']),'Mã đơn vị':ident('DV',r['unit_id']),
            'Email Microsoft':r['email'],'Người sở hữu/quản lý':r['owner'],'Tình trạng xác thực':'Chưa xác minh',
            'MFA (xác thực nhiều bước)':'Chưa xác minh','Trạng thái tài khoản':'Đang giao KTV' if handoff else 'Chờ xác minh',
            'Ghi chú':marker+('; KTV hiện được giao: '+str(handoff['ktv']) if handoff else '')})
    point_by_id={r['id']:r for r in data['receiving_points']}
    inspection_by_id={r['id']:r for r in data['inspections']}
    for r in data['devices']:
        point=point_by_id.get(r.get('point_id'))
        inspection=inspection_by_id.get(r['id'])
        inspection_state=(inspection or {}).get('state')
        device_state={'PACKED':'Đã QC và đóng gói','FAILED':'Không đạt — cần xử lý'}.get(inspection_state,'Chưa QC')
        row('08_THIET_BI', **{'Mã máy':ident('MAY',r['id']),'Mã đơn vị':ident('DV',r['unit_id']),
            'Mã tem tài sản':r['asset_tag'],'Hãng / model':r['model'],'Serial máy':r['serial'],
            'Serial mainboard hiện tại':r['board_serial'],'Nguồn lấy serial':'',
            'Trạng thái thiết bị':device_state,'Ghi chú':marker+'; app chưa lưu nguồn serial riêng',
            'Mã xã/điểm':point['code'] if point else '',
            'Tên xã/phường/đơn vị':point['name'] if point else ''})
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
            'Mã hồ sơ liên quan':r['entity'],'Sau thay đổi':r['action'],
            'Ghi chú':marker+'; chi tiết: '+scrub(json.dumps({k:v for k,v in details.items() if k in {'email','ktv','unit_id','asset_tag','board_serial','old_board','new_board','reason','batch_id','device_id','quantity','number','note','reference'}},ensure_ascii=False))})
    # Human-entered free text is scrubbed too; raw key bytes/cipher/password fields never enter snapshot.
    return {'created_at':datetime.now(timezone.utc).isoformat(),'demo':demo,'tables':out}

def plan_sync(snapshot, properties, live_values, tables):
    """Upsert APP- rows only. Keep human-entered rows and input tabs untouched."""
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
        'Một chiều app → Sheet. Các dòng APP- thuộc app; giữ nguyên dòng mẫu và dữ liệu nhập tay.']
    return {'appendCells':{'sheetId':sheet_id,'rows':[{'values':[{'userEnteredValue':{'stringValue':x},
        'userEnteredFormat':{'wrapStrategy':'WRAP','textFormat':{'fontFamily':'Arial','fontSize':11,'bold':False}}}
        for x in values]}],'fields':'userEnteredValue,userEnteredFormat'}}

