import streamlit as st
import pandas as pd
import requests
import platform
import subprocess
import qrcode
from io import BytesIO

st.set_page_config(page_title="Hệ Thống Bản Quyền Đa Dự Án", page_icon="🛡️", layout="wide")

# ================= CẤU HÌNH API =================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxzVyyyV1Fsswbv5fWXPyqasm2N_BZxiAuZEHX-EvNt7xBMFqmN8QJavuVqpNBigTw/exec"
# ================================================

# Hàm tạo QR Code để in tem
def generate_qr(data_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# Hàm lấy Serial Mainboard tự động
def get_serial_mainboard():
    try:
        os_name = platform.system()
        if os_name == "Windows":
            cmd = "wmic baseboard get serialnumber"
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout, _ = process.communicate()
            lines = stdout.decode('utf-8', errors='ignore').split('\n')
            serial = [line.strip() for line in lines if line.strip() and "SerialNumber" not in line]
            if serial: return serial[0]
    except:
        pass
    return ""

st.title("🛡️ HỆ THỐNG QUẢN TRỊ BẢN QUYỀN ĐA DỰ ÁN")
st.markdown("---")

# MENU ĐIỀU HƯỚNG
list_du_an = ["DA880", "DA881", "DA885"]
selected_du_an = st.sidebar.selectbox("Lựa chọn Dự Án:", list_du_an)
vai_tro = st.sidebar.radio("Nghiệp vụ thực hiện:", ["1. KTV Tiền Kích Hoạt", "2. QC Đối Soát Đóng Gói", "3. Bảo Hành / Quản Trị"])

# ----------------- MODULE 1: TIỀN KÍCH HOẠT -----------------
if vai_tro == "1. KTV Tiền Kích Hoạt":
    st.subheader(f"⚡ GIAI ĐOẠN 1: TIỀN KÍCH HOẠT TẠI CÔNG TY - {selected_du_an}")
    
    col1, col2 = st.columns(2)
    with col1:
        ma_xa = st.selectbox("Đơn vị / Xã nhận thiết bị:", ["Xã Minh Xuân", "Xã Nông Tiến", "Xã Bình Thuận", "Xã An Tường"])
        ktv_name = st.text_input("KTV Thực hiện:", placeholder="Ví dụ: Vỹ")
    
    with col2:
        serial_input = st.text_input("Serial Mainboard:", value=get_serial_mainboard())
        if st.button("🔍 Tự động quét lại Serial"):
            st.rerun()
            
    if st.button("🚀 XÁC NHẬN CẤP KEY & KÍCH HOẠT", type="primary"):
        if not serial_input or not ktv_name:
            st.error("Vui lòng điền đủ Tên KTV và Serial Mainboard!")
        else:
            with st.spinner("Đang kết nối kho dữ liệu..."):
                payload = {
                    "action": "TIEN_KICH_HOAT", "maDuAn": selected_du_an,
                    "maXa": ma_xa, "serialMainboard": serial_input, "ktv": ktv_name
                }
                res = requests.post(WEB_APP_URL, json=payload).json()
                
                if res["status"] == "success":
                    st.success("✅ Đã cấp Key thành công! KTV sử dụng thông tin dưới đây để đăng nhập máy PC:")
                    
                    # Tính năng Copy nhanh vào Clipboard
                    c1, c2, c3 = st.columns(3)
                    with c1: 
                        st.caption("Tài Khoản Microsoft")
                        st.code(res["tkMS"], language="text")
                    with c2: 
                        st.caption("Mật Khẩu")
                        st.code(res["passMS"], language="text")
                    with c3: 
                        st.caption("Key Office")
                        st.code(res["key"], language="text")
                    st.markdown("---")
st.markdown("### 🌐 THỰC HIỆN REDEEM BẢN QUYỀN")
st.markdown("""
<a href="https://setup.office.com/" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #0078D4; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
    👉 Mở trang Redeem Microsoft (setup.office.com)
</a>
""", unsafe_allow_html=True)
                    st.markdown("---")
                    st.markdown("### 🖨️ IN TEM NHÃN MÃ QR")
                    qr_data = f"{selected_du_an} | {ma_xa} | {serial_input}"
                    qr_img = generate_qr(qr_data)
                    
                    st.image(qr_img, width=200, caption="Mã đối soát QR (In 2 bản: Dán vỏ PC và Vỏ hộp)")
                    st.download_button(label="📥 Tải Tem QR (In Nhiệt)", data=qr_img, file_name=f"Tem_{serial_input}.png", mime="image/png")
                else:
                    st.error(f"❌ LỖI: {res['message']}")

# ----------------- MODULE 2: QC ĐỐI SOÁT -----------------
elif vai_tro == "2. QC Đối Soát Đóng Gói":
    st.subheader(f"📦 GIAI ĐOẠN 2: QC ĐỐI SOÁT & NIÊM PHONG - {selected_du_an}")
    st.info("KTV quét mã QR trên vỏ hộp và trên thân máy để đối chiếu trước khi đóng thùng xuất xưởng.")
    
    col_hop, col_may = st.columns(2)
    with col_hop: qr_hop = st.text_input("Mã quét từ VỎ HỘP:", key="hop")
    with col_may: qr_may = st.text_input("Mã quét từ THÂN MÁY PC:", key="may")
    
    if st.button("🔍 KIỂM TRA ĐỐI SOÁT"):
        if qr_hop and qr_may:
            if qr_hop.strip() == qr_may.strip():
                serial_extracted = qr_hop.split(" | ")[-1].strip() # Tách lấy chuỗi Serial
                
                # Bắn API cập nhật trạng thái QC Passed
                payload = {"action": "QC_PASSED", "serial": serial_extracted}
                res = requests.post(WEB_APP_URL, json=payload).json()
                
                if res["status"] == "success":
                    st.success("✅ KHỚP CHÍNH XÁC! Hệ thống đã ghi nhận QC Passed. Cho phép dán tem niêm phong.")
                else:
                    st.error(res["message"])
            else:
                st.error("❌ CẢNH BÁO ĐỎ: VỎ HỘP VÀ THÂN MÁY KHÔNG KHỚP NHAU! Yêu cầu sắp xếp lại.")
        else:
            st.warning("Vui lòng quét đủ mã của cả Vỏ hộp và Thân máy.")

# ----------------- MODULE 3: BẢO HÀNH -----------------
elif vai_tro == "3. Bảo Hành / Quản Trị":
    st.subheader("🔧 CẬP NHẬT BẢO HÀNH (THAY MAINBOARD)")
    st.info("Sử dụng khi máy bị hỏng Mainboard thực tế tại Xã cần thay mới để không mất dấu Bản quyền.")
    
    old_serial = st.text_input("Nhập Serial Mainboard CŨ (Bị hỏng):")
    new_serial = st.text_input("Nhập Serial Mainboard MỚI (Thay thế):")
    
    if st.button("Cập Nhật Liên Kết Bản Quyền"):
        if old_serial and new_serial:
            payload = {"action": "DOI_BAO_HANH", "oldSerial": old_serial.strip(), "newSerial": new_serial.strip()}
            res = requests.post(WEB_APP_URL, json=payload).json()
            if res["status"] == "success":
                st.success("✅ Đã ghi đè Serial mới thành công. Bản quyền đã được liên kết lại với mainboard mới!")
            else:
                st.error(res["message"])
