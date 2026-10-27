# Quản lý bản quyền V2 — V2-20261027-C

Bản xem thử nghiệp vụ cho anh Vỹ, viết bằng Streamlit/Python, không dùng Apps Script.
Entry point: `v2_app.py`. App cũ `app.py` giữ riêng trên main.

Đã có: Admin nhập lô key được mã hóa, phát hiện trùng và rollback cả lô;
V kiểm tra/redeem vào tài khoản đơn vị; hồ sơ máy; Admin giao license cho KTV;
KTV chỉ xem/gửi việc được giao; ghi thành công/thất bại; thay mainboard giữ lịch sử;
Admin duyệt kích hoạt lại; nhật ký; báo cáo CSV đã che key; công cụ PowerShell đọc serial cục bộ.

Mỗi tài khoản có thể có nhiều bản ghi license; từng license được quản lý và gán riêng
cho một máy. Không mặc định mọi loại license đều được redeem qua Microsoft account.
Office Retail đã xác minh dùng luồng redeem; loại khác cần hướng dẫn nhà cung cấp.

Đây là bản thử, chưa là hệ thống production. Xem `docs/DEPLOYMENT.md` để chạy demo,
cấu hình Cloud Run/PostgreSQL, OIDC và các điều kiện trước khi nhập key thật.

Kiểm tra: `python -m pytest -q tests` (pytest cài riêng).

Bản B thêm nhãn tiếng Việt, hướng dẫn theo vai trò và ví dụ 2 license cùng tài khoản, 2 máy, 1 kết quả thành công/1 kết quả lỗi. Xem docs/HUONG_DAN_THANH_VIEN.md và docs/DOI_CHIEU_GOOGLE_SHEET.md.

Bản C thêm xuất/đồng bộ báo cáo một chiều app → Google Sheet cho Admin. Đã ghi một
bản minh họa 37 bản ghi qua kết nối Drive; app trực tuyến chưa được triển khai/cấp quyền.
Xem `docs/DONG_BO_GOOGLE_SHEET.md`. Dòng APP- do app quản lý, góp ý giữ tại tab 14.
