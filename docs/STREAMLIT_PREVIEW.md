# Bản thử trực tuyến BẢN QUYỀN

Triển khai theo cách mở app Streamlit bằng đường link, giống hình thức sử dụng
app QUẢN LÝ DỰ ÁN. Đây là bản thử dữ liệu giả, chưa phải hệ thống vận hành thật.

## Cấu hình tạo app trên Streamlit Community Cloud

| Mục | Giá trị |
|---|---|
| Repository (kho mã nguồn) | dangkyauto10/quan-ly-ban-quyen-da-du-an |
| Branch (nhánh mã chạy thử) | v2-preview-20261027 |
| Main file path (tệp khởi chạy) | preview_app.py |
| Python | 3.12 |
| Secrets (bí mật cấu hình) | Để trống cho bản thử này |

Tệp requirements.txt ở gốc kho đã dẫn đến requirements-v2.txt để cài thư viện V2.
Sau khi dịch vụ xác nhận triển khai thành công mới lấy đường link thực tế để gửi V.
Không suy đoán địa chỉ app từ tên kho mã.

## V kiểm tra theo thứ tự

1. Chọn Admin (quản trị): xem Tổng quan, Kho key, Thiết bị và Phân bổ.
2. Chọn Người redeem (quy đổi key): đối chiếu hai license (giấy phép) giả
   thuộc cùng tài khoản Microsoft. Không đưa key giả lên Microsoft.
3. Chọn KTV (kỹ thuật viên) có việc: báo lại thành công cho công việc đang lỗi.
4. Chuyển về Admin: kiểm tra kết quả và Nhật ký.
5. Chọn KTV khác: xác nhận không thấy công việc của KTV trước.
6. Thử Bảo hành: ghi serial (số nhận dạng) mainboard mới rồi kiểm tra
   hồ sơ chờ duyệt kích hoạt lại và lịch sử serial cũ/mới.
7. Trong bản thử cục bộ, tab kế hoạch Sheet bị tắt; kiểm tra luồng nhập ở preview
   sau khi cấu hình tài khoản Google runtime.

Mỗi phiên trình duyệt có dữ liệu riêng; đổi vai trò trong cùng phiên để kiểm tra
liên tục. Phiên mới hoặc máy khác không thấy thay đổi của phiên trước.
Không nhập key thật hoặc thông tin tài khoản thật. Đây chưa phải kiểm thử đăng nhập
hay chia sẻ dữ liệu giữa nhiều người.

## Phần còn phải hoàn thiện trước vận hành

Bản hiện tại giữ kho key và trạng thái vận hành trong cơ sở dữ liệu riêng; Admin nạp
kế hoạch nhận PC từ tab 16 trong Google Sheet và xuất báo cáo app sang các tab dữ liệu.
Luồng Google cần tài khoản runtime có quyền trên file. Chưa dùng key thật trước khi
kiểm tra đăng nhập, phân quyền, đồng thời và khôi phục dữ liệu trên môi trường chạy.
