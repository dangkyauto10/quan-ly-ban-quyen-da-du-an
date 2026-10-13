# ----------------- MODULE 1: TIỀN KÍCH HOẠT -----------------
if vai_tro == "1. KTV Tiền Kích Hoạt":
    st.subheader(f"⚡ GIAI ĐOẠN 1: TIỀN KÍCH HOẠT TẠI CÔNG TY - {selected_du_an}")
    
    with st.expander("📖 Xem Hướng Dẫn Sử Dụng Chi Tiết (Bước 1)"):
        st.markdown("""
        1. **Chọn Đơn Vị/Xã**: Lựa chọn đúng xã nhận thiết bị tương ứng trên danh sách.
        2. **Lấy Serial**: Hệ thống tự động quét Serial Mainboard phần cứng.
        3. **Cấp Key**: Bấm **Xác nhận cấp key**, hệ thống sẽ tự động ghép nối bản quyền trống từ kho.
        4. **Redeem**: Bấm nút mở trang Microsoft để nhập thủ công, bảo vệ tài khoản khỏi khóa spam.
        5. **In Tem**: Tải mã QR in nhiệt dán vỏ hộp và thân máy.
        """)

    col1, col2 = st.columns(2)
    with col1:
        # Lấy danh sách Xã và KTV động từ API
        list_xa = ["Đang tải danh sách..."]
        list_ktv = ["Đang tải danh sách..."]
        try:
            res_data = requests.post(WEB_APP_URL, json={"action": "GET_DANH_SACH_XA", "maDuAn": selected_du_an}).json()
            if res_data.get("status") == "success":
                if len(res_data.get("data")) > 0:
                    list_xa = res_data["data"]
                else:
                    list_xa = ["Không có dữ liệu đơn vị"]
                
                # Nạp danh sách KTV
                if res_data.get("ktv_data") and len(res_data.get("ktv_data")) > 0:
                    list_ktv = res_data["ktv_data"]
                else:
                    list_ktv = ["Không có dữ liệu KTV"]
            else:
                 list_xa = ["Lỗi lấy dữ liệu xã"]
                 list_ktv = ["Lỗi lấy dữ liệu KTV"]
        except Exception as e:
             list_xa = ["Lỗi kết nối API"]
             list_ktv = ["Lỗi kết nối API"]

        ma_xa = st.selectbox("Đơn vị / Xã nhận thiết bị:", list_xa)
        ktv_name = st.selectbox("KTV Thực hiện:", list_ktv) # Đã chuyển thành selectbox
    
    with col2:
        serial_input = st.text_input("Serial Mainboard:", value=get_serial_mainboard())
        if st.button("🔍 Tự động quét lại Serial"):
            st.rerun()
            
    if st.button("🚀 XÁC NHẬN CẤP KEY & KÍCH HOẠT", type="primary"):
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
                    st.success("✅ Đã cấp Key thành công! KTV sử dụng thông tin dưới đây để đăng nhập máy PC:")
                    
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
