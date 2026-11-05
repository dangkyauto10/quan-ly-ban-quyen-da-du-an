import csv
import io
import os
import secrets
import uuid
import tempfile
from pathlib import Path
import streamlit as st
from cryptography.fernet import Fernet
from license_app.core import DomainError
from license_app.packing import PackingLedger as Ledger
from license_app.demo import seed_demo
from license_app.guidance import ROLE_NAMES, PAGE_GUIDES, display_record
st.set_page_config(page_title='Bản quyền V2',page_icon='🛡️',layout='wide')
st.markdown('''<style>
:root {color-scheme:light;--ink:#13243b;--teal:#087f75;--mint:#dff6ef;--line:#dce5ef;--muted:#61738a;}
[data-testid="stAppViewContainer"] {background:radial-gradient(ellipse at 92% 0%,#eaf7f5 0,transparent 28%),#f4f7fb;}
.stApp {background:#f5f7fb;color:#18273d;}
.block-container {padding-top:4.5rem;max-width:1400px;padding-bottom:3rem;}
[data-testid="stSidebar"] {background:#edf2f8!important;border-right:1px solid #d8e2ed;}
[data-testid="stSidebar"] {color:#1b2d45;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label p,
[data-testid="stSidebar"] .side-brand {color:#1b2d45;}
[data-testid="stSidebar"] a {color:#087f75;}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
[data-testid="stSidebar"] button[kind="secondary"] {background:#fff;border:1px solid #cbd7e4;color:#1b2d45;}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] *,
[data-testid="stSidebar"] button[kind="secondary"] * {color:#1b2d45!important;}
[data-testid="stSidebar"] [data-baseweb="select"] {background:#fff;border-radius:9px;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#18273d!important;}
[data-testid="stSidebar"] [data-baseweb="select"] input {color:#18273d!important;-webkit-text-fill-color:#18273d!important;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#5c6d82;}
[data-testid="stSidebar"] [data-testid="stIconMaterial"] {color:#51657d;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:4px;}
[data-testid="stSidebar"] [role="radio"] {padding:8px 6px;border-radius:8px;}
[data-testid="stSidebar"] hr {border-color:#344359;}
h1,h2,h3, [data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3, [data-testid="stMain"] p {letter-spacing:-.015em;color:#14283f!important;}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p {color:#33465e!important;}
[data-testid="stMain"] label, [data-testid="stMain"] label p {color:#33465e!important;}
[data-testid="stMain"] input, [data-testid="stMain"] textarea {background:#fff!important;color:#18273d!important;border:1px solid #cbd7e4!important;border-radius:8px;}
[data-testid="stMainBlockContainer"] {max-width:1480px;}
header[data-testid="stHeader"] {background:rgba(244,247,251,.88);}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:1.2rem;}
.brand-lockup {display:flex;align-items:center;gap:11px;margin:0 0 20px;}
.brand-mark {width:37px;height:37px;border-radius:11px;background:#10263d;color:#8cf0d4;display:grid;place-items:center;font-size:18px;font-weight:800;box-shadow:0 5px 14px #10263d24;}
.brand-kicker {font-size:10px;letter-spacing:1.8px;font-weight:750;color:#087f75;margin:0 0 3px;}
.brand-note {color:#64748b;font-size:14px;margin:9px 0 25px;}
.side-brand-row {display:flex;align-items:center;gap:10px;margin:4px 0 3px;}
.side-mark {width:30px;height:30px;border:1px solid #47cdb5;border-radius:9px;color:#8cf0d4;display:grid;place-items:center;font-size:15px;font-weight:800;}
.side-brand {font-size:17px;font-weight:750;letter-spacing:.3px;margin:0;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) {background:#dff4ef;border:1px solid #a7ddd1;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) p {color:#075f58!important;font-weight:700;}
[data-testid="stSidebar"] [data-testid="stSelectbox"] {margin-top:2px;}
div[data-testid="stMetric"] {box-shadow:0 5px 18px #14283f08;}
.step-card {box-shadow:0 5px 18px #14283f08;}
.step-number {display:flex;align-items:center;gap:6px;}
.step-title {color:#14283f;}
.step-card:hover {border-color:#8bd7ca;transform:translateY(-2px);transition:all .18s ease;}
[data-testid="stSidebar"] {width:230px!important;}
div[data-testid="stMetric"] {background:white;border:1px solid #e1e7ef;border-radius:14px;padding:20px 22px;border-top:3px solid #13a394;}
[data-testid="stMetricLabel"] {color:#64748b;}
[data-testid="stMetricValue"] {color:#14283f;font-weight:700;}
[data-testid="stForm"] {background:#fff;border:1px solid #e1e7ef;border-radius:14px;padding:22px;}
[data-testid="stDataFrame"], [data-testid="stExpander"] {border-radius:12px;overflow:hidden;}
.stButton button,.stDownloadButton button,.stLinkButton a {border-radius:9px;min-height:42px;}
button[kind="primary"],button[kind="primaryFormSubmit"] {background:#087f75;border-color:#087f75;color:white;}
.brand-title {font-size:30px;font-weight:750;line-height:1.2;letter-spacing:-1px;margin:0;}
.side-note {font-size:12px;color:#9eafc6!important;margin-bottom:24px;}
.page-note {color:#64748b;margin-top:-10px;margin-bottom:24px;font-size:14px;}
.step-card {background:#fff;border:1px solid #e1e7ef;border-radius:12px;padding:16px;height:178px;box-sizing:border-box;margin-bottom:10px;}
.step-number {font-size:11px;color:#087f75;font-weight:750;letter-spacing:1px;}
.step-title {font-size:16px;font-weight:700;margin:7px 0;}
.step-note {font-size:13px;color:#64748b;line-height:1.5;}
@media(max-width:640px) {.block-container {padding:4rem 1rem 2rem;}.brand-title {font-size:25px;}[data-testid="stForm"] {padding:14px;}div[data-testid="stMetric"] {padding:14px;}.step-card {height:auto;min-height:130px;}}
</style>''',unsafe_allow_html=True)
st.markdown('<div class="brand-lockup"><div class="brand-mark">V⌗</div><div><div class="brand-kicker">V · LICENSE OPERATIONS</div><div style="font-size:12px;color:#61738a">Hệ thống quản lý bản quyền và thiết bị</div></div></div>',unsafe_allow_html=True)
st.title('Quản lý bản quyền')
st.markdown('<div class="brand-note">Quản lý tập trung · Theo dõi từng PC · Đối chiếu tem và đóng gói</div>',unsafe_allow_html=True)
st.sidebar.markdown('<div class="side-brand-row"><div class="side-mark">V⌗</div><div class="side-brand">BẢN QUYỀN</div></div><div class="side-note">ĐIỀU PHỐI THIẾT BỊ</div>',unsafe_allow_html=True)
LABELS={'RECEIVED':'Mới nhận','VERIFIED':'Đã kiểm tra','REDEEMED':'Đã redeem','ASSIGNED':'Đã giao máy','ACTIVATED':'Đã kích hoạt','WARRANTY_REVIEW':'Chờ xét bảo hành','PENDING':'Chờ kích hoạt','SUCCESS':'Thành công','FAILED':'Thất bại'}
@st.cache_resource
def connect(url,key,fp):return Ledger(url,key,fp)
if os.getenv('APP_MODE','production') in {'demo','shared_test','team_test'}:
    shared_test=os.getenv('APP_MODE') in {'shared_test','team_test'}
    st.warning('DỮ LIỆU GIẢ DÙNG CHUNG · Chọn danh tính thử, chưa phải đăng nhập thật. Chỉ thử nghiệp vụ; bản trực tuyến có thể mất dữ liệu/tem khi khởi động lại hoặc triển khai lại.' if shared_test else 'DỮ LIỆU GIẢ · Chỉ nhập key thử. Mỗi phiên trình duyệt có dữ liệu minh họa riêng.')
    if shared_test:
        from license_app.shared_test import shared_config
        st.session_state.config=shared_config()
    if 'config' not in st.session_state:
        demo_path=Path(tempfile.gettempdir()) / f'license-demo-{uuid.uuid4()}.db'
        st.session_state.config=('sqlite:///'+demo_path.as_posix(),Fernet.generate_key().decode(),secrets.token_urlsafe(48))
    ledger=connect(*st.session_state.config)
    if not shared_test:seed_demo(ledger)
    else:
        @st.cache_resource
        def seed_shared(url,key,fp):
            seed_demo(connect(url,key,fp))
            return True
        seed_shared(*st.session_state.config)
    demo_people={'admin@example.test':'Admin (quản trị) mẫu','vy@example.test':'Người redeem (quy đổi key) mẫu','ktv@example.test':'KTV (kỹ thuật viên) có việc','ktv2@example.test':'KTV khác — chưa có việc','qc@example.test':'Bộ phận kiểm tra độc lập mẫu'}
    demo_people.update({f'qc{n}@example.test':f'Người kiểm tra số {n} — mẫu' for n in range(2,7)})
    actor=st.sidebar.selectbox('Xem thử vai trò',list(demo_people),format_func=demo_people.get)
else:
    if os.getenv('APP_MODE','production')!='production':st.error('APP_MODE không hợp lệ.');st.stop()
    from license_app.web_config import load_web_settings,ConfigurationError
    try:
        try:deployment_secrets=st.secrets.to_dict()
        except FileNotFoundError:deployment_secrets={}
        settings=load_web_settings(deployment_secrets)
    except ConfigurationError as config_error:
        st.info('Bản web đang chờ quản trị kết nối đăng nhập và kho dữ liệu dùng chung. KTV không cần cài phần mềm.')
        st.error('Các mục cấu hình còn thiếu hoặc chưa hợp lệ:')
        for field in config_error.fields:
            st.text('• '+field)
        st.caption('Sửa các mục trên trong Settings → Secrets. Chỉ hiển thị tên mục; không hiển thị mật khẩu hay giá trị khóa.')
        st.stop()
    url,key,fp,admin=[settings[x] for x in ['DATABASE_URL','LICENSE_ENCRYPTION_KEY','FINGERPRINT_KEY','BOOTSTRAP_ADMIN_EMAIL']]
    if not st.user.is_logged_in:
        st.info('Đăng nhập tài khoản được Admin cấp quyền.')
        if st.button('Đăng nhập bằng Google',type='primary'):st.login()
        st.stop()
    if st.user.get('email_verified') is not True:st.error('Email chưa được xác minh.');st.stop()
    actor=st.user.get('email','').lower().strip()
    if st.sidebar.button('Đăng xuất'):st.logout()
    try:
        ledger=connect(url,key,fp);ledger.bootstrap(admin)
    except Exception:st.error('Không kết nối được kho dữ liệu. Liên hệ quản trị.');st.stop()
try:role=ledger.role(actor)
except DomainError:
    st.info('Tài khoản chưa được cấp quyền hoặc đã tạm dừng. Liên hệ Admin để được phân công.')
    st.stop()
st.sidebar.caption(actor+' · '+ROLE_NAMES[role])
menus=['Việc của tôi'] if role=='KTV' else ['Tổng quan','Đơn vị & tài khoản','Kho key','Redeem Office','Thiết bị','Phân bổ','Kích hoạt','Bảo hành','Nhật ký']
if role=='ADMIN':menus.extend(['Người dùng','Đồng bộ Google Sheet'])
if role=='QC':menus=['Đối chiếu tem và kiểm tra']
elif role=='ADMIN':menus.extend(['Kế hoạch PC theo điểm','In tem PC và vỏ hộp','Đối chiếu tem và kiểm tra'])
elif role=='KTV':menus.extend(['In tem PC và vỏ hộp','Đối chiếu tem và kiểm tra'])
if role=='OPERATOR':menus=[name for name in menus if name!='Redeem Office']
menus.append('Hướng dẫn theo vai trò')
groups={
    'Tổng quan':['Tổng quan'],
    '01 · Chuẩn bị & bản quyền':['Đơn vị & tài khoản','Kế hoạch PC theo điểm','Kho key','Redeem Office'],
    '02 · Giao việc & kích hoạt':['Thiết bị','Phân bổ','Kích hoạt','Việc của tôi'],
    '03 · Tem QR & kiểm tra':['In tem PC và vỏ hộp','Đối chiếu tem và kiểm tra'],
    '04 · Bảo hành & lịch sử':['Bảo hành','Nhật ký'],
    'Quản trị':['Người dùng','Đồng bộ Google Sheet'],
    'Hướng dẫn':['Hướng dẫn theo vai trò'],
}
groups={name:[item for item in items if item in menus] for name,items in groups.items()}
groups={name:items for name,items in groups.items() if items}
st.sidebar.divider()
section=st.sidebar.selectbox('Nhóm công việc',list(groups),key='nav-section')
page=st.sidebar.radio('Chức năng',groups[section],key='nav-page-'+section)
st.sidebar.divider()
st.sidebar.caption('V2 · Giao diện sáng · 05/11/2026')
st.subheader(page)
page_notes={
    'Tổng quan':'Theo dõi kho bản quyền và chọn bước tiếp theo trong quy trình.',
    'Đơn vị & tài khoản':'Khai báo nơi nhận PC và tài khoản Microsoft quản lý sản phẩm.',
    'Kế hoạch PC theo điểm':'Chốt số lượng PC theo từng đơn vị để đánh số và giao nhận.',
    'Kho key':'Nhập lô key, kiểm tra chứng từ và theo dõi trạng thái bản quyền.',
    'Redeem Office':'Admin redeem tại Microsoft rồi ghi nhận tài khoản nhận sản phẩm.',
    'Thiết bị':'Khai báo mã PC và serial để đối chiếu xuyên suốt quá trình.',
    'Phân bổ':'Chọn bản quyền, máy nhận và KTV chịu trách nhiệm.',
    'In tem PC và vỏ hộp':'Tạo hai tem cho cùng một PC sau khi kích hoạt thành công.',
    'Đối chiếu tem và kiểm tra':'Quét tem PC và hộp, kiểm tra thiết bị rồi xác nhận đóng gói.',
    'Người dùng':'Cấp quyền theo nhiệm vụ cho từng tài khoản Google.',
}
if page in page_notes:st.markdown('<div class="page-note">'+page_notes[page]+'</div>',unsafe_allow_html=True)
if page=='Người dùng':
    notice=st.session_state.get('report-confirmation')
    if notice and notice[0]==actor:st.success(notice[1])
if page in PAGE_GUIDES:
    title, steps=PAGE_GUIDES[page]
    with st.expander('Cách thực hiện: '+title):
        for index,step in enumerate(steps,1):st.write(f'{index}. {step}')
def rows(name):return ledger.rows(actor,name)
def table(data):
    if data:st.dataframe([display_record(r,LABELS) for r in data],hide_index=True,width='stretch')
    else:st.info('Chưa có hồ sơ.')
def pick(label,data,fmt):
    if not data:st.info('Chưa có lựa chọn phù hợp.');return None
    return st.selectbox(label,data,format_func=fmt)
def run(name,fn,confirmation=None):
    token=st.session_state.setdefault('op-'+name,str(uuid.uuid4()))
    try:
        fn(token)
        st.session_state.pop('op-'+name,None)
        if confirmation:st.session_state['report-confirmation']=(actor,confirmation)
        st.rerun()
    except DomainError as e:st.error(str(e))
    except Exception:st.error('Chưa xác nhận lưu thành công. Hãy kiểm tra kết nối và tải lại hồ sơ.')
def label(r):return f"{r['product']} · {r['sku']} · …{r['tail']} · {LABELS[r['state']]}"
if page in {'Kế hoạch PC theo điểm','In tem PC và vỏ hộp','Đối chiếu tem và kiểm tra'}:
    from license_app.preparation_ui import render
    render(ledger,actor,role,page,os.getenv('APP_MODE')=='demo')
elif page=='Tổng quan':
    data=rows('licenses'); cols=st.columns(4)
    for col,title,n in zip(cols,['Đã nhận','Chưa phân bổ','Đã giao máy','Đã kích hoạt'],[len(data),sum(r['state'] in {'RECEIVED','VERIFIED','REDEEMED'} for r in data),sum(r['state']=='ASSIGNED' for r in data),sum(r['state']=='ACTIVATED' for r in data)]):col.metric(title,n)
    st.markdown('### Luồng xử lý bản quyền')
    steps=[('01','Chuẩn bị','Đơn vị, số lượng PC, key và tài khoản.','Đơn vị & tài khoản'),('02','Redeem & giao việc','Admin ghi nhận redeem và phân công KTV.','Phân bổ'),('03','Kích hoạt · in tem QR','KTV báo kết quả; in tem PC và vỏ hộp theo số thứ tự.','Kích hoạt'),('04','Quét · kiểm tra · đóng gói','QC đối chiếu cặp QR, đơn vị và số lượng thiết bị.','Đối chiếu tem và kiểm tra')]
    def open_page(target):
        for group,items in groups.items():
            if target in items:
                st.session_state['nav-section']=group
                st.session_state['nav-page-'+group]=target
                return
    for col,(number,title,note,target) in zip(st.columns(4),steps):
        with col:
            st.markdown(f'<div class="step-card"><div class="step-number">BƯỚC {number}</div><div class="step-title">{title}</div><div class="step-note">{note}</div></div>',unsafe_allow_html=True)
            if target in menus:st.button({'01':'Chuẩn bị','02':'Giao việc','03':'Kích hoạt','04':'Kiểm tra'}[number]+' →',key='shortcut-'+number,on_click=open_page,args=(target,),use_container_width=True)
    st.markdown('### Danh sách bản quyền')
    if not data:st.info('Kho dữ liệu mới chưa có bản quyền. Bắt đầu từ bước 01: thêm đơn vị và tài khoản, sau đó nhập lô key thử nghiệm.')
    else:table(data)
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
    if role!='ADMIN':st.error('Chỉ Admin thực hiện redeem và xem key gốc.');st.stop()
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
    notice=st.session_state.get('report-confirmation')
    if notice and notice[0]==actor:st.success(notice[1])
    pending=[r for r in data if r['state'] in {'PENDING','FAILED'}]
    if not pending:
        st.info('Không còn công việc chờ báo cáo. Các hồ sơ đã xử lý nằm trong bảng phía trên.')
        st.stop()
    with st.form('report',clear_on_submit=True):
        job=pick('Việc cần báo cáo',pending,lambda r:r.get('asset_tag',r['device_id'])+' · '+r['id'][:8])
        success=st.radio('Kết quả',['Thành công','Thất bại'])=='Thành công'
        error=st.text_input('Mã lỗi nếu thất bại');note=st.text_area('Trạng thái đã kiểm tra / nội dung xử lý')
        evidence=st.text_input('Link HTTPS minh chứng (nếu có; không chứa key hoặc mật khẩu)')
        if st.form_submit_button('Gửi báo cáo') and job:
            if not note.strip():st.error('Anh/chị cần nhập nội dung đã kiểm tra / xử lý trước khi gửi báo cáo.')
            elif not success and not error.strip():st.error('Báo cáo thất bại cần có mã lỗi.')
            else:
                machine=job.get('asset_tag',job['device_id'])
                outcome='Thành công — công việc đã hoàn thành.' if success else 'Thất bại — công việc còn chờ xử lý.'
                run('report',lambda t:ledger.report(actor,job['id'],success,error,note,evidence,t),
                    f'Đã lưu báo cáo cho máy {machine}. Kết quả: {outcome} Đã ghi nhật ký.')
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
    st.caption('Chỉ cấp quyền cho email Google đã xác minh. Thành viên mở web và đăng nhập Google; không cài Python.')
    existing=rows('users')
    with st.form('update-user'):
        person=pick('Thành viên cần cập nhật',existing,lambda r:r['email']+' · '+ROLE_NAMES[r['role']])
        role_choice=st.selectbox('Vai trò mới',['KTV','QC','OPERATOR','ADMIN'],format_func=ROLE_NAMES.get)
        enabled=st.checkbox('Được phép sử dụng app',value=True)
        if st.form_submit_button('Lưu quyền thành viên') and person:
            run('update-user',lambda t:ledger.update_user(actor,person['email'],role_choice,enabled,t),
                'Đã cập nhật quyền thành viên.')
    with st.form('user'):
        email=st.text_input('Email Google đã xác minh');new_role=st.selectbox('Quyền',['KTV','QC','OPERATOR','ADMIN'],format_func=ROLE_NAMES.get)
        if st.form_submit_button('Cấp quyền'):run('user',lambda t:ledger.add_user(actor,email,new_role,t))
elif page=='Hướng dẫn theo vai trò':
    st.info('Hướng dẫn dự thảo cho chức năng hiện có. Cách vận hành chính thức sẽ cập nhật sau khi anh Vỹ chốt các mục góp ý.')
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
    from license_app.sheet_sync import make_snapshot, sync_with_service, SHEET_ID
    st.write('Đồng bộ một chiều app → các tab dữ liệu. Dòng có mã bắt đầu APP- do app cập nhật; ghi ý kiến ở tab 14_V_GOP_Y.')
    st.caption('Chỉ xuất key đã che. Mật khẩu, key gốc và nội dung kho mã hóa không được xuất.')
    snapshot=make_snapshot(ledger,actor,demo=os.getenv('APP_MODE') in {'demo','shared_test','team_test'})
    st.write('Số bản ghi có thể xuất:',sum(len(r) for r in snapshot['tables'].values()))
    st.download_button('Tải bản dữ liệu để đối chiếu (JSON — tệp dữ liệu có cấu trúc)',
        __import__('json').dumps(snapshot,ensure_ascii=False,indent=2),'ban_quyen_dong_bo.json','application/json')
    st.link_button('Mở Google Sheet nghiên cứu','https://docs.google.com/spreadsheets/d/'+SHEET_ID+'/edit')
    if os.getenv('APP_MODE') in {'demo','shared_test','team_test'}:
        st.info('Phiên demo cá nhân chỉ cho xem/xuất dữ liệu giả. Bản minh họa dùng chung được B ghi riêng vào Sheet để anh Vỹ nghiên cứu.')
    else:
        cfg=st.secrets.get('google_sheets',{})
        target=cfg.get('spreadsheet_id',SHEET_ID)
        st.caption('Đích đồng bộ: '+target)
        if st.button('Đồng bộ báo cáo lên Google Sheet',type='primary'):
            try:
                import google.auth
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
                scopes=['https://www.googleapis.com/auth/spreadsheets']
                info=st.secrets.get('google_service_account')
                credentials=Credentials.from_service_account_info(dict(info),scopes=scopes) if info else google.auth.default(scopes=scopes)[0]
                count=sync_with_service(build('sheets','v4',credentials=credentials,cache_discovery=False),target,snapshot)
                st.success(f'Đã đồng bộ {count} bản ghi. Xem thời điểm tại tab 15_DONG_BO_APP.')
            except DomainError as err:st.error(str(err))
            except Exception:st.error('Chưa đồng bộ được. Kiểm tra Google Sheets API, danh tính chạy app và quyền Người chỉnh sửa trên đúng file Sheet. Dữ liệu app vẫn đã lưu; có thể đồng bộ lại.')
