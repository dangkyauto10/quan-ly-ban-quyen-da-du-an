# BẢN QUYỀN V2-E — gói kiểm thử tại Công ty

## 1. Cài và mở

- Giải nén ZIP vào một thư mục cố định trên một PC Windows; cần Python 3.12 và Internet để cài thư viện lần đầu.
- Nháy đúp CAI_DAT_LAN_DAU.cmd. Thành công thì chạy MO_APP_TEST.cmd.
- Giữ cửa sổ chạy mở suốt thời gian test. PC truy cập http://localhost:8501.
- Các PC/điện thoại khác dùng cùng mạng, truy cập http://DIA_CHI_IPv4_CUA_MAY_CHAY:8501. Cửa sổ chạy in ipconfig để tìm IPv4 của card đang kết nối, ví dụ 192.168.x.x (không dùng địa chỉ ví dụ để truy cập).
- Nếu Windows hỏi quyền mạng Python, chỉ cho phép mạng Riêng tư/Private của Công ty. Không mở cổng router ra Internet. Mạng khách có thể chặn các máy nhìn thấy nhau.
- Đây là chọn vai trò giả phục vụ test, không phải tài khoản đăng nhập thật. Không nhập key thật, mật khẩu hoặc thông tin bí mật.
- Dữ liệu và khóa mã hóa nằm ở test-data trên máy chủ. Không xóa/chỉ sao chép riêng file DB; cần giữ cả thư mục. Chạy một cửa sổ app duy nhất trên một PC, các thành viên dùng trình duyệt truy cập.

## 2. Chia việc test

| Người | Chọn vai trò | Thực hiện |
|---|---|---|
| Người quản trị | Admin mẫu | Kiểm tra/redeem giả; tạo điểm và máy; đặt số lượng, cấp số PC; phân bản quyền/KTV |
| KTV | KTV có việc | Báo thành công PC-MAU-02; mở In tem PC và vỏ hộp, tải cặp tem |
| Bộ phận kiểm tra | Bộ phận kiểm tra độc lập mẫu | Nhận hai mã, đối chiếu đúng/sai; nhập serial thực và kết quả; xác nhận đóng gói |
| KTV thứ hai | KTV khác — chưa có việc | Kiểm tra không thấy máy được giao cho KTV trước |

Bộ minh họa có hai máy PC-MAU-01, PC-MAU-02. Admin vào Kế hoạch PC theo điểm, đặt tổng 2 rồi cấp số cho cả hai. PC-MAU-01 đã báo thành công giả, PC-MAU-02 đang lỗi giả để thử báo lại. Không redeem key giả trên website Microsoft.

## 3. In và đối chiếu

- Chọn máy, mặc định tem 60 × 40 mm. Tải HTML, mở trên PC và in 100%, tắt đầu/chân trang. Chưa có máy in thì dùng các mã trong mục Mã tem để thử đối chiếu.
- Mỗi PC có một tem THÂN MÁY và một tem VỎ HỘP, cùng tên điểm, số thứ tự/tổng, mã máy và serial.
- Máy quét cần loại 2D đọc được QR, kết nối USB, chế độ bàn phím HID. Đặt bàn phím Windows tiếng Anh, tắt Caps Lock khi quét. Chọn ô Mã QR 1, quét thân PC; chọn ô Mã QR 2, quét hộp. Nếu cấu hình Enter cuối mã, mã sẽ được gửi về app; nếu chưa thì nhấn Enter hoặc bấm ra ngoài ô. Bản này chưa tự chuyển con trỏ giữa hai ô.
- Điện thoại có thể tải ảnh QR vào từng ô. Truy cập IP nội bộ bằng HTTP không có camera web trực tiếp; dùng camera máy chụp ảnh rồi chọn ảnh. QR chứa dữ liệu đã ký, không tự mở website khi dùng camera thường.
- ĐÚNG CẶP chỉ xác nhận tem khớp nhau. Người kiểm tra vẫn cần đối chiếu serial thực trên PC, thực hiện kiểm tra kỹ thuật và nhập nội dung.
- Máy đạt mới được xác nhận đóng gói. Máy không đạt chuyển lại việc KTV để sửa/báo lại, sau đó kiểm tra lại. Thử quét PC của máy 1 với hộp máy 2 phải báo SAI CẶP; quét hai tem cùng loại phải báo chưa đủ đối chiếu.
- Hai máy tính/điện thoại cùng bản nội bộ dùng chung dữ liệu. Giữ test-data thì khởi động lại app vẫn đọc được tem cũ. Tem bản demo trực tuyến khác không dùng chung với gói này.

## 4. Ghi nhận kết quả

Mỗi thành viên ghi: bước thử, mã máy, kết quả mong đợi/thực tế và ảnh lỗi nếu có. Admin tải danh sách CSV (mở bằng Excel) tại Kế hoạch PC theo điểm để đối soát. Cập nhật từ người khác hiện khi đổi trang hoặc thực hiện thao tác; chưa có cập nhật trực tiếp liên tục.

Dừng app trước khi chạy SAO_LUU_TEST.cmd. Khôi phục: dừng app, giữ bản hiện tại, giải nén bản sao lưu và đặt nguyên thư mục test-data vào chỗ cũ rồi mở lại. Bản sao lưu test chứa khóa của dữ liệu thử nên chỉ giữ trong nhóm test.

## 5. Phạm vi bàn giao

Đã kiểm tra tự động trên môi trường phát triển. Chưa thực nghiệm Windows, mạng Công ty, máy in, máy quét hay điện thoại của đội. Chưa phải bản vận hành thật: đăng nhập riêng từng thành viên, quyền thực tế, sao lưu tự động và triển khai trực tuyến dữ liệu chung còn phải hoàn thiện. Không thay đổi app QUẢN LÝ DỰ ÁN hoặc Google Sheet hiện có.
