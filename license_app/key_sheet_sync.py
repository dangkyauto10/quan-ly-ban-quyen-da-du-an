"""Post-commit report sync. Never writes the ledger or exports raw key fields."""
from threading import RLock
import logging
import time
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
    stage='đọc dữ liệu APP'
    started=time.monotonic()
    try:
        with _LOCK:
            snapshot = make_snapshot(ledger, actor, demo=False)
            if keys_only:
                snapshot['tables'] = {n:snapshot['tables'][n] for n in KEY_TABS}
            stage='khởi tạo danh tính Google'
            service=build_sheets_service(settings)
            stage='đọc/ghi Google Sheet'
            count = sync_with_service(service, configured_spreadsheet_id(settings), snapshot, optional_tabs=tuple(n for n in KEY_TABS if n not in {'05_KHO_KEY','06_TK_MICROSOFT','12_NHAT_KY'}) if keys_only else ())
        keys = len(snapshot['tables'].get('05_KHO_KEY',[]))
        msg=f'Đã lưu APP và đồng bộ Google Sheet: {keys} hồ sơ Key, {count} dòng báo cáo. Xem tab 15_DONG_BO_APP.'
        if snapshot.get('skipped_tabs'):
            return ('warning',msg+' Chưa có các tab: '+', '.join(snapshot['skipped_tabs'])+'. Dữ liệu ở APP vẫn đầy đủ.')
        return ('success',msg)
    except DomainError as err:
        return ('warning','Dữ liệu APP đã lưu (không cần nhập/Redeem lại). Chưa đồng bộ Sheet ['+stage+']: '+str(err))
    except Exception as err:
        status = getattr(getattr(err,'resp',None),'status',None)
        try: status=int(status)
        except (TypeError,ValueError): status=None
        kind=type(err).__name__
        elapsed=round(time.monotonic()-started,1)
        details={401:'Danh tính Google chưa xác thực.',403:'Google từ chối quyền truy cập hoặc API chưa được cấp quyền.',404:'Không tìm thấy hoặc không có quyền mở workbook.',429:'Google giới hạn yêu cầu.',400:'Google từ chối cấu trúc yêu cầu.',500:'Google gặp lỗi máy chủ.',503:'Dịch vụ Google tạm thời không khả dụng.'}
        detail=details.get(status)
        if not detail:
            low=kind.lower()
            if 'timeout' in low: detail='Kết nối quá thời gian chờ.'
            elif 'refresh' in low or 'credential' in low: detail='Không xác thực được danh tính Google.'
            elif 'connection' in low or 'transport' in low or 'socket' in low or 'ssl' in low or 'servernotfound' in low: detail='Lỗi kết nối mạng hoặc TLS.'
            elif kind in {'ModuleNotFoundError','ImportError'}: detail='Thiếu hoặc lỗi thư viện kết nối.'
            else: detail='Lỗi kỹ thuật tại bước nêu trên.'
        # Never emit raw exception messages, request payloads, secrets, or traceback.
        code=f'{kind}; HTTP {status}' if status is not None else kind
        logging.getLogger(__name__).warning('KEY_SYNC_FAILED stage=%s code=%s elapsed=%ss',stage,code,elapsed)
        return ('warning',f'Dữ liệu APP đã lưu (không cần nhập/Redeem lại). Chưa đồng bộ Sheet: {detail} Bước: {stage}; mã lỗi: {code}; thời gian: {elapsed}s.')
