"""Isolated trial: publish masked active keys to the copied workbook only."""
from threading import RLock

TEST_SHEET_ID = '1_DqhFZYEkha5qEYO3pBrRYrn8MYf_9tGbhJrl_XYKww'
TAB = '19_KEY_DA_KICH_HOAT'
TAB_ID = 1900261126
HEADERS = ['Tên PC (Serial mainboard)', 'Key Office', 'Key Windows', 'Key Antivirus', 'Mã PC nội bộ (APP)']
LOCK = RLock()
PRODUCTS = {'Office': 1, 'Windows': 2, 'Antivirus': 3}


def report_rows(records):
    pcs = {}
    serial_owners = {}
    seen = set()
    for r in records:
        if r['job_state'] != 'SUCCESS' or r['license_state'] != 'ACTIVATED':
            continue
        column = PRODUCTS.get(r['product'])
        if column is None:
            continue
        pc_id = str(r['device_id'])
        serial = str(r['board_serial'] or '').strip().upper()
        tail = str(r['tail'] or '')
        if not serial or not 1 <= len(tail) <= 5:
            raise ValueError('Invalid serial or masked key')
        if serial_owners.setdefault(serial, pc_id) != pc_id:
            raise ValueError('Duplicate mainboard serial')
        pc = pcs.setdefault(pc_id, [serial, [], [], [], pc_id])
        if pc[0] != serial:
            raise ValueError('Inconsistent mainboard serial')
        identity = (pc_id, str(r['license_id']))
        if identity in seen:
            continue
        seen.add(identity)
        pc[column].append('…' + tail)
    return [[pc[0], *['; '.join(sorted(v)) for v in pc[1:4]], pc[4]]
            for pc in sorted(pcs.values(), key=lambda p: (p[0], p[4]))]


def read_records(ledger, actor):
    from sqlalchemy import select
    from .core import devices, jobs, licenses
    with ledger.engine.connect() as c:
        ledger._auth(c, actor, {'ADMIN', 'KTV'})
        stmt = select(devices.c.id.label('device_id'), devices.c.board_serial,
                      licenses.c.id.label('license_id'), licenses.c.product, licenses.c.tail,
                      jobs.c.state.label('job_state'), licenses.c.state.label('license_state')).select_from(
            devices.join(jobs, jobs.c.device_id == devices.c.id).join(licenses, jobs.c.license_id == licenses.c.id)
        ).where(jobs.c.state == 'SUCCESS', licenses.c.state == 'ACTIVATED')
        return [dict(r) for r in c.execute(stmt).mappings()]


def plan_requests(rows, grid_rows):
    if grid_rows < 2 or any(len(row) != 5 for row in rows):
        raise ValueError('Invalid report grid')
    required = max(grid_rows, len(rows) + 1)
    requests = []
    if required > grid_rows:
        requests.append({'appendDimension': {'sheetId': TAB_ID, 'dimension': 'ROWS', 'length': required - grid_rows}})
        requests.append({'setBasicFilter': {'filter': {'range': {'sheetId': TAB_ID, 'startRowIndex': 0,
                         'endRowIndex': required, 'startColumnIndex': 0, 'endColumnIndex': 4}}}})
    # Only the dedicated generated report tab is cleared. Header and all other tabs stay intact.
    requests.append({'repeatCell': {'range': {'sheetId': TAB_ID, 'startRowIndex': 1, 'endRowIndex': required,
                     'startColumnIndex': 0, 'endColumnIndex': 5}, 'cell': {}, 'fields': 'userEnteredValue'}})
    if rows:
        requests.append({'updateCells': {'range': {'sheetId': TAB_ID, 'startRowIndex': 1,
                         'endRowIndex': len(rows) + 1, 'startColumnIndex': 0, 'endColumnIndex': 5},
                         'rows': [{'values': [{'userEnteredValue': {'stringValue': str(value)}} for value in row]}
                                  for row in rows], 'fields': 'userEnteredValue'}})
    return requests


def sync_with_service(service, rows):
    api = service.spreadsheets()
    meta = api.get(spreadsheetId=TEST_SHEET_ID, fields='spreadsheetId,sheets(properties)').execute(num_retries=0)
    props = next((s['properties'] for s in meta['sheets'] if s['properties']['sheetId'] == TAB_ID), None)
    if meta['spreadsheetId'] != TEST_SHEET_ID or not props or props['title'] != TAB:
        raise ValueError('Wrong report destination')
    grid = props['gridProperties']
    if grid['columnCount'] != 5:
        raise ValueError('Wrong report grid')
    header = api.values().get(spreadsheetId=TEST_SHEET_ID, range=TAB+'!A1:E1').execute(num_retries=0)
    if header.get('values') != [HEADERS]:
        raise ValueError('Wrong report header')
    api.batchUpdate(spreadsheetId=TEST_SHEET_ID, body={'requests': plan_requests(rows, grid['rowCount'])}).execute(num_retries=0)
    return len(rows)


def publish_test(ledger, actor, settings, *, demo):
    # This branch cannot export a live database or write the original workbook.
    if not demo or settings.get('activated_key_sync_test_enabled') is not True:
        return None
    # Never attempt default credential discovery on Streamlit: fail fast if absent.
    if not settings.get('google_service_account'):
        return 'warning', 'APP đã lưu. Bản thử chưa có danh tính Google Sheets.'
    service = None
    try:
        with LOCK:
            rows = report_rows(read_records(ledger, actor))
            from .sheet_sync import build_sheets_service
            service = build_sheets_service(settings)
            count = sync_with_service(service, rows)
        return 'success', f'Đã cập nhật bản Sheet thử nghiệm: {count} PC.'
    except Exception:
        return 'warning', 'APP đã lưu. Chưa đồng bộ được Sheet thử nghiệm; không cần kích hoạt lại.'
    finally:
        if service is not None:
            try:
                service.close()
            except Exception:
                pass
