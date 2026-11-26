"""Isolated, read-only file preview. Writes only via the existing ledger.import_keys."""
import hashlib
import hmac
import io
import json
import posixpath
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

from sqlalchemy import select
from license_app.core import DomainError, licenses

MAX_FILE = 10 * 1024 * 1024
MAX_EXPANDED = 60 * 1024 * 1024
MAX_ITEMS = 10000
MS_KEY = re.compile(r'(?:[A-Z0-9]{5}-){4}[A-Z0-9]{5}')
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
P = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def _archive(raw):
    if len(raw) > MAX_FILE:
        raise DomainError('File vượt 10 MB. Hãy chia thành các lô nhỏ hơn.')
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        infos = z.infolist()
        if (len(infos) > 2000 or sum(i.file_size for i in infos) > MAX_EXPANDED
                or len({i.filename for i in infos}) != len(infos)
                or any(i.flag_bits & 1 for i in infos)):
            z.close()
            raise DomainError('File quá lớn, được mã hóa hoặc cấu trúc không được hỗ trợ.')
        return z
    except (zipfile.BadZipFile, OSError):
        raise DomainError('Không đọc được file Excel/Word. Hãy lưu lại dưới dạng .xlsx hoặc .docx.') from None


def _xml(z, path):
    try:
        # Accept ordinary UTF-8 OOXML only; forbid entity and DTD declarations.
        raw = z.read(path).decode('utf-8-sig')
        if '\x00' in raw or re.search(r'<!\s*(?:DOCTYPE|ENTITY)', raw, re.I):
            raise ValueError()
        return ET.fromstring(raw)
    except (KeyError, UnicodeError, ValueError, ET.ParseError, RuntimeError, OSError, zipfile.BadZipFile):
        raise DomainError('File không đúng cấu trúc XML được hỗ trợ hoặc bị hỏng.') from None


def _sheets(z):
    rels = _xml(z, 'xl/_rels/workbook.xml.rels')
    targets = {r.get('Id'): r.get('Target', '') for r in rels.findall(P+'Relationship')
               if r.get('TargetMode') != 'External' and r.get('Type','').endswith('/worksheet')}
    out = {}
    for sheet in _xml(z, 'xl/workbook.xml').findall('.//'+S+'sheet'):
        target = targets.get(sheet.get(R+'id'))
        if target:
            path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
            if path.startswith('xl/worksheets/') and path in z.namelist():
                out[sheet.get('name')] = path
    if not out:
        raise DomainError('Không tìm thấy trang tính Excel được hỗ trợ.')
    return out


def sheet_names(raw):
    with _archive(raw) as z:
        return list(_sheets(z))


def _string(node, ns):
    # Exclude phonetic annotations, which are not the visible cell text.
    return ''.join(t.text or '' for t in node.findall(ns+'t') + node.findall(ns+'r/'+ns+'t'))


def excel_entries(raw, sheet, column, skip_header=True):
    if not re.fullmatch(r'[A-Z]{1,3}', column):
        raise DomainError('Nhập cột Excel, ví dụ A, B hoặc C.')
    with _archive(raw) as z:
        path = _sheets(z).get(sheet)
        if not path:
            raise DomainError('Trang tính không còn tồn tại.')
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [_string(i, S) for i in _xml(z, 'xl/sharedStrings.xml').findall(S+'si')]
        out = []
        first = True
        for c in _xml(z, path).iter(S+'c'):
            address = c.get('r','')
            if not re.fullmatch(column+r'[1-9][0-9]*', address):
                continue
            v = c.find(S+'v')
            kind = c.get('t','n')
            if c.find(S+'f') is not None:
                value = None  # Never evaluate or import formula results.
            elif kind == 's':
                try:
                    index = int(v.text)
                    if index < 0: raise ValueError()
                    value = shared[index]
                except (TypeError, AttributeError, ValueError, IndexError):
                    raise DomainError('Bảng chuỗi Excel không hợp lệ.') from None
            elif kind == 'inlineStr':
                inline = c.find(S+'is')
                value = _string(inline, S) if inline is not None else ''
            elif kind == 'str':
                value = v.text or '' if v is not None else ''
            else:
                # Require text cells to avoid Excel stripping leading zeroes or rounding codes.
                value = None if v is not None and v.text else ''
            if value is not None and not value.strip():
                continue
            if first and skip_header:
                first = False
                continue
            first = False
            out.append((address, value))
            if len(out) > MAX_ITEMS:
                raise DomainError('Mỗi lô tối đa 10.000 dòng. Hãy chia file.')
        return out


def word_entries(raw, skip_header=False):
    with _archive(raw) as z:
        root = _xml(z, 'word/document.xml')
        body = root.find(W+'body')
        if body is None:
            raise DomainError('Không tìm thấy nội dung Word.')
        out = []
        for index, p in enumerate(body.iter(W+'p'), 1):
            parts = []
            for node in p.iter():
                if node.tag == W+'t': parts.append(node.text or '')
                elif node.tag in {W+'br', W+'cr', W+'tab'}: parts.append('\n')
            for line_no, line in enumerate(''.join(parts).splitlines(),1):
                if line.strip(): out.append((f'Đoạn {index}.{line_no}', line))
            if len(out) > MAX_ITEMS:
                raise DomainError('Mỗi lô tối đa 10.000 dòng. Hãy chia file.')
        return out[1:] if skip_header else out


def validate_meta(batch, product, sku, channel, route, expires):
    if not batch.strip() or not sku.strip() or product not in {'Office','Windows','Antivirus'}:
        raise DomainError('Nhập mã lô, phần mềm và phiên bản/SKU.')
    if channel not in {'Retail','OEM','Volume','Vendor'} or route not in {'DIRECT','ACCOUNT_REDEEM'}:
        raise DomainError('Chọn đúng kênh và luồng xử lý.')
    if route == 'ACCOUNT_REDEEM' and (product != 'Office' or channel != 'Retail'):
        raise DomainError('Chỉ Office Retail phù hợp mới dùng luồng Redeem.')
    if expires:
        try: datetime.strptime(expires,'%Y-%m-%d')
        except ValueError: raise DomainError('Ngày hết hạn cần theo YYYY-MM-DD.') from None


def preview(ledger, actor, entries, product):
    """No writes, no decrypt/reveal. Compare with the same HMAC as Ledger.import_keys."""
    candidates = []
    report = []
    seen = set()
    with ledger.engine.connect() as c:
        ledger._auth(c, actor, {'ADMIN'})
        for location, raw in entries:
            key = re.sub(r'\s+', '', raw).upper() if isinstance(raw, str) else ''
            valid = (bool(MS_KEY.fullmatch(key)) if product in {'Office','Windows'} else
                     isinstance(raw, str) and len(key) >= 8 and len(key) <= 512
                     and not any(ch.isspace() for ch in raw.strip()) and not any(ord(ch)<32 for ch in key))
            if not valid:
                report.append({'Vị trí':location,'Key đã che':'—','Kết quả':'Sai định dạng / không phải văn bản'})
                continue
            digest = hmac.new(ledger.fingerprint_key, key.encode(), hashlib.sha256).hexdigest()
            # Mask the full key even for the minimum-length vendor code.
            masked = '…'+key[-5:]
            item = {'Vị trí':location,'Key đã che':masked,'Kết quả':''}
            report.append(item)
            if digest in seen:
                item['Kết quả'] = 'Trùng trong file'
            else:
                seen.add(digest)
                candidates.append((digest, key, item))
        existing = set()
        digests = [x[0] for x in candidates]
        for start in range(0,len(digests),400):
            existing.update(c.execute(select(licenses.c.fingerprint).where(licenses.c.fingerprint.in_(digests[start:start+400]))).scalars())
    ready = []
    for digest, key, item in candidates:
        if digest in existing: item['Kết quả']='Đã có trong kho'
        else:
            item['Kết quả']='Có thể nhập'; ready.append(key)
    return ready, report


def render_import(st, ledger, actor):
    """Extra UI only; existing manual workflow is intentionally untouched."""
    with st.expander('📥 Nhập danh sách key từ Excel / Word', expanded=False):
        st.caption('Mỗi file/lần nhập chỉ dùng cho một lô, cùng phần mềm, SKU, kênh và luồng. Không tự xác nhận chứng từ hoặc Redeem.')
        st.caption('Excel .xlsx: chọn cột key dạng văn bản, mỗi ô một key. Word .docx: mỗi dòng/ô bảng một key; tài liệu ảnh hoặc file .xls/.doc cần chuyển định dạng trước.')
        col1,col2=st.columns(2)
        with col1:
            batch=st.text_input('Mã lô',key='bulk-key-batch')
            product=st.selectbox('Phần mềm',['Office','Windows','Antivirus'],key='bulk-key-product')
            sku=st.text_input('Phiên bản / SKU',key='bulk-key-sku')
        with col2:
            channel=st.selectbox('Kênh cấp phép',['Retail','OEM','Volume','Vendor'],key='bulk-key-channel')
            route=st.selectbox('Luồng xử lý',['DIRECT','ACCOUNT_REDEEM'],format_func=lambda x:'Redeem Office Retail' if x=='ACCOUNT_REDEEM' else 'Kích hoạt theo nhà cung cấp',key='bulk-key-route')
            expires=st.text_input('Ngày hết hạn nếu có (YYYY-MM-DD)',key='bulk-key-expires')
        upload=st.file_uploader('Chọn danh sách Excel hoặc Word (tối đa 10 MB)',type=['xlsx','docx'],key='bulk-key-file')
        if upload is None: return
        try:
            raw=upload.getvalue()
            if upload.name.lower().endswith('.xlsx'):
                left,right=st.columns(2)
                sheet=left.selectbox('Trang tính',sheet_names(raw),key='bulk-key-sheet')
                column=right.text_input('Cột chứa key',value='A',key='bulk-key-column').strip().upper()
                skip=st.checkbox('Bỏ dòng tiêu đề (ô có nội dung đầu tiên của cột)',value=False,key='bulk-key-xlsx-skip')
                entries=excel_entries(raw,sheet,column,skip)
                source=[sheet,column,skip]
            else:
                skip=st.checkbox('Bỏ dòng đầu tiên có nội dung',value=False,key='bulk-key-docx-skip')
                entries=word_entries(raw,skip)
                source=['word',skip]
            validate_meta(batch,product,sku,channel,route,expires)
            ready, report=preview(ledger,actor,entries,product)
        except DomainError as err:
            st.warning(str(err)); return
        except Exception:
            st.error('Không thể đọc hoặc kiểm tra danh sách. Không có dữ liệu nào được ghi.'); return
        counts=[len(report),len(ready),len(report)-len(ready)]
        for col,title,count in zip(st.columns(3),['Đọc được','Có thể nhập','Loại khỏi lô'],counts):col.metric(title,count)
        if report: st.dataframe(report,hide_index=True,height=230,width='stretch')
        else: st.info('Không tìm thấy dòng dữ liệu ở vị trí đã chọn.')
        st.caption('Kiểm tra hình thức và trùng lặp, không xác nhận key còn hiệu lực tại nhà cung cấp. Các key mới vẫn ở trạng thái Mới nhận.')
        if not ready:return
        signature=hmac.new(ledger.fingerprint_key, json.dumps([actor,hashlib.sha256(raw).hexdigest(),source,batch,product,sku,channel,route,expires,ready],ensure_ascii=False).encode(),hashlib.sha256).hexdigest()
        # A changed selection or concurrent warehouse change produces a different button key,
        # so a click from the previous preview cannot submit a different set of keys.
        confirmed=st.checkbox(f'Tôi xác nhận thông tin lô và chỉ nhập {len(ready)} key được đánh dấu Có thể nhập.',key='bulk-key-confirm-'+signature)
        if st.button(f'Nhập {len(ready)} key vào kho',disabled=not confirmed,type='primary',key='bulk-key-submit-'+signature):
            op_key='bulk-key-operation-'+signature
            op=st.session_state.setdefault(op_key,str(uuid.uuid4()))
            try:
                result=ledger.import_keys(actor,batch,product,sku,channel,route,ready,expires,op)
                st.success(f'Đã nhập {result} key vào kho. Chuyển sang xác nhận kiểm tra chứng từ theo quy trình cũ.')
            except DomainError as err:
                st.error(str(err)+' Không ghi đè key cũ. Kiểm tra lại danh sách trước khi nhập.')
            except Exception:
                st.error('Chưa xác nhận được kết quả. Kiểm tra lại kho trước khi gửi lại; không nhập lặp.')
