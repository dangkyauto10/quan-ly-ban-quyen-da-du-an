import csv
import hashlib
import json
import base64
import io
import os
import secrets
import uuid
import tempfile
import zipfile
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet
from license_app.core import DomainError
from license_app.packing import PackingLedger as Ledger
from license_app.demo import seed_demo
from license_app.guidance import ROLE_NAMES, PAGE_GUIDES, display_record
st.set_page_config(page_title='KEY BẢN QUYỀN',page_icon='assets/key-ban-quyen-icon.svg',layout='wide')
board_serial_reader = components.declare_component(
    'board_serial_reader', path=str(Path(__file__).parent / 'license_app' / 'serial_reader'))
logo_data=base64.b64encode(Path('assets/key-ban-quyen-icon.svg').read_bytes()).decode('ascii')
logo_src='data:image/svg+xml;base64,'+logo_data
hero_photo_src='data:image/webp;base64,'+base64.b64encode(Path('assets/hero-tech-operations.webp').read_bytes()).decode('ascii')
st.markdown('''<style>
:root {color-scheme:light;--ink:#13243b;--teal:#9a6a00;--mint:#fff2c7;--line:#dce5ef;--muted:#61738a;}
[data-testid="stAppViewContainer"] {background:radial-gradient(ellipse at 92% 0%,#fff0c2 0,transparent 24%),#f2f5fa;}
.stApp {background:#f2f5fa;color:#17263d;}
.block-container {padding:2.2rem clamp(1.25rem,3vw,3.5rem) 3rem;max-width:none;width:100%;}
[data-testid="stSidebar"] {background:#edf2f8!important;border-right:0!important;}
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
[data-testid="stMain"] h1 {text-align:center!important;font-size:46px!important;font-weight:800!important;letter-spacing:.02em!important;text-transform:uppercase;margin:0 auto 12px!important;}
.hero-tech {position:relative;isolation:isolate;overflow:hidden;min-height:260px;border-radius:24px;border:0;margin:0 0 30px;padding:28px 30px 25px;background-image:linear-gradient(90deg,#07132644 0%,#07132630 30%,#07132636 70%,#07132644 100%),var(--hero-photo);background-size:cover;background-position:center 53%;box-shadow:0 18px 42px #10243a2b;color:#fff;text-align:center;}
.hero-content {position:relative;z-index:1;max-width:680px;margin:0 auto;text-align:center;padding:4px 16px 2px;border-radius:24px;background:radial-gradient(ellipse at center,#061529c9 0%,#061529a6 52%,transparent 100%);}
.hero-lockup {display:flex;align-items:center;justify-content:center;gap:13px;margin:0 auto 6px;}
.hero-logo {width:44px;height:44px;object-fit:contain;filter:drop-shadow(0 3px 10px #020b18aa);}
.hero-name {color:#f2c755;font-size:15px;font-weight:800;letter-spacing:2px;text-align:left;margin-bottom:3px;}
.hero-sub {color:#d4e2f2;font-size:13px;text-align:left;}
.hero-tech h1 {position:relative;z-index:1;color:#fff!important;font-size:39px!important;line-height:1.14!important;font-weight:850!important;letter-spacing:.015em!important;margin:9px auto 10px!important;text-shadow:0 3px 22px #020b18c9;max-width:650px;}
.hero-note {position:relative;z-index:1;color:#e3edfa;font-size:14px;font-weight:550;text-shadow:0 2px 12px #020b18;}
.process-breadcrumb {display:flex;gap:10px;align-items:center;justify-content:space-between;padding:12px 14px;margin:0 0 18px;border-radius:16px;background:linear-gradient(110deg,#e7eff8,#f5f8fc);box-shadow:inset 0 1px #fff,0 8px 20px #14283f0a;}
.process-phase {flex:1;display:flex;align-items:center;gap:9px;min-width:0;padding:8px 11px;border-radius:12px;color:#65768a;font-size:13px;font-weight:650;background:#ffffff75;}
.process-phase.active {color:#102a46;background:linear-gradient(140deg,#fff,#edf8ff);box-shadow:0 7px 15px #10243a1a,0 0 0 1px #acd3ed;}
.process-phase.prior {color:#65768a;background:#eef3f8;}
.process-phase b {display:grid;place-items:center;flex:0 0 27px;height:27px;border-radius:9px;background:#dce6f0;color:#34506d;font-size:11px;}
.process-phase.active b {background:#163957;color:#fff;}
.process-phase.prior b {background:#e0e8f0;color:#52677d;}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p {color:#33465e!important;font-size:17px;line-height:1.65;}
[data-testid="stMain"] label, [data-testid="stMain"] label p {color:#33465e!important;font-size:15px!important;}
[data-testid="stMain"] input, [data-testid="stMain"] textarea {background:#fff!important;color:#18273d!important;border:1px solid #cbd7e4!important;border-radius:8px;}
[data-testid="stMainBlockContainer"] {max-width:none;width:100%;}
[data-testid="stSidebar"] {width:215px!important;}
[data-testid="stSidebar"] label p,[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {font-size:14px!important;}
[data-testid="stCaptionContainer"] p {font-size:15px!important;color:#52657b!important;line-height:1.5;}
[data-testid="stMetricLabel"] {font-size:14px!important;}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div {font-size:34px!important;font-weight:750!important;color:#14283f!important;}
[data-testid="stExpander"] summary {font-size:15px!important;}
header[data-testid="stHeader"] {background:rgba(244,247,251,.88);}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:1.2rem;}
.brand-lockup {display:flex;align-items:center;justify-content:center;gap:18px;margin:8px 0 28px;text-align:left;}
.brand-mark {width:72px;height:72px;display:grid;place-items:center;overflow:hidden;flex:0 0 72px;}
.brand-mark img {width:100%;height:100%;object-fit:contain;}
.brand-kicker {font-size:17px;letter-spacing:2px;font-weight:800;color:#8b5c00;margin:0 0 5px;}
.brand-note {color:#64748b;font-size:14px;margin:9px 0 25px;}
.side-brand-row {display:flex;align-items:center;gap:10px;margin:4px 0 3px;}
.side-mark {width:37px;height:37px;display:grid;place-items:center;overflow:hidden;}
.side-mark img {width:100%;height:100%;object-fit:contain;}
.side-brand {font-size:13px;font-weight:800;letter-spacing:.15px;margin:0;white-space:nowrap;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) {background:#dff4ef;border:1px solid #a7ddd1;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) p {color:#075f58!important;font-weight:700;}
[data-testid="stSidebar"] [data-testid="stSelectbox"] {margin-top:2px;}
div[data-testid="stMetric"] {box-shadow:0 5px 18px #14283f08;}
.step-card {box-shadow:0 5px 18px #14283f08;}
.step-number {display:flex;align-items:center;gap:6px;}
.step-title {color:#14283f;}
.step-card:hover {border-color:#8bd7ca;transform:translateY(-2px);transition:all .18s ease;}

div[data-testid="stMetric"] {background:#fff;border:1px solid #dce3ed;border-radius:16px;padding:25px 26px;border-top:5px solid #d7a820;min-height:132px;box-shadow:0 8px 22px #14283f0d;}
[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) div[data-testid="stMetric"] {border-top-color:#3974c6;}
[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(3) div[data-testid="stMetric"] {border-top-color:#148879;}
[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(4) div[data-testid="stMetric"] {border-top-color:#7655ad;}
[data-testid="stMetricLabel"] {color:#52657b;font-size:16px!important;font-weight:650!important;}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] *, div[data-testid="stMetricValue"] {color:#14283f!important;font-size:46px!important;font-weight:800!important;line-height:1.1!important;}
[data-testid="stForm"] {background:#fff;border:1px solid #e1e7ef;border-radius:14px;padding:22px;}
[data-testid="stDataFrame"], [data-testid="stExpander"] {border-radius:12px;overflow:hidden;}
.stButton button,.stDownloadButton button,.stLinkButton a {border-radius:9px;min-height:46px;font-size:15px!important;font-weight:650!important;}
button[kind="primary"],button[kind="primaryFormSubmit"] {background:#122b49!important;border-color:#122b49!important;color:#fff!important;box-shadow:0 4px 12px #122b4926;}
button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover {background:#9a6a00!important;border-color:#9a6a00!important;}
button[kind="primary"] *,button[kind="primaryFormSubmit"] *,[data-testid="stMain"] button[kind="primary"] * {color:#fff!important;-webkit-text-fill-color:#fff!important;}

.brand-title {font-size:30px;font-weight:750;line-height:1.2;letter-spacing:-1px;margin:0;}
.side-note {font-size:11px;color:#64748b!important;margin-bottom:24px;letter-spacing:.5px;}
.page-note {color:#64748b;margin-top:-10px;margin-bottom:24px;font-size:14px;}
.step-card {background:linear-gradient(145deg,#fffdf7,#fff);border:1px solid #e5d8ad;border-left:5px solid #d6a51c;border-radius:14px;padding:22px;height:190px;box-sizing:border-box;margin-bottom:10px;box-shadow:0 8px 22px #14283f0d;}
.step-number {font-size:12px;color:#825900;font-weight:800;letter-spacing:1px;background:#fff0bd;border-radius:999px;display:inline-block;padding:5px 10px;}
.step-title {font-size:21px;font-weight:700;margin:9px 0;color:#14283f;}
.step-note {font-size:18px;color:#40546c;line-height:1.6;}
@media(max-width:640px) {.block-container {padding:4rem 1rem 2rem;}.hero-tech {min-height:205px;padding:20px 14px;border-radius:16px;background-position:center 50%;}.hero-tech h1 {font-size:29px!important;}.hero-logo {width:50px;height:50px;}.hero-name {font-size:14px;letter-spacing:1.3px;}.hero-sub,.hero-note {font-size:13px;}[data-testid="stForm"] {padding:14px;}div[data-testid="stMetric"] {padding:14px;}.step-card {height:auto;min-height:130px;}}
/* Raised, consistent surfaces across dashboard and workflow pages */
[data-testid="stSidebar"] {box-shadow:8px 0 28px #10243a0b;z-index:3;}
[data-testid="stSidebar"] hr {display:none;}
[data-testid="stMain"] h2 {font-weight:760!important;margin-top:1.35rem!important;margin-bottom:.35rem!important;}
[data-testid="stMain"] h3 {font-weight:720!important;margin-top:1rem!important;}
[data-testid="stMetric"] {position:relative;overflow:hidden;background:linear-gradient(145deg,#fff,#f8fbff)!important;box-shadow:0 10px 24px #13243b12,0 2px 5px #13243b08!important;transition:transform .18s ease,box-shadow .18s ease;}
[data-testid="stMetric"]:hover {transform:translateY(-4px);box-shadow:0 18px 32px #13243b1c,0 4px 8px #13243b0c!important;}
[data-testid="stHorizontalBlock"]:has(.step-card) {gap:14px;padding:12px;border-radius:22px;background:linear-gradient(130deg,#eaf1f8,#f4f8fc);box-shadow:inset 0 1px #fff,0 10px 25px #13243b0b;}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {gap:12px;padding:4px 2px;}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) [data-testid="stMetric"] {border-top:1px solid #dce3ed!important;}
[data-testid="stForm"] {background:linear-gradient(145deg,#fff 0%,#fbfdff 100%)!important;border:1px solid #dce6f0!important;border-radius:18px!important;padding:24px!important;box-shadow:0 12px 28px #13243b10,0 2px 5px #13243b08!important;transition:transform .18s ease,box-shadow .18s ease;}
[data-testid="stForm"]:hover {transform:translateY(-2px);box-shadow:0 17px 34px #13243b16,0 3px 8px #13243b0a!important;}
[data-testid="stDataFrame"], [data-testid="stTable"] {border:1px solid #dce5ef;border-radius:14px!important;box-shadow:0 10px 24px #13243b10;overflow:hidden;}
[data-testid="stExpander"] {background:linear-gradient(145deg,#fff,#f9fbfe);border:1px solid #dce5ef!important;border-radius:14px!important;box-shadow:0 7px 18px #13243b0b;transition:box-shadow .18s ease,transform .18s ease;}
[data-testid="stExpander"]:hover {box-shadow:0 12px 25px #13243b14;transform:translateY(-1px);}
[data-testid="stAlert"] {border-radius:14px!important;box-shadow:0 8px 20px #13243b0b;border:1px solid #dbe6f1;}
[data-testid="stMain"] input:focus,[data-testid="stMain"] textarea:focus,[data-testid="stMain"] [data-baseweb="select"]:focus-within {border-color:#0ea5a0!important;box-shadow:0 0 0 3px #12a89b26!important;}
[data-testid="stMain"] [data-baseweb="select"] {border-radius:10px;}
.stButton button,.stDownloadButton button,.stLinkButton a {box-shadow:0 5px 12px #14283f14;transition:transform .16s ease,box-shadow .16s ease,filter .16s ease;}
.stButton button:hover,.stDownloadButton button:hover,.stLinkButton a:hover {transform:translateY(-2px);box-shadow:0 9px 18px #14283f20;filter:brightness(1.04);}
.step-card {position:relative;overflow:hidden;background:radial-gradient(ellipse at 100% 0%,#eaf7ff 0%,transparent 44%),linear-gradient(145deg,#fff 0%,#f7fbff 100%);border:1px solid #d9e3ef;border-radius:16px;border-left-width:1px;box-shadow:0 12px 26px #13243b12,0 2px 5px #13243b08;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;}
.step-audience {display:inline-flex;align-items:center;margin-left:7px;padding:4px 8px;border-radius:999px;background:#eaf0f7;color:#415b75;font-size:10px;font-weight:750;letter-spacing:.04em;vertical-align:middle;}
.step-card:hover {border-color:#b8cce0;transform:translateY(-5px);box-shadow:0 20px 35px #13243b1c,0 5px 10px #13243b0a;}
.step-number {background:#eaf3ff;color:#155982;}
/* Make the navigation rail readable and comfortable to use */
[data-testid="stSidebar"],[data-testid="stSidebar"] > div:first-child {width:290px!important;min-width:290px!important;max-width:290px!important;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding:1.4rem 1rem 1.8rem!important;}
[data-testid="stSidebar"] .side-brand-row {gap:13px;margin:8px 0 14px;}
[data-testid="stSidebar"] .side-mark {width:50px;height:50px;flex:0 0 50px;}
[data-testid="stSidebar"] .side-brand {font-size:17px!important;font-weight:850;letter-spacing:.25px;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {font-size:15px!important;line-height:1.5;color:#435b73!important;}
[data-testid="stSidebar"] label p,[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {font-size:16px!important;line-height:1.45;}
[data-testid="stSidebar"] [data-testid="stSelectbox"] label p,[data-testid="stSidebar"] [data-testid="stRadio"] label p {font-weight:700;}
[data-testid="stSidebar"] [data-baseweb="select"] {min-height:48px;border-radius:12px;}
[data-testid="stSidebar"] [data-baseweb="select"] * {font-size:16px!important;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:7px;}
[data-testid="stSidebar"] [role="radio"] {min-height:46px;padding:11px 12px!important;border-radius:12px;}
[data-testid="stSidebar"] [role="radio"] p {font-size:16px!important;font-weight:600;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) {background:linear-gradient(110deg,#dff4ef,#edf9f5);box-shadow:0 5px 12px #0c817410;border-color:#a7ddd1;}
[data-testid="stSidebar"] [data-testid="stButton"] button {min-height:46px;padding:8px 16px;font-size:15px!important;border-radius:11px;}
@media(max-width:900px) {.process-breadcrumb {flex-wrap:wrap;}.process-phase {flex:1 1 42%;}}
@media(max-width:640px) {.block-container {padding:4rem 1rem 2rem;}.hero-tech {min-height:205px;padding:20px 14px;border-radius:16px;background-position:center 50%;}.hero-content {padding:8px 4px;background:radial-gradient(ellipse at center,#061529d9 0%,#061529a8 65%,transparent 100%);}.hero-tech h1 {font-size:27px!important;}.hero-logo {width:38px;height:38px;}.hero-name {font-size:12px;letter-spacing:1.3px;}.hero-sub,.hero-note {font-size:12px;}.process-breadcrumb {gap:5px;padding:8px;}.process-phase {flex:1 1 calc(50% - 6px);padding:7px 8px;font-size:11px;}[data-testid="stForm"] {padding:14px;}div[data-testid="stMetric"] {padding:14px;}.step-card {height:auto;min-height:130px;}}
@media(prefers-reduced-motion:reduce) {[data-testid="stMetric"],[data-testid="stForm"],[data-testid="stExpander"],.stButton button,.stDownloadButton button,.stLinkButton a,.step-card {transition:none!important;}}
</style>''',unsafe_allow_html=True)
st.markdown(f'''<section class="hero-tech" style="--hero-photo:url('{hero_photo_src}')">
<div class="hero-content"><div class="hero-lockup"><img class="hero-logo" src="{logo_src}" alt="Logo KEY BẢN QUYỀN"><div><div class="hero-name">KEY BẢN QUYỀN</div><div class="hero-sub">Điều phối bản quyền và thiết bị</div></div></div><h1>TỪ KHO KEY ĐẾN MÁY SẴN SÀNG BÀN GIAO</h1><div class="hero-note">Nhận key → Redeem → Giao KTV → Kích hoạt · In tem QR → QC đóng gói</div></div></section>''',unsafe_allow_html=True)
st.sidebar.markdown(f'<div class="side-brand-row"><div class="side-mark"><img src="{logo_src}" alt="Logo KEY BẢN QUYỀN"></div><div class="side-brand">KEY BẢN QUYỀN</div></div>',unsafe_allow_html=True)
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
menus=['Việc của tôi','Tem của tôi'] if role=='KTV' else ['Hàng đợi in'] if role=='PRINT' else ['Tổng quan','Đơn vị & tài khoản','Kho key','Redeem Office','Thiết bị','Phân bổ','Kích hoạt','Bảo hành','Nhật ký']
if role=='ADMIN':menus.extend(['Người dùng','Đồng bộ Google Sheet'])
if role=='QC':menus=['Đối chiếu tem và kiểm tra']
elif role=='ADMIN':menus.extend(['Kế hoạch PC theo điểm','In tem PC và vỏ hộp','Đối chiếu tem và kiểm tra','Hàng đợi in'])
if role=='OPERATOR':menus=[name for name in menus if name!='Redeem Office']
menus.append('Hướng dẫn theo vai trò')
groups={
    'Tổng quan':['Tổng quan'],
    '01 · Chuẩn bị & bản quyền':['Đơn vị & tài khoản','Kế hoạch PC theo điểm','Kho key','Redeem Office'],
    '02 · Giao việc & kích hoạt':['Thiết bị','Phân bổ','Kích hoạt','Việc của tôi'],
    '03 · Tem QR & kiểm tra':['Tem của tôi','In tem PC và vỏ hộp','Đối chiếu tem và kiểm tra','Hàng đợi in'],
    '04 · Bảo hành & lịch sử':['Bảo hành','Nhật ký'],
    'Quản trị':['Người dùng','Đồng bộ Google Sheet'],
    'Hướng dẫn':['Hướng dẫn theo vai trò'],
}
groups={name:[item for item in items if item in menus] for name,items in groups.items()}
groups={name:items for name,items in groups.items() if items}
post_action_page=st.session_state.pop('post-action-page',None)
if post_action_page:
    section_name=next((name for name,items in groups.items() if post_action_page in items),None)
    if section_name:
        st.session_state['nav-section']=section_name
        st.session_state['nav-page-'+section_name]=post_action_page
st.sidebar.divider()
section=st.sidebar.selectbox('Nhóm công việc',list(groups),key='nav-section')
page=st.sidebar.radio('Chức năng',groups[section],key='nav-page-'+section)
st.sidebar.divider()
st.sidebar.caption('V2 · Giao diện sáng · 05/11/2026')
st.subheader(page)
flow_phases=[('01','Chuẩn bị'),('02','Redeem & giao việc'),('03','Kích hoạt & in QR'),('04','Quét & đóng gói')]
flow_stage={'Đơn vị & tài khoản':0,'Kế hoạch PC theo điểm':0,'Kho key':0,'Redeem Office':1,'Thiết bị':1,'Phân bổ':1,'Kích hoạt':2,'Việc của tôi':2,'Tem của tôi':2,'In tem PC và vỏ hộp':2,'Hàng đợi in':2,'Đối chiếu tem và kiểm tra':3}
if page in flow_stage:
    current=flow_stage[page]
    flow_html=''.join(f'<div class="process-phase {"active" if i==current else "prior" if i<current else ""}"><b>{number}</b><span>{title}</span></div>' for i,(number,title) in enumerate(flow_phases))
    st.markdown(f'<div class="process-breadcrumb">{flow_html}</div>',unsafe_allow_html=True)
page_notes={
    'Tổng quan':'Theo dõi kho bản quyền và chọn bước tiếp theo trong quy trình.',
    'Đơn vị & tài khoản':'Khai báo nơi nhận PC và tài khoản Microsoft quản lý sản phẩm.',
    'Kế hoạch PC theo điểm':'Chốt số lượng PC theo từng đơn vị để đánh số và giao nhận.',
    'Kho key':'Nhập lô key, kiểm tra chứng từ và theo dõi trạng thái bản quyền.',
    'Redeem Office':'Admin redeem tại Microsoft rồi ghi nhận tài khoản nhận sản phẩm.',
    'Thiết bị':'Khai báo mã PC và serial để đối chiếu xuyên suốt quá trình.',
    'Phân bổ':'Chọn bản quyền, máy nhận và KTV chịu trách nhiệm.',
    'In tem PC và vỏ hộp':'Admin xử lý tem lẻ khi cần; lô của KTV được in tại trạm USB.',
    'Tem của tôi':'Gửi PC đã kích hoạt thành công theo lô đến trạm in USB.',
    'Hàng đợi in':'Trạm in USB xử lý lô tem theo đơn vị và KTV.',
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
def run(name,fn,confirmation=None,next_page=None,select_record=None):
    token=st.session_state.setdefault('op-'+name,str(uuid.uuid4()))
    try:
        fn(token)
        st.session_state.pop('op-'+name,None)
        if confirmation:st.session_state['report-confirmation']=(actor,confirmation)
        if next_page:st.session_state['post-action-page']=next_page
        if select_record:st.session_state['last-activated-device-'+actor]=select_record
        st.rerun()
    except DomainError as e:st.error(str(e))
    except Exception:st.error('Chưa xác nhận lưu thành công. Hãy kiểm tra kết nối và tải lại hồ sơ.')
def label(r):return f"{r['product']} · {r['sku']} · …{r['tail']} · {LABELS[r['state']]}"
def serial_agent_archive():
    bundle=io.BytesIO()
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(Path('tools/SerialAgent.ps1'),'SerialAgent.ps1')
        archive.write(Path('tools/START_SERIAL_AGENT.cmd'),'START_SERIAL_AGENT.cmd')
    return bundle.getvalue()
if page in {'Kế hoạch PC theo điểm','In tem PC và vỏ hộp','Đối chiếu tem và kiểm tra','Tem của tôi','Hàng đợi in'}:
    from license_app.preparation_ui import render
    render(ledger,actor,role,page,os.getenv('APP_MODE')=='demo')
elif page=='Tổng quan':
    data=rows('licenses'); cols=st.columns(4)
    for col,title,n in zip(cols,['Đã nhận','Chưa phân bổ','Đã giao máy','Đã kích hoạt'],[len(data),sum(r['state'] in {'RECEIVED','VERIFIED','REDEEMED'} for r in data),sum(r['state']=='ASSIGNED' for r in data),sum(r['state']=='ACTIVATED' for r in data)]):col.metric(title,n)
    st.markdown('### Một quy trình · Bốn chặng')
    st.caption('Từ lúc nhận key đến khi QC xác nhận đủ cặp tem PC và hộp; mỗi chặng có màn hình thao tác riêng.')
    step2_target='Redeem Office' if role=='ADMIN' else 'Phân bổ'
    step3_target='Việc của tôi' if role=='KTV' else 'Kích hoạt'
    steps=[('01','Chuẩn bị','Đơn vị, số lượng PC, key và tài khoản.','Đơn vị & tài khoản','ADMIN'),('02','Redeem & giao việc','Ghi nhận redeem, gắn license với máy và giao KTV.',step2_target,'ADMIN'),('03','Kích hoạt · in tem QR','KTV báo kết quả; in tem PC và vỏ hộp đúng số thứ tự.',step3_target,'KTV'),('04','Quét · kiểm tra · đóng gói','QC quét hai tem, đối chiếu máy, đơn vị và số lượng.','Đối chiếu tem và kiểm tra','QC')]
    def open_page(target):
        for group,items in groups.items():
            if target in items:
                st.session_state['nav-section']=group
                st.session_state['nav-page-'+group]=target
                return
    for col,(number,title,note,target,audience) in zip(st.columns(4),steps):
        with col:
            st.markdown(f'<div class="step-card"><div class="step-number">CHẶNG {number}<span class="step-audience">{audience}</span></div><div class="step-title">{title}</div><div class="step-note">{note}</div></div>',unsafe_allow_html=True)
            if target in menus:st.button({'01':'Mở chuẩn bị','02':'Mở redeem / giao việc','03':'Mở việc KTV','04':'Mở kiểm tra'}[number]+'  →',key='shortcut-'+number,on_click=open_page,args=(target,),use_container_width=True,type='primary')
    st.markdown('### Danh sách bản quyền')
    if not data:st.info('Kho dữ liệu chưa có bản quyền. Nhập kế hoạch đơn vị/điểm/SKU tại tab 16 của Google Sheet, nạp vào app, rồi nhập lô key thử nghiệm.')
    else:table(data)
    if data:
        st.bar_chart({LABELS[s]:sum(r['state']==s for r in data) for s in LABELS if any(r['state']==s for r in data)})
        buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(data[0]));writer.writeheader();writer.writerows([{k:("'"+v if isinstance(v,str) and v[:1] in {'=','+','-','@','\t','\r'} else v) for k,v in row.items()} for row in data])
        st.download_button('Tải báo cáo CSV',buf.getvalue().encode('utf-8-sig'),'bao_cao.csv','text/csv')
elif page=='Đơn vị & tài khoản':
    if role=='ADMIN':
        from license_app.sheet_sync import (PLAN_TAB, PLAN_HEADERS, ACCOUNT_TAB, build_sheets_service,
            configured_spreadsheet_id, read_delivery_plan, read_account_roster)
        st.markdown('### Nạp kế hoạch từ Google Sheet')
        st.caption('Google Sheet là nơi nhập đơn vị, xã/điểm nhận, số PC và số lượng theo từng phần mềm/SKU. App đọc kế hoạch sau khi Admin xem trước; key đầy đủ vẫn nằm trong kho bảo mật của app.')
        target=configured_spreadsheet_id(st.secrets)
        st.link_button('Mở file kế hoạch Google Sheet','https://docs.google.com/spreadsheets/d/'+target+'/edit')
        st.caption('Tab nguồn: '+PLAN_TAB+' · mỗi dòng là một điểm nhận và một SKU; để trống Phần mềm/SKU nếu chỉ khai báo điểm.')
        preview_key='sheet-plan-preview-'+actor
        if os.getenv('APP_MODE') in {'demo','shared_test','team_test'}:
            st.info('Chế độ minh họa không đọc kế hoạch thật từ Google Sheet.')
        elif st.button('Đọc và xem trước kế hoạch từ Sheet',type='primary',key='read-delivery-plan'):
            try:
                records=read_delivery_plan(build_sheets_service(st.secrets),target)
                digest=hashlib.sha256(json.dumps(records,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                st.session_state[preview_key]={'records':records,'digest':digest,'target':target}
                st.rerun()
            except DomainError as e:st.error(str(e))
            except Exception:st.error('Không đọc được kế hoạch. Kiểm tra quyền xem file Google Sheet và kết nối Google Sheets của app.')
        preview=st.session_state.get(preview_key)
        if preview and preview['target']==target:
            records=preview['records']
            st.dataframe([{'Mã dự án':r['project'],'Tên dự án':r['project_name'],
                'Đơn vị được cấp':r['unit_name'],'Mã xã/điểm':r['point_code'],
                'Tên xã/phường/đơn vị':r['point_name'],'Số PC tại điểm':r['pc_quantity'],
                'Phần mềm':r['product'] or '—','SKU':r['sku'] or '—',
                'Số license':r['license_quantity'] if r['product'] else '—'} for r in records],
                hide_index=True,width='stretch')
            st.warning('Khi nạp, app cập nhật các điểm có trong Sheet. Điểm không có trong Sheet vẫn được giữ. Không thể giảm quota SKU xuống thấp hơn số license đã gán cho PC.')
            if st.button('Nạp kế hoạch đã xem vào app',type='primary',key='apply-delivery-plan'):
                try:
                    current=read_delivery_plan(build_sheets_service(st.secrets),target)
                    digest=hashlib.sha256(json.dumps(current,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                    if digest!=preview['digest']:
                        st.error('Sheet đã thay đổi sau khi xem trước. Hãy đọc lại kế hoạch rồi nạp.')
                        st.session_state.pop(preview_key,None)
                    else:
                        operation=st.session_state.setdefault('op-sheet-plan-'+actor,str(uuid.uuid4()))
                        ledger.save_delivery_plan(actor,current,operation)
                        st.session_state.pop('op-sheet-plan-'+actor,None)
                        st.session_state.pop(preview_key,None)
                        st.success('Đã nạp kế hoạch từ Google Sheet vào app.')
                        st.rerun()
                except DomainError as e:st.error(str(e))
                except Exception:st.error('Chưa nạp được kế hoạch. Dữ liệu trong app chưa được xác nhận cập nhật; hãy tải lại và kiểm tra kết nối.')
        schedule=ledger.delivery_plan_rows(actor)
        if schedule:
            st.markdown('### Kế hoạch đã nạp vào app')
            st.dataframe([{'Mã dự án':r['project'],'Tên dự án':r['project_name'],
                'Đơn vị được cấp':r['unit'],'Mã xã/điểm':r['code'],'Tên xã/phường/điểm':r['point'],
                'Số PC tại điểm':r['pc_quantity'],'Tổng PC của đơn vị':r['unit_pc_total'] or 0,
                'Phần mềm':r['product'] or '—','SKU':r['sku'] or '—',
                'Số license':r['license_quantity'] if r['product'] else '—'} for r in schedule],
                hide_index=True,width='stretch')
        else:st.info('Chưa có kế hoạch được nạp. Nhập danh sách tại tab 16_KE_HOACH_CAP_PC rồi bấm đọc và nạp.')
    st.markdown('### Nạp danh sách tài khoản Microsoft theo lô')
    st.caption('Nguồn là tab 17_TAI_KHOAN_MS, đối chiếu Mã dự án + Tên đơn vị được cấp với tab 16. Chỉ nhập email và người quản lý; không đưa mật khẩu hoặc MFA vào Sheet.')
    account_preview_key='sheet-account-preview-'+actor
    if os.getenv('APP_MODE') in {'demo','shared_test','team_test'}:
        st.info('Chế độ minh họa không đọc danh sách tài khoản thật từ Google Sheet.')
    elif st.button('Đọc và xem trước danh sách tài khoản',key='read-account-roster'):
        try:
            records=read_account_roster(build_sheets_service(st.secrets),target)
            digest=hashlib.sha256(json.dumps(records,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            st.session_state[account_preview_key]={'records':records,'digest':digest,'target':target};st.rerun()
        except DomainError as e:st.error(str(e))
        except Exception:st.error('Không đọc được tab tài khoản. Kiểm tra quyền Google Sheet và kết nối của app.')
    account_preview=st.session_state.get(account_preview_key)
    if role=='ADMIN' and account_preview and account_preview['target']==target:
        st.dataframe([{'Mã dự án':r['project'],'Tên dự án':r['project_name'],'Đơn vị được cấp':r['unit_name'],
            'Email Microsoft':r['email'],'Người quản lý':r['owner']} for r in account_preview['records']],hide_index=True,width='stretch')
        if st.button('Nạp danh sách đã xem vào app',type='primary',key='apply-account-roster'):
            try:
                current=read_account_roster(build_sheets_service(st.secrets),target)
                digest=hashlib.sha256(json.dumps(current,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                if digest!=account_preview['digest']:
                    st.error('Sheet đã thay đổi sau khi xem trước. Hãy đọc lại danh sách rồi nạp.')
                    st.session_state.pop(account_preview_key,None)
                else:
                    token=st.session_state.setdefault('op-account-roster-'+actor,str(uuid.uuid4()))
                    result=ledger.import_accounts(actor,current,token)
                    st.session_state.pop('op-account-roster-'+actor,None);st.session_state.pop(account_preview_key,None)
                    st.success(f"Đã thêm {result['added']} tài khoản; {result['unchanged']} dòng đã có sẵn.");st.rerun()
            except DomainError as e:st.error(str(e))
            except Exception:st.error('Chưa nạp được danh sách; dữ liệu app chưa xác nhận cập nhật.')
    account_rows=ledger.account_assignment_rows(actor)
    if role=='ADMIN':
        st.markdown('### Giao tài khoản đã redeem cho KTV')
        redeemed_ids={r['account_id'] for r in rows('licenses') if r.get('account_id') and r['state'] in {'REDEEMED','ASSIGNED','ACTIVATED','WARRANTY_REVIEW'}}
        eligible=[r for r in account_rows if r['id'] in redeemed_ids]
        if eligible:
            account=st.selectbox('Tài khoản Microsoft',eligible,format_func=lambda r:f"{r['project']} · {r['unit']} · {r['email']} · {r['ktv'] or 'Chưa giao'}",key='account-handoff')
            ktvs=[r for r in rows('users') if r['role']=='KTV' and r['active']]
            if account['ktv']:
                st.info('Đang giao cho KTV: '+account['ktv'])
                if st.button('Thu hồi giao tài khoản',key='release-account'):
                    try:ledger.release_account_from_ktv(actor,account['id'],str(uuid.uuid4()));st.success('Đã ghi nhận thu hồi.');st.rerun()
                    except DomainError as e:st.error(str(e))
            elif ktvs:
                ktv=st.selectbox('KTV nhận tài khoản',[r['email'] for r in ktvs],key='account-ktv')
                if st.button('Giao tài khoản Microsoft cho KTV',type='primary',key='assign-account'):
                    try:ledger.assign_account_to_ktv(actor,account['id'],ktv,str(uuid.uuid4()));st.success('Đã giao tài khoản cho KTV.');st.rerun()
                    except DomainError as e:st.error(str(e))
        else:st.info('Tài khoản sẽ xuất hiện tại đây sau khi được redeem vào Microsoft.')
    st.markdown('### Danh sách tài khoản')
    table(account_rows)
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
        unit=pick('Đơn vị nhận máy',rows('units'),lambda r:f"{r.get('project_name') or r['project']} · {r['project']} · {r['name']}")
        point_rows=rows('receiving_points')
        point_options=[r for r in point_rows if unit and r['unit_id']==unit['id']]
        point=pick('Xã/phường/điểm nhận PC',point_options,lambda r:f"{r['code']} · {r['name']} ({r['pc_quantity']} PC)") if point_options else None
        tag=st.text_input('Mã máy nội bộ');model=st.text_input('Hãng / model')
        serial=st.text_input('Serial máy / mã tem đã đối soát');board=st.text_input('Serial mainboard (để trống nếu KTV sẽ đọc trên PC)')
        if st.form_submit_button('Thêm máy') and unit:
            if not point_options:st.error('Đơn vị này chưa có điểm nhận. Nạp danh sách phân bổ trước khi thêm PC.')
            elif point:run('device',lambda t:ledger.add_device(actor,unit['id'],tag,serial,board,model,t,point['id']))
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
    job=None
    if role=='KTV':
        st.info('Mỗi việc là một license được giao cho một PC. Hoàn tất PC này, in và dán đúng cặp tem, rồi mới chuyển sang việc tiếp theo.')
        job=pick('Chọn PC / license đang làm',pending,
            lambda r:f"{r.get('asset_tag',r['device_id'])} · {r.get('product','')} · {r.get('sku','')} · …{r.get('tail','')} · {r['id'][:8]}")
        if job:
            st.download_button('Tải công cụ đọc serial mainboard cho PC này',serial_agent_archive(),
                'cong_cu_doc_serial_mainboard.zip','application/zip',key='serial-agent-download-'+job['id'])
            st.caption('Giải nén trên PC đang xử lý, chạy START_SERIAL_AGENT.cmd và để cửa sổ công cụ mở. Sau đó bấm nút đọc bên dưới. Công cụ chỉ đọc serial mainboard, không kích hoạt và không nhận lệnh từ app.')
            read=board_serial_reader(job_id=job['id'],default=None,key='board-reader-'+job['id'])
            if isinstance(read,dict) and read.get('ok') and read.get('serial'):
                serial_value=str(read['serial']).strip()
                marker=f"board-bound-{actor}-{job['id']}"
                if st.session_state.get(marker)!=serial_value:
                    operation_key=f"board-bind-op-{actor}-{job['id']}"
                    operation=st.session_state.setdefault(operation_key,str(uuid.uuid4()))
                    try:
                        ledger.bind_board_serial(actor,job['id'],serial_value,operation)
                        st.session_state.pop(operation_key,None)
                        st.session_state[marker]=serial_value
                        st.rerun()
                    except DomainError as e:
                        st.error(str(e))
            elif isinstance(read,dict) and read.get('ok') is False:
                st.warning('Chưa nhận được serial. Kiểm tra công cụ đang chạy trên đúng PC và quyền mạng cục bộ của Chrome.')
            serial_ready=(st.session_state.get(f"board-bound-{actor}-{job['id']}")==job.get('board_serial'))
            if serial_ready:
                st.success('Đã đọc và gắn serial mainboard '+job['board_serial']+' với PC / license đang chọn.')
            else:
                st.warning('Đọc serial trên chính PC này trước khi gửi báo cáo kích hoạt thành công.')
    else:
        job=pick('Việc cần báo cáo',pending,lambda r:r.get('asset_tag',r['device_id'])+' · '+r['id'][:8])
    if role!='KTV' or (job and st.session_state.get(f"board-bound-{actor}-{job['id']}")==job.get('board_serial')):
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
    with st.form('update-user'):
        person=pick('Thành viên cần cập nhật',existing,lambda r:r['email']+' · '+ROLE_NAMES[r['role']])
        role_choice=st.selectbox('Vai trò mới',['KTV','QC','OPERATOR','PRINT','ADMIN'],format_func=ROLE_NAMES.get)
        enabled=st.checkbox('Được phép sử dụng app',value=True)
        if st.form_submit_button('Lưu quyền thành viên') and person:
            run('update-user',lambda t:ledger.update_user(actor,person['email'],role_choice,enabled,t),
                'Đã cập nhật quyền thành viên.')
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
    snapshot=make_snapshot(ledger,actor,demo=os.getenv('APP_MODE') in {'demo','shared_test','team_test'})
    st.write('Số bản ghi có thể xuất:',sum(len(r) for r in snapshot['tables'].values()))
    st.download_button('Tải bản dữ liệu để đối chiếu (JSON — tệp dữ liệu có cấu trúc)',
        __import__('json').dumps(snapshot,ensure_ascii=False,indent=2),'ban_quyen_dong_bo.json','application/json')
    target=configured_spreadsheet_id(st.secrets)
    st.link_button('Mở Google Sheet','https://docs.google.com/spreadsheets/d/'+target+'/edit')
    if os.getenv('APP_MODE') in {'demo','shared_test','team_test'}:
        st.info('Chế độ minh họa chỉ dùng dữ liệu giả và không đọc hoặc ghi Google Sheet dùng chung.')
    else:
        st.caption('Đích đồng bộ: '+target)
        if st.button('Đồng bộ báo cáo lên Google Sheet',type='primary'):
            try:
                count=sync_with_service(build_sheets_service(st.secrets),target,snapshot)
                st.success(f'Đã đồng bộ {count} bản ghi. Xem thời điểm tại tab 15_DONG_BO_APP.')
            except DomainError as err:st.error(str(err))
            except Exception:st.error('Chưa đồng bộ được. Kiểm tra Google Sheets API, danh tính chạy app và quyền Người chỉnh sửa trên đúng file Sheet. Dữ liệu app vẫn đã lưu; có thể đồng bộ lại.')

