# Triển khai V2 — bản thử nghiệm 2026-10-27

## Trạng thái
Đã có mã chạy thử và kiểm tra trên SQLite. Chưa triển khai Cloud Run/Cloud SQL,
chưa kiểm chứng OIDC Google, PostgreSQL thực, hoặc Microsoft activation trực tiếp.
Bản đầu quản lý 1 license / 1 thiết bị; license nhiều seat và MAK/KMS chưa hỗ trợ tự động.
Redeem và kiểm tra trạng thái kích hoạt thực hiện tại Microsoft, app chỉ ghi xác nhận.
Không có API tạo tài khoản Microsoft, không lưu mật khẩu Microsoft hoặc MFA.

## Chạy xem thử trên máy riêng
Python 3.12, tại thư mục gốc repo:

    pip install -r requirements-v2.txt
    APP_MODE=demo streamlit run v2_app.py

Windows PowerShell:

    $env:APP_MODE='demo'
    streamlit run v2_app.py

Chọn vai trò minh họa ở thanh bên. Mỗi phiên trình duyệt có SQLite riêng trong
thư mục tạm của hệ điều hành (Windows/Linux). Khóa mã hóa chỉ nằm trong phiên,
không có quy trình khôi phục demo; file tạm có thể còn đến khi hệ điều hành dọn dẹp.
Không dùng key thật trong demo.

Có sẵn một đơn vị, một tài khoản giả, bốn người dùng giả, ba key giả và hai máy.
Hai key đã ghi nhận redeem giả vào cùng tài khoản: một máy báo thành công,
một máy báo lỗi. Key thứ ba chờ kiểm tra; KTV thứ hai chưa có công việc.
Mở Hướng dẫn theo vai trò hoặc Cách thực hiện ở từng màn hình để xem cách thao tác.
Có thể báo lại thành công cho việc đang lỗi, sau đó dùng Admin xem lịch sử.

Muốn thử thêm luồng mới: nhập key giả RRRRR-SSSSS-TTTTT-UUUUU-VVVVV, Office,
Retail (bán lẻ), ACCOUNT_REDEEM (quy đổi vào tài khoản), rồi thực hiện kiểm tra,
ghi nhận redeem giả, thêm máy mới và giao KTV. Không thử key giả trên Microsoft.

## Production: cấu hình cần có trước khi đưa key thật
- Cloud Run service, Cloud SQL PostgreSQL và Artifact Registry cùng vùng phù hợp.
- Bật billing; tính chi phí Cloud SQL theo vùng/cấu hình trước khi tạo tài nguyên.
  Đây là dịch vụ có chi phí định kỳ, không mặc định là miễn phí.
- Runtime service account riêng với Cloud SQL Client; Secret Manager Secret Accessor
  chỉ trên những secret cần dùng. Không cấp Owner/Editor cho runtime.
- Bật Cloud SQL backups + PITR; diễn tập restore vào instance riêng.
- Khóa runtime DB theo schema ứng dụng; audit không cho UPDATE/DELETE bởi runtime.
  meta.create_all chỉ tạo schema ban đầu, chưa thay thế migration cho nâng cấp về sau.
- DATABASE_URL=postgresql+psycopg://... sử dụng Cloud SQL Unix socket:
  postgresql+psycopg://USER:PASSWORD@/DATABASE?host=/cloudsql/PROJECT:REGION:INSTANCE
  Dùng URL encoding cho user/password. Chỉ lưu URL trong Secret Manager.
- LICENSE_ENCRYPTION_KEY: Fernet key riêng, sinh một lần trong môi trường tin cậy.
- FINGERPRINT_KEY: bí mật ổn định ít nhất 32 ký tự, dùng HMAC phát hiện key trùng.
- BOOTSTRAP_ADMIN_EMAIL: email Google đã xác minh của Admin đầu tiên.
- APP_MODE=production. Chế độ production từ chối SQLite và không có chọn vai trò tự do.
- Mount secret auth.toml tại /home/appuser/.streamlit/secrets.toml theo auth.example.toml.
  Tạo OAuth Web client Google; redirect chính xác https://APP_URL/oauth2callback.
  App dùng OIDC Streamlit, kiểm tra email_verified và allowlist/role trong DB.
  Người đăng nhập hợp lệ nhưng chưa được Admin cấp quyền sẽ bị chặn.
- Mật khẩu và mã khôi phục Microsoft nằm ngoài app, do đơn vị sở hữu quản lý.
- Khóa Fernet hiện mã hóa dữ liệu ở tầng ứng dụng và được phân phối qua Secret Manager.
  Chưa tích hợp KMS envelope encryption trực tiếp; phải giữ backup khóa an toàn,
  không đổi khóa/FINGERPRINT_KEY trên dữ liệu đang dùng trước khi có quy trình migration.

## GitHub → Cloud Run
Dockerfile.v2 sẵn cho build; CI chỉ chạy kiểm tra, không tự triển khai.
Muốn deploy từ GitHub Actions: cấu hình OIDC Workload Identity Federation giới hạn
đúng repo/branch/environment, service account deploy riêng, không dùng JSON key dài hạn.
Thêm workflow deploy khi biết project, region, service, Cloud SQL connection và policy
phê duyệt của công ty; các giá trị này chưa được cung cấp nên chưa tạo workflow ghi Cloud.
Build bằng Dockerfile.v2. Runtime cổng 8080, user 10001. App không gọi Apps Script/Sheets.

## Tiêu chí trước cutover
- Kiểm tra 2 request đồng thời trên PostgreSQL thật; rollback, idempotency và constraint.
- Kiểm tra OIDC login/logout, allowlist, người khác không xem/gửi công việc của KTV.
- Đi hết quy trình với một license được công ty cho phép dùng thử; redeem là thao tác
  không thể hoàn tác bằng app, phải kiểm tra tài khoản/điều kiện trước khi xác nhận.
- Xác minh trạng thái Office/Windows thực, phân biệt loại license và quyền chuyển máy.
- Kiểm tra backup/restore cả DB và encryption key; chỉ sau đó mới cho nhập key thật.
- Repo hiện công khai; chỉ chứa mã và dữ liệu giả. Đổi repo sang private là cấu hình riêng
  cần chủ repo thực hiện; không đưa secrets hoặc file dữ liệu vào git.
- V2 dùng ledger mới trống. Chỉ xử lý xóa dữ liệu cũ và ngừng Apps Script sau khi đã
  sao lưu/xác minh phạm vi và cutover đạt. Bản này không có lệnh xóa dữ liệu hệ thống cũ.

## Phạm vi tiếp theo
Thu hồi/giao lại license, vô hiệu người dùng, nhiều seat, nhập danh mục hàng loạt,
QR tài sản, ảnh lưu riêng, báo cáo Sheets tự đồng bộ và KMS rotation chưa được triển khai.
CSV hiện chỉ xuất dữ liệu quản lý đã che key; nội dung bắt đầu bằng công thức được escape.

Nguồn thiết kế:
- https://docs.streamlit.io/develop/concepts/connections/authentication
- https://docs.cloud.google.com/sql/docs/postgres/connect-run
- https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
- https://support.microsoft.com/vi-vn/microsoft-365-activation-licensing/this-product-key-has-already-been-used-error-in-office
