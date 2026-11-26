"""Post-commit report sync. Never writes the ledger or exports raw key fields."""
from threading import RLock
from .core import DomainError
from .sheet_sync import make_snapshot, sync_with_service, build_sheets_service, configured_spreadsheet_id

KEY_TABS = ('01_DU_AN_DON_VI','02_NGUOI_DUNG','03_SAN_PHAM','04_LO_BAN_GIAO',
            '05_KHO_KEY','06_TK_MICROSOFT','07_REDEEM_LICENSE','12_NHAT_KY')
_LOCK = RLock()

def publish(ledger, actor, settings, *, demo=False, keys_only=True):
    # Keep the existing administrator-only export permission and demo isolation.
    if demo:
        return ('info','Đã lưu APP thử nghiệm. Không ghi Google Sheet dùng chung trong chế độ mô phỏng.')
    if ledger.role(actor) != 'ADMIN':
        return ('warning','Đã lưu APP. Cần Admin đồng bộ báo cáo Google Sheet; quyền xuất dữ liệu không thay đổi.')
    try:
        with _LOCK:
            snapshot = make_snapshot(ledger, actor, demo=False)
            if keys_only:
                snapshot['tables'] = {n:snapshot['tables'][n] for n in KEY_TABS}
            count = sync_with_service(build_sheets_service(settings), configured_spreadsheet_id(settings), snapshot, optional_tabs=tuple(n for n in KEY_TABS if n not in {'05_KHO_KEY','06_TK_MICROSOFT','12_NHAT_KY'}) if keys_only else ())
        keys = len(snapshot['tables'].get('05_KHO_KEY',[]))
        msg=f'Đã lưu APP và đồng bộ Google Sheet: {keys} hồ sơ Key, {count} dòng báo cáo. Xem tab 15_DONG_BO_APP.'
        if snapshot.get('skipped_tabs'):
            return ('warning',msg+' Chưa có các tab: '+', '.join(snapshot['skipped_tabs'])+'. Dữ liệu ở APP vẫn đầy đủ.')
        return ('success',msg)
    except DomainError as err:
        return ('warning','Dữ liệu APP đã lưu (không cần nhập/Redeem lại). Chưa đồng bộ Sheet: '+str(err))
    except Exception as err:
        status = getattr(getattr(err,'resp',None),'status',None)
        detail = {401:'Danh tính Google chưa xác thực (401).',403:'Kiểm tra Sheets API và quyền Editor của service account (403).',404:'Không tìm thấy hoặc không có quyền mở workbook (404).',429:'Google giới hạn yêu cầu (429). Hãy thử lại.',400:'Google từ chối cấu trúc yêu cầu (400). Kiểm tra các tab/cột báo cáo.'}.get(status,'Kiểm tra kết nối, cấu hình Google Sheets và quyền ghi.')
        return ('warning','Dữ liệu APP đã lưu (không cần nhập/Redeem lại). Chưa đồng bộ Sheet: '+detail)
