import streamlit as st
import pandas as pd
import requests
import qrcode
from io import BytesIO

st.set_page_config(page_title="Hệ Thống Bản Quyền Đa Dự Án", page_icon="🛡️", layout="wide")

# ================= CẤU HÌNH API =================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxekVF8gvJARSf5gemQxGWLr51AZk-bnO3irYJa6FbCQrsWuuO57aZYSDmb8iv8M_xaJQ/exec"
# ================================================

def generate_qr(data_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

st.header("🛡️ HỆ THỐNG QUẢN TRỊ BẢN QUYỀN ĐA DỰ ÁN")
st.markdown("---")

list_du_an = ["DA880", "DA881", "DA885"]
selected_du_an = st.sidebar.selectbox("Lựa chọn Dự Án:", list_du_an)
vai_tro = st.sidebar.radio("Nghiệp vụ thực hiện:", ["1. KTV Tiền Kích Hoạt", "2. QC Đối Soát Đóng Gói", "3. Bảo Hành / Quản Trị"])

# ----------------- MODULE 1: TIỀN KÍCH HOẠT -----------------
if vai_tro == "1. KTV Tiền Kích Hoạt":
    st.subheader(f"⚡ GIAI ĐOẠN 1: TIỀN KÍCH HOẠT TẠI CÔNG TY - {selected_du_an}")
    
    with st.expander("📖 Xem Hướng Dẫn Sử Dụng Chi Tiết (Bước 1)"):
        st.markdown("""
        1. **Chọn Đơn Vị/Xã**: Lựa chọn đúng xã nhận thiết bị.
        2. **Lấy Serial**: Chạy file TOOL_KICH_HOAT.bat để tự động mở web và điền Serial.
        3. **Cấp Key**: Bấm **Xác nhận cấp key**, hệ thống trả về trọn bộ Key Windows, Office và Diệt Virus.
        """)

    col1, col2 = st.columns(2)
    with col1:
        list_xa = ["Đang tải danh sách..."]
        list_ktv = ["Đang tải danh sách..."]
        try:
            res_data = requests.post(WEB_APP_URL, json={"action": "GET_DANH_SACH_XA", "maDuAn": selected_du_an}).json()
            if res_data.get("status") == "success":
                list_xa = res_data.get("data") if len(res_data.get("data")) > 0 else ["Không có dữ liệu đơn vị"]
                list_ktv = res_data.get("ktv_data") if res_data.get("ktv_data") and len(res_data.get("ktv_data")) > 0 else ["Không có dữ liệu KTV"]
            else:
                 list_xa, list_ktv = ["Lỗi lấy dữ liệu xã"], ["Lỗi lấy dữ liệu KTV"]
        except:
             list_xa, list_ktv = ["Lỗi kết nối API"], ["Lỗi kết nối API"]

        ma_xa = st.selectbox("Đơn vị / Xã nhận thiết bị:", list_xa)
        ktv_name = st.selectbox("KTV Thực hiện:", list_ktv)
    
    with col2:
        query_params = st.query_params
        auto_serial = query_params.get("serial", "")
        serial_input = st.text_input("Serial Mainboard:", value=auto_serial)
            
    if st.button("🚀 XÁC NHẬN CẤP TRỌN BỘ KEY & KÍCH HOẠT", type="primary", use_container_width=True):
        if not serial_input or ktv_name in ["Đang tải danh sách...", "Không có dữ liệu KTV", "Lỗi kết nối API"]:
            st.error("Vui lòng đảm bảo Serial Mainboard và Tên KTV hợp lệ!")
        else:
            with st.spinner("Đang kết nối kho dữ liệu..."):
                payload = {
                    "action": "TIEN_KICH_HOAT", "maDuAn": selected_du_an,
                    "maXa": ma_xa, "serialMainboard": serial_input, "ktv": ktv_name
                }
                res = requests.post(WEB_APP_URL, json=payload).json()
                
                if res["status"] == "success":
                    st.success("✅ Đã cấp trọn bộ bản quyền thành công!")
                    
                    # Hiển thị chia nhóm thông tin rõ ràng
                    st.markdown("### 🪟 1. BẢN QUYỀN WINDOWS")
                    st.code(res["keyWin"] if res["keyWin"] else "Chưa có Key Windows trong kho", language="text")
                    
                    st.markdown("### 📦 2. BẢN QUYỀN OFFICE")
                    c1, c2, c3 = st.columns(3)
                    with c1: 
                        st.caption("Tài Khoản Microsoft")
                        st.code(res["tkMS"], language="text")
                    with c2: 
                        st.caption("Mật Khẩu")
                        st.code(res["passMS"], language="text")
                    with c3: 
                        st.caption("Key Office")
                        st.code(res["keyOffice"], language="text")
                    
                    st.markdown("### virus 3. PHẦN MỀM DIỆT VIRUS & HẠN SỬ DỤNG")
                    v1, v2 = st.columns(2)
                    with v1:
                        st.caption("TK / Key Diệt Virus")
                        st.code(res["keyAnti"] if res["keyAnti"] else "Không có", language="text")
                    with v2:
                        st.caption("⏰ Hạn Sử Dụng Diệt Virus")
                        st.error(f"📅 **{res['expAnti']}**" if res["expAnti"] else "Chưa cập nhật hạn")
                    
                    st.markdown("---")
                    st.markdown("### 🌐 THỰC HIỆN REDEEM OFFICE")
                    redeem_url = f"https://setup.office.com/?msokey={res['keyOffice']}"
                    st.markdown(f"""
                    <a href="{redeem_url}" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #0078D4; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        👉 Mở trang Redeem (Tự động điền sẵn Key Office)
                    </a>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.markdown("### 🖨️ IN TEM NHÃN MÃ QR")
                    qr_data = f"{selected_du_an} | {ma_xa} | {serial_input}"
                    qr_img = generate_qr(qr_data)
                    st.image(qr_img, width=200, caption="Mã đối soát QR")
                    st.download_button(label="📥 Tải Tem QR (In Nhiệt)", data=qr_img, file_name=f"Tem_{serial_input}.png", mime="image/png")
                else:
                    st.error(f"❌ LỖI: {res['message']}")

# ----------------- MODULE 2: QC ĐỐI SOÁT -----------------
elif vai_tro == "2. QC Đối Soát Đóng Gói":
    st.subheader(f"📦 GIAI ĐOẠN 2: QC ĐỐI SOÁT & NIÊM PHONG - {selected_du_an}")
    col_hop, col_may = st.columns(2)
    with col_hop: qr_hop = st.text_input("Mã quét từ VỎ HỘP:", key="hop")
    with col_may: qr_may = st.text_input("Mã quét từ THÂN MÁY PC:", key="may")
    
    if st.button("🔍 KIỂM TRA ĐỐI SOÁT", use_container_width=True):
        if qr_hop and qr_may:
            if qr_hop.strip() == qr_may.strip():
                serial_extracted = qr_hop.split(" | ")[-1].strip()
                payload = {"action": "QC_PASSED", "serial": serial_extracted}
                res = requests.post(WEB_APP_URL, json=payload).json()
                if res["status"] == "success":
                    st.success("✅ KHỚP CHÍNH XÁC! Đã ghi nhận QC Passed.")
                else:
                    st.error(res["message"])
            else:
                st.error("❌ CẢNH BÁO ĐỎ: VỎ HỘP VÀ THÂN MÁY KHÔNG KHỚP NHAU!")
        else:
            st.warning("Vui lòng quét đủ mã.")

# ----------------- MODULE 3: BẢO HÀNH -----------------
elif vai_tro == "3. Bảo Hành / Quản Trị":
    st.subheader("🔧 CẬP NHẬT BẢO HÀNH (THAY MAINBOARD)")
    old_serial = st.text_input("Nhập Serial Mainboard CŨ:")
    new_serial = st.text_input("Nhập Serial Mainboard MỚI:")
    
    if st.button("Cập Nhật Liên Kết Bản Quyền", use_container_width=True):
        if old_serial and new_serial:
            payload = {"action": "DOI_BAO_HANH", "oldSerial": old_serial.strip(), "newSerial": new_serial.strip()}
            res = requests.post(WEB_APP_URL, json=payload).json()
            if res["status"] == "success":
                st.success("✅ Đã cập nhật Serial mới thành công!")
            else:
                st.error(res["message"])
