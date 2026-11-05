import secrets
import os
import hashlib
import csv
import io
import time
import streamlit as st
import streamlit.components.v1 as components
from .core import DomainError
from .labels import label_token,print_html,print_html_batch,compare_labels,decode_photo

@st.cache_resource
def preview_signing_key():
    # Shared only for label snapshot verification across demo browsers.
    # It never grants access to another browser's ledger.
    return secrets.token_bytes(32)

def render(ledger,actor,role,page,is_demo):
    if os.getenv('APP_MODE') in {'shared_test','team_test'}:
        key=hashlib.sha256(ledger.fingerprint_key+b'paired-label-v1').digest()
    elif not is_demo:
        key_text=os.getenv('QR_SIGNING_KEY') or st.secrets.get('qr_signing_key','')
        if len(key_text)<32:st.error('Admin cần cấu hình qr_signing_key ít nhất 32 ký tự, ổn định để đối chiếu tem.');return
        key=key_text.encode()
    else:key=preview_signing_key()
    if page=='Hàng đợi in':
        batches=ledger.label_queue_rows(actor)
        if not batches:st.info('Chưa có lô tem đang chờ in.');return
        grouped={}
        for row in batches:grouped.setdefault(row['batch_id'],[]).append(row)
        choices=list(grouped)
        selected=st.selectbox('Lô chờ in',choices,format_func=lambda bid:
            f"{grouped[bid][0]['project']} · {grouped[bid][0]['unit']} · {grouped[bid][0]['ktv']} · {len(grouped[bid])} PC")
        rows=grouped[selected]
        st.dataframe([{'PC':r['asset_tag'],'Serial mainboard':r['board_serial'],
            'Thứ tự':f"{r['number']}/{r['quantity']}"} for r in rows],hide_index=True,width='stretch')
        width=st.number_input('Rộng tem (mm)',50,100,60,key='queue-width')
        height=st.number_input('Cao tem (mm)',35,100,40,key='queue-height')
        batch,records=ledger.label_batch_records(actor,selected)
        content=print_html_batch(records,key,int(width),int(height))
        st.caption('Mỗi PC in hai tem liền nhau theo thứ tự. In xong cả lô, đối chiếu số tem và xác nhận để KTV nhận.')
        components.html(content,height=230,scrolling=True)
        st.download_button('Tải lô tem (HTML)',content,'lo_tem_pc_vo_hop.html','text/html')
        if st.button('Xác nhận đã in xong toàn bộ lô',type='primary',key='confirm-print-'+selected):
            try:ledger.confirm_label_batch_printed(actor,selected,secrets.token_hex(16));st.success('Đã chuyển lô sang trạng thái đã in. KTV có thể nhận tem.');st.rerun()
            except DomainError as e:st.error(str(e))
        return
    data=ledger.preparation_rows(actor)
    if os.getenv('APP_MODE')=='shared_test':st.caption('Dữ liệu thử lưu chung trên máy chạy app. Điện thoại cùng mạng có thể tải ảnh QR; máy quét USB nhập vào hai ô mã. Camera trực tiếp trên web cần HTTPS.')
    if page=='Kế hoạch PC theo điểm':
        units=ledger.rows(actor,'units')
        if not units:st.info('Tạo đơn vị trước tại Đơn vị & tài khoản.');return
        with st.form('pc-plan'):
            unit=st.selectbox('Điểm / đơn vị',units,format_func=lambda r:f"{r.get('project_name') or r['project']} · {r['project']} · {r['name']}")
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
            st.dataframe([{'Điểm':r['unit'],'Mã máy':r['asset_tag'],'Serial mainboard':r['board_serial'],'Số thứ tự':r['number'],'Tổng PC kế hoạch':r['quantity']} for r in data],hide_index=True)
            buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['Dự án','Điểm','Mã máy','Serial mainboard','Thứ tự','Tổng PC','Trạng thái kiểm tra'])
            for r in data:
                values=[r['project'],r['unit'],r['asset_tag'],r['board_serial'],r['number'],r['quantity'],r['inspection_state'] or 'Chưa kiểm tra']
                writer.writerow(["'"+v if isinstance(v,str) and v[:1] in '=+-@\t\r' else v for v in values])
            st.download_button('Tải danh sách đối soát PC (CSV — mở bằng Excel)',buf.getvalue().encode('utf-8-sig'),'danh_sach_pc.csv','text/csv')
            device=st.selectbox('Máy cần cấp số thứ tự',[r for r in data if not r['number']],format_func=lambda r:r['asset_tag']) if any(not r['number'] for r in data) else None
            if device and st.button('Cấp số thứ tự máy'):
                try:ledger.number_device(actor,device['id'],secrets.token_hex(16));st.rerun()
                except DomainError as e:st.error(str(e))
        return
    if page=='Tem của tôi':
        existing=ledger.label_batches_for_ktv(actor)
        used={device_id for batch in existing for device_id in batch['device_ids']}
        ready=[r for r in data if r['number'] and r['activation_ready'] and r['id'] not in used]
        st.markdown('### Gửi PC đã kích hoạt vào hàng đợi chung')
        if ready:
            units={r['unit_id']:r['unit'] for r in ready}
            unit_id=st.selectbox('Đơn vị của lô',list(units),format_func=lambda uid:units[uid],key='queue-unit')
            devices=[r for r in ready if r['unit_id']==unit_id]
            chosen=st.multiselect('Chọn PC đã hoàn tất kích hoạt',devices,
                format_func=lambda r:f"{r['asset_tag']} · {r['number']}/{r['quantity']} · S/N {r['board_serial']}",
                key='queue-devices-'+unit_id)
            handwritten=st.checkbox('Đã ghi serial mainboard lên từng vỏ hộp tương ứng trước khi gửi lô.',key='queue-handwritten-'+unit_id)
            if st.button('Chuyển lô sang chờ in',type='primary',key='submit-queue-'+unit_id):
                if not handwritten:st.error('Ghi serial lên vỏ hộp trước khi gửi lô để đối chiếu tại trạm in.')
                else:
                    try:ledger.queue_label_batch(actor,unit_id,[r['id'] for r in chosen],secrets.token_hex(16));st.success('Đã gửi lô vào hàng đợi trạm in.');st.rerun()
                    except DomainError as e:st.error(str(e))
        else:st.info('Chưa có PC mới đủ điều kiện gửi tem. Hoàn tất kích hoạt và cấp số thứ tự trước.')
        st.markdown('### Lô tem của tôi')
        if not existing:st.info('Chưa có lô gửi hoặc in.')
        for batch in existing:
            names={r['id']:r['asset_tag'] for r in data}
            with st.container(border=True):
                state_name={'WAITING':'Đang chờ in','PRINTED':'Đã in · chờ KTV nhận','COLLECTED':'Đã nhận và đối chiếu'}.get(batch['state'],batch['state'])
                st.markdown(f"**{batch['project']} · {batch['unit']}** — {len(batch['device_ids'])} PC · trạng thái: **{state_name}**")
                st.write(', '.join(names.get(device_id,device_id) for device_id in batch['device_ids']))
                if batch['state']=='PRINTED':
                    checked=st.checkbox('Đã nhận đủ tem, đối chiếu từng serial với vỏ hộp, dán đúng PC/hộp và đóng lại.',key='collect-confirm-'+batch['id'])
                    if st.button('Xác nhận đã nhận và đối chiếu lô',key='collect-'+batch['id'],type='primary'):
                        if not checked:st.error('Cần đối chiếu serial và số tem của toàn bộ PC trong lô trước khi xác nhận.')
                        else:
                            try:ledger.confirm_label_batch_collected(actor,batch['id'],secrets.token_hex(16));st.rerun()
                            except DomainError as e:st.error(str(e))
        return
    if page=='In tem PC và vỏ hộp':
        if role=='KTV':st.error('KTV gửi tem theo lô tại “Tem của tôi”; chỉ trạm in dùng máy in USB.');return
        ready=[r for r in data if r['number'] and r['activation_ready']]
        if not ready:st.info('Cần cấp số máy tại Kế hoạch PC theo điểm và KTV báo kích hoạt thành công trước khi in tem.');return
        last_id=st.session_state.get('last-activated-device-'+actor) if role=='KTV' else None
        selected_index=next((i for i,r in enumerate(ready) if r['id']==last_id),0)
        record=st.selectbox('Máy in tem',ready,index=selected_index,
            format_func=lambda r:f"{r['unit']} · {r['asset_tag']} · {r['number']}/{r['quantity']}")
        if role=='KTV' and record['id']==last_id:
            st.success('Đang chọn đúng PC KTV vừa báo kích hoạt thành công. In cặp tem này trước khi chuyển sang PC khác.')
        width=st.number_input('Rộng tem (mm)',50,100,60)
        height=st.number_input('Cao tem (mm)',35,100,40)
        content=print_html(record,key,int(width),int(height))
        st.caption('Tải tệp, mở bằng trình duyệt trên PC rồi bấm In 2 tem. Chọn tỷ lệ 100%, tắt đầu/chân trang. In thử và quét kiểm tra trước in hàng loạt.')
        components.html(content,height=410,scrolling=True)
        st.download_button('Tải cặp tem để in (HTML)',content,'tem_pc_vo_hop.html','text/html')
        if role=='KTV':
            confirmed=st.checkbox('Tôi đã in, dán tem PC và tem hộp lên đúng cặp máy này, rồi đóng hộp.',key='ktv-label-confirm-'+record['id'])
            if st.button('Kết thúc PC này và đăng xuất',type='primary',key='ktv-finish-'+record['id']):
                if not confirmed:st.error('Xác nhận đã dán đủ cặp tem và đóng đúng hộp trước khi kết thúc.')
                else:
                    try:
                        ledger.confirm_labels_applied(actor,record['id'],secrets.token_hex(16))
                        st.logout()
                    except DomainError as e:st.error(str(e))
        with st.expander('Mã tem để thử đối chiếu khi chưa có máy in'):
            st.code(label_token(record,'PC',key),language=None)
            st.code(label_token(record,'BOX',key),language=None)
        return
    if is_demo:st.warning('Dữ liệu riêng từng phiên; để đội thử chung, dùng preview_app.py mới hoặc test_app.py.')
    notice=st.session_state.get('packing-notice')
    if notice and notice['actor']==actor:st.success(notice['text'])
    st.caption('Mỗi người chọn danh tính kiểm tra khác nhau. Chụp lần lượt hai tem QR, đối chiếu serial mainboard thực rồi gửi kết quả. Đây là đọc ảnh chụp QR, chưa phải camera quét liên tục.')
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
            st.success(f"ĐÚNG CẶP · {matched['unit']} · PC {matched['number']}/{matched['quantity']} · {matched['asset_tag']} · Serial mainboard {matched['serial']}")
        except DomainError as e:st.error(str(e))
    else:st.info('CHƯA ĐỦ ĐỐI CHIẾU: cần một tem thân máy và một tem vỏ hộp.')
    if st.button('Xóa hai mã / quét máy tiếp theo'):
        st.session_state['scan-round']=round_id+1
        st.rerun()
    if role!='QC' or not matched:return
    local=next((r for r in data if r['id']==matched['id']),None)
    if not local:
        st.error('Không có hồ sơ máy trong kho dữ liệu này. Kiểm tra đang mở đúng app và dùng đúng tem.');return
    if (local['asset_tag']!=matched['asset_tag'] or local['board_serial']!=matched['serial'] or
        any(local[k]!=matched[k] for k in ['unit','project','number','quantity'])):
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
        serial=st.text_input('Serial mainboard đọc trực tiếp trên PC')
        passed=st.radio('Kết quả kiểm tra kỹ thuật',['Đạt','Không đạt'],index=None)
        note=st.text_area('Nội dung kiểm tra / lỗi phát hiện')
        checked=st.checkbox('Đã đối chiếu serial mainboard thực và thực hiện kiểm tra kỹ thuật')
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
