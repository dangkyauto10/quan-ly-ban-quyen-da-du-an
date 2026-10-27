# Quản lý bản quyền V2 — V2-20261027-A

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
