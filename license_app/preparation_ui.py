import secrets
import os
import hashlib
import csv
import io
import time
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
    if os.getenv('APP_MODE') in {'shared_test','team_test'}:
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
        ready=[r for r in data if r['number'] and r['activation_ready']]
        if not ready:st.info('Cần cấp số máy tại Kế hoạch PC theo điểm và KTV báo kích hoạt thành công trước khi in tem.');return
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
    if is_demo:st.warning('Dữ liệu riêng từng phiên; để đội thử chung, dùng preview_app.py mới hoặc test_app.py.')
    notice=st.session_state.get('packing-notice')
    if notice and notice['actor']==actor:st.success(notice['text'])
    st.caption('Mỗi người chọn danh tính kiểm tra khác nhau. Chụp lần lượt hai tem QR, đối chiếu serial thực rồi gửi kết quả. Đây là đọc ảnh chụp QR, chưa phải camera quét liên tục.')
    if role in {'ADMIN','QC'}:
        reservations=ledger.check_claims(actor)
        states={'PACKED':'Đã đóng gói','PASSED':'Đã kiểm tra đạt','FAILED':'Lỗi — chờ KTV'}
        summary=[]
        for r in data:
            claim=reservations.get(r['id'])
            busy=claim and claim['until']>int(time.time())
            summary.append({'Máy':r['asset_tag'],'Điểm':r['unit'],
                'Trạng thái':states.get(r['inspection_state'],'Chưa kiểm tra'),
                'Đang kiểm tra':claim['owner'] if busy else ''})
        st.dataframe(summary,hide_index=True,width='stretch')
        if st.button('Cập nhật danh sách máy'):st.rerun()
        if role=='ADMIN':
            active=[r for r in data if r['id'] in reservations]
            if active:
                release=st.selectbox('Máy cần thu hồi lượt kiểm tra',active,format_func=lambda r:r['asset_tag'])
                if st.button('Thu hồi lượt kiểm tra'):
                    try:ledger.release_check(actor,release['id'],secrets.token_hex(16));st.rerun()
                    except DomainError as e:st.error(str(e))
    round_id=st.session_state.get('scan-round',0)
    tokens=[]
    for i,title in enumerate(['1. Tem THÂN MÁY','2. Tem VỎ HỘP']):
        st.subheader(title)
        field=f'scan-text-{round_id}-{i}'
        photo=None
        if os.getenv('APP_MODE')!='shared_test':
            photo=st.camera_input('Chụp '+title[3:].lower(),key=f'camera-{round_id}-{i}')
        upload=st.file_uploader('Hoặc chọn ảnh tem',type=['png','jpg','jpeg'],key=f'upload-{round_id}-{i}')
        source=photo or upload
        if source:
            raw=source.getvalue();digest=hashlib.sha256(raw).hexdigest()
            marker=f'scan-image-{round_id}-{i}'
            if st.session_state.get(marker)!=digest:
                try:st.session_state[field]=decode_photo(raw)
                except DomainError as e:st.session_state[field]='';st.error(str(e))
                st.session_state[marker]=digest
        tokens.append(st.text_input('Nội dung QR '+str(i+1)+' (dán mã khi thử chưa có tem)',key=field))
    matched=None
    if all(tokens):
        try:
            matched=compare_labels(*tokens,key)
            st.success(f"ĐÚNG CẶP · {matched['unit']} · PC {matched['number']}/{matched['quantity']} · {matched['asset_tag']} · S/N {matched['serial']}")
        except DomainError as e:st.error(str(e))
    else:st.info('CHƯA ĐỦ ĐỐI CHIẾU: cần một tem thân máy và một tem vỏ hộp.')
    if st.button('Xóa hai mã / quét máy tiếp theo'):
        st.session_state['scan-round']=round_id+1
        st.rerun()
    if role!='QC' or not matched:return
    local=next((r for r in data if r['id']==matched['id']),None)
    if not local:
        st.error('Không có hồ sơ máy trong kho dữ liệu này. Kiểm tra đang mở đúng app và dùng đúng tem.');return
    if any(local[k]!=matched[k] for k in ['asset_tag','serial','unit','project','number','quantity']):
        st.error('Tem đã cũ so với hồ sơ. Cần in lại cả cặp tem.');return
    if local['inspection_state']=='PACKED':
        st.info('Máy này đã đóng gói hoàn tất. Chuyển sang máy tiếp theo.');return
    claim=ledger.check_claims(actor).get(local['id'])
    owned=claim and claim['owner']==actor and claim['until']>int(time.time())
    if st.button('Nhận máy / gia hạn 15 phút kiểm tra'):
        try:ledger.claim_for_check(actor,local['id'],secrets.token_hex(16));st.rerun()
        except DomainError as e:st.error(str(e))
    if not owned:
        if claim and claim['until']>int(time.time()):st.warning('Máy đang do '+claim['owner']+' kiểm tra.')
        else:st.info('Bấm Nhận máy để giữ lượt kiểm tra, tránh hai người xử lý trùng.')
        return
    st.info('Anh/chị đang giữ lượt kiểm tra máy này trong tối đa 15 phút. Có thể gia hạn hoặc trả máy.')
    if st.button('Trả máy — chưa gửi kết quả'):
        try:ledger.release_check(actor,local['id'],secrets.token_hex(16));st.rerun()
        except DomainError as e:st.error(str(e))
    with st.form('mobile-packing-'+str(round_id)):
        serial=st.text_input('Serial đọc trực tiếp trên PC')
        passed=st.radio('Kết quả kiểm tra kỹ thuật',['Đạt','Không đạt'],index=None)
        note=st.text_area('Nội dung kiểm tra / lỗi phát hiện')
        checked=st.checkbox('Đã đối chiếu serial thực và thực hiện kiểm tra kỹ thuật')
        send=st.form_submit_button('Gửi kết quả — đạt thì hoàn tất đóng gói',type='primary')
        if send:
            if not checked or passed is None:st.error('Chọn kết quả và xác nhận đã kiểm tra trước khi gửi.')
            else:
                operation=st.session_state.setdefault(f'pack-op-{actor}-{round_id}',secrets.token_hex(16))
                try:
                    ledger.submit_packing(actor,*tokens,key,passed=='Đạt',note,serial,operation)
                    text=f"Đã lưu {local['asset_tag']} · {local['unit']}. "+('ĐÓNG GÓI HOÀN TẤT.' if passed=='Đạt' else 'KHÔNG ĐẠT — đã chuyển KTV xử lý lại.')
                    st.session_state['packing-notice']={'actor':actor,'text':text}
                    st.session_state['scan-round']=round_id+1
                    st.rerun()
                except DomainError as e:st.error(str(e))
                except Exception:st.error('Chưa xác nhận lưu thành công. Giữ nguyên màn hình và thử gửi lại; không chuyển máy khi chưa có xác nhận.')
