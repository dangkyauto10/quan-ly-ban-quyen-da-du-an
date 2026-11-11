import secrets
import os
import hashlib
import csv
import io
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from .core import DomainError
from .labels import label_token,print_html,print_html_batch,compare_labels

live_qr_scanner=components.declare_component(
    'license_live_qr_scanner',path=str(Path(__file__).parent/'qr_scanner'))

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
        points=ledger.rows(actor,'receiving_points')
        if not points:st.info('Chưa có điểm nhận. Nạp danh sách đơn vị, xã/phường và số lượng tại Đơn vị & tài khoản.');return
        st.caption('Số PC theo từng điểm được lấy từ danh sách phân bổ. Số tem PC được đánh liên tục trong phạm vi đơn vị được cấp.')
        point_rows=[]
        for point in points:
            unit=next((u for u in units if u['id']==point['unit_id']),None)
            devices_at=[r for r in data if r.get('point_code')==point['code'] and r['unit_id']==point['unit_id']]
            point_rows.append({'Mã dự án':unit['project'] if unit else '',
                'Đơn vị được cấp':unit['name'] if unit else '', 'Mã điểm':point['code'],
                'Xã/phường/điểm':point['name'],'PC phân bổ':point['pc_quantity'],
                'Đã khai báo PC':len(devices_at),'Đã đánh số':sum(bool(r['number']) for r in devices_at),
                'Đã QC/đóng gói':sum(r['inspection_state']=='PACKED' for r in devices_at)})
        st.dataframe(point_rows,hide_index=True,width='stretch')
        if data:
            st.markdown('### Danh sách PC')
            st.dataframe([{'Đơn vị được cấp':r['unit'],'Xã/phường/điểm':r.get('point') or 'Chưa gán điểm',
                'Mã máy':r['asset_tag'],'Serial mainboard':r['board_serial'],
                'Số tem':f"{r['number']}/{r['quantity']}" if r['number'] else 'Chưa đánh số',
                'Trạng thái kiểm tra':r['inspection_state'] or 'Chưa kiểm tra'} for r in data],hide_index=True,width='stretch')
            buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['Mã dự án','Đơn vị được cấp','Mã điểm','Xã/phường/điểm','Mã máy','Serial mainboard','Thứ tự','Tổng PC','Trạng thái kiểm tra'])
            for r in data:
                values=[r['project'],r['unit'],r.get('point_code') or '',r.get('point') or '',r['asset_tag'],r['board_serial'],r['number'],r['quantity'],r['inspection_state'] or 'Chưa kiểm tra']
                writer.writerow(["'"+v if isinstance(v,str) and v[:1] in '=+-@\t\r' else v for v in values])
            st.download_button('Tải danh sách đối soát PC (CSV — mở bằng Excel)',buf.getvalue().encode('utf-8-sig'),'danh_sach_pc.csv','text/csv')
            unnumbered=[r for r in data if not r['number']]
            device=st.selectbox('PC cần đánh số tem',unnumbered,format_func=lambda r:f"{r['unit']} · {r.get('point') or 'Chưa gán điểm'} · {r['asset_tag']}") if unnumbered else None
            if device and st.button('Cấp số thứ tự tem'):
                try:ledger.number_device(actor,device['id'],secrets.token_hex(16));st.rerun()
                except DomainError as e:st.error(str(e))
        return
    if page=='Tem của tôi':
        existing=ledger.label_batches_for_ktv(actor)
        inflight={device_id for batch in existing if batch['state'] in {'WAITING','PRINTED'} for device_id in batch['device_ids']}
        ready=[r for r in data if r['number'] and r['activation_ready'] and r['id'] not in inflight
            and r.get('ktv_completion_state')!='QC_PASSED']
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
        latest_collected={}
        for batch in existing:
            if batch['state']=='COLLECTED':
                for device_id in batch['device_ids']:
                    old=latest_collected.get(device_id)
                    if old is None or (batch.get('collected_at') or batch['created_at'])>(old.get('collected_at') or old['created_at']):
                        latest_collected[device_id]=batch
        for batch in existing:
            names={r['id']:r['asset_tag'] for r in data}
            with st.container(border=True):
                state_name={'WAITING':'Đang chờ in','PRINTED':'Đã in · chờ KTV nhận','COLLECTED':'Đã nhận và đối chiếu'}.get(batch['state'],batch['state'])
                st.markdown(f"**{batch['project']} · {batch['unit']}** — {len(batch['device_ids'])} PC · trạng thái: **{state_name}**")
                st.write(', '.join(names.get(device_id,device_id) for device_id in batch['device_ids']))
                if batch['state']=='PRINTED':
                    checked=st.checkbox('Đã nhận đủ cặp tem của lô từ trạm in.',key='collect-confirm-'+batch['id'])
                    if st.button('Xác nhận đã nhận tem',key='collect-'+batch['id'],type='primary'):
                        if not checked:st.error('Xác nhận số tem nhận được trước khi chuyển sang đối chiếu từng PC.')
                        else:
                            try:ledger.confirm_label_batch_collected(actor,batch['id'],secrets.token_hex(16));st.rerun()
                            except DomainError as e:st.error(str(e))
                if batch['state']=='COLLECTED':
                    st.markdown('**Đối chiếu, dán tem và đóng hộp theo từng PC**')
                    for device_id in batch['device_ids']:
                        record=next((r for r in data if r['id']==device_id),None)
                        if not record:continue
                        state=record.get('ktv_completion_state') or ''
                        if state=='QC_PASSED':
                            st.success(f"{record['asset_tag']} · {record['number']}/{record['quantity']} — đã QC đạt")
                            continue
                        if state=='READY_QC':
                            st.info(f"{record['asset_tag']} · đã bàn giao QC, chờ kết quả.")
                            continue
                        if latest_collected.get(device_id,{}).get('id')!=batch['id']:
                            st.caption(f"{record['asset_tag']} · cặp tem thuộc lô cũ; dùng lô in lại mới nhất để xác nhận.")
                            continue
                        with st.form('pc-close-'+device_id):
                            st.write(f"{record['asset_tag']} · {record['number']}/{record['quantity']} · đơn vị {record['unit']}")
                            serial=st.text_input('Nhập lại serial mainboard trên PC/hộp',value=record['board_serial'],key='close-serial-'+device_id)
                            applied=st.checkbox('Hai tem thuộc đúng cặp serial này đã dán lên thân máy và hộp; PC đã đóng hộp.',key='close-confirm-'+device_id)
                            note=st.text_input('Ghi chú bàn giao cho QC (nếu có)',key='close-note-'+device_id)
                            if st.form_submit_button('Xác nhận hoàn tất PC, chuyển QC'):
                                if not applied:st.error('Cần xác nhận đã dán đúng cặp tem và đóng hộp.')
                                else:
                                    try:ledger.confirm_labels_applied(actor,device_id,serial,note or 'Đã đối chiếu cặp tem và đóng hộp.',secrets.token_hex(16));st.success('Đã chuyển riêng PC này sang QC.');st.rerun()
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
            st.info('KTV nhận tem theo hàng đợi chung và xác nhận từng PC tại “Tem của tôi”.')
        with st.expander('Mã tem để thử đối chiếu khi chưa có máy in'):
            st.code(label_token(record,'PC',key),language=None)
            st.code(label_token(record,'BOX',key),language=None)
        return
    if is_demo:st.warning('Dữ liệu riêng từng phiên; để đội thử chung, dùng preview_app.py mới hoặc test_app.py.')
    notice=st.session_state.get('packing-notice')
    if notice and notice['actor']==actor:st.success(notice['text'])
    st.caption('Bên thứ ba quét QR trên thân máy và hộp vỏ. Nếu đúng cặp và khớp hồ sơ, app tự ghi nhận QC hoàn tất.')
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
    titles=['Tem THÂN MÁY','Tem VỎ HỘP']
    token_keys=[f'scan-text-{round_id}-{i}' for i in range(2)]
    tokens=[st.session_state.get(k,'') for k in token_keys]
    next_index=next((i for i,value in enumerate(tokens) if not value),None)
    if next_index is not None:
        title=titles[next_index]
        st.subheader(title)
        st.caption('Đưa camera sau vào gần mã QR. App đọc trực tiếp từ hình ảnh đang xem trước; không chụp, tải lên hoặc lưu ảnh.')
        scan_id=f'{round_id}-{next_index}'
        result=live_qr_scanner(scan_id=scan_id,label=title,default=None,
            key=f'live-qr-{round_id}',height=300)
        if isinstance(result,dict) and result.get('scan_id')==scan_id and result.get('text'):
            st.session_state[token_keys[next_index]]=result['text']
            st.rerun()
        if next_index==1 and tokens[0]:
            st.success('Đã đọc QR tem THÂN MÁY. Tiếp tục quét tem VỎ HỘP.')
    else:
        st.success('Đã đọc đủ hai mã QR. Đang đối chiếu cặp tem.')
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
    if role not in {'QC','KTV'} or not matched:return
    local=next((r for r in data if r['id']==matched['id']),None)
    if not local:
        st.error('Không có hồ sơ máy trong kho dữ liệu này. Kiểm tra đang mở đúng app và dùng đúng tem.');return
    if (local['asset_tag']!=matched['asset_tag'] or local['board_serial']!=matched['serial'] or
        any(local[k]!=matched[k] for k in ['unit','project','number','quantity'])):
        st.error('Tem đã cũ so với hồ sơ. Cần in lại cả cặp tem.');return
    if local['inspection_state']=='PACKED':
        st.success('PC này đã xác nhận đúng cặp tem và hoàn tất đóng gói. Chuyển sang máy tiếp theo.');return
    operation=st.session_state.setdefault(f'pack-op-{actor}-{round_id}',secrets.token_hex(16))
    if role=='KTV':
        st.info('Quét độc lập trên điện thoại sau khi bên thứ ba đã kiểm tra PC; không cần quay lại các bước kích hoạt.')
        external_qc=st.checkbox('Bên thứ ba đã kiểm tra PC và cho phép đóng gói.',key=f'external-qc-{round_id}')
        if st.button('Xác nhận cặp tem khớp và hoàn tất đóng gói',type='primary',key=f'final-pack-{round_id}'):
            if not external_qc:
                st.error('Cần xác nhận bên thứ ba đã kiểm tra trước khi đóng gói.')
            else:
                try:
                    ledger.confirm_paired_labels(actor,*tokens,key,operation,external_qc_passed=True)
                    st.session_state['packing-notice']={'actor':actor,
                        'text':f"Đã quét đúng cặp tem cho {local['asset_tag']} · {local['unit']} sau khi bên thứ ba kiểm tra; hoàn tất đóng gói."}
                    st.session_state['scan-round']=round_id+1
                    st.rerun()
                except DomainError as e:st.error(str(e))
                except Exception:st.error('Chưa ghi nhận đối chiếu. Giữ nguyên hai mã và thử lại.')
        return
    try:
        ledger.confirm_paired_labels(actor,*tokens,key,operation)
        st.session_state['packing-notice']={'actor':actor,
            'text':f"Đã quét đúng cặp tem cho {local['asset_tag']} · {local['unit']}. QC HOÀN TẤT; có thể niêm phong hộp."}
        st.session_state['scan-round']=round_id+1
        st.rerun()
    except DomainError as e:st.error(str(e))
    except Exception:st.error('Chưa ghi nhận QC. Giữ nguyên hai mã và không niêm phong hộp khi chưa có xác nhận.')

