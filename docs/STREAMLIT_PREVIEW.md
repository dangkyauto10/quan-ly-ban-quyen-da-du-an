# Kiểm thử trực tuyến app BẢN QUYỀN

App thử dùng Streamlit Community Cloud. Cấu hình đang theo repo
`dangkyauto10/quan-ly-ban-quyen-da-du-an`, nhánh `v2-preview-20261027` và tệp
khởi chạy `preview_app.py`.

## Hai chế độ chạy

- `team_test`: dữ liệu giả dùng chung để thử giao diện/quy trình. Không đọc hoặc
  ghi Google Sheet và dữ liệu có thể mất khi dịch vụ khởi động lại.
- Đăng nhập thật: bật `web_login_enabled=true`, dùng Google OAuth và PostgreSQL
  thử riêng. Dữ liệu lưu bền hơn; chỉ dùng key giả trong giai đoạn kiểm thử.

Không để chế độ thử dùng chung truy cập kho hoặc dữ liệu của dự án khác.

## Kết nối Google Sheet

App dùng Google Sheets API với danh tính service account trong cấu hình
`google_service_account` hoặc Application Default Credentials của môi trường.
Google Sheets API phải bật và email service account phải được chia sẻ với quyền
Editor trên đúng file. Bí mật không được đưa vào GitHub, chat hay tài liệu.

Trong app đăng nhập thật, Admin có thể đọc/xem trước rồi xác nhận nạp tab
`16_KE_HOACH_CAP_PC` và `17_TAI_KHOAN_MS`; app xuất báo cáo vào tabs `01–12` và
ghi kết quả tại `15_DONG_BO_APP`. Chế độ `team_test` không thực hiện các kết nối này.

## Trình tự kiểm thử nghiệp vụ

1. Dùng dữ liệu giả: nạp kế hoạch một dự án có Windows, Office và Antivirus;
   kiểm tra dự án, đơn vị, điểm, số PC, SKU và quota.
2. Nạp danh sách email Microsoft thử tại tab 17; kiểm tra xem trước, trùng email,
   sai tên dự án/đơn vị và nạp lặp không tạo tài khoản trùng.
3. Nhập key giả riêng cho từng loại; Office Retail đi theo redeem Microsoft giả,
   Windows/Antivirus đi theo luồng của nhà cung cấp.
4. Admin giao tài khoản Office đã redeem và từng license cho đúng KTV. Một KTV
   theo trọn một PC từ kích hoạt tới serial, hai tem, nhận tem và đóng hộp.
5. Kiểm tra trạm in USB, quét hai QR bằng điện thoại, xác minh đơn vị/PC/serial,
   thử sai cặp và để QC độc lập xác nhận.
6. Thử một hồ sơ bảo hành thay mainboard; kiểm tra serial cũ/mới, lần kích hoạt,
   tem mới và nhật ký.
7. Với môi trường đăng nhập thật và cơ sở dữ liệu thử riêng, xác nhận đồng bộ
   báo cáo sang Sheet rồi đọc lại header, dòng `APP-` và log ở tab 15.

Không dùng key thật hoặc tài khoản Microsoft thật để kiểm thử quy trình. App không
tự redeem hay tự xác minh trạng thái kích hoạt với Microsoft/nhà cung cấp; KTV ghi
kết quả sau khi kiểm tra thực tế. Trước khi mở dùng thật cần nghiệm thu đăng nhập,
quyền KTV/QC, cơ sở dữ liệu dùng chung, quyền Sheet và khả năng sao lưu/khôi phục.
