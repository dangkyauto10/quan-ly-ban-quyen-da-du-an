# Môi trường mô phỏng kích hoạt

`MO_KICH_HOAT_TEST.cmd` mở một môi trường dùng chung cho PC và điện thoại trong cùng mạng Wi-Fi. Dữ liệu được lưu riêng tại `activation-test-data/`, không dùng chung với `test-data/` và không ghi vào Google Sheet nghiệp vụ.

## Dữ liệu mẫu

- Đơn vị: `Đơn vị mô phỏng — không có thật`.
- Máy: `TEST-PC-01`, serial giả `MB-SERIAL-MAU-01`.
- Ba việc đang chờ KTV: Windows, Office Retail và Antivirus.
- Key/tài khoản là giá trị giả; Office chỉ đánh dấu redeem mô phỏng, không đăng nhập Microsoft.
- KTV mẫu: `ktv@example.test`; Admin mẫu: `admin@example.test`; QC mẫu: `qc@example.test`.

## Cách thử

1. Chạy `MO_KICH_HOAT_TEST.cmd` trên PC. Truy cập `http://localhost:8502`.
2. Ở mục “Xem thử vai trò”, chọn `ktv@example.test`, vào “Việc của tôi”.
3. Chọn từng license trên `TEST-PC-01`; ghi kết quả thành công/thất bại và nội dung mô phỏng. Chế độ này tự nhận serial giả để thử luồng, không chạy công cụ đọc serial thật.
4. Đổi vai trò sang Admin để xem trạng thái và nhật ký. Có thể mở cùng địa chỉ IPv4 của PC kèm `:8502` trên điện thoại cùng Wi-Fi.

Dữ liệu không kết nối Microsoft, không xác minh license thật, không kích hoạt Windows/Office/Antivirus, không tiêu hao key thật. Môi trường này thử cách giao việc, báo cáo, trạng thái và truy vết; kiểm thử kích hoạt thực tế cần PC và license thật sau này.
