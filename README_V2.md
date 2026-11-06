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

Kế hoạch đơn vị/điểm/SKU được nạp từ tab `16_KE_HOACH_CAP_PC`; email tài khoản
Microsoft được nạp theo lô từ tab `17_TAI_KHOAN_MS`, Admin xem trước và xác nhận.
Account đã redeem được giao đích danh cho KTV; PC chỉ qua QC sau khi KTV xác nhận
riêng dán cặp tem, đối serial và đóng hộp. Lịch sử bảo hành/làm lại được giữ để tra cứu.
Báo cáo đi từ app sang các tab dữ liệu, còn kho key đầy đủ vẫn ở kho bảo mật riêng.
Xem `docs/DONG_BO_GOOGLE_SHEET.md`.

Tab 16 quản lý quota riêng theo Windows, Office và Antivirus. Tab 17 chỉ nhập danh
sách tài khoản Microsoft dùng cho Office Retail đã redeem; Windows và Antivirus
theo SKU và luồng kích hoạt của nhà cung cấp. Sheet là đầu vào đã xác nhận và báo cáo
một chiều từ app, còn trạng thái vận hành chính được giữ trong cơ sở dữ liệu app.

