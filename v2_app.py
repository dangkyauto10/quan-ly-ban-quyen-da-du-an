            serial_ready=(st.session_state.get(f"board-bound-{actor}-{job['id']}")==str(job.get('board_serial') or '').strip().upper())
            if serial_ready:
                st.success(('Đã gắn serial giả ' if activation_demo else 'Đã đọc và gắn serial mainboard ')+job['board_serial']+' với PC / license đang chọn.')
            else:
                st.warning('Đọc serial trên chính PC này trước khi gửi báo cáo kích hoạt thành công.')
    else:
        job=pick('Việc cần báo cáo',pending,lambda r:r.get('asset_tag',r['device_id'])+' · '+r['id'][:8])
    if role!='KTV' or (job and st.session_state.get(f"board-bound-{actor}-{job['id']}")==str(job.get('board_serial') or '').strip().upper()):
      with st.form('report',clear_on_submit=True):
        result_choice=st.radio('Kết quả',['Thành công','Thất bại'],index=None)
        success=result_choice=='Thành công'
        error=st.text_input('Mã lỗi nếu thất bại');note=st.text_area('Trạng thái đã kiểm tra / nội dung xử lý')
        evidence=st.text_input('Link HTTPS minh chứng (nếu có; không chứa key hoặc mật khẩu)')
        if st.form_submit_button('Gửi báo cáo') and job:
            if result_choice is None:st.error('Chọn đúng kết quả sau khi đã kiểm tra trạng thái kích hoạt.')
            elif not note.strip():st.error('Anh/chị cần nhập nội dung đã kiểm tra / xử lý trước khi gửi báo cáo.')
            elif not success and not error.strip():st.error('Báo cáo thất bại cần có mã lỗi.')
            else:
                machine=job.get('asset_tag',job['device_id'])
                outcome='Thành công — công việc đã hoàn thành.' if success else 'Thất bại — công việc còn chờ xử lý.'
                run('report',lambda t:ledger.report(actor,job['id'],success,error,note,evidence,t),
                    f'Đã lưu báo cáo cho máy {machine}. Kết quả: {outcome} Đã ghi nhật ký.',
                    next_page='Tem của tôi' if role=='KTV' and success else None,
                    select_record=job['device_id'] if role=='KTV' and success else None)
      if role=='KTV':
        st.caption('Sau khi hoàn tất các PC của đơn vị, ghi serial lên vỏ hộp và gửi thành một lô tại “Tem của tôi”.')
elif page=='Bảo hành':
    st.caption('Tra lịch sử theo mã dự án, đơn vị, mã PC, serial máy hoặc serial mainboard hiện tại/cũ.')
    search=st.text_input('Từ khóa tra hồ sơ bảo hành')
    if search.strip():
        matches=ledger.device_dossier(actor,search)
        audit_rows=rows('audit')
        jobs_all=rows('jobs')
        licenses_all=rows('licenses')
        for device in matches:
            st.markdown(f"#### {device['asset_tag']} · {device['project']} · {device['unit']}")
            st.write(f"Serial máy: {device['serial']} · Serial mainboard hiện tại: {device['board_serial']} · {device['model']}")
            related_jobs=[j for j in jobs_all if j['device_id']==device['id']]
            license_ids={j['license_id'] for j in related_jobs}
            st.dataframe([{'KTV':j['ktv'],'Trạng thái':j['state'],'Lỗi':j.get('error_code') or '',
                'Báo cáo':j.get('note') or '', 'License':next((('…'+l['tail']) for l in licenses_all if l['id']==j['license_id']),'')}
                for j in related_jobs],hide_index=True,width='stretch')
            account_ids={l.get('account_id') for l in licenses_all if l['id'] in license_ids and l.get('account_id')}
            history=[a for a in audit_rows if a['entity']==device['id'] or any(a['entity']==j['id'] for j in related_jobs)
                or any(a['entity']==lid for lid in license_ids) or a['entity'] in account_ids]
            st.dataframe(history,hide_index=True,width='stretch')
            dossier={'device':device,'jobs':related_jobs,'license_summaries':[{'id':l['id'],'product':l['product'],'sku':l['sku'],'tail':l['tail'],'state':l['state']}
                for l in licenses_all if l['id'] in license_ids],'audit':history}
            st.download_button('Tải hồ sơ bảo hành JSON',json.dumps(dossier,ensure_ascii=False,indent=2),
                f"ho-so-{device['asset_tag']}.json",'application/json',key='dossier-'+device['id'])
    else:st.info('Nhập từ khóa để tra hồ sơ đã hoàn thành hoặc đang bảo hành.')
    if role!='ADMIN':st.info('Admin xác nhận thay mainboard và duyệt kích hoạt lại.');st.stop()
    with st.form('warranty'):
        device=pick('Máy thay mainboard',rows('devices'),lambda r:r['asset_tag'])
        board=st.text_input('Serial mainboard mới');reason=st.text_area('Căn cứ / nội dung bảo hành')
        if st.form_submit_button('Lưu thay mainboard') and device:run('warranty',lambda t:ledger.warranty(actor,device['id'],board,reason,t))
    with st.form('reactivate'):
        job=pick('Hồ sơ chờ duyệt',[r for r in rows('jobs') if r['state']=='WARRANTY_REVIEW'],lambda r:r['id'])
        ref=st.text_area('Căn cứ được phép kích hoạt lại / xác nhận nhà cung cấp')
        if st.form_submit_button('Duyệt và giao lại KTV') and job:run('reactivate',lambda t:ledger.approve_reactivation(actor,job['id'],ref,t))
elif page=='Nhật ký':table(rows('audit'))
elif page=='Người dùng':
    table(rows('users'))
    st.caption('Chỉ cấp quyền cho email Google đã xác minh. Thành viên mở web và đăng nhập Google; không cài Python.')
    existing=rows('users')
    left,right=st.columns(2)
    with left:
        with st.form('update-user'):
            person=pick('Thành viên cần cập nhật',existing,lambda r:r['email']+' · '+ROLE_NAMES[r['role']])
            role_choice=st.selectbox('Vai trò mới',['KTV','QC','OPERATOR','PRINT','ADMIN'],format_func=ROLE_NAMES.get)
            enabled=st.checkbox('Được phép sử dụng app',value=True)
            if st.form_submit_button('Lưu quyền thành viên') and person:
                run('update-user',lambda t:ledger.update_user(actor,person['email'],role_choice,enabled,t),
                    'Đã cập nhật quyền thành viên.')
    with right:
        with st.form('user'):
            email=st.text_input('Email Google đã xác minh');new_role=st.selectbox('Quyền',['KTV','QC','OPERATOR','PRINT','ADMIN'],format_func=ROLE_NAMES.get)
            if st.form_submit_button('Cấp quyền'):run('user',lambda t:ledger.add_user(actor,email,new_role,t))
elif page=='Hướng dẫn theo vai trò':
    st.info('Hướng dẫn thao tác theo vai trò trong luồng BẢN QUYỀN: nhận key, redeem phù hợp, giao KTV, kích hoạt, in tem, QC và theo dõi bảo hành.')
    sequences={
        'ADMIN':['Người dùng','Đơn vị & tài khoản','Kho key','Redeem Office','Thiết bị','Phân bổ','Kích hoạt','Bảo hành','Nhật ký'],
        'OPERATOR':['Đơn vị & tài khoản','Kho key','Kích hoạt','Nhật ký'],
        'KTV':['Việc của tôi'],
        'QC':[],
    }
    if role=='QC':st.info('Quét hai tem, đối chiếu serial thực, ghi kết quả kỹ thuật rồi xác nhận đóng gói. Người kiểm tra độc lập với KTV kích hoạt.')
    for name in sequences[role]:
        title,steps=PAGE_GUIDES[name]
        with st.expander(name+' — '+title,expanded=role=='KTV'):
            for index,step in enumerate(steps,1):st.write(f'{index}. {step}')
    st.caption('Chữ dùng trong app: Admin = quản trị; KTV = kỹ thuật viên; redeem = quy đổi key; license = giấy phép bản quyền; serial = số nhận dạng; SKU = mã phiên bản sản phẩm.')
elif page=='Đồng bộ Google Sheet':
    from license_app.sheet_sync import (make_snapshot, sync_with_service, build_sheets_service,
        configured_spreadsheet_id)
    st.write('Kế hoạch đầu vào được đọc từ tab 16_KE_HOACH_CAP_PC; báo cáo xử lý được ghi từ app sang các tab dữ liệu.')
    st.caption('Chỉ xuất key đã che. Mật khẩu, key gốc và nội dung kho mã hóa không được xuất.')
    snapshot=make_snapshot(ledger,actor,demo=os.getenv('APP_MODE') in {'demo','shared_test','team_test','activation_demo'} or activation_demo)
    st.write('Số bản ghi có thể xuất:',sum(len(r) for r in snapshot['tables'].values()))
    st.download_button('Tải bản dữ liệu để đối chiếu (JSON — tệp dữ liệu có cấu trúc)',
        __import__('json').dumps(snapshot,ensure_ascii=False,indent=2),'ban_quyen_dong_bo.json','application/json')
    target=configured_spreadsheet_id(st.secrets)
    st.link_button('Mở Google Sheet','https://docs.google.com/spreadsheets/d/'+target+'/edit')
    if os.getenv('APP_MODE') in {'demo','shared_test','team_test','activation_demo'} or activation_demo:
        st.info('Chế độ minh họa chỉ dùng dữ liệu giả và không đọc hoặc ghi Google Sheet dùng chung.')
    else:
        st.caption('Đích đồng bộ: '+target)
        if st.button('Đồng bộ báo cáo lên Google Sheet',type='primary'):
            try:
                count=sync_with_service(build_sheets_service(st.secrets),target,snapshot)
                st.success(f'Đã đồng bộ {count} bản ghi. Xem thời điểm tại tab 15_DONG_BO_APP.')
            except DomainError as err:st.error(str(err))
            except Exception:st.error('Chưa đồng bộ được. Kiểm tra Google Sheets API, danh tính chạy app và quyền Người chỉnh sửa trên đúng file Sheet. Dữ liệu app vẫn đã lưu; có thể đồng bộ lại.')

