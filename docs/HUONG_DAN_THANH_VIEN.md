# Hướng dẫn thành viên — kiểm thử nghiệp vụ BẢN QUYỀN

App theo dõi Windows, Microsoft Office và Antivirus (diệt virus) riêng theo key,
SKU, license và luồng kích hoạt. Google Sheet là đầu vào có xem trước/xác nhận và
nơi nhận báo cáo; cơ sở dữ liệu app giữ trạng thái xử lý chính.

## Admin (người quản trị)

1. Tại Người dùng: nhập email Google đã xác minh; chọn quản trị, người quản lý redeem
(quy đổi key) hoặc KTV (kỹ thuật viên).
2. Tại Google Sheet, nhập tab 16 theo đơn vị/điểm/SKU và tab 17 theo email Microsoft
và người quản lý. Trong app, đọc, xem trước rồi xác nhận nạp. Mật khẩu và MFA
(xác thực nhiều bước) do người quản lý tài khoản giữ ngoài app.
3. Tại Kho key: nhập mã lô, phần mềm, phiên bản/SKU (mã phân biệt sản phẩm), kênh cấp
phép và key, mỗi dòng một key. Lô có key trùng sẽ bị từ chối, không ghi dở dang.
4. Giao người kiểm tra đối chiếu chứng từ, sản phẩm và điều kiện sử dụng; ghi căn cứ.
5. Tại Thiết bị: tạo mã tem máy nội bộ, chọn đơn vị, nhập serial (số nhận dạng), model
(kiểu máy). Công cụ đọc serial tại PC (máy tính) chỉ đọc và hiển thị thông tin cục bộ.
6. Tại Phân bổ: chọn bản quyền sẵn sàng, máy nhận và KTV. Với Office đã redeem, tài
khoản Microsoft phải cùng đơn vị với máy nhận và được giao cho KTV phụ trách.
7. Tại Kích hoạt: theo dõi kết quả KTV, tiếp nhận mã lỗi và phân công hỗ trợ.
8. Tại Bảo hành: chọn máy, lưu serial mainboard (bo mạch chủ) mới và căn cứ; kiểm tra
quyền xử lý theo license (giấy phép bản quyền), ghi căn cứ duyệt rồi giao kích hoạt lại.
9. Tại Nhật ký: tra ai đã nhập, kiểm tra, xem key, redeem, giao việc và xử lý bảo hành.

## Người quản lý redeem (quy đổi key)

1. Đối chiếu đơn vị, email Microsoft và người quản lý tài khoản.
2. Tại Kho key: chọn hồ sơ mới nhận, kiểm tra sản phẩm/SKU, nguồn gốc và điều kiện.
Kiểm tra định dạng key chỉ phát hiện lỗi hình thức, không xác thực với nhà cung cấp.
3. Tại Redeem Office: chọn key đã kiểm tra, hiện key cho tác vụ hiện tại nếu cần.
4. Thực hiện trên trang Microsoft bằng đúng tài khoản. App chưa tự đăng ký tài khoản,
redeem hoặc đọc kết quả trực tiếp từ Microsoft.
5. Chỉ ghi nhận thành công sau khi thấy đúng sản phẩm trong đúng tài khoản; ghi tên
sản phẩm hoặc tham chiếu xác nhận. Gặp lỗi/chưa rõ cần báo Admin.
6. Trong demo chỉ ghi nhận kết quả giả trong app, không thử key giả trên Microsoft.
Không dùng một quy tắc redeem chung cho Windows, Office và phần mềm diệt virus.

## KTV (kỹ thuật viên)

1. Đăng nhập email được cấp quyền và mở Việc của tôi.
2. Đối chiếu mã máy, serial, đơn vị, sản phẩm và tài khoản Microsoft được phân.
Nếu sai máy, báo Admin đối chiếu trước khi tiếp tục.
3. Cài đúng phiên bản. Phối hợp người quản lý tài khoản để đăng nhập theo cách đã duyệt;
không đưa mật khẩu/MFA vào app.
4. Xác minh trạng thái kích hoạt tại phần mềm. App ghi nhận liên kết serial để theo dõi,
chưa tự kích hoạt Office dựa trên serial hoặc tự kiểm chứng Microsoft.
5. Chọn đúng việc; báo thành công hoặc thất bại. Thất bại cần mã lỗi và nội dung.
Đường dẫn ảnh minh chứng nếu có cần tránh lộ key, mật khẩu và dữ liệu cá nhân.
6. Sau khi xử lý lỗi, gửi lại cùng công việc. Nhật ký giữ cả sự kiện thất bại trước đó.
7. Không thấy việc: đối chiếu email đang đăng nhập, nhờ Admin kiểm tra phân công.

## Đọc kết quả và tra cứu

CSV (tệp bảng mở bằng Excel) và đồng bộ Google Sheet không chứa key gốc. Tab 16–17
được app đọc sau khi Admin xem trước/xác nhận; app xuất báo cáo vào tabs 01–12 và
ghi lần đồng bộ ở tab 15. Sửa báo cáo trong Sheet không sửa trạng thái chính trong app.
UTC là giờ quốc tế; kiểm thử thời gian theo nhật ký app.

## Nội dung còn chờ anh Vỹ chốt

Phương thức kích hoạt thực tế, khả năng đọc serial theo từng model mainboard, quyền
chuyển máy của từng SKU và chính sách lưu trữ/sao lưu vẫn phải đối chiếu nhà cung cấp
và môi trường triển khai. Không dùng key thật cho tới khi nghiệm thu các mục đó.

