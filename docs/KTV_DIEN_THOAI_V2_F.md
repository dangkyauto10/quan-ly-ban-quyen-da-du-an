# V2-F — kiểm tra và đóng gói trên điện thoại

## Bản thử trực tuyến dùng chung

Nhánh v2-preview-20261027, tệp preview_app.py giờ mở kho dữ liệu thử dùng chung. Đây không phải triển khai dữ liệu thật: mọi người có thể chọn danh tính mẫu, chưa có đăng nhập riêng. Chỉ dùng key giả và thông tin giả.

Trên dịch vụ Streamlit HTTPS, camera_input cho chụp ảnh từng QR bằng camera điện thoại. Đây chưa phải quét camera trực tiếp liên tục. Trình duyệt có thể hỏi quyền camera; chỉ cấp quyền cho đúng trang app. Nếu camera không mở, dùng Chọn ảnh để thử. Không cần máy quét mã vạch riêng.

SQLite và khóa tem nằm trong thư mục test-data trên máy chạy app, không được đưa lên GitHub. Trên Cloud, dữ liệu và tem thử có thể mất hiệu lực khi dịch vụ khởi động lại/tái tạo môi trường hoặc triển khai lại. Cần kho dữ liệu bền vững và đăng nhập xác thực trước vận hành thật.

## Cách đội thử 4–6 người

1. Admin dùng PC: chuẩn bị hai máy mẫu; PC-MAU-02 cần KTV báo lại thành công. Lập kế hoạch số PC, cấp số từng máy rồi in cặp tem. Chỉ máy đã báo kích hoạt thành công tất cả giấy phép mới có trong danh sách in.
2. Gửi đúng link app V2 cho đội. Mỗi người chọn một danh tính khác nhau: Bộ phận kiểm tra độc lập mẫu hoặc Người kiểm tra số 2–6. Đây là danh tính giả dùng thử, không bảo vệ khỏi việc người khác chọn cùng danh tính.
3. Mở Đối chiếu tem và kiểm tra. Chụp tem thân PC, rồi tem vỏ hộp. Nếu chưa in tem, dán hai mã thử vào hai ô QR.
4. App hiển thị ĐÚNG CẶP hoặc SAI CẶP. Cùng loại tem/thiếu một tem thì chưa đủ đối chiếu. Đúng cặp vẫn phải đọc serial trên máy và kiểm tra kỹ thuật.
5. Bấm Nhận máy / gia hạn 15 phút kiểm tra. Nếu người khác đang giữ máy thì bị chặn. Có thể bấm Trả máy nếu chưa xử lý; Admin có thể thu hồi lượt kiểm tra. Hết hạn phải nhận/gia hạn trước khi gửi.
6. Nhập serial thực; chọn Đạt/Không đạt, nội dung kiểm tra và xác nhận đã kiểm tra. Bấm Gửi kết quả — đạt thì hoàn tất đóng gói.
7. Đạt: app lưu đóng gói, nhật ký người/thời điểm và thông báo xanh; tự xóa mã của cặp vừa gửi để sẵn sàng máy tiếp theo. Không đạt: lưu lỗi, trả việc về KTV, không đóng gói.
8. Người khác bấm Cập nhật danh sách máy để thấy kết quả. Chưa có cập nhật tự động theo thời gian thực.

## Các tình huống phải thử

- 6 danh tính cùng nhận một PC: chỉ 1 nhận thành công.
- Thân PC 1 + hộp PC 2: SAI CẶP, không có bước gửi đóng gói.
- Hai tem cùng loại: chưa đủ đối chiếu.
- Serial nhập sai: không lưu; giữ màn hình để sửa.
- Chưa nhận máy, hết hạn, người khác giữ máy: không gửi được.
- Bấm gửi lại cùng thao tác: chỉ có một bản ghi hoàn tất.
- Báo không đạt: KTV thấy máy quay lại việc cần xử lý; sửa/báo lại rồi QC kiểm tra lại.
- Thay mainboard: hủy kết quả kiểm tra/đóng gói cũ và lượt giữ máy; yêu cầu kích hoạt, kiểm tra lại.

## Bản chạy tại Công ty

MO_APP_TEST.cmd vẫn dùng test_app.py để chia sẻ trong mạng nội bộ, dữ liệu được giữ khi dừng/mở lại nếu giữ nguyên test-data. HTTP nội bộ không bật camera trực tiếp; điện thoại dùng ảnh chụp hoặc cần người quản trị triển khai HTTPS. Không mở cổng router ra Internet.

Bản F đã kiểm thử bằng mã và trình duyệt mô phỏng, chưa kiểm chứng camera trên điện thoại, máy in tem, mạng Công ty hay tải trên dịch vụ thật. Hai app BẢN QUYỀN và QUẢN LÝ DỰ ÁN vẫn độc lập; không sửa Google Sheet hiện có.
