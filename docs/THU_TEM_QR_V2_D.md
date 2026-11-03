# Thử số lượng PC, tem QR và kiểm tra độc lập — V2-D

Bản này bổ sung vào app BẢN QUYỀN, không thay đổi QUẢN LÝ DỰ ÁN.

1. Admin tạo điểm tại Đơn vị & tài khoản, tạo máy tại Thiết bị.
2. Mở Kế hoạch PC theo điểm, chọn điểm, nhập tổng số PC và lưu. Chọn từng máy và bấm Cấp số thứ tự máy. Số không đổi khi in lại; không cấp vượt kế hoạch.
3. Chọn In tem PC và vỏ hộp. Chọn máy, khổ mặc định 60 × 40 mm. Tải HTML, mở bằng trình duyệt, bấm In 2 tem, chọn 100%, tắt đầu/chân trang. Cần thử trên máy in thật trước in hàng loạt. Tên đơn vị dài cần chọn khổ tem lớn hơn.
4. Mỗi PC có hai QR phân biệt THÂN MÁY/VỎ HỘP. Cùng tên điểm, thứ tự/tổng số, mã máy và serial. Không chứa key hoặc tài khoản Microsoft.
5. Đối chiếu tem và kiểm tra: chụp từng QR hoặc chọn ảnh; cũng có thể dán nội dung mã trong phần thử ở màn hình in tem. Đây là đọc ảnh từng QR, chưa phải camera quét liên tục. Điện thoại có thể hỏi quyền camera; chỉ cấp khi dùng chức năng chụp.
6. ĐÚNG CẶP cần hai tem khác loại cùng hồ sơ và thông tin. SAI CẶP nếu khác máy/thông tin; cùng loại hoặc thiếu một tem thì chưa đủ đối chiếu. Hai tem đúng không chứng minh đã dán lên đúng thiết bị: vẫn phải đọc serial thực.
7. Chọn Bộ phận kiểm tra độc lập mẫu. Đối chiếu cặp tem, nhập serial trên PC, kết quả và nội dung kiểm tra rồi lưu. Máy không đạt quay lại công việc KTV. Sau khi KTV sửa/báo thành công, kiểm tra lại.
8. Chỉ máy đã kích hoạt tất cả giấy phép, kiểm tra đạt và đúng cặp tem mới được người kiểm tra xác nhận đóng gói hoàn tất. Thay mainboard sẽ hủy kết quả kiểm tra/đóng gói cũ.

## Giới hạn bản thử

Dữ liệu nghiệp vụ vẫn riêng từng phiên. Hai điện thoại/PC cùng bản app có thể kiểm tra chữ ký và đối chiếu hai QR (dữ liệu tại lúc in), nhưng không truy cập sổ dữ liệu của phiên khác. Kết quả kiểm tra không tự chuyển từ điện thoại về phiên PC. Thử trọn quy trình lưu kết quả trong cùng phiên trình duyệt bằng hai mã mẫu, hoặc ảnh QR.

Khóa ký tem thử chia sẻ trong tiến trình app; app khởi động lại có thể làm tem thử mất hiệu lực. Chưa dùng tem này cho vận hành thật. Bản thật cần khóa qr_signing_key ổn định trong secrets, dữ liệu chung, đăng nhập QC thực và kiểm thử điện thoại/máy in. QR là chuỗi dữ liệu đã ký, không phải URL tự mở bằng camera điện thoại; mở app Đối chiếu tem và kiểm tra để chụp/đọc.

Chưa bổ sung bàn giao theo đợt/xuất Excel, in lại một tem riêng, máy quét camera liên tục, hoặc kết nối hai app. Chưa kiểm chứng khổ in thực tế, độ bám tem và camera trên điện thoại của V.
