"""Post-commit report sync. Never writes the ledger or exports raw key fields."""
from threading import RLock
import logging
import time
from .core import DomainError
from .sheet_sync import make_snapshot, sync_with_service, configured_spreadsheet_id

KEY_TABS = ('01_DU_AN_DON_VI','02_NGUOI_DUNG','03_SAN_PHAM','04_LO_BAN_GIAO',
            '05_KHO_KEY','06_TK_MICROSOFT','07_REDEEM_LICENSE','12_NHAT_KY')
_LOCK = RLock()

# Key reports use a requests transport instead of httplib2's network stack.
# Keep this separate from the existing plan, supplier and activation functions.
def build_sheets_service(settings):
    import re
    import requests
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from httplib2 import Response

    scopes=['https://www.googleapis.com/auth/spreadsheets']
    deadline=time.monotonic()+25
    session=requests.Session()
    auth_request=Request(session=session)
    def timeout_for(requested=6):
        remaining=deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Google request deadline exceeded')
        # Both connection and read are bounded; no automatic HTTP retries.
        limit=min(6,remaining/2,requested if isinstance(requested,(int,float)) and requested>0 else 6)
        return (limit,limit)
    def bounded_auth_request(url,method='GET',body=None,headers=None,timeout=6,**kwargs):
        return auth_request(url,method=method,body=body,headers=headers,timeout=timeout_for(timeout),**kwargs)
    info=settings.get('google_service_account')
    identity=''
    try:
        if info:
            credentials=Credentials.from_service_account_info(dict(info),scopes=scopes)
        else:
            credentials=google.auth.default(scopes=scopes,request=bounded_auth_request)[0]
        candidate=getattr(credentials,'service_account_email','')
        if isinstance(candidate,str) and re.fullmatch(r'[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.iam\.gserviceaccount\.com',candidate):
            identity=candidate
        # Explicit refresh separates identity/token failures from Sheets API calls.
        credentials.refresh(bounded_auth_request)
        class RequestsHttp:
            def request(self,uri,method='GET',body=None,headers=None,**kwargs):
                hdr=dict(headers or {})
                credentials.before_request(bounded_auth_request,method,uri,hdr)
                response=session.request(method,uri,data=body,headers=hdr,timeout=timeout_for(),allow_redirects=False)
                result=Response({**{str(k).lower():str(v) for k,v in response.headers.items()},'status':str(response.status_code)})
                result.status=response.status_code
                result.reason=response.reason
                return result,response.content
            def close(self):
                session.close()
        service=build('sheets','v4',http=RequestsHttp(),cache_discovery=False,static_discovery=True)
        service._key_sync_identity=identity
        return service
    except DomainError:
        session.close()
        raise
    except DefaultCredentialsError:
        session.close()
        raise DomainError('APP chưa có danh tính Google Sheets hợp lệ. Cần cấu hình [google_service_account] trong Streamlit Secrets.') from None
    except Exception as err:
        session.close()
        suffix='; tài khoản dịch vụ: '+identity if identity else ''
        raise DomainError('Không xác thực được Google trước khi ghi Sheet. Mã lỗi: '+type(err).__name__+suffix+'.') from None

def publish(ledger, actor, settings, *, demo=False, keys_only=True):
    # Keep the existing administrator-only export permission and demo isolation.
    if demo:
        return ('info','Đã lưu APP thử nghiệm. Không ghi Google Sheet dùng chung trong chế độ mô phỏng.')
    if ledger.role(actor) != 'ADMIN':
        return ('warning','Đã lưu APP. Cần Admin đồng bộ báo cáo Google Sheet; quyền xuất dữ liệu không thay đổi.')
    stage='đọc dữ liệu APP'
    started=time.monotonic()
    service=None
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
        identity=getattr(service,'_key_sync_identity','')
        suffix=' Tài khoản dịch vụ: '+identity if isinstance(identity,str) and identity else ''
        return ('warning',f'Dữ liệu APP đã lưu (không cần nhập/Redeem lại). Chưa đồng bộ Sheet: {detail} Bước: {stage}; mã lỗi: {code}; thời gian: {elapsed}s.'+suffix)
    finally:
        if service is not None:
            try: service.close()
            except Exception: pass
