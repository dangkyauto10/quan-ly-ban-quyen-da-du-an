# Web BẢN QUYỀN V2-G — cấu hình một lần bởi quản trị

Mục tiêu: thành viên mở cùng link HTTPS, đăng nhập Google và dùng đúng vai trò đã cấp; không tải ZIP/cài Python trên máy KTV.

## Mã đã có

- preview_app.py: giữ link/nhánh thử hiện tại. Mặc định vẫn dữ liệu giả dùng chung. Khi quản trị đặt web_login_enabled=true trong Secrets, chuyển sang đăng nhập thật và kho PostgreSQL. Cấu hình thiếu/sai thì dừng; không quay lại chọn vai trò giả.
- web_app.py: tệp triển khai riêng luôn yêu cầu đăng nhập thật, không nạp dữ liệu mẫu.
- Đăng nhập Google yêu cầu email_verified=true. Admin cấp đúng email. Người ngoài danh sách hoặc người bị tạm dừng không được vào nghiệp vụ. Đăng nhập thành công không tự cấp quyền.
- Admin thêm/cập nhật/tạm dừng thành viên; không cho xóa quyền Admin hoạt động cuối cùng. Quyền được kiểm tra lại tại từng thao tác, không chỉ ẩn menu.
- Chỉ Admin xem key gốc và redeem. KTV chỉ thấy việc của mình; QC kiểm tra/đóng gói độc lập.
- Khóa mã hóa, phát hiện trùng và ký QR lấy từ Secrets, không tự sinh trong đĩa tạm. Giữ nguyên khóa khi triển khai lại.

## Hai kết nối cần chuẩn bị trước khi bật

1. Google OAuth Web client (ứng dụng đăng nhập Google). Tạo/cấu hình trong Google Auth Platform: thông tin ứng dụng, đối tượng được dùng, client kiểu Web application. Redirect URI phải chính xác https://DIA_CHI_APP_V2/oauth2callback. Nếu ứng dụng ở chế độ thử của Google, thêm các tài khoản thử theo giao diện Google trước. Không dùng mật khẩu Microsoft hay tài khoản dịch vụ để thay OAuth client.
2. PostgreSQL riêng, lưu trữ bền vững, có sao lưu do dịch vụ quản lý. Lấy URL gồm host, database, username/password; mật khẩu trong URL phải được mã hóa URL đúng. Dùng sslmode=require hoặc xác minh chứng chỉ. Không dùng SQLite trên đĩa Streamlit cho dữ liệu thật. Kiểm tra chi phí/giới hạn của dịch vụ trước khi tạo tài nguyên.

Không nhập URL chứa mật khẩu hoặc client_secret vào chat, GitHub, ảnh chụp, ghi chú hay file chia sẻ cho KTV.

## Điền trong Manage app → Settings → Secrets

Dùng .streamlit/web.secrets.example.toml làm cấu trúc, thay tất cả placeholder bằng giá trị thật trên trang quản trị. Không ghi đè các phần Secrets khác đang dùng.

- app.database_url: URL PostgreSQL riêng, không trỏ cơ sở dữ liệu dự án khác.
- app.encryption_key: Fernet key hợp lệ, sinh một lần và sao lưu cùng khóa; không đổi tùy ý.
- app.fingerprint_key và qr_signing_key: hai bí mật ngẫu nhiên riêng ít nhất 32 ký tự, giữ ổn định.
- app.admin_email: email Google thật của quản trị đầu tiên.
- auth: redirect_uri chính xác, cookie_secret ngẫu nhiên ít nhất 32 ký tự, client_id/client_secret do Google cấp và metadata URL Google trong mẫu.
- web_login_enabled=true: bước chuyển sang đăng nhập thật tại cùng preview_app.py. Bản dùng thật bắt đầu ở kho rỗng, không chuyển các key/máy giả tự động.

Bản dùng Secrets [app] hoạt động trên Streamlit Community Cloud. Triển khai Cloud Run có thể dùng DATABASE_URL, LICENSE_ENCRYPTION_KEY, FINGERPRINT_KEY, BOOTSTRAP_ADMIN_EMAIL và QR_SIGNING_KEY từ môi trường; auth vẫn theo cấu hình Streamlit.

## Kiểm tra nghiệm thu trước giao KTV

1. Đăng nhập Admin thực. Tạo KTV/QC bằng email thực được phép; đăng xuất.
2. Email chưa được cấp quyền phải bị chặn. KTV chỉ thấy việc mình; QC không thấy kho key/account. Tạm dừng thành viên đang mở trình duyệt phải chặn thao tác tiếp theo.
3. Dùng dữ liệu giả trong kho riêng để đi hết nhập key → Admin ghi redeem giả → phân công → KTV báo → in tem → QC quét/nhận máy → kiểm tra/đóng gói.
4. Thử 4–6 điện thoại, quyền camera, sai cặp/sai serial/giữ máy trùng/gửi lặp và lỗi kết nối.
5. Khởi động lại app: dữ liệu, quyền và tem còn đúng. Diễn tập sao lưu/khôi phục DB trên kho riêng, giữ đúng khóa, rồi mới dùng key thật.

Chưa xác minh đăng nhập Google thật, PostgreSQL thật, chính sách sao lưu dịch vụ hay camera điện thoại thực trong môi trường của V. Khi chưa có các cấu hình trên, đây là mã sẵn để cấu hình, chưa phải web đăng nhập thật đã triển khai.

Nguồn chính thức:
- https://docs.streamlit.io/develop/tutorials/authentication/google
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- https://docs.streamlit.io/develop/tutorials/databases/postgresql
- https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
