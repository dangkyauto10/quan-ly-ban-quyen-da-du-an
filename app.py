import streamlit as st
import pandas as pd
import requests
import qrcode
from io import BytesIO

st.set_page_config(page_title="Hệ Thống Bản Quyền Đa Dự Án", page_icon="🛡️", layout="wide")

# ================= CẤU HÌNH API & LINK WEB =================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxQ1Yzr_u0VtaBQErzXR4YqRAwGNcw9ePRy6jJ4CM9n9H2S-i7EkobHKYjrPl4Y2toL/exec"
STREAMLIT_APP_URL = "https://quan-ly-ban-quyen-da-du-an-vwhggefuh7qfwpplhpelcb.streamlit.app"

def generate_qr(data_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

BAT_LINES = [
    "@echo off",
    "title TOOL LAY SERIAL TU DONG - DA DU AN",
    "color 0A",
    "echo DANG QUET SERIAL PHAN CUNG MAY TINH...",
    "set \"SN=\"",
    "for /f \"delims=\" %%A in ('powershell -NoProfile -Command \"$s = (Get-CimInstance Win32_BIOS).SerialNumber; if (-not $s -or$s -like '*O.E.M*' -or $s -like '*To be filled*' -or$s -like '*Default*') { $s = (Get-CimInstance Win32_BaseBoard).SerialNumber }; if (-not$s -or $s -like '*O.E.M*' -or$s -like '*To be filled*') { $s = (Get-CimInstance Win32_ComputerSystemProduct).IdentifyingNumber }; if (-not$s -or $s -like '*O.E.M*' -or$s -like '*To be filled*') { $s = 'NHAP_TAY_TREN_VO_MAY' };$s -replace '[^a-zA-Z0-9_-]',''\"') do set \"SN=%%A\"",
    "echo Serial doc duoc: %SN%",
    "start \"\" \"" + STREAMLIT_APP_URL + "/?serial=%SN%\"",
    "exit"
]
BAT_SCRIPT_CONTENT = "\r\n".join(BAT_LINES)

st.header("🛡️ HỆ THỐNG QUẢN TRỊ BẢN QUYỀN ĐA DỰ ÁN")
st.markdown("---")

list_du_an = ["DA880", "DA881", "DA885"]
try:
    res_proj = requests.post(WEB_APP_URL, json={"action": "GET_DANH_SACH_DU_AN"}, timeout=15).json()
    if res_proj.get("status") == "success" and len(res_proj.get("projects", [])) > 0:
        list_du_an = res_proj.get("projects")
except:
    pass

selected_du_an = st.sidebar.selectbox("📂 Lựa chọn Dự Án:", list_du_an)
vai_tro = st.sidebar.radio("⚙️ Nghiệp vụ thực hiện:", ["1. KTV Tiền Kích Hoạt", "2. QC Đối Soát Đóng Gói", "3. Bảo Hành / Quản Trị"])

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Công cụ lấy Serial")
st.sidebar.download_button(
    label="📥 Tải TOOL_KICH_HOAT.bat",
    data=BAT_SCRIPT_CONTENT.encode("utf-8"),
    file_name="TOOL_KICH_HOAT.bat",
    mime="application/bat",
    use_container_width=True,
    key="btn_bat_sidebar"
)
st.sidebar.info("📌 Tải file .bat lưu vào USB, cắm vào PC cần kích hoạt và nháy đúp để tự động mở Web & điền Serial.")

# ----------------- MODULE 1: TIỀN KÍCH HOẠT -----------------
if vai_tro == "1. KTV Tiền Kích Hoạt":
    st.subheader("⚡ GIAI ĐOẠN 1: TIỀN KÍCH HOẠT TẠI CÔNG TY - " + selected_du_an)
    
    st.info(
        "📖 **QUY TRÌNH THỰC HIỆN CHUẨN DÀNH CHO KTV (BƯỚC 1):**\n\n"
        "**1. Lấy Serial tự động:** Bấm nút **`📥 Tải TOOL_KICH_HOAT.bat`** bên dưới lưu vào USB, chạy trên PC để tự động điền Serial.\n\n"
        "**2. Xử lý máy O.E.M:** Nếu máy báo mã ảo `O.E.M`, KTV **bắt buộc gõ tay mã Serial (S/N) in trên tem vỏ thùng/thân máy PC**.\n\n"
        "**3. Chọn Đơn vị & KTV:** Chọn đúng **Điểm / Xã / Trường / Đơn vị** và **Tên KTV** thực hiện.\n\n"
        "**4. Cấp Key & In Tem QR:** Bấm **`🚀 XÁC NHẬN CẤP TRỌN BỘ KEY & KÍCH HOẠT`**, sau đó bấm **`📥 Tải Tem QR (In Nhiệt)`** ở cuối trang in ra 02 bản (dán Thân máy & Vỏ hộp)."
    )

    st.download_button(
        label="📥 Tải TOOL_KICH_HOAT.bat (Chạy trên PC hoặc lưu USB để tự động lấy Serial)",
        data=BAT_SCRIPT_CONTENT.encode("utf-8"),
        file_name="TOOL_KICH_HOAT.bat",
        mime="application/bat",
        use_container_width=True,
        key="btn_bat_main"
    )
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        list_xa = ["Đang tải danh sách..."]
        list_ktv = ["Đang tải danh sách..."]
        try:
            response = requests.post(WEB_APP_URL, json={"action": "GET_DANH_SACH_XA", "maDuAn": selected_du_an}, timeout=20)
            res_data = response.json()
            if res_data.get("status") == "success":
                list_xa = res_data.get("data") if len(res_data.get("data")) > 0 else ["Không có dữ liệu đơn vị"]
                list_ktv = res_data.get("ktv_data") if res_data.get("ktv_data") and len(res_data.get("ktv_data")) > 0 else ["Không có dữ liệu KTV"]
            else:
                list_xa, list_ktv = ["Lỗi lấy dữ liệu đơn vị"], ["Lỗi lấy dữ liệu KTV"]
        except:
            list_xa, list_ktv = ["Lỗi kết nối API"], ["Lỗi kết nối API"]
            st.error("Máy chủ Google đang phản hồi chậm. Vui lòng tải lại trang.")

        ma_xa = st.selectbox("Điểm / Xã / Trường / Đơn vị nhận thiết bị:", list_xa)
        ktv_name = st.selectbox("KTV / Thành viên thực hiện:", list_ktv)
    
    with col2:
        auto_serial = st.query_params.get("serial", "")
        auto_serial = auto_serial.strip("/").replace("/", "-")
        
        clean_auto = auto_serial.replace(" ", "").lower()
        if "o.e.m" in clean_auto or "tobefilled" in clean_auto or clean_auto == "to" or "nhap_tay" in clean_auto:
            st.warning("⚠️ Mainboard O.E.M không có Serial trong chip. Vui lòng gõ tay số S/N trên tem vỏ máy:")
            auto_serial = ""
            
        serial_input = st.text_input("Serial Mainboard (Hoặc S/N trên tem vỏ máy):", value=auto_serial)

    if st.button("🚀 XÁC NHẬN CẤP TRỌN BỘ KEY & KÍCH HOẠT", type="primary", use_container_width=True):
        clean_check = serial_input.strip().replace(" ", "").lower()
        if not clean_check or "o.e.m" in clean_check or "tobefilled" in clean_check or clean_check == "to":
            st.error("❌ CHẶN BẢO MẬT: Vui lòng nhập mã Serial thực tế trên tem dán ở vỏ máy PC!")
            st.stop()
            
        if ktv_name in ["Đang tải danh sách...", "Không có dữ liệu KTV", "Lỗi kết nối API"] or ma_xa in ["Đang tải danh sách...", "Không có dữ liệu đơn vị", "Lỗi kết nối API"]:
            st.error("Vui lòng đảm bảo Đơn vị và Tên KTV hợp lệ!")
        else:
            with st.spinner("Đang rút Key của đơn vị và ghi Nhật ký (Tối đa 30s)..."):
                try:
                    payload = {
                        "action": "TIEN_KICH_HOAT", "maDuAn": selected_du_an,
                        "maXa": ma_xa, "serialMainboard": serial_input.strip(), "ktv": ktv_name
                    }
                    res = requests.post(WEB_APP_URL, json=payload, timeout=30).json()
                    if res.get("status") == "success":
                        st.session_state["last_activated"] = res
                        st.success("✅ Đã cấp bản quyền thành công cho đơn vị: " + ma_xa)
                    else:
                        st.error("❌ TỪ CHỐI CẤP KEY: " + str(res.get("message", "Lỗi không xác định")))
                except:
                    st.error("❌ Mất kết nối đến Google (Timeout). Vui lòng thử lại sau vài giây!")

    if "last_activated" in st.session_state:
        res = st.session_state["last_activated"]
        st.markdown("### 🪟 1. BẢN QUYỀN WINDOWS")
        st.code(res.get("keyWin") if res.get("keyWin") else "Chưa có Key Windows", language="text")
        
        st.markdown("### 📦 2. BẢN QUYỀN OFFICE")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Tài Khoản Microsoft")
            st.code(res.get("tkMS", ""), language="text")
        with c2:
            st.caption("Mật Khẩu")
            st.code(res.get("passMS", ""), language="text")
        with c3:
            st.caption("Key Office")
            st.code(res.get("keyOffice", ""), language="text")
        
        st.markdown("### 🛡️ 3. PHẦN MỀM DIỆT VIRUS")
        v1, v2 = st.columns(2)
        with v1:
            st.caption("TK / Key Diệt Virus")
            st.code(res.get("keyAnti") if res.get("keyAnti") else "Không có", language="text")
        with v2:
            st.caption("⏰ Hạn Sử Dụng")
            st.info(str(res.get("expAnti")) if res.get("expAnti") else "Chưa cập nhật hạn")
        
        redeem_url = "https://setup.office.com/redeem/enter-key?key=" + str(res.get("keyOffice", ""))
        st.markdown("[👉 **Mở trang Redeem 1-chạm**](" + redeem_url + ") | [🔑 **Mở trang Tài khoản Microsoft**](https://account.microsoft.com/services)")

    st.markdown("---")
    st.markdown("### 🖨️ IN TEM NHÃN MÃ QR (DÁN THÂN MÁY & VỎ THÙNG)")
    preview_serial = serial_input.strip() if serial_input.strip() else "CHUA_CO_SERIAL"
    qr_data = selected_du_an + " - " + ma_xa + " - " + preview_serial
    qr_img = generate_qr(qr_data)
    
    col_qr1, col_qr2 = st.columns([1, 3])
    with col_qr1:
        st.image(qr_img, width=180)
    with col_qr2:
        st.write("**Thông tin mã hóa trên tem:** `" + qr_data + "`")
        st.download_button(
            label="📥 Tải Tem QR (In Nhiệt)",
            data=qr_img,
            file_name="Tem_" + preview_serial + ".png",
            mime="image/png",
            use_container_width=True,
            key="btn_qr_main"
        )

# ----------------- MODULE 2: QC ĐỐI SOÁT -----------------
elif vai_tro == "2. QC Đối Soát Đóng Gói":
    st.subheader("📦 GIAI ĐOẠN 2: QC ĐỐI SOÁT & NIÊM PHONG - " + selected_du_an)
    st.info("📖 **QUY TRÌNH QC:** Quét mã QR trên **VỎ HỘP** và **THÂN MÁY PC**, sau đó bấm Kiểm tra đối soát. Báo xanh KHỚP CHÍNH XÁC mới được dán tem niêm phong.")

    col_hop, col_may = st.columns(2)
    with col_hop:
        qr_hop = st.text_input("Mã quét từ VỎ HỘP:", key="hop")
    with col_may:
        qr_may = st.text_input("Mã quét từ THÂN MÁY PC:", key="may")
    
    if st.button("🔍 KIỂM TRA ĐỐI SOÁT", type="primary", use_container_width=True):
        if qr_hop and qr_may:
            if qr_hop.strip() == qr_may.strip():
                raw_qr = qr_hop.strip()
                serial_extracted = raw_qr.split(" - ")[-1].strip() if " - " in raw_qr else raw_qr.split()[-1].strip()
                try:
                    payload = {"action": "QC_PASSED", "serial": serial_extracted}
                    res = requests.post(WEB_APP_URL, json=payload, timeout=20).json()
                    if res.get("status") == "success":
                        st.success("✅ KHỚP CHÍNH XÁC! Đã ghi nhận QC Passed vào Cột I.")
                    else:
                        st.error(res.get("message"))
                except:
                    st.error("Lỗi kết nối API.")
            else:
                st.error("❌ CẢNH BÁO ĐỎ: VỎ HỘP VÀ THÂN MÁY KHÔNG KHỚP NHAU!")
        else:
            st.warning("Vui lòng quét đủ mã của cả Vỏ hộp và Thân máy.")

# ----------------- MODULE 3: BẢO HÀNH -----------------
elif vai_tro == "3. Bảo Hành / Quản Trị":
    st.subheader("🔧 GIAI ĐOẠN 3: CẬP NHẬT BẢO HÀNH (THAY MAINBOARD)")
    st.info("📖 **QUY TRÌNH BẢO HÀNH:** Nhập Serial Mainboard CŨ (hỏng) và Serial Mainboard MỚI (thay thế) để cập nhật liên kết bản quyền trên Nhật ký.")

    old_serial = st.text_input("Nhập Serial Mainboard CŨ (Bị hỏng):")
    new_serial = st.text_input("Nhập Serial Mainboard MỚI (Thay thế):")
    
    if st.button("Cập Nhật Liên Kết Bản Quyền", type="primary", use_container_width=True):
        if old_serial and new_serial:
            try:
                payload = {"action": "DOI_BAO_HANH", "oldSerial": old_serial.strip(), "newSerial": new_serial.strip()}
                res = requests.post(WEB_APP_URL, json=payload, timeout=20).json()
                if res.get("status") == "success":
                    st.success("✅ Đã cập nhật Serial mới thành công vào Cột E & H!")
                else:
                    st.error(res.get("message"))
            except:
                st.error("Lỗi kết nối API.")
# === KET THUC CODE ===
