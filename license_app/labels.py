"""Signed label snapshots: no keys or Microsoft accounts on printed labels."""
import base64
import hashlib
import hmac
import html
import io
import json
import zlib
import uuid
from urllib.parse import urlparse, parse_qs
import qrcode
import qrcode.image.svg
from .core import DomainError

def label_token(record,kind,key):
    if kind not in {'PC','BOX'}:raise DomainError('Loại tem không hợp lệ.')
    if not record.get('number') or not record.get('quantity'):raise DomainError('Cần cấp số thứ tự PC trước khi in tem.')
    board_serial=(record.get('board_serial') or '').strip()
    if not board_serial:raise DomainError('Cần ghi nhận serial mainboard trước khi tạo tem.')
    try:
        device_id=uuid.UUID(str(record['id'])).bytes
    except (KeyError,ValueError,TypeError):
        device_id=None
    if device_id is not None:
        kind_code=0 if kind=='PC' else 1
        # v6 reduces the signed payload and QR matrix for faster phone scanning.
        payload=bytes([6,kind_code])+device_id+label_snapshot_digest(record)[:8]
        signature=hmac.new(key,b'v6.'+payload,hashlib.sha256).digest()[:8]
        compact=base64.urlsafe_b64encode(payload+signature).decode().rstrip('=')
        return 'v6.'+compact
    return _legacy_label_token(record,kind,key,board_serial)

def label_snapshot_digest(record):
    """Bind a compact QR to the equipment details printed beside it."""
    data={k:record[k] for k in ['id','asset_tag','unit','project','number','quantity']}
    data['serial']=(record.get('board_serial') or record.get('serial') or '').strip()
    if (record.get('point_id') or record.get('point') is not None or
            record.get('point_code') is not None):
        data.update(v=3,point=record.get('point') or '',point_code=record.get('point_code') or '')
    else:data['v']=2
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    return hashlib.sha256(raw).digest()[:12]

def label_matches_record(matched,actual):
    if matched.get('id')!=actual.get('id'):return False
    if matched.get('v') in {5,6}:
        snapshot=matched.get('snapshot',b'')
        return hmac.compare_digest(snapshot,label_snapshot_digest(actual)[:len(snapshot)])
    return all(actual.get(k)==matched.get(k) for k in actual)

def _legacy_label_token(record,kind,key,board_serial):
    data={k:record[k] for k in ['id','asset_tag','unit','project','number','quantity']}
    data['serial']=board_serial
    if record.get('point_id'):
        data.update(v=3,point=record.get('point') or '',point_code=record.get('point_code') or '')
    else:data['v']=2
    data['kind']=kind
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    body=base64.urlsafe_b64encode(zlib.compress(raw,9)).decode().rstrip('=')
    signed='v4.'+body
    sig=base64.urlsafe_b64encode(hmac.new(key,signed.encode(),hashlib.sha256).digest()[:16]).decode().rstrip('=')
    return signed+'.'+sig

def read_label(value,key):
    value=value.strip()
    if value.startswith('https://'):value=parse_qs(urlparse(value).query).get('tem',[''])[0]
    if len(value)>6000:raise DomainError('Tem quá dài hoặc không hợp lệ.')
    try:
        if value.startswith('v6.'):
            encoded=value[3:]
            packed=base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4))
            if base64.urlsafe_b64encode(packed).decode().rstrip('=')!=encoded:raise ValueError()
            if len(packed)!=34:raise ValueError()
            payload,signature=packed[:26],packed[26:]
            expected=hmac.new(key,b'v6.'+payload,hashlib.sha256).digest()[:8]
            if not hmac.compare_digest(signature,expected) or payload[0]!=6 or payload[1] not in {0,1}:raise ValueError()
            return {'v':6,'id':str(uuid.UUID(bytes=payload[2:18])),
                'snapshot':payload[18:26],
                'kind':'PC' if payload[1]==0 else 'BOX'}
        if value.startswith('v5.'):
            encoded=value[3:]
            packed=base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4))
            if base64.urlsafe_b64encode(packed).decode().rstrip('=')!=encoded:raise ValueError()
            if len(packed)!=46:raise ValueError()
            payload,signature=packed[:30],packed[30:]
            expected=hmac.new(key,b'v5.'+payload,hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(signature,expected) or payload[0]!=5 or payload[1] not in {0,1}:raise ValueError()
            return {'v':5,'id':str(uuid.UUID(bytes=payload[2:18])),
                'snapshot':payload[18:30],
                'kind':'PC' if payload[1]==0 else 'BOX'}
        if value.startswith('v4.'):
            version,body,sig=value.split('.')
            signed=version+'.'+body
            expected=base64.urlsafe_b64encode(
                hmac.new(key,signed.encode(),hashlib.sha256).digest()[:16]).decode().rstrip('=')
            if not hmac.compare_digest(sig,expected):raise ValueError()
            compressed=base64.urlsafe_b64decode(body+'='*(-len(body)%4))
            decoder=zlib.decompressobj()
            raw=decoder.decompress(compressed,8193)
            if len(raw)>8192 or decoder.unconsumed_tail or not decoder.eof:raise ValueError()
            data=json.loads(raw)
        else:
            body,sig=value.split('.')
            expected=hmac.new(key,body.encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig,expected):raise ValueError()
            data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data['v'] not in {2,3} or data['kind'] not in {'PC','BOX'}:raise ValueError()
        if any(k not in data for k in ['id','asset_tag','serial','unit','project','number','quantity']):raise ValueError()
        if data['v']==3 and any(k not in data for k in ['point','point_code']):raise ValueError()
        return data
    except Exception:raise DomainError('Tem không hợp lệ hoặc thuộc phiên bản in khác. Hãy tạo lại tem thử.') from None

def compare_labels(first,second,key):
    a,b=read_label(first,key),read_label(second,key)
    if a['kind']==b['kind']:raise DomainError('CHƯA ĐỦ ĐỐI CHIẾU: cần một tem THÂN MÁY và một tem VỎ HỘP.')
    if a['v'] in {5,6} or b['v'] in {5,6}:
        if a['v']!=b['v']:raise DomainError('Hai tem khác phiên bản. Hãy in lại đúng cả cặp tem.')
        if a['id']!=b['id'] or a['snapshot']!=b['snapshot']:
            raise DomainError('SAI CẶP: hai tem không cùng hồ sơ máy hoặc tem đã thay đổi.')
        return a
    fields=['id','asset_tag','serial','unit','project','number','quantity']
    if a['v']==3 or b['v']==3:
        fields+=['point','point_code']
        if a['v']!=b['v']:raise DomainError('SAI CẶP: hai tem khác phiên bản hoặc thông tin điểm nhận.')
    if any(a[k]!=b[k] for k in fields):raise DomainError('SAI CẶP: hai tem không cùng hồ sơ máy hoặc thông tin tem đã thay đổi.')
    return a

def qr_svg(text):
    q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=8,border=4)
    q.add_data(text);q.make(fit=True)
    out=io.BytesIO();q.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(out)
    return out.getvalue().decode()

def print_html(record,key,width=60,height=40):
    return print_html_batch([record],key,width,height)

def print_html_batch(records,key,width=60,height=40):
    if not 50<=width<=100 or not 35<=height<=100:raise DomainError('Khổ tem chưa hỗ trợ.')
    if not records:raise DomainError('Lô tem đang trống.')
    labels=[]
    for record in records:
        for kind,title in [('PC','THÂN MÁY'),('BOX','VỎ HỘP')]:
            token=label_token(record,kind,key)
            board_serial=(record.get('board_serial') or '').strip()
            if not board_serial:raise DomainError('Cần ghi nhận serial mainboard trước khi tạo tem.')
            lines=['ĐƠN VỊ ĐƯỢC CẤP',record['unit']]
            if record.get('point'):lines.append(record['point'])
            lines.extend([f"PC: {record['number']:02d}/{record['quantity']:02d}",record['asset_tag'],'S/N Main: '+board_serial])
            info=''.join('<p>'+html.escape(s)+'</p>' for s in lines)
            labels.append('<section><header>'+html.escape(title)+'</header><div class="label-body">'+qr_svg(token)+'<div class="label-info">'+info+'</div></div></section>')
    batch_note=f'Lô gồm {len(records)} PC, in liên tục theo số thứ tự; mỗi PC có hai tem liền nhau.'
    return f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Tem PC và vỏ hộp</title>
<style>@page{{size:{width}mm {height}mm;margin:0}}*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif}}section{{width:{width}mm;height:{height}mm;padding:1.5mm;display:flex;flex-direction:column;gap:1mm;break-after:page;overflow:hidden}}section:last-child{{break-after:auto}}section>header{{height:4.2mm;flex:0 0 4.2mm;text-align:center;font-size:8pt;font-weight:800;line-height:4.2mm;color:#102a46}}.label-body{{display:flex;align-items:center;gap:1mm;min-height:0;flex:1}}.label-body svg{{width:27mm;height:27mm;flex:0 0 27mm}}.label-info{{flex:1;min-width:0;line-height:1.05}}p{{margin:0 0 .7mm;font-size:6.5pt;line-height:1.05;overflow-wrap:anywhere}}.label-info p:nth-child(2){{font-size:8pt;font-weight:bold}}@media screen{{section{{border:1px solid #aaa;margin:10px}}}}@media print{{button,aside{{display:none}}}}</style>
<button onclick="window.print()">In {len(labels)} tem</button><aside>{html.escape(batch_note)} Chọn đúng khổ tem, tỷ lệ 100%, tắt đầu/chân trang. QR chứa thông tin tem đã ký, không chứa key.</aside>{''.join(labels)}</html>'''

def decode_photo(raw):
    import cv2
    import numpy as np
    img=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
    if img is None:raise DomainError('Không đọc được ảnh.')
    text,_,_=cv2.QRCodeDetector().detectAndDecode(img)
    if not text:raise DomainError('Chưa đọc được QR. Chụp gần hơn, đủ sáng và đủ bốn góc tem.')
    return text
