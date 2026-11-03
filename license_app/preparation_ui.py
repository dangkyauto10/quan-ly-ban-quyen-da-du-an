import secrets
import os
import hashlib
import csv
import io
import streamlit as st
import streamlit.components.v1 as components
from .core import DomainError
from .labels import label_token,print_html,compare_labels,decode_photo

@st.cache_resource
def preview_signing_key():
    # Shared only for label snapshot verification across demo browsers.
    # It never grants access to another browser's ledger.
    return secrets.token_bytes(32)

def render(ledger,actor,role,page,is_demo):
    if os.getenv('APP_MODE')=='shared_test':
        key=hashlib.sha256(ledger.fingerprint_key+b'paired-label-v1').digest()
    elif not is_demo:
        key_text=st.secrets.get('qr_signing_key','')
        if len(key_text)<32:st.error('Admin cần cấu hình qr_signing_key ít nhất 32 ký tự, ổn định để đối chiếu tem.');return
        key=key_text.encode()
    else:key=preview_signing_key()
    data=ledger.preparation_rows(actor)
    if os.getenv('APP_MODE')=='shared_test':st.caption('Dữ liệu thử lưu chung trên máy chạy app. Điện thoại cùng mạng có thể tải ảnh QR; máy quét USB nhập vào hai ô mã. Camera trực tiếp trên web cần HTTPS.')
    if page=='Kế hoạch PC theo điểm':
        units=ledger.rows(actor,'units')
        if not units:st.info('Tạo đơn vị trước tại Đơn vị & tài khoản.');return
        with st.form('pc-plan'):
            unit=st.selectbox('Điểm / đơn vị',units,format_func=lambda r:r['project']+' · '+r['name'])
            qty=st.number_input('Số PC cần chuẩn bị',min_value=1,max_value=100000,value=10,step=1)
            save=st.form_submit_button('Lưu kế hoạch số PC')
            if save:
                try:ledger.set_plan(actor,unit['id'],int(qty),secrets.token_hex(16));st.success('Đã lưu kế hoạch số PC.');data=ledger.preparation_rows(actor)
                except DomainError as e:st.error(str(e))
        if data:
            counts=[]
            for u in units:
                ds=[r for r in data if r['unit_id']==u['id']]
                planned=next((r['quantity'] for r in ds if r['quantity']),None)
                counts.append({'Điểm':u['name'],'Kế hoạch':planned,'Đã gán số':sum(bool(r['number']) for r in ds),'Đóng gói':sum(r['inspection_state']=='PACKED' for r in ds)})
            st.dataframe(counts,hide_index=True)
            st.dataframe([{'Điểm':r['unit'],'Mã máy':r['asset_tag'],'Số thứ tự':r['number'],'Tổng PC kế hoạch':r['quantity']} for r in data],hide_index=True)
            buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['Dự án','Điểm','Mã máy','Serial','Thứ tự','Tổng PC','Trạng thái kiểm tra'])
            for r in data:
                values=[r['project'],r['unit'],r['asset_tag'],r['serial'],r['number'],r['quantity'],r['inspection_state'] or 'Chưa kiểm tra']
                writer.writerow(["'"+v if isinstance(v,str) and v[:1] in '=+-@\t\r' else v for v in values])
            st.download_button('Tải danh sách đối soát PC (CSV — mở bằng Excel)',buf.getvalue().encode('utf-8-sig'),'danh_sach_pc.csv','text/csv')
            device=st.selectbox('Máy cần cấp số thứ tự',[r for r in data if not r['number']],format_func=lambda r:r['asset_tag']) if any(not r['number'] for r in data) else None
            if device and st.button('Cấp số thứ tự máy'):
                try:ledger.number_device(actor,device['id'],secrets.token_hex(16));st.rerun()
                except DomainError as e:st.error(str(e))
        return
    if page=='In tem PC và vỏ hộp':
        ready=[r for r in data if r['number']]
        if not ready:st.info('Admin cần lập kế hoạch và cấp số máy tại Kế hoạch PC theo điểm.');return
        record=st.selectbox('Máy in tem',ready,format_func=lambda r:f"{r['unit']} · {r['asset_tag']} · {r['number']}/{r['quantity']}")
        width=st.number_input('Rộng tem (mm)',50,100,60)
        height=st.number_input('Cao tem (mm)',35,100,40)
        content=print_html(record,key,int(width),int(height))
        st.caption('Tải tệp, mở bằng trình duyệt trên PC rồi bấm In 2 tem. Chọn tỷ lệ 100%, tắt đầu/chân trang. In thử và quét kiểm tra trước in hàng loạt.')
        components.html(content,height=410,scrolling=True)
        st.download_button('Tải cặp tem để in (HTML)',content,'tem_pc_vo_hop.html','text/html')
        with st.expander('Mã tem để thử đối chiếu khi chưa có máy in'):
            st.code(label_token(record,'PC',key),language=None)
            st.code(label_token(record,'BOX',key),language=None)
        return
    if is_demo:st.warning('Đối chiếu QR dùng được giữa điện thoại và PC khi cùng bản app đang chạy. Dữ liệu tem là ảnh chụp lúc in; kết quả kiểm tra vẫn lưu riêng từng phiên. App khởi động lại có thể làm tem thử hết hiệu lực. Chưa dùng cho dữ liệu thật.')
    st.caption('Máy quét QR 2D USB: bấm ô mã tem thứ nhất rồi quét; bấm ô thứ hai rồi quét. Chụp từng QR hoặc tải ảnh tem. Có thể dán nội dung QR vào hai ô bên dưới. Đây là đọc ảnh từng tem, chưa phải quét camera liên tục.')
    tokens=[]
    for i,title in enumerate(['Tem thứ nhất','Tem thứ hai']):
        st.subheader(title)
        photo=None
        if os.getenv('APP_MODE')!='shared_test':
            photo=st.camera_input('Chụp '+title.lower(),key='camera-'+str(i))
        upload=st.file_uploader('Hoặc chọn ảnh '+title.lower(),type=['png','jpg','jpeg'],key='upload-'+str(i))
        source=photo or upload
        if source:
            try:st.session_state['scan-text-'+str(i)]=decode_photo(source.getvalue())
            except DomainError as e:st.error(str(e))
        tokens.append(st.text_input('Mã QR '+str(i+1)+' — bấm vào đây rồi quét',key='scan-text-'+str(i)))
    matched=None
    if all(tokens):
        try:
            matched=compare_labels(*tokens,key)
            st.success(f"ĐÚNG CẶP · {matched['unit']} · PC {matched['number']}/{matched['quantity']} · {matched['asset_tag']} · S/N {matched['serial']}")
            st.caption('Hai tem khớp nhau; cần đối chiếu serial trên máy và thực hiện kiểm tra kỹ thuật riêng.')
        except DomainError as e:st.error(str(e))
    else:st.info('CHƯA ĐỦ ĐỐI CHIẾU: cần đọc một tem thân máy và một tem vỏ hộp.')
    if role!='QC':return
    if not matched:return
    local=next((r for r in data if r['id']==matched['id']),None)
    if not local:
        st.info('Tem thuộc phiên dữ liệu khác. Đã đối chiếu hai tem; chưa ghi kết quả vào hồ sơ phiên này.');return
    if any(local[k]!=matched[k] for k in ['asset_tag','serial','unit','project','number','quantity']):
        st.error('Thông tin tem đã cũ so với hồ sơ hiện tại. Cần in lại cả cặp tem.');return
    with st.form('independent-inspection'):
        st.write('Kiểm tra độc lập: '+local['asset_tag'])
        serial=st.text_input('Serial đọc trực tiếp trên PC')
        passed=st.radio('Kết quả kiểm tra kỹ thuật',['Đạt','Không đạt'])=='Đạt'
        note=st.text_area('Nội dung kiểm tra kỹ thuật')
        if st.form_submit_button('Lưu kết quả kiểm tra'):
            try:ledger.inspect_device(actor,local['id'],passed,note,serial,secrets.token_hex(16));st.success('Đã lưu kiểm tra. Chỉ máy đạt mới được xác nhận đóng gói.')
            except DomainError as e:st.error(str(e))
    if st.button('Xác nhận đúng cặp và đóng gói hoàn tất'):
        try:ledger.close_package(actor,local['id'],secrets.token_hex(16));st.success('Đã hoàn tất kiểm tra và đóng gói PC cùng vỏ hộp.')
        except DomainError as e:st.error(str(e))
