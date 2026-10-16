import streamlit as st
import pandas as pd
import requests
import qrcode
from io import BytesIO

st.set_page_config(page_title="Hệ Thống Bản Quyền Đa Dự Án", page_icon="🛡️", layout="wide")

# ================= CẤU HÌNH API & LINK WEB =================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxQ1Yzr_u0VtaBQErzXR4YqRAwGNcw9ePRy6jJ4CM9n9H2S-i7EkobHKYjrPl4Y2toL/exec"
STREAMLIT_APP_URL = "https://quan-ly-ban-quyen-da-du-an-vwhggefuh7qfwpplhpelcb.streamlit.app"
# ===========================================================

def generate_qr(data_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# Nội dung file .bat: Không dùng f-string, không dùng ngoặc nhọn hay dấu gạch đứng để chống lỗi khi Copy-Paste
BAT_SCRIPT_CONTENT = (
    "@echo off\r\n"
    "title TOOL LAY SERIAL TU DONG - DA DU AN\r\n"
    "color 0A\r\n"
    "echo DANG QUET SERIAL PHAN CUNG MAY TINH...\r\n"
    "set \"SN=\"\r\n"
    "for /f \"delims=\" %%A in ('powershell -NoProfile -Command \"$s = (Get-CimInstance Win32_BIOS).SerialNumber; if (-not $s -or$s -like '*O.E.M*' -or $s -like '*To be filled*' -or$s -like '*Default*') { $s = (Get-CimInstance Win32_BaseBoard).SerialNumber }; if (-not$s -or $s -like '*O.E.M*' -or$s -like '*To be filled*') { $s = (Get-CimInstance Win32_ComputerSystemProduct).IdentifyingNumber }; if (-not$s -or $s -like '*O.E.M*' -or$s -like '*To be filled*') { $s = 'NHAP_TAY_TREN_VO_MAY' };$s -replace '[^a-zA-Z0-9_-]',''\"') do set \"SN=%%A\"\r\n"
    "echo Serial doc duoc: %SN%\r\n"
    "start \"\" \"" + STREAMLIT_APP_URL + "/?serial=%SN%\"\r\n"
    "exit\r\n"
)

st.header("🛡️ HỆ THỐNG QUẢN TRỊ BẢN QUYỀN ĐA DỰ ÁN")
st.markdown("---")

# TỰ ĐỘNG LẤY DANH SÁCH DỰ ÁN ĐỘNG TỪ DM_CHUAN / KHO_KEY_DA_NHAP
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
st.sidebar.info(
    "📌 **HƯỚNG DẪN NHANH:**\n"
    "1. Tải file `TOOL_KICH_HOAT.bat` lưu vào USB.\n"
    "2. Cắm vào máy PC cần kích hoạt và nháy đúp chạy file.\n"
    "3. Trình duyệt sẽ tự động mở lên và điền sẵn mã Serial."
)

# ----------------- MODULE 1: TIỀN KÍCH HOẠT -----------------
if vai_tro == "1. KTV Tiền Kích Hoạt":
    st.subheader(f"⚡ GIAI ĐOẠN 1: TIỀN KÍCH HOẠT TẠI CÔNG TY - {selected_du_an}")
    
    # 1. HIỂN THỊ TRỰC DIỆN HƯỚNG DẪN (KHÔNG ẨN)
    st.info(
        "📖 **QUY TRÌNH THỰC HIỆN CHUẨN DÀNH CHO KTV (BƯỚC 1):**\n\n"
        "**1. Lấy Serial tự động:** Bấm nút **`📥 Tải TOOL_KICH_HOAT.bat`** ngay bên dưới để tải về USB. Cắm vào máy tính đang cài đặt và chạy file để tự động mở Web và điền Serial.\n\n"
        "**2. Xử lý máy O.E.M (Nếu có):** Nếu hệ thống cảnh báo mã `To be filled by O.E.M.` (do nhà sản xuất không nạp Serial vào Mainboard), KTV **bắt buộc gõ tay mã Serial (S/N) in trên tem dán ở vỏ thùng hoặc thân máy PC** vào ô Serial Mainboard.\n\n"
        "**3. Chọn Đơn vị & KTV:** Chọn đúng **Điểm / Xã / Trường / Đơn vị** nhận máy và **Tên KTV** thực hiện.\n\n"
        "**4. Cấp Key & Kích hoạt:** Bấm nút **`🚀 XÁC NHẬN CẤP TRỌN BỘ KEY & KÍCH HOẠT`**. Sử dụng Tài khoản Microsoft và Key hiện ra trên màn hình để kích hoạt máy.\n\n"
        "**5. In & Dán Tem QR:** Bấm nút **`📥 Tải Tem QR (In Nhiệt)`** ở cuối màn hình, in ra **02 bản** (01 bản dán lên **Thân máy PC**, 01 bản dán lên **Vỏ hộp**) để bàn giao sang bộ phận QC."
    )

    # 2. HIỂN THỊ TRỰC DIỆN NÚT TẢI TOOL .BAT NGAY TRÊN MÀN HÌNH CHÍNH
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
        except Exception as e:
             list_xa, list_ktv = ["Lỗi kết nối API"], ["Lỗi kết nối API"]
             st.error("Máy chủ Google đang xử lý quá chậm hoặc bị chặn. Vui lòng tải lại trang.")

        ma_xa = st.selectbox("Điểm / Xã / Trường / Đơn vị nhận thiết bị:", list_xa)
        ktv_name = st.selectbox("KTV / Thành viên thực hiện:", list_ktv)
    
    with col2:
        query_params = st.query_params
        auto_serial = query_params.get("serial", "")
        
        # Làm sạch dấu gạch chéo / ở đầu và cuối (VD: /HFW42N2/TW3207086D0001/ -> HFW42N2-TW3207086D0001)
        auto_serial = auto_serial.strip("/").replace("/", "-")
        
        clean_auto = auto_serial.replace(" ", "").lower()
        if "o.e.m" in clean_auto or "tobefilled" in clean_auto or clean_auto == "to" or "nhap_tay" in clean_auto:
            st.warning("⚠️ Máy tính này dùng Mainboard O.E.M (không nạp Serial trong chip). Vui lòng gõ tay số Serial in trên tem vỏ máy vào ô dưới đây:")
            auto_serial = ""
            
        serial_input = st.text_input("Serial Mainboard (Hoặc S/N trên tem vỏ máy):", value=auto_serial, placeholder="Nhập chính xác mã S/N trên vỏ máy...")

    # 3. NÚT XÁC NHẬN CẤP KEY
    if st.button("🚀 XÁC NHẬN CẤP TRỌN BỘ KEY & KÍCH HOẠT", type="primary", use_container_width=True):
        clean_check = serial_input.strip().replace(" ", "").lower()
        if not clean_check or "o.e.m" in clean_check or "tobefilled" in clean_check or clean_check == "to":
            st.error("❌ CHẶN BẢO MẬT: Không được dùng mã Serial ảo 'To be filled by O.E.M.'! Vui lòng nhập mã Serial thực tế trên tem dán ở vỏ máy PC!")
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
                    response = requests.post(WEB_APP_URL, json=payload, timeout=30)
                    res = response.json()
                    
                    if res.get("status") == "success":
                        st.session_state["last_activated"] = {
                            "ma_xa": ma_xa,
                            "serial": serial_input.strip(),
                            "du_an": selected_du_an,
                            "res": res
                        }
                        st.success(f"✅ Đã cấp bản quyền thành công cho đơn vị: **{ma_xa}** ({selected_du_an})!")
                    else:
                        st.error(f"❌ TỪ CHỐI CẤP KEY: {res.get('message', 'Lỗi không xác định')}")
                except Exception as e:
                    st.error("❌ Mất kết nối đến Google (Timeout). Máy chủ đang phản hồi chậm, vui lòng thử lại sau vài giây!")

    # HIỂN THỊ THÔNG TIN KEY KHI ĐÃ KÍCH HOẠT
    if "last_activated" in st.session_state:
        act_data = st.session_state["last_activated"]
        res = act_data["res"]
        st.markdown("### 🪟 1. BẢN QUYỀN WINDOWS")
        st.code(res.get("keyWin") if res.get("keyWin") else "Chưa có Key Windows trong kho", language="text")
        
        st.markdown("### 📦 2. BẢN QUYỀN OFFICE")
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.caption("Tài Khoản Microsoft (Đã Redeem)")
            st.code(res.get("tkMS", ""), language="text")
        with c2: 
            st.caption("Mật Khẩu")
            st.code(res.get("passMS", ""), language="text")
        with c3: 
            st.caption("Key Office (Đối chiếu)")
            st.code(res.get("keyOffice", ""), language="text")
        
        st.markdown("### 🛡️ 3. PHẦN MỀM DIỆT VIRUS & HẠN SỬ DỤNG")
        v1, v2 = st.columns(2)
        with v1:
            st.caption("TK / Key Diệt Virus")
            st.code(res.get("keyAnti") if res.get("keyAnti") else "Không có", language="text")
        with v2:
            st.caption("⏰ Hạn Sử Dụng Diệt Virus")
            st.info(f"📅 **{res.get('expAnti')}**" if res.get("expAnti") else "Chưa cập nhật hạn")
        
        st.markdown("---")
        st.markdown("### 🌐 ĐĂNG NHẬP KÍCH HOẠT OFFICE HOẶC REDEEM")
        redeem_url = f"https://setup.office.com/redeem/enter-key?key={res.get('keyOffice', '')}"
        st.markdown(f"""
        <a href="{redeem_url}" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #0078D4; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
            👉 Mở trang Redeem 1-chạm (Nếu Key chưa nạp)
        </a>
        <a href="https://account.microsoft.com/services" target="_blank" style="display: inline-block; margin-left: 10px; padding: 10px 20px; background-color: #107C41; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
            🔑 Mở trang Tài khoản Microsoft (Nếu đã nạp sẵn)
        </a>
        """, unsafe_allow_html=True)

    # 4. HIỂN THỊ TRỰC DIỆN KHU VỰC IN TEM QR & NÚT TẢI TEM QR (LUÔN HIỆN SẴN, KHÔNG ẨN)
    st.markdown("---")
    st.markdown("### 🖨️ IN TEM NHÃN MÃ QR (DÁN THÂN MÁY & VỎ THÙNG)")
    preview_serial = serial_input.strip() if serial_input.strip() else "CHUA_CO_SERIAL"
    qr_data = selected_du_an + " - " + ma_xa + " - " + preview_serial
    qr_img = generate_qr(qr_data)
    
    col_qr1, col_qr2 = st.columns([1, 3])
    with col_qr1:
        st.image(qr_img, width=180, caption=f"QR: {qr_data}")
    with col_qr2:
        st.write(f"**Thông tin mã hóa trên tem:** `{qr_data}`")
        st.download_button(
            label="📥 Tải Tem QR (In Nhiệt)",
            data=qr_img,
            file_name=f"Tem_{preview_serial}.png",
            mime="image/png",
            use_container_width=True,
            key="btn_qr_main"
        )
        st.caption("💡 Lưu ý: Đảm bảo đã nhập đúng Serial Mainboard và bấm Xác nhận cấp Key trước khi tải tem đem đi in.")

# ----------------- MODULE 2: QC ĐỐI SOÁT -----------------
elif vai_tro == "2. QC Đối Soát Đóng Gói":
    st.subheader(f"📦 GIAI ĐOẠN 2: QC ĐỐI SOÁT & NIÊM PHONG - {selected_du_an}")
    
    st.info(
        "📖 **QUY TRÌNH ĐỐI SOÁT ĐÓNG GÓI DÀNH CHO QC (BƯỚC 2):**\n\n"
        "**1. Quét mã Vỏ hộp:** Đặt con trỏ chuột vào ô **Mã quét từ VỎ HỘP**, dùng súng bắn mã vạch quét tem QR dán ngoài thùng carton.\n\n"
        "**2. Quét mã Thân máy:** Đặt con trỏ chuột vào ô **Mã quét từ THÂN MÁY PC**, quét tiếp tem QR dán trên vỏ case máy tính.\n\n"
        "**3. Xác nhận Niêm phong:** Bấm **`🔍 KIỂM TRA ĐỐI SOÁT`**. Nếu hệ thống báo xanh **`KHỚP CHÍNH XÁC`**, trạng thái **`QC Passed - Đã Niêm Phong`** sẽ tự động lưu vào Cột I trên Google Sheets. Lúc này QC mới được phép đóng thùng và dán tem niêm phong."
    )

    col_hop, col_may = st.columns(2)
    with col_hop: qr_hop = st.text_input("Mã quét từ VỎ HỘP:", key="hop")
    with col_may: qr_may = st.text_input("Mã quét từ THÂN MÁY PC:", key="may")
    
    if st.button("🔍 KIỂM TRA ĐỐI SOÁT", type="primary", use_container_width=True):
        if qr_hop and qr_may:
            if qr_hop.strip() == qr_may.strip():
                # Hỗ trợ tách mã Serial cho cả định dạng cũ và mới
                raw_qr = qr_hop.strip()
                serial_extracted = raw_qr.split(" - ")[-1].strip() if " - " in raw_qr else raw_qr.split()[-1].strip()
                try:
                    payload = {"action": "QC_PASSED", "serial": serial_extracted}
                    res = requests.post(WEB_APP_URL, json=payload, timeout=20).json()
                    if res.get("status") == "success":
                        st.success("✅ KHỚP CHÍNH XÁC! Đã ghi nhận QC Passed vào đúng Cột I. Cho phép dán tem niêm phong!")
                    else:
                        st.error(res.get("message"))
                except:
                    st.error("Lỗi kết nối API.")
            else:
                st.error("❌ CẢNH BÁO ĐỎ: VỎ HỘP VÀ THÂN MÁY KHÔNG KHỚP NHAU! Yêu cầu kiểm tra và sắp xếp lại ngay!")
        else:
            st.warning("Vui lòng qu
