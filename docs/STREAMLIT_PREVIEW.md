# Bản thử trực tuyến BẢN QUYỀN

Mô hình mở app Streamlit bằng đường link giống cách sử dụng app QUẢN LÝ DỰ ÁN. Bản thử chỉ dùng dữ liệu giả.

## Cấu hình tạo app

| Mục | Giá trị |
|---|---|
| Repository (kho mã nguồn) | dangkyauto10/quan-ly-ban-quyen-da-du-an |
| Branch (nhánh thử) | v2-preview-20261027 |
| Main file path (tệp khởi chạy) | preview_app.py |
| Python | 3.12 |
| Secrets (bí mật cấu hình) | Để trống |

requirements.txt đã dẫn đến requirements-v2.txt để cài thư viện V2. Chỉ gửi đường link sau khi dịch vụ xác nhận triển khai thành công.

## V kiểm tra

1. Chọn Admin (quản trị): xem Tổng quan, Kho key, Thiết bị và Phân bổ.
2. Chọn Người redeem (quy đổi key): đối chiếu hai license (giấy phép) giả cùng một tài khoản. Không đưa key giả lên Microsoft.
3. Chọn KTV (kỹ thuật viên) có việc: báo thành công cho việc đang lỗi.
4. Về Admin: kiểm tra kết quả và Nhật ký.
5. Chọn KTV khác: xác nhận không thấy việc của người trước.
6. Thử Bảo hành: thay serial (số nhận dạng) mainboard, xem lịch sử cũ/mới và duyệt kích hoạt lại.
7. Xem Đồng bộ Google Sheet: bản thử chỉ xuất tệp đối chiếu, không ghi Sheet.

Mỗi phiên trình duyệt có dữ liệu riêng. Đổi vai trò trong cùng phiên để kiểm tra liên tục. Phiên mới hoặc máy khác không thấy thay đổi của phiên trước. Không nhập key thật hoặc thông tin tài khoản thật. Chọn vai trò giả chưa phải đăng nhập/phân quyền thật.

## Trước vận hành

Bản hiện tại dùng cơ sở dữ liệu riêng và xuất báo cáo một chiều sang Sheet; chưa chuyển Sheet thành kho dữ liệu chính. Cần hoàn thiện lưu dữ liệu dùng chung, đăng nhập thật, ghi đồng thời an toàn, quyền Sheet và kiểm tra sao lưu/khôi phục trước khi sử dụng key thật.
