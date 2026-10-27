import csv
import io
import os
import secrets
import uuid
import tempfile
from pathlib import Path
import streamlit as st
from cryptography.fernet import Fernet
from license_app.core import Ledger, DomainError
from license_app.demo import seed_demo
from license_app.guidance import ROLE_NAMES, PAGE_GUIDES, display_record
st.set_page_config(page_title='Bản quyền V2',page_icon='🛡️',layout='wide')
st.title('Quản lý bản quyền')
st.caption('V2-20261027-B · Bản xem thử có hướng dẫn theo vai trò')
LABELS={'RECEIVED':'Mới nhận','VERIFIED':'Đã kiểm tra','REDEEMED':'Đã redeem','ASSIGNED':'Đã giao máy','ACTIVATED':'Đã kích hoạt','WARRANTY_REVIEW':'Chờ xét bảo hành','PENDING':'Chờ kích hoạt','SUCCESS':'Thành công','FAILED':'Thất bại'}
@st.cache_resource
def connect(url,key,fp):return Ledger(url,key,fp)
if os.getenv('APP_MODE','production')=='demo':
    st.warning('DỮ LIỆU GIẢ · Chỉ nhập key thử. Mỗi phiên trình duyệt có dữ liệu minh họa riêng.')
    if 'config' not in st.session_state:
        demo_path=Path(tempfile.gettempdir()) / f'license-demo-{uuid.uuid4()}.db'
        st.session_state.config=('sqlite:///'+demo_path.as_posix(),Fernet.generate_key().decode(),secrets.token_urlsafe(48))
    ledger=connect(*st.session_state.config)
    seed_demo(ledger)
    demo_people={'admin@example.test':'Admin (quản trị) mẫu','vy@example.test':'Người redeem (quy đổi key) mẫu','ktv@example.test':'KTV (kỹ thuật viên) có việc','ktv2@example.test':'KTV khác — chưa có việc'}
    actor=st.sidebar.selectbox('Xem thử vai trò',list(demo_people),format_func=demo_people.get)
else:
    if os.getenv('APP_MODE','production')!='production':st.error('APP_MODE không hợp lệ.');st.stop()
    url,key,fp,admin=[os.getenv(x,'') for x in ['DATABASE_URL','LICENSE_ENCRYPTION_KEY','FINGERPRINT_KEY','BOOTSTRAP_ADMIN_EMAIL']]
    if not all([url,key,fp,admin]) or not url.startswith('postgresql+psycopg://'):
        st.error('Chưa cấu hình PostgreSQL và bí mật triển khai. Xem docs/DEPLOYMENT.md.');st.stop()
    if not st.user.is_logged_in:
        st.info('Đăng nhập tài khoản được Admin cấp quyền.')
        if st.button('Đăng nhập Google'):st.login()
        st.stop()
    if st.user.get('email_verified') is not True:st.error('Email chưa được xác minh.');st.stop()
    actor=st.user.get('email','').lower().strip()
    try:
        ledger=connect(url,key,fp);ledger.bootstrap(admin)
    except Exception:st.error('Không kết nối được kho dữ liệu. Liên hệ quản trị.');st.stop()
    if st.sidebar.button('Đăng xuất'):st.logout()
try:role=ledger.role(actor)
except DomainError as e:st.error(str(e));st.stop()
st.sidebar.caption(actor+' · '+ROLE_NAMES[role])
menus=['Việc của tôi'] if role=='KTV' else ['Tổng quan','Đơn vị & tài khoản','Kho key','Redeem Office','Thiết bị','Phân bổ','Kích hoạt','Bảo hành','Nhật ký']
if role=='ADMIN':menus.append('Người dùng')
menus.append('Hướng dẫn theo vai trò')
page=st.sidebar.radio('Chức năng',menus)
st.subheader(page)
if page in PAGE_GUIDES:
    title, steps=PAGE_GUIDES[page]
    with st.expander('Cách thực hiện: '+title):
        for index,step in enumerate(steps,1):st.write(f'{index}. {step}')
def rows(name):return ledger.rows(actor,name)
def table(data):
    if data:st.dataframe([display_record(r,LABELS) for r in data],hide_index=True,use_container_width=True)
    else:st.info('Chưa có hồ sơ.')
def pick(label,data,fmt):
    if not data:st.info('Chưa có lựa chọn phù hợp.');return None
    return st.selectbox(label,data,format_func=fmt)
def run(name,fn):
    token=st.session_state.setdefault('op-'+name,str(uuid.uuid4()))
    try:fn(token);st.session_state.pop('op-'+name,None);st.rerun()
    except DomainError as e:st.error(str(e))
    except Exception:st.error('Chưa xác nhận lưu thành công. Hãy kiểm tra kết nối và tải lại hồ sơ.')
def label(r):return f"{r['product']} · {r['sku']} · …{r['tail']} · {LABELS[r['state']]}"
if page=='Tổng quan':
    data=rows('licenses'); cols=st.columns(4)
    for col,title,n in zip(cols,['Đã nhận','Chưa phân bổ','Đã giao máy','Đã kích hoạt'],[len(data),sum(r['state'] in {'RECEIVED','VERIFIED','REDEEMED'} for r in data),sum(r['state']=='ASSIGNED' for r in data),sum(r['state']=='ACTIVATED' for r in data)]):col.metric(title,n)
    table(data)
    if data:
        st.bar_chart({LABELS[s]:sum(r['state']==s for r in data) for s in LABELS if any(r['state']==s for r in data)})
        buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(data[0]));writer.writeheader();writer.writerows([{k:("'"+v if isinstance(v,str) and v[:1] in {'=','+','-','@','\t','\r'} else v) for k,v in row.items()} for row in data])
        st.download_button('Tải báo cáo CSV',buf.getvalue().encode('utf-8-sig'),'bao_cao.csv','text/csv')
elif page=='Đơn vị & tài khoản':
    if role=='ADMIN':
        with st.form('unit'):
            project=st.text_input('Mã dự án');name=st.text_input('Tên đơn vị')
            if st.form_submit_button('Thêm đơn vị'):run('unit',lambda t:ledger.add_unit(actor,project,name,t))
    table(rows('units'))
    with st.form('account'):
        unit=pick('Đơn vị',rows('units'),lambda r:r['project']+' · '+r['name'])
        email=st.text_input('Email Microsoft');owner=st.text_input('Người quản lý tài khoản')
        st.caption('App không thu thập mật khẩu hoặc mã MFA.')
        if st.form_submit_button('Thêm tài khoản') and unit:run('account',lambda t:ledger.add_account(actor,unit['id'],email,owner,t))
    table(rows('accounts'))
elif page=='Kho key':
    if role=='ADMIN':
        with st.form('import',clear_on_submit=True):
            batch=st.text_input('Mã lô');product=st.selectbox('Phần mềm',['Office','Windows','Antivirus'])
            sku=st.text_input('Phiên bản / SKU');channel=st.selectbox('Kênh cấp phép',['Retail','OEM','Volume','Vendor'])
            route=st.selectbox('Luồng xử lý',['DIRECT','ACCOUNT_REDEEM'],format_func=lambda x:'Office Retail: redeem vào tài khoản' if x=='ACCOUNT_REDEEM' else 'Kích hoạt theo nhà cung cấp')
            expires=st.text_input('Ngày hết hạn nếu có (YYYY-MM-DD)');keys=st.text_area('Mỗi dòng một key; chỉ dùng key giả khi xem thử')
            if st.form_submit_button('Nhập kho'):run('import',lambda t:ledger.import_keys(actor,batch,product,sku,channel,route,keys.splitlines(),expires,t))
    data=rows('licenses');table(data)
    with st.form('verify'):
        lic=pick('Hồ sơ chờ kiểm tra',[r for r in data if r['state']=='RECEIVED'],label)
        ref=st.text_area('Căn cứ: chứng từ, phiên bản và điều kiện sử dụng')
        if st.form_submit_button('Xác nhận đã kiểm tra') and lic:run('verify',lambda t:ledger.verify(actor,lic['id'],ref,t))
elif page=='Redeem Office':
    lic=pick('Key đã kiểm tra',[r for r in rows('licenses') if r['route']=='ACCOUNT_REDEEM' and r['state']=='VERIFIED'],label)
    if lic:
        if st.button('Hiện key cho tác vụ này'):st.code(ledger.reveal(actor,lic['id']),language=None)
        st.link_button('Mở Microsoft để redeem','https://microsoft365.com/setup')
        with st.form('redeem'):
            account=pick('Tài khoản nhận sản phẩm',rows('accounts'),lambda r:r['email'])
            ref=st.text_input('Sản phẩm Microsoft xác nhận / mã tham chiếu')
            confirmed=st.checkbox('Đã thấy sản phẩm trong đúng tài khoản Microsoft')
            if st.form_submit_button('Ghi nhận redeem thành công') and account:
                if confirmed:run('redeem',lambda t:ledger.redeem(actor,lic['id'],account['id'],ref,t))
                else:st.error('Cần xác nhận kết quả tại Microsoft.')
    table([r for r in rows('licenses') if r['state']=='REDEEMED'])
elif page=='Thiết bị':
    st.download_button('Tải công cụ đọc serial PowerShell',Path('tools/Get-DeviceIdentity.ps1').read_bytes(),'Get-DeviceIdentity.ps1')
    st.caption('Công cụ đọc serial tại chỗ, không gửi dữ liệu lên mạng. Xem mã trước khi chạy.')
    with st.form('device'):
        unit=pick('Đơn vị nhận máy',rows('units'),lambda r:r['project']+' · '+r['name'])
        tag=st.text_input('Mã máy nội bộ');model=st.text_input('Hãng / model')
        serial=st.text_input('Serial máy / mã tem đã đối soát');board=st.text_input('Serial mainboard / mã đối soát vật lý')
        if st.form_submit_button('Thêm máy') and unit:run('device',lambda t:ledger.add_device(actor,unit['id'],tag,serial,board,model,t))
    table(rows('devices'))
elif page=='Phân bổ':
    if role!='ADMIN':st.info('Admin phân license và giao KTV.');st.stop()
    with st.form('assign'):
        lic=pick('License sẵn sàng',[r for r in rows('licenses') if r['state']=='REDEEMED' or (r['state']=='VERIFIED' and r['route']=='DIRECT')],label)
        device=pick('Máy nhận',rows('devices'),lambda r:r['asset_tag'])
        ktv=pick('KTV',[r for r in rows('users') if r['role']=='KTV' and r['active']],lambda r:r['email'])
        if st.form_submit_button('Phân bổ và giao việc') and lic and device and ktv:run('assign',lambda t:ledger.assign(actor,lic['id'],device['id'],ktv['email'],t))
    table(rows('jobs'))
elif page in ['Kích hoạt','Việc của tôi']:
    data=rows('jobs');table(data)
    if role=='OPERATOR':st.stop()
    with st.form('report'):
        job=pick('Việc cần báo cáo',[r for r in data if r['state'] in {'PENDING','FAILED'}],lambda r:r.get('asset_tag',r['device_id'])+' · '+r['id'][:8])
        success=st.radio('Kết quả',['Thành công','Thất bại'])=='Thành công'
        error=st.text_input('Mã lỗi nếu thất bại');note=st.text_area('Trạng thái đã kiểm tra / nội dung xử lý')
        evidence=st.text_input('Link HTTPS minh chứng (nếu có; không chứa key hoặc mật khẩu)')
        if st.form_submit_button('Gửi báo cáo') and job:run('report',lambda t:ledger.report(actor,job['id'],success,error,note,evidence,t))
elif page=='Bảo hành':
    table(rows('devices'))
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
    with st.form('user'):
        email=st.text_input('Email Google đã xác minh');new_role=st.selectbox('Quyền',['KTV','OPERATOR','ADMIN'],format_func=ROLE_NAMES.get)
        if st.form_submit_button('Cấp quyền'):run('user',lambda t:ledger.add_user(actor,email,new_role,t))
elif page=='Hướng dẫn theo vai trò':
    st.info('Hướng dẫn dự thảo cho chức năng hiện có. Cách vận hành chính thức sẽ cập nhật sau khi anh Vỹ chốt các mục góp ý.')
    sequences={
        'ADMIN':['Người dùng','Đơn vị & tài khoản','Kho key','Thiết bị','Phân bổ','Kích hoạt','Bảo hành','Nhật ký'],
        'OPERATOR':['Đơn vị & tài khoản','Kho key','Redeem Office','Kích hoạt','Nhật ký'],
        'KTV':['Việc của tôi'],
    }
    for name in sequences[role]:
        title,steps=PAGE_GUIDES[name]
        with st.expander(name+' — '+title,expanded=role=='KTV'):
            for index,step in enumerate(steps,1):st.write(f'{index}. {step}')
    st.caption('Chữ dùng trong app: Admin = quản trị; KTV = kỹ thuật viên; redeem = quy đổi key; license = giấy phép bản quyền; serial = số nhận dạng; SKU = mã phiên bản sản phẩm.')
