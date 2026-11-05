"""Signed label snapshots: no keys or Microsoft accounts on printed labels."""
import base64
import hashlib
import hmac
import html
import io
import json
from urllib.parse import urlparse, parse_qs
import qrcode
import qrcode.image.svg
from .core import DomainError

def label_token(record,kind,key):
    if kind not in {'PC','BOX'}:raise DomainError('Loại tem không hợp lệ.')
    if not record.get('number') or not record.get('quantity'):raise DomainError('Cần cấp số thứ tự PC trước khi in tem.')
    board_serial=(record.get('board_serial') or '').strip()
    if not board_serial:raise DomainError('Cần ghi nhận serial mainboard trước khi tạo tem.')
    data={k:record[k] for k in ['id','asset_tag','unit','project','number','quantity']}
    data['serial']=board_serial
    data.update(v=2,kind=kind)
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    body=base64.urlsafe_b64encode(raw).decode().rstrip('=')
    sig=hmac.new(key,body.encode(),hashlib.sha256).hexdigest()
    return body+'.'+sig

def read_label(value,key):
    value=value.strip()
    if value.startswith('https://'):value=parse_qs(urlparse(value).query).get('tem',[''])[0]
    if len(value)>6000:raise DomainError('Tem quá dài hoặc không hợp lệ.')
    try:
        body,sig=value.split('.')
        expected=hmac.new(key,body.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data['v']!=2 or data['kind'] not in {'PC','BOX'}:raise ValueError()
        if any(k not in data for k in ['id','asset_tag','serial','unit','project','number','quantity']):raise ValueError()
        return data
    except Exception:raise DomainError('Tem không hợp lệ hoặc thuộc phiên bản in khác. Hãy tạo lại tem thử.') from None

def compare_labels(first,second,key):
    a,b=read_label(first,key),read_label(second,key)
    if a['kind']==b['kind']:raise DomainError('CHƯA ĐỦ ĐỐI CHIẾU: cần một tem THÂN MÁY và một tem VỎ HỘP.')
    fields=['id','asset_tag','serial','unit','project','number','quantity']
    if any(a[k]!=b[k] for k in fields):raise DomainError('SAI CẶP: hai tem không cùng hồ sơ máy hoặc thông tin tem đã thay đổi.')
    return a

def qr_svg(text):
    q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=8,border=4)
    q.add_data(text);q.make(fit=True)
    out=io.BytesIO();q.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(out)
    return out.getvalue().decode()

def print_html(record,key,width=60,height=40):
    if not 50<=width<=100 or not 35<=height<=100:raise DomainError('Khổ tem chưa hỗ trợ.')
    labels=[]
    for kind,title in [('PC','THÂN MÁY'),('BOX','VỎ HỘP')]:
        token=label_token(record,kind,key)
        board_serial=(record.get('board_serial') or '').strip()
        if not board_serial:raise DomainError('Cần ghi nhận serial mainboard trước khi tạo tem.')
        lines=[title,record['unit'],f"PC: {record['number']:02d}/{record['quantity']:02d}",record['asset_tag'],'S/N Main: '+board_serial]
        labels.append('<section>'+qr_svg(token)+'<div>'+''.join('<p>'+html.escape(s)+'</p>' for s in lines)+'</div></section>')
    return f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Tem PC và vỏ hộp</title>
<style>@page{{size:{width}mm {height}mm;margin:0}}*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif}}section{{width:{width}mm;height:{height}mm;padding:2mm;display:flex;align-items:center;gap:1mm;break-after:page;overflow:hidden}}section:last-child{{break-after:auto}}svg{{width:29mm;height:29mm;flex-shrink:0}}div{{flex:1;min-width:0}}p{{margin:0 0 1mm;font-size:8pt;overflow-wrap:anywhere}}p:first-child{{font-weight:bold}}p:nth-child(3){{font-weight:bold;font-size:11pt}}@media screen{{section{{border:1px solid #aaa;margin:10px}}}}@media print{{button,aside{{display:none}}}}</style>
<button onclick="window.print()">In 2 tem</button><aside>Chọn đúng khổ tem, tỷ lệ 100%, tắt đầu/chân trang. QR chứa thông tin tem đã ký, không chứa key. Bản thử: quét/chụp trong chức năng Đối chiếu tem; không phải liên kết tự mở.</aside>{''.join(labels)}</html>'''

def decode_photo(raw):
    import cv2
    import numpy as np
    img=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
    if img is None:raise DomainError('Không đọc được ảnh.')
    text,_,_=cv2.QRCodeDetector().detectAndDecode(img)
    if not text:raise DomainError('Chưa đọc được QR. Chụp gần hơn, đủ sáng và đủ bốn góc tem.')
    return text
